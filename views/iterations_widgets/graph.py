import streamlit as st
from streamlit_flow import streamlit_flow
from streamlit_flow.elements import StreamlitFlowNode, StreamlitFlowEdge
from streamlit_flow.state import StreamlitFlowState
from streamlit_flow.layouts import TreeLayout

from classes.constants import IterationType
from classes.iteration_graph import IterationGraph
from classes.session import Session


def streamlit_flow_graph_widget(iteration_graph: IterationGraph) -> StreamlitFlowState:
    iterations = iteration_graph.iterations
    connections = iteration_graph.connections
    selected_node_id = iteration_graph.selected_node_id

    node_style = {
        "background": "rgba(255, 255, 255, 0.9)",
        "box-shadow": "0 8px 32px 0 rgba( 31, 38, 135, 0.37 )",
        "backdrop-filter": "blur( 4.5px )",
        "-webkit-backdrop-filter": "blur( 4.5px )",
        "border-radius": "10px",
        "border": "1px solid rgba( 255, 255, 255, 0.18 )",
    }

    nodes = []

    for node_id, iteration in iterations.items():
        is_root = iteration_graph.is_root(node_id)
        is_leaf = iteration_graph.is_leaf(node_id)

        if is_root:
            node_type = "input"
        elif is_leaf:
            node_type = "output"
        else:
            node_type = "default"

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

        nodes.append(
            StreamlitFlowNode(
                id=f"{node_id}",
                pos=(100, 100),
                data={"content": node_content},
                node_type=node_type,
                source_position="right",
                target_position="left",
                draggable=False,
                style=node_style,
            )
        )

    edges = []

    for node_id, children in connections.items():
        for child_id in children:
            edges.append(
                StreamlitFlowEdge(
                    id=f"{node_id}-{child_id}",
                    source=node_id,
                    target=child_id,
                    edge_type="simplebezier",
                    animated=True,
                )
            )

    state = StreamlitFlowState(nodes, edges, selected_node_id)
    state.timestamp = 0

    new_state = streamlit_flow(
        key=f"iteration_flow-{len(iterations)}",
        state=state,
        layout=TreeLayout(direction="right"),
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
        allow_new_edges=False,
    )

    iteration_graph.select_node_id(new_state.selected_id)

    return new_state


@st.dialog("Confirm Delete")
def delete_confirmation_dialog_widget(node_id: str):
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    st.write(
        f"Are you sure you want to delete iteration #{iteration_graph.iterations[node_id].id}?"
    )

    children = iteration_graph.get_descendants(node_id)
    if children:
        st.markdown("The following iterations will also be deleted:")
        st.markdown("\n".join([f"* `Iteration #{child}`" for child in children]))

    st.write("This action cannot be undone.")
    if st.button("Delete"):
        iteration_graph.delete_iteration(node_id)
        st.rerun()


def iteration_graph_widget():
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph
    options = session.options

    st.title("Iteration Graph")

    new_state = streamlit_flow_graph_widget(iteration_graph)

    if new_state.selected_id is not None:
        if st.sidebar.button(
            label=f"Open Iteration #{new_state.selected_id}",
            use_container_width=True,
            type="primary",
            icon=":material/open_in_new:",
        ):
            iteration_graph.select_current_node_id(new_state.selected_id)
            st.rerun()

    if new_state.selected_id is None:
        st.sidebar.button(
            label="Add New Iteration",
            icon=":material/add:",
            use_container_width=True,
            type="secondary",
            on_click=iteration_graph.set_current_iter_create_mode,
            kwargs={"iteration_type": IterationType.SINGLE},
        )

    else:
        if (
            iteration_graph.iteration_depth(new_state.selected_id)
            < options.max_iteration_depth
        ):
            st.sidebar.button(
                label="Add Child Iteration",
                icon=":material/add:",
                use_container_width=True,
                type="secondary",
                on_click=iteration_graph.set_current_iter_create_mode,
                kwargs={
                    "iteration_type": IterationType.DOUBLE,
                    "parent_node_id": new_state.selected_id,
                },
            )

        if st.sidebar.button(
            label="Delete Iteration",
            icon=":material/delete:",
            use_container_width=True,
            type="secondary",
        ):
            delete_confirmation_dialog_widget(new_state.selected_id)


__all__ = ["iteration_graph_widget"]
