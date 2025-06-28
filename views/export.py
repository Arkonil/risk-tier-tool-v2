import io
import streamlit as st

from classes.session import Session
from classes.constants import README_CONTENT


def export():
    session: Session = st.session_state["session"]

    st.title("Export")

    with st.container(border=True):
        st.markdown("### Export Session Data as `.rt.zip` File")

        zip_buffer = None
        if st.button(
            label="Create Download Link",
            icon=":material/file_download:",
        ):
            zip_buffer = session.to_rt_zip_buffer()

        st.download_button(
            label="Download `rt_export.rt.zip`",
            data=zip_buffer if zip_buffer else io.BytesIO(),
            file_name="rt_export.rt.zip",
            mime="application/zip",
            disabled=zip_buffer is None,
            icon=":material/file_download:",
        )

        st.markdown(README_CONTENT)
        # st.success("Downloading started. Please wait...")


export_page = st.Page(
    page=export,
    title="Export",
    icon=":material/file_download:",
)


__all__ = ["export_page"]
