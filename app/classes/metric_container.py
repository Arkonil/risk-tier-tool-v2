import re
import typing as t

from classes.data import Data
from classes.metric import Metric
from classes.utils import integer_generator


__generator = integer_generator()


def new_id(current_ids: t.Iterable[str] = None) -> str:
    if current_ids is None:
        current_ids = []

    while True:
        new_id = str(next(__generator))
        if new_id not in current_ids:
            return new_id


class MetricContainer:
    def __init__(self):
        self.metrics: dict[str, Metric] = {}
        self._verified_metrics: dict[str, Metric] = {}

        self._current_metric_view_mode: t.Literal["view", "edit"] = "view"
        self._current_metric_edit_id: str | None = None

    @property
    def mode(self) -> t.Literal["view", "edit"]:
        return self._current_metric_view_mode

    @property
    def current_metric_edit_id(self) -> str | None:
        return self._current_metric_edit_id

    def set_mode(self, mode: t.Literal["view", "edit"], metric_id: str = None) -> None:
        self._current_metric_view_mode = mode
        self._current_metric_edit_id = metric_id

        if mode == "view":
            self._verified_metrics = {}

    def validate_metric(
        self,
        metric_id: str,
        name: str,
        query: str,
        data: Data,
    ) -> Metric:
        if name.strip() == "":
            raise ValueError("Metric name cannot be empty.")

        if name in [m.name for m in self.metrics.values() if m.id != metric_id]:
            raise ValueError(f"Metric name '{name}' already exists.")

        if query in self._verified_metrics:
            new_metric = self._verified_metrics[query]
            new_metric.id = metric_id
            new_metric.name = name
            self._verified_metrics[query] = new_metric

            return new_metric

        new_metric = Metric(id_=metric_id, name=name, query_string=query)

        # Validating query string
        new_metric.validate_query(data=data.sample_df)

        return new_metric

    def create_metric(
        self, metric_id: str | None, name: str, query: str, data: Data
    ) -> None:
        if metric_id is None:
            metric_id = new_id(current_ids=self.metrics.keys())

        new_metric = self.validate_metric(metric_id, name, query, data)

        self.metrics[metric_id] = new_metric

    def remove_metric(self, metric_id: str) -> None:
        if metric_id in self.metrics:
            del self.metrics[metric_id]

    def duplicate_metric(self, metric_id: str) -> None:
        metric_obj = self.metrics[metric_id].copy()
        metric_obj.id = new_id(current_ids=self.metrics.keys())

        if match := re.match(r"^(.*) - copy\((\d+)\)?$", metric_obj.name):
            metric_obj.name = f"{match.group(1)} - copy({int(match.group(2)) + 1})"
        elif metric_obj.name.endswith(" - copy"):
            metric_obj.name = f"{metric_obj.name}(2)"
        else:
            metric_obj.name = f"{metric_obj.name} - copy"

        self.metrics[metric_obj.id] = metric_obj

    def to_dict(self) -> dict[str, t.Any]:
        return {
            "metrics": {
                metric_id: metric_obj.to_dict()
                for metric_id, metric_obj in self.metrics.items()
            },
            "current_metric_view_mode": self._current_metric_view_mode,
            "current_metric_edit_id": self._current_metric_edit_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, t.Any]) -> "MetricContainer":
        instance = cls()

        if "metrics" in data:
            for metric_id, metric_data in data["metrics"].items():
                metric_obj = Metric.from_dict(metric_data)
                instance.metrics[metric_id] = metric_obj

        if "current_metric_view_mode" in data:
            instance._current_metric_view_mode = data["current_metric_view_mode"]

        if "current_metric_edit_id" in data:
            instance._current_metric_edit_id = data["current_metric_edit_id"]

        return instance
