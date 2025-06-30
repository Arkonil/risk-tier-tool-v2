from abc import ABC, abstractmethod
import typing as t

import numpy as np
import pandas as pd

from classes.constants import (
    DefaultOptions,
    GridColumn,
    IterationType,
    LossRateTypes,
    RTDetCol,
    RangeColumn,
    VariableType,
)
from classes.data import Data


class IterationOutput(t.TypedDict):
    risk_tier_column: pd.Series
    errors: list[str]
    warnings: list[str]
    invalid_groups: list[int]


class IterationBase(ABC):
    var_type: VariableType = None
    iter_type: IterationType = None

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
        self, _id: str, name: str, variable: pd.Series, initial_group_count: int
    ):
        self._id = _id
        self._name = name
        self._variable = variable
        self._groups = self._create_initial_groups(variable, initial_group_count)
        self._default_groups = self._groups.copy()

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def variable(self) -> pd.Series:
        return self._variable

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
    def get_risk_tiers(
        self, previous_risk_tiers: pd.Series | None, default: bool
    ) -> IterationOutput:
        raise NotImplementedError()

    @abstractmethod
    def set_group(self, group_index: int, *args, **kwargs):
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

    def to_dict(self) -> dict[str, t.Any]:
        """Serializes the IterationBase object to a dictionary."""
        return {
            "var_type": self.var_type.value,
            "iter_type": self.iter_type.value,
            "id": self._id,
            "name": self._name,
            "variable_name": self._variable.name,
            "groups": self._groups.to_dict(),
            "default_groups": self._default_groups.to_dict(),
        }


class SingleVarIteration(IterationBase):
    iter_type = IterationType.SINGLE

    def __init__(self, risk_tier_details: pd.DataFrame, **kwargs):
        super().__init__(**kwargs, initial_group_count=len(risk_tier_details))

        self._risk_tier_details = risk_tier_details

    @t.override
    @property
    def groups(self) -> pd.Series:
        return self._groups

    @property
    def risk_tier_details(self) -> pd.DataFrame:
        return self._risk_tier_details

    def update_maf(self, loss_rate_type: LossRateTypes, maf: pd.Series):
        if len(maf) != len(self._risk_tier_details):
            raise ValueError(f"Invalid maf length: {len(maf)}")

        if loss_rate_type == LossRateTypes.DLR:
            self._risk_tier_details[RTDetCol.MAF_DLR] = maf.to_list()
        elif loss_rate_type == LossRateTypes.ULR:
            self._risk_tier_details[RTDetCol.MAF_ULR] = maf.to_list()
        else:
            raise ValueError(f"Invalid loss rate type: {loss_rate_type}")

    @t.override
    def get_risk_tiers(
        self, previous_risk_tiers: pd.Series | None, default: bool
    ) -> IterationOutput:
        output = self.get_group_mapping(default=default)

        output["risk_tier_column"] = output["risk_tier_column"].astype(
            pd.CategoricalDtype(categories=self.risk_tier_details.index)
        )

        return output

    def to_dict(self):
        dict_data = super().to_dict()

        risk_tier_details_data = self._risk_tier_details.to_dict(orient="tight")

        dict_data.update({
            "risk_tier_details": risk_tier_details_data,
        })

        return dict_data


