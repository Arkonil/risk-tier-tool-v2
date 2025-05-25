import streamlit as st

from classes.data import Data
from classes.session import Session

def show_text(column, text: str):
    column.html(
        f"""
            <div style="display: flex; justify-content: center; font-size: 1.5em; font-weight: bold;">
                <span>{text}</span>
            </div>
        """
    )

def show_unit_wrt_off_selector(data: Data):
    col1, col2, col3, col4, col5 = st.columns([4, 1, 5, 1, 5])

    show_text(col1, "# Write Off %")
    show_text(col2, "=")
    options = [None] + data.sample_df.columns.to_list()
    current_index = data.get_col_pos(data.var_unt_wrt_off)

    if current_index is not None:
        current_index += 1

    data.var_unt_wrt_off = col3.selectbox(
        label="#WO_var",
        options=options,
        label_visibility="collapsed",
        index=current_index,
        format_func=lambda v: "" if v is None else v,
        placeholder="# Write Off Variable"
    )
    show_text(col4, "/")
    show_text(col5, "# Accounts")

def show_dlr_wrt_off_selector(data: Data):
    col1, col2, col3, col4, col5 = st.columns([4, 1, 5, 1, 5])

    show_text(col1, "$ Write Off %")
    show_text(col2, "=")
    options = [None] + data.sample_df.columns.to_list()
    current_index = data.get_col_pos(data.var_dlr_wrt_off)

    if current_index is not None:
        current_index += 1

    data.var_dlr_wrt_off = col3.selectbox(
        label="$WO_var",
        options=options,
        label_visibility="collapsed",
        index=current_index,
        format_func=lambda v: "" if v is None else v,
        placeholder="$ Write Off Variable"
    )

    show_text(col4, "/")

    options = [None] + data.sample_df.columns.to_list()
    current_index = data.get_col_pos(data.var_avg_bal)

    if current_index is not None:
        current_index += 1

    data.var_avg_bal = col5.selectbox(
        label="Avg_Bal",
        options=options,
        label_visibility="collapsed",
        index=current_index,
        format_func=lambda v: "" if v is None else v,
        placeholder="Avg Balance Variable"
    )


def show_variable_selector():
    session: Session = st.session_state['session']
    data = session.data

    show_unit_wrt_off_selector(data)
    show_dlr_wrt_off_selector(data)

@st.dialog("Set Variables", width="large")
def show_variable_selector_dialog():
    with st.container(border=True):
        show_variable_selector()

    if st.button("Submit"):
        st.rerun()
