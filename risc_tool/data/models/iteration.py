import textwrap
import typing as t
from abc import ABC, abstractmethod
from string import Template

import numpy as np
import pandas as pd

from risc_tool.data.models.defaults import DefaultOptions
from risc_tool.data.models.enums import (
    GridColumn,
    IterationType,
    LossRateTypes,
    RangeColumn,
    RSDetCol,
    VariableType,
)
from risc_tool.data.models.iteration_output import IterationOutput
from risc_tool.data.models.json_models import DataFrameTightJSON, IterationJSON
from risc_tool.data.models.types import IterationID
from risc_tool.utils.wrap_text import TAB, wrap_text


class IterationBase(ABC):
    var_type: VariableType
    iter_type: IterationType

    @staticmethod
    @abstractmethod
    def _new_group_default_value_factory():
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def _create_initial_groups(
        variable: pd.Series, initial_group_count: int
    ) -> pd.Series:
        raise NotImplementedError()

    def __init__(
        self, uid: IterationID, name: str, variable: pd.Series, initial_group_count: int
    ):
        self.uid = uid
        self.name = name
        self._variable = variable
        self._groups = self._create_initial_groups(variable, initial_group_count)
        self._default_groups = self._groups.copy()
        self.active: bool = True

    @property
    def variable(self) -> pd.Series:
        return self._variable

    @property
    def pretty_name(self) -> str:
        parts = [f"Itearation #{self.uid}"]

        if self.name:
            parts.append(self.name)

        return " - ".join(parts)

    @property
    @abstractmethod
    def groups(self) -> pd.Series:
        raise NotImplementedError()

    @property
    def default_groups(self) -> pd.Series:
        return self._default_groups

    def set_default_groups(self, default_groups: pd.Series):
        self._default_groups = default_groups.copy()
        self._groups = default_groups.copy()

    @abstractmethod
    def get_risk_segments(
        self, previous_risk_segments: pd.Series | None, default: bool
    ) -> IterationOutput:
        raise NotImplementedError()

    @abstractmethod
    def set_group(
        self,
        group_index: int,
        lower_bound: float | None = None,
        upper_bound: float | None = None,
        categories: set[str] | None = None,
    ):
        raise NotImplementedError()

    @abstractmethod
    def _validate(self, default: bool) -> tuple[list[str], list[str], list]:
        raise NotImplementedError()

    @abstractmethod
    def get_group_mapping(self, default: bool) -> IterationOutput:
        raise NotImplementedError()

    def _check_group_index(self, group_index: int) -> None:
        num_groups = len(self._groups)

        if group_index < 0 or group_index >= num_groups:
            raise ValueError(
                f"Value of colidx out of range [0, {num_groups - 1}]. "
                f"Provided value: {group_index}"
            )

    def to_dict(self) -> IterationJSON:
        """Serializes the IterationBase object to a dictionary."""
        return IterationJSON(
            var_type=self.var_type,
            iter_type=self.iter_type,
            uid=self.uid,
            name=self.name,
            variable_name=str(self._variable.name),
            groups=self._groups.to_dict(),
            default_groups=self._default_groups.to_dict(),
        )

    def generate_sas_code_for_groups(
        self, default: bool, mapping: dict[t.Hashable, int]
    ) -> str:
        """Generates SAS code to create this iteration."""
        groups = self.default_groups if default else self.groups

        code_template = 'if missing($VARIABLE_NAME) then $OUTPUT_VARIABLE_NAME = "";\n'

        if self.var_type == VariableType.NUMERICAL:
            for group_index, group_value in groups.items():
                lower_bound, upper_bound = group_value
                if (
                    np.isnan(lower_bound)
                    or np.isnan(upper_bound)
                    or lower_bound >= upper_bound
                ):
                    continue

                code_template += (
                    f"else if {lower_bound} < $VARIABLE_NAME <= {upper_bound} then\n"
                    f"    $OUTPUT_VARIABLE_NAME = $GROUP_INDEX_{mapping.get(group_index, group_index)};\n"
                )

        elif self.var_type == VariableType.CATEGORICAL:
            for group_index, group_value in groups.items():
                if len(group_value) == 0:
                    continue

                if pd.api.types.is_numeric_dtype(self.variable.cat.categories.dtype):
                    categories = ", ".join(str(cat) for cat in group_value)
                else:
                    categories = ", ".join(f'"{cat}"' for cat in group_value)

                categories = wrap_text(
                    categories,
                    width=80,
                    break_long_words=False,
                    break_on_hyphens=False,
                )

                if len(categories) > 1:
                    category_text = textwrap.indent("\n".join(categories), TAB)
                    category_text = "\n" + category_text + "\n"
                else:
                    category_text = categories[0]

                code_template += (
                    f"else if $VARIABLE_NAME in ({category_text}) "
                    f"then $OUTPUT_VARIABLE_NAME = $GROUP_INDEX_{mapping.get(group_index, group_index)};\n"
                )

        else:
            raise ValueError(f"Unsupported variable type: {self.var_type}")

        code_template += "else $OUTPUT_VARIABLE_NAME = $MISSING;\n"

        return code_template


