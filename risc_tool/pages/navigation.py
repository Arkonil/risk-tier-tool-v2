import streamlit as st

from risc_tool.pages.config import config_page
from risc_tool.pages.data_explorer import data_explorer_page
from risc_tool.pages.data_importer import data_importer_page
from risc_tool.pages.export import export_page
from risc_tool.pages.filters import filter_page
from risc_tool.pages.home import home_page
from risc_tool.pages.iterations import iterations_page
from risc_tool.pages.metrics import metrics_page


def set_page_navigation():
    pg = st.navigation({
        "Home": [
            home_page,
        ],
        "Tools": [
            data_importer_page,
            data_explorer_page,
            metrics_page,
            filter_page,
            config_page,
            iterations_page,
        ],
        "Results": [
            export_page,
        ],
    })

    pg.run()


__all__ = ["set_page_navigation"]
