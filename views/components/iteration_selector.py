import streamlit as st

from classes.session import Session


def iteration_selector_widget(
    selected_iteration_id: str = None,
    is_default: bool = None,
    key: int = 0,
):
    """
    Displays a selector for choosing iterations from all available iterations.
    """
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    iteration_ids = list(iteration_graph.iterations.keys())
    all_options = [
        (iter_id, is_default)
        for iter_id in iteration_ids
        for is_default in [True, False]
    ]

    if selected_iteration_id is not None and is_default is not None:
        for i, option in enumerate(all_options):
            if option == (selected_iteration_id, is_default):
                selected_option_index = i
                break
    else:
        # If no specific iteration is selected, default to the first option
        selected_option_index = 0

    def format_func(option: tuple[str, bool]) -> str:
        if option is None:
            return "No Iteration Selected"

        iteration_id, is_default = option
        default_or_edited = "Default" if is_default else "Edited"

        iteration = iteration_graph.iterations[iteration_id]
        if iteration.name:
            return f"Iteration {iteration_id} - {iteration.name} - {default_or_edited}"

        return f"Iteration {iteration_id} - {iteration.variable.name} - {default_or_edited}"

    iteration_id, is_default = st.selectbox(
        label="Select Iteration",
        options=all_options,
        key=f"selected_iteration_{key}",
        index=selected_option_index,
        format_func=format_func,
    )

    return iteration_id, is_default


__all__ = ["iteration_selector_widget"]
