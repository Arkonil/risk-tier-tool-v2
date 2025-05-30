import numpy as np
import pandas as pd
import streamlit as st

from classes.common import SUB_RISK_TIERS, color_map, Names, Metric
from classes.session import Session

from views.iterations_widgets.dialogs import set_risk_tiers, show_metric_selector
from views.iterations_widgets.navigation import show_navigation_buttons
from views.variable_selector import show_variable_selector_dialog

def show_category_editor(node_id: str):
    session: Session = st.session_state['session']
    iteration_graph = session.iteration_graph

    iteration = iteration_graph.iterations[node_id]

    if iteration.var_type != "categorical":
        st.error("Group editor is only available for categorical variables.", icon=":material/error:")
        return

    groups = iteration.groups
    groups = pd.DataFrame({Names.GROUPS.value : groups})

    with st.expander("Edit Groups"):
        columns = st.columns(min(5, len(groups)))

        all_categories = set(iteration.variable.cat.categories)
        assigned_categories = set(groups[Names.GROUPS.value].explode())
        unassigned_categories = all_categories - assigned_categories

        for i, row in enumerate(groups.itertuples()):
            group_index = row.Index
            group = set(row[1])

            with columns[i % len(columns)]:
                new_group = set(st.multiselect(
                    label=SUB_RISK_TIERS.loc[group_index],
                    options=sorted(list(group.union(unassigned_categories))),
                    default=sorted(list(group),
                )))

                if group != new_group:
                    iteration.set_group(group_index, new_group)
                    iteration_graph.add_to_calculation_queue(iteration.id)
                    st.rerun()

