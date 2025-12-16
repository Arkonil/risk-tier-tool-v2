import streamlit as st

from risc_tool.data.session import Session


def set_session_state():
    if "session" not in st.session_state:
        session = Session()
        st.session_state["session"] = session


__all__ = ["set_session_state"]
