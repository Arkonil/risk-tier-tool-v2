import streamlit as st

from classes.session import Session

def show_navigation_buttons():
    session: Session = st.session_state['session']
    iteration_graph = session.iteration_graph
    node_id = iteration_graph._current_node_id
    node_depth = iteration_graph.iteration_depth(node_id)
    
    w1, w2, w3, w4 = 100, 120, 120, 100
    
    columns = st.columns([w1, w2, w3, w4, (1000 - w1 - w2 - w3 - w4)], vertical_alignment="center")
    
    current_column = 0
    with columns[current_column]:
        if st.button("Back", icon=":material/arrow_back_ios:", type="primary"):
            iteration_graph.select_current_node_id()
            st.rerun()
            
    current_column += 1
        
    if node_depth > 1:
        with columns[current_column]:
            if st.button("Previous", icon=":material/arrow_back_ios:", type="primary"):
                iteration_graph.select_current_node_id(iteration_graph.get_parent(node_id))
                st.rerun()
                
        current_column += 1
            
    if node_depth < 3 and node_id in iteration_graph.connections and len(iteration_graph.connections[node_id]) > 0:
        with columns[current_column]:
            child_node_id = st.selectbox("Select child node", iteration_graph.connections[node_id], label_visibility="collapsed")
            
        current_column += 1
        with columns[current_column]:
            if st.button("Next", icon=":material/arrow_forward_ios:", type="primary"):
                iteration_graph.select_current_node_id(child_node_id)
                st.rerun()
        
    