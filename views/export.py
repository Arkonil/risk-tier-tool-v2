import streamlit as st

from views.export_widgets import (
    show_session_archive_download,
    show_python_code_download,
    show_sas_code_download,
)


def export():
    st.title("Export")

    export_archive, export_python, export_sas = st.tabs([
        "Session Archive",
        "Python Code",
        "SAS Code",
    ])

    with export_archive:
        show_session_archive_download()

    with export_python:
        show_python_code_download()

    with export_sas:
        show_sas_code_download()


export_page = st.Page(
    page=export,
    title="Export",
    icon=":material/file_download:",
)


__all__ = ["export_page"]
