import streamlit as st

from views.export_widgets.session_archive import session_archive_download_widget
from views.export_widgets.sas_code import sas_code_generator_widget
from views.export_widgets.python_code import python_code_generator_widget


def export_view():
    st.title("Export")

    export_archive, export_python, export_sas = st.tabs([
        "Session Archive",
        "Python Code",
        "SAS Code",
    ])

    with export_archive:
        session_archive_download_widget()

    with export_python:
        python_code_generator_widget()

    with export_sas:
        sas_code_generator_widget()


export_page = st.Page(
    page=export_view,
    title="Export",
    icon=":material/file_download:",
)


__all__ = ["export_page"]
