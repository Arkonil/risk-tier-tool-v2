import streamlit as st

from views.options_widgets.risk_tier_details import risk_tier_details_selector_widget
from views.options_widgets.scalars import scalar_calculation_widget


def options_view() -> None:
    st.markdown("# Options")

    st.divider()

    risk_tier_details_selector_widget()

    st.divider()

    scalar_calculation_widget()


options_page = st.Page(
    page=options_view,
    title="Options",
    icon=":material/settings:",
)


__all__ = ["options_page"]
