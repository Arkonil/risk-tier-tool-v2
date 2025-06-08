import typing as t
from typing_extensions import TypeAlias

import streamlit as st

SpecType: TypeAlias = t.Union[int, t.Sequence[t.Union[int, float]]]


def columns_with_divider(
    spec: SpecType,
    *,
    gap: t.Literal["small", "medium", "large"] = "small",
    vertical_alignment: t.Literal["top", "center", "bottom"] = "top",
) -> t.List[st.delta_generator.DeltaGenerator]:
    return st.container(key="column-divider-container").columns(
        spec=spec, gap=gap, vertical_alignment=vertical_alignment
    )
