import itertools
import re
import textwrap
import typing as t

import pandas as pd

from risc_tool.data.models.defaults import DefaultOptions
from risc_tool.data.models.enums import (
    LossRateTypes,
    RangeColumn,
    RSDetCol,
    Signature,
    VariableType,
)
from risc_tool.data.models.iteration import (
    CategoricalDoubleVarIteration,
    CategoricalSingleVarIteration,
    DoubleVarIteration,
    NumericalDoubleVarIteration,
    NumericalSingleVarIteration,
)
from risc_tool.data.models.iteration_graph import IterationGraph
from risc_tool.data.models.iteration_metadata import IterationMetadata
from risc_tool.data.models.iteration_output import IterationOutput
from risc_tool.data.models.types import (
    ChangeIDs,
    FilterID,
    GridMetricSummary,
    IterationID,
    MetricID,
)
from risc_tool.data.repositories.base import BaseRepository
from risc_tool.data.repositories.data import DataRepository
from risc_tool.data.repositories.filter import FilterRepository
from risc_tool.data.repositories.metric import MetricRepository
from risc_tool.data.repositories.options import OptionRepository
from risc_tool.data.repositories.scalar import ScalarRepository
from risc_tool.data.services.auto_band import (
    create_auto_bands,
    does_high_value_implies_high_risk,
)
from risc_tool.utils.wrap_text import TAB

Iteration = (
    NumericalSingleVarIteration
    | NumericalDoubleVarIteration
    | CategoricalSingleVarIteration
    | CategoricalDoubleVarIteration
)


