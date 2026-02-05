import typing as t

import streamlit as st
from pydantic import ValidationError

from risc_tool.data.models.asset_path import AssetPath
from risc_tool.data.models.data_source import DataSource
from risc_tool.data.session import Session
from risc_tool.pages.data_importer import data_importer_page
from risc_tool.pages.data_importer.data_selector import (
    delimiter_input_widget,
    filepath_input_widget,
    header_row_input_widget,
    read_mode_input_widget,
    sample_row_count_input_widget,
    sheet_input_widget,
)


def file_selector(data_source: DataSource, disabled: bool) -> DataSource | None:
    key = f"file_selector-{data_source.uid}-disabled_{disabled}"

    with st.container(border=True, width="stretch", key=key):
        col1, col2 = st.columns([0.75, 0.25])
        with col1:
            filepath = filepath_input_widget(
                key, data_source.filepath, disabled=disabled
            )
        with col2:
            read_mode = read_mode_input_widget(
                key, data_source.read_mode, disabled=disabled
            )

        col1, col2, col3 = st.columns(3)
        with col1:
            delimiter = ","
            sheet_name = "0"

            if read_mode == "CSV":
                delimiter = delimiter_input_widget(
                    key, data_source.delimiter, disabled=disabled
                )
            else:
                sheet_name = sheet_input_widget(
                    key, data_source.sheet_name, disabled=disabled
                )

        with col2:
            header_row = header_row_input_widget(
                key, data_source.header_row, disabled=disabled
            )

        with col3:
            sample_row_count = sample_row_count_input_widget(
                key, data_source.sample_row_count, disabled=disabled
            )

    if filepath is None:
        return None

    return DataSource(
        uid=data_source.uid,
        filepath=filepath,
        label=data_source.label,
        read_mode=t.cast(t.Literal["CSV", "EXCEL"], read_mode),
        delimiter=delimiter,
        sheet_name=sheet_name,
        header_row=header_row,
        sample_row_count=sample_row_count,
    )


def import_json_page():
    session: Session = st.session_state["session"]
    session_archive_vm = session.session_archive_view_model

    st.button(
        label="Back",
        icon=":material/arrow_back_ios:",
        type="primary",
        on_click=lambda: session_archive_vm.set_home_page_view("welcome"),
    )

    st.title("Import JSON File")

    uploaded_file = st.file_uploader(
        label="Upload JSON File",
        type=[".json"],
        help="This file should contain the exported data from a previous session.",
        label_visibility="collapsed",
        accept_multiple_files=False,
        key="json-file-uploader",
    )

    if uploaded_file is None:
        if session_archive_vm.uploaded_file is None:
            return
        else:
            file_obj = session_archive_vm.uploaded_file
    else:
        session_archive_vm.uploaded_file = uploaded_file
        file_obj = uploaded_file

    with st.container(horizontal=True, vertical_alignment="center"):
        st.success(
            f"File uploaded successfully. File name: `{file_obj.name}`",
            icon=":material/check_circle:",
        )

        def clear_uploaded_file():
            session_archive_vm.clear_uploaded_file()
            del st.session_state["json-file-uploader"]

        with st.container(border=True, width="content"):
            st.button(
                label="",
                icon=":material/close:",
                type="primary",
                on_click=clear_uploaded_file,
                help="Clear the Uploaded file",
            )

    try:
        json_obj = session_archive_vm.validate_json(file_obj.read().decode("utf-8"))
    except ValidationError as error:
        st.exception(error)
        return

    data_source_edits = session_archive_vm.validate_data_sources(json_obj)

    if data_source_edits:
        all_sources_valid = True

        st.divider()

        st.markdown("## Data Source Correction")
        st.markdown(
            "*Following data sources found in the `.json` file are invalid. Please update the read config to complete the import.*"
        )

        for invalid_source, edited_source, error in data_source_edits:
            st.space()
            st.markdown(
                f"#### Data Source #{invalid_source.uid} - {invalid_source.label}"
            )

            col1, col2, col3 = st.columns(
                spec=[0.485, 0.03, 0.485],
                vertical_alignment="center",
            )

            with col1:
                st.markdown("##### Config from `.json` file:")
                file_selector(invalid_source, disabled=True)

            with col2:
                st.image(AssetPath.ARROW_RIGHT, width=50)

            with col3:
                if edited_source is None:
                    edited_source = invalid_source

                st.markdown("##### Edited Config:")
                edited_source = file_selector(edited_source, disabled=False)

            with st.container(horizontal=True):
                if error is not None or edited_source is None:
                    st.error(error, icon=":material/error:")
                    all_sources_valid = False
                else:
                    st.success(
                        f"Validated Data Source: {edited_source.filepath}",
                        icon=":material/check_circle:",
                    )

                if st.button(
                    label="Validate",
                    type="primary",
                    key=f"validate-button-{invalid_source.uid}",
                    help="Validate the data source",
                    icon=":material/check_circle:",
                    disabled=edited_source is None,
                ):
                    if edited_source is not None:
                        session_archive_vm.validate_data_source(edited_source)
                        st.rerun()

        if not all_sources_valid:
            return

    invalid_filters, invalid_metrics, invalid_iterations = (
        session_archive_vm.validate_columns(json_obj)
    )

    import_button_label = "Import"
    import_button_icon = ":material/done_all:"

    if invalid_filters or invalid_metrics or invalid_iterations:
        st.divider()
        st.markdown("## Invalid Items:")
        st.markdown(
            "*Following items cannot be imported from the selected data sources.*"
        )

        import_button_label = "Import Anyway"
        import_button_icon = ":material/warning:"

    if invalid_filters:
        st.markdown("### Filters:")
        for filter_obj, error in invalid_filters:
            with st.container(border=True):
                st.markdown(f"#### Filter #{filter_obj.uid} - {filter_obj.name}")
                st.code(filter_obj.query)
                st.error(error, icon=":material/error:")

    if invalid_metrics:
        st.markdown("### Metrics:")
        for metric_obj, error in invalid_metrics:
            with st.container(border=True):
                st.markdown(f"#### Metric #{metric_obj.uid} - {metric_obj.name}")
                st.code(metric_obj.query)
                st.error(error, icon=":material/error:")

    if invalid_iterations:
        st.markdown("### Iterations:")
        for i, (iteration_id, error) in enumerate(invalid_iterations):
            with st.container(border=True):
                st.markdown(f"#### Iteration #{iteration_id}")
                st.error(error, icon=":material/error:")

    st.divider()

    if st.button(label=import_button_label, icon=import_button_icon, type="primary"):
        data = session_archive_vm.from_dict(json_obj)

        session.dangerously_set_repo_vm(
            data_repository=data["data_repository"],
            filter_repository=data["filter_repository"],
            metric_repository=data["metric_repository"],
            options_repository=data["options_repository"],
            scalar_repository=data["scalar_repository"],
            iterations_repository=data["iterations_repository"],
            iterations_view_model=data["iterations_view_model"],
            summary_view_model=data["summary_view_model"],
        )

        st.switch_page(data_importer_page)


__all__ = ["import_json_page"]
