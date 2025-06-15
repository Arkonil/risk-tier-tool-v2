import typing as t

from classes.constants import DefaultOptions


class HomePageState:
    def __init__(self):
        self.scalars_enabled = True
        self.metrics = DefaultOptions().default_metrics
        self.comparison_mode = False
        self.selected_iterations: list[tuple[str, bool]] = [
            [None, None],
            [None, None],
        ]
        self.comparison_view_mode: t.Literal["column", "row"] = "column"
