import streamlit as st

from risc_tool.data.session import Session
from risc_tool.utils.json_formatter import format_json_string


def session_archive_download():
    session: Session = st.session_state["session"]
    session_archive_vm = session.session_archive_view_model

    st.markdown("### Download Session Archive as a `.json` File")

    st.space()

    st.download_button(
        label="Download `session_archive.json`",
        data=format_json_string(
            session_archive_vm.create_dict().model_dump_json(), max_width=120
        ),
        file_name="session_archive.json",
        mime="application/json",
        icon=":material/file_download:",
    )


__all__ = ["session_archive_download"]
