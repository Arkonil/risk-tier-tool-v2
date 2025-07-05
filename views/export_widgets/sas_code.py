import streamlit as st

from classes.session import Session
from views.components import show_iteration_selector, show_load_data_first_error


def show_sas_code_download():
    if show_load_data_first_error(key=0):
        return

    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    st.markdown("### Download SAS Code")

    iteration_id, is_default = show_iteration_selector(key=0)

    use_macros = st.checkbox("Use Macros")

    code = iteration_graph.get_sas_code(iteration_id, is_default, use_macro=use_macros)

    st.code(code, language="sas")


__all__ = ["show_sas_code_download"]
