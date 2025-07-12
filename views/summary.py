import typing as t

import streamlit as st

from classes.constants import Metric, MetricTableColumn
from classes.session import Session
from views.home import home_page
from views.iterations_widgets.dialogs import metric_selector_dialog_widget
from views.iterations_widgets.common import editable_range_widget
from views.components import variable_selector_dialog_widget, iteration_selector_widget


def sidebar_widgets():
    session: Session = st.session_state["session"]
    summ_state = session.summary_page_state

    st.button(
        label="Set Variables",
        use_container_width=True,
        icon=":material/data_table:",
        help="Select variables for calculations",
        type="primary",
        on_click=variable_selector_dialog_widget,
    )

    st.button(
        label="Set Metrics",
        use_container_width=True,
        icon=":material/functions:",
        help="Set metrics to display in the table",
        on_click=metric_selector_dialog_widget,
    )

    if st.button(
        label=f"Change to {'Column' if summ_state.comparison_view_mode == 'row' else 'Row'} View",
        use_container_width=True,
        icon=f":material/{'flex_no_wrap' if summ_state.comparison_view_mode == 'row' else 'flex_direction'}:",
    ):
        if summ_state.comparison_view_mode == "column":
            summ_state.comparison_view_mode = "row"
        else:
            summ_state.comparison_view_mode = "column"
        st.rerun()

    scalars_enabled = st.checkbox(
        label="Enable Scalars",
        value=summ_state.scalars_enabled,
        help="Use Scalars for Annualized Write Off Rates",
    )

    if scalars_enabled != summ_state.scalars_enabled:
        summ_state.scalars_enabled = scalars_enabled
        st.rerun()

    comparison_mode = st.checkbox(
        label="Comparison Mode",
        value=summ_state.comparison_mode,
        help="Enable comparison mode to select two iterations for comparison",
    )

    if comparison_mode != summ_state.comparison_mode:
        summ_state.comparison_mode = comparison_mode
        st.rerun()


def iteration_result_widget(
    selected_iteration: t.Literal[0, 1],
    metrics: list[Metric],
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
        metrics=metrics,
        default=is_default,
        key=key,
    )


def summary_view():
    session: Session = st.session_state["session"]
    summ_state = session.summary_page_state
    iteration_graph = session.iteration_graph

    if iteration_graph.is_empty:
        st.switch_page(home_page)
        return

    with st.sidebar:
        sidebar_widgets()

    st.title("Summary")

    metrics = summ_state.metrics
    showing_metrics = (
        metrics.sort_values(MetricTableColumn.ORDER)
        .loc[metrics[MetricTableColumn.SHOWING], MetricTableColumn.METRIC]
        .to_list()
    )

    if summ_state.comparison_mode:
        if summ_state.comparison_view_mode == "row":
            iteration_result_widget(
                selected_iteration=0,
                metrics=showing_metrics,
                scalars_enabled=summ_state.scalars_enabled,
                key=0,
            )
            iteration_result_widget(
                selected_iteration=1,
                metrics=showing_metrics,
                scalars_enabled=summ_state.scalars_enabled,
                key=1,
            )

        else:
            col1, col2 = st.columns(2)

            with col1:
                iteration_result_widget(
                    selected_iteration=0,
                    metrics=showing_metrics,
                    scalars_enabled=summ_state.scalars_enabled,
                    key=0,
                )

            with col2:
                iteration_result_widget(
                    selected_iteration=1,
                    metrics=showing_metrics,
                    scalars_enabled=summ_state.scalars_enabled,
                    key=1,
                )

        return

    iteration_result_widget(
        selected_iteration=1,
        metrics=showing_metrics,
        scalars_enabled=summ_state.scalars_enabled,
    )


summary_page = st.Page(
    page=summary_view,
    title="Summary",
    icon=":material/dashboard_2:",
)

__all__ = ["summary_page"]
