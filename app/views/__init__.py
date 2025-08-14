import streamlit as st

from views.home import home_page
from views.summary import summary_page
from views.data_importer import data_importer_page
from views.options_widgets import options_page
from views.iterations_widgets import iteration_graph_page
from views.charts import charts_page
from views.export_widgets import export_page
from views.filter_widgets import filter_page


def set_page_navigation():
    pg = st.navigation({
        "Home": [home_page, summary_page],
        "Tools": [
            data_importer_page,
            filter_page,
            options_page,
            iteration_graph_page,
        ],
        "Results": [charts_page, export_page],
    })

    pg.run()


__all__ = ["set_page_navigation"]
