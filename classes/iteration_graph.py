import itertools
import typing as t

import pandas as pd

from classes.auto_band import create_auto_bands
from classes.constants import (
    DefaultOptions,
    IterationMetadata,
    IterationType,
    LossRateTypes,
    RTDetCol,
    RangeColumn,
    VariableType,
)
from classes.iteration import (
    CategoricalDoubleVarIteration,
    CategoricalSingleVarIteration,
    IterationOutput,
    NumericalDoubleVarIteration,
    NumericalSingleVarIteration,
)
from classes.scalars import Scalar
from classes.utils import integer_generator


Iteration = t.Union[
    NumericalSingleVarIteration,
    NumericalDoubleVarIteration,
    CategoricalSingleVarIteration,
    CategoricalDoubleVarIteration,
]

__generator = integer_generator()


def new_id(current_ids: t.Iterable[str] = None) -> str:
    if current_ids is None:
        current_ids = []

    while True:
        new_id = str(next(__generator))
        if new_id not in current_ids:
            return new_id


class IterationGraph:
    def __init__(self) -> None:
        self.iterations: dict[str, Iteration] = {}
        self.connections: dict[str, list[str]] = {}
        self.iteration_metadata: dict[str, IterationMetadata] = {}

        self._iteration_outputs: dict[
            tuple[str, t.Literal["default", "edited"]], IterationOutput
        ] = {}

        self._selected_node_id: str | None = None
        self._current_node_id: str | None = None
        self._current_iter_create_mode: IterationType | None = None
        self._current_iter_create_parent_id: str | None = None

        self._recalculation_required = set()

    @property
    def is_empty(self):
        return len(self.iterations) == 0

    def select_graph_view(self):
        self._selected_node_id = None
        self._current_node_id = None
        self._current_iter_create_mode = None
        self._current_iter_create_parent_id = None

    @property
    def selected_node_id(self):
        return self._selected_node_id

    def select_node_id(self, node_id: str):
        self.select_graph_view()

        if node_id in self.iterations:
            self._selected_node_id = node_id

    @property
    def current_node_id(self):
        return self._current_node_id

    def select_current_node_id(self, node_id: str):
        self.select_graph_view()

        if node_id in self.iterations:
            self._current_node_id = node_id

    @property
    def current_iter_create_mode(self):
        return self._current_iter_create_mode

    @property
    def current_iter_create_parent_id(self):
        return self._current_iter_create_parent_id

    def set_current_iter_create_mode(
        self, iteration_type: IterationType, parent_node_id: str = None
    ):
        self.select_graph_view()

        if iteration_type == IterationType.DOUBLE and parent_node_id is None:
            raise ValueError(
                "Must provide a parent_node_id for double variable iteration"
            )

        if iteration_type in IterationType:
            self._current_iter_create_mode = iteration_type
            self._current_iter_create_parent_id = parent_node_id

    @property
    def current_iteration(self):
        return self.iterations[self.current_node_id]

    def get_parent(self, node_id: str = None) -> str | None:
        if node_id is None:
            node_id = self.current_node_id

        for parent, children in self.connections.items():
            if node_id in children:
                return parent

        return None

    def iteration_depth(self, node_id: str = None) -> int:
        parent_node_id = self.get_parent(node_id)
        if parent_node_id is None:
            return 1

        return 1 + self.iteration_depth(parent_node_id)

    def get_ancestors(self, node_id: str = None) -> list[str]:
        ancestors = []
        parent_node_id = self.get_parent(node_id)
        while parent_node_id is not None:
            ancestors.append(parent_node_id)
            parent_node_id = self.get_parent(parent_node_id)

        return list(reversed(ancestors))

    def get_descendants(self, node_id: str = None) -> list[str]:
        if node_id is None:
            node_id = self.current_node_id

        if node_id not in self.connections:
            return []

        descendants = self.connections[node_id]
        for descendant in descendants:
            descendants += self.get_descendants(descendant)

        return descendants

    def get_root_iter_id(self, node_id: str = None) -> str:
        if node_id is None:
            node_id = self.current_node_id

        if self.is_root(node_id):
            return node_id

        return self.get_root_iter_id(self.get_parent(node_id))

    def get_risk_tier_details(self, node_id: str = None) -> pd.DataFrame:
        if node_id is None:
            node_id = self.current_node_id

        root_iter_id = self.get_root_iter_id(node_id)
        return self.iterations[root_iter_id].risk_tier_details

    def get_color(self, rt_label: str, node_id: str = None):
        if node_id is None:
            node_id = self.current_node_id

        risk_tier_details = self.get_risk_tier_details(node_id)

        font_color = risk_tier_details.loc[
            risk_tier_details[RTDetCol.RISK_TIER] == rt_label, RTDetCol.FONT_COLOR
        ]
        bg_color = risk_tier_details.loc[
            risk_tier_details[RTDetCol.RISK_TIER] == rt_label, RTDetCol.BG_COLOR
        ]

        return font_color.iloc[0], bg_color.iloc[0]

    def is_root(self, node_id: str = None) -> bool:
        if node_id is None:
            node_id = self.current_node_id

        return self.get_parent(node_id) is None

    def is_leaf(self, node_id: str = None) -> bool:
        if node_id is None:
            node_id = self.current_node_id

        return node_id not in self.connections or len(self.connections[node_id]) == 0

    def add_single_var_node(
        self,
        name: str,
        variable: pd.Series,
        variable_dtype: VariableType,
        risk_tier_details: pd.DataFrame,
        loss_rate_type: LossRateTypes,
        auto_band: bool,
        dlr_scalar: Scalar = None,
        ulr_scalar: Scalar = None,
        dlr_wrt_off: pd.Series = None,
        unt_wrt_off: pd.Series = None,
        avg_bal: pd.Series = None,
    ) -> NumericalSingleVarIteration | CategoricalSingleVarIteration:
        new_node_id = new_id(current_ids=self.iterations.keys())

        if variable_dtype == VariableType.NUMERICAL:
            iteration = NumericalSingleVarIteration(
                _id=new_node_id,
                name=name,
                variable=variable,
                risk_tier_details=risk_tier_details,
            )
        elif variable_dtype == VariableType.CATEGORICAL:
            iteration = CategoricalSingleVarIteration(
                _id=new_node_id,
                name=name,
                variable=variable,
                risk_tier_details=risk_tier_details,
            )
        else:
            raise ValueError(f"Invalid variable type: {variable_dtype}")

        self.iterations[new_node_id] = iteration
        self.iteration_metadata[new_node_id] = {
            **DefaultOptions().default_iteation_metadata,
            "loss_rate_type": loss_rate_type,
        }

        if auto_band:
            groups = create_auto_bands(
                variable=variable,
                mask=pd.Series(True, index=variable.index),
                risk_tier_details=risk_tier_details,
                dlr_scalar=dlr_scalar,
                ulr_scalar=ulr_scalar,
                loss_rate_type=loss_rate_type,
                dlr_wrt_off=dlr_wrt_off,
                unt_wrt_off=unt_wrt_off,
                avg_bal=avg_bal,
            )

            if variable_dtype == VariableType.NUMERICAL:
                groups = (
                    groups.apply(
                        lambda row: (
                            row[RangeColumn.LOWER_BOUND],
                            row[RangeColumn.UPPER_BOUND],
                        ),
                        axis=1,
                    )
                    .rename(RangeColumn.GROUPS)
                    .rename_axis(index=[""])
                )

            iteration._default_groups = groups
            iteration._groups = groups

        self._recalculation_required.add((new_node_id, "default"))
        self._recalculation_required.add((new_node_id, "edited"))

        return iteration

    def add_double_var_node(
        self,
        name: str,
        variable: pd.Series,
        variable_dtype: VariableType,
        previous_node_id: str,
        auto_band: bool,
        upgrade_downgrade_limit: int = None,
        dlr_scalar: Scalar = None,
        ulr_scalar: Scalar = None,
        dlr_wrt_off: pd.Series = None,
        unt_wrt_off: pd.Series = None,
        avg_bal: pd.Series = None,
    ) -> NumericalDoubleVarIteration | CategoricalDoubleVarIteration:
        if previous_node_id not in self.iterations:
            raise ValueError(
                f"Invalid previous node id: {previous_node_id}. Iteration does not exist."
            )

        risk_tier_details = self.get_risk_tier_details(previous_node_id)

        new_node_id = new_id(current_ids=self.iterations.keys())

        if variable_dtype == VariableType.NUMERICAL:
            iteration = NumericalDoubleVarIteration(
                _id=new_node_id,
                name=name,
                variable=variable,
                risk_tier_details=risk_tier_details,
            )
        elif variable_dtype == VariableType.CATEGORICAL:
            iteration = CategoricalDoubleVarIteration(
                _id=new_node_id,
                name=name,
                variable=variable,
                risk_tier_details=risk_tier_details,
            )
        else:
            raise ValueError(f"Invalid variable type: {variable_dtype}")

        loss_rate_type = self.iteration_metadata[previous_node_id]["loss_rate_type"]

        self.iterations[new_node_id] = iteration
        self.iteration_metadata[new_node_id] = {
            **DefaultOptions().default_iteation_metadata,
            "loss_rate_type": loss_rate_type,
        }
        self.connections.setdefault(previous_node_id, []).append(new_node_id)

        if auto_band:
            previous_iter_output = self.get_risk_tiers(previous_node_id, default=False)

            if not previous_iter_output["errors"]:
                previous_risk_tiers = previous_iter_output["risk_tier_column"]
                unique_tiers = (
                    previous_risk_tiers.dropna()
                    .drop_duplicates(ignore_index=True)
                    .sort_values()
                )
                rt_groups: dict[int, pd.Series] = {}

                for rt in unique_tiers:
                    groups = create_auto_bands(
                        variable=variable,
                        mask=previous_risk_tiers == rt,
                        risk_tier_details=risk_tier_details.iloc[
                            max(0, rt - upgrade_downgrade_limit) : rt
                            + upgrade_downgrade_limit
                            + 1
                        ].copy(),
                        dlr_scalar=dlr_scalar,
                        ulr_scalar=ulr_scalar,
                        loss_rate_type=loss_rate_type,
                        dlr_wrt_off=dlr_wrt_off,
                        unt_wrt_off=unt_wrt_off,
                        avg_bal=avg_bal,
                    )

                    if variable_dtype == VariableType.NUMERICAL:
                        groups = (
                            groups.replace({
                                groups.min().min(): variable.min() - 1,
                                groups.max().max(): variable.max(),
                            })
                            .apply(
                                lambda row: (
                                    row[RangeColumn.LOWER_BOUND],
                                    row[RangeColumn.UPPER_BOUND],
                                ),
                                axis=1,
                            )
                            .rename(RangeColumn.GROUPS)
                            .rename_axis(index=[""])
                        )

                    rt_groups[rt] = groups

                if variable_dtype == VariableType.NUMERICAL:
                    cut_points = map(
                        lambda s: list(sum(s.to_list(), ())), rt_groups.values()
                    )
                    cut_points = list(sorted(list(set(sum(cut_points, [])))))
                    pairs = itertools.pairwise(cut_points)

                    groups = pd.Series(pairs, name=RangeColumn.GROUPS)
                    risk_tier_grid = pd.DataFrame(
                        index=groups.index, columns=risk_tier_details.index
                    )

                    for i in risk_tier_grid.index:
                        for j in risk_tier_grid.columns:
                            lower_bound = groups[i][0]
                            upper_bound = groups[i][1]

                            rt_group = rt_groups.get(j)
                            if rt_group is None:
                                risk_tier_grid.loc[i, j] = j
                                continue

                            for index, (lb, ub) in rt_group.items():
                                if lb <= lower_bound and ub >= upper_bound:
                                    risk_tier_grid.loc[i, j] = index
                                    break
                            else:
                                risk_tier_grid.loc[i, j] = j

                    iteration._default_groups = groups
                    iteration._groups = groups
                    iteration._risk_tier_grid = risk_tier_grid
                    iteration.default_risk_tier_grid = risk_tier_grid

        self._recalculation_required.add((new_node_id, "default"))
        self._recalculation_required.add((new_node_id, "edited"))

        return iteration

    def delete_iteration(self, node_id: str):
        nodes_to_delete = [node_id] + self.get_descendants(node_id)

        for node in nodes_to_delete:
            if node in self.iterations:
                del self.iterations[node]

            if (node, "default") in self._iteration_outputs:
                del self._iteration_outputs[(node, "default")]

            if (node, "edited") in self._iteration_outputs:
                del self._iteration_outputs[(node, "edited")]

            if node in self.connections:
                del self.connections[node]

        for parent, children in self.connections.items():
            self.connections[parent] = [
                child for child in children if child not in nodes_to_delete
            ]

        self.select_graph_view()

    def add_to_calculation_queue(
        self, node_id: str = None, default: t.Literal[False] = False
    ):
        if node_id is None:
            node_id = self.current_node_id

        default_or_edited = "default" if default else "edited"

        self._recalculation_required.add((node_id, default_or_edited))
        for descendant in self.get_descendants(node_id):
            self._recalculation_required.add((descendant, "default"))
            self._recalculation_required.add((descendant, "edited"))

    def get_risk_tiers(
        self, node_id: str = None, default: bool = False
    ) -> IterationOutput:
        if node_id is None:
            node_id = self.current_node_id

        default_or_edited = "default" if default else "edited"

        if (node_id, default_or_edited) not in self._iteration_outputs:
            self._recalculation_required.add((node_id, default_or_edited))

        # No calculation required. Taking from cache.
        if (node_id, default_or_edited) not in self._recalculation_required:
            return self._iteration_outputs[(node_id, default_or_edited)]

        # Calculation Required.
        previous_risk_tiers = None

        if not self.is_root(node_id):
            previous_node_output = self.get_risk_tiers(
                self.get_parent(node_id), default=False
            )
            previous_risk_tiers = previous_node_output["risk_tier_column"]

        iteration_output = self.iterations[node_id].get_risk_tiers(
            previous_risk_tiers=previous_risk_tiers,
            default=default,
        )

        self._iteration_outputs[(node_id, default_or_edited)] = iteration_output
        self._recalculation_required.remove((node_id, default_or_edited))

        return iteration_output


__all__ = [
    "IterationGraph",
]
