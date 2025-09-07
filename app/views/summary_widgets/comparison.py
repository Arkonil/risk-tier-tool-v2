import typing as t

import streamlit as st

from classes.session import Session
from views.components.metric_selector import metric_selector_widget
from views.iterations_widgets.common import editable_range_widget
from views.components import iteration_selector_widget


def sidebar_widgets():
    session: Session = st.session_state["session"]
    summ_state = session.summary_page_state
    fc = session.filter_container

    def set_metrics(metrics: list[str]):
        summ_state.cv_metrics = metrics

    metric_selector_widget(
        current_metrics=summ_state.cv_metrics,
        set_metrics=set_metrics,
        key=0,
    )

    if st.button(
        label=f"Change to {'Column' if summ_state.cv_view_mode == 'row' else 'Row'} View",
        width="stretch",
        icon=f":material/{'flex_no_wrap' if summ_state.cv_view_mode == 'row' else 'flex_direction'}:",
    ):
        if summ_state.cv_view_mode == "column":
            summ_state.cv_view_mode = "row"
        else:
            summ_state.cv_view_mode = "column"
        st.rerun()

    current_filters = summ_state.cv_filters

    filter_ids = set(
        st.multiselect(
            label="Filter",
            options=list(fc.filters.keys()),
            default=current_filters,
            format_func=lambda filter_id: fc.filters[filter_id].pretty_name,
            label_visibility="collapsed",
            key="filter_selector_summary",
            help="Select filters to apply to the iteration",
            placeholder="Select Filters",
        )
    )

    if filter_ids != current_filters:
        summ_state.cv_filters = filter_ids
        st.rerun()

    scalars_enabled = st.checkbox(
        label="Enable Scalars",
        value=summ_state.cv_scalars_enabled,
        help="Use Scalars for Annualized Write Off Rates",
    )

    if scalars_enabled != summ_state.cv_scalars_enabled:
        summ_state.cv_scalars_enabled = scalars_enabled
        st.rerun()


def iteration_result_widget(
    selected_iteration: t.Literal[0, 1],
    metric_names: list[str],
    scalars_enabled: bool,
    key: int = 0,
):
    session: Session = st.session_state["session"]
    summ_state = session.summary_page_state

    selected_iteration_option = summ_state.selected_iterations[selected_iteration]

    iteration_id, is_default = iteration_selector_widget(
        selected_iteration_id=selected_iteration_option[0],
        is_default=selected_iteration_option[1],
        key=key,
    )

    if (iteration_id, is_default) != selected_iteration_option:
        summ_state.selected_iterations[selected_iteration] = (
            iteration_id,
            is_default,
        )
        st.rerun()

    editable_range_widget(
        iteration_id=iteration_id,
        editable=False,
        scalars_enabled=scalars_enabled,
        metric_names=metric_names,
        default=is_default,
        key=key,
        filter_ids=summ_state.filters,
    )


def comparison_view_widget():
    session: Session = st.session_state["session"]
    summ_state = session.summary_page_state
    all_metrics = session.get_all_metrics()

    with st.sidebar:
        sidebar_widgets()

    metric_names = summ_state.cv_metrics
    metric_names = [
        metric_name for metric_name in metric_names if metric_name in all_metrics
    ]

    if summ_state.cv_view_mode == "row":
        iteration_containers = st.columns(2)
    else:
        iteration_containers = st.container(), st.container()

    for i in range(2):
        with iteration_containers[i]:
            iteration_id, is_default = iteration_selector_widget(
                selected_iteration_id=summ_state.cv_selected_iterations[i][0],
                is_default=summ_state.cv_selected_iterations[i][1],
                key=i,
            )

            if (iteration_id, is_default) != summ_state.cv_selected_iterations[i]:
                summ_state.cv_selected_iterations[i] = (iteration_id, is_default)
                st.rerun()

            editable_range_widget(
                iteration_id=iteration_id,
                default=is_default,
                editable=False,
                scalars_enabled=summ_state.ov_scalars_enabled,
                metric_names=metric_names,
                key=i,
                filter_ids=summ_state.ov_filters,
            )


__all__ = [
    "comparison_view_widget",
]
