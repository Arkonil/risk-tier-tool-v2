import ast
import re

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from risc_tool.data.models.exceptions import InvalidFilterError
from risc_tool.data.models.types import FilterID


class FilterQueryValidator(ast.NodeVisitor):
    """
    An AST visitor that identifies identifiers used as variables/columns,
    attempting to exclude those used only as function names.
    """

    def __init__(self, placeholder_map: dict[str, str]):
        self.found_columns: set[str] = set()
        self.placeholder_map = placeholder_map

    def _resolve_and_add_name(self, identifier: str):
        if identifier.startswith("@"):
            return  # Exclude @-variables

        original_name = self.placeholder_map.get(identifier, identifier)
        if (
            identifier.startswith("__BACKTICKED_")
            and identifier not in self.placeholder_map
        ):
            return  # Ignore unmapped placeholders

        self.found_columns.add(original_name)

    def visit_Name(self, node: ast.Name):
        self._resolve_and_add_name(node.id)

    def visit_Attribute(self, node: ast.Attribute):
        # Find the base identifier of an attribute chain (e.g., 'col' in 'col.str.contains')
        current_obj = node
        while isinstance(current_obj, ast.Attribute):
            current_obj = current_obj.value

        if isinstance(current_obj, ast.Name):
            self._resolve_and_add_name(current_obj.id)
        elif isinstance(current_obj, ast.AST):
            # If the base is a complex expression (e.g., `(colA+colB).method()`), visit it
            self.visit(current_obj)

    def visit_Call(self, node: ast.Call):
        # In a function call `f(arg)`, `f` is the function and `arg` is the potential column.
        # We visit the arguments, but we avoid visiting `node.func` if it is a simple name
        # to prevent adding function names like 'sin' to our column list.
        if not isinstance(node.func, ast.Name):
            # If func is complex (e.g., `col.method()`), visit it to find `col`.
            self.visit(node.func)

        for arg in node.args:
            self.visit(arg)
        for kwarg in node.keywords:
            self.visit(kwarg.value)


class Filter(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias=True,
        validate_by_alias=True,
        extra="allow",
        arbitrary_types_allowed=True,
    )

    uid: FilterID
    name: str
    query: str
    used_columns: list[str] = Field(default_factory=list)
    mask: pd.Series | None = None

    @property
    def pretty_name(self):
        return self.name

    def validate_query(self, available_columns: list[str] | None = None) -> None:
        # --- 1. Preprocess Backticked Identifiers ---
        # This allows parsing names with spaces or special characters.
        backticked_map: dict[str, str] = {}

        def replace_backtick(match: re.Match) -> str:
            name_inside_ticks = match.group(1)
            placeholder = f"__BACKTICKED__{len(backticked_map)}__"
            backticked_map[placeholder] = name_inside_ticks
            return placeholder

        processed_expression = re.sub(r"`([^`]+)`", replace_backtick, self.query)

        # --- 2. Parse and Validate Structure & Semantics ---
        tree = ast.parse(processed_expression, mode="exec")

        if not tree.body or len(tree.body) > 1:
            raise InvalidFilterError(
                self.query,
                "Query expression must contain exactly one single expression.",
            )

        statement = tree.body[0]

        if isinstance(statement, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            raise InvalidFilterError(
                self.query,
                "Assignments ('=') are not allowed. Use '==' for comparison.",
            )

        if not isinstance(statement, ast.Expr):
            raise InvalidFilterError(
                self.query,
                f"Query expression cannot contain statements of type '{type(statement).__name__}'. Only expressions are allowed.",
            )

        expr_node = statement.value

        # --- 3. Heuristic Check for Boolean Nature ---
        allowed_top_level_nodes = (
            ast.Compare,  # a > b, a == b
            ast.BoolOp,  # a and b, a or b
            ast.Constant,  # True (Python 3.8+)
            ast.Name,  # bool_col
            ast.Attribute,  # df.bool_col
            ast.Call,  # col.str.contains('x')
            ast.Subscript,  # col[index] -> bool
        )

        is_likely_boolean = False
        if isinstance(expr_node, allowed_top_level_nodes):
            is_likely_boolean = True
        elif isinstance(expr_node, ast.BinOp) and isinstance(
            expr_node.op, (ast.BitAnd, ast.BitOr, ast.BitXor)
        ):
            # `(a > 1) & (b > 2)` is a valid logical combination
            is_likely_boolean = True
        elif isinstance(expr_node, ast.UnaryOp) and isinstance(
            expr_node.op, (ast.Not, ast.Invert)
        ):
            # `not (a > 1)` or `~bool_col` are valid
            is_likely_boolean = True

        if not is_likely_boolean:
            node_type_name = type(expr_node).__name__
            reason = f"the top-level operation is '{node_type_name}', which typically does not produce a boolean result."
            if isinstance(expr_node, ast.BinOp):
                op_type_name = type(expr_node.op).__name__
                reason = f"the top-level arithmetic operator is '{op_type_name}'."

            raise InvalidFilterError(
                self.query, f"Expression does not appear to be boolean; {reason}"
            )

        # --- 4. Extract Column Names if Structurally Valid ---
        finder = FilterQueryValidator(backticked_map)
        finder.visit(expr_node)
        self.used_columns = sorted(list(finder.found_columns))

        # --- 5. Optionally Check Against List of Available Columns ---
        if available_columns is not None:
            available_set = set(available_columns)
            used_set = set(self.used_columns)
            missing_columns = sorted(list(used_set - available_set))
            if missing_columns:
                raise InvalidFilterError(
                    self.query,
                    f"Following columns are not found in the data: {', '.join(missing_columns)}",
                )

    def create_mask(self, data: pd.DataFrame) -> None:
        # if self.mask is not None:
        #     return

        data_copy = data.copy()
        mask = data_copy.eval(self.query.replace("\n", " "), inplace=False)

        if isinstance(mask, pd.DataFrame) and mask.shape[1] == 1:
            # Converting dataframe with a single column to a series
            mask = mask.iloc[:, 0]

        if not isinstance(mask, pd.Series):
            raise ValueError(
                f"Invalid query used: {self.query}. Result is not a pandas series."
            )

        if not pd.api.types.is_bool_dtype(mask):
            raise ValueError(
                f"Invalid query used: {self.query}. Result is not a boolean series."
            )

        if len(mask) != len(data):
            raise ValueError(
                f"Length Mismatch: len(mask) != len(data) ({len(mask)} != {len(data)}). The query is not applicable to the data."
            )

        self.mask = mask

    def duplicate(self, uid: FilterID | None = None, name: str | None = None):
        if uid is None:
            uid = self.uid
        if name is None:
            name = self.name

        return self.model_copy(
            update={
                "uid": uid,
                "name": name,
                "used_columns": self.used_columns.copy(),
                "mask": self.mask.copy() if self.mask is not None else None,
            }
        )


__all__ = ["Filter"]