class SingleVarIteration(IterationBase):
    iter_type = IterationType.SINGLE

    def __init__(self, risk_segment_details: pd.DataFrame, **kwargs):
        super().__init__(**kwargs, initial_group_count=len(risk_segment_details))

        self._risk_segment_details = risk_segment_details

    @property
    def groups(self) -> pd.Series:
        return self._groups.copy()

    @property
    def risk_segment_details(self) -> pd.DataFrame:
        return self._risk_segment_details.copy()

    def update_maf(self, loss_rate_type: LossRateTypes, maf: pd.Series):
        if len(maf) != len(self._risk_segment_details):
            raise ValueError(f"Invalid maf length: {len(maf)}")

        if loss_rate_type == LossRateTypes.DLR:
            self._risk_segment_details[RSDetCol.MAF_DLR] = maf.to_list()
        elif loss_rate_type == LossRateTypes.ULR:
            self._risk_segment_details[RSDetCol.MAF_ULR] = maf.to_list()
        else:
            raise ValueError(f"Invalid loss rate type: {loss_rate_type}")

    def update_color(
        self,
        color_type: t.Literal[RSDetCol.BG_COLOR, RSDetCol.FONT_COLOR],
        color: pd.Series,
    ):
        if len(color) != len(self._risk_segment_details):
            raise ValueError(f"Invalid color length: {len(color)}")

        if color_type == RSDetCol.BG_COLOR:
            self._risk_segment_details[RSDetCol.BG_COLOR] = color.to_list()
        elif color_type == RSDetCol.FONT_COLOR:
            self._risk_segment_details[RSDetCol.FONT_COLOR] = color.to_list()
        else:
            raise ValueError(f"Invalid color type: {color_type}")

    def get_risk_segments(
        self, previous_risk_segments: pd.Series | None, default: bool
    ) -> IterationOutput:
        output = self.get_group_mapping(default=default)

        output.risk_segment_column = output.risk_segment_column.astype(
            pd.CategoricalDtype(categories=self.risk_segment_details.index)
        )

        return output

    def to_dict(self) -> IterationJSON:
        dict_data = super().to_dict()

        dict_data.risk_segment_details = DataFrameTightJSON.model_validate(
            self._risk_segment_details.to_dict(orient="tight")
        )

        return dict_data

    def generate_sas_code(self, default: bool) -> Template:
        groups = self.default_groups if default else self.groups
        mapping = {group_index: group_index for group_index in groups.index}

        code_template = "format $OUTPUT_VARIABLE_NAME $$50.;\n\n"
        code_template += super().generate_sas_code_for_groups(default, mapping=mapping)
        return Template(code_template)

    def generate_python_code(self, default: bool) -> Template:
        groups = self.default_groups if default else self.groups

        group_definitions = ""
        if self.var_type == VariableType.NUMERICAL:
            for group_index, group_value in groups.items():
                lower_bound, upper_bound = group_value
                if (
                    np.isnan(lower_bound)
                    or np.isnan(upper_bound)
                    or lower_bound >= upper_bound
                ):
                    continue

                group_definitions += f"pd.Interval({lower_bound}, {upper_bound}, closed='right'): $GROUP_INDEX_{group_index},\n"

        elif self.var_type == VariableType.CATEGORICAL:
            for group_index, group_value in groups.items():
                if len(group_value) == 0:
                    continue

                if pd.api.types.is_numeric_dtype(self.variable.cat.categories.dtype):
                    categories = ", ".join(str(cat) for cat in sorted(group_value))
                else:
                    categories = ", ".join(f'"{cat}"' for cat in sorted(group_value))

                group_definitions += f"({categories},): $GROUP_INDEX_{group_index},\n"

        code_template = f"iter_{self.uid}_map = {{\n"
        code_template += textwrap.indent(group_definitions, TAB)
        code_template += "}\n"
        code_template += f"iter_{self.uid}_map = pd.Series(data=iter_{self.uid}_map.values(), index=list(iter_{self.uid}_map.keys()))\n\n"

        code_template += f'$DATA["$OUTPUT_VARIABLE_NAME"] = create_mapped_variable($DATA["$VARIABLE_NAME"], iter_{self.uid}_map)\n'

        return Template(code_template)


