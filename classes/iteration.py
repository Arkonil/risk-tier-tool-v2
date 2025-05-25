from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


MAX_SINGLE_VAR_GROUP_COUNT = 10


class IterationBase(ABC):
    @staticmethod
    def _new_group_default_value_factory() -> None:
        return None

    def __init__(self, _id, name: str, variable: pd.Series, initial_group_count: int) -> None:
        super().__init__()

        self.id = _id
        self.name = name
        self._variable = variable
        self._groups = pd.Series()

        self._create_initial_groups(initial_group_count)
        self._group_mask = pd.Series(True, index=self._groups.index)

    @property
    def variable(self) -> pd.Series:
        if self._variable is None:
            raise ValueError("The variable is not loaded from the data.")

        return self._variable

    @property
    def groups(self) -> pd.Series:
        return self._groups.loc[self._group_mask]

    @property
    def num_groups(self) -> int:
        return len(self._groups)

    def _check_group_index(self, group_index: int) -> None:
        if group_index < 0 or group_index >= self.num_groups:
            raise ValueError(f"Value of colidx out of range [0, {self.num_groups - 1}]. "
                             f"Provided value: {group_index}")

    def add_group(self, group_index: int) -> None:
        if group_index < 0:
            raise ValueError(f"Invalid argument for 'group_index': {group_index}")

        if group_index >= self.num_groups:
            self._groups.loc[self.num_groups] = self._new_group_default_value_factory()

        self._group_mask.iloc[min(group_index, self.num_groups)] = True

    def remove_group(self, group_index: int) -> None:
        self._check_group_index(group_index)

        if self._group_mask.drop(group_index).any():
            self._group_mask.iloc[group_index] = False
        else:
            raise ValueError("Can not remove the last group.")

    @abstractmethod
    def _create_initial_groups(self, initial_group_count: int):
        raise NotImplementedError()

    @abstractmethod
    def _validate(self) -> tuple[list[str], list[str], list]:
        raise NotImplementedError()

    @abstractmethod
    def set_group(self, group_index: int, *args, **kwargs) -> None:
        raise NotImplementedError()

    @abstractmethod
    def get_risk_tiers(self, previous_risk_tiers: pd.Series = None) -> tuple[pd.Series, list[str], list[str], list]:
        raise NotImplementedError()

