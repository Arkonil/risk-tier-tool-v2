import math

import altair as alt
import streamlit as st

from risc_tool.data.models.asset_path import AssetPath
from risc_tool.data.models.filter import Filter
from risc_tool.data.session import Session
from risc_tool.pages.components.query_editor import query_editor

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
    filter_editor_vm = session.filter_editor_view_model

    if st.button(
        label="Back",
        icon=":material/arrow_back_ios:",
        type="primary",
    ):
        filter_editor_vm.set_mode("view")
        st.rerun()


def sidebar_widgets():
    st.link_button(
        label="Pandas Documentation",
        url="https://pandas.pydata.org/docs/user_guide/enhancingperf.html#expression-evaluation-via-eval",
        width="stretch",
        icon=":material/open_in_new:",
    )


def filter_name_selector(current_name: str):
    edited_name = st.text_input(
        label="Filter Name",
        value=current_name,
        label_visibility="collapsed",
        placeholder="Filter Name",
    )

    return edited_name


def pie_chart_widget(filter_obj: Filter | None):
    if filter_obj is None or filter_obj.mask is None:
        return

    counts = filter_obj.mask.value_counts().to_frame().reset_index()
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

    st.altair_chart(chart, width="stretch")


def quick_reference_widget():
    with open(AssetPath.FILTER_QUERY_REFERENCE) as fp:
        text = fp.read()

    with st.expander("Quick Reference"):
        st.markdown(text, unsafe_allow_html=True)


def on_save():
    session: Session = st.session_state["session"]
    filter_editor_vm = session.filter_editor_view_model

    try:
        filter_editor_vm.save_filter()
    except RuntimeError as e:
        st.toast(body=f"RuntimeError: {e}", icon=":material/error:")


def filter_editor():
    session: Session = st.session_state["session"]
    filter_editor_vm = session.filter_editor_view_model

    with st.sidebar:
        sidebar_widgets()

    back_button()

    st.title("Create Filter")

    code_editor_container, controller_container = st.columns([2.5, 1])
    error_container = st.container()

    # Code Completions
    completions = filter_editor_vm.get_column_completions()
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

    # Code Editor
    with code_editor_container:
        edited_name = filter_name_selector(filter_editor_vm.filter_cache.name)
        edited_query = query_editor(filter_editor_vm.filter_cache.query, completions)

        if edited_query["text"] == "":
            edited_query["text"] = filter_editor_vm.filter_cache.query

    # Controls
    with controller_container:

        def on_verify():
            filter_editor_vm.validate_filter(
                name=edited_name,
                query=edited_query["text"],
                latest_editor_id=edited_query["id"],
            )

        st.button(
            label="Verify",
            type="secondary",
            icon=":material/check:",
            width="stretch",
            on_click=on_verify,
        )

        pie_chart_widget(filter_editor_vm.filter_cache)

        disabled_save_button: bool = (
            # Current filter in memory is not verified.
            not filter_editor_vm.is_verified
            # "" -> verify button was clicked. so `is_verified` above should take care of it
            # fvm.latest_editor_id -> no change since last validation
            or (
                edited_query["id"] != ""
                and edited_query["id"] != filter_editor_vm.latest_editor_id
            )
            # Name has changed so need to verify again
            or (edited_name != filter_editor_vm.filter_cache.name)
        )

        st.button(
            label="Save",
            type="primary",
            icon=":material/save:",
            width="stretch",
            on_click=on_save,
            disabled=disabled_save_button,
        )

    if error_message := filter_editor_vm.error_message():
        error_container.error(error_message)
    else:
        with error_container.expander(label="Filter Object", expanded=False):
            st.write(filter_editor_vm.filter_cache)

    quick_reference_widget()


__all__ = ["filter_editor"]
