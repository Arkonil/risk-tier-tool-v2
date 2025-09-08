import pandas as pd
import streamlit as st

from classes.constants import RangeColumn, VariableType, RTDetCol, DefaultMetrics
from classes.session import Session
from views.components.iteration_selector import iteration_selector_widget
from views.components.metric_selector import metric_selector_widget
from views.iterations_widgets.common import get_risk_tier_details


def sidebar_widgets():
    session: Session = st.session_state["session"]
    summ_state = session.summary_page_state
    fc = session.filter_container

    def set_metrics(metrics: list[str]):
        summ_state.ct_metrics = metrics

    metric_selector_widget(
        current_metrics=summ_state.ct_metrics,
        set_metrics=set_metrics,
        key=0,
    )

    current_filters = summ_state.ct_filters

    filter_ids = set(
        st.multiselect(
            label="Filter",
            options=list(fc.filters.keys()),
            default=current_filters,
            format_func=lambda filter_id: fc.filters[filter_id].pretty_name,
            label_visibility="collapsed",
            key="filter_selector_summary",
            help="Select filters to apply to the iteration",
            placeholder="Select Filters",
        )
    )

    if filter_ids != current_filters:
        summ_state.ct_filters = filter_ids
        st.rerun()

    scalars_enabled = st.checkbox(
        label="Enable Scalars",
        value=summ_state.ct_scalars_enabled,
        help="Use Scalars for Annualized Write Off Rates",
    )

    if scalars_enabled != summ_state.ct_scalars_enabled:
        summ_state.ct_scalars_enabled = scalars_enabled
        st.rerun()


def crosstab_widget():
    session: Session = st.session_state["session"]
    data = session.data
    fc = session.filter_container
    iteration_graph = session.iteration_graph
    summ_state = session.summary_page_state
    options = session.options
    all_metrics = session.get_all_metrics()

    with st.sidebar:
        sidebar_widgets()

    metric_names = summ_state.ct_metrics
    metric_names = [
        metric_name for metric_name in metric_names if metric_name in all_metrics
    ]
    metrics = [all_metrics[metric_name] for metric_name in metric_names]

    iteration_selector_container = st.container()
    variable_selector_container = st.container()
    crosstab_container = st.container()
    error_container = st.container()

    with iteration_selector_container:
        iteration_id, is_default = iteration_selector_widget(
            selected_iteration_id=summ_state.ct_selected_iteration_id,
            is_default=summ_state.ct_selected_iteration_default,
            key=0,
        )

        if (iteration_id, is_default) != (
            summ_state.ct_selected_iteration_id,
            summ_state.ct_selected_iteration_default,
        ):
            summ_state.ct_selected_iteration_id = iteration_id
            summ_state.ct_selected_iteration_default = is_default
            st.rerun()

    with variable_selector_container:
        col1, col2, col3 = st.columns(3)

        column_name = col1.selectbox(
            label="Variable",
            options=data.sample_df.columns,
            index=data.sample_df.columns.get_loc(summ_state.ct_variable)
            if summ_state.ct_variable in data.sample_df.columns
            else 0,
        )

        if column_name != summ_state.ct_variable:
            summ_state.ct_variable = column_name
            st.rerun()

        column_type = col2.selectbox(
            label="Variable Type",
            options=[VariableType.NUMERICAL, VariableType.CATEGORICAL],
            index=list(VariableType).index(summ_state.ct_variable_type),
        )

        if column_type != summ_state.ct_variable_type:
            summ_state.ct_variable_type = column_type
            st.rerun()

        variable = data.load_column(summ_state.ct_variable, summ_state.ct_variable_type)

        is_categorical = (summ_state.ct_variable_type == VariableType.CATEGORICAL) or (
            not pd.api.types.is_numeric_dtype(variable)
        )

        label = "Number of Bins"
        if is_categorical:
            label += "(disabled for categorical variables)"

        bin_count = col3.number_input(
            label=label,
            value=summ_state.ct_numeric_variable_bin_count,
            step=1,
            min_value=1,
            max_value=100,
            disabled=is_categorical,
        )

        if bin_count != summ_state.ct_numeric_variable_bin_count:
            summ_state.ct_numeric_variable_bin_count = bin_count
            st.rerun()

        if is_categorical and variable.nunique() > options.max_categorical_unique:
            error_container.error(
                f"Error: Variable `{variable.name}` is not numerical and has more than {options.max_categorical_unique} unique values. "
                f"Total unique values: {variable.nunique()}",
                icon=":material/error:",
            )
            return

    if not is_categorical:
        variable = pd.cut(
            variable,
            bins=summ_state.ct_numeric_variable_bin_count,
        )

    variable = variable.map(str).convert_dtypes()
    variable.name = "__VARIABLE_PLACEHOLDER_NAME__"

    with crosstab_container:
        risk_tier_details, _ = get_risk_tier_details(
            summ_state.ct_selected_iteration_id, recheck=False
        )

        iteration_results = iteration_graph.get_risk_tiers(
            summ_state.ct_selected_iteration_id,
            summ_state.ct_selected_iteration_default,
        )
        errors = iteration_results["errors"]
        warnings = iteration_results["warnings"]
        risk_tier_column = iteration_results["risk_tier_column"]

        if len(errors) > 0:
            with error_container:
                st.error("\n\n".join(errors))
            return

        if len(warnings) > 0:
            with error_container:
                st.warning("\n\n".join(warnings))

        crosstab_df = data.get_summarized_metrics(
            groupby_variable_1=variable,
            groupby_variable_2=risk_tier_column,
            data_filter=fc.get_mask(
                filter_ids=summ_state.ct_filters,
                index=data.df.index,
            ),
            metrics=metrics,
        )

        crosstab_df.rename_axis(
            index={
                "__VARIABLE_PLACEHOLDER_NAME__": summ_state.ct_variable,
                risk_tier_column.name: "Risk Tier",
            },
            inplace=True,
        )

        for metric in metrics:
            metric_summary = crosstab_df[metric.name].copy()

            st.write(f"#### {metric.name}")

            if summ_state.ct_scalars_enabled and (
                metric.name
                in (DefaultMetrics.UNT_BAD_RATE, DefaultMetrics.DLR_BAD_RATE)
            ):
                if metric.name == DefaultMetrics.UNT_BAD_RATE:
                    scalar = session.ulr_scalars
                    maf = risk_tier_details[RTDetCol.MAF_ULR]
                    rsf_name = RangeColumn.RISK_SCALAR_FACTOR_ULR
                elif metric.name == DefaultMetrics.DLR_BAD_RATE:
                    scalar = session.dlr_scalars
                    maf = risk_tier_details[RTDetCol.MAF_DLR]
                    rsf_name = RangeColumn.RISK_SCALAR_FACTOR_DLR

                metric_summary = pd.merge(
                    left=metric_summary,
                    right=scalar.get_risk_scalar_factor(maf=maf).rename(rsf_name),
                    how="left",
                    left_on="Risk Tier",
                    right_index=True,
                )

                metric_summary[metric.name] *= metric_summary[rsf_name]
                metric_summary = metric_summary[metric.name]

            metric_summary = metric_summary.unstack(0)
            metric_summary.sort_index(inplace=True)
            metric_summary.index = metric_summary.index.map(
                risk_tier_details[RTDetCol.RISK_TIER]
            )

            st.dataframe(metric_summary.style.format(metric.format))


__all__ = [
    "crosstab_widget",
]
