from abc import ABC, abstractmethod
import typing as t

import numpy as np
import pandas as pd

from classes.constants import (
    GridColumn,
    IterationType,
    LossRateTypes,
    RTDetCol,
    RangeColumn,
    VariableType,
)


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
        self, previous_risk_tiers: pd.Series = None, default: bool = False
    ) -> IterationOutput:
        raise NotImplementedError()

    @abstractmethod
    def set_group(self, group_index: int, *args, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def _validate(self, default: bool = False) -> tuple[list[str], list[str], list]:
        raise NotImplementedError()

    @abstractmethod
    def get_group_mapping(self, default: bool = False) -> IterationOutput:
        raise NotImplementedError()

    def _check_group_index(self, group_index: int) -> None:
        num_groups = len(self._groups)

        if group_index < 0 or group_index >= num_groups:
            raise ValueError(
                f"Value of colidx out of range [0, {num_groups - 1}]. "
                f"Provided value: {group_index}"
            )


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
        self, previous_risk_tiers: pd.Series = None, default: bool = False
    ) -> IterationOutput:
        output = self.get_group_mapping(default=default)

        output["risk_tier_column"] = output["risk_tier_column"].astype(
            pd.CategoricalDtype(categories=self.risk_tier_details.index)
        )

        return output


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
        self.default_risk_tier_grid = self._risk_tier_grid.copy()

    @t.override
    @property
    def groups(self) -> pd.Series:
        return self._groups.loc[self._groups_mask]

    @property
    def risk_tier_grid(self) -> pd.DataFrame:
        return self._risk_tier_grid.loc[self._groups_mask, :]

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
        self.default_risk_tier_grid = default_risk_tier_grid.copy()
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
        self, previous_risk_tiers: pd.Series = None, default: bool = False
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
    def _validate(self, default: bool = False) -> tuple[list[str], list[str], list]:
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

        intervals.sort(key=lambda t: t[1].left)

        overlaps = []
        for i in range(len(intervals) - 1):
            if intervals[i][1].overlaps(intervals[i + 1][1]):
                overlaps.append(
                    f"{intervals[i][0]}. {intervals[i][1]} "
                    f"and {intervals[i + 1][0]}. {intervals[i + 1][1]}"
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
    def get_group_mapping(self, default: bool = False) -> IterationOutput:
        warnings, error, invalid_groups = self._validate()
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

        self._groups.loc[group_index] = list(sorted(categories))

    @t.override
    def _validate(self, default: bool = False) -> tuple[list[str], list[str], list]:
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
    def get_group_mapping(self, default: bool = False) -> IterationOutput:
        warnings, error, invalid_groups = self._validate()
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


__all__ = [
    "IterationOutput",
    "NumericalSingleVarIteration",
    "NumericalDoubleVarIteration",
    "CategoricalSingleVarIteration",
    "CategoricalDoubleVarIteration",
]
