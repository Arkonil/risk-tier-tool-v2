from pydantic import BaseModel, ConfigDict

from risc_tool.data.models.enums import LossRateTypes
from risc_tool.data.models.types import FilterID, MetricID


class IterationMetadata(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    editable: bool
    scalars_enabled: bool
    split_view_enabled: bool
    show_prev_iter_details: bool
    loss_rate_type: LossRateTypes
    initial_filter_ids: list[FilterID]
    current_filter_ids: list[FilterID]
    metric_ids: list[MetricID]

    @property
    def properties(self):
        return set(self.model_dump(mode="python").keys())

    def update(
        self,
        editable: bool | None = None,
        scalars_enabled: bool | None = None,
        split_view_enabled: bool | None = None,
        show_prev_iter_details: bool | None = None,
        loss_rate_type: LossRateTypes | None = None,
        initial_filter_ids: list[FilterID] | None = None,
        current_filter_ids: list[FilterID] | None = None,
        metric_ids: list[MetricID] | None = None,
    ) -> None:
        if editable is not None:
            self.editable = editable

        if metric_ids is not None:
            self.metric_ids = metric_ids

        if scalars_enabled is not None:
            self.scalars_enabled = scalars_enabled

        if split_view_enabled is not None:
            self.split_view_enabled = split_view_enabled

        if loss_rate_type is not None:
            self.loss_rate_type = loss_rate_type

        if initial_filter_ids is not None:
            self.initial_filter_ids = initial_filter_ids

        if current_filter_ids is not None:
            self.current_filter_ids = current_filter_ids

        if show_prev_iter_details is not None:
            self.show_prev_iter_details = show_prev_iter_details

    def with_changes(
        self,
        editable: bool | None = None,
        scalars_enabled: bool | None = None,
        split_view_enabled: bool | None = None,
        show_prev_iter_details: bool | None = None,
        loss_rate_type: LossRateTypes | None = None,
        initial_filter_ids: list[FilterID] | None = None,
        current_filter_ids: list[FilterID] | None = None,
        metric_ids: list[MetricID] | None = None,
    ):
        if editable is None:
            editable = self.editable

        if metric_ids is None:
            metric_ids = self.metric_ids.copy()

        if scalars_enabled is None:
            scalars_enabled = self.scalars_enabled

        if split_view_enabled is None:
            split_view_enabled = self.split_view_enabled

        if loss_rate_type is None:
            loss_rate_type = self.loss_rate_type

        if initial_filter_ids is None:
            initial_filter_ids = self.initial_filter_ids.copy()

        if current_filter_ids is None:
            current_filter_ids = self.current_filter_ids.copy()

        if show_prev_iter_details is None:
            show_prev_iter_details = self.show_prev_iter_details

        return IterationMetadata(
            editable=editable,
            scalars_enabled=scalars_enabled,
            split_view_enabled=split_view_enabled,
            show_prev_iter_details=show_prev_iter_details,
            loss_rate_type=loss_rate_type,
            initial_filter_ids=initial_filter_ids,
            current_filter_ids=current_filter_ids,
            metric_ids=metric_ids,
        )


__all__ = ["IterationMetadata"]
