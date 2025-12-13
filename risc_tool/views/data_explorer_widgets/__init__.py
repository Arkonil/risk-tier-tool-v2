import streamlit as st
import streamlit_antd_components as sac


from views.components import load_data_error_widget
from views.data_explorer_widgets.iv_analysis import iv_analysis_widget


def explorer_view() -> None:
    if load_data_error_widget():
        return

    st.markdown("# Data Explorer")

    current_tab_index = sac.tabs([sac.TabsItem("IV Analysis")], return_index=True)

    if current_tab_index == 0:
        iv_analysis_widget()


explorer_page = st.Page(
    page=explorer_view,
    title="Data Explorer",
    icon=":material/search:",
)


__all__ = ["explorer_page"]
