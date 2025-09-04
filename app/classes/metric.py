import ast
import re
import typing as t

import numpy as np
import pandas as pd


def _prepare_element_wise_args(
    *args: t.Union[pd.Series, int, float],
) -> tuple[list[t.Union[pd.Series, int, float]], bool]:
    """
    Helper to validate and prepare arguments for element-wise operations.

    Returns a tuple containing:
    - A list of prepared arguments (all as pd.Series if any series was present).
    - A boolean indicating if the result should be a pd.Series.
    """
    if not args:
        raise ValueError("At least one argument is required.")

    is_series_op = any(isinstance(arg, pd.Series) for arg in args)

    if is_series_op:
        series_list = [s for s in args if isinstance(s, pd.Series)]

        # Validate that all series have the same length
        if len(series_list) > 1:
            first_series_len = len(series_list[0])
            if not all(len(s) == first_series_len for s in series_list[1:]):
                raise ValueError("All series arguments must have the same length.")

        # Find the length from the first available series
        series_len = len(series_list[0])

        # Convert all arguments to Series of the same length
        prepared_args = [
            arg if isinstance(arg, pd.Series) else pd.Series([arg] * series_len)
            for arg in args
        ]
        return prepared_args, True
    else:
        return args, False


def element_wise_sum(
    *args: t.Union[pd.Series, int, float],
) -> t.Union[pd.Series, int, float]:
    prepared_args, is_series_op = _prepare_element_wise_args(*args)

    if is_series_op:
        return pd.concat(prepared_args, axis=1).sum(axis=1)
    else:
        return np.sum(prepared_args)


def element_wise_mean(
    *args: t.Union[pd.Series, int, float],
) -> t.Union[pd.Series, int, float]:
    prepared_args, is_series_op = _prepare_element_wise_args(*args)

    if is_series_op:
        return pd.concat(prepared_args, axis=1).mean(axis=1)
    else:
        return np.mean(prepared_args)


def element_wise_median(
    *args: t.Union[pd.Series, int, float],
) -> t.Union[pd.Series, int, float]:
    prepared_args, is_series_op = _prepare_element_wise_args(*args)

    if is_series_op:
        return pd.concat(prepared_args, axis=1).median(axis=1)
    else:
        return np.median(prepared_args)


def element_wise_min(
    *args: t.Union[pd.Series, int, float],
) -> t.Union[pd.Series, int, float]:
    prepared_args, is_series_op = _prepare_element_wise_args(*args)

    if is_series_op:
        return pd.concat(prepared_args, axis=1).min(axis=1)
    else:
        return np.min(prepared_args)


def element_wise_max(
    *args: t.Union[pd.Series, int, float],
) -> t.Union[pd.Series, int, float]:
    prepared_args, is_series_op = _prepare_element_wise_args(*args)

    if is_series_op:
        return pd.concat(prepared_args, axis=1).max(axis=1)
    else:
        return np.max(prepared_args)


def element_wise_std(
    *args: t.Union[pd.Series, int, float],
) -> t.Union[pd.Series, int, float]:
    prepared_args, is_series_op = _prepare_element_wise_args(*args)

    if is_series_op:
        return pd.concat(prepared_args, axis=1).std(axis=1)
    else:
        return np.std(prepared_args)


class QueryValidator(ast.NodeVisitor):
    allowed_functions = {
        "sum",
        "mean",
        "median",
        "min",
        "max",
        "std",
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
        self.placeholder_map[identifier] = original_name

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
        if isinstance(expr_node, ast.Name):
            return False

        if isinstance(expr_node, ast.Constant):
            return True

        if isinstance(expr_node, ast.BinOp):
            return all([
                isinstance(expr_node.op, self.allowed_operators),
                self.is_result_scalar(expr_node.left),
                self.is_result_scalar(expr_node.right),
            ])

        if isinstance(expr_node, ast.Call):
            if isinstance(expr_node.func, ast.Name):
                return all(self.is_result_scalar(arg) for arg in expr_node.args)
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

        return False


class Metric:
    def __init__(
        self,
        name: str,
        query: str,
        use_thousand_sep: bool = True,
        is_percentage: bool = False,
        decimal_places: int = 2,
    ):
        """
        Initializes a Metric object.

        Args:
            name: A human-readable name for the metric.
            query_string: A string representing the calculation logic for the metric.
            use_thousand_sep: Whether to format numbers with a thousand separator.
            is_percentage: Whether the metric represents a percentage value.
            decimal_places: Number of decimal places to format the metric value.
        """

        self.name = name
        self.original_query = query
        self.use_thousand_sep = use_thousand_sep
        self.is_percentage = is_percentage
        self.decimal_places = decimal_places
        self.used_columns: list[str] = []
        self.processed_query: str = ""
        self.placeholder_map: dict[str, str] = {}

    @property
    def query(self):
        return self.original_query

    @property
    def format(self) -> str:
        return f"{{:{',' if self.use_thousand_sep else ''}.{self.decimal_places}f}}{'%' if self.is_percentage else ''}"

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
        self.placeholder_map = validator.placeholder_map
        self.processed_query = processed_expression

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
        for processed_col, original_col in self.placeholder_map.items():
            scope[processed_col] = data[original_col]

        # Add numpy functions to scope
        scope["sum"] = element_wise_sum
        scope["mean"] = element_wise_mean
        scope["median"] = element_wise_median
        scope["min"] = element_wise_min
        scope["max"] = element_wise_max
        scope["std"] = element_wise_std

        result = eval(self.processed_query, {"__builtins__": {}}, scope)

        if not np.isscalar(result):
            raise ValueError(
                f"The result of the metric query must be a scalar value.\nResult:\n{result}"
            )

        if self.is_percentage:
            result *= 100

        return result

    def copy(self) -> "Metric":
        new_metric = Metric(
            self.name,
            self.query,
            self.use_thousand_sep,
            self.is_percentage,
            self.decimal_places,
        )
        new_metric.used_columns = self.used_columns.copy()
        return new_metric

    def to_dict(self) -> dict[str, str | list[str]]:
        """Serializes the Metric object to a dictionary."""
        return {
            "name": self.name,
            "original_query": self.original_query,
            "use_thousand_sep": self.use_thousand_sep,
            "is_percentage": self.is_percentage,
            "decimal_places": self.decimal_places,
            "used_columns": self.used_columns,
            "placeholder_map": self.placeholder_map,
            "processed_query": self.processed_query,
        }

    @classmethod
    def from_dict(cls, dict_data: dict[str, t.Any]) -> "Metric":
        """Creates a Metric object from a dictionary."""
        instance = cls(
            name=dict_data["name"],
            query=dict_data["original_query"],
            use_thousand_sep=dict_data.get("use_thousand_sep", True),
            is_percentage=dict_data.get("is_percentage", False),
            decimal_places=dict_data.get("decimal_places", 2),
        )

        instance.used_columns = dict_data["used_columns"]
        instance.placeholder_map = dict_data["placeholder_map"]
        instance.processed_query = dict_data["processed_query"]

        return instance


__all__ = [
    "QueryValidator",
    "Metric",
]
