import typing as t

import pandas as pd
from classes.constants import DefaultOptions


class SummaryPageState:
    def __init__(self):
        self.scalars_enabled = True
        self.metrics = DefaultOptions().default_metrics
        self.comparison_mode = False
        self.selected_iterations: list[tuple[str, bool]] = [
            (None, None),
            (None, None),
        ]
        self.comparison_view_mode: t.Literal["column", "row"] = "column"

    def to_dict(self) -> dict[str, t.Any]:
        """Serializes the HomePageState object to a dictionary."""

        return {
            "scalars_enabled": self.scalars_enabled,
            "metrics": self.metrics.to_dict(orient="tight"),
            "comparison_mode": self.comparison_mode,
            "selected_iterations": self.selected_iterations,
            "comparison_view_mode": self.comparison_view_mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, t.Any]) -> "SummaryPageState":
        """Creates a HomePageState object from a dictionary."""
        instance = cls()  # Initialize with default values

        instance.scalars_enabled = data.get("scalars_enabled", instance.scalars_enabled)
        instance.comparison_mode = data.get("comparison_mode", instance.comparison_mode)
        instance.selected_iterations = data.get(
            "selected_iterations", instance.selected_iterations
        )
        instance.comparison_view_mode = data.get(
            "comparison_view_mode", instance.comparison_view_mode
        )

        if "metrics" in data and data["metrics"] is not None:
            instance.metrics = pd.DataFrame.from_dict(data["metrics"], orient="tight")

        return instance
