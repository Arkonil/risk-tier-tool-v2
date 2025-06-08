import typing as t

from classes.common import DEFAULT_METRICS_DF


class HomePageState:
    def __init__(self):
        self.scalars_enabled = True
        self.metrcis = DEFAULT_METRICS_DF.copy()
        self.comparison_mode = False
        self.selected_iterations = [None, None]
        self.comparison_view_mode: t.Literal["column", "row"] = "column"
