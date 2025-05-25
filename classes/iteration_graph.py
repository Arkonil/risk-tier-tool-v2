from typing import Literal, Union

import numpy as np
import pandas as pd

from classes.iteration import (
    IterationBase,
    SingleVarIteration,
    DoubleVarIteration,
    NumericalIteration,
    CategoricalIteration,
    NumericalSingleVarIteration,
    NumericalDoubleVarIteration,
    CategoricalSingleVarIteration,
    CategoricalDoubleVarIteration,
)
from classes.common import SUB_RISK_TIERS, Names

def __integer_generator():
    current = 0
    while True:
        current += 1
        yield current


__generator = __integer_generator()


def new_id():
    return str(next(__generator))

class IterationGraph:

    MAX_DEPTH = 10

    def __init__(self) -> None:
        self.iterations: dict[str, IterationBase] = {}

        self.connections: dict[str, list[str]] = {}
        self._iteration_outputs: dict[str, pd.Series] = {}
        self.iteration_metrics: dict[str, pd.Series] = {}

        self._selected_node_id = None
        self._current_node_id = None
        self._recalculation_required = set()

        self.__default_metric_df = pd.DataFrame({
            "metric": [Names.VOLUME, Names.AVG_BAL, Names.WO_COUNT, Names.WO_COUNT_PCT, Names.WO_BAL, Names.WO_BAL_PCT],
            "order": [0, 1, 2, 3, 4, 5],
            "showing": [True, True, True, True, True, True],
        })

    @property
    def selected_node_id(self):
        return self._selected_node_id

    def select_node_id(self, node_id: str = None):
        if node_id in self.iterations:
            self._selected_node_id = node_id
        else:
            self._selected_node_id = None

    @property
    def current_node_id(self):
        return self._current_node_id

    def select_current_node_id(self, node_id: str = None):
        if node_id in self.iterations:
            self._current_node_id = node_id
        else:
            self._current_node_id = None

    @property
    def current_iteration(self):
        return self.iterations[self.current_node_id]

    def get_iteration_type(self, node_id: str = None) -> Literal["numerical", "categorical"]:
        if node_id is None:
            node_id = self.current_node_id

        if isinstance(self.iterations[node_id], NumericalIteration):
            return "numerical"

        if isinstance(self.iterations[node_id], CategoricalIteration):
            return "categorical"

        raise ValueError(f"Invalid iteration type: {type(self.iterations[node_id])}")

    def get_parent(self, node_id: str = None) -> Union[str, None]:
        if node_id is None:
            node_id = self.current_node_id

        for parent, children in self.connections.items():
            if node_id in children:
                return parent

        return None

    def iteration_depth(self, node_id: str = None) -> int:
        if node_id is None:
            node_id = self.current_node_id

        parent_node_id = self.get_parent(node_id)
        if parent_node_id is None:
            return 1

        return 1 + self.iteration_depth(parent_node_id)

    def get_ancestors(self, node_id: str = None) -> list[str]:
        if node_id is None:
            node_id = self.current_node_id

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

    def get_parent_tiers(self, node_id: str = None) -> list[int]:
        if node_id is None:
            node_id = self.current_node_id

        if self.is_root(node_id):
            return []

        parent_node_id = self.get_parent(node_id)
        parent_node = self.iterations[parent_node_id]

        if isinstance(parent_node, SingleVarIteration):
            return parent_node.groups.index.tolist()

        if isinstance(parent_node, DoubleVarIteration):
            return np.unique(parent_node.risk_tier_grid.values.flatten()).tolist()

        raise ValueError(f"Invalid iteration type: {type(parent_node)}")

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
        variable_dtype: Literal["numerical", "categorical"]):

        new_node_id = new_id()

        initial_group_count = len(SUB_RISK_TIERS)

        if variable_dtype == "numerical":
            iteration = NumericalSingleVarIteration(
                _id=new_node_id,
                name=name,
                variable=variable,
                initial_group_count=initial_group_count
            )
        elif variable_dtype == "categorical":
            iteration = CategoricalSingleVarIteration(
                _id=new_node_id,
                name=name,
                variable=variable,
                initial_group_count=initial_group_count
            )
        else:
            raise ValueError(f"Invalid variable type: {variable_dtype}")

        self.iterations[new_node_id] = iteration
        self.iteration_metrics[new_node_id] = self.__default_metric_df.copy()
        self._recalculation_required.add(new_node_id)

        # self.select_node_id(new_node_id)

    def add_double_var_node(
        self,
        name: str,
        variable: pd.Series,
        variable_dtype: Literal["numerical", "categorical"],
        previous_node_id: str):

        new_node_id = new_id()

        if variable_dtype == "numerical":
            iteration = NumericalDoubleVarIteration(
                _id=new_node_id,
                name=name,
                variable=variable,
                initial_group_count=10,
            )
        elif variable_dtype == "categorical":
            iteration = CategoricalDoubleVarIteration(
                _id=new_node_id,
                name=name,
                variable=variable,
                initial_group_count=10,
            )
        else:
            raise ValueError(f"Invalid variable type: {variable_dtype}")

        self.iterations[new_node_id] = iteration
        self.iteration_metrics[new_node_id] = self.__default_metric_df.copy()

        self.connections.setdefault(previous_node_id, []).append(new_node_id)

        self.select_node_id(new_node_id)

    def add_node(
        self,
        name: str,
        variable: pd.Series,
        variable_dtype: Literal["numerical", "categorical"],
        previous_node_id: str = None):

        if previous_node_id is None:
            self.add_single_var_node(name, variable, variable_dtype)
        else:
            self.add_double_var_node(name, variable, variable_dtype, previous_node_id)

    def delete_iteration(self, node_id: str):
        nodes_to_delete = [node_id] + self.get_descendants(node_id)

        for node in nodes_to_delete:
            if node in self.iterations:
                del self.iterations[node]

            if node in self._iteration_outputs:
                del self._iteration_outputs[node]

            if node in self.connections:
                del self.connections[node]

        for parent, children in self.connections.items():
            self.connections[parent] = [
                child for child in children if child not in nodes_to_delete]

        self.select_node_id()

    def add_to_calculation_queue(self, node_id: str = None):
        if node_id is None:
            node_id = self.current_node_id

        self._recalculation_required.add(node_id)
        for descendant in self.get_descendants(node_id):
            self._recalculation_required.add(descendant)

    def get_risk_tiers(self, node_id: str = None) -> tuple[pd.Series, list[str], list[str], list]:
        invalid_groups = []
        warnings = []
        errors = []

        if node_id is None:
            node_id = self.current_node_id

        if node_id not in self._iteration_outputs:
            self._recalculation_required.add(node_id)

        if node_id not in self._recalculation_required:
            return self._iteration_outputs[node_id], errors, warnings, invalid_groups

        if self.is_root(node_id):
            # print(f"Calculating Risk Tiers for node: {node_id}")
            risk_tier_column, errors, warnings, invalid_groups = self.iterations[node_id].get_risk_tiers()

            if not errors:
                self._iteration_outputs[node_id] = risk_tier_column
                self._recalculation_required.remove(node_id)

            return risk_tier_column, errors, warnings, invalid_groups

        calculation_path = self.get_ancestors(node_id)
        calculation_path.append(node_id)

        for node in calculation_path:
            if node not in self._recalculation_required:
                continue

            # print(f"Calculating Risk Tiers for node: {node}")
            risk_tier_column, errors, warnings, invalid_groups = self.iterations[node].get_risk_tiers(
                previous_risk_tiers=self._iteration_outputs[self.get_parent(node)]
            )

            if errors:
                return risk_tier_column, errors, warnings, invalid_groups

            self._iteration_outputs[node] = risk_tier_column
            self._recalculation_required.remove(node)

        return risk_tier_column, errors, warnings, invalid_groups


__all__ = [
    "IterationGraph",
]
