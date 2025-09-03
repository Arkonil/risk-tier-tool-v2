import numpy as np
import pandas as pd
import streamlit as st

from classes.constants import (
    GridColumn,
    RTDetCol,
    RangeColumn,
    VariableType,
    DefaultMetrics,
)
from classes.metric import Metric
from classes.session import Session
from views.iterations_widgets.common import (
    error_and_warning_widget,
    category_editor_widget,
    get_risk_tier_details,
    editable_range_widget,
)
from views.iterations_widgets.dialogs import (
    set_groups_dialog_widget,
    metric_selector_dialog_widget,
)
from views.iterations_widgets.navigation import navigation_widgets
from views.components import variable_selector_dialog_widget


def sidebar_widgets(iteration_id: str):
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph
    fc = session.filter_container

    iteration = iteration_graph.iterations[iteration_id]

    st.button(
        label="Set Variables",
        use_container_width=True,
        icon=":material/data_table:",
        help="Select variables for calculations",
        type="primary",
        on_click=variable_selector_dialog_widget,
    )

    st.button(
        label="Set Metrics",
        use_container_width=True,
        icon=":material/functions:",
        help="Set metrics to display in the table",
        on_click=metric_selector_dialog_widget,
        args=(iteration_id,),
    )

    col1, col2 = st.columns([3, 1])

    col1.button(
        label="Edit Groups",
        use_container_width=True,
        icon=":material/edit:",
        on_click=set_groups_dialog_widget,
        args=(iteration_id,),
    )

    def add_new_group():
        iteration.add_group()
        iteration_graph.add_to_calculation_queue(iteration_id, default=False)

    col2.button(
        label="",
        use_container_width=True,
        icon=":material/add:",
        key="Add Group",
        on_click=add_new_group,
    )

    # Filter Selection
    current_filters = iteration_graph.get_metadata(iteration_id, "filters")

    filter_ids = set(
        st.multiselect(
            label="Filter",
            options=list(fc.filters.keys()),
            default=current_filters,
            format_func=lambda filter_id: fc.filters[filter_id].pretty_name,
            label_visibility="collapsed",
            key=f"filter_selector_{iteration_id}",
            help="Select filters to apply to the iteration",
            placeholder="Select Filters",
        )
    )

    if filter_ids != current_filters:
        iteration_graph.set_metadata(iteration_id, "filters", filter_ids)
        st.rerun()

    # Scalar Toggle
    current_scalars_enabled = iteration_graph.get_metadata(
        iteration_id, "scalars_enabled"
    )

    scalars_enabled = st.checkbox(
        label="Enable Scalars",
        value=current_scalars_enabled,
        help="Use Scalars for Annualized Write Off Rates",
    )

    if scalars_enabled != current_scalars_enabled:
        iteration_graph.set_metadata(iteration_id, "scalars_enabled", scalars_enabled)
        st.rerun()

    # Split View Toggle
    current_split_view_enabled = iteration_graph.get_metadata(
        iteration_id, "split_view_enabled"
    )

    split_view_enabled = st.checkbox(
        label="Split into columns",
        value=current_split_view_enabled,
        help="Split the grid view into columns for each metric",
    )

    if split_view_enabled != current_split_view_enabled:
        iteration_graph.set_metadata(
            iteration_id, "split_view_enabled", split_view_enabled
        )
        st.rerun()

    # Editable Toggle
    current_editable = iteration_graph.get_metadata(iteration_id, "editable")

    editable = st.checkbox(
        label="Editable",
        value=current_editable,
        help="Editable",
    )

    if editable != current_editable:
        iteration_graph.set_metadata(iteration_id, "editable", editable)
        st.rerun()


