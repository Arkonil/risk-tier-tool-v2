import streamlit as st

__all__ = ["set_page_navigation"]

_homepage = st.Page(
    page=f"{__name__}/home.py",
    title="Home",
    icon=":material/home:",
    default=True
)

_summary_page = st.Page(
    page=f"{__name__}/summary.py",
    title="Summary",
    icon=":material/dashboard_2:",
)

_data_importer_page = st.Page(
    page=f"{__name__}/data_importer.py",
    title="Data Importer",
    icon=":material/file_upload:",
)

_scalar_page = st.Page(
    page=f"{__name__}/scalars.py",
    title="Scalar Calculation",
    icon=":material/ssid_chart:"
)

_iteration_graph_page = st.Page(
    page=f"{__name__}/iterations.py",
    title="Iterations",
    icon=":material/account_tree:",
)

_charts_page = st.Page(
    page=f"{__name__}/charts.py",
    title="Charts",
    icon=":material/monitoring:",
)

_export_page = st.Page(
    page=f"{__name__}/export.py",
    title="Export",
    icon=":material/file_download:",
)

def set_page_navigation():
    pg = st.navigation({
        "Home": [_homepage, _summary_page],
        "Tools": [_data_importer_page, _scalar_page, _iteration_graph_page],
        "Results": [_charts_page, _export_page]
    })

    pg.run()
