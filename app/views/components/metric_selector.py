import typing as t

import streamlit as st
from streamlit_sortables import sort_items

from classes.session import Session


@st.dialog("Set Metrics")
def metric_selector_dialog_widget(
    current_metric_names: list[str],
    set_metrics: t.Callable[[list[str]], None],
    key: int = 0,
):
    session: Session = st.session_state["session"]

    all_metrics = session.get_all_metrics()
    all_metric_names = list(all_metrics.keys())

    current_metric_names = [m for m in current_metric_names if m in all_metrics]

    st.write("Select Metrics:")

    selected_metric_names = st.multiselect(
        label="Metrics",
        options=all_metric_names,
        default=current_metric_names,
        label_visibility="collapsed",
        key=f"metric_selector_{key}",
    )

    existing_metrics = [m for m in current_metric_names if m in selected_metric_names]
    new_metrics = [m for m in selected_metric_names if m not in current_metric_names]
    selected_metric_names = existing_metrics + new_metrics

    st.write("Reorder Metrics:")

    sorted_metric_names = sort_items(items=selected_metric_names)

    *_, col = st.columns(4)

    with col:
        if st.button("Submit", type="primary", use_container_width=True):
            set_metrics(sorted_metric_names)
            st.rerun()


def default_set_metrics(metrics: list[str]) -> None:
    return


def metric_selector_widget(
    current_metrics: list[str] = None,
    set_metrics: t.Callable[[list[str]], None] = None,
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
        on_click=metric_selector_dialog_widget,
        args=(current_metrics, set_metrics, key),
    )


__all__ = ["metric_selector_widget"]
