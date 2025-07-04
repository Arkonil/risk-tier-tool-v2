import typing as t

import streamlit as st

from classes.constants import Metric, MetricTableColumn
from classes.session import Session
from views.home import home_page
from views.iterations_widgets.dialogs import show_metric_selector
from views.iterations_widgets.single_var_iteration import show_edited_range
from views.components import show_variable_selector_dialog


def sidebar_options():
    session: Session = st.session_state["session"]
    home_page_state = session.home_page_state

    st.button(
        label="Set Variables",
        use_container_width=True,
        icon=":material/data_table:",
        help="Select variables for calculations",
        type="primary",
        on_click=show_variable_selector_dialog,
    )

    st.button(
        label="Set Metrics",
        use_container_width=True,
        icon=":material/functions:",
        help="Set metrics to display in the table",
        on_click=show_metric_selector,
    )

    if st.button(
        label=f"Change to {'Column' if home_page_state.comparison_view_mode == 'row' else 'Row'} View",
        use_container_width=True,
        icon=f":material/{'flex_no_wrap' if home_page_state.comparison_view_mode == 'row' else 'flex_direction'}:",
    ):
        if home_page_state.comparison_view_mode == "column":
            home_page_state.comparison_view_mode = "row"
        else:
            home_page_state.comparison_view_mode = "column"
        st.rerun()

    scalars_enabled = st.checkbox(
        label="Enable Scalars",
        value=home_page_state.scalars_enabled,
        help="Use Scalars for Annualized Write Off Rates",
    )

    if scalars_enabled != home_page_state.scalars_enabled:
        home_page_state.scalars_enabled = scalars_enabled
        st.rerun()

    comparison_mode = st.checkbox(
        label="Comparison Mode",
        value=home_page_state.comparison_mode,
        help="Enable comparison mode to select two iterations for comparison",
    )

    if comparison_mode != home_page_state.comparison_mode:
        home_page_state.comparison_mode = comparison_mode
        st.rerun()


def show_iteration_result(
    selected_iteration: t.Literal[0, 1],
    metrics: list[Metric],
    scalars_enabled: bool,
    key: int = 0,
):
    session: Session = st.session_state["session"]
    home_page_state = session.home_page_state
    iteration_graph = session.iteration_graph

    selected_iteration_option = home_page_state.selected_iterations[selected_iteration]

    iteration_ids = list(iteration_graph.iterations.keys())
    all_options = [
        (iter_id, is_default)
        for iter_id in iteration_ids
        for is_default in [True, False]
    ]

    selected_option_index = 0
    for i, option in enumerate(all_options):
        if option == selected_iteration_option:
            selected_option_index = i
            break

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

    if (iteration_id, is_default) != selected_iteration_option:
        home_page_state.selected_iterations[selected_iteration] = (
            iteration_id,
            is_default,
        )
        st.rerun()

    show_edited_range(
        iteration_id=iteration_id,
        editable=False,
        scalars_enabled=scalars_enabled,
        metrics=metrics,
        default=is_default,
        key=key,
    )


def summary():
    session: Session = st.session_state["session"]
    home_page_state = session.home_page_state
    iteration_graph = session.iteration_graph

    if iteration_graph.is_empty:
        st.switch_page(home_page)
        return

    with st.sidebar:
        sidebar_options()

    st.title("Summary")

    metrics = home_page_state.metrics
    showing_metrics = (
        metrics.sort_values(MetricTableColumn.ORDER)
        .loc[metrics[MetricTableColumn.SHOWING], MetricTableColumn.METRIC]
        .to_list()
    )

    if home_page_state.comparison_mode:
        if home_page_state.comparison_view_mode == "row":
            show_iteration_result(
                selected_iteration=0,
                metrics=showing_metrics,
                scalars_enabled=home_page_state.scalars_enabled,
                key=0,
            )
            show_iteration_result(
                selected_iteration=1,
                metrics=showing_metrics,
                scalars_enabled=home_page_state.scalars_enabled,
                key=1,
            )

        else:
            col1, col2 = st.columns(2)

            with col1:
                show_iteration_result(
                    selected_iteration=0,
                    metrics=showing_metrics,
                    scalars_enabled=home_page_state.scalars_enabled,
                    key=0,
                )

            with col2:
                show_iteration_result(
                    selected_iteration=1,
                    metrics=showing_metrics,
                    scalars_enabled=home_page_state.scalars_enabled,
                    key=1,
                )

        return

    show_iteration_result(
        selected_iteration=1,
        metrics=showing_metrics,
        scalars_enabled=home_page_state.scalars_enabled,
    )


summary_page = st.Page(
    page=summary,
    title="Summary",
    icon=":material/dashboard_2:",
)

__all__ = ["summary_page"]
