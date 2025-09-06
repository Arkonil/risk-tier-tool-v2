import altair as alt
import pandas as pd
import streamlit as st

from classes.session import Session


def iv_bar_chart(data: list[tuple[str, float]]):
    data = pd.DataFrame(data, columns=["variable", "iv"])
    data.sort_values("iv", ascending=False, inplace=True)

    # Define a limit for the primary y-axis. Values above this will be handled specially.
    y_axis_limit = 0.6

    # Create a new column for plotting, where IV values are clipped at the axis limit.
    data["iv_display"] = data["iv"].clip(upper=y_axis_limit)

    # --- Chart Layers ---

    # 1. Base Layer: The main bar chart
    # The bars are sorted by the original 'iv' value in descending order.
    color_values = ["#d8544f", "#8344ca", "#44c1ca", "#5cb75c"]

    x = alt.X(
        "variable:N",
        sort=alt.EncodingSortField(field="iv", op="max", order="descending"),
        axis=alt.Axis(
            title="Variable",
            labelAngle=0,
        ),
    )

    y = alt.Y(
        "iv_display:Q",
        axis=alt.Axis(title="Information Value (IV)"),
        scale=alt.Scale(domain=[0, y_axis_limit + 0.05]),
    )

    lower_bar_colors = alt.Color(
        "iv_display:Q",
        title="",
        scale=alt.Scale(
            type="threshold",
            domain=[0.02, 0.1, 0.3, 0.5],
            range=color_values + ["transparent"],
        ),
    ).legend(labelOffset=10, format=".2f")

    higher_bar_colors = alt.Gradient(
        gradient="linear",
        x1=1,
        x2=1,
        y1=1,
        y2=0,
        stops=[
            alt.GradientStop(color="hsla(35, 84%, 62%, 100%)", offset=0),
            alt.GradientStop(color="hsla(35, 84%, 62%, 70%)", offset=0.7),
            alt.GradientStop(color="hsla(35, 84%, 62%, 0%)", offset=1),
        ],
    )

    tooltip = [
        alt.Tooltip("variable", title="Variable"),
        alt.Tooltip("iv", title="Information Value", format=".2f"),
    ]

    lower_bars = (
        alt.Chart(data)
        .mark_bar()
        .encode(x=x, y=y, color=lower_bar_colors, tooltip=tooltip)
    )

    # 2. Data for bars that exceed the y-axis limit
    break_data = data[data["iv"] > y_axis_limit].copy()

    higher_bars = (
        alt.Chart(break_data)
        .mark_bar(color=higher_bar_colors)
        .encode(x=x, y=y, tooltip=tooltip)
    )

    # 3. Rule Layer: Horizontal reference lines
    rule_df = pd.DataFrame({"y": [0.02, 0.1, 0.3, 0.5]})

    rules = (
        alt.Chart(rule_df)
        .mark_rule(strokeWidth=1)
        .encode(
            y="y:Q",
            strokeDash=alt.condition(
                alt.datum.y != 0.5, alt.value([5, 5]), alt.value([1, 0])
            ),
            color=alt.Color(
                "y:Q", scale=alt.Scale(domain=[0.02, 0.1, 0.3, 0.5], range=color_values)
            ).legend(None),
        )
    )

    # 4. Text Layer: Display the actual IV value above the clipped bars
    text_labels = (
        alt.Chart(break_data)
        .mark_text(
            align="center",
            dy=-15,  # Position text above the break symbol
            # fontSize=11,
            color="white" if st.context.theme.type == "dark" else "black",
        )
        .encode(x=x, y=y, text=alt.Text("iv:Q", format=".2f"))
    )

    chart = (
        (lower_bars + higher_bars + text_labels + rules)
        .configure_axis(grid=False)
        .properties(height=500)
    )

    return chart


def iv_analysis_widget():
    session: Session = st.session_state["session"]
    data = session.data
    de = session.data_explorer
    fc = session.filter_container

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

    if not pd.api.types.is_numeric_dtype(target):
        error_container.error(
            f"Error: Target variable must be numerical. Selected column is of type `<{target.dtype}>`."
        )
        return

    if not target.isin([0, 1]).all():
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

    input_variables = data.load_columns(list(variables))

    mask = fc.get_mask(filter_ids=filter_ids, index=target.index)

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
