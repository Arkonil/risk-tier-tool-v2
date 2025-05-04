import streamlit as st

from classes.iteration_graph import IterationGraph
from views.iterations_widgets import show_iteration_graph_widgets, show_iteration_widgets

def show_iterations_page():
    session = st.session_state['session']
    iteration_graph: IterationGraph = session.iteration_graph
    
    if iteration_graph.viewing_node_id is None:
        show_iteration_graph_widgets()
    else:
        show_iteration_widgets()
    
show_iterations_page()
