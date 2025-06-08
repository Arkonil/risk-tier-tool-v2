import streamlit as st


def show_welcome_page():
    st.title("Risk Tier Development Tool")

    st.write("")
    st.write("")

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("##### Import Data to get started")
            st.write('Supported file formats: `".csv"`, `".xlsx"`, `".xls"`')
            if st.button("Import Data", icon=":material/file_upload:", type="primary"):
                st.switch_page("views/data_importer.py")

    with col2:
        with st.container(border=True):
            st.markdown("##### Import a `.rt.zip` file to continue working on it")
            st.write('Supported file formats: `".zip"`')
            if st.button("Import `.rt.zip` file", icon=":material/file_upload:"):
                st.switch_page("views/data_importer.py")


def show_home_page():
    show_welcome_page()


show_home_page()
