import typing as t

import numpy as np
import pandas as pd
import streamlit as st

from risc_tool.data.models.defaults import DefaultOptions
from risc_tool.data.models.enums import (
    IterationType,
    LossRateTypes,
    RSDetCol,
    VariableType,
)
from risc_tool.data.models.types import FilterID, IterationID
from risc_tool.data.session import Session
from risc_tool.pages.components.variable_selector import variable_selector_dialog
from risc_tool.pages.iterations.common import error_and_warning_widget
from risc_tool.pages.iterations.navigation import navigation_widgets


def sidebar_widgets():
    st.button(
        label="Set Variables",
        use_container_width=True,
        icon=":material/data_table:",
        help="Select variables for calculations",
        type="primary",
        on_click=variable_selector_dialog,
    )


def variable_selector() -> str:
    session: Session = st.session_state["session"]
    iterations_vm = session.iterations_view_model

    label = "##### Select Variable"

    st.markdown(label)
    variable_name = st.selectbox(
        label=label,
        options=iterations_vm.common_columns,
        label_visibility="collapsed",
    )

    return variable_name


def iteration_name_input() -> str:
    label = "##### Iteration Name"

    st.markdown(label)
    iteration_name = st.text_input(label="Iteration Name", label_visibility="collapsed")

    return iteration_name


def variable_type_selector() -> VariableType:
    label = "##### Variable Type"

    st.markdown(label)
    variable_dtype = st.selectbox(
        label="Variable Type",
        options=[VariableType.NUMERICAL, VariableType.CATEGORICAL],
        index=0,
        label_visibility="collapsed",
    )

    return variable_dtype


def loss_rate_type_selector() -> LossRateTypes:
    label = "##### Loss Rate Type"

    all_options = list(map(lambda m: m.value, LossRateTypes))
    default_option = DefaultOptions().default_iteation_metadata.loss_rate_type

    st.markdown(label)
    loss_rate_type = st.selectbox(
        label=label,
        options=all_options,
        index=all_options.index(default_option),
        label_visibility="collapsed",
    )

    return LossRateTypes(loss_rate_type)


def upgrade_downgrade_selector() -> tuple[bool, int, int]:
    auto_rank_ordering = st.checkbox("Auto Rank Ordering", value=True)
    upgrade_cont_t, downgrade_cont_t = st.columns(2)
    upgrade_cont_i, downgrade_cont_i = st.columns(2)

    upgrade_cont_t.markdown(
        "##### Upgrade Limit",
        help="Upgrade Current RT to a one with lower risk. Example RT2 -> RT1.",
    )
    upgrade_limit = upgrade_cont_i.number_input(
        label="Upgrade Limit",
        min_value=0,
        step=1,
        format="%d",
        label_visibility="collapsed",
        key="upgrade_limit",
        value=0,
    )

    downgrade_cont_t.markdown(
        "##### Downgrade Limit",
        help="Downgrade Current RT to a one with lower risk. Example RT2 -> RT4.",
    )
    downgrade_limit = downgrade_cont_i.number_input(
        label="Downgrade Limit",
        min_value=0,
        step=1,
        format="%d",
        label_visibility="collapsed",
        key="downgrade_limit",
        value=1,
    )

    return auto_rank_ordering, upgrade_limit, downgrade_limit


def filter_selector():
    session: Session = st.session_state["session"]
    iterations_vm = session.iterations_view_model

    label = "##### Select Filters"

    st.markdown(label)

    if iterations_vm.current_iteration_create_parent_id:
        default_value = iterations_vm.get_iteration_metadata(
            iterations_vm.current_iteration_create_parent_id
        ).initial_filter_ids
    else:
        default_value = None

    filters = iterations_vm.get_filters()
    disabled = iterations_vm.current_iteration_create_mode == IterationType.DOUBLE

    filter_ids = st.multiselect(
        label=label,
        options=sorted(list(filters.keys())),
        label_visibility="collapsed",
        format_func=lambda filter_id: filters[filter_id].name,
        disabled=disabled,
        default=default_value,
    )

    return filter_ids


