import pandas as pd
import streamlit as st
from streamlit_sortables import sort_items

from classes.constants import VariableType, RangeColumn
from classes.iteration_graph import IterationGraph
from classes.session import Session


@st.dialog("Set Metrics")
def metric_selector_dialog_widget(iteration_id: str | None = None):
    session: Session = st.session_state["session"]

    all_metrics = session.get_all_metrics()
    all_metric_names = list(all_metrics.keys())

    if iteration_id is None:
        current_metric_names = session.summary_page_state.metrics
    else:
        iteration_graph = session.iteration_graph
        current_metric_names = iteration_graph.get_metadata(iteration_id, "metrics")

    current_metric_names = [m for m in current_metric_names if m in all_metrics]

    st.write("Select Metrics:")

    selected_metric_names = st.multiselect(
        label="Metrics",
        options=all_metric_names,
        default=current_metric_names,
        label_visibility="collapsed",
    )

    if set(selected_metric_names) != set(current_metric_names):
        if iteration_id is None:
            session.summary_page_state.metrics = selected_metric_names
        else:
            iteration_graph.set_metadata(iteration_id, "metrics", selected_metric_names)
        st.rerun(scope="fragment")

    st.write("Reorder Metrics:")

    sorted_metric_names = sort_items(items=selected_metric_names)

    if sorted_metric_names != selected_metric_names:
        if iteration_id is None:
            session.summary_page_state.metrics = sorted_metric_names
        else:
            iteration_graph.set_metadata(iteration_id, "metrics", sorted_metric_names)
        st.rerun(scope="fragment")

    *_, col = st.columns(4)

    with col:
        if st.button("Submit", type="primary", use_container_width=True):
            st.rerun()


@st.dialog("Set Groups")
def set_groups_dialog_widget(iteration_id: str):
    session = st.session_state["session"]
    iteration_graph: IterationGraph = session.iteration_graph
    iteration = iteration_graph.iterations[iteration_id]

    groups = pd.DataFrame({
        RangeColumn.GROUPS: iteration._groups,
        RangeColumn.SELECTED: iteration._groups_mask,
    })

    if iteration.var_type == VariableType.NUMERICAL:
        groups[RangeColumn.LOWER_BOUND] = groups[RangeColumn.GROUPS].map(
            lambda bounds: bounds[0]
        )
        groups[RangeColumn.UPPER_BOUND] = groups[RangeColumn.GROUPS].map(
            lambda bounds: bounds[1]
        )
    else:
        groups[RangeColumn.CATEGORIES] = groups[RangeColumn.GROUPS]

    groups.drop(columns=[RangeColumn.GROUPS], inplace=True)

    column_config = {
        RangeColumn.CATEGORIES: st.column_config.ListColumn(
            label=RangeColumn.CATEGORIES, width="large"
        ),
        RangeColumn.LOWER_BOUND: st.column_config.NumberColumn(
            label=RangeColumn.LOWER_BOUND, disabled=True, format="compact"
        ),
        RangeColumn.UPPER_BOUND: st.column_config.NumberColumn(
            label=RangeColumn.UPPER_BOUND, disabled=True, format="compact"
        ),
        RangeColumn.SELECTED: st.column_config.CheckboxColumn(
            label=RangeColumn.SELECTED, disabled=False
        ),
    }

    edited_groups = st.data_editor(
        groups, column_config=column_config, use_container_width=True
    )

    if (edited_groups[RangeColumn.SELECTED] != groups[RangeColumn.SELECTED]).any():
        for index in groups.index:
            if edited_groups.loc[index, RangeColumn.SELECTED]:
                iteration.add_group(index)
            else:
                iteration.remove_group(index)

        st.rerun(scope="fragment")

    *_, col = st.columns(4)

    with col:
        if st.button("Submit", type="primary", use_container_width=True):
            iteration_graph.add_to_calculation_queue(iteration_id, default=False)
            st.rerun()


__all__ = [
    "metric_selector_dialog_widget",
    "set_groups_dialog_widget",
]
