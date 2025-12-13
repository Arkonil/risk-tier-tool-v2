import streamlit as st

from classes.constants import AssetPath
from classes.session import Session


# @st.cache_data(show_spinner=True)
def get_no_data_image():
    with open(AssetPath.NO_FILTER_ICON) as svgfile:
        svg = svgfile.read()

    return svg


def no_filter_placeholder_widget(key: int = 0) -> bool:
    session: Session = st.session_state["session"]
    fc = session.filter_container

    svg = get_no_data_image()

    st.markdown(
        f"""
        <div style="display: flex; flex-direction: column; align-items: center; gap: 1em; margin: 7.5em 0 1em;">
            <div style="height: 12em; width: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center;">{svg}</div>
            <div style="display: flex; flex-direction: column; align-items: center; font-size: 2em; color: rgb(89, 89, 89);">No Filters Created Yet</div>
        </div>
    """,
        unsafe_allow_html=True,
    )
    _, col, _ = st.columns([1, 0.4, 1])

    with col:
        if st.button(
            "Create Filter",
            key=key,
            use_container_width=True,
            type="primary",
            icon=":material/add:",
        ):
            fc.set_mode("edit")
            st.rerun()


__all__ = [
    "no_filter_placeholder_widget",
]
