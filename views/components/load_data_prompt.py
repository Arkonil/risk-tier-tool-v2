import streamlit as st

from classes.session import Session


def show_load_data_first_error(key: int = 0) -> bool:
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph
    data = session.data

    if not data.sample_loaded:
        st.error("Please load data first")
        if st.button("Load Data", key=key):
            iteration_graph.select_graph_view()

            from views.data_importer import data_importer_page

            st.switch_page(data_importer_page)
        return True

    return False
