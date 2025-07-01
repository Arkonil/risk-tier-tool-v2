import numpy as np
import pandas as pd
import streamlit as st

from classes.constants import (
    IterationType,
    LossRateTypes,
    Metric,
    MetricTableColumn,
    RTDetCol,
    RangeColumn,
    VariableType,
)
from classes.session import Session
from views.iterations_widgets.dialogs import show_metric_selector
from views.iterations_widgets.navigation import show_navigation_buttons
from views.components.variable_selector import show_variable_selector_dialog


def sidebar_options(iteration_id: str):
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    iteration_metadata = iteration_graph.iteration_metadata[iteration_id]

    st.button(
        label="Set Variables",
        use_container_width=True,
        icon=":material/data_table:",
        help="Select variables for calculations",
        type="primary",
        on_click=show_variable_selector_dialog,
    )

    st.button(
        label="Set Metrics",
        use_container_width=True,
        icon=":material/functions:",
        help="Set metrics to display in the table",
        on_click=show_metric_selector,
        args=(iteration_id,),
    )

    scalars_enabled = st.checkbox(
        label="Enable Scalars",
        value=iteration_metadata["scalars_enabled"],
        help="Use Scalars for Annualized Write Off Rates",
    )

    if scalars_enabled != iteration_metadata["scalars_enabled"]:
        iteration_metadata["scalars_enabled"] = scalars_enabled
        st.rerun()


def show_category_editor(iteration_id: str):
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    iteration = iteration_graph.iterations[iteration_id]
    risk_tier_details = iteration_graph.get_risk_tier_details(iteration_id)

    if iteration.var_type != VariableType.CATEGORICAL:
        st.error(
            "Group editor is only available for categorical variables.",
            icon=":material/error:",
        )
        return

    groups = iteration.groups
    groups = pd.DataFrame({RangeColumn.GROUPS: groups})

    with st.expander("Edit Groups"):
        columns = st.columns(min(5, len(groups)))

        all_categories = set(iteration.variable.cat.categories)
        assigned_categories = set(groups[RangeColumn.GROUPS].explode())
        unassigned_categories = all_categories - assigned_categories

        for i, row in enumerate(groups.itertuples()):
            group_index = row.Index
            group = set(row[1])

            with columns[i % len(columns)]:
                new_group = set(
                    st.multiselect(
                        label=risk_tier_details.loc[group_index, RTDetCol.RISK_TIER],
                        options=sorted(list(group.union(unassigned_categories))),
                        default=sorted(
                            list(group),
                        ),
                    )
                )

                if group != new_group:
                    iteration.set_group(group_index, new_group)
                    iteration_graph.add_to_calculation_queue(
                        iteration.id, default=False
                    )
                    st.rerun()


def get_risk_tier_details(iteration_id: str, recheck: bool) -> tuple[pd.DataFrame, str]:
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph
    options = session.options

    root_iter_id = iteration_graph.get_root_iter_id(iteration_id)
    root_iter = iteration_graph.iterations[root_iter_id]
    message = ""

    if not recheck:
        return root_iter.risk_tier_details, message

    curr_rt_details = root_iter.risk_tier_details
    global_rt_details = options.risk_tier_details.loc[
        curr_rt_details[RTDetCol.ORIG_INDEX]
    ].reset_index(drop=False)

    same_rt = curr_rt_details[RTDetCol.RISK_TIER].equals(
        global_rt_details[RTDetCol.RISK_TIER]
    )
    same_llr = curr_rt_details[RTDetCol.LOWER_RATE].equals(
        global_rt_details[RTDetCol.LOWER_RATE]
    )
    same_ulr = curr_rt_details[RTDetCol.UPPER_RATE].equals(
        global_rt_details[RTDetCol.UPPER_RATE]
    )
    same_maf_dlr = curr_rt_details[RTDetCol.MAF_DLR].equals(
        global_rt_details[RTDetCol.MAF_DLR]
    )
    same_maf_ulr = curr_rt_details[RTDetCol.MAF_ULR].equals(
        global_rt_details[RTDetCol.MAF_ULR]
    )

    if same_rt and same_llr and same_ulr:
        if not same_maf_dlr:
            root_iter.update_maf(
                loss_rate_type=LossRateTypes.DLR,
                maf=global_rt_details[RTDetCol.MAF_DLR],
            )

        if not same_maf_ulr:
            root_iter.update_maf(
                loss_rate_type=LossRateTypes.ULR,
                maf=global_rt_details[RTDetCol.MAF_ULR],
            )

        root_iter.update_color(
            color_type=RTDetCol.BG_COLOR,
            color=global_rt_details[RTDetCol.BG_COLOR],
        )

        root_iter.update_color(
            color_type=RTDetCol.FONT_COLOR,
            color=global_rt_details[RTDetCol.FONT_COLOR],
        )

    else:
        message = (
            "Risk Tier Details have been changed after creating the iteration."
            " All calculations will be done with the original details."
        )

    return root_iter.risk_tier_details, message


