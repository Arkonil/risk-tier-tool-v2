import pandas as pd
import streamlit as st

from classes.scalars import Scalar

from views.components import columns_with_divider


def annualizing_factor_calculation(scalar: Scalar) -> Scalar:

    df = pd.DataFrame({
        "years": [scalar.period1, scalar.period2],
        "loss_rates": [scalar.period1_rate, scalar.period2_rate]
    })

    def year_transformer(
        y): return f"{int(y) if float(y).is_integer() else y} Years"

    def year_inv_transformer(s): return float(s.split(" ")[0])

    df['years'] = df['years'].map(year_transformer)
    df['loss_rates'] = df['loss_rates'] * 100

    edited_df = st.data_editor(
        df,
        column_config={
            "years": st.column_config.SelectboxColumn(
                "Years",
                width="medium",
                required=True,
                options=list(map(year_transformer, Scalar.period_options))
            ),
            "loss_rates": st.column_config.NumberColumn(
                f"{'$' if scalar.loss_rate_type == 'dlr' else '#'} Charge Off",
                width="medium",
                required=True,
                format="%.2f %%",
            )
        },
        hide_index=True,
        use_container_width=True,
        key=f"annualizing-factor-{scalar.loss_rate_type}",
    )
    
    if not edited_df.equals(df):

        edited_df['years'] = edited_df['years'].map(year_inv_transformer)
        edited_df['loss_rates'] = edited_df['loss_rates'] / 100

        scalar.period1 = edited_df.loc[0, 'years']
        scalar.period2 = edited_df.loc[1, 'years']

        scalar.period1_rate = edited_df.loc[0, 'loss_rates']
        scalar.period2_rate = edited_df.loc[1, 'loss_rates']
        
        st.rerun()

def risk_scalar_factor_calculation(scalar: Scalar) -> Scalar:

    df = pd.DataFrame({
        "Risk Tier": range(1, 6),
        "Maturity Adjustment Factor": scalar.maturity_adjustment_factor * 100,
        "Risk Scalar Factor": scalar.risk_scalar_factor
    })

    edited_df = st.data_editor(
        df,
        column_config={
            "Maturity Adjustment Factor": st.column_config.NumberColumn(
                label="Maturity Adjustment Factor",
                format="%.1f %%",
            ),
            "Risk Scalar Factor": st.column_config.NumberColumn(
                label="Risk Scalar Factor",
                format="%.1f",
                disabled=True
            )
        },
        hide_index=True,
        use_container_width=True,
        key=f"risk-scalar-factor-{scalar.loss_rate_type}",
    )

    if not edited_df.equals(df):
        scalar.maturity_adjustment_factor = edited_df['Maturity Adjustment Factor'] / 100
        
        st.rerun()

def scalar_edit_widget(scalars: Scalar) -> Scalar:
    
    annualizing_factor_calculation(scalars)

    st.write("Portfolio Scalar:", scalars.portfolio_scalar)

    risk_scalar_factor_calculation(scalars)

def show_scalars_page():
    session = st.session_state['session']

    st.title("Scalar Calculation")

    st.write("")
    st.write("")

    dlr_scalars_column, ulr_scalars_column = columns_with_divider(2)

    with dlr_scalars_column:
        st.subheader("$ Scalar Calculation")
        scalar_edit_widget(session.dlr_scalars)

    with ulr_scalars_column:
        st.subheader("# Scalar Calculation")
        scalar_edit_widget(session.ulr_scalars)

show_scalars_page()
