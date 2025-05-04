import pathlib
import typing as t

import streamlit as st

from classes.session import Session
    
def set_page_config():
    st.set_page_config(layout="wide")

    with open(pathlib.Path("assets/style.css")) as file:
        st.html(f"<style>{file.read()}</style>")

def _add_sesion_state_attr(name: str, obj: t.Any) -> None:
    if name not in st.session_state:
        st.session_state[name] = obj

def initialize_session():
    _add_sesion_state_attr("session", Session())