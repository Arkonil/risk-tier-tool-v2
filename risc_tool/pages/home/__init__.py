import streamlit as st

from risc_tool.pages.data_importer import data_importer_page


def welcome_page_widgets():
    st.title("Risk Tier Development Tool")

    st.write("")
    st.write("")

    with st.container(border=True):
        st.markdown("### Import Data to get started")
        st.write('Supported file formats: `".csv"`, `".xlsx"`, `".xls"`')
        st.write("")
        if st.button("Import Data", icon=":material/file_upload:", type="primary"):
            pass
            st.switch_page(data_importer_page)

    st.write("")
    st.write("")

    with st.container(border=True):
        st.markdown("### Import a `.rt.zip` file to continue working on it")
        st.write('Supported file formats: `".rt.zip"`')
        st.write("")
        uploaded_file = st.file_uploader(
            "Upload a `.rt.zip` file",
            type=[".zip"],
            help="This file should contain the exported data from a previous session.",
            label_visibility="collapsed",
            accept_multiple_files=False,
        )

        if uploaded_file:
            pass


def home_view():
    welcome_page_widgets()


home_page = st.Page(page=home_view, title="Home", icon=":material/home:", default=True)


__all__ = ["home_page"]