def show_edited_range(iteration_id: str, editable: bool = True):
    session: Session = st.session_state['session']
    iteration_graph = session.iteration_graph
    data = session.data

    iteration = iteration_graph.iterations[iteration_id]

    if iteration.var_count == 2:
        editable = False

    if editable and iteration.var_type == "categorical":
        show_category_editor(iteration.id)
        st.divider()

    new_risk_tiers, errors, warnings, _ = iteration_graph.get_risk_tiers(iteration.id)

    if iteration.var_count == 1:
        groups = iteration.groups
        groups = pd.DataFrame({Names.GROUPS.value : groups}) \
            .merge(SUB_RISK_TIERS, how='left', left_index=True, right_index=True)

        if iteration.var_type == "numerical":
            groups[Names.LOWER_BOUND.value] = groups[Names.GROUPS.value].map(lambda bounds: bounds[0])
            groups[Names.UPPER_BOUND.value] = groups[Names.GROUPS.value].map(lambda bounds: bounds[1])
        else:
            groups[Names.CATEGORIES.value] = groups[Names.GROUPS.value]
    else:
        groups = pd.DataFrame({
            Names.RISK_TIER.value: SUB_RISK_TIERS.loc[SUB_RISK_TIERS.index.isin(new_risk_tiers)]
        })

    metrics_df = iteration_graph.iteration_metadata[iteration_graph.current_node_id]['metrics']
    showing_metrics = metrics_df.sort_values("order").loc[metrics_df['showing'], 'metric']

    summ_df = data.get_summarized_metrics(
        new_risk_tiers.rename(Names.RISK_TIER_VALUE.value),
        metrics=showing_metrics.to_list(),
    )

    calculated_df = groups.merge(summ_df, how='left', left_index=True, right_index=True)

    int_cols = [Metric.VOLUME.value, Metric.WO_COUNT.value]
    dec_cols = [Metric.WO_BAL.value, Metric.AVG_BAL.value]
    perc_cols = [Metric.WO_BAL_PCT.value, Metric.WO_COUNT_PCT.value, Metric.ANNL_WO_COUNT_PCT.value, Metric.ANNL_WO_BAL_PCT.value]

    calculated_df = calculated_df.style \
        .map(lambda v: f'background-color: {color_map[v]};', subset=[Names.RISK_TIER.value]) \
        .format(precision=0, thousands=',', subset=int_cols) \
        .format(precision=2, thousands=',', subset=dec_cols) \
        .format('{:.2f} %', subset=perc_cols)

    disabled = not editable
    column_config = {
        Names.RISK_TIER.value: st.column_config.TextColumn(label=Names.RISK_TIER.value, disabled=True),
        Names.CATEGORIES.value: st.column_config.ListColumn(label=Names.CATEGORIES.value, width="large"),
        Names.LOWER_BOUND.value: st.column_config.NumberColumn(label=Names.LOWER_BOUND.value, disabled=disabled, format="compact"),
        Names.UPPER_BOUND.value: st.column_config.NumberColumn(label=Names.UPPER_BOUND.value, disabled=disabled, format="compact"),
        Metric.VOLUME.value: st.column_config.NumberColumn(label=Metric.VOLUME.value, disabled=True),
        Metric.WO_BAL.value: st.column_config.NumberColumn(label=Metric.WO_BAL.value, disabled=True),
        Metric.WO_BAL_PCT.value: st.column_config.NumberColumn(label=Metric.WO_BAL_PCT.value, disabled=True),
        Metric.WO_COUNT.value: st.column_config.NumberColumn(label=Metric.WO_COUNT.value, disabled=True),
        Metric.WO_COUNT_PCT.value: st.column_config.NumberColumn(label=Metric.WO_COUNT_PCT.value, disabled=True),
        Metric.AVG_BAL.value: st.column_config.NumberColumn(label=Metric.AVG_BAL.value, disabled=True),
        Metric.ANNL_WO_COUNT_PCT.value: st.column_config.NumberColumn(label=Metric.ANNL_WO_COUNT_PCT.value, disabled=True),
        Metric.ANNL_WO_BAL_PCT.value: st.column_config.NumberColumn(label=Metric.ANNL_WO_BAL_PCT.value, disabled=True),
    }

    columns = [Names.RISK_TIER.value]
    if iteration.var_count == 1:
        if iteration.var_type == "numerical":
            columns += [Names.LOWER_BOUND.value, Names.UPPER_BOUND.value]
        else:
            columns += [Names.CATEGORIES.value]

    columns += showing_metrics.map(lambda m: m.value).to_list()

    edited_df = st.data_editor(
        calculated_df,
        column_order=columns,
        hide_index=True,
        column_config=column_config,
        use_container_width=True
    )

    if editable and iteration.var_type == "numerical":

        edited_groups = edited_df[[Names.RISK_TIER.value, Names.LOWER_BOUND.value, Names.UPPER_BOUND.value]]

        needs_rerun = False
        for index in edited_groups.index:
            prev_bounds = np.array(groups.loc[index, Names.GROUPS.value]).astype(float)
            curent_bounds = np.array(edited_groups.loc[index, [Names.LOWER_BOUND.value, Names.UPPER_BOUND.value]]).astype(float)

            if not np.array_equal(prev_bounds, curent_bounds, equal_nan=True):
                curr_lb = edited_groups.loc[index, Names.LOWER_BOUND.value]
                curr_ub = edited_groups.loc[index, Names.UPPER_BOUND.value]

                iteration.set_group(index, curr_lb, curr_ub)
                iteration_graph.add_to_calculation_queue(iteration.id)
                needs_rerun = True

        if needs_rerun:
            print(f"needs rerun: {needs_rerun}")
            st.rerun()

    if editable:
        if errors:
            message = "Errors: \n\n" + "\n\n".join(map(lambda msg: f"- {msg}", errors))

            st.error(message, icon=":material/error:")

        if warnings:
            message = "Warnings: \n\n" + "\n\n".join(map(lambda msg: f"- {msg}", warnings))

            st.warning(message, icon=":material/warning:")


def show_single_var_iteration_widgets():
    session: Session = st.session_state['session']
    iteration_graph = session.iteration_graph
    iteration = iteration_graph.current_iteration

    show_navigation_buttons()

    with st.sidebar:
        if st.button(
            label="Set Metrics",
            use_container_width=True,
            icon=":material/functions:",
            help="Set metrics to display in the table",
        ):
            show_metric_selector(iteration.id)

        if st.button(
            label="Set Risk Tiers",
            use_container_width=True,
            icon=":material/leaderboard:",
            help="Set the desired Risk Tiers",
        ):
            set_risk_tiers(iteration.id)

        if st.button(
            label="Set Variables",
            use_container_width=True,
            icon=":material/data_table:",
            help="Select variables for calculations",
        ):
            show_variable_selector_dialog()

        if st.button(
            label="Reverse Group Order",
            use_container_width=True,
            icon=":material/swap_vert:",
            help="Reverse the selection of groups",
        ):
            iteration.reverse_group_order()
            iteration_graph.add_to_calculation_queue(iteration.id)
            st.rerun()


    st.title(f"Iteration #{iteration.id}")
    st.write(f"##### Variable: `{iteration.variable.name}`")

    show_edited_range(
        iteration_id=iteration.id,
        editable=True,
    )