class DoubleVarIteration(IterationBase):
    iter_type = IterationType.DOUBLE

    def __init__(
        self,
        variable: pd.Series,
        risk_segment_details: pd.DataFrame,
        **kwargs,
    ):
        initial_group_count = min(10, variable.nunique())

        super().__init__(
            **kwargs,
            variable=variable,
            initial_group_count=initial_group_count,
        )

        prev_rs_count = len(risk_segment_details)

        self._groups_mask = pd.Series(True, index=self._groups.index)
        self._risk_segment_grid = pd.DataFrame(
            np.repeat(
                np.arange(prev_rs_count).reshape(1, prev_rs_count),
                repeats=len(self._groups),
                axis=0,
            )
        )
        self._default_risk_segment_grid = self._risk_segment_grid.copy()

    @property
    def groups(self) -> pd.Series:
        return self._groups.loc[self._groups_mask]

    @property
    def risk_segment_grid(self) -> pd.DataFrame:
        return self._risk_segment_grid.loc[self._groups_mask, :]

    @property
    def default_risk_segment_grid(self) -> pd.DataFrame:
        return self._default_risk_segment_grid

    def add_group(self, group_index: int | None = None):
        if group_index is None:
            group_index = len(self._groups)

        if group_index < 0:
            raise ValueError(f"Invalid argument for 'group_index': {group_index}")

        num_groups = len(self._groups)

        if group_index >= num_groups:
            self._groups[num_groups] = self._new_group_default_value_factory()

        self._groups_mask[min(group_index, num_groups)] = True

        if len(self._risk_segment_grid) == len(self._groups):
            return

        last_row = self._risk_segment_grid.iloc[[-1]].copy()
        self._risk_segment_grid = pd.concat(
            [self._risk_segment_grid, last_row], ignore_index=True
        )

    def set_default_groups(self, default_groups: pd.Series):
        super().set_default_groups(default_groups)
        self._groups_mask = pd.Series(True, index=self._groups.index)

    def set_default_risk_segment_grid(self, default_risk_segment_grid: pd.DataFrame):
        self._default_risk_segment_grid = default_risk_segment_grid.copy()
        self._risk_segment_grid = default_risk_segment_grid.copy()

    def set_risk_segment_grid(
        self, group_index: int, previous_rs_index: int, value: int
    ):
        self._check_group_index(group_index)

        if previous_rs_index not in self.risk_segment_grid.columns:
            raise ValueError(
                f"Invalid value for risk segment provided: {previous_rs_index}"
            )

        self._risk_segment_grid.at[group_index, previous_rs_index] = value

    def remove_group(self, group_index: int):
        self._check_group_index(group_index)

        if self._groups_mask.drop(group_index).any():
            self._groups_mask.iloc[group_index] = False
        else:
            raise ValueError("Can not remove the last group.")

    def get_risk_segments(
        self, previous_risk_segments: pd.Series | None, default: bool
    ) -> IterationOutput:
        iteration_output = self.get_group_mapping(default=default)
        risk_segment_column = pd.Series(index=self.variable.index)

        if not iteration_output.errors:
            risk_segment_grid = (
                self.default_risk_segment_grid if default else self.risk_segment_grid
            )

            for prev_rs in risk_segment_grid.columns:
                for curr_rs in risk_segment_grid.index:
                    mask = (previous_risk_segments == prev_rs) & (
                        iteration_output.risk_segment_column == curr_rs
                    )

                    risk_segment_column.loc[mask] = risk_segment_grid.loc[
                        curr_rs, prev_rs
                    ]

        risk_segment_column = risk_segment_column.astype(
            pd.CategoricalDtype(categories=self.risk_segment_grid.columns)
        )

        iteration_output.risk_segment_column = risk_segment_column

        return iteration_output

    def to_dict(self):
        dict_data = super().to_dict()

        dict_data.groups_mask = self._groups_mask.to_dict()
        dict_data.risk_segment_grid = DataFrameTightJSON.model_validate(
            self._risk_segment_grid.to_dict(orient="tight")
        )
        dict_data.default_risk_segment_grid = DataFrameTightJSON.model_validate(
            self._default_risk_segment_grid.to_dict(orient="tight")
        )

        return dict_data

    def generate_sas_code(self, default: bool) -> Template:
        grid = self.default_risk_segment_grid if default else self.risk_segment_grid

        code_template = "format $OUTPUT_VARIABLE_NAME $$50.;\n\n"
        code_template += 'if missing($VARIABLE_NAME) or missing($PREV_ITER_OUT_NAME) then $OUTPUT_VARIABLE_NAME = "";\n'

        for column in grid.columns:
            mapping = {
                group_index: grid_value
                for group_index, grid_value in grid[column].to_dict().items()
            }

            code_template += (
                f"else if $PREV_ITER_OUT_NAME = $GROUP_INDEX_{column} then do;\n"
            )

            code_template += textwrap.indent(
                text=self.generate_sas_code_for_groups(
                    default=default, mapping=mapping
                ),
                prefix=TAB,
            )

            code_template += "end;\n"

        code_template += "else $OUTPUT_VARIABLE_NAME = $MISSING;\n"

        return Template(code_template)

    def generate_python_code(self, default: bool) -> Template:
        risk_segment_grid = (
            self.default_risk_segment_grid if default else self.risk_segment_grid
        )
        groups = self.default_groups if default else self.groups

        invalid_groups = []

        group_definitions = ""
        if self.var_type == VariableType.NUMERICAL:
            for group_index, group_value in groups.items():
                lower_bound, upper_bound = group_value
                if (
                    np.isnan(lower_bound)
                    or np.isnan(upper_bound)
                    or lower_bound >= upper_bound
                ):
                    invalid_groups.append(group_index)
                    continue

                group_definitions += (
                    f"pd.Interval({lower_bound}, {upper_bound}, closed='right'),\n"
                )
        elif self.var_type == VariableType.CATEGORICAL:
            for group_index, group_value in groups.items():
                if len(group_value) == 0:
                    invalid_groups.append(group_index)
                    continue

                if pd.api.types.is_numeric_dtype(self.variable.cat.categories.dtype):
                    categories = ", ".join(str(cat) for cat in sorted(group_value))
                else:
                    categories = ", ".join(f'"{cat}"' for cat in sorted(group_value))

                group_definitions += f"({categories},),\n"
        group_definitions = "[\n" + textwrap.indent(group_definitions, TAB) + "]"

        grid_definition = ""
        for index in risk_segment_grid.index:
            if index in invalid_groups:
                continue

            grid_definition += "["
            grid_definition += ", ".join(
                risk_segment_grid.loc[index].map(lambda v: f"$GROUP_INDEX_{v}")
            )
            grid_definition += "],\n"
        grid_definition = "[\n" + textwrap.indent(grid_definition, TAB) + "]"

        column_definition = (
            "["
            + ", ".join(risk_segment_grid.columns.map(lambda v: f"$GROUP_INDEX_{v}"))
            + "]"
        )

        code_template = f"iter_{self.uid}_grid = pd.DataFrame(\n"
        code_template += textwrap.indent(f"data={grid_definition},\n", TAB)
        code_template += textwrap.indent(f"columns={column_definition},\n", TAB)
        code_template += textwrap.indent(f"index={group_definitions},\n", TAB)

        code_template += ")\n\n"

        code_template += f'$DATA["$OUTPUT_VARIABLE_NAME"] = create_grid_mapped_variable($DATA["$VARIABLE_NAME"], $DATA["$PREV_ITER_OUT_NAME"], iter_{self.uid}_grid)\n'

        return Template(code_template)


