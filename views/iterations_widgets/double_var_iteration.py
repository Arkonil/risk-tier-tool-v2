import numpy as np
import pandas as pd
import streamlit as st

from classes.constants import (
    GridColumn,
    Metric,
    MetricTableColumn,
    RTDetCol,
    RangeColumn,
    VariableType,
)
from classes.session import Session
from views.iterations_widgets.dialogs import set_groups, show_metric_selector
from views.iterations_widgets.navigation import show_navigation_buttons
from views.iterations_widgets.single_var_iteration import (
    get_risk_tier_details,
    show_category_editor,
    show_edited_range,
)
from views.variable_selector import show_variable_selector_dialog


def sidebar_options(iteration_id: str):
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    iteration = iteration_graph.iterations[iteration_id]
    iteration_metadata = iteration_graph.iteration_metadata[iteration_id]

    st.button(
        label="Set Variables",
        use_container_width=True,
        icon=":material/data_table:",
        help="Select variables for calculations",
        type="primary",
        on_click=show_variable_selector_dialog,
    )

    st.button(
        label="Set Metrics",
        use_container_width=True,
        icon=":material/functions:",
        help="Set metrics to display in the table",
        on_click=show_metric_selector,
        args=(iteration_id,),
    )

    col1, col2 = st.columns([3, 1])

    col1.button(
        label="Edit Groups",
        use_container_width=True,
        icon=":material/edit:",
        on_click=set_groups,
        args=(iteration_id,),
    )

    def add_new_group():
        iteration.add_group()
        iteration_graph.add_to_calculation_queue(iteration_id)

    col2.button(
        label="",
        use_container_width=True,
        icon=":material/add:",
        key="Add Group",
        on_click=add_new_group,
    )

    scalars_enabled = st.checkbox(
        label="Enable Scalars",
        value=iteration_metadata["scalars_enabled"],
        help="Use Scalars for Annualized Write Off Rates",
    )

    if scalars_enabled != iteration_metadata["scalars_enabled"]:
        iteration_metadata["scalars_enabled"] = scalars_enabled
        st.rerun()

    split_view_enabled = st.checkbox(
        label="Split into columns",
        value=iteration_metadata["split_view_enabled"],
        help="Split the grid view into columns for each metric",
    )

    if split_view_enabled != iteration_metadata["split_view_enabled"]:
        iteration_metadata["split_view_enabled"] = split_view_enabled
        st.rerun()

    editable = st.checkbox(
        label="Editable",
        value=iteration_metadata["editable"],
        help="Editable",
    )

    if editable != iteration_metadata["editable"]:
        iteration_metadata["editable"] = editable
        st.rerun()


