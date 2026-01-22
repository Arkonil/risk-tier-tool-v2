from uuid import UUID

import streamlit as st
import streamlit_antd_components as sac

from risc_tool.data.models.types import IterationID
from risc_tool.data.session import Session
from risc_tool.pages.components.filter_selector import filter_selector
from risc_tool.pages.components.iteration_metric_table import iteration_metric_table
from risc_tool.pages.components.iteration_selector import iteration_selector
from risc_tool.pages.components.metric_selector import metric_selector_button


def sidebar_widgets():
    session: Session = st.session_state["session"]
    summary_vm = session.summary_view_model

    # Metric Selection
    metric_selector_button(
        current_metrics=summary_vm.cv_metric_ids,
        set_metrics=summary_vm.set_comparison_metrics,
    )

    # Filter Selection
    current_filter_ids = summary_vm.cv_filter_ids

    selected_filter_ids = filter_selector(
        key="summary-comparison-filter-selector",
        filter_ids=current_filter_ids,
    )

    if set(selected_filter_ids) != set(current_filter_ids):
        summary_vm.cv_filter_ids = selected_filter_ids
        st.rerun()

    # Layout Toggle
    selected = sac.segmented(
        [
            sac.SegmentedItem("list", "list"),
            sac.SegmentedItem("grid", "grid"),
        ],
        use_container_width=True,
        size="sm",
        index=0 if summary_vm.cv_view_mode == "list" else 1,
        key="summary-comparison-view-mode",
    )

    if selected in ("list", "grid") and selected != summary_vm.cv_view_mode:
        summary_vm.cv_view_mode = selected
        st.rerun()

    # Scalar Toggle
    current_scalars_enabled = summary_vm.cv_scalars_enabled

    scalars_enabled = st.checkbox(
        label="Enable Scalars",
        value=current_scalars_enabled,
        help="Use Scalars for Annualized Write Off Rates",
    )

    if scalars_enabled != current_scalars_enabled:
        summary_vm.cv_scalars_enabled = scalars_enabled
        st.rerun()


def iteration_table(view_idx: UUID, iteration_id: IterationID, default: bool):
    session: Session = st.session_state["session"]
    summary_vm = session.summary_view_model

    with st.container(
        horizontal=True,
        key=f"summary-comparison-iteration-container-{view_idx}",
    ):
        iteration_id, default = iteration_selector(
            key=f"summary-comparison-iteration-selector-{view_idx}",
            iteration_id=iteration_id,
            default=default,
        )

        if (iteration_id, default) != summary_vm.cv_selected_iterations[view_idx]:
            summary_vm.edit_iteration_view(view_idx, iteration_id, default)
            st.rerun()

        st.button(
            label="",
            key=f"summary-comparison-remove-iteration-view-{view_idx}",
            on_click=summary_vm.remove_iteration_view,
            args=(view_idx,),
            icon=":material/delete:",
            type="primary",
            help="Remove this iteration from the comparison",
        )

    iteration_metric_table(
        iteration_id=iteration_id,
        editable=False,
        default=default,
        show_controls=True,
        filter_ids=summary_vm.cv_filter_ids,
        metric_ids=summary_vm.cv_metric_ids,
        scalars_enabled=summary_vm.cv_scalars_enabled,
        key=f"summary-comparison-iteration-metric-table-{view_idx}",
    )


def comparison():
    session: Session = st.session_state["session"]
    summary_vm = session.summary_view_model

    with st.sidebar:
        sidebar_widgets()

    containers = []

    if summary_vm.cv_view_mode == "list":
        containers = [st.container() for _ in summary_vm.cv_selected_iterations.items()]
    else:
        row_count = (
            len(summary_vm.cv_selected_iterations)
            + len(summary_vm.cv_selected_iterations) % 2
        ) // 2
        for _ in range(row_count):
            containers.extend(st.columns(2))

    for i, (view_idx, (iteration_id, default)) in enumerate(
        summary_vm.cv_selected_iterations.items()
    ):
        with containers[i]:
            iteration_table(view_idx, iteration_id, default)

    sac.divider(label="Add New Iteration", align="center", size="md")

    with st.container(horizontal=True):
        new_iteration_id, new_default = iteration_selector(
            key="summary-comparison-iteration-selector-new",
        )

        st.button(
            label="Add View",
            icon=":material/add:",
            type="primary",
            help="Add this iteration to the comparison",
            key="summary-comparison-add-iteration-view",
            on_click=summary_vm.add_iteration_view,
            args=(new_iteration_id, new_default),
        )


__all__ = ["comparison"]
