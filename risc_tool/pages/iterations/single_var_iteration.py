import streamlit as st

from risc_tool.data.models.enums import IterationType
from risc_tool.data.session import Session
from risc_tool.pages.iterations.common import (
    check_current_rs_details,
    editable_range_widget,
    iteration_sidebar_components,
)
from risc_tool.pages.iterations.navigation import navigation_widgets


def single_var_iteration():
    # Navigation
    navigation_widgets()

    session: Session = st.session_state["session"]
    iterations_vm = session.iterations_view_model

    iteration = iterations_vm.current_iteration

    if iteration is None or iteration.iter_type != IterationType.SINGLE:
        st.exception(RuntimeError(f"Invalid Iteration Type: {type(iteration)}"))
        return

    # Sidebar
    with st.sidebar:
        iteration_sidebar_components(iteration_id=iteration.uid)

    # Main Page
    st.title(f"Iteration #{iteration.uid}")
    st.write(f"##### Variable: `{iteration.variable.name}`")

    ## Risk Tier Details Check
    check_current_rs_details()

    ## Default View
    st.markdown("##### Default Range")
    editable_range_widget(
        iteration_id=iteration.uid,
        editable=True,
        default=True,
        key="range-grid-default",
    )

    # # Editable View
    st.markdown("##### Editable Range")
    editable_range_widget(
        iteration_id=iteration.uid,
        editable=True,
        default=False,
        key="range-grid-editable",
    )


__all__ = ["single_var_iteration"]