def show_grid_editor(iteration_id: str, key: int):
    st.subheader("Editable Grid")

    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    iteration = iteration_graph.iterations[iteration_id]
    iteration_metadata = iteration_graph.iteration_metadata[iteration.id]

    risk_tier_details, _ = get_risk_tier_details(iteration.id, recheck=False)

    grid_columns = risk_tier_details[RTDetCol.RISK_TIER]

    groups = pd.DataFrame({RangeColumn.GROUPS: iteration.groups})
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

    grid_df = grid_index.merge(
        iteration.risk_tier_grid.replace(grid_columns),
        how="left",
        left_index=True,
        right_index=True,
    ).rename(columns=grid_columns)

    column_config = {
        RangeColumn.LOWER_BOUND: st.column_config.NumberColumn(
            label=RangeColumn.LOWER_BOUND, disabled=False, format="plain"
        ),
        RangeColumn.UPPER_BOUND: st.column_config.NumberColumn(
            label=RangeColumn.UPPER_BOUND, disabled=False, format="plain"
        ),
    }

    for column in grid_columns:
        column_config[column] = st.column_config.SelectboxColumn(
            label=column,
            options=risk_tier_details[RTDetCol.RISK_TIER],
            required=True,
            disabled=not iteration_metadata["editable"],
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
    edited_grid = st.data_editor(
        grid_df_styled,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        key=f"editable_grid-{iteration.id}-{key}",
    )

    risk_tier_inv_map = pd.Series(
        risk_tier_details.index.values, index=risk_tier_details[RTDetCol.RISK_TIER]
    )

    with pd.option_context("future.no_silent_downcasting", True):
        edited_grid = edited_grid.replace(risk_tier_inv_map).rename(
            columns=risk_tier_inv_map
        )

    # Check if the edited grid is different from the original risk tier grid
    needs_rerun = False
    for i in edited_grid.index:
        for j in edited_grid.columns:
            if j not in iteration.risk_tier_grid.columns:
                continue

            if iteration.risk_tier_grid.loc[i, j] != edited_grid.loc[i, j]:
                iteration.set_risk_tier_grid(i, j, edited_grid.loc[i, j])
                iteration_graph.add_to_calculation_queue()
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
                iteration_graph.add_to_calculation_queue()
                needs_rerun = True

    if needs_rerun:
        st.rerun()


def calculate_summ_df(iteration_id: str):
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph
    data = session.data

    iteration = iteration_graph.iterations[iteration_id]
    iteration_metadata = iteration_graph.iteration_metadata[iteration_id]

    metrics_df = iteration_metadata["metrics"]
    showing_metrics = metrics_df.sort_values(MetricTableColumn.ORDER).loc[
        metrics_df[MetricTableColumn.SHOWING], MetricTableColumn.METRIC
    ]

    prev_iteration_results = iteration_graph.get_risk_tiers(
        iteration_graph.get_parent(iteration.id)
    )
    curr_iteration_results = iteration.get_group_mapping()

    errors = prev_iteration_results["errors"] + curr_iteration_results["errors"]
    warnings = prev_iteration_results["warnings"] + curr_iteration_results["warnings"]

    summ_df = data.get_summarized_metrics(
        groupby_variable_1=curr_iteration_results["risk_tier_column"].rename(
            GridColumn.GROUP_INDEX
        ),
        groupby_variable_2=prev_iteration_results["risk_tier_column"].rename(
            GridColumn.PREV_RISK_TIER
        ),
        metrics=showing_metrics.to_list(),
    )

    return summ_df, errors, warnings


def show_grid_metric(
    iteration_id: str, metric_summary: pd.Series, show_group_details: bool
):
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    iteration = iteration_graph.iterations[iteration_id]
    iteration_metadata = iteration_graph.iteration_metadata[iteration_id]

    scalars_enabled = iteration_metadata["scalars_enabled"]
    metric_name = metric_summary.name
    risk_tier_details, _ = get_risk_tier_details(iteration.id, recheck=False)

    # Index
    groups = pd.DataFrame({RangeColumn.GROUPS: iteration.groups})
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
        metric_name in (Metric.ANNL_WO_COUNT_PCT, Metric.ANNL_WO_BAL_PCT)
    ):
        ulr_scalar = session.ulr_scalars
        dlr_scalar = session.dlr_scalars

        metric_summary = (
            pd.merge(
                left=metric_summary,
                right=iteration.risk_tier_grid.stack()
                .rename_axis(index=[GridColumn.GROUP_INDEX, GridColumn.PREV_RISK_TIER])
                .rename(GridColumn.CURR_RISK_TIER),
                how="left",
                left_index=True,
                right_index=True,
            )
            .merge(
                right=ulr_scalar.get_risk_scalar_factor(
                    maf=risk_tier_details[RTDetCol.MAF_ULR]
                ).rename(RangeColumn.RISK_SCALAR_FACTOR_ULR),
                how="left",
                left_on=GridColumn.CURR_RISK_TIER,
                right_index=True,
            )
            .merge(
                right=dlr_scalar.get_risk_scalar_factor(
                    maf=risk_tier_details[RTDetCol.MAF_DLR]
                ).rename(RangeColumn.RISK_SCALAR_FACTOR_DLR),
                how="left",
                left_on=GridColumn.CURR_RISK_TIER,
                right_index=True,
            )
        )

        if metric_name == Metric.ANNL_WO_COUNT_PCT:
            metric_summary[Metric.ANNL_WO_COUNT_PCT] = (
                metric_summary[Metric.ANNL_WO_COUNT_PCT]
                * metric_summary[RangeColumn.RISK_SCALAR_FACTOR_ULR]
            )

        if metric_name == Metric.ANNL_WO_BAL_PCT:
            metric_summary[Metric.ANNL_WO_BAL_PCT] = (
                metric_summary[Metric.ANNL_WO_BAL_PCT]
                * metric_summary[RangeColumn.RISK_SCALAR_FACTOR_DLR]
            )

        metric_summary = metric_summary.drop(
            columns=[
                RangeColumn.RISK_SCALAR_FACTOR_ULR,
                RangeColumn.RISK_SCALAR_FACTOR_DLR,
                GridColumn.CURR_RISK_TIER,
            ],
            errors="ignore",
        )

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
            rt_label = iteration.risk_tier_grid.loc[row_index, col_index]

            font_color = risk_tier_details.loc[rt_label, RTDetCol.FONT_COLOR]
            bg_color = risk_tier_details.loc[rt_label, RTDetCol.BG_COLOR]

            metric_summary_grid_styled = metric_summary_grid_styled.set_properties(
                **{
                    "color": font_color,
                    "background-color": bg_color,
                },
                subset=idx[row_index, col_label],
            )

    if metric_name in (Metric.VOLUME, Metric.WO_COUNT):
        metric_summary_grid_styled = metric_summary_grid_styled.format(
            precision=0, thousands=",", subset=risk_tier_details[RTDetCol.RISK_TIER]
        )
    elif metric_name in (Metric.AVG_BAL, Metric.WO_BAL):
        metric_summary_grid_styled = metric_summary_grid_styled.format(
            precision=2, thousands=",", subset=risk_tier_details[RTDetCol.RISK_TIER]
        )
    elif metric_name in (
        Metric.WO_COUNT_PCT,
        Metric.WO_BAL_PCT,
        Metric.ANNL_WO_COUNT_PCT,
        Metric.ANNL_WO_BAL_PCT,
    ):
        metric_summary_grid_styled = metric_summary_grid_styled.format(
            lambda v: f"{v:.2f} %", subset=risk_tier_details[RTDetCol.RISK_TIER]
        )

    return metric_summary_grid_styled


