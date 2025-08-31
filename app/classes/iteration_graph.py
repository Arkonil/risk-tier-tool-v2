import itertools
import re
import textwrap
import typing as t

import pandas as pd

from classes.auto_band import create_auto_bands
from classes.constants import (
    TAB,
    DefaultOptions,
    IterationMetadata,
    IterationType,
    LossRateTypes,
    RTDetCol,
    RangeColumn,
    VariableType,
    IterationMetadataKeys,
)
from classes.data import Data
from classes.filter import Filter
from classes.iteration import (
    CategoricalDoubleVarIteration,
    CategoricalSingleVarIteration,
    IterationOutput,
    NumericalDoubleVarIteration,
    NumericalSingleVarIteration,
    from_dict as iteration_from_dict,
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

    def get_parent(self, node_id: str) -> str | None:
        for parent, children in self.connections.items():
            if node_id in children:
                return parent

        return None

    def iteration_depth(self, node_id: str) -> int:
        parent_node_id = self.get_parent(node_id)
        if parent_node_id is None:
            return 1

        return 1 + self.iteration_depth(parent_node_id)

    def get_ancestors(self, node_id: str) -> list[str]:
        ancestors = []
        parent_node_id = self.get_parent(node_id)
        while parent_node_id is not None:
            ancestors.append(parent_node_id)
            parent_node_id = self.get_parent(parent_node_id)

        return list(reversed(ancestors))

    def get_descendants(self, node_id: str) -> list[str]:
        if node_id not in self.connections:
            return []

        descendants = self.connections[node_id]
        for descendant in descendants:
            descendants += self.get_descendants(descendant)

        return descendants

    def get_root_iter_id(self, node_id: str) -> str:
        if self.is_root(node_id):
            return node_id

        return self.get_root_iter_id(self.get_parent(node_id))

    def get_risk_tier_details(self, node_id: str) -> pd.DataFrame:
        root_iter_id = self.get_root_iter_id(node_id)
        return self.iterations[root_iter_id].risk_tier_details

    def get_color(self, rt_label: str, node_id: str):
        risk_tier_details = self.get_risk_tier_details(node_id)

        font_color = risk_tier_details.loc[
            risk_tier_details[RTDetCol.RISK_TIER] == rt_label, RTDetCol.FONT_COLOR
        ]
        bg_color = risk_tier_details.loc[
            risk_tier_details[RTDetCol.RISK_TIER] == rt_label, RTDetCol.BG_COLOR
        ]

        return font_color.iloc[0], bg_color.iloc[0]

    def get_metadata(self, node_id: str, key: IterationMetadataKeys):
        if node_id not in self.iteration_metadata:
            raise ValueError(f"Node ID {node_id} does not exist in iteration metadata.")

        metadata = self.iteration_metadata[node_id]
        if key not in metadata:
            raise KeyError(f"Key '{key}' not found in metadata for node ID {node_id}.")

        root_id = self.get_root_iter_id(node_id)
        if key in ("loss_rate_type", "filters"):
            return self.iteration_metadata[root_id][key]

        return metadata[key]

    def set_metadata(self, node_id: str, key: IterationMetadataKeys, value: t.Any):
        if node_id not in self.iteration_metadata:
            raise ValueError(f"Node ID {node_id} does not exist in iteration metadata.")

        metadata = self.iteration_metadata[node_id]
        if key not in metadata:
            raise KeyError(f"Key '{key}' not found in metadata for node ID {node_id}.")

        # Update filters for all nodes in the subtree
        if key == "filters":
            # If filters are being set, we need to ensure they are valid Filter objects
            if not isinstance(value, set) or not all(isinstance(f, str) for f in value):
                raise ValueError("Filters must be a set of str objects.")

            root_id = self.get_root_iter_id(node_id)
            descendants = self.get_descendants(root_id)
            for descendant in [root_id] + descendants:
                self.iteration_metadata[descendant]["filters"] = value

                # If the metadata is related to filters, we need to mark the node for recalculation
                # TODO: Check. Why is recalculation needed?
                self.add_to_calculation_queue(descendant, default=True)
                self.add_to_calculation_queue(descendant, default=False)

            return

        metadata[key] = value

    def is_root(self, node_id: str) -> bool:
        return self.get_parent(node_id) is None

    def is_leaf(self, node_id: str) -> bool:
        return node_id not in self.connections or len(self.connections[node_id]) == 0

    def add_single_var_node(
        self,
        name: str,
        variable: pd.Series,
        variable_dtype: VariableType,
        risk_tier_details: pd.DataFrame,
        loss_rate_type: LossRateTypes,
        filter_objs: set[Filter],
        auto_band: bool,
        mob: int = None,
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
            "filters": {filter_obj.id for filter_obj in filter_objs},
        }

        if auto_band:
            mask = pd.Series(True, index=variable.index)
            for filter_obj in filter_objs:
                mask &= filter_obj.mask

            groups = create_auto_bands(
                variable=variable,
                mask=mask,
                risk_tier_details=risk_tier_details,
                dlr_scalar=dlr_scalar,
                ulr_scalar=ulr_scalar,
                loss_rate_type=loss_rate_type,
                mob=mob,
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

            iteration.set_default_groups(groups)

        self._recalculation_required.add((new_node_id, "default"))
        self._recalculation_required.add((new_node_id, "edited"))

        return iteration

    def add_double_var_node(
        self,
        name: str,
        variable: pd.Series,
        variable_dtype: VariableType,
        previous_node_id: str,
        filter_objs: set[Filter],
        auto_band: bool,
        mob: int = None,
        upgrade_limit: int = None,
        downgrade_limit: int = None,
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
            "filters": {filter_obj.id for filter_obj in filter_objs},
        }
        self.connections.setdefault(previous_node_id, []).append(new_node_id)

        if auto_band:
            mask = pd.Series(True, index=variable.index)
            for filter_obj in filter_objs:
                mask &= filter_obj.mask

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
                        mask=(previous_risk_tiers == rt) & mask,
                        risk_tier_details=risk_tier_details.iloc[
                            max(0, rt - upgrade_limit) : rt + downgrade_limit + 1
                        ].copy(),
                        dlr_scalar=dlr_scalar,
                        ulr_scalar=ulr_scalar,
                        loss_rate_type=loss_rate_type,
                        mob=mob,
                        dlr_wrt_off=dlr_wrt_off,
                        unt_wrt_off=unt_wrt_off,
                        avg_bal=avg_bal,
                    )

                    if variable_dtype == VariableType.NUMERICAL:
                        with pd.option_context("future.no_silent_downcasting", True):
                            groups = (
                                groups.replace({
                                    groups.min().min(): variable.min() - 1,
                                    groups.max().max(): variable.max(),
                                })
                                .infer_objects(copy=False)
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

                    iteration.set_default_groups(groups)
                    iteration.set_default_risk_tier_grid(risk_tier_grid)

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

    def add_to_calculation_queue(self, node_id: str, default: bool):
        default_or_edited = "default" if default else "edited"

        self._recalculation_required.add((node_id, default_or_edited))
        for descendant in self.get_descendants(node_id):
            self._recalculation_required.add((descendant, "default"))
            self._recalculation_required.add((descendant, "edited"))

    def get_risk_tiers(self, node_id: str, default: bool) -> IterationOutput:
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

    def get_sas_code(self, node_id: str, default: bool, use_macro: bool) -> str:
        node_chain = self.get_ancestors(node_id)
        node_chain.append(node_id)

        risk_tier_details = self.get_risk_tier_details(node_id)
        output_value_mapping = {
            f"GROUP_INDEX_{k}": f'"{v}"'
            for k, v in risk_tier_details[RTDetCol.RISK_TIER].to_dict().items()
        }

        code_templates = []
        pattern = re.compile(r"(.+) \((Numerical|Categorical)\)")

        for i, node in enumerate(node_chain):
            if i < len(node_chain) - 1:
                _default = False
            else:
                _default = default

            iteration = self.iterations[node]
            if match := pattern.match(iteration.variable.name):
                variable_name = match.group(1)
            else:
                variable_name = iteration.variable.name

            # Ordering here is important
            if self.is_root(node):
                output_variable_name = (
                    f"Risk_Tier_{node}_{'default' if _default else 'custom'}"
                )
                previous_iter_out_name = ""
            else:
                previous_iter_out_name = output_variable_name
                output_variable_name = (
                    f"Risk_Tier_{node}_{'default' if _default else 'custom'}"
                )

            code_templates.append({
                "node_id": node,
                "template": iteration.generate_sas_code(default=_default),
                "substitute": {
                    "VARIABLE_NAME": variable_name,
                    "OUTPUT_VARIABLE_NAME": output_variable_name,
                    "PREV_ITER_OUT_NAME": previous_iter_out_name,
                    "MISSING": '""',
                }
                | output_value_mapping,
            })

        code = ""

        if use_macro:
            code += "/* Macro Definitions: */\n"

            raw_variables = {}
            result_variables = {}

            for i, item in enumerate(code_templates):
                substitute_d = item["substitute"]

                raw_variables[f"variable_{i}_"] = substitute_d["VARIABLE_NAME"]
                result_variables[f"result_{i}_"] = substitute_d["OUTPUT_VARIABLE_NAME"]

                substitute_d["VARIABLE_NAME"] = f"&variable_{i}_."
                substitute_d["OUTPUT_VARIABLE_NAME"] = f"&result_{i}_."

            for macro, value in raw_variables.items():
                code += f"%let {macro} = {value};\n"

            for macro, value in result_variables.items():
                code += f"%let {macro} = {value};\n"

            code += "\n"

        for item in code_templates:
            code += f"/* Iteration {item['node_id']} */\n\n"
            code += item["template"].safe_substitute(item["substitute"])
            code += "\n" * 2

        fullcode = "/* Specify input/Output Data Name */\n"
        fullcode += "data result;\n"
        fullcode += textwrap.indent("set source;\n\n", TAB)
        fullcode += textwrap.indent(code.strip(), TAB)
        fullcode += "\nrun;"

        return fullcode.strip()

    def get_python_code(self, node_id: str, default: bool, data: Data) -> str:
        node_chain = self.get_ancestors(node_id)
        node_chain.append(node_id)

        risk_tier_details = self.get_risk_tier_details(node_id)
        output_value_mapping = {
            f"GROUP_INDEX_{k}": f'"{v}"'
            for k, v in risk_tier_details[RTDetCol.RISK_TIER].to_dict().items()
        }

        code_templates = []
        pattern = re.compile(r"(.+) \((Numerical|Categorical)\)")

        for i, node in enumerate(node_chain):
            if i < len(node_chain) - 1:
                _default = False
            else:
                _default = default

            iteration = self.iterations[node]
            if match := pattern.match(iteration.variable.name):
                variable_name = match.group(1)
            else:
                variable_name = iteration.variable.name

            # Ordering here is important
            if self.is_root(node):
                output_variable_name = (
                    f"Risk_Tier_{node}_{'default' if _default else 'custom'}"
                )
                previous_iter_out_name = ""
            else:
                previous_iter_out_name = output_variable_name
                output_variable_name = (
                    f"Risk_Tier_{node}_{'default' if _default else 'custom'}"
                )

            code_templates.append({
                "node_id": node,
                "template": iteration.generate_python_code(default=_default),
                "substitute": {
                    "VARIABLE_NAME": variable_name,
                    "OUTPUT_VARIABLE_NAME": output_variable_name,
                    "PREV_ITER_OUT_NAME": previous_iter_out_name,
                    "MISSING": '""',
                    "DATA": "data",
                }
                | output_value_mapping,
            })

        module_import = textwrap.dedent("""
            # Module Imports
            import numpy as np
            import pandas as pd
            
        """)

        data_import_csv = textwrap.dedent(f"""
            # Data Import
            data = pd.read_csv(
                filepath_or_buffer="{str(data.filepath.absolute())}",
                delimiter="{data.delimiter}",
                header={data.header_row},
            )
            
        """)

        data_import_excel = textwrap.dedent(f"""
            # Data Import
            data = pd.read_excel(
                io="{str(data.filepath.absolute())}",
                sheet_name={data.sheet_name if data.sheet_name.isnumeric() else f'"{data.sheet_name}"'},
                header="{data.header_row}",
            )
            
        """)

        function_definitions = textwrap.dedent("""                   
            # Function Definitions:
            def create_mapped_variable(variable: pd.Series, mapping: pd.Series):
                if isinstance(mapping.index.dtype, pd.IntervalDtype):
                    return pd.cut(
                        x = variable,
                        bins = mapping.index,
                    ).map(mapping).rename("output")
                
                output = pd.Series(index=data.index, name="output", dtype="string")
                
                for cats, out in mapping.items():
                    output.loc[variable.isin(cats)] = out
                
                return output
            
            def create_grid_mapped_variable(
                variable: pd.Series, 
                prev_result_variable: pd.Series, 
                mapping: pd.DataFrame,
            ):
                mapping = (
                    mapping.copy()
                    .stack()
                    .rename_axis(index=["variable", "result"])
                    .rename("output")
                    .reset_index()
                )
                
                df = pd.DataFrame({
                    "variable": variable,
                    "result": prev_result_variable,
                })

                if isinstance(mapping["variable"].dtype, pd.IntervalDtype):
                    df["variable"] = pd.cut(
                        x=df["variable"],
                        bins=mapping["variable"].drop_duplicates(),
                    )
                    
                    df = pd.merge(
                        left=df,
                        right=mapping,
                        how="left",
                        on=["variable", "result"],
                    )
                    
                    return df["output"]
                
                output = pd.Series(index=data.index, name="output", dtype="string")
                
                for group in mapping.itertuples():
                    categories = group.variable
                    prev_result = group.result
                    output_value = group.output
                
                    output.loc[variable.isin(categories) & (prev_result_variable == prev_result)] = output_value
                
                return output
                
        """)

        code = module_import

        if data.read_mode == "CSV":
            code += data_import_csv
        else:
            code += data_import_excel

        code += function_definitions

        for item in code_templates:
            code += f"## Iteration {item['node_id']}\n"
            code += item["template"].safe_substitute(item["substitute"])
            code += "\n"

        return code.strip()

    def to_dict(self):
        return {
            "iterations": {k: v.to_dict() for k, v in self.iterations.items()},
            "connections": self.connections,
            "iteration_metadata": {
                node_id: {
                    "editable": metadata["editable"],
                    "metrics": metadata["metrics"],
                    "scalars_enabled": metadata["scalars_enabled"],
                    "split_view_enabled": metadata["split_view_enabled"],
                    "loss_rate_type": metadata["loss_rate_type"].value,
                    "filters": list(metadata["filters"]),
                }
                for node_id, metadata in self.iteration_metadata.items()
            },
            "selected_node_id": self.selected_node_id,
            "current_node_id": self.current_node_id,
            "current_iter_create_mode": self.current_iter_create_mode,
            "current_iter_create_parent_id": self.current_iter_create_parent_id,
        }

    @classmethod
    def from_dict(cls, dict_data: dict, data: Data):
        graph = cls()
        graph.iterations = {
            k: iteration_from_dict(v, data) for k, v in dict_data["iterations"].items()
        }
        graph.connections = dict_data["connections"]

        graph.iteration_metadata = {
            node_id: {
                "editable": metadata["editable"],
                "metrics": metadata["metrics"],
                "scalars_enabled": metadata["scalars_enabled"],
                "split_view_enabled": metadata["split_view_enabled"],
                "loss_rate_type": LossRateTypes(metadata["loss_rate_type"]),
                "filters": set(metadata["filters"]),
            }
            for node_id, metadata in dict_data.get("iteration_metadata", {}).items()
        }

        graph._selected_node_id = dict_data["selected_node_id"]
        graph._current_node_id = dict_data["current_node_id"]
        graph._current_iter_create_mode = dict_data["current_iter_create_mode"]
        graph._current_iter_create_parent_id = dict_data[
            "current_iter_create_parent_id"
        ]

        return graph


__all__ = [
    "IterationGraph",
]
