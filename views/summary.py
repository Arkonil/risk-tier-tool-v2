import typing as t

import pandas as pd
import streamlit as st

from classes.session import Session
from views.iterations_widgets.dialogs import show_metric_selector
from views.iterations_widgets.single_var_iteration import show_edited_range


def show_welcome_page():
    st.title("Risk Tier Development Tool")

    st.write("")
    st.write("")

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("##### Import Data to get started")
            st.write("Supported file formats: `\".csv\"`, `\".xlsx\"`, `\".xls\"`")
            if st.button("Import Data", icon=":material/file_upload:", type="primary"):
                st.switch_page("views/data_importer.py")

    with col2:
        with st.container(border=True):
            st.markdown("##### Import a `.rt.zip` file to continue working on it")
            st.write("Supported file formats: `\".zip\"`")
            if st.button("Import `.rt.zip` file", icon=":material/file_upload:"):
                st.switch_page("views/data_importer.py")

def show_iteration_result(selected_iteration: t.Literal[1, 2], metrics: pd.Series, scalars_enabled: bool, key: int = 0):
    session: Session = st.session_state['session']
    home_page_state = session.home_page_state
    iteration_graph = session.iteration_graph

    selected_iteration_id = home_page_state.selected_iterations[selected_iteration - 1]

    iteration_ids = list(iteration_graph.iterations.keys())

    def format_func(iteration_id: str) -> str:
        if iteration_id is None:
            return "No Iteration Selected"

        iteration = iteration_graph.iterations[iteration_id]
        if iteration.name:
            return f"Iteration {iteration_id} - {iteration.name}"

        return f"Iteration {iteration_id} - {iteration.variable.name}"

    iteration_id = st.selectbox(
        label="Select Iteration",
        options=iteration_ids,
        key=f"selected_iteration_{selected_iteration}",
        index=iteration_ids.index(selected_iteration_id) if selected_iteration_id in iteration_ids else 0,
        format_func=format_func,
    )

    if iteration_id != selected_iteration_id:
        home_page_state.selected_iterations[selected_iteration - 1] = iteration_id
        st.rerun()

    show_edited_range(
        iteration_id=iteration_id,
        editable=False,
        scalars_enabled=scalars_enabled,
        metrics=metrics,
        key=key,
    )


def show_summary_page():
    session: Session = st.session_state['session']
    home_page_state = session.home_page_state
    iteration_graph = session.iteration_graph

    if iteration_graph.is_empty:
        show_welcome_page()
        return

    st.title("Summary")

    metrics_df = home_page_state.metrcis
    showing_metrics = metrics_df.sort_values("order").loc[metrics_df['showing'], 'metric']

    with st.sidebar:
        if st.button(
            label="Set Metrics",
            use_container_width=True,
            icon=":material/functions:",
            help="Set metrics to display in the table",
        ):
            show_metric_selector(metrics_df)

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

    if comparison_mode:
        if home_page_state.comparison_view_mode == "row":
            show_iteration_result(selected_iteration=1, metrics=showing_metrics, scalars_enabled=scalars_enabled, key=1)
            show_iteration_result(selected_iteration=2, metrics=showing_metrics, scalars_enabled=scalars_enabled, key=2)

        else:
            col1, col2 = st.columns(2)

            with col1:
                show_iteration_result(selected_iteration=1, metrics=showing_metrics, scalars_enabled=scalars_enabled, key=1)

            with col2:
                show_iteration_result(selected_iteration=2, metrics=showing_metrics, scalars_enabled=scalars_enabled, key=2)

        return
    
    show_iteration_result(selected_iteration=1, metrics=showing_metrics, scalars_enabled=scalars_enabled)

show_summary_page()