class NumericalIteration(IterationBase):
    var_type = VariableType.NUMERICAL

    @staticmethod
    def _new_group_default_value_factory():
        return (np.nan, np.nan)

    @staticmethod
    def _create_initial_groups(variable, initial_group_count):
        quantiles = np.linspace(0, 1, initial_group_count + 1)
        percentiles = variable.quantile(quantiles)
        pairs = list(zip(percentiles.iloc[:-1], percentiles.iloc[1:]))

        pairs[0] = (pairs[0][0] - 1, pairs[0][1])

        return pd.Series(pairs, name=RangeColumn.GROUPS)

    def set_group(
        self,
        group_index: int,
        lower_bound: float | None = None,
        upper_bound: float | None = None,
        categories: set[str] | None = None,
    ):
        self._check_group_index(group_index)

        if lower_bound is not None and upper_bound is not None:
            self._groups[group_index] = (lower_bound, upper_bound)

    def _validate(self, default: bool) -> tuple[list[str], list[str], list]:
        invalid_groups = []
        warnings = []
        errors = []
        intervals = []

        mask = pd.Series(False, index=self.variable.index)
        groups = self.default_groups if default else self.groups

        for group_index, (lower_bound, upper_bound) in groups.items():
            missing_bound = False

            if lower_bound is None or np.isnan(lower_bound):
                warnings.append(
                    f"Invalid lower bound in group {group_index}: {lower_bound}"
                )
                invalid_groups.append(group_index)
                missing_bound = True

            if upper_bound is None or np.isnan(upper_bound):
                warnings.append(
                    f"Invalid upper bound in group {group_index}: {upper_bound}"
                )
                invalid_groups.append(group_index)
                missing_bound = True

            if not missing_bound and lower_bound >= upper_bound:
                warnings.append(
                    f"Invalid bounds in row {group_index}: "
                    f"lower bound ({lower_bound}) >= upper bound ({upper_bound})"
                )
                invalid_groups.append(group_index)

            if group_index not in invalid_groups:
                intervals.append((
                    group_index,
                    pd.Interval(lower_bound, upper_bound, closed="right"),
                ))
                mask |= (self.variable > lower_bound) & (self.variable <= upper_bound)

        lbs = pd.Series([i[1].left for i in intervals])
        ubs = pd.Series([i[1].right for i in intervals])

        intervals.sort(key=lambda t: t[1].left)

        overlaps = []
        for i in range(len(intervals) - 1):
            if intervals[i][1].overlaps(intervals[i + 1][1]):
                overlaps.append(
                    f"{intervals[i][0]}. {intervals[i][1]} "
                    f"and {intervals[i + 1][0]}. {intervals[i + 1][1]}"
                )

        if not lbs.is_monotonic_decreasing and not lbs.is_monotonic_increasing:
            warnings.append(
                "Lower bounds of the groups are not monotonic. "
                "This may lead to unexpected behavior."
            )

        if not ubs.is_monotonic_decreasing and not ubs.is_monotonic_increasing:
            warnings.append(
                "Upper bounds of the groups are not monotonic. "
                "This may lead to unexpected behavior."
            )

        if overlaps:
            errors.append(f"Following intervals overlap: {overlaps}")

        if not mask.all():
            warnings.append(
                f"Some values in the variable are not covered by any group: "
                f"{self.variable[~mask].drop_duplicates().sort_values().tolist()}"
            )

        warnings = [f"Iteration {self.uid}: {warning}" for warning in warnings]
        errors = [f"Iteration {self.uid}: {error}" for error in errors]

        return warnings, errors, invalid_groups

    def get_group_mapping(self, default: bool) -> IterationOutput:
        warnings, error, invalid_groups = self._validate(default=default)
        group_indices = pd.Series(
            index=self.variable.index, name=GridColumn.GROUP_INDEX
        )

        groups = self.default_groups if default else self.groups

        if not error:
            valid_groups = groups.drop(invalid_groups)

            for group_index, (lower_bound, upper_bound) in valid_groups.items():
                mask = (self.variable > lower_bound) & (self.variable <= upper_bound)
                group_indices.loc[mask] = group_index

        group_indices = group_indices.astype(
            pd.CategoricalDtype(categories=groups.index)
        )

        return IterationOutput(
            risk_segment_column=group_indices,
            errors=error,
            warnings=warnings,
            invalid_groups=invalid_groups,
        )

    def get_group_display(self):
        np.set_printoptions(legacy="1.25")
        return self.groups.map(
            lambda bounds: f"({float(bounds[0])} - {float(bounds[1])}]"
        )


