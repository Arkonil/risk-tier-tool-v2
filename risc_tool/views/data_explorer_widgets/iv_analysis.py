import altair as alt
import pandas as pd
import streamlit as st

from classes.session import Session


def iv_bar_chart(data: list[tuple[str, float]]):
    data = pd.DataFrame(data, columns=["variable", "iv"])
    data.sort_values("iv", ascending=False, inplace=True)

    x = alt.X(
        "variable:N",
        sort=alt.EncodingSortField(field="iv", op="max", order="descending"),
        axis=alt.Axis(
            title="Variable",
            labelAngle=0,
        ),
    )

    y = alt.Y(
        "iv:Q",
        axis=alt.Axis(title="Information Value (IV)"),
    )

    tooltip = [
        alt.Tooltip("variable", title="Variable"),
        alt.Tooltip("iv", title="Information Value", format=".2f"),
    ]

    text_labels = (
        alt.Chart(data)
        .mark_text(
            align="center",
            dy=-15,
            color="white" if st.context.theme.type == "dark" else "black",
        )
        .encode(x=x, y=y, text=alt.Text("iv:Q", format=".2f"))
    )

    bars = alt.Chart(data).mark_bar(color="#44c1ca").encode(x=x, y=y, tooltip=tooltip)

    chart = (bars + text_labels).configure_axis(grid=False).properties(height=500)

    return chart


def iv_analysis_widget():
    session: Session = st.session_state["session"]
    data = session.data
    de = session.data_explorer
    fc = session.filter_container
    options = session.options

    st.markdown("####  Information Value")
    st.write("")

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

        variables = st.multiselect(
            label="Variables",
            options=data.sample_df.columns,
            default=de.iv_current_variables,
        )

        filter_ids = st.multiselect(
            label="Filters",
            options=list(fc.filters.keys()),
            default=de.iv_current_filter_ids,
            format_func=lambda fid: fc.filters[fid].pretty_name,
        )

    if target_variable is None or not variables:
        chart_container.write("No variables selected")
        return

    target = data.load_column(target_variable)
    input_variables = data.load_columns(list(variables))
    mask = fc.get_mask(filter_ids=filter_ids, index=target.index)

    if not pd.api.types.is_numeric_dtype(target):
        error_container.error(
            f"Error: Target variable must be numerical. Selected column is of type `<{target.dtype}>`."
        )
        return

    if not target[mask].isin([0, 1]).all():
        values = list(set(target.drop_duplicates().to_list()) - {0, 1})
        if len(values) > 10:
            values_str = ", ".join(map(str, values[:9] + ["..."] + values[-1:]))
        else:
            values_str = ", ".join(map(str, values))
        error_container.error(
            f"Error: Target variable must be binary (0 or 1).\n\n"
            f"Following values were found: [{values_str}]"
        )
        return

    for variable in variables:
        if (
            not pd.api.types.is_numeric_dtype(input_variables[variable])
            and input_variables[variable].nunique() > options.max_categorical_unique
        ):
            error_container.warning(
                f"Warning: Variable `{variable}` is not numerical and has more than {options.max_categorical_unique} unique values. "
                f"Total unique values: {input_variables[variable].nunique()}",
                icon=":material/warning:",
            )
            input_variables.drop(columns=[variable], inplace=True)

    iv_values = []

    for var in input_variables.columns:
        try:
            iv_values.append((var, de.get_iv(input_variables[var], target, mask)))
        except Exception as error:
            error_container.error(str(error))
            break
    else:
        with chart_container:
            chart_data = pd.DataFrame(iv_values, columns=["variable", "iv"])
            chart_data.sort_values("iv", ascending=False, inplace=True)
            chart = iv_bar_chart(chart_data)
            st.altair_chart(chart)

    with control_container:
        if st.button(
            "Save Config", width="stretch", type="secondary", icon=":material/save:"
        ):
            if any([
                de.iv_current_target != target.name,
                de.iv_current_variables != variables,
                de.iv_current_filter_ids != filter_ids,
            ]):
                de.iv_current_target = target.name
                de.iv_current_variables = variables
                de.iv_current_filter_ids = filter_ids
                st.rerun()


__all__ = ["iv_analysis_widget"]
