import streamlit as st
import streamlit_antd_components as sac

from risc_tool.data.models.enums import ComparisonOperation, PercentileOptions
from risc_tool.data.models.types import FilterID
from risc_tool.data.session import Session


def outlier_rule_input(
    outlier_id: FilterID,
    variable_name: str,
    comparison_op: ComparisonOperation,
    comparison_base: PercentileOptions | str,
    key: str = "new",
    errors: Exception | None = None,
    frequency: int = 0,
):
    session: Session = st.session_state["session"]
    de_view_model = session.data_explorer_view_model

    all_variables = de_view_model.all_columns

    with st.container(border=True, key=f"outlier-input-container-{key}"):
        col1, col2, col3 = st.columns([6, 2, 3])

        new_variable_name = col1.selectbox(
            label="Select Variable",
            options=all_variables,
            index=all_variables.index(variable_name),
            key=f"outlier-variable-name-selector-{key}",
        )

        new_comparison_op = col2.selectbox(
            label="Comparison Operation",
            options=list(ComparisonOperation),
            index=list(ComparisonOperation).index(comparison_op),
            key=f"outlier-comparison-op-selector-{key}",
        )

        if isinstance(comparison_base, PercentileOptions):
            comparison_base_options = list(PercentileOptions)
            comparison_base_index = comparison_base_options.index(comparison_base)
        else:
            comparison_base_options = [comparison_base] + list(PercentileOptions)
            comparison_base_index = 0

        new_comparison_base = col3.selectbox(
            label="Comparison Base",
            options=comparison_base_options,
            index=comparison_base_index,
            accept_new_options=True,
            format_func=PercentileOptions.format_perc,
            key=f"outlier-comparison-base-selector-{key}",
        )

        try:
            new_comparison_base = PercentileOptions(new_comparison_base)
        except ValueError:
            pass

        with st.container(horizontal=True, horizontal_alignment="right"):
            if errors:
                st.error(errors)
            elif outlier_id != FilterID.TEMPORARY:
                st.write(f"Outlier Count: {frequency:,}")

            save_button_disabled = (variable_name, comparison_op, comparison_base) == (
                new_variable_name,
                new_comparison_op,
                new_comparison_base,
            ) and (outlier_id != FilterID.TEMPORARY)

            if st.button(
                label="Rule Saved" if save_button_disabled else "Save Rule",
                type="primary",
                key=f"outlier-save-button-{key}",
                disabled=save_button_disabled,
                icon=":material/download_done:"
                if save_button_disabled
                else ":material/save:",
            ):
                de_view_model.save_outlier(
                    outlier_id,
                    new_variable_name,
                    new_comparison_op,
                    new_comparison_base,
                )
                st.rerun()

            if outlier_id != FilterID.TEMPORARY:
                if st.button(
                    label="",
                    type="primary",
                    key=f"outlier-delete-button-{key}",
                    icon=":material/delete:",
                ):
                    de_view_model.delete_outlier_rule(outlier_id)
                    st.rerun()


def outlier_rules():
    session: Session = st.session_state["session"]
    de_view_model = session.data_explorer_view_model

    st.subheader("Outlier Rules")
    st.space()

    if de_view_model.current_outlier_rules:
        st.write(f"Total Outlier Count: {de_view_model.total_outlier_count:,}")

    for outlier_rule in de_view_model.current_outlier_rules:
        try:
            comparison_base = PercentileOptions(outlier_rule.comparison_base)
        except ValueError:
            comparison_base = str(outlier_rule.comparison_base)

        outlier_rule_input(
            outlier_id=outlier_rule.uid,
            variable_name=outlier_rule.variable_name,
            comparison_op=outlier_rule.comparison_op,
            comparison_base=comparison_base,
            key=str(outlier_rule.uid),
            errors=de_view_model.ol_errors.get(outlier_rule.uid),
            frequency=(~outlier_rule.mask).sum()
            if outlier_rule.mask is not None
            else -1,
        )

    if de_view_model.current_outlier_rules:
        sac.divider(label="Add New Outlier Rule", align="center", size="md")

    outlier_rule_input(
        outlier_id=FilterID.TEMPORARY,
        variable_name=de_view_model.all_columns[0],
        comparison_op=ComparisonOperation.GT,
        comparison_base=PercentileOptions.PERC_99,
    )


__all__ = ["outlier_rules"]
