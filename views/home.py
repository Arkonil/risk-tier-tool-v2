import streamlit as st

from classes.session import Session


def show_welcome_page():
    session: Session = st.session_state["session"]
    st.title("Risk Tier Development Tool")

    st.write("")
    st.write("")

    with st.container(border=True):
        st.markdown("### Import Data to get started")
        st.write('Supported file formats: `".csv"`, `".xlsx"`, `".xls"`')
        st.write("")
        if st.button("Import Data", icon=":material/file_upload:", type="primary"):
            st.switch_page("views/data_importer.py")

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
            session.import_rt_zip(uploaded_file)

            # st.write(uploaded_file)
            st.switch_page("views/data_importer.py")


def show_home_page():
    show_welcome_page()


show_home_page()
