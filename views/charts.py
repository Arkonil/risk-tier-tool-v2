import streamlit as st

from views.components import show_load_data_first_error


def charts():
    if show_load_data_first_error():
        return

    st.title("Charts")


charts_page = st.Page(
    page=charts,
    title="Charts",
    icon=":material/monitoring:",
)


__all__ = ["charts_page"]
