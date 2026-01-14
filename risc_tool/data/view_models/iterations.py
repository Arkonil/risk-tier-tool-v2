import typing as t
import warnings

import numpy as np
import pandas as pd
from pandas.io.formats.style import Styler
from pydantic import BaseModel, ConfigDict

from risc_tool.data.models.changes import ChangeTracker
from risc_tool.data.models.enums import (
    IterationType,
    LossRateTypes,
    RangeColumn,
    RSDetCol,
    Signature,
    VariableType,
)
from risc_tool.data.models.types import (
    ChangeIDs,
    FilterID,
    GridEditorViewComponents,
    GridMetricView,
    IterationID,
)
from risc_tool.data.repositories.data import DataRepository
from risc_tool.data.repositories.filter import FilterRepository
from risc_tool.data.repositories.iterations import IterationsRepository
from risc_tool.data.repositories.metric import MetricRepository
from risc_tool.data.repositories.options import OptionRepository
from risc_tool.data.repositories.scalar import ScalarRepository

IteraionView = t.Literal["graph", "view", "create"]


class IteraionViewStatus(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    view: IteraionView = "graph"
    iteration_id: IterationID | None = None


def style_from_dfs(
    styler_data: pd.DataFrame,
    font_df: pd.DataFrame,
    bg_df: pd.DataFrame,
):
    """
    Returns a DataFrame of CSS strings.
    Pandas automatically aligns font_df and bg_df by index/columns.
    """
    assert styler_data.shape == font_df.shape == bg_df.shape, (
        "Dataframes must be the same shape"
    )

    font_df = font_df.copy()
    font_df.columns = styler_data.columns
    font_df.index = styler_data.index

    bg_df = bg_df.copy()
    bg_df.columns = styler_data.columns
    bg_df.index = styler_data.index

    # Vectorized string concatenation
    styles = "color: " + font_df + "; background-color: " + bg_df + ";"
    return styles


class IterationsViewModel(ChangeTracker):
    @property
    def _signature(self) -> Signature:
        return Signature.ITERATION_VIEWMODEL

    def __init__(
        self,
        data_repository: DataRepository,
        iterations_repository: IterationsRepository,
        options_repository: OptionRepository,
        filter_repository: FilterRepository,
        metric_repository: MetricRepository,
        scalar_repository: ScalarRepository,
    ):
        super().__init__(
            dependencies=[
                data_repository,
                iterations_repository,
                options_repository,
                filter_repository,
                metric_repository,
                scalar_repository,
            ]
        )

        self.__data_repository = data_repository
        self.__iterations_repository = iterations_repository
        self.__options_repository = options_repository
        self.__filter_repository = filter_repository
        self.__metric_repository = metric_repository
        self.__scalar_repository = scalar_repository

        self.__view_status = IteraionViewStatus()

        # cache
        self.__editable_range_cache: dict[tuple[IterationID, bool], pd.DataFrame] = {}
        self.__editable_grid_cache: dict[tuple[IterationID, bool], pd.DataFrame] = {}

        # self.load_column = self.data_repository.load_column
        # self.load_columns = self.data_repository.load_columns
        self.get_iteration = self.__iterations_repository.get_iteration
        self.set_metadata = self.__iterations_repository.set_metadata
        self.add_single_var_node = self.__iterations_repository.add_single_var_iteration
        self.add_double_var_node = self.__iterations_repository.add_double_var_iteration
        self.is_rs_details_same = self.__iterations_repository.is_rs_details_same
        self.update_rs_details = self.__iterations_repository.update_rs_details
        self.get_all_groups = self.__iterations_repository.get_all_groups
        self.select_groups = self.__iterations_repository.select_groups
        self.add_new_group = self.__iterations_repository.add_new_group

    def on_dependency_update(self, change_ids: ChangeIDs) -> None:
        if self.current_iteration is None:
            self.set_current_status("graph")

        self.__editable_range_cache.clear()
        self.__editable_grid_cache.clear()

    # View Model
    @property
    def current_status(self):
        if self.__view_status.view == "view":
            if (
                self.__view_status.iteration_id is None
                or self.__view_status.iteration_id
                not in self.__iterations_repository.iterations
            ):
                raise ValueError(
                    f"Iteration {self.__view_status.iteration_id} does not exist."
                )

            return "view", self.__view_status.iteration_id

        return self.__view_status.view, self.__view_status.iteration_id

    @property
    def current_iteration(self):
        current_status = self.current_status
        if current_status[0] != "view":
            return None

        return self.__iterations_repository.iterations.get(current_status[1])

    @property
    def current_iteration_type(self):
        current_iteration = self.current_iteration

        if current_iteration is None:
            return None

        return current_iteration.iter_type

    @property
    def current_iteration_create_mode(self):
        view, iteration_id = self.current_status

        if view != "create":
            warnings.warn("Current view is not 'create'; returning SINGLE by default.")
            return IterationType.SINGLE

        if iteration_id is None:
            return IterationType.SINGLE

        return IterationType.DOUBLE

    @property
    def current_iteration_create_parent_id(self):
        view, iteration_id = self.current_status

        if view != "create":
            warnings.warn("Current view is not 'create'; returning None by default.")
            return None

        return iteration_id

    def set_current_status(
        self,
        view: IteraionView,
        current_iteration_id: IterationID | None = None,
        selected_iteration_id: IterationID | None = None,
        iteration_create_parent_id: IterationID | None = None,
    ):
        if view == "view":
            if current_iteration_id is None:
                raise ValueError("Must provide a current iteration ID")

            self.__view_status.view = "view"
            self.__view_status.iteration_id = current_iteration_id
        elif view == "create":
            self.__view_status.view = "create"
            self.__view_status.iteration_id = iteration_create_parent_id
        elif view == "graph":
            self.__view_status.view = "graph"
            self.__view_status.iteration_id = selected_iteration_id
        else:
            raise ValueError(f"Invalid view type: {view}")

    # Data
    @property
    def sample_loaded(self):
        return self.__data_repository.sample_loaded

    @property
    def common_columns(self):
        return self.__data_repository.common_columns

    def get_sample_variable(self, variable_name: str):
        sample_df = self.__data_repository.get_sample_df(
            list(self.__data_repository.data_sources.keys())
        )

        return sample_df[variable_name]

    # Iterations
    @property
    def iterations(self):
        return self.__iterations_repository.iterations

    @property
    def iteration_graph(self):
        return self.__iterations_repository.graph

    def can_have_child(self, node_id: IterationID) -> bool:
        return (
            self.__iterations_repository.graph.iteration_depth(node_id)
            < self.__options_repository.max_iteration_depth
        )

    def delete_iteration(self, node_id: IterationID):
        self.__iterations_repository.delete_iteration(node_id)
        self.set_current_status("graph")

    def get_risk_segment_details(self, node_id: IterationID):
        return self.__iterations_repository.get_risk_segment_details(node_id)

    def get_iteration_metadata(self, node_id: IterationID):
        return self.__iterations_repository.get_metadata(node_id)

    def get_editable_range(
        self, iteration_id: IterationID, default: bool
    ) -> tuple[Styler, list[str], list[str]]:
        iteration = self.__iterations_repository.get_iteration(iteration_id)

        # 1. Label
        rs_label_df = self.__iterations_repository.get_risk_segment_range(iteration_id)
        font_color_df, bg_color_df = self.__iterations_repository.get_color_range(
            iteration_id
        )

        # 2. Control
        if iteration.iter_type == IterationType.SINGLE:
            control_df = self.__iterations_repository.get_controls(
                iteration_id, default=default
            )
        else:
            control_df = None

        # Metrics
        metric_df, errors, warnings = self.__iterations_repository.get_metric_range(
            iteration_id, default
        )

        # Concatenated df
        if control_df is None:
            final_df = pd.concat([rs_label_df, metric_df], axis=1)
        else:
            final_df = pd.concat([rs_label_df, control_df, metric_df], axis=1)

        self.__editable_range_cache[(iteration_id, default)] = final_df

        final_df_styled = final_df.style.apply(
            style_from_dfs,
            axis=None,
            subset=rs_label_df.columns,
            font_df=font_color_df,
            bg_df=bg_color_df,
        )

        return final_df_styled, errors, warnings

    def get_categorical_iteration_options(self, iteration_id: IterationID) -> list[str]:
        iteration = self.__iterations_repository.get_iteration(iteration_id)

        if iteration.var_type == VariableType.CATEGORICAL:
            return sorted(iteration.variable.cat.categories.astype(str).to_list())

        return []

    def editable_range_edit_handler(
        self, iteration_id: IterationID, default: bool, edited_final_df: pd.DataFrame
    ):
        cached_editable_range = self.__editable_range_cache.get((iteration_id, default))

        if cached_editable_range is None or not edited_final_df.equals(
            cached_editable_range
        ):
            control_df_columns = []

            if RangeColumn.LOWER_BOUND in edited_final_df.columns:
                control_df_columns.append(RangeColumn.LOWER_BOUND)

            if RangeColumn.UPPER_BOUND in edited_final_df.columns:
                control_df_columns.append(RangeColumn.UPPER_BOUND)

            if RangeColumn.CATEGORIES in edited_final_df.columns:
                control_df_columns.append(RangeColumn.CATEGORIES)

            control_df = edited_final_df[control_df_columns]

            self.__iterations_repository.set_controls(iteration_id, control_df)

    def get_editable_grid(
        self, iteration_id: IterationID, default: bool, editable: bool
    ) -> GridEditorViewComponents:
        control_df = self.__iterations_repository.get_controls(iteration_id, default)
        risk_segment_grid = self.__iterations_repository.get_risk_segment_grid(
            iteration_id, default, RSDetCol.RISK_SEGMENT
        )
        font_color_grid = self.__iterations_repository.get_risk_segment_grid(
            iteration_id, default, RSDetCol.FONT_COLOR
        )
        bg_color_grid = self.__iterations_repository.get_risk_segment_grid(
            iteration_id, default, RSDetCol.BG_COLOR
        )

        final_df = pd.concat([control_df, risk_segment_grid], axis=1)
        self.__editable_grid_cache[(iteration_id, default)] = final_df

        displayed_columns = final_df.columns.to_list()

        try:
            lower_bound_pos = 1 + displayed_columns.index(RangeColumn.LOWER_BOUND)
        except ValueError:
            lower_bound_pos = None

        try:
            upper_bound_pos = 1 + displayed_columns.index(RangeColumn.UPPER_BOUND)
        except ValueError:
            upper_bound_pos = None

        try:
            categories_pos = 1 + displayed_columns.index(RangeColumn.CATEGORIES)
        except ValueError:
            categories_pos = None

        risk_segment_grid_col_pos: list[int] = []
        for col in risk_segment_grid.columns:
            risk_segment_grid_col_pos.append(1 + displayed_columns.index(col))

        grid_options = risk_segment_grid.columns.to_list()

        show_prev_iter_details = (
            self.get_iteration_metadata(iteration_id).show_prev_iter_details
            and not editable
            and self.__iterations_repository.graph.iteration_depth(iteration_id) == 2
        )

        styler_subset = risk_segment_grid.columns

        if show_prev_iter_details:
            previous_iteration_id = self.__iterations_repository.graph.get_parent(
                iteration_id
            )

            assert previous_iteration_id is not None

            previous_iteration = self.__iterations_repository.get_iteration(
                previous_iteration_id
            )

            control_df_columns = pd.MultiIndex.from_arrays([
                [" "] * len(control_df.columns),
                control_df.columns.map(str).to_list(),
            ])

            risk_segment_grid_columns = pd.MultiIndex.from_arrays([
                risk_segment_grid.columns.to_list(),
                previous_iteration.get_group_display().to_list(),
            ])

            final_df_columns = control_df_columns.append(risk_segment_grid_columns)

            final_df.columns = final_df_columns
            styler_subset = risk_segment_grid_columns

        final_df_styled = final_df.style.apply(
            style_from_dfs,
            axis=None,
            subset=styler_subset,
            font_df=font_color_grid,
            bg_df=bg_color_grid,
        )

        return {
            "styler": final_df_styled,
            "lower_bound_pos": lower_bound_pos,
            "upper_bound_pos": upper_bound_pos,
            "categories_pos": categories_pos,
            "risk_segment_grid_col_pos": risk_segment_grid_col_pos,
            "grid_options": grid_options,
            "show_prev_iter_details": show_prev_iter_details,
        }

    def editable_grid_edit_handler(
        self, iteration_id: IterationID, default: bool, edited_final_df: pd.DataFrame
    ):
        cached_editable_grid = self.__editable_grid_cache.get((iteration_id, default))

        iteration = self.__iterations_repository.get_iteration(iteration_id)
        risk_segment_details = self.__iterations_repository.get_risk_segment_details(
            iteration_id
        )

        if iteration.var_type == VariableType.NUMERICAL:
            control_df_columns = pd.Index([
                RangeColumn.LOWER_BOUND,
                RangeColumn.UPPER_BOUND,
            ])
        else:
            control_df_columns = pd.Index([RangeColumn.CATEGORIES])

        risk_segment_grid_columns = pd.Index(
            risk_segment_details[RSDetCol.RISK_SEGMENT].to_list()
        )

        final_df_columns = control_df_columns.append(risk_segment_grid_columns)
        edited_final_df.columns = final_df_columns

        if cached_editable_grid is None or not edited_final_df.equals(
            cached_editable_grid
        ):
            edited_control_df = edited_final_df[control_df_columns]
            edited_risk_segment_grid = edited_final_df[risk_segment_grid_columns]

            self.__iterations_repository.set_controls(iteration_id, edited_control_df)
            self.__iterations_repository.set_risk_segment_grid(
                iteration_id, edited_risk_segment_grid
            )

    def get_metric_grids(
        self,
        iteration_id: IterationID,
        default: bool,
        show_controls_idx: t.Literal["all", "alternate"] | list[int],
    ) -> tuple[list[GridMetricView], list[str], list[str]]:
        # Get Data
        metric_summaries, errors, warnings = (
            self.__iterations_repository.get_metric_grids(iteration_id, default)
        )
        font_color_grid = self.__iterations_repository.get_risk_segment_grid(
            iteration_id, default, RSDetCol.FONT_COLOR
        )
        bg_color_grid = self.__iterations_repository.get_risk_segment_grid(
            iteration_id, default, RSDetCol.BG_COLOR
        )

        # Return Empty if no metric is selected
        if len(metric_summaries) == 0:
            return [], errors, warnings

        # Calculate show controls, for each metric df
        if show_controls_idx == "all":
            show_controls = [True] * len(metric_summaries)
        elif show_controls_idx == "alternate":
            show_controls = [i % 2 != 0 for i in range(len(metric_summaries))]
        else:
            show_controls = [
                i in show_controls_idx for i in range(len(metric_summaries))
            ]

        # Setting Control columns
        control_df = self.__iterations_repository.get_controls(iteration_id, default)

        # Setup for previous iteration groups
        show_prev_iter_details = (
            self.get_iteration_metadata(iteration_id).show_prev_iter_details
            and self.__iterations_repository.graph.iteration_depth(iteration_id) == 2
        )

        if show_prev_iter_details:
            # Previous Iter
            previous_iteration_id = self.__iterations_repository.graph.get_parent(
                iteration_id
            )
            assert previous_iteration_id is not None
            previous_iteration = self.__iterations_repository.get_iteration(
                previous_iteration_id
            )

            # Setting columns
            control_df_columns = pd.MultiIndex.from_arrays([
                [" "] * len(control_df.columns),
                control_df.columns.map(str).to_list(),
            ])
            metric_grid_columns = pd.MultiIndex.from_arrays([
                font_color_grid.columns.to_list(),
                previous_iteration.get_group_display().to_list(),
            ])

        else:
            # Setting columns
            control_df_columns = control_df.columns
            metric_grid_columns = font_color_grid.columns

        combined_df_columns = control_df_columns.append(metric_grid_columns)
        styler_subset = metric_grid_columns

        metric_df_views: list[GridMetricView] = []

        for metric_summary, show_control in zip(metric_summaries, show_controls):
            metric_grid = metric_summary["metric_grid"]

            if show_control:
                metric_df = pd.concat([control_df, metric_grid], axis=1)
                metric_df.columns = combined_df_columns
            else:
                metric_df = metric_grid
                metric_df.columns = metric_grid_columns

            metric_df_styled = metric_df.style.apply(
                style_from_dfs,
                axis=None,
                subset=styler_subset,
                font_df=font_color_grid,
                bg_df=bg_color_grid,
            )

            metric_df_views.append(
                GridMetricView(
                    metric_styler=metric_df_styled,
                    metric_name=metric_summary["metric_name"],
                    data_source_names=metric_summary["data_source_names"],
                )
            )

        return metric_df_views, errors, warnings

    # Filters
    def get_filters(self, filter_ids: list[FilterID] | None = None):
        return self.__filter_repository.get_filters(filter_ids)

    # # Metrics
    def metric_variables_selected(self, loss_rate_type: LossRateTypes) -> bool:
        if loss_rate_type == LossRateTypes.ULR:
            return self.__metric_repository.var_unt_bad is not None

        if loss_rate_type == LossRateTypes.DLR:
            return (
                self.__metric_repository.var_dlr_bad is not None
                and self.__metric_repository.var_avg_bal is not None
            )

    # Options
    @property
    def global_risk_segment_details(self):
        return self.__options_repository.risk_segment_details.copy()

    @property
    def max_categorical_unique(self):
        return self.__options_repository.max_categorical_unique

    # Scalars
    def scalar_selected(self, loss_rate_type: LossRateTypes) -> bool:
        scalar = self.__scalar_repository.get_scalar(loss_rate_type)
        return not np.isnan(scalar.portfolio_scalar)