def grid_editor_widget(iteration_id: str, key: int, default: bool = False):
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    iteration = iteration_graph.iterations[iteration_id]

    if default:
        st.markdown("##### Default Grid")
        iteration_groups = iteration.default_groups
        iteration_risk_tier_grid = iteration.default_risk_tier_grid
    else:
        st.markdown("##### Editable Grid")
        iteration_groups = iteration.groups
        iteration_risk_tier_grid = iteration.risk_tier_grid

    risk_tier_details, _ = get_risk_tier_details(iteration.id, recheck=False)

    grid_columns = risk_tier_details[RTDetCol.RISK_TIER]

    groups = pd.DataFrame({RangeColumn.GROUPS: iteration_groups})
    grid_index = groups.copy()

    if iteration.var_type == VariableType.NUMERICAL:
        grid_index[RangeColumn.LOWER_BOUND] = grid_index[RangeColumn.GROUPS].map(
            lambda bounds: bounds[0]
        )
        grid_index[RangeColumn.UPPER_BOUND] = grid_index[RangeColumn.GROUPS].map(
            lambda bounds: bounds[1]
        )
        grid_index.drop(columns=[RangeColumn.GROUPS], inplace=True)
    else:
        grid_index.rename(
            columns={RangeColumn.GROUPS: RangeColumn.CATEGORIES}, inplace=True
        )

    with pd.option_context("future.no_silent_downcasting", True):
        grid_df = grid_index.merge(
            iteration_risk_tier_grid.replace(grid_columns).infer_objects(copy=False),
            how="left",
            left_index=True,
            right_index=True,
        ).rename(columns=grid_columns)

    column_config = {
        RangeColumn.LOWER_BOUND: st.column_config.NumberColumn(
            label=RangeColumn.LOWER_BOUND, disabled=default, format="compact"
        ),
        RangeColumn.UPPER_BOUND: st.column_config.NumberColumn(
            label=RangeColumn.UPPER_BOUND, disabled=default, format="compact"
        ),
    }

    current_editable_toggle = iteration_graph.get_metadata(iteration_id, "editable")

    for column in grid_columns:
        column_config[column] = st.column_config.SelectboxColumn(
            label=column,
            options=risk_tier_details[RTDetCol.RISK_TIER],
            required=True,
            disabled=(not current_editable_toggle) or default,
        )

    idx = pd.IndexSlice
    grid_df_styled = grid_df.style

    for row_index in grid_df.index:
        for col_index in grid_columns:
            rt_label = grid_df.loc[row_index, col_index]

            font_color = risk_tier_details.loc[
                risk_tier_details[RTDetCol.RISK_TIER] == rt_label, RTDetCol.FONT_COLOR
            ].values[0]
            bg_color = risk_tier_details.loc[
                risk_tier_details[RTDetCol.RISK_TIER] == rt_label, RTDetCol.BG_COLOR
            ].values[0]

            grid_df_styled = grid_df_styled.set_properties(
                **{
                    "color": font_color,
                    "background-color": bg_color,
                },
                subset=idx[row_index, col_index],
            )

    # Grid Editor
    key = f"{'Default' if default else 'Editable'} Grid-{iteration.id}-{key}"
    edited_grid = st.data_editor(
        grid_df_styled,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        key=key,
    )

    if default:
        return

    risk_tier_inv_map = pd.Series(
        risk_tier_details.index.values, index=risk_tier_details[RTDetCol.RISK_TIER]
    )

    with pd.option_context("future.no_silent_downcasting", True):
        edited_grid = (
            edited_grid.replace(risk_tier_inv_map)
            .infer_objects(copy=False)
            .rename(columns=risk_tier_inv_map)
        )

    # Check if the edited grid is different from the original risk tier grid
    needs_rerun = False
    for i in edited_grid.index:
        for j in edited_grid.columns:
            if j not in iteration_risk_tier_grid.columns:
                continue

            if iteration_risk_tier_grid.loc[i, j] != edited_grid.loc[i, j]:
                iteration.set_risk_tier_grid(i, j, edited_grid.loc[i, j])
                iteration_graph.add_to_calculation_queue(iteration_id, default=False)
                needs_rerun = True

    # Check if the edited groups are different from the original groups
    if iteration.var_type == VariableType.NUMERICAL:
        edited_groups = edited_grid[[RangeColumn.LOWER_BOUND, RangeColumn.UPPER_BOUND]]

        for index in edited_groups.index:
            prev_bounds = np.array(groups.loc[index, RangeColumn.GROUPS]).astype(float)
            curent_bounds = np.array(
                edited_groups.loc[
                    index, [RangeColumn.LOWER_BOUND, RangeColumn.UPPER_BOUND]
                ]
            ).astype(float)

            if not np.array_equal(prev_bounds, curent_bounds, equal_nan=True):
                curr_lb = edited_groups.loc[index, RangeColumn.LOWER_BOUND]
                curr_ub = edited_groups.loc[index, RangeColumn.UPPER_BOUND]

                iteration.set_group(index, curr_lb, curr_ub)
                iteration_graph.add_to_calculation_queue(iteration_id, default=False)
                needs_rerun = True

    if needs_rerun:
        st.rerun()


