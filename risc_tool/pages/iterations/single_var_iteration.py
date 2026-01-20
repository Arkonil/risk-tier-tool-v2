import streamlit as st

from risc_tool.data.models.enums import IterationType
from risc_tool.data.session import Session
from risc_tool.pages.components.iteration_metric_table import iteration_metric_table
from risc_tool.pages.iterations.common import (
    check_current_rs_details,
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

    metadata = iterations_vm.get_iteration_metadata(iteration.uid)

    # Sidebar
    with st.sidebar:
        iteration_sidebar_components(iteration_id=iteration.uid)

    # Main Page
    st.title(iteration.pretty_name)
    st.write(f"##### Variable: `{iteration.variable.name}`")

    ## Risk Tier Details Check
    check_current_rs_details()

    ## Default View
    st.markdown("##### Default Range")
    iteration_metric_table(
        iteration_id=iteration.uid,
        editable=True,
        default=True,
        show_controls=True,
        filter_ids=metadata.current_filter_ids,
        metric_ids=metadata.metric_ids,
        scalars_enabled=metadata.scalars_enabled,
        key="range-grid-default",
    )

    # # Editable View
    st.markdown("##### Editable Range")
    iteration_metric_table(
        iteration_id=iteration.uid,
        editable=True,
        default=False,
        show_controls=True,
        filter_ids=metadata.current_filter_ids,
        metric_ids=metadata.metric_ids,
        scalars_enabled=metadata.scalars_enabled,
        key="range-grid-editable",
    )


__all__ = ["single_var_iteration"]
