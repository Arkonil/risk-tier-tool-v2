from uuid import uuid4

import numpy as np
import pandas as pd
import streamlit as st

from classes.common import SUB_RISK_TIERS, SUB_RT_INV_MAP, Names, color_map, Metric
from classes.iteration_graph import IterationGraph
from classes.session import Session

from views.iterations_widgets.dialogs import set_groups, show_metric_selector
from views.iterations_widgets.navigation import show_navigation_buttons
from views.iterations_widgets.single_var_iteration import show_edited_range, show_category_editor
from views.variable_selector import show_variable_selector_dialog

def show_edited_grid(scalars_enabled: bool, split_view_enabled: bool, metrics: pd.Series) -> str | None:
    session: Session = st.session_state['session']
    iteration_graph: IterationGraph = session.iteration_graph
    data = session.data

    iteration = iteration_graph.current_iteration
    # iteration_metadata = iteration_graph.iteration_metadata[iteration.id]

    if iteration.var_type == "categorical":
        show_category_editor(iteration.id)
        st.divider()

    # Columns
    grid_columns = SUB_RISK_TIERS.loc[iteration_graph.get_parent_tiers(iteration.id)]

    # Index
    groups = pd.DataFrame({Names.GROUPS.value : iteration.groups})
    grid_index = groups.copy()

    if iteration.var_type == "numerical":
        grid_index[Names.LOWER_BOUND.value] = grid_index[Names.GROUPS.value].map(lambda bounds: bounds[0])
        grid_index[Names.UPPER_BOUND.value] = grid_index[Names.GROUPS.value].map(lambda bounds: bounds[1])
        grid_index.drop(columns=[Names.GROUPS.value], inplace=True)
    else:
        grid_index.rename(columns={Names.GROUPS.value: Names.CATEGORIES.value}, inplace=True)

    # Conttoller
    # Create the grid DataFrame
    grid_df = grid_index.merge(
        iteration.risk_tier_grid.loc[:, iteration_graph.get_parent_tiers(iteration.id)].replace(SUB_RISK_TIERS),
        how='left',
        left_index=True,
        right_index=True,
    ).rename(columns=grid_columns)

    column_config = {
        Names.LOWER_BOUND.value: st.column_config.NumberColumn(label=Names.LOWER_BOUND.value, disabled=False, format="plain"),
        Names.UPPER_BOUND.value: st.column_config.NumberColumn(label=Names.UPPER_BOUND.value, disabled=False, format="plain"),
    }

    selectbox_columns = grid_df.columns.to_series().filter(SUB_RISK_TIERS)
    for column in selectbox_columns:
        column_config[column] = st.column_config.SelectboxColumn(
            label=column,
            options=SUB_RISK_TIERS,
            # width="small",
            required=True,
            disabled=False,
        )

    grid_df = grid_df.style \
        .map(lambda v: f'background-color: {color_map[v]};', subset=selectbox_columns)

    col1, col2 = st.columns(2)

    # Grid Editor
    edited_grid = col1.data_editor(
        grid_df,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        key=f"edited_grid_{iteration.id}-{uuid4()}",
    )

    edited_styled_grid = edited_grid \
        .drop(columns=[Names.LOWER_BOUND.value, Names.UPPER_BOUND.value, Names.CATEGORIES.value], errors="ignore") \
        .style.map(lambda v: f'background-color: {color_map[v]};', subset=selectbox_columns)

    # Show the edited grid
    col2.dataframe(edited_styled_grid, hide_index=True, key=f"edited_grid_{iteration.id}_1")

    # Replace the values in the edited grid with the corresponding risk tier values
    with pd.option_context('future.no_silent_downcasting', True):
        edited_grid = edited_grid \
            .replace(SUB_RT_INV_MAP) \
            .infer_objects(copy=False) \
            .rename(columns=SUB_RT_INV_MAP)

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
    if iteration.var_type == "numerical":
        edited_groups = edited_grid[[Names.LOWER_BOUND.value, Names.UPPER_BOUND.value]]

        for index in edited_groups.index:
            prev_bounds = np.array(groups.loc[index, Names.GROUPS.value]).astype(float)
            curent_bounds = np.array(edited_groups.loc[index, [Names.LOWER_BOUND.value, Names.UPPER_BOUND.value]]).astype(float)

            if not np.array_equal(prev_bounds, curent_bounds, equal_nan=True):
                curr_lb = edited_groups.loc[index, Names.LOWER_BOUND.value
    ]
                curr_ub = edited_groups.loc[index, Names.UPPER_BOUND.value]

                iteration.set_group(index, curr_lb, curr_ub)
                iteration_graph.add_to_calculation_queue()
                needs_rerun = True

    if needs_rerun:
        print(f"needs rerun: {needs_rerun}")
        st.rerun()

    previous_risk_tiers, errors, warnings, _ = iteration_graph.get_risk_tiers(iteration_graph.get_parent())

    if errors:
        message = "Errors: \n\n" + "\n\n".join(map(lambda msg: f"- {msg}", errors))
        return message

    if warnings:
        message = "Warnings: \n\n" + "\n\n".join(map(lambda msg: f"- {msg}", warnings))
        st.warning(message, icon=":material/warning:")

    group_indices, errors, warnings, _ = iteration.get_group_mapping()

    if errors:
        message = "Errors: \n\n" + "\n\n".join(map(lambda msg: f"- {msg}", errors))
        return message

    if warnings:
        message = "Warnings: \n\n" + "\n\n".join(map(lambda msg: f"- {msg}", warnings))
        st.warning(message, icon=":material/warning:")

    # metrics_df = iteration_graph.iteration_metadata[iteration_graph.current_node_id]['metrics']
    # showing_metrics = metrics_df.sort_values("order").loc[metrics_df['showing'], 'metric']
    showing_metrics = metrics

    summ_df = data.get_summarized_metrics(
        groupby_variable_1=group_indices.rename(Names.GROUP_INDEX.value),
        groupby_variable_2=previous_risk_tiers.rename(Names.RISK_TIER_VALUE.value),
        metrics=showing_metrics.to_list(),
    )

    # Get a list of names of the metrics that are currently set to 'showing'
    showing_metric_names = [m.name for m in showing_metrics]

    if scalars_enabled and (
        Metric.ANNL_WO_COUNT_PCT.name in showing_metric_names or
        Metric.ANNL_WO_BAL_PCT.name in showing_metric_names
    ):
        ulr_scalar = session.ulr_scalars
        dlr_scalar = session.dlr_scalars

        summ_df = summ_df.merge(
            iteration.risk_tier_grid \
                .stack() \
                .rename_axis(index=[Names.GROUP_INDEX.value, Names.RISK_TIER_VALUE.value]) \
                .rename("New Risk Tier"),
            how='left',
            left_index=True,
            right_index=True,
        ).merge(
            ulr_scalar.risk_scalar_factor.rename("rsf_ulr"),
            how='left',
            left_on="New Risk Tier",
            right_index=True,
        ).merge(
            dlr_scalar.risk_scalar_factor.rename("rsf_dlr"),
            how='left',
            left_on="New Risk Tier",
            right_index=True,
        )

        if Metric.ANNL_WO_COUNT_PCT.value in summ_df.columns:
            summ_df[Metric.ANNL_WO_COUNT_PCT.value] = summ_df[Metric.ANNL_WO_COUNT_PCT.value] * summ_df["rsf_ulr"]

        if Metric.ANNL_WO_BAL_PCT.value in summ_df.columns:
            summ_df[Metric.ANNL_WO_BAL_PCT.value] = summ_df[Metric.ANNL_WO_BAL_PCT.value] * summ_df["rsf_dlr"]

        summ_df = summ_df.drop(columns=["rsf_ulr", "rsf_dlr", "New Risk Tier"], errors="ignore")

    def calculate_grid_of_metric(metric: Metric) -> pd.DataFrame:
        metric_summary =  summ_df[metric.value] \
            .to_frame() \
            .unstack(1) \
            .droplevel(0, axis=1) \
            .rename(columns=SUB_RISK_TIERS)

        metric_summary.index.name = Names.GROUP_INDEX.value

        metric_summary = pd.merge(grid_index, metric_summary, how="left", left_index=True, right_index=True)

        idx = pd.IndexSlice
        metric_summary = metric_summary.style

        for i in metric_summary.data.index:
            for j in metric_summary.data.columns:
                if j not in SUB_RISK_TIERS.values:
                    continue

                color = color_map[SUB_RISK_TIERS.loc[edited_grid.loc[i, SUB_RT_INV_MAP.loc[j]]]]
                metric_summary = metric_summary.set_properties(**{'background-color': color}, subset=idx[i, j])

        return metric_summary

    column_config = {
        Names.LOWER_BOUND.value: st.column_config.NumberColumn(label=Names.LOWER_BOUND.value, disabled=False, format="plain"),
        Names.UPPER_BOUND.value: st.column_config.NumberColumn(label=Names.UPPER_BOUND.value, disabled=False, format="plain"),
    }

    selectbox_columns = previous_risk_tiers.dropna().drop_duplicates().sort_values().map(SUB_RISK_TIERS)

    with st.expander("Grid View", expanded=True):
        columns = []
        if split_view_enabled:
            for _ in range(0, len(showing_metrics), 2):
                columns += st.columns(2)
        else:
            for _ in range(0, len(showing_metrics)):
                columns += st.columns(1)

        for metric in showing_metrics:
            new_column = columns.pop(0)

            metric_summary = calculate_grid_of_metric(metric)

            if metric.value in [Metric.VOLUME.value, Metric.WO_COUNT.value]:
                metric_summary = metric_summary.format(precision=0, thousands=',', subset=selectbox_columns)
            elif metric.value in [Metric.AVG_BAL.value, Metric.WO_BAL.value]:
                metric_summary = metric_summary.format(precision=2, thousands=',', subset=selectbox_columns)
            elif metric.value in [Metric.WO_COUNT_PCT.value, Metric.WO_BAL_PCT.value, Metric.ANNL_WO_COUNT_PCT.value, Metric.ANNL_WO_BAL_PCT.value]:
                metric_summary = metric_summary.format(lambda v: f"{v:.2f} %", subset=selectbox_columns)

            new_column.markdown(f"### {metric.value}")
            new_column.dataframe(metric_summary, hide_index=True, column_config=column_config, use_container_width=True)

