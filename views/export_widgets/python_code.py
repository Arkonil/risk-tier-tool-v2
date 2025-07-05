import streamlit as st

from classes.session import Session
from views.components import show_iteration_selector, show_load_data_first_error


def show_python_code_download():
    if show_load_data_first_error(key=1):
        return

    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph
    data = session.data

    st.markdown("### Download Python Code")

    iteration_id, is_default = show_iteration_selector(key=1)
    code_template = iteration_graph.get_python_code(iteration_id, is_default, data)

    st.code(code_template, language="python")


__all__ = ["show_python_code_download"]
