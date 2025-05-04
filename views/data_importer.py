import pathlib
import typing as t

import streamlit as st

from classes.data import Data

def filepath_input(default_value=None) -> pathlib.Path:
    st.markdown("##### File Path:")
    path_text = st.text_input(
        label="#### File Path:",
        label_visibility="collapsed",
        value=default_value
    )

    if not path_text:
        return

    path = pathlib.Path(path_text)

    return path

def read_mode_input(default_value) -> t.Literal["CSV", "EXCEL"]:
    st.markdown('##### Read Mode:')
    options = ['CSV', 'EXCEL']

    return st.selectbox(
        label='##### Read Mode:',
        options=options,
        label_visibility="collapsed",
        index=options.index(default_value)
    )

def delimeter_input(default_value=None):
    delimeters = [
        { "name": "comma", "value": "," },
        { "name": "semicolon", "value": ";" },
        { "name": "pipe", "value": "|" },
        { "name": "whitespace", "value": "\\s+" }
    ]

    for i, d in enumerate(delimeters):
        if d['value'] == default_value:
            current_index = i
            break
    else:
        current_index = 0

    def format_delimeter(delimeter):
        return f"{delimeter['name'].capitalize()} ({delimeter['value']})"

    st.markdown('##### Delimeter:')

    return st.selectbox(
        label='##### Delimeter:',
        options=delimeters,
        format_func=format_delimeter,
        label_visibility="collapsed",
        index=current_index
    )

def sheet_input(default_value):
    label = '##### Sheet Name or Index:'
    st.markdown(label)

    return st.text_input(
        label=label,
        value=default_value,
        label_visibility="collapsed"
    )

def header_row_input(default_value):
    label = '##### Header Row:'
    st.markdown(label)

    return st.number_input(
        label=label,
        min_value=0,
        max_value=1_048_575, # max number of rows in excel is 1,048,576
        value=default_value,
        label_visibility="collapsed",
    )

def sample_row_count_input(default_value):
    label = '##### Sample Row Count:'
    st.markdown(label)

    return st.number_input(
        label=label,
        min_value=100,
        value=default_value,
        step=100,
        label_visibility="collapsed",
    )

def show_data_importer_page():

    # Declarations
    data: Data = st.session_state['session'].data

    filepath: pathlib.Path = None
    read_mode: t.Literal["CSV", "EXCEL"] = None
    delimeter: dict[str, str] = None
    sheet_name: str = None
    header_row: int = None
    sample_row_count: int = None

    # UI - File Info
    st.title("Import Data")

    st.write("")

    col1, col2 = st.columns([0.75, 0.25])

    with col1:
        filepath = filepath_input(data.filepath)

    with col2:
        read_mode = read_mode_input(data.read_mode)

    st.write("")

    col1, col2, col3 = st.columns(3)

    with col1:
        if read_mode == 'CSV':
            delimeter = delimeter_input(data.delimiter)
        else:
            sheet_name = sheet_input(data.sheet_name)
    with col2:
        header_row = header_row_input(data.header_row)
    with col3:
        sample_row_count = sample_row_count_input(data.sample_row_count)

    st.write("")

    # Info Validation
    validation_result = data.validate_read_config(filepath, read_mode)
    if not validation_result:
        return

    valid, display_message = validation_result

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
    else:
        button_text = "Import Sample Data"
        button_icon = ":material/file_upload:"
        button_type = "primary"

    if st.button(button_text, icon=button_icon, type=button_type):
        with st.status('Importing data...') as status:
            try:
                data.reset()
                data.load_sample(
                    filepath=filepath,
                    read_mode=read_mode,
                    delimiter=delimeter['value'] if isinstance(delimeter, dict) else None,
                    sheet_name=sheet_name,
                    header_row=header_row,
                    nrows=sample_row_count
                )
            # pylint: disable=broad-exception-caught
            except Exception as error:
                status.update(label="Error Importing Data!", state="error", expanded=True)
                st.markdown(f"#### {error}")
                st.exception(error)
            # pylint: enable=broad-exception-caught
            else:
                status.update(label="Data Imported", state="complete", expanded=True)

    if not data.sample_loaded:
        return

    st.markdown("#### Sample Data")
    st.dataframe(data.sample_df, width=2000)

    st.markdown("#### Variables")

    with st.container(border=True, key="final_application_status"):
        st.markdown("###### Application Status Variable")
        data.var_app_status = st.selectbox(
            label="Application Status",
            options=data.sample_df.columns,
            index=data.get_col_pos(data.var_app_status),
            label_visibility="collapsed"
        )

        if data.var_app_status is not None:
            unq_vals = set(data.load_column(data.var_app_status).unique())

            col1, col2 = st.columns(2, vertical_alignment="bottom")

            with col1:
                selected_vals = st.multiselect("Approved", options=unq_vals, default=unq_vals)
                data.var_app_status_accepted = set(selected_vals)
                data.var_app_status_declined = unq_vals - data.var_app_status_accepted

            with col2:
                if data.var_app_status_declined:
                    selected_vals = st.multiselect(
                        "Declined",
                        options=data.var_app_status_declined,
                        disabled=True,
                        default=data.var_app_status_declined
                    )
                else:
                    st.write("All values are selected.")

            if not data.var_app_status_accepted:
                st.error("Please select at least one value for `Approved`.")

        st.divider()

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.markdown("###### # Write Off flag")
            data.var_unt_wrt_off = st.selectbox(
                label="#WO",
                options=data.sample_df.columns,
                index=data.get_col_pos(data.var_unt_wrt_off),
                label_visibility="collapsed"
            )

        with col2:
            st.markdown("###### $ Write Off Balance")
            data.var_dlr_wrt_off = st.selectbox(
                label="$WO",
                options=data.sample_df.columns,
                index=data.get_col_pos(data.var_dlr_wrt_off),
                label_visibility="collapsed"
            )

        with col3:
            st.markdown("###### Average Recievable")
            data.var_avg_bal = st.selectbox(
                label="avg_bal",
                options=data.sample_df.columns,
                index=data.get_col_pos(data.var_avg_bal),
                label_visibility="collapsed"
            )

        with col4:
            st.markdown("###### MOB")
            data.mob = int(st.number_input(
                label="mob",
                label_visibility="collapsed",
                min_value=1, value=data.mob
            ))

        with col5:
            st.markdown("###### Revenue")
            data.var_revenue = st.selectbox(
                label="revenue",
                options=data.sample_df.columns,
                index=data.get_col_pos(data.var_revenue),
                label_visibility="collapsed"
            )

        if not data.all_variable_selected():
            st.error("Please select all variables.")


show_data_importer_page()