class SingleVarIteration(IterationBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_group(self, group_index: int) -> None:
        if group_index >= MAX_SINGLE_VAR_GROUP_COUNT:
            raise ValueError(f"Can not add more than {MAX_SINGLE_VAR_GROUP_COUNT} groups.")

        return super().add_group(group_index)

class DoubleVarIteration(IterationBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._risk_tier_grid = pd.DataFrame(np.repeat(np.arange(10).reshape(1, 10), self.num_groups, axis=0))
        
    @property
    def risk_tier_grid(self) -> pd.DataFrame:
        return self._risk_tier_grid.loc[self._group_mask, :]

    def set_risk_tier_grid(self, group_index: int, previous_iteration_rt, value) -> None:
        self._check_group_index(group_index)

        if previous_iteration_rt not in self.risk_tier_grid.columns:
            raise ValueError(f"Invalid value for risk tier provided: {previous_iteration_rt}")

        self._risk_tier_grid.loc[group_index, previous_iteration_rt] = value

    def add_group(self, group_index):
        super().add_group(group_index)

        if len(self._risk_tier_grid) == len(self._groups):
            return

        last_row = self._risk_tier_grid.iloc[[-1]]
        self._risk_tier_grid = pd.concat([self._risk_tier_grid, last_row], ignore_index=True)

class NumericalIteration(IterationBase):
    @staticmethod
    def _new_group_default_value_factory():
        return (np.nan, np.nan)

    def __init__(self, _id, name, variable, initial_group_count):
        super().__init__(_id, name, variable, initial_group_count)

    def _create_initial_groups(self, initial_group_count: int):
        quantiles = np.linspace(0, 1, initial_group_count + 1)
        percentiles = self.variable.quantile(quantiles)
        pairs = list(zip(percentiles.iloc[:-1], percentiles.iloc[1:]))

        self._groups = pd.Series(pairs, name=self.variable.name)

    def _validate(self) -> tuple[list[str], list[str], list]:
        groups = self._groups.loc[self._group_mask]

        invalid_groups = []
        warnings = []
        errors = []
        intervals = []

        for group_index, (lower_bound, upper_bound) in groups.items():
            missing_bound = False

            if lower_bound is None or np.isnan(lower_bound):
                warnings.append(f"Invalid lower bound in group {group_index}: {lower_bound}")
                invalid_groups.append(group_index)
                missing_bound = True

            if upper_bound is None or np.isnan(upper_bound):
                warnings.append(f"Invalid upper bound in group {group_index}: {upper_bound}")
                invalid_groups.append(group_index)
                missing_bound = True

            if not missing_bound and lower_bound >= upper_bound:
                warnings.append(f"Invalid bounds in row {group_index}: "
                                f"lower bound ({lower_bound}) >= upper bound ({upper_bound})")
                invalid_groups.append(group_index)

            if group_index not in invalid_groups:
                intervals.append((group_index, pd.Interval(lower_bound, upper_bound, closed='right')))

        intervals.sort(key=lambda t: t[1].left)

        overlaps = []
        for i in range(len(intervals) - 1):
            if intervals[i][1].overlaps(intervals[i + 1][1]):
                overlaps.append(f"{intervals[i][0]}. {intervals[i][1]} "
                                f"and {intervals[i + 1][0]}. {intervals[i + 1][1]}")

        if overlaps:
            errors.append(f"Following intervals overlap: {overlaps}")

        return warnings, errors, invalid_groups

    # pylint: disable=arguments-differ
    def set_group(self, group_index: int, lower_bound: float, upper_bound: float) -> None:
        self._check_group_index(group_index)

        self._groups.loc[group_index] = (lower_bound, upper_bound)
    # pylint: enable=arguments-differ
    
    def get_group_mapping(self) -> tuple[pd.Series, list[str], list[str], list]:
        groups = self.groups
        
        warnings, error, invalid_groups = self._validate()
        group_indices = pd.Series(index=self.variable.index)
        
        if error:
            return group_indices, error, warnings, invalid_groups
        
        valid_groups = groups.drop(invalid_groups)
        
        for group_index, (lower_bound, upper_bound) in valid_groups.items():
            mask = (self.variable > lower_bound) & (self.variable <= upper_bound)
            group_indices.loc[mask] = group_index
        
        return group_indices, error, warnings, invalid_groups


class CategoricalIteration(IterationBase):
    @staticmethod
    def _new_group_default_value_factory():
        return []

    def __init__(self, _id, name, variable, initial_group_count):
        super().__init__(_id, name, variable, initial_group_count)

    def _create_initial_groups(self, initial_group_count: int):
        unique_values = list(sorted(list(self.variable.unique())))
        groups = [set() for _ in range(initial_group_count)]

        while unique_values:
            for group in groups:
                group.add(unique_values.pop(0))
                if not unique_values:
                    break

        self._groups = pd.Series(groups, name=self.variable.name)

    def _validate(self) -> tuple[list[str], list[str], list]:
        groups = self._groups.loc[self._group_mask]

        invalid_groups = []
        warnings = []
        errors = []

        all_categories = set(self.variable.cat.categories)
        assigned_categories = set()

        for group_index, category_list in groups.items():
            if not isinstance(category_list, set):
                warnings.append(f"Group at index {group_index} is not a set: {category_list}")
                invalid_groups.append(group_index)
                continue

            if not category_list:
                warnings.append(f"Group at index {group_index} is empty.")
                invalid_groups.append(group_index)
                continue

            for category in category_list:
                if not isinstance(category, type(self.variable.iloc[0])):
                    warnings.append(f"Invalid type {type(category)} for category {category} "
                                    f"in group at index {group_index}")
                    invalid_groups.append(group_index)

                if category not in all_categories:
                    warnings.append(f"Category '{category}' in group at index {group_index} "
                                    "is not in the variable's unique values.")
                    invalid_groups.append(group_index)

                if category in assigned_categories:
                    errors.append(f"Category '{category}' is assigned to multiple groups.")

                assigned_categories.add(category)

        if len(all_categories - assigned_categories) > 0:
            warnings.append(f"The following categories are not assigned to any group: "
                            f"{', '.join(all_categories - assigned_categories)}")

        return warnings, errors, invalid_groups

    # pylint: disable=arguments-differ
    def set_group(self, group_index: int, categories: set[str]) -> None:
        self._check_group_index(group_index)

        self._groups.loc[group_index] = categories
    # pylint: enable=arguments-differ
    
    def get_group_mapping(self) -> tuple[pd.Series, list[str], list[str], list]:
        groups = self.groups
        
        warnings, error, invalid_groups = self._validate()
        group_indices = pd.Series(index=self.variable.index)
        
        if error:
            return group_indices, error, warnings, invalid_groups
        
        valid_groups = groups.drop(invalid_groups)
        
        for group_index, category_list in valid_groups.items():
            mask = self.variable.isin(category_list)
            group_indices.loc[mask] = group_index
        
        return group_indices, error, warnings, invalid_groups


class NumericalSingleVarIteration(NumericalIteration, SingleVarIteration):
    def __init__(self, _id, name, variable, initial_group_count):
        super().__init__(_id, name, variable, initial_group_count)

    def get_risk_tiers(self, previous_risk_tiers: pd.Series = None) -> tuple[pd.Series, list[str], list[str], list]:
        return self.get_group_mapping()

class CategoricalSingleVarIteration(CategoricalIteration, SingleVarIteration):

    def __init__(self, _id, name, variable, initial_group_count):
        super().__init__(_id, name, variable, initial_group_count)

    def get_risk_tiers(self, previous_risk_tiers: pd.Series = None) -> tuple[pd.Series, list[str], list[str], list]:
        return self.get_group_mapping()

class NumericalDoubleVarIteration(NumericalIteration, DoubleVarIteration):
    def __init__(self, _id, name, variable, initial_group_count):
        super().__init__(_id, name, variable, initial_group_count)

    def get_risk_tiers(self, previous_risk_tiers: pd.Series = None) -> tuple[pd.Series, list[str], list[str], list]:
        group_indices, error, warnings, invalid_groups = self.get_group_mapping()
        # groups = self.groups

        # warnings, error, invalid_groups = self._validate()
        risk_tier_column = pd.Series(index=self.variable.index)

        if error:
            return risk_tier_column, error, warnings, invalid_groups

        # valid_groups = groups.drop(invalid_groups)
        risk_tier_grid = self.risk_tier_grid

        for prev_rt in risk_tier_grid.columns:
            for curr_rt in risk_tier_grid.index:
                mask = (previous_risk_tiers == prev_rt) & (group_indices == curr_rt)
                
                risk_tier_column.loc[mask] = risk_tier_grid.loc[curr_rt, prev_rt]

        # for prev_rt in risk_tier_grid.columns:
        #     for group_index, (lower_bound, upper_bound) in valid_groups.items():
        #         mask = previous_risk_tiers == prev_rt
        #         mask &= (self.variable > lower_bound)
        #         mask &= (self.variable <= upper_bound)
        #         risk_tier_column.loc[mask] = risk_tier_grid.loc[group_index, prev_rt]

        return risk_tier_column, error, warnings, invalid_groups

class CategoricalDoubleVarIteration(CategoricalIteration, DoubleVarIteration):
    def __init__(self, _id, name, variable, initial_group_count):
        super().__init__(_id, name, variable, initial_group_count)

    def get_risk_tiers(self, previous_risk_tiers: pd.Series = None) -> tuple[pd.Series, list[str], list[str], list]:
        group_indices, error, warnings, invalid_groups = self.get_group_mapping()
        # groups = self.groups

        # warnings, error, invalid_groups = self._validate()
        risk_tier_column = pd.Series(index=self.variable.index)

        if error:
            return risk_tier_column, error, warnings, invalid_groups

        # valid_groups = groups.drop(invalid_groups)
        risk_tier_grid = self.risk_tier_grid

        for prev_rt in risk_tier_grid.columns:
            for curr_rt in risk_tier_grid.index:
                mask = (previous_risk_tiers == prev_rt) & (group_indices == curr_rt)
                
                risk_tier_column.loc[mask] = risk_tier_grid.loc[curr_rt, prev_rt]
        # for prev_rt in risk_tier_grid.columns:
        #     for group_index, category_list in valid_groups.items():
        #         mask = previous_risk_tiers == prev_rt
        #         mask &= self.variable.isin(category_list)
        #         risk_tier_column.loc[mask] = risk_tier_grid.loc[group_index, prev_rt]

        return risk_tier_column, error, warnings, invalid_groups


__all__ = [
    'IterationBase',
    'SingleVarIteration',
    'DoubleVarIteration',
    'NumericalIteration',
    'NumericalSingleVarIteration',
    'NumericalDoubleVarIteration',
    'CategoricalIteration',
    'CategoricalSingleVarIteration',
    'CategoricalDoubleVarIteration',
]
