import streamlit as st

from classes.data import Data
from classes.session import Session


def metric_text_widget(column, text: str):
    column.html(
        f"""
            <div style="display: flex; justify-content: center; font-size: 1.5em; font-weight: bold;">
                <span>{text}</span>
            </div>
        """
    )


def unit_wrt_off_selector_widget(data: Data):
    col1, col2, col3, col4, col5 = st.columns([4, 1, 5, 1, 5])

    metric_text_widget(col1, "# Bad Rate %")
    metric_text_widget(col2, "=")
    options = [None] + data.sample_df.columns.to_list()
    current_index = data.get_col_pos(data.var_unt_wrt_off)

    if current_index is not None:
        current_index += 1

    var_unt_wrt_off = col3.selectbox(
        label="#WO_var",
        options=options,
        label_visibility="collapsed",
        index=current_index,
        format_func=lambda v: "" if v is None else v,
        placeholder="# Bad Rate Variable",
    )
    metric_text_widget(col4, "/")
    metric_text_widget(col5, "# Accounts")

    return var_unt_wrt_off


def dlr_wrt_off_selector_widget(data: Data):
    col1, col2, col3, col4, col5 = st.columns([4, 1, 5, 1, 5])

    metric_text_widget(col1, "$ Bad Rate %")
    metric_text_widget(col2, "=")
    options = [None] + data.sample_df.columns.to_list()
    current_index = data.get_col_pos(data.var_dlr_wrt_off)

    if current_index is not None:
        current_index += 1

    var_dlr_wrt_off = col3.selectbox(
        label="$WO_var",
        options=options,
        label_visibility="collapsed",
        index=current_index,
        format_func=lambda v: "" if v is None else v,
        placeholder="$ Bad Rate Variable",
    )

    metric_text_widget(col4, "/")

    options = [None] + data.sample_df.columns.to_list()
    current_index = data.get_col_pos(data.var_avg_bal)

    if current_index is not None:
        current_index += 1

    var_avg_bal = col5.selectbox(
        label="Avg_Bal",
        options=options,
        label_visibility="collapsed",
        index=current_index,
        format_func=lambda v: "" if v is None else v,
        placeholder="Avg Balance Variable",
    )

    return var_dlr_wrt_off, var_avg_bal


def mob_selector_widget(data: Data):
    col1, col2, col3, _ = st.columns([4, 1, 5, 6])

    metric_text_widget(col1, "MOB")
    metric_text_widget(col2, "=")
    mob = col3.number_input(
        label="MOB_var",
        value=data.current_rate_mob,
        min_value=1,
        max_value=100,
        step=1,
        label_visibility="collapsed",
        format="%d",
        placeholder="Months on Book",
    )

    return mob


def lifetime_rate_mob_selector_widget(data: Data):
    col1, col2, col3, _ = st.columns([4, 1, 5, 6])

    metric_text_widget(col1, "Lifetime MOB")
    metric_text_widget(col2, "=")
    lifetime_rate_mob = col3.number_input(
        label="Lifetime MOB",
        value=data.lifetime_rate_mob,
        min_value=data.current_rate_mob,
        max_value=100,
        step=1,
        label_visibility="collapsed",
        format="%d",
        placeholder="Lifetime Rate Months on Book",
    )

    return lifetime_rate_mob


def variable_selector_widget():
    session: Session = st.session_state["session"]
    data = session.data

    var_unt_wrt_off = unit_wrt_off_selector_widget(data)
    unt_error_container = st.container()
    var_dlr_wrt_off, var_avg_bal = dlr_wrt_off_selector_widget(data)
    dlr_error_container = st.container()
    mob = mob_selector_widget(data)
    mob_error_container = st.container()
    lifetime_rate_mob = lifetime_rate_mob_selector_widget(data)

    # TODO: Check if the logic works as intended
    needs_rerun = False
    if var_unt_wrt_off != data.var_unt_wrt_off:
        try:
            data.var_unt_wrt_off = var_unt_wrt_off
            needs_rerun = True
        except ValueError as e:
            unt_error_container.error(f"Error: {e}")

    if var_dlr_wrt_off != data.var_dlr_wrt_off:
        try:
            data.var_dlr_wrt_off = var_dlr_wrt_off
            needs_rerun = True
        except ValueError as e:
            dlr_error_container.error(f"Error: {e}")

    if var_avg_bal != data.var_avg_bal:
        try:
            data.var_avg_bal = var_avg_bal
            needs_rerun = True
        except ValueError as e:
            dlr_error_container.error(f"Error: {e}")

    if mob != data.current_rate_mob:
        try:
            data.current_rate_mob = mob
            needs_rerun = True
        except ValueError as e:
            mob_error_container.error(f"Error: {e}")

    if lifetime_rate_mob != data.lifetime_rate_mob:
        data.lifetime_rate_mob = lifetime_rate_mob
        needs_rerun = True

    if needs_rerun:
        try:
            st.rerun(scope="fragment")
        except st.errors.StreamlitAPIException:
            st.rerun()


@st.dialog("Set Variables", width="large")
def variable_selector_dialog_widget():
    with st.container(border=True):
        variable_selector_widget()

    *_, col = st.columns(6)

    with col:
        if st.button("Submit", type="primary", use_container_width=True):
            st.rerun()


__all__ = ["variable_selector_widget", "variable_selector_dialog_widget"]
