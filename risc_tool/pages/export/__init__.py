import typing as t

import streamlit as st
import streamlit_antd_components as sac

from risc_tool.data.models.enums import ExportTabName
from risc_tool.data.session import Session
from risc_tool.pages.export.code_generator import iteration_code_generator
from risc_tool.pages.export.session_archive import session_archive_download


def export_view():
    session: Session = st.session_state["session"]
    export_vm = session.export_view_model

    st.title("Export")

    if export_vm.no_iteration:
        session_archive_download()
        return

    tabs: list[sac.TabsItem | str | dict] = [
        sac.TabsItem(tab) for tab in export_vm.tab_names
    ]

    selected_tab_index = sac.tabs(
        items=tabs,
        index=export_vm.tab_names.index(export_vm.current_tab_name),
        return_index=True,
        key="export-page-tabs",
    )

    selected_tab_index = t.cast(int, selected_tab_index)
    selected_tab_name = export_vm.tab_names[selected_tab_index]

    if selected_tab_name not in ExportTabName:
        raise ValueError(f"Invalid tab name: {selected_tab_name}")

    if selected_tab_name != export_vm.current_tab_name:
        export_vm.current_tab_name = ExportTabName(selected_tab_name)
        st.rerun()

    if selected_tab_name == ExportTabName.SESSION_ARCHIVE:
        session_archive_download()
    elif selected_tab_name == ExportTabName.PYTHON_CODE:
        iteration_code_generator(language="python")
    elif selected_tab_name == ExportTabName.SAS_CODE:
        iteration_code_generator(language="sas")


export_page = st.Page(
    page=export_view,
    title="Export",
    icon=":material/file_download:",
)


__all__ = ["export_page"]
