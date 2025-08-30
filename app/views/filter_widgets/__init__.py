import streamlit as st

from classes.session import Session

from views.components import load_data_error_widget
from views.filter_widgets.filter_editor import filter_editor
from views.filter_widgets.filter_list import filter_list


def filter_view():
    if load_data_error_widget():
        return

    session: Session = st.session_state["session"]
    fc = session.filter_container

    if fc.mode == "view":
        filter_list()
    elif fc.mode == "edit":
        filter_editor()
    else:
        raise ValueError(f"Invalid view mode: {fc.mode}")


filter_page = st.Page(
    page=filter_view,
    title="Filters (Experimental)",
    icon=":material/filter_alt:",
)

__all__ = [
    "filter_page",
]
