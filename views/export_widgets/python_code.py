import streamlit as st

from classes.session import Session
from views.components import iteration_selector_widget, load_data_error_widget


def python_code_generator_widget():
    if load_data_error_widget(key=1):
        return

    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph
    data = session.data

    st.markdown("### Download Python Code")

    iteration_id, is_default = iteration_selector_widget(key=1)
    code_template = iteration_graph.get_python_code(iteration_id, is_default, data)

    st.code(code_template, language="python")


__all__ = ["python_code_generator_widget"]
