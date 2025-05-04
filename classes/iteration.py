from abc import ABC

import numpy as np
import pandas as pd


class IterationBase(ABC):
    RISK_TIERS = list(map(str, range(1, 6)))
    SUB_RISK_TIERS = list(sorted(
        [f'{rt}A' for rt in RISK_TIERS] + [f'{rt}B' for rt in RISK_TIERS], reverse=True))

    def __init__(self, id: str, variable: pd.Series = None) -> None:
        self.id = id
        self._variable = variable
        self._ranges = pd.DataFrame(
            columns=['lower_bound', 'upper_bound'], index=range(len(self.SUB_RISK_TIERS)))

    @property
    def num_ranges(self) -> int:
        return len(self._ranges)

    @property
    def variable(self) -> pd.Series:
        if self._variable is None:
            raise ValueError(f"The variable is not loaded from the data.")

        return self._variable
        
    def set_variable(self, variable: pd.Series) -> None:
        self._variable = variable

    def _check_rngidx(self, rngidx: int) -> None:
        if rngidx < 0 or rngidx >= self.num_ranges:
            raise ValueError(
                f"Value of colidx out of range [0, {self.num_ranges - 1}]. Provided value: {rngidx}")

    def validate(self) -> tuple[dict, list]:
        warnings = {}
        errors = []
        intervals = []

        for row in self._ranges.itertuples():
            rowidx = row.Index
            lower_bound = row.lower_bound
            upper_bound = row.upper_bound

            warnings[rowidx] = []

            missing_bound = False

            if lower_bound is None or np.isnan(lower_bound):
                warnings[rowidx].append(
                    f"Invalid lower bound in row {rowidx}: {lower_bound}")
                missing_bound = True

            if upper_bound is None or np.isnan(upper_bound):
                warnings[rowidx].append(
                    f"Invalid upper bound in row {rowidx}: {upper_bound}")
                missing_bound = True

            if not missing_bound and lower_bound >= upper_bound:
                warnings[rowidx].append(
                    f"Invalid bounds in row {rowidx}: lower bound ({lower_bound}) >= upper bound ({upper_bound})")

            if not warnings[rowidx]:
                intervals.append(
                    (rowidx, pd.Interval(lower_bound, upper_bound)))

        intervals.sort(key=lambda t: t[1].left)

        overlaps = []
        for i in range(len(intervals) - 1):
            if intervals[i][1].overlaps(intervals[i + 1][1]):
                overlaps.append((intervals[i][0], intervals[i + 1][0]))

        errors.append(f"The ranges of the folowing rows overlaps: {overlaps}")

        return warnings, errors

    def set_range(self, rngidx: int, lower_bound: float, upper_bound: float) -> None:
        self._check_rngidx(rngidx)

        self._ranges.loc[rngidx, 'lower_bound'] = lower_bound
        self._ranges.loc[rngidx, 'upper_bound'] = upper_bound

    def get_risk_tiers(self) -> pd.Series:
        raise NotImplementedError()


class IterationSingleVar(IterationBase):
    def __init__(self, id: str, variable: pd.Series = None) -> None:
        super().__init__(id, variable)
        self._ranges['risk_tier'] = self.SUB_RISK_TIERS

    def get_risk_tiers(self) -> pd.Series:
        warnings, errors = self.validate()
        risk_tier_column = pd.Series(
            index=self.variable.index, name=self.variable.name)

        if errors:
            return risk_tier_column

        valid_risk_tiers = list(
            set(self.SUB_RISK_TIERS) - set(self._ranges.loc[warnings.keys(), 'risk_tier']))

        for risk_tier in valid_risk_tiers:
            lower_bound = self._ranges.loc[self._ranges['risk_tier']
                                           == risk_tier, 'lower_bound']
            upper_bound = self._ranges.loc[self._ranges['risk_tier']
                                           == risk_tier, 'upper_bound']

            mask = (self._variable > lower_bound) & (
                self._variable <= upper_bound)
            risk_tier_column.loc[mask] = risk_tier

        return risk_tier_column


class IterationDoubleVar(IterationBase):
    def __init__(self, id: str, previos_iteration: IterationBase, variable: pd.Series = None) -> None:
        super().__init__(id, variable)

        self._previous_iteration = previos_iteration
        self._risk_tier_grid = pd.DataFrame(np.array(self.SUB_RISK_TIERS).repeat(
            self.num_ranges).reshape(-1, self.num_ranges), index=self.SUB_RISK_TIERS)

    def delete_range(self, rngidx: int) -> None:
        self._check_rngidx(rngidx)

        self._ranges = self._ranges.drop(index=rngidx).reset_index()
        self._risk_tier_grid = np.delete(self._risk_tier_grid, rngidx, 1)

    def insert_range(self, rngidx: int) -> None:
        self._check_rngidx(rngidx)

        rngidx = max(1, rngidx)
        mask = self._ranges.index
        mask1 = mask[mask < rngidx]
        mask2 = mask[mask == rngidx]
        mask3 = mask[mask >= rngidx]

        part1 = self._ranges.iloc[mask1].copy()
        part2 = self._ranges.iloc[mask2].copy()
        part3 = self._ranges.iloc[mask3].copy()

        part2.loc[rngidx, 'upper_bound'] = part2.loc[rngidx, 'lower_bound']

        self._ranges = pd.concat(
            [part1, part2, part3], axis=0).reset_index(drop=True)

        part1 = self._risk_tier_grid.iloc[:, mask1].copy()
        part2 = self._risk_tier_grid.iloc[:, mask2].copy()
        part3 = self._risk_tier_grid.iloc[:, mask3].copy()

        self._risk_tier_grid = pd.concat([part1, part2, part3], axis=1)
        self._risk_tier_grid.columns = self._ranges.index

    def set_risk_tier_grid(self, rngidx: int, previous_iteration_rt, value) -> None:
        if previous_iteration_rt not in self.SUB_RISK_TIERS:
            raise ValueError(
                f"Invalid value for risk tier provided: {previous_iteration_rt}")

        self._risk_tier_grid.loc[self.SUB_RISK_TIERS.index(
            previous_iteration_rt), rngidx] = value

    def get_risk_tiers(self) -> pd.Series:
        warnings, error = self.validate()
        risk_tier_column = pd.Series(
            index=self.variable.index, name=self.variable.name)

        if error:
            return risk_tier_column

        previous_risk_tiers = self._previous_iteration.get_risk_tiers()
        valid_columns = list(
            sorted(list(set(self._ranges.index) - set(warnings.keys()))))

        for prev_rt in previous_risk_tiers.unique():
            for colidx in valid_columns:
                lower_bound = self._ranges.loc[colidx, 'lower_bound']
                upper_bound = self._ranges.loc[colidx, 'upper_bound']

                risk_tier_column.loc[
                    (previous_risk_tiers == prev_rt) &
                    (self._variable > lower_bound) &
                    (self._variable <= upper_bound)
                ] = self._risk_tier_grid.loc[prev_rt, colidx]

        return risk_tier_column

__all__ = ['IterationSingleVar', 'IterationDoubleVar']
