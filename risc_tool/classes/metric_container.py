import typing as t

from classes.constants import DefaultMetrics
from classes.data import Data
from classes.metric import Metric
from classes.utils import create_duplicate_name


class MetricContainer:
    def __init__(self):
        self.metrics: dict[str, Metric] = {}
        self._verified_metrics: dict[str, Metric] = {}

        self._current_metric_view_mode: t.Literal["view", "edit"] = "view"
        self._current_metric_edit_name: str | None = None

    @property
    def mode(self) -> t.Literal["view", "edit"]:
        return self._current_metric_view_mode

    @property
    def current_metric_edit_name(self) -> str | None:
        return self._current_metric_edit_name

    def set_mode(
        self, mode: t.Literal["view", "edit"], metric_name: str = None
    ) -> None:
        self._current_metric_view_mode = mode
        self._current_metric_edit_name = metric_name

        if mode == "view":
            self._verified_metrics = {}

    def validate_metric(
        self,
        name: str,
        query: str,
        use_thousand_sep: bool,
        is_percentage: bool,
        decimal_places: int,
        data: Data,
    ) -> Metric:
        if name.strip() == "":
            raise ValueError("Metric name cannot be empty.")

        if name in DefaultMetrics:
            raise ValueError(f"Metric name '{name}' is reserved.")

        if name != self._current_metric_edit_name and name in self.metrics:
            raise ValueError(f"Metric name '{name}' already exists.")

        if query in self._verified_metrics:
            new_metric = self._verified_metrics[query]
            new_metric.name = name
            self._verified_metrics[query] = new_metric

            return new_metric

        new_metric = Metric(
            name=name,
            query=query,
            use_thousand_sep=use_thousand_sep,
            is_percentage=is_percentage,
            decimal_places=decimal_places,
        )

        # Validating query string
        new_metric.validate_query(data=data.sample_df)

        return new_metric

    def create_metric(
        self,
        name: str,
        query: str,
        use_thousand_sep: bool,
        is_percentage: bool,
        decimal_places: int,
        data: Data,
    ) -> None:
        new_metric = self.validate_metric(
            name,
            query,
            use_thousand_sep,
            is_percentage,
            decimal_places,
            data,
        )

        self.metrics[name] = new_metric

    def remove_metric(self, metric_name: str) -> None:
        if metric_name in self.metrics:
            del self.metrics[metric_name]

    def duplicate_metric(self, metric_name: str) -> None:
        metric_obj = self.metrics[metric_name].copy()

        existing_names = set(self.metrics.keys())
        metric_obj.name = create_duplicate_name(metric_obj.name, existing_names)

        self.metrics[metric_obj.name] = metric_obj

    def to_dict(self) -> dict[str, t.Any]:
        return {
            "metrics": {
                metric_name: metric_obj.to_dict()
                for metric_name, metric_obj in self.metrics.items()
            },
            "current_metric_view_mode": self._current_metric_view_mode,
            "current_metric_edit_name": self._current_metric_edit_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, t.Any]) -> "MetricContainer":
        instance = cls()

        if "metrics" in data:
            for metric_name, metric_data in data["metrics"].items():
                metric_obj = Metric.from_dict(metric_data)
                instance.metrics[metric_name] = metric_obj

        if "current_metric_view_mode" in data:
            instance._current_metric_view_mode = data["current_metric_view_mode"]

        if "current_metric_edit_name" in data:
            instance._current_metric_edit_name = data["current_metric_edit_name"]

        return instance
