import streamlit as st

from views.options_widgets import (
    show_risk_tier_details_selector,
    show_scalar_calculation,
)


def options() -> None:
    st.markdown("# Options")

    st.divider()

    show_risk_tier_details_selector()

    st.divider()

    show_scalar_calculation()


options_page = st.Page(
    page=options,
    title="Options",
    icon=":material/settings:",
)


__all__ = ["options_page"]