def calculate_summ_df(iteration_id: str, default: bool = False):
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph
    data = session.data
    fc = session.filter_container
    all_metrics = session.get_all_metrics()

    iteration = iteration_graph.iterations[iteration_id]

    metric_names = iteration_graph.get_metadata(iteration.id, "metrics")
    metric_names = [
        metric_name for metric_name in metric_names if metric_name in all_metrics
    ]
    metrics = [all_metrics[metric_name] for metric_name in metric_names]

    prev_iteration_results = iteration_graph.get_risk_tiers(
        iteration_graph.get_parent(iteration.id), default=False
    )
    curr_iteration_results = iteration.get_group_mapping(default=default)

    errors = prev_iteration_results["errors"] + curr_iteration_results["errors"]
    warnings = prev_iteration_results["warnings"] + curr_iteration_results["warnings"]

    summ_df = data.get_summarized_metrics(
        groupby_variable_1=curr_iteration_results["risk_tier_column"].rename(
            GridColumn.GROUP_INDEX
        ),
        groupby_variable_2=prev_iteration_results["risk_tier_column"].rename(
            GridColumn.PREV_RISK_TIER
        ),
        data_filter=fc.get_mask(
            iteration_graph.get_metadata(iteration.id, "filters"),
            index=data.df.index,
        ),
        metrics=metrics,
    )

    return summ_df, errors, warnings


