import typing as t

import streamlit as st

from risc_tool.data.session import Session
from risc_tool.pages.components.iteration_selector import iteration_selector


def iteration_code_generator(language: t.Literal["sas", "python"]):
    session: Session = st.session_state["session"]
    export_vm = session.export_view_model

    code_preview_container, control_container = st.columns([2.5, 1])

    with control_container:
        st.markdown("##### Select Iteration")
        selected_iteration_id = iteration_selector(
            key=f"{language}-code-iteration-selector"
        )

        warning_container = st.container()

        mode = st.segmented_control(
            label="Default/Edited",
            options=["Default", "Edited"],
            selection_mode="single",
            default="Edited",
            width="stretch",
            label_visibility="collapsed",
            key=f"{language}-code-mode-selector",
        )

        if language == "sas":
            use_macro = st.checkbox(
                "Use SAS Macro variables",
                value=True,
                key=f"{language}-code-use-macro-selector",
            )
        else:
            use_macro = True

        if mode is None:
            warning_container.warning(
                "Select either 'Default' or 'Edited' mode.", icon=":material/warning:"
            )
            return

        if language == "sas":
            code = export_vm.get_sas_code(
                iteration_id=selected_iteration_id,
                default=(mode == "Default"),
                use_macro=use_macro,
            )
        elif language == "python":
            code = export_vm.get_python_code(
                iteration_id=selected_iteration_id,
                default=(mode == "Default"),
            )

    with code_preview_container:
        st.code(code, language=language, line_numbers=True, height=550)
