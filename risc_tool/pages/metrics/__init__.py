import streamlit as st

from risc_tool.data.session import Session
from risc_tool.pages.components.load_data_prompt import load_data_prompt
from risc_tool.pages.metrics.metric_editor import metric_editor
from risc_tool.pages.metrics.metric_list import metric_list


def metrics():
    session: Session = st.session_state["session"]
    metric_editor_vm = session.metric_editor_view_model

    if not metric_editor_vm.sample_loaded:
        load_data_prompt()
        return

    if metric_editor_vm.mode == "edit":
        metric_editor()
    else:
        metric_list()


metrics_page = st.Page(
    page=metrics,
    title="Metrics",
    icon=":material/functions:",
)

__all__ = [
    "metrics_page",
]
