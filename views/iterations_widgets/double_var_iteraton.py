import numpy as np
import pandas as pd
import streamlit as st

from classes.common import SUB_RISK_TIERS, SUB_RT_INV_MAP, Names, color_map
from classes.iteration_graph import IterationGraph
from classes.session import Session

from views.iterations_widgets.dialogs import set_groups, show_metric_selector
from views.iterations_widgets.navigation import show_navigation_buttons
from views.iterations_widgets.single_var_iteration import show_edited_range
from views.variable_selector import show_variable_selector_dialog

def show_edited_grid(split_view: bool):
    session: Session = st.session_state['session']
    iteration_graph: IterationGraph = session.iteration_graph
    data = session.data

    iteration = iteration_graph.current_iteration
    iteration_type = iteration_graph.get_iteration_type(iteration.id)

    groups = iteration.groups
    groups = pd.DataFrame({Names.GROUPS : groups})

    if iteration_type == "categorical":
        with st.expander("Edit Groups", expanded=True):
            column = st.columns(min(5, len(groups)))

            all_categories = set(iteration.variable.cat.categories)
            assigned_categories = set(groups[Names.GROUPS].explode())
            unassigned_categories = all_categories - assigned_categories

            for i, row in enumerate(groups.itertuples()):
                group_index = row.Index
                group = set(row[1])

                with column[i % len(column)]:
                    new_group = set(st.multiselect(
                        label=f"Group {group_index + 1}",
                        options=sorted(list(group.union(unassigned_categories))),
                        default=sorted(list(group),
                        # disabled=True,
                    )))

                    if group != new_group:
                        iteration.set_group(group_index, new_group)
                        iteration_graph.add_to_calculation_queue()
                        st.rerun()

        st.divider()

    # Columns
    grid_columns = SUB_RISK_TIERS.loc[iteration_graph.get_parent_tiers(iteration.id)]
    # st.write(grid_columns)

    # Index
    grid_index = groups.copy()

    if iteration_type == "numerical":
        grid_index[Names.LOWER_BOUND] = grid_index[Names.GROUPS].map(lambda bounds: bounds[0])
        grid_index[Names.UPPER_BOUND] = grid_index[Names.GROUPS].map(lambda bounds: bounds[1])
        grid_index.drop(columns=[Names.GROUPS], inplace=True)
    else:
        grid_index.rename(columns={Names.GROUPS: Names.CATEGORIES}, inplace=True)
    # st.write(grid_index)

    # Conttoller
    grid_df = grid_index.merge(
        iteration.risk_tier_grid.loc[:, iteration_graph.get_parent_tiers(iteration.id)].replace(SUB_RISK_TIERS),
        how='left',
        left_index=True,
        right_index=True,
    ).rename(columns=grid_columns)

    column_config = {
        Names.LOWER_BOUND: st.column_config.NumberColumn(label=Names.LOWER_BOUND, disabled=False, format="plain"),
        Names.UPPER_BOUND: st.column_config.NumberColumn(label=Names.UPPER_BOUND, disabled=False, format="plain"),
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

    edited_grid = col1.data_editor(
        grid_df,
        column_config=column_config,
        hide_index=True,
        use_container_width=True
    )

    edited_styled_grid = edited_grid \
        .drop(columns=[Names.LOWER_BOUND, Names.UPPER_BOUND, Names.CATEGORIES], errors="ignore") \
        .style.map(lambda v: f'background-color: {color_map[v]};', subset=selectbox_columns)

    col2.dataframe(edited_styled_grid, hide_index=True)

    with pd.option_context('future.no_silent_downcasting', True):
        edited_grid = edited_grid \
            .replace(SUB_RT_INV_MAP) \
            .infer_objects(copy=False) \
            .rename(columns=SUB_RT_INV_MAP)

    needs_rerun = False
    for i in edited_grid.index:
        for j in edited_grid.columns:
            if j not in iteration.risk_tier_grid.columns:
                continue

            if iteration.risk_tier_grid.loc[i, j] != edited_grid.loc[i, j]:
                iteration.set_risk_tier_grid(i, j, edited_grid.loc[i, j])
                iteration_graph.add_to_calculation_queue()
                needs_rerun = True

    if iteration_type == "numerical":

        edited_groups = edited_grid[[Names.LOWER_BOUND, Names.UPPER_BOUND]]

        for index in edited_groups.index:
            prev_bounds = np.array(groups.loc[index, Names.GROUPS]).astype(float)
            curent_bounds = np.array(edited_groups.loc[index, [Names.LOWER_BOUND, Names.UPPER_BOUND]]).astype(float)

            if not np.array_equal(prev_bounds, curent_bounds, equal_nan=True):
                curr_lb = edited_groups.loc[index, Names.LOWER_BOUND]
                curr_ub = edited_groups.loc[index, Names.UPPER_BOUND]

                iteration.set_group(index, curr_lb, curr_ub)
                iteration_graph.add_to_calculation_queue()
                needs_rerun = True

    if needs_rerun:
        print(f"needs rerun: {needs_rerun}")
        st.rerun()

    previous_risk_tiers, errors, warnings, _ = iteration_graph.get_risk_tiers(iteration_graph.get_parent())

    if errors:
        message = "Errors: \n\n" + "\n\n".join(map(lambda msg: f"- {msg}", errors))
        # st.error(message, icon=":material/error:")
        return message

    if warnings:
        message = "Warnings: \n\n" + "\n\n".join(map(lambda msg: f"- {msg}", warnings))
        st.warning(message, icon=":material/warning:")

    group_indices, errors, warnings, _ = iteration.get_group_mapping()

    if errors:
        message = "Errors: \n\n" + "\n\n".join(map(lambda msg: f"- {msg}", errors))
        # st.error(message, icon=":material/error:")
        return message

    if warnings:
        message = "Warnings: \n\n" + "\n\n".join(map(lambda msg: f"- {msg}", warnings))
        st.warning(message, icon=":material/warning:")


    base_df = pd.DataFrame({
        Names.RISK_TIER_VALUE: previous_risk_tiers,
        Names.GROUP_INDEX: group_indices,
        Names.VOLUME: 1,
        Names.AVG_BAL: data.load_column(data.var_avg_bal),
        Names.WO_BAL: data.load_column(data.var_dlr_wrt_off),
        Names.WO_COUNT: data.load_column(data.var_unt_wrt_off),
    })

    summ_df = base_df.groupby([Names.RISK_TIER_VALUE, Names.GROUP_INDEX]).sum()
    summ_df[Names.WO_BAL_PCT] = 100 * summ_df[Names.WO_BAL] / summ_df[Names.AVG_BAL]
    summ_df[Names.WO_COUNT_PCT] = 100 * summ_df[Names.WO_COUNT] / summ_df[Names.VOLUME]

    def calculate_grid_of_metric(metric: str) -> pd.DataFrame:
        metric_summary =  summ_df[metric] \
            .to_frame() \
            .unstack(0) \
            .droplevel(0, axis=1) \
            .rename(columns=SUB_RISK_TIERS)

        metric_summary.index.name = Names.GROUP_INDEX

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

    metrics_df = iteration_graph.iteration_metadata[iteration_graph.current_node_id]['metrics']

    column_config = {
        Names.LOWER_BOUND: st.column_config.NumberColumn(label=Names.LOWER_BOUND, disabled=False, format="plain"),
        Names.UPPER_BOUND: st.column_config.NumberColumn(label=Names.UPPER_BOUND, disabled=False, format="plain"),
    }

    showing_metrics = metrics_df.sort_values("order").loc[metrics_df['showing'], 'metric']

    with st.expander("Grid View"):
        columns = []
        if split_view:
            for _ in range(0, len(showing_metrics), 2):
                columns += st.columns(2)
        else:
            for _ in range(0, len(showing_metrics)):
                columns += st.columns(1)

        for metric in showing_metrics:
            new_column = columns.pop(0)

            if metric == Names.VOLUME:
                volume_summary = calculate_grid_of_metric(Names.VOLUME)
                volume_summary = volume_summary.format(precision=0, thousands=',', subset=selectbox_columns)

                new_column.markdown(f"### {Names.VOLUME}")
                new_column.dataframe(volume_summary, hide_index=True, column_config=column_config, use_container_width=True)
            elif metric == Names.AVG_BAL:
                avg_bal_summary = calculate_grid_of_metric(Names.AVG_BAL)
                avg_bal_summary = avg_bal_summary.format(precision=2, thousands=',', subset=selectbox_columns)

                new_column.markdown(f"### {Names.AVG_BAL}")
                new_column.dataframe(avg_bal_summary, hide_index=True, column_config=column_config, use_container_width=True)
            elif metric == Names.WO_COUNT:
                wo_unt_summary = calculate_grid_of_metric(Names.WO_COUNT)
                wo_unt_summary = wo_unt_summary.format(precision=0, thousands=',', subset=selectbox_columns)

                new_column.markdown(f"### {Names.WO_COUNT}")
                new_column.dataframe(wo_unt_summary, hide_index=True, column_config=column_config, use_container_width=True)
            elif metric == Names.WO_BAL:
                wo_bal_summary = calculate_grid_of_metric(Names.WO_BAL)
                wo_bal_summary = wo_bal_summary.format(precision=2, thousands=',', subset=selectbox_columns)

                new_column.markdown(f"### {Names.WO_BAL}")
                new_column.dataframe(wo_bal_summary, hide_index=True, column_config=column_config, use_container_width=True)
            elif metric == Names.WO_COUNT_PCT:
                wo_unt_perc_summary = calculate_grid_of_metric(Names.WO_COUNT_PCT)
                wo_unt_perc_summary = wo_unt_perc_summary.format(lambda v: f"{v:.2f} %", subset=selectbox_columns)

                new_column.markdown(f"### {Names.WO_COUNT_PCT}")
                new_column.dataframe(wo_unt_perc_summary, hide_index=True, column_config=column_config, use_container_width=True)
            elif metric == Names.WO_BAL_PCT:
                wo_bal_perc_summary = calculate_grid_of_metric(Names.WO_BAL_PCT)
                wo_bal_perc_summary = wo_bal_perc_summary.format(lambda v: f"{v:.2f} %", subset=selectbox_columns)

                new_column.markdown(f"### {Names.WO_BAL_PCT}")
                new_column.dataframe(wo_bal_perc_summary, hide_index=True, column_config=column_config, use_container_width=True)


def show_double_var_iteration_widgets():
    session: Session = st.session_state['session']
    iteration_graph = session.iteration_graph
    iteration = iteration_graph.iterations[iteration_graph.current_node_id]

    show_navigation_buttons()

    with st.sidebar:
        if st.button("Set Metrics", use_container_width=True):
            show_metric_selector(iteration.id)

        col1, col2 = st.columns([3, 1])
        if col1.button("Edit Groups", use_container_width=True):
            set_groups(iteration.id)

        if col2.button("", use_container_width=True, icon=":material/add:", key="Add Group"):
            iteration.add_group(iteration.num_groups)
            iteration_graph.add_to_calculation_queue(iteration.id)
            st.rerun()

        if st.button("Set Variables", use_container_width=True):
            show_variable_selector_dialog()

        split_view = st.checkbox("Split into columns")

    st.title(f"Iteration #{iteration.id}")
    st.write(f"##### Variable: `{iteration.variable.name}`")

    error_message = show_edited_grid(split_view)

    if error_message:
        st.error(error_message, icon=":material/error:")
        return

    with st.expander("Final Risk Tier View"):
        iter_id = iteration.id

        while iter_id is not None:
            st.title(f"Iteration #{iter_id}")
            st.markdown(f"##### Variable: `{iteration_graph.iterations[iter_id].variable.name}`")
            show_edited_range(iter_id, editable=False)
            iter_id = iteration_graph.get_parent(iter_id)