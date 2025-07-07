import streamlit as st

from classes.session import Session


@st.cache_data(show_spinner=True)
def get_no_data_image():
    with open("assets/no-data-error.svg") as svgfile:
        svg = svgfile.read()

    return svg


def load_data_error_widget(key: int = 0) -> bool:
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph
    data = session.data

    if not data.sample_loaded:
        svg = get_no_data_image()

        st.markdown(
            f"""
            <div style="display: flex; flex-direction: column; align-items: center; gap: 1em; margin: 7.5em 0 1em;">
                <div style="height: 16em; width: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center;">{svg}</div>
                <div style="display: flex; flex-direction: column; align-items: center; font-size: 2.5em; color: rgb(89, 89, 89);">Data is not Loaded</div>
            </div>
        """,
            unsafe_allow_html=True,
        )
        _, col, _ = st.columns([1, 0.4, 1])

        with col:
            if st.button(
                "Load Data",
                key=key,
                use_container_width=True,
                type="primary",
            ):
                iteration_graph.select_graph_view()

                from views.data_importer import data_importer_page

                st.switch_page(data_importer_page)
            return True

    return False


__all__ = ["load_data_error_widget"]
