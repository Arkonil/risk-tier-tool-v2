import streamlit as st


from classes.iteration_graph import IterationGraph
from classes.session import Session

from views.components import load_data_error_widget
from views.iterations_widgets.graph import iteration_graph_widget
from views.iterations_widgets.iteration_creator import iteration_creation_widget
from views.iterations_widgets.double_var_iteration import double_var_iteration_widget
from views.iterations_widgets.single_var_iteration import single_var_iteration_widgets


def iterations_view():
    if load_data_error_widget():
        return

    session: Session = st.session_state["session"]
    iteration_graph: IterationGraph = session.iteration_graph

    if iteration_graph.current_iter_create_mode is not None:
        iteration_creation_widget()
    elif iteration_graph.current_node_id is not None:
        if iteration_graph.is_root(iteration_graph.current_iteration.id):
            single_var_iteration_widgets()
        else:
            double_var_iteration_widget()
    else:
        iteration_graph_widget()


iteration_graph_page = st.Page(
    page=iterations_view,
    title="Iterations",
    icon=":material/account_tree:",
)


__all__ = ["iteration_graph_page"]