class DoubleVarIteration(IterationBase):
    iter_type = IterationType.DOUBLE

    def __init__(self, risk_tier_details: pd.DataFrame, **kwargs):
        initial_group_count = 10

        super().__init__(**kwargs, initial_group_count=initial_group_count)

        prev_rt_count = len(risk_tier_details)

        self._groups_mask = pd.Series(True, index=self._groups.index)
        self._risk_tier_grid = pd.DataFrame(
            np.repeat(
                np.arange(prev_rt_count).reshape(1, prev_rt_count),
                repeats=len(self._groups),
                axis=0,
            )
        )
        self._default_risk_tier_grid = self._risk_tier_grid.copy()

    @t.override
    @property
    def groups(self) -> pd.Series:
        return self._groups.loc[self._groups_mask]

    @property
    def risk_tier_grid(self) -> pd.DataFrame:
        return self._risk_tier_grid.loc[self._groups_mask, :]

    @property
    def default_risk_tier_grid(self) -> pd.DataFrame:
        return self._default_risk_tier_grid

    def add_group(self, group_index: int | None = None):
        if group_index is None:
            group_index = len(self._groups)

        if group_index < 0:
            raise ValueError(f"Invalid argument for 'group_index': {group_index}")

        num_groups = len(self._groups)

        if group_index >= num_groups:
            self._groups.loc[num_groups] = self._new_group_default_value_factory()

        self._groups_mask.loc[min(group_index, num_groups)] = True

        if len(self._risk_tier_grid) == len(self._groups):
            return

        last_row = self._risk_tier_grid.iloc[[-1]].copy()
        self._risk_tier_grid = pd.concat(
            [self._risk_tier_grid, last_row], ignore_index=True
        )

    @t.override
    def set_default_groups(self, default_groups: pd.Series):
        super().set_default_groups(default_groups)
        self._groups_mask = pd.Series(True, index=self._groups.index)

    def set_default_risk_tier_grid(self, default_risk_tier_grid: pd.DataFrame):
        self._default_risk_tier_grid = default_risk_tier_grid.copy()
        self._risk_tier_grid = default_risk_tier_grid.copy()

    def set_risk_tier_grid(self, group_index: int, previous_rt_index: int, value: int):
        self._check_group_index(group_index)

        if previous_rt_index not in self.risk_tier_grid.columns:
            raise ValueError(
                f"Invalid value for risk tier provided: {previous_rt_index}"
            )

        self._risk_tier_grid.loc[group_index, previous_rt_index] = value

    def remove_group(self, group_index: int):
        self._check_group_index(group_index)

        if self._groups_mask.drop(group_index).any():
            self._groups_mask.iloc[group_index] = False
        else:
            raise ValueError("Can not remove the last group.")

    @t.override
    def get_risk_tiers(
        self, previous_risk_tiers: pd.Series | None, default: bool
    ) -> IterationOutput:
        iteration_output = self.get_group_mapping(default=default)
        risk_tier_column = pd.Series(index=self.variable.index)

        if not iteration_output["errors"]:
            risk_tier_grid = (
                self.default_risk_tier_grid if default else self.risk_tier_grid
            )

            for prev_rt in risk_tier_grid.columns:
                for curr_rt in risk_tier_grid.index:
                    mask = (previous_risk_tiers == prev_rt) & (
                        iteration_output["risk_tier_column"] == curr_rt
                    )

                    risk_tier_column.loc[mask] = risk_tier_grid.loc[curr_rt, prev_rt]

        risk_tier_column = risk_tier_column.astype(
            pd.CategoricalDtype(categories=self.risk_tier_grid.columns)
        )

        iteration_output.update({"risk_tier_column": risk_tier_column})

        return iteration_output

    def to_dict(self):
        dict_data = super().to_dict()

        groups_mask_data = self._groups_mask.to_dict()
        risk_tier_grid_data = self._risk_tier_grid.to_dict(orient="tight")
        default_risk_tier_grid_data = self._default_risk_tier_grid.to_dict(
            orient="tight"
        )

        dict_data.update({
            "groups_mask": groups_mask_data,
            "risk_tier_grid": risk_tier_grid_data,
            "default_risk_tier_grid": default_risk_tier_grid_data,
        })

        return dict_data


class NumericalIteration(IterationBase):
    var_type = VariableType.NUMERICAL

    @t.override
    @staticmethod
    def _new_group_default_value_factory():
        return (np.nan, np.nan)

    @t.override
    @staticmethod
    def _create_initial_groups(variable, initial_group_count):
        quantiles = np.linspace(0, 1, initial_group_count + 1)
        percentiles = variable.quantile(quantiles)
        pairs = list(zip(percentiles.iloc[:-1], percentiles.iloc[1:]))

        pairs[0] = (pairs[0][0] - 1, pairs[0][1])

        return pd.Series(pairs, name=RangeColumn.GROUPS)

    @t.override
    def set_group(self, group_index: int, lower_bound: float, upper_bound: float):
        self._check_group_index(group_index)

        self._groups.loc[group_index] = (lower_bound, upper_bound)

    @t.override
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

        lbs = pd.Series(map(lambda i: i[1].left, intervals))
        ubs = pd.Series(map(lambda i: i[1].right, intervals))
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

        warnings = [f"Iteration {self.id}: {warning}" for warning in warnings]
        errors = [f"Iteration {self.id}: {error}" for error in errors]

        return warnings, errors, invalid_groups

    @t.override
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

        return {
            "risk_tier_column": group_indices,
            "errors": error,
            "warnings": warnings,
            "invalid_groups": invalid_groups,
        }


