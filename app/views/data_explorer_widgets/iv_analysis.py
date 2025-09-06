import pandas as pd
import streamlit as st

from classes.constants import VariableType
from classes.session import Session


def iv_analysis_widget():
    session: Session = st.session_state["session"]
    data = session.data
    de = session.data_explorer
    fc = session.filter_container

    chart_container, control_container = st.columns([2.5, 1])
    error_container = st.container()

    with control_container:
        current_target_index = data.get_col_pos(de.iv_current_target)
        if current_target_index is None:
            current_target_index = -1

        target_variable = st.selectbox(
            label="Target Variable",
            options=[None] + data.sample_df.columns.to_list(),
            index=current_target_index + 1,
        )

        # if target_variable != de.iv_current_target:
        #     de.iv_current_target = target_variable
        #     st.rerun()

        variables = st.multiselect(
            label="Variables",
            options=data.sample_df.columns,
            default=de.iv_current_variables,
        )

        # if set(variables) != set(de.iv_current_variables):
        #     de.iv_current_variables = variables
        #     st.rerun()

        filter_ids = st.multiselect(
            label="Filters",
            options=list(fc.filters.keys()),
            default=de.iv_current_filter_ids,
            format_func=lambda fid: fc.filters[fid].pretty_name,
        )

        # if set(filter_ids) != set(de.iv_current_filter_ids):
        #     de.iv_current_filter_ids = filter_ids
        #     st.rerun()

    if target_variable is None or not variables:
        chart_container.write("No variables selected")
        return

    target = data.load_column(target_variable, VariableType.NUMERICAL)

    if not pd.api.types.is_numeric_dtype(target):
        error_container.error(
            f"Error: Target variable must be numerical. Selected column is of type `<{target.dtype}>`."
        )
        return

    if not target.isin([0, 1]).all():
        values = set(target.drop_duplicates().to_list()) - {0, 1}
        error_container.error(
            f"Error: Target variable must be binary (0 or 1).\n\n"
            f"Following values were found: [{', '.join(map(str, values))}]"
        )
        return

    input_variables = data.load_columns(
        list(variables), column_types=[VariableType.NUMERICAL for _ in variables]
    )

    mask = fc.get_mask(filter_ids=filter_ids, index=target.index)

    iv_values = {}

    for var in input_variables.columns:
        try:
            iv_values[var] = de.get_iv(input_variables[var], target, mask)
        except Exception as error:
            error_container.error(str(error))
            break
    else:
        with chart_container:
            st.write(iv_values)


__all__ = ["iv_analysis_widget"]
