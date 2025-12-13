import streamlit as st

from classes.session import Session
from views.components import load_data_error_widget
from views.metric_widgets.metric_list import metric_list
from views.metric_widgets.metric_editor import metric_editor


def metric_view():
    if load_data_error_widget():
        return

    session: Session = st.session_state["session"]
    mc = session.metric_container

    if mc.mode == "view":
        metric_list()
    elif mc.mode == "edit":
        metric_editor()
    else:
        raise ValueError(f"Invalid view mode: {mc.mode}")


metric_page = st.Page(
    page=metric_view,
    title="Metrics",
    icon=":material/functions:",
)

__all__ = [
    "metric_page",
]
