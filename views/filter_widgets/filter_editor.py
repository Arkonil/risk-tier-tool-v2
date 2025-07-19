import math

import streamlit as st
import altair as alt
from code_editor import code_editor

from classes.constants import AssetPath
from classes.filter import Filter
from classes.session import Session

math_functions = [
    "sin",
    "cos",
    "exp",
    "log",
    "expm1",
    "expm1",
    "log1p",
    "sqrt",
    "sinh",
    "cosh",
    "tanh",
    "arcsin",
    "arccos",
    "arctan",
    "arccosh",
    "arcsinh",
    "arctanh",
    "abs",
    "arctan2",
    "log10",
]


def back_button():
    session: Session = st.session_state["session"]
    fc = session.filter_container

    if st.button(
        label="Back",
        icon=":material/arrow_back_ios:",
        type="primary",
    ):
        fc.set_mode("view")
        st.rerun()


def sidebar_widgets():
    st.link_button(
        label="Pandas Documentation",
        url="https://pandas.pydata.org/docs/user_guide/enhancingperf.html#expression-evaluation-via-eval",
        use_container_width=True,
        icon=":material/open_in_new:",
    )


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
                "meta": "Function",
                "name": f,
                "score": 100,
            },
            math_functions,
        )
    )

    return code_editor(
        code=code,
        lang="python",
        completions=completions,
        replace_completer=True,
        keybindings="vscode",
        props={
            "minLines": 16,
            "fontSize": 16,
            "enableSnippets": False,
            "debounceChangePeriod": 1,
            "placeholder": "Write your filter query here...",
        },
        options={
            "showLineNumbers": True,
        },
        # ghost_text="Write your filter query here...",
        response_mode=["debounce"],
    )


def pie_chart_widget(filter_: Filter | None):
    if filter_ is None:
        return

    counts = filter_.mask.value_counts().to_frame().reset_index()
    counts.columns = ["Condition Satisfies", "Count"]

    base_chart = alt.Chart(counts).encode(
        theta=alt.Theta(field="Count", type="quantitative").stack(True),
        color=alt.Color(field="Condition Satisfies", type="nominal"),
    )

    pie_chart = base_chart.mark_arc(
        outerRadius=80,
        innerRadius=40,
        cornerRadius=3,
        padAngle=0.04,
        thetaOffset=-math.pi / 2,
    )

    legends = base_chart.mark_text(
        outerRadius=115,
        size=16,
        thetaOffset=-math.pi / 2,
    ).encode(text=alt.Text(field="Count", type="quantitative", format=","))

    chart = pie_chart + legends

    st.altair_chart(chart, use_container_width=False)


def quick_reference_widget():
    with open(AssetPath.QUERY_REFERENCE) as fp:
        text = fp.read()

    with st.expander("Quick Reference"):
        st.markdown(text, unsafe_allow_html=True)


def filter_editor():
    session: Session = st.session_state["session"]
    data = session.data
    fc = session.filter_container

    with st.sidebar:
        sidebar_widgets()

    back_button()

    st.markdown("# Create Filter")

    if fc.current_filter_edit_id is not None:
        code = fc.filters[fc.current_filter_edit_id].query
        name = fc.filters[fc.current_filter_edit_id].name
    else:
        code = ""
        name = ""

    code_editor_container, controller_container = st.columns([2.5, 1])
    error_container = st.container()

    # Code Editor
    with code_editor_container:
        name = st.text_input(
            label="Filter Name",
            value=name,
            label_visibility="collapsed",
            placeholder="Filter Name",
        )
        query = query_editor_widget(code)

        if query["text"] == "":
            query["text"] = code

    # Controls
    new_filter = None

    with controller_container:
        verify_button = st.button(
            "Verify",
            type="secondary",
            icon=":material/check:",
            use_container_width=True,
        )

    if verify_button and (query["text"] or code):
        try:
            new_filter = fc.validate_filter(
                filter_id=fc.current_filter_edit_id,
                name=name,
                query=query["text"] or code,
                data=data,
            )

        except SyntaxError as error:
            msg = handle_syntax_error(error)
            error_container.error(msg)
        except ValueError as error:
            msg = handle_value_error(error)
            error_container.error(msg)

    with controller_container:
        save_button = st.button(
            "Save",
            type="primary",
            icon=":material/save:",
            disabled=new_filter is None,
            use_container_width=True,
        )

    if save_button:
        fc.create_filter(
            filter_id=fc.current_filter_edit_id,
            name=name,
            query=query["text"],
            data=data,
        )
        fc.set_mode("view")
        st.rerun()

    with controller_container:
        pie_chart_widget(new_filter)

    quick_reference_widget()


__all__ = [
    "filter_editor",
]
