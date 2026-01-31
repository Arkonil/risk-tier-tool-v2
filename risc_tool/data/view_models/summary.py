import typing as t
from uuid import UUID, uuid4

from risc_tool.data.models.changes import ChangeNotifier
from risc_tool.data.models.enums import Signature, SummaryPageTabName
from risc_tool.data.models.json_models import SummaryViewModelJSON
from risc_tool.data.models.types import ChangeIDs, FilterID, IterationID, MetricID
from risc_tool.data.repositories.data import DataRepository
from risc_tool.data.repositories.iterations import IterationsRepository


class SummaryViewModel(ChangeNotifier):
    @property
    def _signature(self) -> Signature:
        return Signature.SUMMARY_VIEW_MODEL

    def __init__(
        self,
        data_repository: DataRepository,
        iteration_repository: IterationsRepository,
    ):
        super().__init__()

        # Dependencies
        self.__data_repository: DataRepository = data_repository
        self.__iteration_repository: IterationsRepository = iteration_repository

        # Page State
        self.tab_names: list[SummaryPageTabName] = [
            SummaryPageTabName.OVERVIEW,
            SummaryPageTabName.COMPARISON,
            SummaryPageTabName.PIVOT,
        ]
        self.current_tab_name: SummaryPageTabName = self.tab_names[0]

        # Overview Tab Data
        self.ov_metric_ids: list[MetricID] = [
            MetricID.VOLUME,
            MetricID.DLR_BAD_RATE,
            MetricID.UNT_BAD_RATE,
        ]
        self.ov_filter_ids: list[FilterID] = []
        self.ov_scalars_enabled = True
        self.ov_selected_iteration_id: IterationID | None = None
        self.ov_selected_iteration_default: bool = False

        # Comparison Tab Data
        self.cv_metric_ids: list[MetricID] = [
            MetricID.VOLUME,
            MetricID.DLR_BAD_RATE,
            MetricID.UNT_BAD_RATE,
        ]
        self.cv_filter_ids: list[FilterID] = []
        self.cv_scalars_enabled = True
        self.cv_selected_iterations: dict[UUID, tuple[IterationID, bool]] = (
            t.OrderedDict()
        )
        self.cv_view_mode: t.Literal["grid", "list"] = "list"

    def to_dict(self) -> SummaryViewModelJSON:
        return SummaryViewModelJSON(
            ov_metric_ids=self.ov_metric_ids,
            ov_filter_ids=self.ov_filter_ids,
            ov_selected_iteration_id=self.ov_selected_iteration_id,
            ov_selected_iteration_default=self.ov_selected_iteration_default,
            cv_metric_ids=self.cv_metric_ids,
            cv_filter_ids=self.cv_filter_ids,
            cv_scalars_enabled=self.cv_scalars_enabled,
            cv_selected_iterations=self.cv_selected_iterations,
            cv_view_mode=self.cv_view_mode,
        )

    @classmethod
    def from_dict(
        cls,
        data: SummaryViewModelJSON,
        data_repository: DataRepository,
        iteration_repository: IterationsRepository,
    ) -> "SummaryViewModel":
        instance = cls(
            data_repository=data_repository,
            iteration_repository=iteration_repository,
        )
        instance.ov_metric_ids = data.ov_metric_ids
        instance.ov_filter_ids = data.ov_filter_ids
        instance.ov_selected_iteration_id = data.ov_selected_iteration_id
        instance.ov_selected_iteration_default = data.ov_selected_iteration_default
        instance.cv_metric_ids = data.cv_metric_ids
        instance.cv_filter_ids = data.cv_filter_ids
        instance.cv_scalars_enabled = data.cv_scalars_enabled
        instance.cv_selected_iterations = data.cv_selected_iterations
        instance.cv_view_mode = data.cv_view_mode

        return instance

    def on_dependency_update(self, change_ids: ChangeIDs) -> None:
        return

    # Data
    @property
    def sample_loaded(self) -> bool:
        return self.__data_repository.sample_loaded

    # Iterations
    @property
    def no_iteration(self) -> bool:
        return len(self.__iteration_repository.iterations) == 0

    # Overview Page
    def set_overview_metrics(self, metric_ids: list[MetricID]) -> None:
        self.ov_metric_ids = metric_ids

    # Comparison Page
    def set_comparison_metrics(self, metric_ids: list[MetricID]) -> None:
        self.cv_metric_ids = metric_ids

    def remove_iteration_view(self, view_idx: UUID):
        self.cv_selected_iterations.pop(view_idx, None)

    def add_iteration_view(self, iteration_id: IterationID, default: bool):
        self.cv_selected_iterations.setdefault(uuid4(), (iteration_id, default))

    def edit_iteration_view(
        self, view_idx: UUID, iteration_id: IterationID, default: bool
    ):
        self.cv_selected_iterations[view_idx] = (iteration_id, default)


__all__ = ["SummaryViewModel"]
