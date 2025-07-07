import io
import streamlit as st

from classes.session import Session
from classes.constants import README_CONTENT


def show_session_archive_download():
    session: Session = st.session_state["session"]

    st.markdown("### Download Session Archive as `.rt.zip` File")

    zip_buffer = None
    if st.button(
        label="Create Download Link",
        icon=":material/file_download:",
    ):
        zip_buffer = session.to_rt_zip_buffer()

    st.download_button(
        label="Download `session_archive.rt.zip`",
        data=zip_buffer if zip_buffer else io.BytesIO(),
        file_name="session_archive.rt.zip",
        mime="application/zip",
        disabled=zip_buffer is None,
        icon=":material/file_download:",
    )

    st.markdown(README_CONTENT)


__all__ = ["show_session_archive_download"]
