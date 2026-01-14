import streamlit as st

from risc_tool.data.models.enums import IterationType
from risc_tool.data.session import Session
from risc_tool.pages.components.load_data_prompt import load_data_prompt
from risc_tool.pages.iterations.double_var_iteration import double_var_iteration
from risc_tool.pages.iterations.graph import iteration_graph
from risc_tool.pages.iterations.iteration_creator import iteration_creator
from risc_tool.pages.iterations.single_var_iteration import single_var_iteration


def iterations():
    session: Session = st.session_state["session"]
    iterations_vm = session.iterations_view_model

    if not iterations_vm.sample_loaded:
        load_data_prompt()
        return

    view, _ = iterations_vm.current_status

    if view == "view":
        if iterations_vm.current_iteration_type == IterationType.SINGLE:
            single_var_iteration()
        else:
            double_var_iteration()
    elif view == "create":
        iteration_creator()
    else:
        iteration_graph()


iterations_page = st.Page(
    page=iterations,
    title="Iterations",
    icon=":material/account_tree:",
)


__all__ = ["iterations_page"]