def show_error_and_warnings(errors: list[str], warnings: list[str]):
    if errors or warnings:
        severe = len(errors) > 0

        counts = []
        if errors:
            counts.append(f"{len(errors)} Errors")
        if warnings:
            counts.append(f"{len(warnings)} Warnings")

        count_label = " and ".join(counts)

        with st.expander(count_label, expanded=severe):
            if errors:
                message = "Errors: \n\n" + "\n\n".join(
                    map(lambda msg: f"- {msg}", errors)
                )

                st.error(message, icon=":material/error:")

            if warnings:
                message = "Warnings: \n\n" + "\n\n".join(
                    map(lambda msg: f"- {msg}", warnings)
                )

                st.warning(message, icon=":material/warning:")


def show_edited_range(
    iteration_id: str,
    editable: bool,
    scalars_enabled: bool,
    metrics: list[Metric],
    default: bool,
    key: int = 0,
):
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph
    data = session.data

    iteration = iteration_graph.iterations[iteration_id]

    risk_tier_details, _ = get_risk_tier_details(iteration.id, recheck=False)

    if iteration.iter_type == IterationType.DOUBLE or default:
        editable = False

    iteration_output = iteration_graph.get_risk_tiers(iteration.id, default=default)

    new_risk_tiers = iteration_output["risk_tier_column"]
    errors = iteration_output["errors"]
    warnings = iteration_output["warnings"]
    # invalid_groups = iteration_output["invalid_groups"]

    groups = risk_tier_details[[RTDetCol.RISK_TIER, RTDetCol.MAF_ULR, RTDetCol.MAF_DLR]]

    if iteration.iter_type == IterationType.SINGLE:
        groups = groups.merge(
            iteration.default_groups if default else iteration.groups,
            how="left",
            left_index=True,
            right_index=True,
        )

        if iteration.var_type == VariableType.NUMERICAL:
            groups[RangeColumn.LOWER_BOUND] = groups[RangeColumn.GROUPS].map(
                lambda bounds: bounds[0]
            )
            groups[RangeColumn.UPPER_BOUND] = groups[RangeColumn.GROUPS].map(
                lambda bounds: bounds[1]
            )
        else:
            groups[RangeColumn.CATEGORIES] = groups[RangeColumn.GROUPS]

    summ_df = data.get_summarized_metrics(
        new_risk_tiers.rename(RangeColumn.RISK_TIER),
        metrics=metrics,
    )
    calculated_df = pd.merge(
        groups, summ_df, how="left", left_index=True, right_index=True
    )

    if scalars_enabled and (
        Metric.ANNL_WO_COUNT_PCT in metrics or Metric.ANNL_WO_BAL_PCT in metrics
    ):
        ulr_scalar = session.ulr_scalars
        dlr_scalar = session.dlr_scalars

        calculated_df[RangeColumn.RISK_SCALAR_FACTOR_ULR] = (
            ulr_scalar.get_risk_scalar_factor(calculated_df[RTDetCol.MAF_ULR])
        )
        calculated_df[RangeColumn.RISK_SCALAR_FACTOR_DLR] = (
            dlr_scalar.get_risk_scalar_factor(calculated_df[RTDetCol.MAF_DLR])
        )

        if Metric.ANNL_WO_COUNT_PCT in calculated_df.columns:
            calculated_df[Metric.ANNL_WO_COUNT_PCT] = (
                calculated_df[Metric.ANNL_WO_COUNT_PCT]
                * calculated_df[RangeColumn.RISK_SCALAR_FACTOR_ULR]
            )

        if Metric.ANNL_WO_BAL_PCT in calculated_df.columns:
            calculated_df[Metric.ANNL_WO_BAL_PCT] = (
                calculated_df[Metric.ANNL_WO_BAL_PCT]
                * calculated_df[RangeColumn.RISK_SCALAR_FACTOR_DLR]
            )

    int_cols = [Metric.VOLUME, Metric.WO_COUNT]
    dec_cols = [Metric.WO_BAL, Metric.AVG_BAL]
    perc_cols = [
        Metric.WO_BAL_PCT,
        Metric.WO_COUNT_PCT,
        Metric.ANNL_WO_COUNT_PCT,
        Metric.ANNL_WO_BAL_PCT,
    ]

    def get_style(rt_label: str) -> str:
        font_color, bg_color = iteration_graph.get_color(rt_label, iteration_id)
        return f"color: {font_color}; background-color: {bg_color};"

    calculated_df_styled = (
        calculated_df.style.map(
            get_style,
            subset=[RTDetCol.RISK_TIER],
        )
        .format(precision=0, thousands=",", subset=int_cols)
        .format(precision=2, thousands=",", subset=dec_cols)
        .format("{:.2f} %", subset=perc_cols)
    )

    disabled = not editable
    column_config = {
        RTDetCol.RISK_TIER: st.column_config.TextColumn(
            label=RTDetCol.RISK_TIER, disabled=True
        ),
        RangeColumn.CATEGORIES: st.column_config.ListColumn(
            label=RangeColumn.CATEGORIES, width="large"
        ),
        RangeColumn.LOWER_BOUND: st.column_config.NumberColumn(
            label=RangeColumn.LOWER_BOUND, disabled=disabled, format="compact"
        ),
        RangeColumn.UPPER_BOUND: st.column_config.NumberColumn(
            label=RangeColumn.UPPER_BOUND, disabled=disabled, format="compact"
        ),
        Metric.VOLUME: st.column_config.NumberColumn(
            label=Metric.VOLUME, disabled=True
        ),
        Metric.WO_BAL: st.column_config.NumberColumn(
            label=Metric.WO_BAL, disabled=True
        ),
        Metric.WO_BAL_PCT: st.column_config.NumberColumn(
            label=Metric.WO_BAL_PCT, disabled=True
        ),
        Metric.WO_COUNT: st.column_config.NumberColumn(
            label=Metric.WO_COUNT, disabled=True
        ),
        Metric.WO_COUNT_PCT: st.column_config.NumberColumn(
            label=Metric.WO_COUNT_PCT, disabled=True
        ),
        Metric.AVG_BAL: st.column_config.NumberColumn(
            label=Metric.AVG_BAL, disabled=True
        ),
        Metric.ANNL_WO_COUNT_PCT: st.column_config.NumberColumn(
            label=Metric.ANNL_WO_COUNT_PCT, disabled=True
        ),
        Metric.ANNL_WO_BAL_PCT: st.column_config.NumberColumn(
            label=Metric.ANNL_WO_BAL_PCT, disabled=True
        ),
    }

    columns = [RTDetCol.RISK_TIER]
    if iteration.iter_type == IterationType.SINGLE:
        if iteration.var_type == VariableType.NUMERICAL:
            columns += [RangeColumn.LOWER_BOUND, RangeColumn.UPPER_BOUND]
        else:
            columns += [RangeColumn.CATEGORIES]

    columns += metrics

    edited_df = st.data_editor(
        calculated_df_styled,
        column_order=columns,
        hide_index=True,
        column_config=column_config,
        use_container_width=True,
        key=f"edited_range-{key}-{iteration.id}",
    )

    if editable and iteration.var_type == VariableType.NUMERICAL:
        edited_groups = edited_df[
            [RTDetCol.RISK_TIER, RangeColumn.LOWER_BOUND, RangeColumn.UPPER_BOUND]
        ]

        needs_rerun = False
        for index in edited_groups.index:
            prev_bounds = np.array(groups.loc[index, RangeColumn.GROUPS]).astype(float)
            curent_bounds = np.array(
                edited_groups.loc[
                    index, [RangeColumn.LOWER_BOUND, RangeColumn.UPPER_BOUND]
                ]
            ).astype(float)

            if not np.array_equal(prev_bounds, curent_bounds, equal_nan=True):
                new_lb = edited_groups.loc[index, RangeColumn.LOWER_BOUND]
                new_ub = edited_groups.loc[index, RangeColumn.UPPER_BOUND]

                iteration.set_group(index, new_lb, new_ub)
                iteration_graph.add_to_calculation_queue(iteration.id, default=False)
                needs_rerun = True

        if needs_rerun:
            print(f"needs rerun: {needs_rerun}")
            st.rerun()

    if editable:
        show_error_and_warnings(errors, warnings)


