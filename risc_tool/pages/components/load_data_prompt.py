import streamlit as st

from risc_tool.data.models.asset_path import AssetPath
from risc_tool.pages.data_importer import data_importer_page


def load_data_prompt(key: int = 0):
    with st.container(horizontal_alignment="center"):
        st.space("large")

        st.image(AssetPath.NO_DATA_ERROR_ICON, width=250)

        st.subheader(
            "No Data Loaded",
            anchor=False,
            width="content",
            text_alignment="center",
        )

        if st.button(
            "Load Data",
            key=key,
            type="primary",
        ):
            st.switch_page(data_importer_page)


__all__ = ["load_data_prompt"]
