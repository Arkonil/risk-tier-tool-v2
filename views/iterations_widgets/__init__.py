import streamlit as st

from classes.session import Session
from views.iterations_widgets.double_var_iteration import (
    show_double_var_iteration_widgets,
)
from views.iterations_widgets.graph import show_iteration_graph_widgets
from views.iterations_widgets.iteration_creator import show_iteration_creation_page
from views.iterations_widgets.single_var_iteration import (
    show_single_var_iteration_widgets,
)


def show_iteration_widgets():
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    if iteration_graph.is_root(iteration_graph.current_iteration.id):
        show_single_var_iteration_widgets()
    else:
        show_double_var_iteration_widgets()


__all__ = [
    "show_iteration_graph_widgets",
    "show_iteration_widgets",
    "show_iteration_creation_page",
]
