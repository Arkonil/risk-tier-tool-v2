import streamlit as st

from views.options_widgets import (
    show_risk_tier_details_selector,
    show_scalar_calculation,
)


def show_options_page() -> None:
    st.markdown("# Options")

    st.divider()

    show_risk_tier_details_selector()

    st.divider()

    show_scalar_calculation()


show_options_page()
