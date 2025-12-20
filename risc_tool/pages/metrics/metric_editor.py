import streamlit as st
from code_editor import code_editor

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

    current_data_source_ids = mc.metric_cache.data_source_ids

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

    st.rerun()


def metric_name_selector(current_name: str):
    edited_name = st.text_input(
        label="Metric Name",
        value=current_name,
        label_visibility="collapsed",
        placeholder="Metric Name",
    )

    return edited_name


def query_editor(current_query: str, column_completions: list[dict[str, str | int]]):
    code_editor_output = code_editor(
        # key="code_editor",
        code=current_query,
        lang="python",
        completions=column_completions,
        replace_completer=True,
        keybindings="vscode",
        props={
            "minLines": 13,
            "fontSize": 16,
            "enableSnippets": False,
            "debounceChangePeriod": 100,
        },
        options={
            "showLineNumbers": True,
        },
        response_mode="debounce",
    )

    return code_editor_output


def format_display(
    key: int, use_thousand_sep: bool, is_percentage: bool, decimal_places: int
):
    with st.container(horizontal=True, vertical_alignment="center"):
        original_value = st.text_input(
            label="Original Value",
            key=f"format_display_{key}_original_value",
            value=1234.567,
            label_visibility="collapsed",
        )

        if original_value is None:
            original_value = ""

        try:
            original_value = float(original_value.strip())
        except ValueError:
            original_value = 1230.567

        st.image(AssetPath.ARROW_RIGHT)

        formatter = f"{{:{',' if use_thousand_sep else ''}.{decimal_places}f}}{'%' if is_percentage else ''}"
        st.text_input(
            label="Transformed Value",
            key=f"format_display_{key}_transformed_value",
            value=formatter.format(
                original_value * 100 if is_percentage else original_value
            ),
            disabled=True,
            label_visibility="collapsed",
        )


def format_seletor():
    session: Session = st.session_state["session"]
    mc = session.metric_editor_view_model

    st.markdown("##### Metric Format:")

    use_thousand_sep = st.checkbox(
        "Use Thousand Separator",
        value=mc.metric_cache.use_thousand_sep,
        help="Format numbers with a comma as a thousand separator (e.g., 1,000).",
    )

    if use_thousand_sep != mc.metric_cache.use_thousand_sep:
        mc.set_metric_property(use_thousand_sep=use_thousand_sep)
        st.rerun()

    is_percentage = st.checkbox(
        "Is Percentage",
        value=mc.metric_cache.is_percentage,
        help="Format the metric as a percentage (e.g., 50%).",
    )

    if is_percentage != mc.metric_cache.is_percentage:
        mc.set_metric_property(is_percentage=is_percentage)
        st.rerun()

    decimal_places = st.number_input(
        "Decimal Places",
        min_value=0,
        value=mc.metric_cache.decimal_places,
        help="Number of decimal places to display for the metric.",
    )

    if decimal_places != mc.metric_cache.decimal_places:
        mc.set_metric_property(decimal_places=decimal_places)
        st.rerun()

    with st.container(border=True):
        st.markdown("##### Format Preview:")

        format_display(
            mc.metric_cache.uid,
            use_thousand_sep,
            is_percentage,
            decimal_places,
        )


def on_save():
    session: Session = st.session_state["session"]
    mc = session.metric_editor_view_model

    try:
        mc.save_metric()
    except RuntimeError as e:
        st.toast(body=f"RuntimeError: {e}", icon=":material/error:")


def metric_editor():
    session: Session = st.session_state["session"]
    mc = session.metric_editor_view_model

    back_button()

    st.title("Metric Editor")

    code_editor_container, controller_container = st.columns([2.5, 1])
    error_container = st.container()

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

    # Code Editor
    with code_editor_container:
        data_source_selector()

        edited_name = metric_name_selector(mc.metric_cache.name)
        edited_query = query_editor(mc.metric_cache.query, completions)

        if edited_query["text"] == "":
            edited_query["text"] = mc.metric_cache.query

    # Controls
    with controller_container:

        def on_verify():
            print("on_verify", edited_name, edited_query["text"], edited_query["id"])
            mc.validate_metric(edited_name, edited_query["text"], edited_query["id"])

        st.button(
            label="Verify",
            type="secondary",
            icon=":material/check:",
            width="stretch",
            on_click=on_verify,
        )

        format_seletor()

        disabled_save_button: bool = (
            not mc._is_verified
            or (edited_query["id"] != "" and edited_query["id"] != mc.latest_editor_id)
            or (edited_name != mc.metric_cache.name)
        )

        st.button(
            label="Save",
            type="primary",
            icon=":material/save:",
            use_container_width=True,
            on_click=on_save,
            disabled=disabled_save_button,
        )

    if error_message := mc.error_message():
        error_container.error(error_message)
    else:
        with error_container.expander(label="Metric Object", expanded=False):
            st.write(mc.metric_cache)


__all__ = ["metric_editor"]
