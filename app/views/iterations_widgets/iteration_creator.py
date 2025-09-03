import numpy as np
import pandas as pd
import streamlit as st

from classes.constants import (
    DefaultOptions,
    LossRateTypes,
    RTDetCol,
    IterationType,
    VariableType,
)
from classes.session import Session
from views.iterations_widgets.common import error_and_warning_widget
from views.iterations_widgets.navigation import navigation_widgets
from views.components import variable_selector_dialog_widget


def sidebar_widgets():
    st.button(
        label="Set Variables",
        use_container_width=True,
        icon=":material/data_table:",
        help="Select variables for calculations",
        type="primary",
        on_click=variable_selector_dialog_widget,
    )


def iteration_creation_widget() -> None:
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph
    options = session.options
    data = session.data
    dlr_scalar = session.dlr_scalars
    ulr_scalar = session.ulr_scalars
    fc = session.filter_container

    with st.sidebar:
        sidebar_widgets()

    navigation_widgets()

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

        col11, col12 = st.columns(2)

        with col11:
            auto_band = st.checkbox("Create Automatic Banding", value=True)

        if auto_band:
            use_scalars = col12.checkbox("Use Scalars", value=True)

            if iteration_graph.current_iter_create_mode == IterationType.SINGLE:
                all_options = list(map(lambda m: m.value, LossRateTypes))
                default_option = DefaultOptions().default_iteation_metadata[
                    "loss_rate_type"
                ]

                st.markdown("##### Loss Rate Type")
                loss_rate_type = LossRateTypes(
                    st.selectbox(
                        label="Loss Rate Type",
                        options=all_options,
                        label_visibility="collapsed",
                        index=all_options.index(default_option),
                    )
                )

            if iteration_graph.current_iter_create_mode == IterationType.DOUBLE:
                auto_rank_ordering = st.checkbox("Auto Rank Ordering", value=True)
                upgrade_cont, downgrade_cont = st.columns(2)

                upgrade_cont.markdown(
                    "##### Upgrade Limit",
                    help="Upgrade Current RT to a one with lower risk. Example RT2 -> RT1.",
                )
                upgrade_limit = upgrade_cont.number_input(
                    label="Upgrade Limit",
                    min_value=0,
                    step=1,
                    format="%d",
                    label_visibility="collapsed",
                    key="upgrade_limit",
                    value=0,
                )

                downgrade_cont.markdown(
                    "##### Downgrade Limit",
                    help="Downgrade Current RT to a one with lower risk. Example RT2 -> RT4.",
                )
                downgrade_limit = downgrade_cont.number_input(
                    label="Downgrade Limit",
                    min_value=0,
                    step=1,
                    format="%d",
                    label_visibility="collapsed",
                    key="downgrade_limit",
                    value=1,
                )

        else:
            use_scalars = False
            loss_rate_type = DefaultOptions().default_iteation_metadata[
                "loss_rate_type"
            ]

        filter_ids = []
        if fc.filters:
            st.markdown("##### Select Filters")
            filter_ids = st.multiselect(
                label="Select Filters",
                options=list(fc.filters.keys()),
                label_visibility="collapsed",
                format_func=lambda filter_id: fc.filters[filter_id].pretty_name,
                disabled=iteration_graph.current_iter_create_mode
                == IterationType.DOUBLE,
                default=iteration_graph.get_metadata(
                    iteration_graph.current_iter_create_parent_id, "filters"
                )
                if iteration_graph.current_iter_create_parent_id
                else None,
            )

    if iteration_graph.current_iter_create_mode == IterationType.SINGLE:
        previous_node_id = None
        rt_details = options.risk_tier_details.copy()
    else:
        previous_node_id = iteration_graph.current_iter_create_parent_id
        rt_details = iteration_graph.get_risk_tier_details(previous_node_id).copy()
        loss_rate_type = iteration_graph.get_metadata(
            previous_node_id, "loss_rate_type"
        )

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
        if iteration_graph.current_iter_create_mode == IterationType.SINGLE:
            st.markdown("##### Select Risk Tiers")
        else:
            st.markdown("##### Selected Risk Tiers *(from Root Node)*")

        edited_rt_details = st.data_editor(
            data=rt_details_styled,
            column_order=[
                RTDetCol.SELECTED,
                RTDetCol.RISK_TIER,
                RTDetCol.LOWER_RATE,
                RTDetCol.UPPER_RATE,
            ],
            column_config=coloumn_config,
            use_container_width=True,
            hide_index=True,
            disabled=disabled_columns,
        )

        risk_tier_details = options.risk_tier_details.loc[
            edited_rt_details[edited_rt_details[RTDetCol.SELECTED]].index
        ].reset_index(drop=False)

    errors = []

    if auto_band:
        if loss_rate_type == LossRateTypes.DLR and (
            data.var_dlr_wrt_off is None or data.var_avg_bal is None
        ):
            errors.append(
                "Variables for :red-badge[`$ Write Off`] and :red-badge[`Avg Balance`] are not selected."
            )

        if loss_rate_type == LossRateTypes.ULR and data.var_unt_wrt_off is None:
            errors.append("Variable for :red-badge[`# Write Off`] is not selected.")

        if use_scalars:
            if loss_rate_type == LossRateTypes.DLR and np.isnan(
                dlr_scalar.portfolio_scalar
            ):
                errors.append("Scalars for :red-badge[`$ Write Off`] are not set.")

            if loss_rate_type == LossRateTypes.ULR and np.isnan(
                ulr_scalar.portfolio_scalar
            ):
                errors.append("Scalars for :red-badge[`# Write Off`] are not set.")

    if errors:
        error_and_warning_widget(errors, [])

    if iteration_graph.current_iter_create_mode == IterationType.SINGLE:
        button_label = "Create Root Iteration"
    else:
        button_label = "Create Child Iteration"

    if st.button(
        label=button_label,
        type="primary",
        disabled=bool(errors),
        icon=":material/add:",
    ):
        variable_dtype = VariableType(variable_dtype)
        variable = session.data.load_column(variable_name, variable_dtype)

        if not pd.api.types.is_numeric_dtype(variable):
            variable_dtype = VariableType.CATEGORICAL

        if iteration_graph.current_iter_create_mode == IterationType.SINGLE:
            iteration = iteration_graph.add_single_var_node(
                name=iteration_name,
                variable=variable,
                variable_dtype=variable_dtype,
                risk_tier_details=risk_tier_details,
                loss_rate_type=loss_rate_type,
                filter_objs={fc.filters[filter_id] for filter_id in filter_ids},
                auto_band=auto_band,
                mob=data.current_rate_mob if auto_band else None,
                dlr_scalar=dlr_scalar if auto_band and use_scalars else None,
                ulr_scalar=ulr_scalar if auto_band and use_scalars else None,
                dlr_wrt_off=data.load_column(
                    data.var_dlr_wrt_off, VariableType.NUMERICAL
                )
                if auto_band
                else None,
                unt_wrt_off=data.load_column(
                    data.var_unt_wrt_off, VariableType.NUMERICAL
                )
                if auto_band
                else None,
                avg_bal=data.load_column(data.var_avg_bal, VariableType.NUMERICAL)
                if auto_band
                else None,
            )

            iteration_graph.select_current_node_id(iteration.id)
            st.rerun()

        else:
            iteration = iteration_graph.add_double_var_node(
                name=iteration_name,
                variable=variable,
                variable_dtype=variable_dtype,
                previous_node_id=previous_node_id,
                filter_objs={fc.filters[filter_id] for filter_id in filter_ids},
                auto_band=auto_band,
                mob=data.current_rate_mob if auto_band else None,
                upgrade_limit=upgrade_limit if auto_band else None,
                downgrade_limit=downgrade_limit if auto_band else None,
                dlr_scalar=dlr_scalar if auto_band and use_scalars else None,
                ulr_scalar=ulr_scalar if auto_band and use_scalars else None,
                dlr_wrt_off=data.load_column(
                    data.var_dlr_wrt_off, VariableType.NUMERICAL
                )
                if auto_band
                else None,
                unt_wrt_off=data.load_column(
                    data.var_unt_wrt_off, VariableType.NUMERICAL
                )
                if auto_band
                else None,
                avg_bal=data.load_column(data.var_avg_bal, VariableType.NUMERICAL)
                if auto_band
                else None,
                auto_rank_ordering=auto_rank_ordering if auto_band else None,
            )

            iteration_graph.select_current_node_id(iteration.id)
            st.rerun()


__all__ = ["iteration_creation_widget"]
