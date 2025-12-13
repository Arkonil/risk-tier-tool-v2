import streamlit as st
from code_editor import code_editor

from classes.constants import AssetPath
from classes.session import Session
from classes.metric import QueryValidator


def back_button():
    session: Session = st.session_state["session"]
    mc = session.metric_container

    if st.button(
        label="Back",
        icon=":material/arrow_back_ios:",
        type="primary",
    ):
        mc.set_mode("view")
        st.rerun()


def handle_syntax_error(error: SyntaxError):
    return f"""
        **SyntaxError**: {error.msg}
        **Line**: {error.lineno}
            {error.text.rstrip()}
            {" " * (error.offset - 1)}{"^" * (error.end_offset - error.offset + 1)}
    """.replace("\n", "\n\n")


def handle_value_error(error: ValueError):
    return f"""
        **ValueError**: {error}
    """.replace("\n", "\n\n")


def query_editor_widget(code: str):
    session: Session = st.session_state["session"]
    data = session.data

    # Code Completions
    completions = []

    ## Column names
    completions += data.column_name_completions

    ## Functions
    completions += list(
        map(
            lambda f: {
                "caption": f,
                "value": f,
                "meta": "function",
                "name": f,
                "score": 100,
            },
            QueryValidator.allowed_functions | QueryValidator.allowed_series_methods,
        )
    )

    return code_editor(
        code=code,
        lang="python",
        completions=completions,
        replace_completer=True,
        keybindings="vscode",
        props={
            "minLines": 13,
            "fontSize": 16,
            "enableSnippets": False,
            "debounceChangePeriod": 1,
            "placeholder": "Write your metric logic here...",
        },
        options={
            "showLineNumbers": True,
        },
        response_mode=["debounce"],
    )


def metric_editor():
    session: Session = st.session_state["session"]
    data = session.data
    mc = session.metric_container

    back_button()

    st.markdown("# Metric Editor")

    if mc.current_metric_edit_name is not None:
        code = mc.metrics[mc.current_metric_edit_name].query
        name = mc.metrics[mc.current_metric_edit_name].name
        use_thousand_sep = mc.metrics[mc.current_metric_edit_name].use_thousand_sep
        is_percentage = mc.metrics[mc.current_metric_edit_name].is_percentage
        decimal_places = mc.metrics[mc.current_metric_edit_name].decimal_places
    else:
        code = ""
        name = ""
        use_thousand_sep = True
        is_percentage = False
        decimal_places = 2

    code_editor_container, controller_container = st.columns([2.5, 1])
    error_container = st.container()

    # Code Editor
    with code_editor_container:
        name = st.text_input(
            label="Metric Name",
            value=name,
            label_visibility="collapsed",
            placeholder="Metric Name",
        )
        query = query_editor_widget(code)

        if query["text"] == "":
            query["text"] = code

    # Controls
    new_metric = None

    with controller_container:
        verify_button = st.button(
            "Verify",
            type="secondary",
            icon=":material/check:",
            use_container_width=True,
        )

    if verify_button and (query["text"] or code):
        try:
            new_metric = mc.validate_metric(
                name=name,
                query=query["text"] or code,
                use_thousand_sep=use_thousand_sep,
                is_percentage=is_percentage,
                decimal_places=decimal_places,
                data=data,
            )

        except SyntaxError as error:
            msg = handle_syntax_error(error)
            error_container.error(msg)
        except ValueError as error:
            msg = handle_value_error(error)
            error_container.error(msg)

    with controller_container:
        use_thousand_sep = st.checkbox(
            "Use Thousand Separator",
            value=use_thousand_sep,
            help="Format numbers with a comma as a thousand separator (e.g., 1,000).",
        )

        is_percentage = st.checkbox(
            "Is Percentage",
            value=is_percentage,
            help="Format the metric as a percentage (e.g., 50%).",
        )

        decimal_places = st.number_input(
            "Decimal Places",
            min_value=0,
            value=decimal_places,
            help="Number of decimal places to display for the metric.",
        )

        with st.container(border=True):
            st.markdown("##### Format Preview:")

            with st.container(horizontal=True, vertical_alignment="center"):
                original_value = st.text_input(
                    "Original Value",
                    value=1234.567,
                    label_visibility="collapsed",
                )

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

        save_button = st.button(
            "Save",
            type="primary",
            icon=":material/save:",
            use_container_width=True,
            disabled=new_metric is None,
        )

    if save_button:
        mc.create_metric(
            name=name,
            query=query["text"] or code,
            use_thousand_sep=use_thousand_sep,
            is_percentage=is_percentage,
            decimal_places=decimal_places,
            data=data,
        )
        mc.set_mode("view")
        st.rerun()


__all__ = [
    "metric_editor",
]
