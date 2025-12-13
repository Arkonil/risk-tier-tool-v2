import streamlit as st

from classes.session import Session
from views.components import iteration_selector_widget, load_data_error_widget


def sas_code_generator_widget():
    if load_data_error_widget(key=0):
        return

    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    st.markdown("### Download SAS Code")

    iteration_id, is_default = iteration_selector_widget(key=0)

    use_macros = st.checkbox("Use Macros")

    code = iteration_graph.get_sas_code(iteration_id, is_default, use_macro=use_macros)

    st.code(code, language="sas")


__all__ = ["sas_code_generator_widget"]
