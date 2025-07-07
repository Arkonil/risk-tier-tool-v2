import typing as t

import numpy as np
import pandas as pd
import streamlit as st

from classes.constants import RTDetCol
from classes.session import Session


def color_selector_widget(
    type: t.Literal["font", "background"],
    row_indices: t.Iterator[int],
    color: str | None,
    disabled: bool,
) -> None:
    session: Session = st.session_state["session"]
    options = session.options

    col1, col2 = st.columns([1, 4])

    with col1:
        color = st.color_picker(
            label=f"{type.capitalize()} Color",
            label_visibility="collapsed",
            value=color,
        )

    callback = (
        options.set_risk_tier_font_color
        if type == "font"
        else options.set_risk_tier_bg_color
    )

    with col2:
        st.button(
            label=f"Use {type.capitalize()} Color",
            use_container_width=True,
            type="secondary",
            icon=":material/palette:",
            disabled=disabled,
            on_click=callback,
            kwargs={
                "row_indices": row_indices,
                "color": color,
            },
        )


def risk_tier_details_selector_widget() -> None:
    st.markdown("## Risk Tier Details")

    session: Session = st.session_state["session"]
    options = session.options

    risk_tier_details = options.risk_tier_details.copy()

    with pd.option_context("future.no_silent_downcasting", True):
        risk_tier_details[RTDetCol.LOWER_RATE] = (
            risk_tier_details[RTDetCol.LOWER_RATE]
            .replace({-np.inf: np.nan})
            .infer_objects(copy=False)
            * 100
        )
        risk_tier_details[RTDetCol.UPPER_RATE] = (
            risk_tier_details[RTDetCol.UPPER_RATE]
            .replace({np.inf: np.nan})
            .infer_objects(copy=False)
            * 100
        )
    risk_tier_details[RTDetCol.SELECTED] = False

    risk_tier_details_styled = risk_tier_details.style
    idx = pd.IndexSlice

    for row_index in risk_tier_details.index:
        for column in risk_tier_details.columns:
            if column not in (
                RTDetCol.FONT_COLOR,
                RTDetCol.BG_COLOR,
            ):
                continue

            font_color = risk_tier_details.loc[row_index, RTDetCol.FONT_COLOR]
            bg_color = risk_tier_details.loc[row_index, RTDetCol.BG_COLOR]

            risk_tier_details_styled = risk_tier_details_styled.set_properties(
                **{
                    "color": font_color,
                    "background-color": bg_color,
                },
                subset=idx[row_index, column],
            )

    column_config = {
        RTDetCol.RISK_TIER: st.column_config.TextColumn(
            label=RTDetCol.RISK_TIER,
        ),
        RTDetCol.LOWER_RATE: st.column_config.NumberColumn(
            label=RTDetCol.LOWER_RATE,
            format="%.2f %%",
            disabled=True,
        ),
        RTDetCol.UPPER_RATE: st.column_config.NumberColumn(
            label=RTDetCol.UPPER_RATE,
            format="%.2f %%",
            min_value=0.0,
            max_value=100.0,
        ),
        RTDetCol.BG_COLOR: st.column_config.TextColumn(
            label=RTDetCol.BG_COLOR,
            disabled=True,
        ),
        RTDetCol.FONT_COLOR: st.column_config.TextColumn(
            label=RTDetCol.FONT_COLOR,
            disabled=True,
        ),
        RTDetCol.SELECTED: st.column_config.CheckboxColumn(
            label=RTDetCol.SELECTED,
        ),
    }

    col1, col2 = st.columns([4, 1])

    with col1:
        edited_risk_tier_details = st.data_editor(
            risk_tier_details_styled,
            use_container_width=True,
            column_config=column_config,
            column_order=[
                RTDetCol.SELECTED,
                RTDetCol.RISK_TIER,
                RTDetCol.LOWER_RATE,
                RTDetCol.UPPER_RATE,
                RTDetCol.FONT_COLOR,
                RTDetCol.BG_COLOR,
            ],
        )

        selected = edited_risk_tier_details[RTDetCol.SELECTED].any()

    with col2:
        st.write("#### Controls")
        # Add Row Button
        st.button(
            "Add Row",
            use_container_width=True,
            type="secondary",
            icon=":material/add:",
            on_click=options.add_risk_tier_row,
        )

        # Delete Selected Rows Button
        st.button(
            "Delete Selected Rows",
            use_container_width=True,
            type="secondary",
            icon=":material/delete:",
            disabled=not selected,
            on_click=options.delete_selected_risk_tier_rows,
            args=(
                edited_risk_tier_details[
                    edited_risk_tier_details[RTDetCol.SELECTED]
                ].index,
            ),
        )

        # Set Color Button
        color_selector_widget(
            type="font",
            row_indices=edited_risk_tier_details[
                edited_risk_tier_details[RTDetCol.SELECTED]
            ].index,
            color=edited_risk_tier_details[edited_risk_tier_details[RTDetCol.SELECTED]][
                RTDetCol.FONT_COLOR
            ].values[0]
            if selected
            else None,
            disabled=not selected,
        )

        color_selector_widget(
            type="background",
            row_indices=edited_risk_tier_details[
                edited_risk_tier_details[RTDetCol.SELECTED]
            ].index,
            color=edited_risk_tier_details[edited_risk_tier_details[RTDetCol.SELECTED]][
                RTDetCol.BG_COLOR
            ].values[0]
            if selected
            else None,
            disabled=not selected,
        )

        # Reset Button
        st.button(
            "Reset",
            use_container_width=True,
            type="secondary",
            icon=":material/restart_alt:",
            on_click=options.set_default_values,
        )

    st.info(
        f"The value :blue-badge[**`None`**] in the column "
        f":blue-badge[**`{RTDetCol.UPPER_RATE}`**] "
        f"represents _+Infinity_.",
        icon=":material/info:",
    )

    if not edited_risk_tier_details[RTDetCol.RISK_TIER].is_unique:
        duplicate_values = (
            edited_risk_tier_details[
                edited_risk_tier_details[RTDetCol.RISK_TIER].duplicated(keep=False)
            ][RTDetCol.RISK_TIER]
            .unique()
            .tolist()
        )

        st.error(
            f"Risk Tier Names must be unique. The following names have repitation: {duplicate_values}",
            icon=":material/error:",
        )

        return

    if (edited_risk_tier_details[RTDetCol.RISK_TIER] == "").any():
        st.error("Risk Tier Names cannot be empty", icon=":material/error:")
        return

    needs_rerun = False

    s1 = edited_risk_tier_details[RTDetCol.RISK_TIER].str.strip()
    s2 = risk_tier_details[RTDetCol.RISK_TIER].str.strip()

    unequal_names = ~(s1.eq(s2) | (s1.isna() & s2.isna()))

    if unequal_names.any():
        unequal_names = unequal_names[unequal_names]

        for row_index in unequal_names.index:
            options.set_risk_tier_name(
                row_index=row_index,
                name=s1[row_index],
            )
        needs_rerun = True

    s1 = edited_risk_tier_details[RTDetCol.UPPER_RATE]
    s2 = risk_tier_details[RTDetCol.UPPER_RATE]

    unequal_upper_rates = ~(s1.eq(s2) | (s1.isna() & s2.isna()))

    if unequal_upper_rates.any():
        options.set_risk_tier_upper_rate(s1[unequal_upper_rates].fillna(np.inf) / 100)
        needs_rerun = True

    if needs_rerun:
        st.rerun()


__all__ = ["risk_tier_details_selector_widget"]
