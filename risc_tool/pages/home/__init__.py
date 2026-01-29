import streamlit as st

from risc_tool.data.session import Session
from risc_tool.pages.home.import_json import import_json_page
from risc_tool.pages.home.welcome import welcome_page


def home_view():
    session: Session = st.session_state["session"]
    session_archive_vm = session.session_archive_view_model

    if session_archive_vm.home_page_view == "welcome":
        welcome_page()
    elif session_archive_vm.home_page_view == "import-json":
        import_json_page()


home_page = st.Page(
    page=home_view,
    title="Home",
    icon=":material/home:",
    default=True,
)


__all__ = ["home_page"]
