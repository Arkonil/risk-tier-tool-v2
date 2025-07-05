import streamlit as st

from classes.session import Session
from views.components import show_iteration_selector, show_load_data_first_error


def show_python_code_download():
    if show_load_data_first_error(key=1):
        return

    session: Session = st.session_state["session"]

    st.markdown("### Download Python Code")

    code = ""
    code += "# This is a placeholder for the Python code export.\n"
    code += "# You can implement the logic to export the session data as Python code.\n"
    code += "\n"
    code += "import pandas as pd\n"
    code += "import numpy as np\n"
    code += "\n"
    code += "# Example of creating a DataFrame from session data\n"
    code += "data = {\n"
    code += "    'column1': [1, 2, 3],\n"
    code += "    'column2': [4, 5, 6]\n"
    code += "}\n"

    st.code(code, language="python")


__all__ = ["show_python_code_download"]