def risk_segment_details_selector():
    session: Session = st.session_state["session"]
    iterations_vm = session.iterations_view_model

    if iterations_vm.current_iteration_create_mode == IterationType.SINGLE:
        previous_node_id = None
        rs_details = iterations_vm.global_risk_segment_details.copy()
    else:
        previous_node_id = t.cast(
            IterationID, iterations_vm.current_iteration_create_parent_id
        )
        rs_details = iterations_vm.get_risk_segment_details(previous_node_id).copy()

    # Column Modification
    rs_details[RSDetCol.LOWER_RATE] = (rs_details[RSDetCol.LOWER_RATE] * 100).map(
        lambda v: "-Infinity" if np.isinf(v) else f"{v:.2f}%"
    )

    rs_details[RSDetCol.UPPER_RATE] = (rs_details[RSDetCol.UPPER_RATE] * 100).map(
        lambda v: "+Infinity" if np.isinf(v) else f"{v:.2f}%"
    )

    rs_details[RSDetCol.MAF_DLR] = rs_details[RSDetCol.MAF_DLR].map(
        lambda v: f"{v * 100:.1f} %"
    )
    rs_details[RSDetCol.MAF_ULR] = rs_details[RSDetCol.MAF_ULR].map(
        lambda v: f"{v * 100:.1f} %"
    )

    rs_details[RSDetCol.SELECTED] = True

    disabled_columns = rs_details.columns
    if iterations_vm.current_iteration_create_mode == IterationType.SINGLE:
        disabled_columns = disabled_columns.drop(RSDetCol.SELECTED)

    rs_details_styled = rs_details.style

    for row_index in rs_details.index:
        font_color = rs_details.loc[row_index, RSDetCol.FONT_COLOR]
        bg_color = rs_details.loc[row_index, RSDetCol.BG_COLOR]
        rs_details_styled = rs_details_styled.set_properties(
            subset=(
                slice(row_index, row_index),
                slice(RSDetCol.RISK_SEGMENT, RSDetCol.RISK_SEGMENT),
            ),
            **{
                "color": str(font_color),
                "background-color": str(bg_color),
            },
        )

    coloumn_config = {
        RSDetCol.SELECTED.value: st.column_config.CheckboxColumn(
            label=RSDetCol.SELECTED,
        ),
        RSDetCol.RISK_SEGMENT.value: st.column_config.TextColumn(
            label=RSDetCol.RISK_SEGMENT,
        ),
        RSDetCol.LOWER_RATE.value: st.column_config.TextColumn(
            label=RSDetCol.LOWER_RATE,
        ),
        RSDetCol.UPPER_RATE.value: st.column_config.TextColumn(
            label=RSDetCol.UPPER_RATE,
        ),
    }

    if iterations_vm.current_iteration_create_mode == IterationType.SINGLE:
        st.markdown("##### Select Risk Segments")
    else:
        st.markdown("##### Selected Risk Segments *(from Root Node)*")

    edited_rs_details = st.data_editor(
        data=rs_details_styled,
        column_order=[
            RSDetCol.SELECTED,
            RSDetCol.RISK_SEGMENT,
            RSDetCol.LOWER_RATE,
            RSDetCol.UPPER_RATE,
        ],
        column_config=coloumn_config,
        width="stretch",
        hide_index=True,
        disabled=disabled_columns,
    )

    return edited_rs_details[RSDetCol.SELECTED]


