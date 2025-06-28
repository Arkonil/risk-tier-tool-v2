import streamlit as st

from classes.iteration_graph import IterationGraph
from views.iterations_widgets import (
    show_iteration_graph_widgets,
    show_iteration_widgets,
    show_iteration_creation_page,
)


def iterations():
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
