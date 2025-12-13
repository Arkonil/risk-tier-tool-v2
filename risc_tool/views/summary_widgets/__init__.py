import streamlit as st
import streamlit_antd_components as sac

from classes.session import Session
from views.components.load_data_prompt import load_data_error_widget
from views.summary_widgets.no_summary_placeholder import no_summary_placeholder_widget
from views.summary_widgets.overview import overview_widget
from views.summary_widgets.comparison import comparison_view_widget
from views.summary_widgets.crosstab import crosstab_widget


def summary_view():
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph
    summ_state = session.summary_page_state

    st.title("Summary")

    if load_data_error_widget():
        return

    if iteration_graph.is_empty:
        no_summary_placeholder_widget()
        return

    current_page_index = sac.tabs(
        [
            sac.TabsItem("Overview", icon="eye"),
            sac.TabsItem("Comparison", icon="arrow-left-right"),
            sac.TabsItem("Crosstab", icon="window-sidebar"),
        ],
        return_index=True,
        index=summ_state.current_page_index,
        key="summary_tabs",
    )

    if summ_state.current_page_index != current_page_index:
        summ_state.current_page_index = current_page_index
        st.rerun()

    if current_page_index == 0:
        overview_widget()
    elif current_page_index == 1:
        comparison_view_widget()
    elif current_page_index == 2:
        crosstab_widget()


summary_page = st.Page(
    page=summary_view,
    title="Summary",
    icon=":material/dashboard_2:",
)

__all__ = ["summary_page"]
