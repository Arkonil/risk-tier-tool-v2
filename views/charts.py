import streamlit as st

from views.components import load_data_error_widget


def charts_view():
    if load_data_error_widget():
        return

    st.title("Charts")


charts_page = st.Page(
    page=charts_view,
    title="Charts",
    icon=":material/monitoring:",
)


__all__ = ["charts_page"]
