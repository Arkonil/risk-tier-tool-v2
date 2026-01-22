import typing as t

import streamlit as st
import streamlit_antd_components as sac

from risc_tool.data.models.enums import SummaryPageTabName
from risc_tool.data.session import Session
from risc_tool.pages.components.load_data_prompt import load_data_prompt
from risc_tool.pages.summary.comparison import comparison
from risc_tool.pages.summary.crosstab import crosstab
from risc_tool.pages.summary.no_summary_placeholder import no_summary_placeholder
from risc_tool.pages.summary.overview import overview


def summary_view():
    session: Session = st.session_state["session"]
    summary_vm = session.summary_view_model

    if not summary_vm.sample_loaded:
        load_data_prompt()
        return

    if summary_vm.no_iteration:
        no_summary_placeholder()
        return

    st.title("Summary")

    tabs: list[sac.TabsItem | str | dict] = [
        sac.TabsItem(page_name) for page_name in summary_vm.tab_names
    ]

    selected_tab_index = sac.tabs(
        items=tabs,
        index=summary_vm.tab_names.index(summary_vm.current_tab_name),
        return_index=True,
        key="summary-page-tabs",
        on_change=print,
    )

    selected_tab_index = t.cast(int, selected_tab_index)
    selected_tab_name = summary_vm.tab_names[selected_tab_index]

    if selected_tab_name not in summary_vm.tab_names:
        raise ValueError(f"Invalid tab name: {selected_tab_name}")

    if selected_tab_name != summary_vm.current_tab_name:
        summary_vm.current_tab_name = selected_tab_name
        st.rerun()

    if selected_tab_name == SummaryPageTabName.OVERVIEW:
        overview()
    elif selected_tab_name == SummaryPageTabName.COMPARISON:
        comparison()
    elif selected_tab_name == SummaryPageTabName.CROSSTAB:
        crosstab()


summary_page = st.Page(
    page=summary_view,
    title="Summary",
    icon=":material/dashboard_2:",
)

__all__ = ["summary_page"]
