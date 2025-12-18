import streamlit as st
from code_editor import code_editor
from streamlit.errors import StreamlitAPIException

from risc_tool.data.models.asset_path import AssetPath
from risc_tool.data.models.metric import MetricQueryValidator
from risc_tool.data.session import Session


def back_button():
    session: Session = st.session_state["session"]
    mc = session.metric_editor_view_model

    if st.button(
        label="Back",
        icon=":material/arrow_back_ios:",
        type="primary",
    ):
        mc.set_mode("view")
        st.rerun()


def data_source_selector():
    session: Session = st.session_state["session"]
    mc = session.metric_editor_view_model

    current_data_source_ids = mc.metric_cache.valid_data_source_ids

    selected_data_source_ids = st.multiselect(
        label="Select Data Sources",
        options=mc.all_data_source_ids,
        default=current_data_source_ids,
        format_func=mc.get_data_source_label,
        key="select_data_source_ids",
        width="stretch",
        label_visibility="collapsed",
        placeholder="Select Data Sources",
    )

    if set(selected_data_source_ids) == set(current_data_source_ids):
        return

    mc.selected_data_source_ids = selected_data_source_ids

    try:
        st.rerun(scope="fragment")
    except StreamlitAPIException:
        st.rerun()


def metric_name_selector():
    session: Session = st.session_state["session"]
    mc = session.metric_editor_view_model

    current_name = mc.metric_cache.name

    edited_name = st.text_input(
        label="Metric Name",
        value=current_name,
        label_visibility="collapsed",
        placeholder="Metric Name",
    )

    if edited_name == current_name:
        return

    mc.set_name(edited_name)
    st.rerun()


@st.fragment
def query_editor() -> None:
    session: Session = st.session_state["session"]
    mc = session.metric_editor_view_model

    # Code Completions
    completions = mc.get_column_completions()
    completions += list(
        map(
            lambda f: {
                "caption": f,
                "value": f,
                "meta": "function",
                "name": f,
                "score": 100,
            },
            MetricQueryValidator.allowed_functions
            | MetricQueryValidator.allowed_series_methods,
        )
    )

    current_query = mc.metric_cache.query

    code_editor_output = code_editor(
        code=current_query,
        lang="python",
        completions=completions,
        replace_completer=True,
        keybindings="vscode",
        props={
            "minLines": 13,
            "fontSize": 16,
            "enableSnippets": False,
            # "debounceChangePeriod": 100,
            "placeholder": "Write your metric logic here...",
        },
        options={
            "showLineNumbers": True,
        },
        # response_mode="debounce",
    )

    if code_editor_output["text"] == current_query or code_editor_output["text"] == "":
        return

    mc.set_query(code_editor_output["text"])
    st.rerun(scope="fragment")


def format_seletor():
    session: Session = st.session_state["session"]
    mc = session.metric_editor_view_model

    use_thousand_sep = st.checkbox(
        "Use Thousand Separator",
        value=mc.metric_cache.use_thousand_sep,
        help="Format numbers with a comma as a thousand separator (e.g., 1,000).",
    )

    if use_thousand_sep != mc.metric_cache.use_thousand_sep:
        mc.metric_cache.use_thousand_sep = use_thousand_sep
        st.rerun()

    is_percentage = st.checkbox(
        "Is Percentage",
        value=mc.metric_cache.is_percentage,
        help="Format the metric as a percentage (e.g., 50%).",
    )

    if is_percentage != mc.metric_cache.is_percentage:
        mc.metric_cache.is_percentage = is_percentage
        st.rerun()

    decimal_places = st.number_input(
        "Decimal Places",
        min_value=0,
        value=mc.metric_cache.decimal_places,
        help="Number of decimal places to display for the metric.",
    )

    if decimal_places != mc.metric_cache.decimal_places:
        mc.metric_cache.decimal_places = decimal_places
        st.rerun()

    with st.container(border=True):
        st.markdown("##### Format Preview:")

        with st.container(horizontal=True, vertical_alignment="center"):
            original_value = st.text_input(
                "Original Value",
                value=1234.567,
                label_visibility="collapsed",
            )

            if original_value is None:
                original_value = ""

            try:
                original_value = float(original_value)
            except ValueError:
                original_value = 1234.567

            st.image(AssetPath.ARROW_RIGHT)

            formatter = f"{{:{',' if use_thousand_sep else ''}.{decimal_places}f}}{'%' if is_percentage else ''}"
            st.text_input(
                "Transformed Value",
                value=formatter.format(
                    original_value * 100 if is_percentage else original_value
                ),
                disabled=True,
                label_visibility="collapsed",
            )


# def handle_syntax_error(error: SyntaxError):
#     error_msgs = [
#         f"**SyntaxError**: {error.msg}",
#         f"**Line**: {error.lineno}",
#     ]

#     if error.text:
#         error_msgs.append(error.text.rstrip())

#     if error.offset is not None and error.end_offset is not None:
#         error_msgs.append(
#             f"{' ' * (error.offset - 1)}{'^' * (error.end_offset - error.offset + 1)}"
#         )

#     return "\n\n".join(error_msgs)


# def handle_value_error(error: ValueError):
#     return f"""
#         **ValueError**: {error}
#     """.replace("\n", "\n\n")


def metric_editor():
    session: Session = st.session_state["session"]
    mc = session.metric_editor_view_model

    back_button()

    st.title("Metric Editor")

    code_editor_container, controller_container = st.columns([2.5, 1])
    error_container = st.container()

    # Code Editor
    with code_editor_container:
        data_source_selector()
        metric_name_selector()
        query_editor()

    # Controls
    with controller_container:
        st.button(
            label="Verify",
            type="secondary",
            icon=":material/check:",
            width="stretch",
            on_click=mc.validate_metric,
        )

        format_seletor()

        st.button(
            label="Save",
            type="primary",
            icon=":material/save:",
            use_container_width=True,
            on_click=mc.save_metric,
            # disabled=new_metric is None,
        )

    with error_container:
        st.error(mc.error_message())


__all__ = ["metric_editor"]
