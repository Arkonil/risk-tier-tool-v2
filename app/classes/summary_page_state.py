import typing as t

from classes.constants import DefaultOptions


class SummaryPageState:
    def __init__(self):
        self.current_page_index: int = 0

        # Overview Page Data
        self.ov_metrics = DefaultOptions().default_metrics
        self.ov_scalars_enabled = True
        self.ov_filters: set[str] = set()
        self.ov_selected_iteration_id: str = None
        self.ov_selected_iteration_default: bool = None

        # Comparison Page Data
        self.cv_metrics = DefaultOptions().default_metrics
        self.cv_scalars_enabled = True
        self.cv_filters: set[str] = set()
        self.cv_selected_iterations: list[tuple[str, bool]] = [
            (None, None),
            (None, None),
        ]
        self.cv_view_mode: t.Literal["column", "row"] = "column"

        # Crosstab Page Data

    def to_dict(self) -> dict[str, t.Any]:
        """Serializes the HomePageState object to a dictionary."""

        return {
            "current_page_index": self.current_page_index,
            "ov_metrics": self.ov_metrics,
            "ov_scalars_enabled": self.ov_scalars_enabled,
            "ov_filters": list(self.ov_filters),
            "ov_selected_iteration_id": self.ov_selected_iteration_id,
            "ov_selected_iteration_default": self.ov_selected_iteration_default,
            "cv_metrics": self.cv_metrics,
            "cv_scalars_enabled": self.cv_scalars_enabled,
            "cv_filters": list(self.cv_filters),
            "cv_selected_iterations": self.cv_selected_iterations,
            "cv_view_mode": self.cv_view_mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, t.Any]) -> "SummaryPageState":
        """Creates a SummaryPageState object from a dictionary."""
        # Initialize with default values
        instance = cls()

        # Overview Page Data
        instance.current_page_index = data.get("current_page_index", 0)
        instance.ov_metrics = data.get("ov_metrics", DefaultOptions().default_metrics)
        instance.ov_scalars_enabled = data.get("ov_scalars_enabled", True)
        instance.ov_filters = set(data.get("ov_filters", []))
        instance.ov_selected_iteration_id = data.get("ov_selected_iteration_id", None)
        instance.ov_selected_iteration_default = data.get(
            "ov_selected_iteration_default", None
        )

        # Comparison Page Data
        instance.cv_metrics = data.get("cv_metrics", DefaultOptions().default_metrics)
        instance.cv_scalars_enabled = data.get("cv_scalars_enabled", True)
        instance.cv_filters = set(data.get("cv_filters", []))
        instance.cv_selected_iterations = data.get(
            "cv_selected_iterations",
            [
                (None, None),
                (None, None),
            ],
        )
        instance.cv_view_mode = data.get("cv_view_mode", "column")

        return instance
