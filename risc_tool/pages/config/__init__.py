import streamlit as st

from risc_tool.pages.config.risk_segment_details import risk_seg_details_selector
from risc_tool.pages.config.scalar_editor import scalar_calculation


def config() -> None:
    st.title("Configurations")

    risk_seg_details_selector()
    st.space()
    scalar_calculation()


config_page = st.Page(
    page=config,
    title="Configurations",
    icon=":material/settings:",
)

__all__ = ["config_page"]
