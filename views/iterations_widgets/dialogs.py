import pandas as pd
import streamlit as st
from streamlit_sortables import sort_items

from classes.common import SUB_RISK_TIERS, Names
from classes.iteration_graph import IterationGraph

@st.dialog("Set Metrics")
def show_metric_selector(node_id: str):
    session = st.session_state['session']
    iteration_graph: IterationGraph = session.iteration_graph
    metrics_df = iteration_graph.iteration_metadata[node_id]['metrics']

    st.write("Select Metrics:")

    selected_metrics = st.multiselect(
        label="Metrics",
        options=metrics_df['metric'].to_list(),
        default=metrics_df.loc[metrics_df['showing'], 'metric'],
        label_visibility="collapsed",
        format_func=lambda m: m.value,
    )

    if set(selected_metrics) != set(metrics_df.loc[metrics_df['showing'], 'metric']):
        metrics_df.loc[metrics_df['metric'].isin(selected_metrics), 'showing'] = True
        metrics_df.loc[~metrics_df['metric'].isin(selected_metrics), 'showing'] = False
        st.rerun(scope="fragment")

    st.write("Reorder Metrics:")

    sorted_metrics = sort_items(
        list(map(lambda m: m.value, metrics_df.sort_values('order').loc[metrics_df['showing'], 'metric'].to_list()))
    )

    sorted_metrics = pd.DataFrame({
        'metric': sorted_metrics,
        'new_order': range(len(sorted_metrics)),
    })

    temp = pd.merge(
        metrics_df,
        sorted_metrics,
        how='left',
        left_on='metric_name',
        right_on='metric',
        suffixes=('', '_y')
        ).dropna().sort_values('new_order')

    if not temp['order'].is_monotonic_increasing and not temp['order'].is_monotonic_decreasing:
        index = temp.index
        order = temp['order'].sort_values().to_list()
        metrics_df.loc[index, 'order'] = order
        st.rerun(scope="fragment")

    if st.button("Submit"):
        st.rerun()

@st.dialog("Set Risk Tiers")
def set_risk_tiers(node_id: str):
    session = st.session_state['session']
    iteration_graph: IterationGraph = session.iteration_graph
    iteration = iteration_graph.iterations[node_id]

    current_labels = SUB_RISK_TIERS.loc[iteration.groups.index]

    new_labels = st.multiselect(
        label="Risk Tiers",
        options=SUB_RISK_TIERS,
        default=current_labels,
    )

    if st.button("Submit"):
        for i in range(iteration.num_groups):
            if SUB_RISK_TIERS.loc[i] not in new_labels:
                iteration.remove_group(i)
            else:
                iteration.add_group(i)

        iteration_graph.add_to_calculation_queue(node_id)
        st.rerun()

@st.dialog("Set Groups")
def set_groups(node_id: str):
    session = st.session_state['session']
    iteration_graph: IterationGraph = session.iteration_graph
    iteration = iteration_graph.iterations[node_id]

    # pylint: disable=protected-access
    groups = pd.DataFrame({
        Names.GROUPS.value : iteration._groups,
        'Selected': iteration._group_mask
    })
    # pylint: enable=protected-access

    if iteration.var_type == "numerical":
        groups[Names.LOWER_BOUND.value] = groups[Names.GROUPS.value].map(lambda bounds: bounds[0])
        groups[Names.UPPER_BOUND.value] = groups[Names.GROUPS.value].map(lambda bounds: bounds[1])
    else:
        groups[Names.CATEGORIES.value] = groups[Names.GROUPS.value]

    groups.drop(columns=[Names.GROUPS.value], inplace=True)

    column_config = {
        Names.CATEGORIES.value: st.column_config.ListColumn(label=Names.CATEGORIES.value, width="large"),
        Names.LOWER_BOUND.value: st.column_config.NumberColumn(label=Names.LOWER_BOUND.value, disabled=True, format="compact"),
        Names.UPPER_BOUND.value: st.column_config.NumberColumn(label=Names.UPPER_BOUND.value, disabled=True, format="compact"),
        'Selected': st.column_config.CheckboxColumn(label='Selected', disabled=False),
    }

    edited_groups = st.data_editor(groups, column_config=column_config, use_container_width=True)

    if (edited_groups['Selected'] != groups['Selected']).any():
        for index in groups.index:
            if edited_groups.loc[index, 'Selected']:
                iteration.add_group(index)
            else:
                iteration.remove_group(index)

        st.rerun(scope="fragment")

    if st.button("Submit"):
        iteration_graph.add_to_calculation_queue(node_id)
        st.rerun()
