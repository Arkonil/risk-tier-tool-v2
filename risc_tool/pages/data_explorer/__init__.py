import streamlit as st
import streamlit_antd_components as sac

from risc_tool.data.models.enums import DataExplorerTabName
from risc_tool.data.session import Session
from risc_tool.pages.components.load_data_prompt import load_data_prompt
from risc_tool.pages.data_explorer.iv_analysis import iv_analysis


def data_explorer() -> None:
    session: Session = st.session_state["session"]
    data_explorer_view_model = session.data_explorer_view_model

    if not data_explorer_view_model.sample_loaded:
        load_data_prompt()
        return

    st.title("Data Explorer")

    current_tab_name = sac.tabs(
        [sac.TabsItem(tab) for tab in data_explorer_view_model.tab_names],
    )

    if current_tab_name not in DataExplorerTabName:
        raise ValueError(f"Invalid tab name: {current_tab_name}")

    if current_tab_name != data_explorer_view_model.current_tab_name:
        data_explorer_view_model.current_tab_name = DataExplorerTabName(
            current_tab_name
        )
        st.rerun()

    if current_tab_name == DataExplorerTabName.IV_ANALYSIS:
        iv_analysis()


data_explorer_page = st.Page(
    page=data_explorer,
    title="Data Explorer",
    icon=":material/search:",
)


__all__ = ["data_explorer_page"]
