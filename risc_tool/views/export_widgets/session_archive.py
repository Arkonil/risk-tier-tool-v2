import io
import streamlit as st

from classes.session import Session
from classes.constants import AssetPath


def session_archive_download_widget():
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

    with open(AssetPath.SESSION_EXPORT_DOC, "r") as f:
        st.markdown(f.read())


__all__ = ["session_archive_download_widget"]