class CategoricalIteration(IterationBase):
    var_type = VariableType.CATEGORICAL

    @t.override
    @staticmethod
    def _new_group_default_value_factory():
        return []

    @t.override
    @staticmethod
    def _create_initial_groups(variable, initial_group_count):
        unique_values = list(sorted(list(variable.unique())))
        groups = [set() for _ in range(initial_group_count)]

        while unique_values:
            for group in groups:
                group.add(unique_values.pop(0))
                if not unique_values:
                    break

        return pd.Series(groups, name=RangeColumn.GROUPS)

    @t.override
    def set_group(self, group_index: int, categories: t.Iterable[str]):
        self._check_group_index(group_index)

        self._groups.loc[group_index] = set(categories)

    @t.override
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

            for category in category_list:
                if not isinstance(category, type(self.variable.iloc[0])):
                    warnings.append(
                        f"Invalid type {type(category)} for category {category} "
                        f"in group at index {group_index}. Expected type: {type(self.variable.iloc[0])}"
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

        warnings = [f"Iteration {self.id}: {warning}" for warning in warnings]
        errors = [f"Iteration {self.id}: {error}" for error in errors]

        return warnings, errors, invalid_groups

    @t.override
    def get_group_mapping(self, default: bool) -> IterationOutput:
        warnings, error, invalid_groups = self._validate(default=default)
        group_indices = pd.Series(index=self.variable.index)

        groups = self.default_groups if default else self.groups

        if not error:
            valid_groups = groups.drop(invalid_groups)

            for group_index, category_list in valid_groups.items():
                mask = self.variable.isin(category_list)
                group_indices.loc[mask] = group_index

        return {
            "risk_tier_column": group_indices,
            "errors": error,
            "warnings": warnings,
            "invalid_groups": invalid_groups,
        }


class NumericalSingleVarIteration(NumericalIteration, SingleVarIteration):
    def __init__(
        self, _id: str, name: str, variable: pd.Series, risk_tier_details: pd.DataFrame
    ):
        super().__init__(
            _id=_id, name=name, variable=variable, risk_tier_details=risk_tier_details
        )

    @classmethod
    def from_dict(
        dict_data: dict[str, t.Any], data: Data
    ) -> "NumericalSingleVarIteration":
        """Creates a NumericalSingleVarIteration object from a dictionary."""

        _id = dict_data["id"]
        name = dict_data["name"]
        variable = data.load_column(
            dict_data["variable_name"], VariableType(dict_data["variable_type"])
        )
        rt_df = pd.DataFrame.from_dict(dict_data["risk_tier_details"], orient="tight")

        return NumericalSingleVarIteration(
            _id=_id,
            name=name,
            variable=variable,
            risk_tier_details=rt_df,
        )


class CategoricalSingleVarIteration(CategoricalIteration, SingleVarIteration):
    def __init__(
        self, _id: str, name: str, variable: pd.Series, risk_tier_details: pd.DataFrame
    ):
        super().__init__(
            _id=_id, name=name, variable=variable, risk_tier_details=risk_tier_details
        )


class NumericalDoubleVarIteration(NumericalIteration, DoubleVarIteration):
    def __init__(
        self, _id: str, name: str, variable: pd.Series, risk_tier_details: pd.DataFrame
    ):
        super().__init__(
            _id=_id, name=name, variable=variable, risk_tier_details=risk_tier_details
        )


class CategoricalDoubleVarIteration(CategoricalIteration, DoubleVarIteration):
    def __init__(
        self, _id: str, name: str, variable: pd.Series, risk_tier_details: pd.DataFrame
    ):
        super().__init__(
            _id=_id, name=name, variable=variable, risk_tier_details=risk_tier_details
        )


def from_dict(dict_data: dict[str, t.Any], data: Data) -> IterationBase:
    """Creates an IterationBase object from a dictionary."""
    try:
        iter_type = IterationType(dict_data.get("iter_type"))
    except ValueError:
        raise ValueError(f"Unsupported iteration type: {dict_data.get('iter_type')}")

    try:
        var_type = VariableType(dict_data.get("var_type"))
    except ValueError:
        raise ValueError(f"Unsupported variable type: {dict_data.get('var_type')}")

    class_map = {
        (IterationType.SINGLE, VariableType.NUMERICAL): NumericalSingleVarIteration,
        (IterationType.SINGLE, VariableType.CATEGORICAL): CategoricalSingleVarIteration,
        (IterationType.DOUBLE, VariableType.NUMERICAL): NumericalDoubleVarIteration,
        (IterationType.DOUBLE, VariableType.CATEGORICAL): CategoricalDoubleVarIteration,
    }

    cls = class_map.get((iter_type, var_type))

    _id = dict_data.get("id")
    name = dict_data.get("name")
    variable_name = dict_data.get("variable_name")
    variable = data.df[variable_name]

    instance: IterationBase = cls(
        _id=_id,
        name=name,
        variable=variable,
        risk_tier_details=DefaultOptions().risk_tier_details,
    )

    map_func = tuple if var_type == VariableType.NUMERICAL else set

    groups = pd.Series(dict_data.get("groups", {}), name=RangeColumn.GROUPS).map(
        map_func
    )
    groups.index = groups.index.astype(int)

    default_groups = pd.Series(
        dict_data.get("default_groups", {}), name=RangeColumn.GROUPS
    ).map(map_func)
    default_groups.index = default_groups.index.astype(int)

    instance._groups = groups
    instance._default_groups = default_groups

    if iter_type == IterationType.SINGLE:
        risk_tier_details = pd.DataFrame.from_dict(
            dict_data.get("risk_tier_details", {}), orient="tight"
        )
        instance._risk_tier_details = risk_tier_details
    else:
        instance._groups_mask = pd.Series(dict_data.get("groups_mask", {}))
        instance._groups_mask.index = instance._groups_mask.index.astype(int)
        instance._risk_tier_grid = pd.DataFrame.from_dict(
            dict_data.get("risk_tier_grid", {}), orient="tight"
        )
        instance._default_risk_tier_grid = pd.DataFrame.from_dict(
            dict_data.get("default_risk_tier_grid", {}), orient="tight"
        )

    return instance


__all__ = [
    "IterationOutput",
    "NumericalSingleVarIteration",
    "NumericalDoubleVarIteration",
    "CategoricalSingleVarIteration",
    "CategoricalDoubleVarIteration",
]
