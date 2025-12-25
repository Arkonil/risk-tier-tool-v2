import typing as t

from pydantic import BaseModel, ConfigDict

from risc_tool.data.models.enums import LossRateTypes
from risc_tool.data.models.types import FilterID, MetricID


class IterationMetadata(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    editable: bool
    metric_ids: list[MetricID]
    scalars_enabled: bool
    split_view_enabled: bool
    loss_rate_type: LossRateTypes
    filter_ids: list[FilterID]
    show_prev_iter_details: bool

    @property
    def properties(self):
        return set(self.model_dump(mode="python").keys())


IterationMetadataKeys = t.Literal[
    "editable",
    "metric_ids",
    "scalars_enabled",
    "split_view_enabled",
    "loss_rate_type",
    "filter_ids",
    "show_prev_iter_details",
]

__all__ = [
    "IterationMetadata",
    "IterationMetadataKeys",
]
