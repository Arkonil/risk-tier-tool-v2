import pathlib
import typing as t

import streamlit as st

from classes.constants import AssetPath
from classes.session import Session


def set_page_config():
    st.set_page_config(
        page_title="Risk Tier Development Tool",
        page_icon=AssetPath.RT_ICON,
        layout="wide",
    )

    with open(pathlib.Path(AssetPath.STYLESHEET), encoding="utf-8") as file:
        st.html(f"<style>{file.read()}</style>")


def _add_sesion_state_attr(name: str, obj: t.Any) -> None:
    if name not in st.session_state:
        st.session_state[name] = obj


def initialize_session():
    _add_sesion_state_attr("session", Session())


__all__ = ["set_page_config", "initialize_session"]
