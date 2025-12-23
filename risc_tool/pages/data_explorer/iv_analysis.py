import altair as alt
import pandas as pd
import streamlit as st

from risc_tool.data.session import Session


def data_source_selector():
    session: Session = st.session_state["session"]
    data_explorer_vm = session.data_explorer_view_model

    current_data_source_ids = data_explorer_vm.iv_data_sources

    iv_data_sources = st.multiselect(
        label="Select Data Sources",
        options=data_explorer_vm.all_data_source_ids,
        default=current_data_source_ids,
        format_func=data_explorer_vm.get_data_source_label,
        key="select_data_source_ids",
        width="stretch",
        label_visibility="collapsed",
        placeholder="Select Data Sources",
    )

    if set(iv_data_sources) == set(current_data_source_ids):
        return

    data_explorer_vm.iv_data_sources = iv_data_sources
    st.rerun()


def iv_bar_chart(dataframe: pd.DataFrame):
    x = alt.X(
        "variable:N",
        sort=alt.EncodingSortField(field="iv", op="max", order="descending"),
        axis=alt.Axis(
            title="Variable",
            labelAngle=0,
        ),
    )

    y = alt.Y(
        "iv:Q",
        axis=alt.Axis(title="Information Value (IV)"),
    )

    tooltip = [
        alt.Tooltip("variable", title="Variable"),
        alt.Tooltip("iv", title="Information Value", format=".2f"),
    ]

    text_labels = (
        alt.Chart(dataframe)
        .mark_text(
            align="center",
            dy=-15,
            color="white" if st.context.theme.type == "dark" else "black",
        )
        .encode(x=x, y=y, text=alt.Text("iv:Q", format=".2f"))
    )

    bars = (
        alt.Chart(dataframe).mark_bar(color="#44c1ca").encode(x=x, y=y, tooltip=tooltip)
    )

    chart = (bars + text_labels).configure_axis(grid=False).properties(height=500)

    return chart


def iv_analysis():
    session: Session = st.session_state["session"]
    de_view_model = session.data_explorer_view_model

    st.subheader("Information Value")
    st.space()

    chart_container, control_container = st.columns([2.5, 1])
    error_container = st.container()

    with control_container:
        # Data Source Selector
        data_source_selector()

        # Target Variable Selector
        available_target_variables = [None] + de_view_model.available_target_columns
        current_target_index = available_target_variables.index(
            de_view_model.iv_current_target
        )
        target_variable = st.selectbox(
            label="Target Variable",
            options=available_target_variables,
            index=current_target_index,
        )

        # Input Variable Selector
        available_input_variables = de_view_model.available_input_columns
        input_variables = st.multiselect(
            label="Variables",
            options=available_input_variables,
            default=de_view_model.iv_current_variables,
        )

        # Filter Selector
        all_filters = de_view_model.all_filters
        filter_ids = st.multiselect(
            label="Filters",
            options=list(all_filters.keys()),
            default=de_view_model.iv_current_filter_ids,
            format_func=lambda filter_uid: all_filters[filter_uid].name,
        )

        if st.button(
            label="Save Config",
            width="stretch",
            type="secondary",
            icon=":material/save:",
        ):
            if any([
                de_view_model.iv_current_target != target_variable,
                de_view_model.iv_current_variables != input_variables,
                de_view_model.iv_current_filter_ids != filter_ids,
            ]):
                de_view_model.iv_current_target = target_variable
                de_view_model.iv_current_variables = input_variables
                de_view_model.iv_current_filter_ids = filter_ids
                st.rerun()

    with chart_container:
        iv_df = de_view_model.get_iv_df(
            target_variable=target_variable,
            input_variables=input_variables,
            filter_ids=filter_ids,
        )

        if iv_df is not None:
            chart = iv_bar_chart(iv_df)
            st.altair_chart(chart)

    with error_container:
        for error in de_view_model.iv_errors:
            st.error(error)

        for warning in de_view_model.iv_warnings:
            st.warning(warning)


__all__ = ["iv_analysis"]