def error_display(
    variable_sample: pd.Series,
    variable_dtype: VariableType,
    auto_band: bool,
    loss_rate_type: LossRateTypes,
    use_scalars: bool,
) -> bool:
    session: Session = st.session_state["session"]
    iterations_vm = session.iterations_view_model

    errors: list[str] = []

    is_categorical = (variable_dtype == VariableType.CATEGORICAL) or (
        not pd.api.types.is_numeric_dtype(variable_sample)
    )

    if (
        is_categorical
        and variable_sample.nunique() > iterations_vm.max_categorical_unique
    ):
        errors.append(
            f"Error: Variable `{variable_sample.name}` is not numerical and has more than {iterations_vm.max_categorical_unique} unique values. "
            f"Total unique values: {variable_sample.nunique()}",
        )

    if auto_band:
        if not iterations_vm.metric_variables_selected(loss_rate_type):
            if loss_rate_type == LossRateTypes.DLR:
                errors.append(
                    "Variables for :red-badge[`$ Bad`] and :red-badge[`Avg Balance`] are not selected."
                )

            if loss_rate_type == LossRateTypes.ULR:
                errors.append("Variable for :red-badge[`# Bad`] is not selected.")

        if use_scalars:
            if not iterations_vm.scalar_selected(loss_rate_type):
                if loss_rate_type == LossRateTypes.DLR:
                    errors.append("Scalars for :red-badge[`$ Bad`] are not set.")

                if loss_rate_type == LossRateTypes.ULR:
                    errors.append("Scalars for :red-badge[`# Bad`] are not set.")

    if errors:
        error_and_warning_widget(errors, [])

    return len(errors) > 0


def iteration_creator():
    session: Session = st.session_state["session"]
    iterations_vm = session.iterations_view_model

    with st.sidebar:
        sidebar_widgets()

    navigation_widgets()

    st.title("Create New Iteration")

    col1, col2 = st.columns([1, 2])

    # Left Column Controls
    with col1:
        variable_name = variable_selector()
        iteration_name = iteration_name_input()
        variable_dtype = variable_type_selector()

        col11, col12 = st.columns(2)

        auto_band = col11.checkbox("Create Automatic Banding", value=True)
        auto_rank_ordering, upgrade_limit, downgrade_limit = True, 1, 1

        if auto_band:
            use_scalars = col12.checkbox("Use Scalars", value=True)

            if iterations_vm.current_iteration_create_mode == IterationType.SINGLE:
                loss_rate_type = loss_rate_type_selector()
            else:
                loss_rate_type = iterations_vm.get_iteration_metadata(
                    t.cast(
                        IterationID, iterations_vm.current_iteration_create_parent_id
                    )
                ).loss_rate_type
                auto_rank_ordering, upgrade_limit, downgrade_limit = (
                    upgrade_downgrade_selector()
                )

        else:
            use_scalars = False
            loss_rate_type = DefaultOptions().default_iteation_metadata.loss_rate_type

        filter_ids: list[FilterID] = filter_selector()

    # Right Column Controls
    with col2:
        risk_segment_details = risk_segment_details_selector()

    variable_sample = iterations_vm.get_sample_variable(variable_name)

    errors = error_display(
        variable_sample, variable_dtype, auto_band, loss_rate_type, use_scalars
    )

    if iterations_vm.current_iteration_create_mode == IterationType.SINGLE:
        button_label = "Create Root Iteration"
    else:
        button_label = "Create Child Iteration"

    if st.button(
        label=button_label,
        type="primary",
        disabled=errors,
        icon=":material/add:",
    ):
        if not pd.api.types.is_numeric_dtype(variable_sample):
            variable_dtype = VariableType.CATEGORICAL

        if iterations_vm.current_iteration_create_mode == IterationType.SINGLE:
            iteration = iterations_vm.add_single_var_iteration(
                name=iteration_name,
                variable_name=variable_name,
                variable_dtype=variable_dtype,
                selected_segments_mask=t.cast(pd.Series, risk_segment_details),
                loss_rate_type=loss_rate_type,
                filter_ids=filter_ids,
                auto_band=auto_band,
                use_scalar=use_scalars,
            )

            iterations_vm.set_current_status("view", iteration.uid)
            st.rerun()

        else:
            previous_node_id = t.cast(
                IterationID, iterations_vm.current_iteration_create_parent_id
            )

            iteration = iterations_vm.add_double_var_iteration(
                name=iteration_name,
                previous_iteration_id=previous_node_id,
                variable_name=variable_name,
                variable_dtype=variable_dtype,
                auto_band=auto_band,
                use_scalar=use_scalars,
                upgrade_limit=upgrade_limit if auto_band else None,
                downgrade_limit=downgrade_limit if auto_band else None,
                auto_rank_ordering=auto_rank_ordering if auto_band else None,
            )

            iterations_vm.set_current_status("view", iteration.uid)
            st.rerun()


__all__ = ["iteration_creator"]
