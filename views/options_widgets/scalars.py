import pandas as pd
import streamlit as st

from classes.constants import LossRateTypes, RTDetCol, ScalarTableColumn
from classes.data import Data
from classes.scalars import Scalar
from classes.session import Session


def annualizing_factor_calculation(scalar: Scalar, data: Data) -> Scalar:
    df = pd.DataFrame({
        "Loss Rate Description": ["Current Rate", "Lifetime Rate"],
        "MOB": [data.current_rate_mob, data.lifetime_rate_mob],
        "Loss Rates": [scalar.current_rate, scalar.lifetime_rate],
    })

    df["MOB"] = df["MOB"].map(lambda mob: f"{mob} MOB")
    df["Loss Rates"] = df["Loss Rates"] * 100

    st.subheader(
        f"{'$' if scalar.loss_rate_type == LossRateTypes.DLR else r'#'} Scalar Calculation"
    )

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
                label=f"{'$' if scalar.loss_rate_type == LossRateTypes.DLR else r'#'} Charge Off",
                required=True,
                format="%.2f %%",
            ),
        },
        hide_index=True,
        use_container_width=True,
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

        scalar.current_rate = edited_df.loc[0, "Loss Rates"]
        scalar.lifetime_rate = edited_df.loc[1, "Loss Rates"]

        st.rerun()


def risk_scalar_factor_calculation(scalar: Scalar) -> Scalar:
    session: Session = st.session_state["session"]
    options = session.options

    # Risk Tier Column
    risk_tier = options.risk_tier_details[RTDetCol.RISK_TIER].rename(
        ScalarTableColumn.RISK_TIER
    )

    # Maturity Adjustment Factor
    column_name = (
        RTDetCol.MAF_DLR
        if scalar.loss_rate_type == LossRateTypes.DLR
        else RTDetCol.MAF_ULR
    )
    maf = options.risk_tier_details[column_name].rename(ScalarTableColumn.MAF)

    # Risk Scalar Factor
    rsf = scalar.get_risk_scalar_factor(maf)

    df = pd.DataFrame([risk_tier, 100 * maf, rsf]).T

    idx = pd.IndexSlice
    df_styled = df.style

    for row_index in df.index:
        color = options.get_color(df.loc[row_index, ScalarTableColumn.RISK_TIER])
        df_styled = df_styled.set_properties(
            **{
                "color": color[RTDetCol.FONT_COLOR],
                "background-color": color[RTDetCol.BG_COLOR],
            },
            subset=idx[row_index, ScalarTableColumn.RISK_TIER],
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
                        options.set_risk_tier_maf(
                            row_index=row_index,
                            maf=column_value / 100,
                            loss_rate_type=scalar.loss_rate_type,
                        )

    st.data_editor(
        df_styled,
        column_config={
            ScalarTableColumn.RISK_TIER: st.column_config.TextColumn(
                label=ScalarTableColumn.RISK_TIER,
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
        use_container_width=True,
        key=key,
        on_change=on_edit,
    )


def scalar_edit_widget(scalars: Scalar, data: Data) -> Scalar:
    annualizing_factor_calculation(scalars, data)
    risk_scalar_factor_calculation(scalars)


def show_scalar_calculation() -> None:
    st.markdown("## Scalar Calculation")

    session = st.session_state["session"]

    dlr_scalars_column, ulr_scalars_column = st.columns(2)

    with dlr_scalars_column:
        scalar_edit_widget(session.dlr_scalars, session.data)

    with ulr_scalars_column:
        scalar_edit_widget(session.ulr_scalars, session.data)

    st.info(
        ":blue-badge[**Risk Scalar Factor**] is calculated as "
        ":blue-badge[`max(portfolio_scalar * maturity_adjustment_factor, 1)`], "
        "as the loss rate at :blue-badge[`n + 1`] th MOB will be more than or eqaul to "
        "the loss rate of :blue-badge[`n`] th MOB",
        icon=":material/info:",
    )
