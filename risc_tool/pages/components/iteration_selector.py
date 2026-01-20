import streamlit as st

from risc_tool.data.models.types import IterationID
from risc_tool.data.session import Session


def iteration_selector(
    key: str,
    iteration_id: IterationID | None = None,
    default: bool | None = None,
) -> tuple[IterationID, bool]:
    session: Session = st.session_state["session"]
    options = session.iterations_repository.iteration_selector_options()

    options_list = list(options.keys())

    if (
        iteration_id is not None
        and default is not None
        and (iteration_id, default) in options_list
    ):
        index = options_list.index((iteration_id, default))
    else:
        index = 0

    iteration_id, default = st.selectbox(
        label=f"iter_selector_{key}",
        options=options_list,
        index=index,
        label_visibility="collapsed",
        format_func=lambda k: options.get(k, ""),
        key=f"iter_selector_{key}",
    )

    return iteration_id, default


__all__ = ["iteration_selector"]
