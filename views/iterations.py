import streamlit as st

from classes.session import Session
from classes.iteration_graph import IterationGraph
from views.components import show_load_data_first_error
from views.iterations_widgets import (
    show_iteration_graph_widgets,
    show_iteration_creation_page,
    show_single_var_iteration_widgets,
    show_double_var_iteration_widgets,
)


def show_iteration_widgets():
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    if iteration_graph.is_root(iteration_graph.current_iteration.id):
        show_single_var_iteration_widgets()
    else:
        show_double_var_iteration_widgets()


def iterations():
    if show_load_data_first_error():
        return

    session = st.session_state["session"]
    iteration_graph: IterationGraph = session.iteration_graph

    if iteration_graph.current_iter_create_mode is not None:
        show_iteration_creation_page()
    elif iteration_graph.current_node_id is not None:
        show_iteration_widgets()
    else:
        show_iteration_graph_widgets()


iteration_graph_page = st.Page(
    page=iterations,
    title="Iterations",
    icon=":material/account_tree:",
)


__all__ = ["iteration_graph_page"]
