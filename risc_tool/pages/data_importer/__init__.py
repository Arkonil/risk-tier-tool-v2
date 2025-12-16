import streamlit as st

from risc_tool.data.session import Session
from risc_tool.pages.components.variable_selector import variable_selector
from risc_tool.pages.data_importer.data_selector import data_selector
from risc_tool.pages.data_importer.data_viewer import data_viewer


def data_importer():
    session: Session = st.session_state["session"]
    data_importer_view_model = session.data_importer_view_model

    st.title("Data Importer")

    st.subheader("Select Data Sources")
    data_selector()

    if not data_importer_view_model.sample_loaded:
        return

    st.space()

    st.subheader("Preview Data")
    data_viewer()

    st.space()

    st.subheader("Variable Selector")
    with st.container(border=True):
        variable_selector()


data_importer_page = st.Page(
    page=data_importer,
    title="Data Importer",
    icon=":material/file_upload:",
)


__all__ = ["data_importer_page"]
