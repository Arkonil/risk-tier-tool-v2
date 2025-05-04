import pathlib as p

import pandas as pd
import streamlit as st
from streamlit_flow import streamlit_flow
from streamlit_flow.elements import StreamlitFlowNode, StreamlitFlowEdge
from streamlit_flow.state import StreamlitFlowState
from streamlit_flow.layouts import TreeLayout

from classes.common import SUB_RISK_TIERS
from classes.iteration_graph import IterationGraph
from classes.session import Session


def streamlit_flow_graph(iteration_graph: IterationGraph) -> StreamlitFlowState:
    iterations = iteration_graph.iterations
    connections = iteration_graph.connections
    selected_node_id = iteration_graph.selected_node_id

    node_style = {
        "border-radius": "1em"
    }

    nodes = []

    for node_id, iteration in iterations.items():
        is_root = iteration_graph.is_root(node_id)
        is_leaf = iteration_graph.is_leaf(node_id)

        if is_root:
            node_type = 'input'
        elif is_leaf:
            node_type = 'output'
        else:
            node_type = 'default'

        if iteration.name == "":
            node_content = f"""<p>
                <strong>Iteration #{node_id}</strong>
                <br />
                <i>{iteration.variable.name}</i>
            </p>"""
        else:
            node_content = f"""<p>
                <strong>Iteration #{node_id}</strong>
                <br />
                {iteration.name}
                <br />
                <i>{iteration.variable.name}</i>
            </p>"""

        nodes.append(StreamlitFlowNode(
            id=f"{node_id}",
            pos=(100, 100),
            data={'content': node_content},
            node_type=node_type,
            source_position='right',
            target_position='left',
            draggable=False,
            style=node_style
        ))

    edges = []

    for node_id, children in connections.items():
        for child_id in children:
            edges.append(StreamlitFlowEdge(
                id=f"{node_id}-{child_id}",
                source=node_id,
                target=child_id,
                edge_type='simplebezier',
                animated=True,
            ))

    state = StreamlitFlowState(nodes, edges, selected_node_id)
    state.timestamp = 0

    new_state = streamlit_flow(
        key=f'iteration_flow-{len(iterations)}',
        state=state,
        layout=TreeLayout(direction='right'),
        fit_view=True,
        height=550,
        enable_node_menu=False,
        enable_edge_menu=False,
        enable_pane_menu=False,
        show_controls=False,
        get_edge_on_click=False,
        get_node_on_click=True,
        show_minimap=st.sidebar.checkbox("Show Minimap", value=True),
        hide_watermark=True,
        allow_new_edges=False
    )

    iteration_graph.select_node_id(new_state.selected_id)

    return new_state

@st.dialog("Choose a variable")
def show_primary_iter_var_selection_dialog():
    session: Session = st.session_state['session']
    data = session.data

    if not data.sample_loaded:
        st.error("Please load data first")
        if st.button("Load Data"):
            st.switch_page(p.Path(__file__).parent.parent / "data_importer.py")
        return

    variable_name = st.selectbox("Select a variable", data.sample_df.columns)
    iteration_name = st.text_input("Iteration Name")
    variable_dtype = st.selectbox("Variable Type", ["numerical", "categorical"])
    labels = st.multiselect("Risk Tiers", SUB_RISK_TIERS, default=SUB_RISK_TIERS)

    if st.button("Select"):
        variable = data.load_column(variable_name)

        if not pd.api.types.is_numeric_dtype(variable):
            variable_dtype = "categorical"

        session.iteration_graph.add_single_var_node(
            name=iteration_name,
            variable=variable,
            variable_dtype=variable_dtype,
            labels=labels,
        )

        st.rerun()

@st.dialog("Choose a variable")
def show_secondary_iter_var_selection_dialog(parent_node_id: str):
    session: Session = st.session_state['session']
    data = session.data

    variable_name = st.selectbox("Select a variable", data.sample_df.columns)
    iteration_name = st.text_input("Iteration Name")
    variable_dtype = st.selectbox("Variable Type", ["numerical", "categorical"])

    if st.button("Select"):
        variable = data.load_column(variable_name)

        if not pd.api.types.is_numeric_dtype(variable):
            variable_dtype = "categorical"

        session.iteration_graph.add_double_var_node(
            name=iteration_name,
            variable=variable,
            variable_dtype=variable_dtype,
            previous_node_id=parent_node_id,
        )
        st.rerun()

@st.dialog("Confirm Delete")
def show_delete_confirmation_dialog(node_id: str):
    session: Session = st.session_state['session']
    iteration_graph = session.iteration_graph

    st.write("Are you sure you want to delete this iteration?")
    if st.button("Delete"):
        iteration_graph.delete_iteration(node_id)
        st.rerun()


def show_iteration_graph_widgets():
    session: Session = st.session_state['session']
    iteration_graph = session.iteration_graph

    st.title("Iteration Graph")

    new_state = streamlit_flow_graph(iteration_graph)

    if new_state.selected_id is not None:
        if st.sidebar.button(
            label=f"Open Iteration #{new_state.selected_id}",
            use_container_width=True,
            type="primary",
            icon=":material/open_in_new:"
        ):
            iteration_graph.select_current_node_id(new_state.selected_id)
            st.rerun()

    if new_state.selected_id is None:
        if st.sidebar.button(
            label="Add New Iteration",
            icon=":material/add:",
            use_container_width=True,
            type="secondary"
        ):
            show_primary_iter_var_selection_dialog()
    else:
        if iteration_graph.iteration_depth(new_state.selected_id) < 3:
            if st.sidebar.button(
                label="Add Child Iteration",
                icon=":material/add:",
                use_container_width=True,
                type="secondary"
            ):
                show_secondary_iter_var_selection_dialog(new_state.selected_id)

        if st.sidebar.button(
            label="Delete Iteration",
            icon=":material/delete:",
            use_container_width=True,
            type="secondary"
        ):
            show_delete_confirmation_dialog(new_state.selected_id)
