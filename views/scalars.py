import pandas as pd
import streamlit as st

from classes.common import SUB_RISK_TIERS, color_map, Names
from classes.data import Data
from classes.scalars import Scalar

def annualizing_factor_calculation(scalar: Scalar, data: Data) -> Scalar:
    df = pd.DataFrame({
        "Loss Rate Description": ["Current Rate", "Lifetime Rate"],
        "MOB": [data.current_rate_mob, data.lifetime_rate_mob],
        "Loss Rates": [scalar.current_rate, scalar.lifetime_rate]
    })

    df['MOB'] = df['MOB'].map(lambda mob: f"{mob} MOB")
    df['Loss Rates'] = df['Loss Rates'] * 100

    st.subheader(f"{'$' if scalar.loss_rate_type == 'dlr' else r'#'} Scalar Calculation")

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
                label=f"{'$' if scalar.loss_rate_type == 'dlr' else r'#'} Charge Off",
                required=True,
                format="%.2f %%",
            )
        },
        hide_index=True,
        use_container_width=True,
        key=f"annualizing-factor-{scalar.loss_rate_type}",
    )

    col2.metric(
        label="{0} Portfolio Scalar".format('$' if scalar.loss_rate_type == 'dlr' else r'\#'),
        value=f"{scalar.portfolio_scalar:.2f}",
        border=True
    )

    if not edited_df.equals(df):
        edited_df['Loss Rates'] = edited_df['Loss Rates'] / 100

        scalar.current_rate = edited_df.loc[0, 'Loss Rates']
        scalar.lifetime_rate = edited_df.loc[1, 'Loss Rates']

        st.rerun()

def risk_scalar_factor_calculation(scalar: Scalar) -> Scalar:
    df = pd.DataFrame({
        Names.RISK_TIER.value: SUB_RISK_TIERS,
        Names.MATURITY_ADJUSTMENT_FACTOR.value: scalar.maturity_adjustment_factor * 100,
        Names.RISK_SCALAR_FACTOR.value: scalar.risk_scalar_factor
    })

    df = df.style.map(lambda v: f'background-color: {color_map[v]};', subset=[Names.RISK_TIER.value])

    edited_df = st.data_editor(
        df,
        column_config={
            Names.RISK_TIER.value: st.column_config.TextColumn(
                label=Names.RISK_TIER.value,
                disabled=True,
            ),
            Names.MATURITY_ADJUSTMENT_FACTOR.value: st.column_config.NumberColumn(
                label=Names.MATURITY_ADJUSTMENT_FACTOR.value,
                format="%.1f %%",

            ),
            Names.RISK_SCALAR_FACTOR.value: st.column_config.NumberColumn(
                label=Names.RISK_SCALAR_FACTOR.value,
                format="%.2f",
                disabled=True
            )
        },
        hide_index=True,
        use_container_width=True,
        key=f"risk-scalar-factor-{scalar.loss_rate_type}",
    )

    if not edited_df.equals(df.data):
        scalar.maturity_adjustment_factor = edited_df[Names.MATURITY_ADJUSTMENT_FACTOR.value] / 100

        st.rerun()

def scalar_edit_widget(scalars: Scalar, data: Data) -> Scalar:

    annualizing_factor_calculation(scalars, data)
    risk_scalar_factor_calculation(scalars)

def show_scalars_page():
    session = st.session_state['session']

    st.title("Scalar Calculation")

    st.write("")
    st.write("")

    dlr_scalars_column, ulr_scalars_column = st.columns(2)

    with dlr_scalars_column:
        scalar_edit_widget(session.dlr_scalars, session.data)

    with ulr_scalars_column:
        scalar_edit_widget(session.ulr_scalars, session.data)

show_scalars_page()
