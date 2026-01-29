import streamlit as st

from risc_tool.data.session import Session
from risc_tool.pages.data_importer import data_importer_page


def welcome_page():
    session: Session = st.session_state["session"]
    session_archive_vm = session.session_archive_view_model

    st.title("Risk Tier Development Tool")

    st.write("")
    st.write("")

    with st.container(border=True):
        st.markdown("### Import Data to get started")
        st.write('Supported file formats: `".csv"`, `".xlsx"`, `".xls"`')
        st.space()
        if st.button("Import Data", icon=":material/file_upload:", type="primary"):
            pass
            st.switch_page(data_importer_page)

    st.write("")
    st.write("")

    with st.container(border=True):
        st.markdown("### Import a `.json` file to continue working on it")
        st.space()
        st.button(
            label="Import JSON File",
            on_click=lambda: session_archive_vm.set_home_page_view("import-json"),
            icon=":material/open_in_new:",
        )


__all__ = ["welcome_page"]
