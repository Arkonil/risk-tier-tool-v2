import streamlit as st

from classes.session import Session
from views.iterations_widgets.navigation import show_navigation_buttons

def show_double_var_iteration_widgets():
    session: Session = st.session_state['session']
    iteration_graph = session.iteration_graph

    show_navigation_buttons()

    iteration = iteration_graph.iterations[iteration_graph.current_node_id]

    st.title(f"Iteration #{iteration.id}")