def grid_metric_widget(
    iteration_id: str,
    metric_summary: pd.Series,
    metric_format: str,
    show_group_details: bool,
    default: bool = False,
):
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    iteration = iteration_graph.iterations[iteration_id]

    scalars_enabled = iteration_graph.get_metadata(iteration_id, "scalars_enabled")
    metric_name = metric_summary.name
    risk_tier_details, _ = get_risk_tier_details(iteration.id, recheck=False)

    if default:
        iteration_groups = iteration.default_groups
        iteration_risk_tier_grid = iteration.default_risk_tier_grid
    else:
        iteration_groups = iteration.groups
        iteration_risk_tier_grid = iteration.risk_tier_grid

    # Index
    groups = pd.DataFrame({RangeColumn.GROUPS: iteration_groups})
    grid_index = groups.copy()

    if show_group_details:
        if iteration.var_type == VariableType.NUMERICAL:
            grid_index[RangeColumn.LOWER_BOUND] = grid_index[RangeColumn.GROUPS].map(
                lambda bounds: bounds[0]
            )
            grid_index[RangeColumn.UPPER_BOUND] = grid_index[RangeColumn.GROUPS].map(
                lambda bounds: bounds[1]
            )
            grid_index.drop(columns=[RangeColumn.GROUPS], inplace=True)
        else:
            grid_index.rename(
                columns={RangeColumn.GROUPS: RangeColumn.CATEGORIES}, inplace=True
            )

    grid_index.rename_axis(index=GridColumn.GROUP_INDEX, inplace=True)

    if scalars_enabled and (
        metric_name in (DefaultMetrics.UNT_BAD_RATE, DefaultMetrics.DLR_BAD_RATE)
    ):
        if metric_name == DefaultMetrics.UNT_BAD_RATE:
            scalar = session.ulr_scalars
            maf = risk_tier_details[RTDetCol.MAF_ULR]
            rsf_name = RangeColumn.RISK_SCALAR_FACTOR_ULR
        else:
            scalar = session.dlr_scalars
            maf = risk_tier_details[RTDetCol.MAF_DLR]
            rsf_name = RangeColumn.RISK_SCALAR_FACTOR_DLR

        metric_summary = pd.merge(
            left=metric_summary,
            right=iteration_risk_tier_grid.stack()
            .rename_axis(index=[GridColumn.GROUP_INDEX, GridColumn.PREV_RISK_TIER])
            .rename(GridColumn.CURR_RISK_TIER),
            how="left",
            left_index=True,
            right_index=True,
        ).merge(
            right=scalar.get_risk_scalar_factor(maf=maf).rename(rsf_name),
            how="left",
            left_on=GridColumn.CURR_RISK_TIER,
            right_index=True,
        )

        metric_summary[metric_name] *= metric_summary[rsf_name]

        metric_summary = metric_summary[metric_name]

    metric_summary_grid = (
        metric_summary.to_frame()
        .unstack(1)
        .droplevel(0, axis=1)
        .rename(columns=risk_tier_details[RTDetCol.RISK_TIER])
    )

    metric_summary_grid = grid_index.merge(
        metric_summary_grid,
        how="left",
        left_index=True,
        right_index=True,
    )

    metric_summary_grid = metric_summary_grid.drop(
        columns=[RangeColumn.GROUPS], errors="ignore"
    )

    idx = pd.IndexSlice
    metric_summary_grid_styled = metric_summary_grid.style

    for row_index in metric_summary_grid.index:
        for col_label in metric_summary_grid.columns:
            if col_label not in risk_tier_details[RTDetCol.RISK_TIER].to_list():
                continue

            col_index = risk_tier_details.loc[
                risk_tier_details[RTDetCol.RISK_TIER] == col_label
            ].index[0]
            rt_label = iteration_risk_tier_grid.loc[row_index, col_index]

            font_color = risk_tier_details.loc[rt_label, RTDetCol.FONT_COLOR]
            bg_color = risk_tier_details.loc[rt_label, RTDetCol.BG_COLOR]

            metric_summary_grid_styled = metric_summary_grid_styled.set_properties(
                **{
                    "color": font_color,
                    "background-color": bg_color,
                },
                subset=idx[row_index, col_label],
            ).format(metric_format, subset=idx[row_index, col_label])

    return metric_summary_grid_styled


def grid_layout_widget(
    iteration_id: str, metrics: list[Metric], default: bool, key: int = 0
):
    summ_df, errors, warnings = calculate_summ_df(
        iteration_id=iteration_id, default=default
    )

    if not metrics:
        grid_container, col2 = st.container(key=f"editor_grid_container-{key}"), None
    else:
        grid_container, col2 = st.columns(2)

    status_container = st.container(key=f"editor_status_container-{key}")

    with grid_container:
        grid_editor_widget(iteration_id=iteration_id, key=key, default=default)

    with status_container:
        error_and_warning_widget(errors, warnings)

    if not metrics:
        return

    column_config = {
        RangeColumn.LOWER_BOUND: st.column_config.NumberColumn(
            label=RangeColumn.LOWER_BOUND, disabled=False, format="compact"
        ),
        RangeColumn.UPPER_BOUND: st.column_config.NumberColumn(
            label=RangeColumn.UPPER_BOUND, disabled=False, format="compact"
        ),
    }

    with col2:
        metric = metrics[0]
        st.markdown(f"##### {metric.name}")
        st.dataframe(
            grid_metric_widget(
                iteration_id=iteration_id,
                metric_summary=summ_df[metric.name],
                metric_format=metric.format,
                show_group_details=False,
                default=default,
            ),
            hide_index=True,
            column_config=column_config,
        )

    columns = []
    row_count = (len(metrics[1:]) + len(metrics[1:]) % 2) // 2

    for _ in range(row_count):
        columns.extend(st.columns(2))

    show_details = True

    for metric in metrics[1:]:
        with columns.pop(0):
            st.markdown(f"##### {metric.name}")
            st.dataframe(
                grid_metric_widget(
                    iteration_id=iteration_id,
                    metric_summary=summ_df[metric.name],
                    metric_format=metric.format,
                    show_group_details=show_details,
                    default=default,
                ),
                hide_index=True,
                column_config=column_config,
            )
            show_details = not show_details