class CategoricalIteration(IterationBase):
    var_type = VariableType.CATEGORICAL

    @staticmethod
    def _new_group_default_value_factory():
        return []

    @staticmethod
    def _create_initial_groups(variable, initial_group_count):
        unique_values = variable.cat.categories.tolist()
        groups = [set() for _ in range(initial_group_count)]

        while unique_values:
            for group in groups:
                group.add(unique_values.pop(0))
                if not unique_values:
                    break

        return pd.Series(groups, name=RangeColumn.GROUPS)

    def set_group(
        self,
        group_index: int,
        lower_bound: float | None = None,
        upper_bound: float | None = None,
        categories: set[str] | None = None,
    ):
        self._check_group_index(group_index)

        self._groups[group_index] = categories or set()

    def _validate(self, default: bool) -> tuple[list[str], list[str], list]:
        invalid_groups = []
        warnings = []
        errors = []

        all_categories = set(self.variable.cat.categories)
        assigned_categories = set()
        groups = self.default_groups if default else self.groups

        for group_index, category_list in groups.items():
            if not isinstance(category_list, set):
                warnings.append(
                    f"Group at index {group_index} is not a set: {category_list}"
                )
                invalid_groups.append(group_index)
                continue

            if not category_list:
                warnings.append(f"Group at index {group_index} is empty.")
                invalid_groups.append(group_index)
                continue

            possible_types = [type(self.variable.iloc[0])]

            if pd.api.types.is_integer_dtype(self.variable.cat.categories.dtype):
                possible_types.append(int)
            elif pd.api.types.is_float_dtype(self.variable.cat.categories.dtype):
                possible_types.append(float)
            elif pd.api.types.is_string_dtype(self.variable.cat.categories.dtype):
                possible_types.append(str)

            for category in category_list:
                if not isinstance(category, tuple(possible_types)):
                    warnings.append(
                        f"Invalid type {type(category)} for category {category} "
                        f"in group at index {group_index}. Expected type: {', '.join(map(str, possible_types))}."
                    )
                    invalid_groups.append(group_index)

                if category not in all_categories:
                    warnings.append(
                        f"Category '{category}' in group at index {group_index} "
                        "is not in the variable's unique values."
                    )
                    invalid_groups.append(group_index)

                if category in assigned_categories:
                    errors.append(
                        f"Category '{category}' is assigned to multiple groups."
                    )

                assigned_categories.add(category)

        if len(all_categories - assigned_categories) > 0:
            warnings.append(
                f"The following categories are not assigned to any group: "
                f"{', '.join(all_categories - assigned_categories)}"
            )

        warnings = [f"Iteration {self.uid}: {warning}" for warning in warnings]
        errors = [f"Iteration {self.uid}: {error}" for error in errors]

        return warnings, errors, invalid_groups

    def get_group_mapping(self, default: bool) -> IterationOutput:
        warnings, error, invalid_groups = self._validate(default=default)
        group_indices = pd.Series(
            index=self.variable.index, name=GridColumn.GROUP_INDEX
        )

        groups = self.default_groups if default else self.groups

        if not error:
            valid_groups = groups.drop(invalid_groups)

            for group_index, category_list in valid_groups.items():
                mask = self.variable.isin(category_list)
                group_indices.loc[mask] = group_index

        group_indices = group_indices.astype(
            pd.CategoricalDtype(categories=groups.index),
        )

        return IterationOutput(
            risk_segment_column=group_indices,
            errors=error,
            warnings=warnings,
            invalid_groups=invalid_groups,
        )

    def get_group_display(self):
        return self.groups.map(lambda categories: ", ".join(categories))


