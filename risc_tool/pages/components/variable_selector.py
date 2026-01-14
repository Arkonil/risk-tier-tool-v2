import typing as t

import streamlit as st
from streamlit.errors import StreamlitAPIException

from risc_tool.data.session import Session


def metric_text_widget(column, text: str):
    column.html(
        f"""
            <div style="display: flex; justify-content: center; font-size: 1.5em; font-weight: bold;">
                <span>{text}</span>
            </div>
        """
    )


def data_source_selector() -> None:
    session: Session = st.session_state["session"]
    variable_selector_vm = session.variable_selector_view_model

    current_data_source_ids = variable_selector_vm.selected_data_source_ids

    col1, col2, col3 = st.columns([4, 1, 11], gap=None)
    metric_text_widget(col1, "Data Sources")
    metric_text_widget(col2, "=")
    with col3:
        selected_data_source_ids = st.multiselect(
            label="Select Data Sources",
            options=variable_selector_vm.all_data_source_ids,
            default=current_data_source_ids,
            format_func=variable_selector_vm.get_data_source_label,
            key="select_data_source_ids",
            width="stretch",
            label_visibility="collapsed",
            placeholder="Select Data Sources",
        )

    if set(selected_data_source_ids) == set(current_data_source_ids):
        return

    variable_selector_vm.selected_data_source_ids = selected_data_source_ids

    try:
        st.rerun(scope="fragment")
    except StreamlitAPIException:
        st.rerun()


def column_selector(column_usage: t.Literal["unt_bad", "dlr_bad", "avg_bal"]) -> None:
    session: Session = st.session_state["session"]
    variable_selector_vm = session.variable_selector_view_model

    options = variable_selector_vm.available_columns

    current_column = variable_selector_vm.get_variable(column_usage)
    current_index = options.index(current_column)

    if current_index == 0:
        current_index = None

    if column_usage == "unt_bad":
        placeholder = r"# Bad Rate Variable"
    elif column_usage == "dlr_bad":
        placeholder = "$ Bad Rate Variable"
    elif column_usage == "avg_bal":
        placeholder = "Avg Balance Variable"
    else:
        placeholder = ""

    selected_column = st.selectbox(
        label=f"var_selector_{column_usage}",
        options=options,
        label_visibility="collapsed",
        index=current_index,
        format_func=lambda v: "" if v is None else v,
        placeholder=placeholder,
    )

    if current_column == selected_column:
        return

    variable_selector_vm.set_variable(column_usage, selected_column)

    try:
        st.rerun(scope="fragment")
    except StreamlitAPIException:
        st.rerun()


def mob_selector(mob_type: t.Literal["current", "lifetime"]) -> None:
    session: Session = st.session_state["session"]
    variable_selector_vm = session.variable_selector_view_model

    current_mob = variable_selector_vm.get_mob(mob_type)

    selected_mob = st.number_input(
        label=f"mob_selector_{mob_type}",
        value=current_mob,
        min_value=1,
        max_value=100,
        step=1,
        label_visibility="collapsed",
        format="%d",
        placeholder="Months on Book",
    )

    if current_mob == selected_mob:
        return

    variable_selector_vm.set_mob(mob_type, selected_mob)

    try:
        st.rerun(scope="fragment")
    except StreamlitAPIException:
        st.rerun()


def unt_bad_selector() -> None:
    col1, col2, col3, col4, col5 = st.columns([4, 1, 5, 1, 5], gap=None)
    metric_text_widget(col1, "# Bad Rate %")
    metric_text_widget(col2, "=")
    with col3:
        column_selector("unt_bad")
    metric_text_widget(col4, "/")
    metric_text_widget(col5, "# Accounts")


def dlr_bad_selector() -> None:
    col1, col2, col3, col4, col5 = st.columns([4, 1, 5, 1, 5], gap=None)
    metric_text_widget(col1, "$ Bad Rate %")
    metric_text_widget(col2, "=")
    with col3:
        column_selector("dlr_bad")
    metric_text_widget(col4, "/")
    with col5:
        column_selector("avg_bal")


def current_mob_selector() -> None:
    col1, col2, col3, _ = st.columns([4, 1, 5, 6], gap=None)
    metric_text_widget(col1, "MOB")
    metric_text_widget(col2, "=")
    with col3:
        mob_selector("current")


def lifetime_mob_selector() -> None:
    col1, col2, col3, _ = st.columns([4, 1, 5, 6], gap=None)
    metric_text_widget(col1, "Lifetime MOB")
    metric_text_widget(col2, "=")
    with col3:
        mob_selector("lifetime")


def variable_selector():
    data_source_selector()
    unt_bad_selector()
    dlr_bad_selector()
    current_mob_selector()
    lifetime_mob_selector()


@st.dialog("Set Variables", width="large", on_dismiss="rerun")
def variable_selector_dialog():
    with st.container(border=True):
        variable_selector()

    _, col = st.columns(2)

    with col:
        if st.button("Submit", type="primary", width="stretch"):
            st.rerun()


__all__ = ["variable_selector", "variable_selector_dialog"]
