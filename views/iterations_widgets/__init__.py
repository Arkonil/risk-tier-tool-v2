import streamlit as st

from .graph import show_iteration_graph_widgets
from .single_var_iteration import show_single_var_iteration_widgets
from .double_var_iteraton import show_double_var_iteration_widgets

def show_iteration_widgets():
    session = st.session_state['session']
    iteration_graph = session.iteration_graph
    
    if iteration_graph.iteration_depth(iteration_graph.viewing_node_id) == 1:
        show_single_var_iteration_widgets()
    else:
        show_double_var_iteration_widgets()

__all__ = ['show_iteration_graph_widgets', 'show_iteration_widgets']