class NumericalSingleVarIteration(NumericalIteration, SingleVarIteration):
    def __init__(
        self,
        uid: IterationID,
        name: str,
        variable: pd.Series,
        risk_segment_details: pd.DataFrame,
    ):
        super().__init__(
            uid=uid,
            name=name,
            variable=variable,
            risk_segment_details=risk_segment_details,
        )


class CategoricalSingleVarIteration(CategoricalIteration, SingleVarIteration):
    def __init__(
        self,
        uid: IterationID,
        name: str,
        variable: pd.Series,
        risk_segment_details: pd.DataFrame,
    ):
        super().__init__(
            uid=uid,
            name=name,
            variable=variable,
            risk_segment_details=risk_segment_details,
        )


class NumericalDoubleVarIteration(NumericalIteration, DoubleVarIteration):
    def __init__(
        self,
        uid: IterationID,
        name: str,
        variable: pd.Series,
        risk_segment_details: pd.DataFrame,
    ):
        super().__init__(
            uid=uid,
            name=name,
            variable=variable,
            risk_segment_details=risk_segment_details,
        )


class CategoricalDoubleVarIteration(CategoricalIteration, DoubleVarIteration):
    def __init__(
        self,
        uid: IterationID,
        name: str,
        variable: pd.Series,
        risk_segment_details: pd.DataFrame,
    ):
        super().__init__(
            uid=uid,
            name=name,
            variable=variable,
            risk_segment_details=risk_segment_details,
        )


