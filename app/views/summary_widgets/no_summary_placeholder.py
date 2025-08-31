import streamlit as st

from classes.constants import AssetPath
from views.iterations_widgets import iteration_graph_page


@st.cache_data
def get_no_iteration_image():
    with open(AssetPath.NO_ITERATION_ICON) as svgfile:
        svg = svgfile.read()

    return svg


def no_summary_placeholder_widget(key: int = 0) -> bool:
    svg = get_no_iteration_image()

    st.markdown(
        f"""
        <div style="display: flex; flex-direction: column; align-items: center; gap: 1em; margin: 7.5em 0 1em;">
            <div style="height: 12em; width: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center;">{svg}</div>
            <div style="display: flex; flex-direction: column; align-items: center; font-size: 2em; color: rgb(89, 89, 89);">No Iterations Created Yet</div>
        </div>
    """,
        unsafe_allow_html=True,
    )
    _, col, _ = st.columns([1, 0.4, 1])

    with col:
        if st.button(
            "Create Iteration",
            key=key,
            use_container_width=True,
            type="primary",
            icon=":material/add:",
        ):
            st.switch_page(iteration_graph_page)


__all__ = [
    "no_summary_placeholder_widget",
]