def liner_layout_widget(iteration_id: str, metrics: list[Metric], key: int = 0):
    summ_df, errors, warnings = calculate_summ_df(
        iteration_id=iteration_id, default=False
    )

    grid_editor_widget(iteration_id=iteration_id, key=key, default=False)

    error_and_warning_widget(errors, warnings)

    column_config = {
        RangeColumn.LOWER_BOUND: st.column_config.NumberColumn(
            label=RangeColumn.LOWER_BOUND, disabled=False, format="compact"
        ),
        RangeColumn.UPPER_BOUND: st.column_config.NumberColumn(
            label=RangeColumn.UPPER_BOUND, disabled=False, format="compact"
        ),
    }

    for metric in metrics:
        st.markdown(f"##### {metric.name}")
        st.dataframe(
            grid_metric_widget(
                iteration_id=iteration_id,
                metric_summary=summ_df[metric.name],
                metric_format=metric.format,
                show_group_details=True,
                default=False,
            ),
            hide_index=True,
            column_config=column_config,
        )


def double_var_iteration_widget():
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph
    all_metrics = session.get_all_metrics()

    iteration = iteration_graph.current_iteration

    split_view_enabled = iteration_graph.get_metadata(
        iteration.id, "split_view_enabled"
    )
    metric_names = iteration_graph.get_metadata(iteration.id, "metrics")
    metric_names = [
        metric_name for metric_name in metric_names if metric_name in all_metrics
    ]
    metrics = [all_metrics[metric_name] for metric_name in metric_names]
    scalars_enabled = iteration_graph.get_metadata(iteration.id, "scalars_enabled")

    # Sidebar
    with st.sidebar:
        sidebar_widgets(iteration_id=iteration.id)

    # Main Page
    ## Navigation
    navigation_widgets()

    st.title(f"Iteration #{iteration.id}")
    st.write(f"##### Variable: `{iteration.variable.name}`")

    ## Risk Tier Details Check
    _, message = get_risk_tier_details(iteration.id, recheck=True)

    if message:
        st.error(message, icon=":material/error:")

    ## Default View
    st.markdown("## Default View")
    grid_layout_widget(
        iteration_id=iteration.id, metrics=metrics[:1], default=True, key=0
    )

    st.divider()

    st.markdown("## Editable View")
    ## Category Editor
    if iteration.var_type == VariableType.CATEGORICAL:
        category_editor_widget(iteration.id)

    ## Grids
    if split_view_enabled:
        grid_layout_widget(
            iteration_id=iteration.id, metrics=metrics, default=False, key=1
        )
    else:
        liner_layout_widget(iteration_id=iteration.id, metrics=metrics, key=2)

    iter_id = iteration.id

    with st.container(border=True):
        st.markdown("## Previous Iterations")

        while iter_id is not None:
            st.markdown(f"#### Iteration #{iter_id}")
            st.markdown(
                f"###### Variable: `{iteration_graph.iterations[iter_id].variable.name}`"
            )
            editable_range_widget(
                iteration_id=iter_id,
                editable=False,
                scalars_enabled=scalars_enabled,
                metric_names=metric_names,
                default=False,
                filter_ids=iteration_graph.get_metadata(iteration.id, "filters"),
            )
            iter_id = iteration_graph.get_parent(iter_id)


__all__ = ["double_var_iteration_widget"]
