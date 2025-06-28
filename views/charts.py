import streamlit as st


def charts(): ...


charts_page = st.Page(
    page=charts,
    title="Charts",
    icon=":material/monitoring:",
)


__all__ = ["charts_page"]
