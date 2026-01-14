import typing as t

import streamlit as st
from streamlit_sortables import sort_items

from risc_tool.data.models.types import MetricID
from risc_tool.data.session import Session


@st.dialog("Set Metrics")
def metric_selector_dialog(
    current_metric_ids: list[MetricID],
    set_metrics: t.Callable[[list[MetricID]], None],
    key: int = 0,
):
    session: Session = st.session_state["session"]
    metric_repository = session.metric_repository

    all_metrics = metric_repository.get_all_metrics()

    available_metric_ids = list(sorted(all_metrics.keys()))
    current_metric_ids = [
        uid for uid in current_metric_ids if uid in available_metric_ids
    ]

    st.write("Select Metrics:")

    selected_metric_ids = st.multiselect(
        label="Metrics",
        options=all_metrics.keys(),
        default=current_metric_ids,
        format_func=lambda metric_id: all_metrics[metric_id].pretty_name,
        label_visibility="collapsed",
        key=f"metric_selector_{key}",
    )

    existing_metrics = [uid for uid in current_metric_ids if uid in selected_metric_ids]
    new_metrics = [uid for uid in selected_metric_ids if uid not in current_metric_ids]
    selected_metric_ids = existing_metrics + new_metrics

    st.write("Reorder Metrics:")

    selected_metric_names = [
        all_metrics[metric_id].pretty_name for metric_id in selected_metric_ids
    ]
    sorted_metric_names = sort_items(items=selected_metric_names)
    sorted_metric_ids = [
        selected_metric_ids[selected_metric_names.index(metric_name)]
        for metric_name in sorted_metric_names
    ]

    _, col = st.columns(2)

    with col:
        if st.button("Submit", type="primary", width="stretch"):
            set_metrics(sorted_metric_ids)
            st.rerun()


def default_set_metrics(metrics: list[MetricID]) -> None:
    return


def metric_selector_button(
    current_metrics: list[MetricID] | None = None,
    set_metrics: t.Callable[[list[MetricID]], None] | None = None,
    key: int = 0,
):
    if current_metrics is None:
        current_metrics = []

    if set_metrics is None:
        set_metrics = default_set_metrics

    st.button(
        label="Set Metrics",
        width="stretch",
        icon=":material/functions:",
        help="Set metrics to display in the table",
        key=f"metric_selector_button_{key}",
        on_click=lambda: metric_selector_dialog(current_metrics, set_metrics, key),
    )


__all__ = ["metric_selector_button"]
