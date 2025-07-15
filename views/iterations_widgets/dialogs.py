import pandas as pd
import streamlit as st
from streamlit_sortables import sort_items

from classes.constants import MetricTableColumn, VariableType, RangeColumn
from classes.iteration_graph import IterationGraph
from classes.session import Session


@st.dialog("Set Metrics")
def metric_selector_dialog_widget(iteration_id: str | None = None):
    session: Session = st.session_state["session"]

    if iteration_id is None:
        metrics_df = session.summary_page_state.metrics
    else:
        iteration_graph = session.iteration_graph
        metrics_df = iteration_graph.iteration_metadata[iteration_id]["metrics"]

    st.write("Select Metrics:")

    all_metrics = metrics_df[MetricTableColumn.METRIC].to_list()
    showing_metrics = metrics_df.loc[
        metrics_df[MetricTableColumn.SHOWING], MetricTableColumn.METRIC
    ].to_list()

    selected_metrics = st.multiselect(
        label="Metrics",
        options=all_metrics,
        default=showing_metrics,
        label_visibility="collapsed",
    )

    if set(selected_metrics) != set(showing_metrics):
        metrics_df.loc[
            metrics_df[MetricTableColumn.METRIC].isin(selected_metrics),
            MetricTableColumn.SHOWING,
        ] = True
        metrics_df.loc[
            ~metrics_df[MetricTableColumn.METRIC].isin(selected_metrics),
            MetricTableColumn.SHOWING,
        ] = False
        st.rerun(scope="fragment")

    st.write("Reorder Metrics:")

    sorted_metrics = sort_items(
        metrics_df.sort_values(MetricTableColumn.ORDER)
        .loc[metrics_df[MetricTableColumn.SHOWING], MetricTableColumn.METRIC]
        .to_list(),
    )

    sorted_metrics = pd.DataFrame({
        MetricTableColumn.METRIC: sorted_metrics,
        "new_order": range(len(sorted_metrics)),
    })

    temp = (
        pd.merge(
            metrics_df,
            sorted_metrics,
            how="left",
            left_on=MetricTableColumn.METRIC,
            right_on=MetricTableColumn.METRIC,
            suffixes=("", "_y"),
        )
        .dropna()
        .sort_values("new_order")
    )

    if not temp[MetricTableColumn.ORDER].is_monotonic_increasing:
        index = temp.index
        order = temp[MetricTableColumn.ORDER].sort_values().to_list()
        metrics_df.loc[index, MetricTableColumn.ORDER] = order
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