def show_double_var_iteration_widgets():
    session: Session = st.session_state['session']
    iteration_graph = session.iteration_graph
    iteration = iteration_graph.iterations[iteration_graph.current_node_id]

    iteration_metadata = iteration_graph.iteration_metadata[iteration.id]
    
    metrics_df = iteration_metadata["metrics"]
    showing_metrics = metrics_df.sort_values("order").loc[metrics_df['showing'], 'metric']

    show_navigation_buttons()

    with st.sidebar:
        if st.button(
            label="Set Variables",
            use_container_width=True,
            icon=":material/data_table:",
            help="Select variables for calculations",
        ):
            show_variable_selector_dialog()

        st.divider()

        col1, col2 = st.columns([3, 1])
        if col1.button("Edit Groups", use_container_width=True, icon=":material/edit:",):
            set_groups(iteration.id)

        if col2.button("", use_container_width=True, icon=":material/add:", key="Add Group"):
            iteration.add_group(iteration.num_groups)
            iteration_graph.add_to_calculation_queue(iteration.id)
            st.rerun()

        if st.button(
            label="Reverse Group Order",
            use_container_width=True,
            icon=":material/swap_vert:",
            help="Reverse the selection of groups",
        ):
            iteration.reverse_group_order()
            iteration_graph.add_to_calculation_queue(iteration.id)
            st.rerun()

        if st.button("Set Metrics", use_container_width=True, icon=":material/functions:",):
            show_metric_selector(metrics_df)

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

    st.title(f"Iteration #{iteration.id}")
    st.write(f"##### Variable: `{iteration.variable.name}`")

    error_message = show_edited_grid(
        scalars_enabled=scalars_enabled,
        split_view_enabled=split_view_enabled,
        metrics=showing_metrics
    )

    if error_message:
        st.error(error_message, icon=":material/error:")
        return

    with st.expander("Final Risk Tier View"):
        iter_id = iteration.id

        while iter_id is not None:
            st.title(f"Iteration #{iter_id}")
            st.markdown(f"##### Variable: `{iteration_graph.iterations[iter_id].variable.name}`")
            show_edited_range(iter_id, editable=False, scalars_enabled=scalars_enabled, metrics=showing_metrics)
            iter_id = iteration_graph.get_parent(iter_id)