def show_single_var_iteration_widgets():
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    iteration = iteration_graph.current_iteration
    iteration_metadata = iteration_graph.iteration_metadata[iteration.id]

    metrics = iteration_metadata["metrics"]
    showing_metrics = (
        metrics.sort_values(MetricTableColumn.ORDER)
        .loc[metrics[MetricTableColumn.SHOWING], MetricTableColumn.METRIC]
        .to_list()
    )

    # Sidebar
    with st.sidebar:
        sidebar_options(iteration_id=iteration.id)

    # Main Page
    ## Navigation
    show_navigation_buttons()

    st.title(f"Iteration #{iteration.id}")
    st.write(f"##### Variable: `{iteration.variable.name}`")

    ## Risk Tier Details Check
    _, message = get_risk_tier_details(iteration.id, recheck=True)

    if message:
        st.error(message, icon=":material/error:")

    ## Default View

    st.markdown("##### Default Range")
    show_edited_range(
        iteration_id=iteration.id,
        editable=True,
        scalars_enabled=iteration_metadata["scalars_enabled"],
        metrics=showing_metrics,
        default=True,
        key=0,
    )

    ## Category Editor
    if iteration.var_type == VariableType.CATEGORICAL:
        show_category_editor(iteration.id)

    ## Ranges
    st.markdown("##### Editable Ranges")
    show_edited_range(
        iteration_id=iteration.id,
        editable=True,
        scalars_enabled=iteration_metadata["scalars_enabled"],
        metrics=showing_metrics,
        default=False,
        key=1,
    )
