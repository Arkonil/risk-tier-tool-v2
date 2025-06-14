import pathlib as p

import numpy as np
import pandas as pd
import streamlit as st

from classes.constants import RTDetCol, IterationType, VariableType
from classes.session import Session
from views.iterations_widgets.navigation import show_navigation_buttons


def show_load_data_first_error() -> bool:
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph
    data = session.data

    if not data.sample_loaded:
        st.error("Please load data first")
        if st.button("Load Data"):
            iteration_graph.select_graph_view()
            st.switch_page(p.Path(__file__).parent.parent / "data_importer.py")
        return True

    return False


def show_iteration_creation_page() -> None:
    if show_load_data_first_error():
        return

    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph
    options = session.options

    show_navigation_buttons()

    st.markdown("# Create New Iteration")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("##### Select Variable")
        variable_name = st.selectbox(
            label="Select a variable",
            options=session.data.sample_df.columns,
            label_visibility="collapsed",
        )

        st.markdown("##### Iteration Name")
        iteration_name = st.text_input(
            label="Iteration Name", label_visibility="collapsed"
        )

        st.markdown("##### Variable Type")
        variable_dtype = st.selectbox(
            label="Variable Type",
            options=list(map(lambda m: m.value, VariableType)),
            label_visibility="collapsed",
        )

        st.markdown("##### ")
        auto_band = st.checkbox("Create Automatic Banding", value=True)

    if iteration_graph.current_iter_create_mode == IterationType.SINGLE:
        previous_node_id = None
        rt_details = options.risk_tier_details.copy()
    else:
        previous_node_id = iteration_graph.current_iter_create_parent_id
        rt_details = iteration_graph.get_risk_tier_details(previous_node_id).copy()

    # Column Modification
    rt_details[RTDetCol.LOWER_RATE] = (rt_details[RTDetCol.LOWER_RATE] * 100).map(
        lambda v: "-Infinity" if np.isinf(v) else f"{v:.2f}%"
    )

    rt_details[RTDetCol.UPPER_RATE] = (rt_details[RTDetCol.UPPER_RATE] * 100).map(
        lambda v: "+Infinity" if np.isinf(v) else f"{v:.2f}%"
    )

    rt_details[RTDetCol.MAF_DLR] = rt_details[RTDetCol.MAF_DLR].map(
        lambda v: f"{v * 100:.1f} %"
    )
    rt_details[RTDetCol.MAF_ULR] = rt_details[RTDetCol.MAF_ULR].map(
        lambda v: f"{v * 100:.1f} %"
    )

    rt_details[RTDetCol.SELECTED] = True

    disabled_columns = rt_details.columns
    if iteration_graph.current_iter_create_mode == IterationType.SINGLE:
        disabled_columns = disabled_columns.drop(RTDetCol.SELECTED)

    rt_details_styled = rt_details.style
    idx = pd.IndexSlice

    for row_index in rt_details.index:
        font_color = rt_details.loc[row_index, RTDetCol.FONT_COLOR]
        bg_color = rt_details.loc[row_index, RTDetCol.BG_COLOR]
        rt_details_styled = rt_details_styled.set_properties(
            **{
                "color": font_color,
                "background-color": bg_color,
            },
            subset=idx[row_index, RTDetCol.RISK_TIER],
        )

    coloumn_config = {
        RTDetCol.SELECTED: st.column_config.CheckboxColumn(
            label=RTDetCol.SELECTED,
        ),
        RTDetCol.RISK_TIER: st.column_config.TextColumn(
            label=RTDetCol.RISK_TIER,
        ),
        RTDetCol.LOWER_RATE: st.column_config.TextColumn(
            label=RTDetCol.LOWER_RATE,
        ),
        RTDetCol.UPPER_RATE: st.column_config.TextColumn(
            label=RTDetCol.UPPER_RATE,
        ),
    }

    with col2:
        st.markdown("##### Select Risk Tiers")

        edited_rt_details = st.data_editor(
            data=rt_details_styled,
            column_order=[
                RTDetCol.SELECTED,
                RTDetCol.RISK_TIER,
                RTDetCol.LOWER_RATE,
                RTDetCol.UPPER_RATE,
                # RTDetCol.MAF_DLR,
                # RTDetCol.MAF_ULR,
            ],
            column_config=coloumn_config,
            use_container_width=True,
            hide_index=True,
            disabled=disabled_columns,
        )

        risk_tier_details = options.risk_tier_details.loc[
            edited_rt_details[edited_rt_details[RTDetCol.SELECTED]].index
        ].reset_index(drop=False)

    if st.button("Create", type="primary"):
        variable = session.data.load_column(variable_name)

        variable_dtype = VariableType(variable_dtype)
        if not pd.api.types.is_numeric_dtype(variable):
            variable_dtype = VariableType.CATEGORICAL

        if iteration_graph.current_iter_create_mode == IterationType.SINGLE:
            iteration = iteration_graph.add_single_var_node(
                name=iteration_name,
                variable=variable,
                variable_dtype=variable_dtype,
                risk_tier_details=risk_tier_details,
            )

            iteration_graph.select_current_node_id(iteration.id)
            st.rerun()

        else:
            iteration = iteration_graph.add_double_var_node(
                name=iteration_name,
                variable=variable,
                variable_dtype=variable_dtype,
                previous_node_id=previous_node_id,
            )

            iteration_graph.select_current_node_id(iteration.id)
            st.rerun()

    st.write({
        "variable_name": variable_name,
        "iteration_name": iteration_name,
        "variable_type": variable_dtype,
        "risk_tier_details": risk_tier_details,
        "auto_band": auto_band,
    })
