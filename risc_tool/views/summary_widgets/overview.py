import streamlit as st

from classes.session import Session
from views.components.iteration_selector import iteration_selector_widget
from views.components.metric_selector import metric_selector_widget
from views.iterations_widgets.common import editable_range_widget


def sidebar_widgets():
    session: Session = st.session_state["session"]
    summ_state = session.summary_page_state
    fc = session.filter_container

    def set_metrics(metrics: list[str]):
        summ_state.ov_metrics = metrics

    metric_selector_widget(
        current_metrics=summ_state.ov_metrics,
        set_metrics=set_metrics,
        key=0,
    )

    current_filters = summ_state.ov_filters

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
        summ_state.ov_filters = filter_ids
        st.rerun()

    scalars_enabled = st.checkbox(
        label="Enable Scalars",
        value=summ_state.ov_scalars_enabled,
        help="Use Scalars for Annualized Write Off Rates",
    )

    if scalars_enabled != summ_state.ov_scalars_enabled:
        summ_state.ov_scalars_enabled = scalars_enabled
        st.rerun()


def overview_widget():
    session: Session = st.session_state["session"]
    summ_state = session.summary_page_state
    all_metrics = session.get_all_metrics()

    with st.sidebar:
        sidebar_widgets()

    metric_names = summ_state.ov_metrics
    metric_names = [
        metric_name for metric_name in metric_names if metric_name in all_metrics
    ]

    iteration_id, is_default = iteration_selector_widget(
        selected_iteration_id=summ_state.ov_selected_iteration_id,
        is_default=summ_state.ov_selected_iteration_default,
        key=0,
    )

    if (iteration_id, is_default) != (
        summ_state.ov_selected_iteration_id,
        summ_state.ov_selected_iteration_default,
    ):
        summ_state.ov_selected_iteration_id = iteration_id
        summ_state.ov_selected_iteration_default = is_default
        st.rerun()

    editable_range_widget(
        iteration_id=iteration_id,
        default=is_default,
        editable=False,
        scalars_enabled=summ_state.ov_scalars_enabled,
        metric_names=metric_names,
        key=0,
        filter_ids=summ_state.ov_filters,
    )


__all__ = [
    "overview_widget",
]