class IterationsRepository(BaseRepository):
    @property
    def _signature(self) -> Signature:
        return Signature.ITERATION_REPOSITORY

    def __init__(
        self,
        data_repository: DataRepository,
        filter_repository: FilterRepository,
        metric_repository: MetricRepository,
        options_repository: OptionRepository,
        scalar_repository: ScalarRepository,
    ) -> None:
        super().__init__(
            dependencies=[
                data_repository,
                filter_repository,
                metric_repository,
                options_repository,
                scalar_repository,
            ]
        )

        # Attributes
        self.iterations: dict[IterationID, Iteration] = {}
        self.graph = IterationGraph()

        # Cached data
        self.__iteration_outputs: dict[
            tuple[IterationID, t.Literal["default", "edited"]], IterationOutput
        ] = {}

        self.__recalculation_required: set[
            tuple[IterationID, t.Literal["default", "edited"]]
        ] = set()

        # Dependencies
        self.__data_repository = data_repository
        self.__filter_repository = filter_repository
        self.__metric_repository = metric_repository
        self.__options_repository = options_repository
        self.__scalar_repository = scalar_repository

    def on_dependency_update(self, change_ids: ChangeIDs) -> None:
        # Data Update
        common_columns = self.__data_repository.common_columns

        for iteration in self.iterations.values():
            if iteration.variable.name not in common_columns:
                iteration.active = False
                continue

            new_variable_series = self.__data_repository.load_column(
                column_name=str(iteration.variable.name),
                column_type=iteration.var_type,
            )

            if (
                iteration.var_type == VariableType.NUMERICAL
                and not pd.api.types.is_numeric_dtype(new_variable_series)
            ):
                iteration.active = False
                continue

            iteration._variable = new_variable_series
            iteration.active = True

        # Clear Cache
        self.__iteration_outputs.clear()
        self.__recalculation_required.clear()

    def iteration_selector_options(self, keep_inactive: bool = False):
        return {
            iter_id: iter_obj.pretty_name
            for iter_id, iter_obj in self.iterations.items()
            if keep_inactive or iter_obj.active
        }

    def get_iteration(self, iteration_id: IterationID) -> Iteration:
        if iteration_id not in self.iterations:
            raise ValueError(f"Iteration {iteration_id} does not exist.")

        return self.iterations[iteration_id]

    def get_root_iteration(self, iteration_id: IterationID):
        root_iter_id = self.graph.get_root_iter_id(iteration_id)
        root_iter = self.get_iteration(root_iter_id)

        if isinstance(
            root_iter, (NumericalSingleVarIteration, CategoricalSingleVarIteration)
        ):
            return root_iter

        raise ValueError(f"Iteration {root_iter_id} is not a root iteration.")

    def get_risk_segment_details(self, iteration_id: IterationID) -> pd.DataFrame:
        root_iter = self.get_root_iteration(iteration_id)
        return root_iter.risk_segment_details

    def get_metadata(self, iteration_id: IterationID) -> IterationMetadata:
        return self.get_iteration(iteration_id).metadata

    def set_metadata(
        self,
        iteration_id: IterationID,
        editable: bool | None = None,
        metric_ids: list[MetricID] | None = None,
        scalars_enabled: bool | None = None,
        split_view_enabled: bool | None = None,
        loss_rate_type: LossRateTypes | None = None,
        filter_ids: list[FilterID] | None = None,
        show_prev_iter_details: bool | None = None,
    ):
        iteration = self.get_iteration(iteration_id)

        # Updating Current Metadata
        iteration.metadata.update(
            editable=editable,
            metric_ids=metric_ids,
            scalars_enabled=scalars_enabled,
            split_view_enabled=split_view_enabled,
            loss_rate_type=loss_rate_type,
            current_filter_ids=filter_ids,
            show_prev_iter_details=show_prev_iter_details,
        )

        if (
            loss_rate_type is not None or filter_ids is not None
        ) and not self.graph.is_root(iteration_id):
            # Getting Root ID
            root_id = self.graph.get_root_iter_id(iteration_id)

            # Updating Metadat to Root ID
            for iter_id in [root_id] + self.graph.get_descendants(root_id):
                self.get_iteration(iter_id).metadata.update(
                    loss_rate_type=loss_rate_type,
                    current_filter_ids=filter_ids,
                )

            self.add_to_calculation_queue(root_id)
        else:
            self.add_to_calculation_queue(iteration_id)

        self.notify_subscribers()

    def delete_iteration(self, iteration_id: IterationID):
        iteration_ids_to_delete = [iteration_id] + self.graph.get_descendants(
            iteration_id
        )

        for iteration_id in iteration_ids_to_delete:
            if iteration_id in self.iterations:
                del self.iterations[iteration_id]

            if (iteration_id, "default") in self.__iteration_outputs:
                del self.__iteration_outputs[(iteration_id, "default")]

            if (iteration_id, "edited") in self.__iteration_outputs:
                del self.__iteration_outputs[(iteration_id, "edited")]

            if iteration_id in self.graph.connections:
                del self.graph.connections[iteration_id]

        for parent, children in self.graph.connections.items():
            self.graph.connections[parent] = [
                child for child in children if child not in iteration_ids_to_delete
            ]

        self.notify_subscribers()

    def add_to_calculation_queue(self, iteration_id: IterationID):
        self.__recalculation_required.add((iteration_id, "default"))
        self.__recalculation_required.add((iteration_id, "edited"))

        for descendant in self.graph.get_descendants(iteration_id):
            self.__recalculation_required.add((descendant, "default"))
            self.__recalculation_required.add((descendant, "edited"))

    def get_risk_segments(
        self, iteration_id: IterationID, default: bool
    ) -> IterationOutput:
        default_or_edited = "default" if default else "edited"

        if (iteration_id, default_or_edited) not in self.__iteration_outputs:
            self.add_to_calculation_queue(iteration_id)

        # No calculation required. Taking from cache.
        if (iteration_id, default_or_edited) not in self.__recalculation_required:
            return self.__iteration_outputs[(iteration_id, default_or_edited)]

        # Calculation Required.
        previous_risk_segments = None

        if not self.graph.is_root(iteration_id) and (
            (parent_id := self.graph.get_parent(iteration_id)) is not None
        ):
            previous_iteration_output = self.get_risk_segments(parent_id, default=False)
            previous_risk_segments = previous_iteration_output.risk_segment_column

        iteration_output = self.iterations[iteration_id].get_risk_segments(
            previous_risk_segments=previous_risk_segments,
            default=default,
        )

        self.__iteration_outputs[(iteration_id, default_or_edited)] = iteration_output
        self.__recalculation_required.remove((iteration_id, default_or_edited))

        return iteration_output

    def get_code_templates(
        self,
        iteration_id: IterationID,
        default: bool,
        language: t.Literal["sas", "python"],
    ):
        node_chain = self.graph.get_ancestors(iteration_id)
        node_chain.append(iteration_id)

        risk_tier_details = self.get_risk_segment_details(iteration_id)
        output_value_mapping = {
            f"GROUP_INDEX_{k}": f'"{v}"'
            for k, v in risk_tier_details[RSDetCol.RISK_SEGMENT].to_dict().items()
        }

        code_templates: list[dict[str, t.Any]] = []
        pattern = re.compile(r"(.+) \((Numerical|Categorical)\)")

        output_variable_name: str = ""

        for i, node in enumerate(node_chain):
            if i < len(node_chain) - 1:
                _default = False
            else:
                _default = default

            iteration = self.iterations[node]
            if match := pattern.match(str(iteration.variable.name)):
                variable_name = match.group(1)
            else:
                variable_name = iteration.variable.name

            previous_iter_out_name = output_variable_name
            output_variable_name = (
                f"Risk_Seg_{node}_{'default' if _default else 'custom'}"
            )

            code_templates.append({
                "node_id": node,
                "template": iteration.generate_sas_code(default=_default)
                if language == "sas"
                else iteration.generate_python_code(default=_default),
                "substitute": {
                    "VARIABLE_NAME": variable_name,
                    "OUTPUT_VARIABLE_NAME": output_variable_name,
                    "PREV_ITER_OUT_NAME": previous_iter_out_name,
                    "MISSING": '""',
                    "DATA": "data",
                }
                | output_value_mapping,
            })

        return code_templates

    def get_sas_code(
        self, iteration_id: IterationID, default: bool, use_macro: bool
    ) -> str:
        code = ""
        code_templates = self.get_code_templates(iteration_id, default, "sas")

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

    def get_python_code(self, iteration_id: IterationID, default: bool) -> str:
        code_templates = self.get_code_templates(iteration_id, default, "python")

        # Module Imports
        module_import_code = textwrap.dedent("""
            # Module Imports
            import numpy as np
            import pandas as pd

        """)

        # Data Import
        data_import_code = textwrap.dedent("""
            # Data Import    
            data_sources = []
        """)

        for i, data_source in enumerate(self.__data_repository.data_sources.values()):
            if data_source.read_mode == "CSV":
                data_import_code += textwrap.dedent(f"""
                    data_{i} = pd.read_csv(
                        filepath_or_buffer="{str(data_source.filepath.absolute())}",
                        delimiter="{data_source.delimiter}",
                        header={data_source.header_row},
                    )
                    data_sources.append(data_{i})
                """)

            elif data_source.read_mode == "EXCEL":
                data_import_code += textwrap.dedent(f"""
                    data_{i} = pd.read_excel(
                        io="{str(data_source.filepath.absolute())}",
                        sheet_name={data_source.sheet_name if data_source.sheet_name.isnumeric() else f'"{data_source.sheet_name}"'},
                        header={data_source.header_row},
                    )
                    data_sources.append(data_{i})
                """)

        data_import_code += textwrap.dedent("""
            data = pd.concat(data_sources, axis=0, keys=data_sources.keys())

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

        code = module_import_code + data_import_code + function_definitions

        for item in code_templates:
            code += f"## Iteration {item['node_id']}\n"
            code += item["template"].safe_substitute(item["substitute"])
            code += "\n"

        return code.strip()

    def add_single_var_iteration(
        self,
        name: str,
        variable_name: str,
        variable_dtype: VariableType,
        selected_segments_mask: pd.Series,
        loss_rate_type: LossRateTypes,
        filter_ids: list[FilterID],
        auto_band: bool,
        use_scalar: bool,
    ) -> NumericalSingleVarIteration | CategoricalSingleVarIteration:
        # Validation
        common_columns = self.__data_repository.common_columns
        if variable_name not in common_columns:
            raise ValueError(f"Variable {variable_name} does not exist.")

        new_iteration_id = IterationID(
            self._get_new_id(current_ids=self.iterations.keys())
        )
        variable = self.__data_repository.load_column(
            column_name=variable_name, column_type=variable_dtype
        )
        risk_segment_details = (
            self.__options_repository.risk_segment_details.loc[selected_segments_mask]
            .reset_index(drop=False)
            .copy()
        )

        if variable_dtype == VariableType.NUMERICAL:
            iteration = NumericalSingleVarIteration(
                uid=new_iteration_id,
                name=name,
                variable=variable,
                risk_segment_details=risk_segment_details,
            )
        elif variable_dtype == VariableType.CATEGORICAL:
            iteration = CategoricalSingleVarIteration(
                uid=new_iteration_id,
                name=name,
                variable=variable,
                risk_segment_details=risk_segment_details,
            )
        else:
            raise ValueError(f"Invalid variable type: {variable_dtype}")

        iteration.metadata = DefaultOptions().default_iteation_metadata.with_changes(
            loss_rate_type=loss_rate_type,
            initial_filter_ids=filter_ids,
            current_filter_ids=filter_ids,
        )

        if auto_band:
            filter_mask = self.__filter_repository.get_mask(filter_ids=filter_ids)
            data_source_mask = self.__data_repository.get_data_source_mask(
                data_source_ids=self.__metric_repository.data_source_ids
            )
            mask = filter_mask & data_source_mask

            var_dlr_bad = None
            var_unt_bad = None
            var_avg_bal = None

            if loss_rate_type == LossRateTypes.DLR:
                var_dlr_bad = self.__data_repository.load_column(
                    column_name=self.__metric_repository.var_dlr_bad,
                    column_type=VariableType.NUMERICAL,
                    data_source_ids=self.__metric_repository.data_source_ids,
                )
                var_avg_bal = self.__data_repository.load_column(
                    column_name=self.__metric_repository.var_avg_bal,
                    column_type=VariableType.NUMERICAL,
                    data_source_ids=self.__metric_repository.data_source_ids,
                )
            else:
                var_unt_bad = self.__data_repository.load_column(
                    column_name=self.__metric_repository.var_unt_bad,
                    column_type=VariableType.NUMERICAL,
                    data_source_ids=self.__metric_repository.data_source_ids,
                )

            if use_scalar:
                dlr_scalar = self.__scalar_repository.get_scalar(LossRateTypes.DLR)
                ulr_scalar = self.__scalar_repository.get_scalar(LossRateTypes.ULR)
            else:
                dlr_scalar = None
                ulr_scalar = None

            groups = create_auto_bands(
                variable=variable,
                mask=mask,
                risk_segment_details=risk_segment_details,
                dlr_scalar=dlr_scalar,
                ulr_scalar=ulr_scalar,
                loss_rate_type=loss_rate_type,
                mob=self.__metric_repository.current_rate_mob,
                var_dlr_bad=var_dlr_bad,
                var_unt_bad=var_unt_bad,
                var_avg_bal=var_avg_bal,
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
            else:
                groups = groups[RangeColumn.GROUPS].rename_axis(index=[""])

            iteration.set_default_groups(groups)

        self.iterations[new_iteration_id] = iteration
        self.add_to_calculation_queue(new_iteration_id)

        self.notify_subscribers()

        return iteration

    def add_double_var_iteration(
        self,
        name: str,
        previous_iteration_id: IterationID,
        variable_name: str,
        variable_dtype: VariableType,
        auto_band: bool,
        use_scalar: bool,
        upgrade_limit: int | None = None,
        downgrade_limit: int | None = None,
        auto_rank_ordering: bool | None = None,
    ) -> NumericalDoubleVarIteration | CategoricalDoubleVarIteration:
        # Validation
        common_columns = self.__data_repository.common_columns
        if variable_name not in common_columns:
            raise ValueError(f"Variable {variable_name} does not exist.")

        if previous_iteration_id not in self.iterations:
            raise ValueError(
                f"Invalid previous iteration id: {previous_iteration_id}. Iteration does not exist."
            )

        new_iteration_id = IterationID(
            self._get_new_id(current_ids=self.iterations.keys())
        )
        variable = self.__data_repository.load_column(
            column_name=variable_name, column_type=variable_dtype
        )
        risk_segment_details = self.get_risk_segment_details(previous_iteration_id)

        if variable_dtype == VariableType.NUMERICAL:
            iteration = NumericalDoubleVarIteration(
                uid=new_iteration_id,
                name=name,
                variable=variable,
                risk_segment_details=risk_segment_details,
            )
        elif variable_dtype == VariableType.CATEGORICAL:
            iteration = CategoricalDoubleVarIteration(
                uid=new_iteration_id,
                name=name,
                variable=variable,
                risk_segment_details=risk_segment_details,
            )
        else:
            raise ValueError(f"Invalid variable type: {variable_dtype}")

        loss_rate_type = self.iterations[previous_iteration_id].metadata.loss_rate_type
        filter_ids = self.iterations[previous_iteration_id].metadata.initial_filter_ids

        iteration.metadata = DefaultOptions().default_iteation_metadata.with_changes(
            loss_rate_type=loss_rate_type,
            initial_filter_ids=filter_ids,
            current_filter_ids=filter_ids,
        )

        if auto_band:
            filter_mask = self.__filter_repository.get_mask(filter_ids=filter_ids)
            data_source_mask = self.__data_repository.get_data_source_mask(
                data_source_ids=self.__metric_repository.data_source_ids
            )
            mask = filter_mask & data_source_mask

            previous_iter_output = self.get_risk_segments(
                previous_iteration_id, default=False
            )

            if previous_iter_output.errors:
                raise ValueError("\n".join(previous_iter_output.errors))

            previous_risk_segments = previous_iter_output.risk_segment_column

            unique_segments = (
                previous_risk_segments.dropna()
                .drop_duplicates(ignore_index=True)
                .sort_values()
            )
            rs_groups: dict[int, pd.Series] = {}

            var_dlr_bad = None
            var_unt_bad = None
            var_avg_bal = None
            hv_imp_hr = None

            if loss_rate_type == LossRateTypes.DLR:
                var_dlr_bad = self.__data_repository.load_column(
                    column_name=self.__metric_repository.var_dlr_bad,
                    column_type=VariableType.NUMERICAL,
                    data_source_ids=self.__metric_repository.data_source_ids,
                )
                var_avg_bal = self.__data_repository.load_column(
                    column_name=self.__metric_repository.var_avg_bal,
                    column_type=VariableType.NUMERICAL,
                    data_source_ids=self.__metric_repository.data_source_ids,
                )

                numerator = var_dlr_bad
                denominator = var_avg_bal
            else:
                var_unt_bad = self.__data_repository.load_column(
                    column_name=self.__metric_repository.var_unt_bad,
                    column_type=VariableType.NUMERICAL,
                    data_source_ids=self.__metric_repository.data_source_ids,
                )

                numerator = var_unt_bad
                denominator = pd.Series(1, index=variable.index)

            if variable_dtype == VariableType.NUMERICAL:
                hv_imp_hr = does_high_value_implies_high_risk(
                    variable=variable,
                    numerator=numerator,
                    denominator=denominator,
                )

            if use_scalar:
                dlr_scalar = self.__scalar_repository.get_scalar(LossRateTypes.DLR)
                ulr_scalar = self.__scalar_repository.get_scalar(LossRateTypes.ULR)
            else:
                dlr_scalar = None
                ulr_scalar = None

            for rs in unique_segments:
                groups: pd.DataFrame = create_auto_bands(
                    variable=variable,
                    mask=(previous_risk_segments == rs) & mask,
                    risk_segment_details=risk_segment_details.iloc[
                        max(0, rs - upgrade_limit) : rs + downgrade_limit + 1
                    ].copy(),
                    dlr_scalar=dlr_scalar,
                    ulr_scalar=ulr_scalar,
                    loss_rate_type=loss_rate_type,
                    mob=self.__metric_repository.current_rate_mob,
                    var_dlr_bad=var_dlr_bad,
                    var_unt_bad=var_unt_bad,
                    var_avg_bal=var_avg_bal,
                    hv_imp_hr=hv_imp_hr,
                )

                if variable_dtype == VariableType.NUMERICAL:
                    with pd.option_context("future.no_silent_downcasting", True):
                        group_series = (
                            groups.replace({  # type: ignore
                                groups.min().min(): variable.min() - 1,  # type: ignore
                                groups.max().max(): variable.max(),  # type: ignore
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
                else:
                    group_series = groups[RangeColumn.GROUPS].rename_axis(index=[""])

                rs_groups[rs] = group_series

            if variable_dtype == VariableType.NUMERICAL:
                cut_points: list[float] = []
                for rs_group in rs_groups.values():
                    for g in rs_group.to_list():
                        cut_points.extend(list(g))

                pairs = list(itertools.pairwise(cut_points))

                if not hv_imp_hr:
                    pairs = list(reversed(pairs))

                group_series: pd.Series = pd.Series(pairs, name=RangeColumn.GROUPS)
                risk_segment_grid = pd.DataFrame(
                    index=group_series.index,
                    columns=risk_segment_details.index,
                )

                for i in risk_segment_grid.index:
                    for j in risk_segment_grid.columns:
                        j = int(j)

                        lower_bound = group_series[i][0]
                        upper_bound = group_series[i][1]

                        rs_group = rs_groups.get(j)
                        if rs_group is None:
                            risk_segment_grid.at[i, j] = j
                            continue

                        for index, (lb, ub) in rs_group.items():
                            if lb <= lower_bound and ub >= upper_bound:
                                risk_segment_grid.at[i, j] = index  # type: ignore
                                break
                        else:
                            risk_segment_grid.at[i, j] = j

                if auto_rank_ordering:
                    risk_segment_grid = risk_segment_grid.cummax(axis=1).cummax(axis=0)

                    i = 1
                    while i < risk_segment_grid.shape[0]:
                        if not risk_segment_grid.iloc[i].equals(
                            risk_segment_grid.iloc[i - 1]
                        ):
                            i += 1
                            continue

                        risk_segment_grid = pd.concat(
                            [
                                risk_segment_grid.iloc[:i],
                                risk_segment_grid.iloc[i + 1 :],
                            ],
                            axis=0,
                        )

                        group_series.iloc[i - 1] = (  # type: ignore
                            group_series.iloc[i - 1][0],  # type: ignore
                            group_series.iloc[i][1],  # type: ignore
                        )

                        group_series = pd.concat(
                            [group_series.iloc[:i], group_series.iloc[i + 1 :]],
                            axis=0,
                        )  # type: ignore

                iteration.set_default_groups(group_series)
                iteration.set_default_risk_segment_grid(risk_segment_grid)
            else:
                # TODO: Add Algorithm for categorical double var optimization
                pass

        self.iterations[new_iteration_id] = iteration
        self.graph.add_child(previous_iteration_id, new_iteration_id)

        self.add_to_calculation_queue(new_iteration_id)

        self.notify_subscribers()

        return iteration

    def is_rs_details_same(
        self, iteration_id: IterationID
    ) -> t.Literal["equal", "unequal", "updatable"]:
        curr_rt_details = self.get_risk_segment_details(iteration_id)
        global_rt_details = self.__options_repository.risk_segment_details.loc[
            curr_rt_details[RSDetCol.ORIG_INDEX]
        ].reset_index(drop=False)

        same_rt = curr_rt_details[RSDetCol.RISK_SEGMENT].equals(
            global_rt_details[RSDetCol.RISK_SEGMENT]
        )
        same_llr = curr_rt_details[RSDetCol.LOWER_RATE].equals(
            global_rt_details[RSDetCol.LOWER_RATE]
        )
        same_ulr = curr_rt_details[RSDetCol.UPPER_RATE].equals(
            global_rt_details[RSDetCol.UPPER_RATE]
        )
        same_maf_dlr = curr_rt_details[RSDetCol.MAF_DLR].equals(
            global_rt_details[RSDetCol.MAF_DLR]
        )
        same_maf_ulr = curr_rt_details[RSDetCol.MAF_ULR].equals(
            global_rt_details[RSDetCol.MAF_ULR]
        )
        same_font_color = curr_rt_details[RSDetCol.FONT_COLOR].equals(
            global_rt_details[RSDetCol.FONT_COLOR]
        )
        same_bg_color = curr_rt_details[RSDetCol.BG_COLOR].equals(
            global_rt_details[RSDetCol.BG_COLOR]
        )

        if same_rt and same_llr and same_ulr:
            if same_maf_dlr and same_maf_ulr and same_font_color and same_bg_color:
                return "equal"
            else:
                return "updatable"
        else:
            return "unequal"

    def update_rs_details(self, iteration_id: IterationID) -> None:
        if self.is_rs_details_same(iteration_id) != "updatable":
            return

        root_iter = self.get_root_iteration(iteration_id)

        curr_rt_details = self.get_risk_segment_details(iteration_id)
        global_rt_details = self.__options_repository.risk_segment_details.loc[
            curr_rt_details[RSDetCol.ORIG_INDEX]
        ].reset_index(drop=False)

        root_iter.update_maf(
            loss_rate_type=LossRateTypes.DLR,
            maf=global_rt_details[RSDetCol.MAF_DLR],
        )

        root_iter.update_maf(
            loss_rate_type=LossRateTypes.ULR,
            maf=global_rt_details[RSDetCol.MAF_ULR],
        )

        root_iter.update_color(
            color_type=RSDetCol.BG_COLOR,
            color=global_rt_details[RSDetCol.BG_COLOR],
        )

        root_iter.update_color(
            color_type=RSDetCol.FONT_COLOR,
            color=global_rt_details[RSDetCol.FONT_COLOR],
        )

        self.add_to_calculation_queue(root_iter.uid)

        self.notify_subscribers()

    def get_all_groups(self, iteration_id: IterationID) -> pd.DataFrame:
        if iteration_id not in self.iterations:
            raise ValueError(f"Iteration {iteration_id} does not exist.")

        iteration = self.iterations[iteration_id]

        groups = pd.DataFrame({
            RangeColumn.GROUPS: iteration._groups,
        })

        if isinstance(iteration, DoubleVarIteration):
            groups[RangeColumn.SELECTED] = iteration._groups_mask

        if iteration.var_type == VariableType.NUMERICAL:
            groups[RangeColumn.LOWER_BOUND] = groups[RangeColumn.GROUPS].map(
                lambda bounds: bounds[0]
            )
            groups[RangeColumn.UPPER_BOUND] = groups[RangeColumn.GROUPS].map(
                lambda bounds: bounds[1]
            )
        else:
            groups[RangeColumn.CATEGORIES] = groups[RangeColumn.GROUPS].map(
                lambda group: list(map(str, group))
            )

        return groups.drop(columns=RangeColumn.GROUPS)

    def select_groups(self, iteration_id: IterationID, selected_indices: list[int]):
        if iteration_id not in self.iterations:
            raise ValueError(f"Iteration {iteration_id} does not exist.")

        iteration = self.iterations[iteration_id]

        if not isinstance(iteration, DoubleVarIteration):
            return

        all_indices = iteration._groups.index.to_list()
        unselected_indices = [
            index for index in all_indices if index not in selected_indices
        ]

        for group_index in selected_indices:
            iteration.add_group(group_index)

        for group_index in unselected_indices:
            iteration.remove_group(group_index)

        self.add_to_calculation_queue(iteration.uid)
        self.notify_subscribers()

    def add_new_group(self, iteration_id: IterationID):
        if iteration_id not in self.iterations:
            raise ValueError(f"Iteration {iteration_id} does not exist.")

        iteration = self.iterations[iteration_id]

        if not isinstance(iteration, DoubleVarIteration):
            return

        iteration.add_group()

        self.add_to_calculation_queue(iteration.uid)
        self.notify_subscribers()

    def get_risk_segment_range(self, iteration_id: IterationID) -> pd.DataFrame:
        risk_segment_details = self.get_risk_segment_details(iteration_id)
        return risk_segment_details[[RSDetCol.RISK_SEGMENT]]

    def get_color_range(
        self, iteration_id: IterationID
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        risk_segment_details = self.get_risk_segment_details(iteration_id)

        font_color_df = risk_segment_details[[RSDetCol.FONT_COLOR]]
        bg_color_df = risk_segment_details[[RSDetCol.BG_COLOR]]

        return font_color_df, bg_color_df

    def get_controls(self, iteration_id: IterationID, default: bool) -> pd.DataFrame:
        iteration = self.get_iteration(iteration_id)

        control_df = pd.DataFrame({
            RangeColumn.GROUPS: iteration.default_groups
            if default
            else iteration.groups,
        })

        if iteration.var_type == VariableType.NUMERICAL:
            control_df[RangeColumn.LOWER_BOUND] = control_df[RangeColumn.GROUPS].map(
                lambda bounds: bounds[0]
            )
            control_df[RangeColumn.UPPER_BOUND] = control_df[RangeColumn.GROUPS].map(
                lambda bounds: bounds[1]
            )
        else:
            control_df[RangeColumn.CATEGORIES] = control_df[RangeColumn.GROUPS].map(
                lambda group: list(map(str, group))
            )

        control_df = control_df.drop(RangeColumn.GROUPS, axis=1)

        return control_df

    def set_controls(self, iteration_id: IterationID, groups: pd.DataFrame):
        if iteration_id not in self.iterations:
            raise ValueError(f"Iteration {iteration_id} does not exist.")

        iteration = self.get_iteration(iteration_id)

        if RangeColumn.LOWER_BOUND in groups.columns:
            lower_bounds = groups[RangeColumn.LOWER_BOUND]
        else:
            lower_bounds = pd.Series(index=groups.index)

        if RangeColumn.UPPER_BOUND in groups.columns:
            upper_bounds = groups[RangeColumn.UPPER_BOUND]
        else:
            upper_bounds = pd.Series(index=groups.index)

        if RangeColumn.CATEGORIES in groups.columns:
            categories = groups[RangeColumn.CATEGORIES]
            categories = (
                categories.map(set)
                .explode()
                .dropna()
                .groupby(level=0)
                .agg(set)
                .reindex(groups.index)
                .apply(lambda x: set() if pd.isna(x) else x)
            )

        else:
            categories = pd.Series(index=groups.index)

        for row_index in iteration.groups.index:
            iteration.set_group(
                group_index=row_index,
                lower_bound=lower_bounds[row_index],
                upper_bound=upper_bounds[row_index],
                categories=categories[row_index],
            )

        self.add_to_calculation_queue(iteration.uid)
        self.notify_subscribers()

    def get_metric_range(self, iteration_id: IterationID, default: bool):
        iteration = self.get_iteration(iteration_id)
        risk_segment_details = self.get_risk_segment_details(iteration_id)

        all_metrics = self.__metric_repository.get_all_metrics()

        valid_metrics = [
            all_metrics[metric_id]
            for metric_id in iteration.metadata.metric_ids
            if metric_id in all_metrics
        ]

        iteration_output = self.get_risk_segments(iteration_id, default=default)

        metric_df = self.__data_repository.get_summarized_metrics(
            groupby_variable_1=iteration_output.risk_segment_column,
            data_filter=self.__filter_repository.get_mask(
                iteration.metadata.current_filter_ids
            ),
            metrics=valid_metrics,
        )

        scalar_df = risk_segment_details[[RSDetCol.MAF_DLR, RSDetCol.MAF_ULR]]
        metric_df = metric_df.loc[scalar_df.index]

        if iteration.metadata.scalars_enabled:
            if MetricID.DLR_BAD_RATE in iteration.metadata.metric_ids:
                scalar = self.__scalar_repository.get_scalar(LossRateTypes.DLR)
                metric_name = all_metrics[MetricID.DLR_BAD_RATE].pretty_name
                metric_df[metric_name] *= scalar.get_risk_scalar_factor(
                    scalar_df[RSDetCol.MAF_DLR]
                )

            if MetricID.UNT_BAD_RATE in iteration.metadata.metric_ids:
                scalar = self.__scalar_repository.get_scalar(LossRateTypes.ULR)
                metric_name = all_metrics[MetricID.UNT_BAD_RATE].pretty_name
                metric_df[metric_name] *= scalar.get_risk_scalar_factor(
                    scalar_df[RSDetCol.MAF_ULR]
                )

        for metric_id in iteration.metadata.metric_ids:
            metric = all_metrics[metric_id]
            metric_name = metric.pretty_name
            metric_df[metric_name] = metric_df[metric_name].map(metric.format)

        return metric_df, iteration_output.errors, iteration_output.warnings

    def get_risk_segment_grid(
        self, iteration_id: IterationID, default: bool, details_column: RSDetCol
    ) -> pd.DataFrame:
        iteration = self.get_iteration(iteration_id)

        if not isinstance(iteration, DoubleVarIteration):
            raise ValueError(
                f"Iteration {iteration_id} is not a double variable iteration."
            )

        risk_segment_grid = (
            iteration.default_risk_segment_grid
            if default
            else iteration.risk_segment_grid
        )
        risk_segment_details = self.get_risk_segment_details(iteration_id)

        value_mapping = risk_segment_details[details_column].to_dict()
        risk_segment_grid = risk_segment_grid.map(lambda v: value_mapping.get(v, v))

        column_mapping = risk_segment_details[RSDetCol.RISK_SEGMENT].to_dict()
        risk_segment_grid.columns = risk_segment_grid.columns.map(
            lambda v: column_mapping.get(v, v)
        )

        return risk_segment_grid

    def set_risk_segment_grid(
        self, iteration_id: IterationID, risk_segment_grid: pd.DataFrame
    ):
        iteration = self.get_iteration(iteration_id)

        if not isinstance(iteration, DoubleVarIteration):
            raise ValueError(
                f"Iteration {iteration_id} is not a double variable iteration."
            )

        risk_segment_details = self.get_risk_segment_details(iteration_id)
        column_mapping: dict[int, str] = risk_segment_details[
            RSDetCol.RISK_SEGMENT
        ].to_dict()
        inv_column_mapping = {v: k for k, v in column_mapping.items()}

        risk_segment_grid = risk_segment_grid.copy().map(
            lambda v: inv_column_mapping.get(v, v)
        )
        risk_segment_grid.columns = risk_segment_grid.columns.map(
            lambda v: inv_column_mapping.get(v, -1)
        )

        risk_segment_grid = risk_segment_grid.reindex(
            index=iteration.risk_segment_grid.index,
            columns=iteration.risk_segment_grid.columns,
        )
        risk_segment_grid = risk_segment_grid.astype(int)

        for row_index in risk_segment_grid.index:
            for col_index in risk_segment_grid.columns:
                value = risk_segment_grid.at[row_index, col_index]
                if pd.isna(value):
                    continue

                try:
                    iteration.set_risk_segment_grid(
                        group_index=row_index,
                        previous_rs_index=int(col_index),
                        value=int(value),  # type: ignore
                    )
                except ValueError:
                    continue

        self.add_to_calculation_queue(iteration.uid)
        self.notify_subscribers()

    def get_metric_grids(self, iteration_id: IterationID, default: bool):
        iteration = self.get_iteration(iteration_id)

        parent_iteration_id = self.graph.get_parent(iteration_id)

        if not isinstance(iteration, DoubleVarIteration) or parent_iteration_id is None:
            raise ValueError(
                f"Iteration {iteration_id} is not a double variable iteration."
            )

        row_output = iteration.get_group_mapping(default=default)
        col_output = self.get_risk_segments(parent_iteration_id, default=False)

        errors = row_output.errors + col_output.errors
        warnings = row_output.warnings + col_output.warnings

        risk_segment_details = self.get_risk_segment_details(iteration_id)
        column_mapping = risk_segment_details[RSDetCol.RISK_SEGMENT].to_dict()

        all_metrics = self.__metric_repository.get_all_metrics()

        metric_df = self.__data_repository.get_summarized_metrics(
            groupby_variable_1=row_output.risk_segment_column.rename(
                "Current Iter Result"
            ),
            groupby_variable_2=col_output.risk_segment_column.rename(
                "Previous Iter Result"
            ),
            data_filter=self.__filter_repository.get_mask(
                iteration.metadata.current_filter_ids
            ),
            metrics=[
                all_metrics[metric_id] for metric_id in iteration.metadata.metric_ids
            ],
        )

        if iteration.metadata.scalars_enabled and (
            (MetricID.DLR_BAD_RATE in iteration.metadata.metric_ids)
            or (MetricID.UNT_BAD_RATE in iteration.metadata.metric_ids)
        ):
            risk_segment_grid = (
                iteration.default_risk_segment_grid
                if default
                else iteration.risk_segment_grid
            ).stack(0)

            if isinstance(risk_segment_grid, pd.DataFrame):
                risk_segment_grid = risk_segment_grid.iloc[:, 0]

            risk_segment_grid = risk_segment_grid.rename("Grid Value")
            scalar_df = pd.merge(
                left=risk_segment_grid,
                right=risk_segment_details[[RSDetCol.MAF_DLR, RSDetCol.MAF_ULR]],
                left_on="Grid Value",
                right_index=True,
                how="left",
            )
            scalar_df = scalar_df.reindex(index=metric_df.index)

            if MetricID.DLR_BAD_RATE in iteration.metadata.metric_ids:
                scalar = self.__scalar_repository.get_scalar(LossRateTypes.DLR)
                metric_name = all_metrics[MetricID.DLR_BAD_RATE].pretty_name
                metric_df[metric_name] *= scalar.get_risk_scalar_factor(
                    scalar_df[RSDetCol.MAF_DLR]
                )

            if MetricID.UNT_BAD_RATE in iteration.metadata.metric_ids:
                scalar = self.__scalar_repository.get_scalar(LossRateTypes.ULR)
                metric_name = all_metrics[MetricID.UNT_BAD_RATE].pretty_name
                metric_df[metric_name] *= scalar.get_risk_scalar_factor(
                    scalar_df[RSDetCol.MAF_ULR]
                )

        metric_df = metric_df.rename(mapper=column_mapping, axis=0, level=1)

        metric_outputs: list[GridMetricSummary] = []

        for metric_id in iteration.metadata.metric_ids:
            metric = all_metrics[metric_id]
            metric_name = metric.pretty_name
            metric_df[metric_name] = metric_df[metric_name].map(metric.format)

            metric_outputs.append(
                GridMetricSummary(
                    metric_grid=metric_df[metric_name].unstack(1),
                    metric_name=metric_name,
                    data_source_names=[
                        self.__data_repository.data_sources[ds_id].label
                        for ds_id in metric.data_source_ids
                    ],
                )
            )

        return metric_outputs, errors, warnings
