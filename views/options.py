import streamlit as st

from views.options_widgets import (
    show_risk_tier_details_selector,
    show_scalar_calculation,
)


def show_options_page() -> None:
    st.markdown("# Options")

    st.write("")
    st.write("")

    with st.expander("Risk Tier Details", expanded=True):
        show_risk_tier_details_selector()

    st.write("")
    st.write("")

    with st.expander("Scalar Calculation", expanded=True):
        show_scalar_calculation()


show_options_page()
