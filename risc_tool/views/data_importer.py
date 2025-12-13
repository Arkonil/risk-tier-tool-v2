import pathlib
import typing as t

import streamlit as st

from classes.session import Session
from views.components import variable_selector_widget


def filepath_input_widget(default_value=None) -> pathlib.Path:
    st.markdown("##### File Path:")
    path_text = st.text_input(
        label="#### File Path:", label_visibility="collapsed", value=default_value
    )

    if not path_text:
        return

    path = pathlib.Path(path_text)

    return path


def read_mode_input_widget(default_value) -> t.Literal["CSV", "EXCEL"]:
    st.markdown("##### Read Mode:")
    options = ["CSV", "EXCEL"]

    return st.selectbox(
        label="##### Read Mode:",
        options=options,
        label_visibility="collapsed",
        index=options.index(default_value),
    )


def delimiter_input_widget(default_value=None):
    delimeters = [
        {"name": "comma", "value": ","},
        {"name": "semicolon", "value": ";"},
        {"name": "pipe", "value": "|"},
        {"name": "whitespace", "value": "\\s+"},
    ]

    for i, d in enumerate(delimeters):
        if d["value"] == default_value:
            current_index = i
            break
    else:
        current_index = 0

    def format_delimeter(delimeter):
        return f"{delimeter['name'].capitalize()} ({delimeter['value']})"

    st.markdown("##### Delimiter:")

    return st.selectbox(
        label="##### Delimiter:",
        options=delimeters,
        format_func=format_delimeter,
        label_visibility="collapsed",
        index=current_index,
    )


def sheet_input_widget(default_value):
    label = "##### Sheet Name or Index:"
    st.markdown(label)

    return st.text_input(label=label, value=default_value, label_visibility="collapsed")


def header_row_input_widget(default_value):
    label = "##### Header Row:"
    st.markdown(label)

    return st.number_input(
        label=label,
        min_value=0,
        max_value=1_048_575,  # max number of rows in excel is 1,048,576
        value=default_value,
        label_visibility="collapsed",
    )


def sample_row_count_input_widget(default_value):
    label = "##### Sample Row Count:"
    st.markdown(label)

    return st.number_input(
        label=label,
        min_value=100,
        value=default_value,
        step=100,
        label_visibility="collapsed",
    )


def data_import_option_widgets():
    session: Session = st.session_state["session"]
    data = session.data

    filepath: pathlib.Path = None
    read_mode: t.Literal["CSV", "EXCEL"] = None
    delimiter: dict[str, str] = None
    sheet_name: str = None
    header_row: int = None
    sample_row_count: int = None

    st.markdown("### Data Import Options")

    col1, col2 = st.columns([0.75, 0.25])

    with col1:
        filepath = filepath_input_widget(data.filepath)
    with col2:
        read_mode = read_mode_input_widget(data.read_mode)

    st.write("")

    col1, col2, col3 = st.columns(3)

    with col1:
        if read_mode == "CSV":
            delimiter = delimiter_input_widget(data.delimiter)
        else:
            sheet_name = sheet_input_widget(data.sheet_name)
    with col2:
        header_row = header_row_input_widget(data.header_row)
    with col3:
        sample_row_count = sample_row_count_input_widget(data.sample_row_count)

    st.write("")

    # Info Validation
    if not filepath:
        return

    valid, display_message = data.validate_read_config(filepath, read_mode)

    # UI - Info Validation
    if not valid:
        st.error(display_message)
        return

    st.success(display_message)

    # UI - Import Data
    if data.sample_loaded:
        button_text = "Refresh Sample Data"
        button_icon = ":material/autorenew:"
        button_type = "secondary"

        st.markdown(
            "*Note: Refreshing the data will reset all options and iterations.*"
        )
    else:
        button_text = "Import Sample Data"
        button_icon = ":material/file_upload:"
        button_type = "primary"

    if st.button(button_text, icon=button_icon, type=button_type):
        with st.status("Importing data...", state="running") as status:
            try:
                session.reset()
                data.load_sample(
                    filepath=filepath,
                    read_mode=read_mode,
                    delimiter=delimiter["value"]
                    if isinstance(delimiter, dict)
                    else None,
                    sheet_name=sheet_name,
                    header_row=header_row,
                    nrows=sample_row_count,
                )
            except Exception as error:
                status.update(
                    label="Error Importing Data!", state="error", expanded=True
                )
                st.markdown(f"#### {error}")
                st.exception(error)
            else:
                status.update(label="Data Imported", state="complete", expanded=True)


def sample_data_widget():
    session: Session = st.session_state["session"]
    data = session.data

    st.markdown("### Sample Data")
    st.dataframe(data.sample_df, use_container_width=True)


def variable_selector_container_widget():
    st.markdown("### Variable Selector")
    with st.container(border=True):
        st.write("")
        variable_selector_widget()


def data_importer_view():
    session: Session = st.session_state["session"]
    data = session.data

    st.title("Data Importer")

    st.divider()

    data_import_option_widgets()

    if not data.sample_loaded:
        return

    st.divider()

    sample_data_widget()

    st.divider()

    variable_selector_container_widget()


data_importer_page = st.Page(
    page=data_importer_view,
    title="Data Importer",
    icon=":material/file_upload:",
)


__all__ = ["data_importer_page"]
