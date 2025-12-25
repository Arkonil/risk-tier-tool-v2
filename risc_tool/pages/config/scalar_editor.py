import pandas as pd
import streamlit as st

from risc_tool.data.models.enums import LossRateTypes, RSDetCol, ScalarTableColumn
from risc_tool.data.session import Session


def annualization_factor_editor(loss_rate_type: LossRateTypes) -> None:
    session: Session = st.session_state["session"]
    config_vm = session.config_view_model

    df = pd.DataFrame({
        "Loss Rate Description": ["Current Rate", "Lifetime Rate"],
        "MOB": [config_vm.current_rate_mob, config_vm.lifetime_rate_mob],
        "Loss Rates": [
            config_vm.get_current_rate(loss_rate_type),
            config_vm.get_lifetime_rate(loss_rate_type),
        ],
    })

    df["MOB"] = df["MOB"].map(lambda mob: f"{mob} MOB")
    df["Loss Rates"] = df["Loss Rates"] * 100

    scalar = config_vm.get_scalar(loss_rate_type)

    col1, _, col2, _ = st.columns([12, 1, 4, 1])

    edited_df = col1.data_editor(
        df,
        column_config={
            "Loss Rate Description": st.column_config.TextColumn(
                label="Loss Rate Description",
                disabled=True,
            ),
            "MOB": st.column_config.TextColumn(
                label="MOB",
                disabled=True,
            ),
            "Loss Rates": st.column_config.NumberColumn(
                label=f"{'$' if scalar.loss_rate_type == LossRateTypes.DLR else r'#'} Bad Rate",
                required=True,
                format="%.2f %%",
            ),
        },
        hide_index=True,
        width="stretch",
        key=f"annualizing-factor-{scalar.loss_rate_type}",
    )

    col2.metric(
        label="{0} Portfolio Scalar".format(
            "$" if scalar.loss_rate_type == LossRateTypes.DLR else r"\#"
        ),
        value=f"{scalar.portfolio_scalar:.2f}",
        border=True,
    )

    if not edited_df.equals(df):
        edited_df["Loss Rates"] = edited_df["Loss Rates"] / 100

        new_current_rate = edited_df.loc[0, "Loss Rates"]
        new_lifetime_rate = edited_df.loc[1, "Loss Rates"]

        if not isinstance(new_current_rate, float):
            raise ValueError(f"{new_current_rate} is not a float")

        if not isinstance(new_lifetime_rate, float):
            raise ValueError(f"{new_lifetime_rate} is not a float")

        config_vm.set_current_rate(loss_rate_type, new_current_rate)
        config_vm.set_lifetime_rate(loss_rate_type, new_lifetime_rate)

        st.rerun()


def risk_scalar_factor_editor(loss_rate_type: LossRateTypes) -> None:
    session: Session = st.session_state["session"]
    config_vm = session.config_view_model

    scalar = config_vm.get_scalar(loss_rate_type)

    # Risk Segment Column
    risk_seg_names = config_vm.risk_segment_details[RSDetCol.RISK_SEGMENT].rename(
        ScalarTableColumn.RISK_SEGMENT
    )

    # Maturity Adjustment Factor
    column_name = (
        RSDetCol.MAF_DLR if loss_rate_type == LossRateTypes.DLR else RSDetCol.MAF_ULR
    )
    maf = config_vm.risk_segment_details[column_name].rename(ScalarTableColumn.MAF)

    # Risk Scalar Factor
    rsf = scalar.get_risk_scalar_factor(maf)

    df = pd.DataFrame([risk_seg_names, 100 * maf, rsf]).T

    df_styled = df.style

    for row_index in df.index:
        if not isinstance(row_index, int):
            continue

        risk_seg_name = str(df.loc[row_index, ScalarTableColumn.RISK_SEGMENT])
        color = config_vm.get_color(risk_seg_name)

        df_styled = df_styled.set_properties(
            subset=(
                slice(row_index, row_index),
                slice(ScalarTableColumn.RISK_SEGMENT, ScalarTableColumn.RISK_SEGMENT),
            ),
            **{
                "color": str(color.loc[row_index, RSDetCol.FONT_COLOR]),
                "background-color": str(color.loc[row_index, RSDetCol.BG_COLOR]),
            },
        )

    key = f"risk-scalar-factor-{scalar.loss_rate_type}"

    def on_edit():
        changes = st.session_state[key]

        if (
            isinstance(changes, dict)
            and changes
            and "edited_rows" in changes
            and changes["edited_rows"]
        ):
            for row_index, columns in changes["edited_rows"].items():
                for column_name, column_value in columns.items():
                    if column_name == ScalarTableColumn.MAF:
                        config_vm.set_risk_seg_maf(
                            row_index=row_index,
                            maf=column_value / 100,
                            loss_rate_type=scalar.loss_rate_type,
                        )

    st.data_editor(
        df_styled,
        column_config={
            ScalarTableColumn.RISK_SEGMENT: st.column_config.TextColumn(
                label=ScalarTableColumn.RISK_SEGMENT,
                disabled=True,
            ),
            ScalarTableColumn.MAF: st.column_config.NumberColumn(
                label=ScalarTableColumn.MAF,
                format="%.1f %%",
            ),
            ScalarTableColumn.RISK_SCALAR_FACTOR: st.column_config.NumberColumn(
                label=ScalarTableColumn.RISK_SCALAR_FACTOR, format="%.2f", disabled=True
            ),
        },
        hide_index=True,
        width="stretch",
        key=key,
        on_change=on_edit,
    )


def scalar_editor(loss_rate_type: LossRateTypes):
    st.subheader(f"{'$' if loss_rate_type == LossRateTypes.DLR else r'#'} Bad Rate")
    annualization_factor_editor(loss_rate_type)
    risk_scalar_factor_editor(loss_rate_type)


def scalar_calculation() -> None:
    st.subheader("Scalar Calculation")

    dlr_scalars_column, ulr_scalars_column = st.columns(2)

    with dlr_scalars_column:
        scalar_editor(LossRateTypes.ULR)

    with ulr_scalars_column:
        scalar_editor(LossRateTypes.DLR)

    st.info(
        ":blue-badge[`Risk Scalar Factor`] is calculated as "
        ":blue-badge[`max(portfolio_scalar * maturity_adjustment_factor, 1)`], "
        "as the loss rate at :blue-badge[`n + 1`] th MOB will be more than or eqaul to "
        "the loss rate of :blue-badge[`n`] th MOB.",
        icon=":material/info:",
    )


__all__ = ["scalar_calculation"]