Iteration = (
    NumericalSingleVarIteration
    | NumericalDoubleVarIteration
    | CategoricalSingleVarIteration
    | CategoricalDoubleVarIteration
)


def from_dict(dict_data: IterationJSON, variable: pd.Series) -> Iteration:
    """Creates an IterationBase object from a dictionary."""

    iter_type = dict_data.iter_type
    var_type = dict_data.var_type

    class_map = {
        (IterationType.SINGLE, VariableType.NUMERICAL): NumericalSingleVarIteration,
        (IterationType.SINGLE, VariableType.CATEGORICAL): CategoricalSingleVarIteration,
        (IterationType.DOUBLE, VariableType.NUMERICAL): NumericalDoubleVarIteration,
        (IterationType.DOUBLE, VariableType.CATEGORICAL): CategoricalDoubleVarIteration,
    }

    cls = class_map[(iter_type, var_type)]

    instance: IterationBase = cls(
        uid=dict_data.uid,
        name=dict_data.name,
        variable=variable,
        risk_segment_details=DefaultOptions().risk_segment_details,
    )

    map_func = tuple if var_type == VariableType.NUMERICAL else set

    # groups
    groups = pd.Series(dict_data.groups, name=RangeColumn.GROUPS).map(map_func)
    groups.index = groups.index.astype(int)

    # default groups
    default_groups = pd.Series(dict_data.default_groups, name=RangeColumn.GROUPS).map(
        map_func
    )
    default_groups.index = default_groups.index.astype(int)

    instance._groups = groups
    instance._default_groups = default_groups

    # risk segment details
    if (
        isinstance(
            instance, (NumericalSingleVarIteration, CategoricalSingleVarIteration)
        )
        and dict_data.risk_segment_details is not None
    ):
        instance._risk_segment_details = pd.DataFrame.from_dict(
            dict_data.risk_segment_details.model_dump(), orient="tight"
        )
        instance._risk_segment_details[RSDetCol.UPPER_RATE] = (
            instance._risk_segment_details[RSDetCol.UPPER_RATE].fillna(np.inf)
        )

    # groups mask
    if not isinstance(
        instance, (NumericalSingleVarIteration, CategoricalSingleVarIteration)
    ):
        instance._groups_mask = pd.Series(
            dict_data.groups_mask, name=GridColumn.GROUP_INDEX
        )

    # risk segment grid
    if (
        not isinstance(
            instance, (NumericalSingleVarIteration, CategoricalSingleVarIteration)
        )
        and dict_data.risk_segment_grid is not None
    ):
        instance._risk_segment_grid = pd.DataFrame.from_dict(
            dict_data.risk_segment_grid.model_dump(), orient="tight"
        )

    # default risk segment grid
    if (
        not isinstance(
            instance, (NumericalSingleVarIteration, CategoricalSingleVarIteration)
        )
        and dict_data.default_risk_segment_grid is not None
    ):
        instance._default_risk_segment_grid = pd.DataFrame.from_dict(
            dict_data.default_risk_segment_grid.model_dump(), orient="tight"
        )

    return instance


__all__ = [
    "IterationOutput",
    "NumericalSingleVarIteration",
    "NumericalDoubleVarIteration",
    "CategoricalSingleVarIteration",
    "CategoricalDoubleVarIteration",
]
