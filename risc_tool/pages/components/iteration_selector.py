import streamlit as st

from risc_tool.data.session import Session


def iteration_selector(key: str):
    session: Session = st.session_state["session"]
    options = session.iterations_repository.iteration_selector_options()

    iteration_id = st.selectbox(
        label=f"iter_selector_{key}",
        options=options,
        label_visibility="collapsed",
        format_func=lambda k: options.get(k, ""),
        key=f"iter_selector_{key}",
    )

    return iteration_id


__all__ = ["iteration_selector"]
