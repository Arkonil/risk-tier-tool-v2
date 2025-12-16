import streamlit as st

from risc_tool.pages.data_importer import data_importer_page
from risc_tool.pages.home import home_page


def set_page_navigation():
    pg = st.navigation({
        "Home": [
            home_page,
        ],
        "Tools": [
            data_importer_page,
        ],
    })

    pg.run()


__all__ = ["set_page_navigation"]
