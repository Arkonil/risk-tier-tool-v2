import ast
import re
import typing as t

import numpy as np
import pandas as pd


class QueryValidator(ast.NodeVisitor):
    allowed_functions = {
        "sum",
        "mean",
        "median",
        "min",
        "max",
        "std",
        "var",
        "count",
        "count_distinct",
    }

    allowed_series_methods = {
        "all",
        "any",
        "autocorr",
        "corr",
        "count",
        "cov",
        "kurt",
        "max",
        "mean",
        "median",
        "min",
        "mode",
        "prod",
        "quantile",
        "sem",
        "skew",
        "std",
        "sum",
        "var",
        "kurtosis",
        "nunique",
    }

    # 'quantile' must be scalar

    allowed_operators = (
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.Mod,
        ast.FloorDiv,
    )

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
        if isinstance(node.func, ast.Name):
            if node.func.id not in self.allowed_functions:
                raise ValueError(f"Unsupported function: {node.func.id}")
        else:
            # If func is complex (e.g., `col.method()`), visit it to find `col`.
            self.visit(node.func)

        for arg in node.args:
            self.visit(arg)

        for kwarg in node.keywords:
            self.visit(kwarg.value)

    def visit_BinOp(self, node: ast.BinOp):
        if not isinstance(node.op, self.allowed_operators):
            raise ValueError(f"Unsupported binary operator: {type(node.op).__name__}")

        self.visit(node.left)
        self.visit(node.right)

    def is_result_scalar(self, expr_node: ast.AST) -> bool:
        if isinstance(expr_node, ast.Constant):
            return True

        if isinstance(expr_node, ast.Call):
            if isinstance(expr_node.func, ast.Name):
                func_name = expr_node.func.id
                return func_name in self.allowed_functions
            elif isinstance(expr_node.func, ast.Attribute):
                func_name = expr_node.func.attr

                if func_name == "quantile":
                    if expr_node.args:
                        return isinstance(expr_node.args[0], ast.Constant)

                    if expr_node.keywords:
                        for kw in expr_node.keywords:
                            if kw.arg == "q":
                                return isinstance(kw.value, ast.Constant)

                return func_name in self.allowed_series_methods

        if isinstance(expr_node, ast.BinOp):
            return all([
                isinstance(expr_node.op, self.allowed_operators),
                self.is_result_scalar(expr_node.left),
                self.is_result_scalar(expr_node.right),
            ])


class Metric:
    def __init__(self, id_: str, name: str, query_string: str):
        self.id = id_
        self.name = name
        self._query = query_string
        self.used_columns: list[str] = []

    @property
    def query(self):
        return self._query

    @property
    def pretty_name(self):
        return self.name

    def validate_query(self, data: pd.DataFrame) -> None:
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
        expr_node = ast.parse(processed_expression, mode="eval").body

        # --- 3. Validate Query Structure ---
        validator = QueryValidator(backticked_map)

        if not validator.is_result_scalar(expr_node):
            node_type_name = type(expr_node).__name__
            raise ValueError(
                f"Expression does not appear to be a scalar value; top-level operation is '{node_type_name}'."
            )

        validator.visit(expr_node)

        # --- 4. Extract Column Names and Functions if Structurally Valid ---
        self.used_columns = sorted(list(validator.found_columns))

        # --- 5. Check Against List of Available Columns ---
        available_columns = data.columns.to_list()
        available_set = set(available_columns)
        used_set = set(self.used_columns)
        missing_columns = sorted(list(used_set - available_set))
        if missing_columns:
            raise ValueError(
                f"Following columns are not found in the data: {', '.join(missing_columns)}"
            )

        #  --- 6. Test-evaluate the expression to catch runtime errors ---
        result = self.calculate(data)

        if not np.isscalar(result):
            raise ValueError("The result of the metric query must be a scalar value.")

    def calculate(self, data: pd.DataFrame) -> int | float | np.number:
        # Local scope for eval
        scope = {}

        # Add columns to scope
        for col in self.used_columns:
            scope[col] = data[col]

        # Add numpy functions to scope
        scope["sum"] = np.sum
        scope["mean"] = np.mean
        scope["median"] = np.median
        scope["min"] = np.min
        scope["max"] = np.max
        scope["std"] = np.std
        scope["var"] = np.var
        scope["count"] = lambda series: series.size
        scope["count_distinct"] = lambda series: series.nunique()

        try:
            result = eval(self.query, {"__builtins__": {}}, scope)
        except Exception as e:
            raise RuntimeError(f"An error occurred during query evaluation: {e}")

        if not np.isscalar(result):
            raise ValueError(
                f"The result of the metric query must be a scalar value.\nResult:\n{result}"
            )

        return result

    def copy(self) -> "Metric":
        new_metric = Metric(self.id, self.name, self.query)
        new_metric.used_columns = self.used_columns.copy()
        return new_metric

    def to_dict(self) -> dict[str, str | list[str]]:
        """Serializes the Metric object to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "query": self.query,
            "used_columns": self.used_columns,
        }

    @classmethod
    def from_dict(cls, dict_data: dict[str, t.Any]) -> "Metric":
        """Creates a Metric object from a dictionary."""
        instance = cls(
            id_=dict_data["id"],
            name=dict_data["name"],
            query_string=dict_data["query"],
        )

        if "used_columns" in dict_data:
            instance.used_columns = dict_data["used_columns"]

        return instance


__all__ = [
    "QueryValidator",
    "Metric",
]