def show_grid_layout(iteration_id: str, metrics: list[Metric]):
    summ_df, errors, warnings = calculate_summ_df(iteration_id=iteration_id)

    if not metrics:
        grid_container, col2 = st.container(key="editor_grid_container"), None
    else:
        grid_container, col2 = st.columns(2)

    status_container = st.container(key="editor_status_container")

    with grid_container:
        show_grid_editor(iteration_id=iteration_id, key=1)

    with status_container:
        if warnings:
            st.warning(
                "Warnings: \n\n" + "\n\n".join(map(lambda msg: f"- {msg}", warnings)),
                icon=":material/warning:",
            )

        if errors:
            st.error(
                "Errors: \n\n" + "\n\n".join(map(lambda msg: f"- {msg}", errors)),
                icon=":material/error:",
            )
            return

    if not metrics:
        return

    column_config = {
        RangeColumn.LOWER_BOUND: st.column_config.NumberColumn(
            label=RangeColumn.LOWER_BOUND, disabled=False, format="plain"
        ),
        RangeColumn.UPPER_BOUND: st.column_config.NumberColumn(
            label=RangeColumn.UPPER_BOUND, disabled=False, format="plain"
        ),
    }

    with col2:
        metric = metrics[0]
        st.subheader(metric)
        st.dataframe(
            show_grid_metric(
                iteration_id=iteration_id,
                metric_summary=summ_df[metric],
                show_group_details=False,
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
            st.subheader(metric)
            st.dataframe(
                show_grid_metric(
                    iteration_id=iteration_id,
                    metric_summary=summ_df[metric],
                    show_group_details=show_details,
                ),
                hide_index=True,
                column_config=column_config,
            )
            show_details = not show_details


def show_liner_layout(iteration_id: str, metrics: list[Metric]):
    summ_df, errors, warnings = calculate_summ_df(iteration_id=iteration_id)

    show_grid_editor(iteration_id=iteration_id, key=1)

    if warnings:
        st.warning(
            "Warnings: \n\n" + "\n\n".join(map(lambda msg: f"- {msg}", warnings)),
            icon=":material/warning:",
        )

    if errors:
        st.error(
            "Errors: \n\n" + "\n\n".join(map(lambda msg: f"- {msg}", errors)),
            icon=":material/error:",
        )
        return

    column_config = {
        RangeColumn.LOWER_BOUND: st.column_config.NumberColumn(
            label=RangeColumn.LOWER_BOUND, disabled=False, format="plain"
        ),
        RangeColumn.UPPER_BOUND: st.column_config.NumberColumn(
            label=RangeColumn.UPPER_BOUND, disabled=False, format="plain"
        ),
    }

    for metric in metrics:
        st.subheader(metric)
        st.dataframe(
            show_grid_metric(
                iteration_id=iteration_id,
                metric_summary=summ_df[metric],
                show_group_details=True,
            ),
            hide_index=True,
            column_config=column_config,
        )


def show_double_var_iteration_widgets():
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    iteration = iteration_graph.iterations[iteration_graph.current_node_id]
    iteration_metadata = iteration_graph.iteration_metadata[iteration.id]

    split_view_enabled = iteration_metadata["split_view_enabled"]
    metrics = iteration_metadata["metrics"]
    showing_metrics = (
        metrics.sort_values(MetricTableColumn.ORDER)
        .loc[metrics[MetricTableColumn.SHOWING], MetricTableColumn.METRIC]
        .to_list()
    )

    # Sidebar
    with st.sidebar:
        sidebar_options(iteration_id=iteration.id)

    # Main Page
    ## Navigation
    show_navigation_buttons()

    st.title(f"Iteration #{iteration.id}")
    st.write(f"##### Variable: `{iteration.variable.name}`")

    ## Risk Tier Details Check
    _, message = get_risk_tier_details(iteration.id, recheck=True)

    if message:
        st.error(message, icon=":material/error:")

    ## Category Editor
    if iteration.var_type == VariableType.CATEGORICAL:
        show_category_editor(iteration.id)

    ## Grids
    if split_view_enabled:
        show_grid_layout(iteration_id=iteration.id, metrics=showing_metrics)
    else:
        show_liner_layout(iteration_id=iteration.id, metrics=showing_metrics)

    with st.expander("Final Risk Tier View"):
        iter_id = iteration.id

        while iter_id is not None:
            st.title(f"Iteration #{iter_id}")
            st.markdown(
                f"##### Variable: `{iteration_graph.iterations[iter_id].variable.name}`"
            )
            show_edited_range(
                iteration_id=iter_id,
                editable=False,
                scalars_enabled=iteration_metadata["scalars_enabled"],
                metrics=showing_metrics,
            )
            iter_id = iteration_graph.get_parent(iter_id)
