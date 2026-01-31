import typing as t

import numpy as np
import pandas as pd
import streamlit as st

from risc_tool.data.models.enums import RSDetCol
from risc_tool.data.session import Session


def color_selector(
    type: t.Literal["font", "background"],
    row_indices: list[int],
    color: str | None,
    disabled: bool,
) -> None:
    session: Session = st.session_state["session"]
    config_vm = session.config_view_model

    col1, col2 = st.columns([1, 4])

    with col1:
        color = st.color_picker(
            label=f"{type.capitalize()} Color",
            label_visibility="collapsed",
            value=color,
        )

    callback = (
        config_vm.set_risk_seg_font_color
        if type == "font"
        else config_vm.set_risk_seg_bg_color
    )

    with col2:
        st.button(
            label=f"Use {type.capitalize()} Color",
            width="stretch",
            type="secondary",
            icon=":material/palette:",
            disabled=disabled,
            on_click=callback,
            kwargs={
                "row_indices": row_indices,
                "color": color,
            },
        )


def risk_seg_details_selector() -> None:
    session: Session = st.session_state["session"]
    config_vm = session.config_view_model

    risk_segment_details = config_vm.risk_segment_details.copy()

    with pd.option_context("future.no_silent_downcasting", True):
        risk_segment_details[RSDetCol.LOWER_RATE] = (
            risk_segment_details[RSDetCol.LOWER_RATE]
            .replace({-np.inf: np.nan})
            .infer_objects(copy=False)
            .mul(100)
        )
        risk_segment_details[RSDetCol.UPPER_RATE] = (
            risk_segment_details[RSDetCol.UPPER_RATE]
            .replace({np.inf: np.nan})
            .infer_objects(copy=False)
            .mul(100)
        )

    risk_segment_details[RSDetCol.SELECTED] = False

    risk_segment_details_styled = risk_segment_details.style

    for row_index in risk_segment_details.index:
        for column in risk_segment_details.columns:
            if column not in (
                RSDetCol.FONT_COLOR,
                RSDetCol.BG_COLOR,
            ):
                continue

            font_color = risk_segment_details.loc[row_index, RSDetCol.FONT_COLOR]
            bg_color = risk_segment_details.loc[row_index, RSDetCol.BG_COLOR]

            risk_segment_details_styled = risk_segment_details_styled.set_properties(
                subset=(slice(row_index, row_index), slice(column, column)),
                **{
                    "color": str(font_color),
                    "background-color": str(bg_color),
                },
            )

    column_config = {
        RSDetCol.RISK_SEGMENT.value: st.column_config.TextColumn(
            label=RSDetCol.RISK_SEGMENT,
        ),
        RSDetCol.LOWER_RATE.value: st.column_config.NumberColumn(
            label=RSDetCol.LOWER_RATE,
            format="%.2f %%",
            disabled=True,
        ),
        RSDetCol.UPPER_RATE.value: st.column_config.NumberColumn(
            label=RSDetCol.UPPER_RATE,
            format="%.2f %%",
            min_value=0.0,
            max_value=100.0,
        ),
        RSDetCol.BG_COLOR.value: st.column_config.TextColumn(
            label=RSDetCol.BG_COLOR,
            disabled=True,
        ),
        RSDetCol.FONT_COLOR.value: st.column_config.TextColumn(
            label=RSDetCol.FONT_COLOR,
            disabled=True,
        ),
        RSDetCol.SELECTED.value: st.column_config.CheckboxColumn(
            label=RSDetCol.SELECTED,
        ),
    }

    st.subheader("Risk Segment Details")

    col1, col2 = st.columns([4, 1])

    with col1:
        edited_risk_segment_details = st.data_editor(
            data=risk_segment_details_styled,
            width="stretch",
            column_order=[
                RSDetCol.SELECTED,
                RSDetCol.RISK_SEGMENT,
                RSDetCol.LOWER_RATE,
                RSDetCol.UPPER_RATE,
                RSDetCol.FONT_COLOR,
                RSDetCol.BG_COLOR,
            ],
            column_config=column_config,
        )

        selected = edited_risk_segment_details[RSDetCol.SELECTED].any()

    with col2:
        st.write("#### Controls")

        # Add Row Button
        st.button(
            label="Add Row",
            width="stretch",
            type="secondary",
            icon=":material/add:",
            on_click=config_vm.add_risk_seg_row,
        )

        # Delete Selected Rows Button
        st.button(
            label="Delete Selected Rows",
            width="stretch",
            type="secondary",
            icon=":material/delete:",
            disabled=not selected,
            on_click=config_vm.delete_selected_risk_seg_rows,
            args=(
                edited_risk_segment_details[
                    edited_risk_segment_details[RSDetCol.SELECTED]
                ].index,
            ),
        )

        # Set Color Button
        color_selector(
            type="font",
            row_indices=edited_risk_segment_details[
                edited_risk_segment_details[RSDetCol.SELECTED]
            ].index.to_list(),
            color=edited_risk_segment_details[
                edited_risk_segment_details[RSDetCol.SELECTED]
            ][RSDetCol.FONT_COLOR].values[0]
            if selected
            else None,
            disabled=not selected,
        )

        color_selector(
            type="background",
            row_indices=edited_risk_segment_details[
                edited_risk_segment_details[RSDetCol.SELECTED]
            ].index.to_list(),
            color=edited_risk_segment_details[
                edited_risk_segment_details[RSDetCol.SELECTED]
            ][RSDetCol.BG_COLOR].values[0]
            if selected
            else None,
            disabled=not selected,
        )

        # Reset Button
        st.button(
            label="Reset",
            width="stretch",
            type="secondary",
            icon=":material/restart_alt:",
            on_click=config_vm.set_risk_seg_default_values,
        )

    st.info(
        f"The value :blue-badge[**`None`**] in the column "
        f":blue-badge[**`{RSDetCol.UPPER_RATE}`**] "
        f"represents _+Infinity_.",
        icon=":material/info:",
    )

    if not edited_risk_segment_details[RSDetCol.RISK_SEGMENT].is_unique:
        duplicate_values = (
            edited_risk_segment_details[
                edited_risk_segment_details[RSDetCol.RISK_SEGMENT].duplicated(
                    keep=False
                )
            ][RSDetCol.RISK_SEGMENT]
            .unique()
            .tolist()
        )

        st.error(
            f"Risk Segment Names must be unique. The following names have repetition: {duplicate_values}",
            icon=":material/error:",
        )

        return

    if (edited_risk_segment_details[RSDetCol.RISK_SEGMENT] == "").any():
        st.error("Risk Segment Names cannot be empty", icon=":material/error:")
        return

    needs_rerun = False

    s1 = edited_risk_segment_details[RSDetCol.RISK_SEGMENT].str.strip()
    s2 = risk_segment_details[RSDetCol.RISK_SEGMENT].str.strip()

    unequal_names = ~(s1.eq(s2) | (s1.isna() & s2.isna()))

    if unequal_names.any():
        unequal_names = unequal_names[unequal_names]

        for row_index in unequal_names.index:
            config_vm.set_risk_seg_name(
                row_index=row_index,
                name=s1[row_index],
            )
        needs_rerun = True

    s1 = edited_risk_segment_details[RSDetCol.UPPER_RATE]
    s2 = risk_segment_details[RSDetCol.UPPER_RATE]

    unequal_upper_rates = ~(s1.eq(s2) | (s1.isna() & s2.isna()))

    if unequal_upper_rates.any():
        config_vm.set_risk_seg_upper_rate(s1[unequal_upper_rates].fillna(np.inf) / 100)
        needs_rerun = True

    if needs_rerun:
        st.rerun()


__all__ = ["risk_seg_details_selector"]
