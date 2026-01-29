import typing as t

from streamlit.runtime.uploaded_file_manager import UploadedFile

from risc_tool.data.models.changes import ChangeTracker
from risc_tool.data.models.data_source import DataSource
from risc_tool.data.models.enums import Signature
from risc_tool.data.models.json_models import (
    DataSourceJSON,
    SessionArchiveRepositoryJSON,
)
from risc_tool.data.models.types import ChangeIDs, DataSourceID
from risc_tool.data.repositories.data import DataRepository
from risc_tool.data.repositories.filter import FilterRepository
from risc_tool.data.repositories.iterations import IterationsRepository
from risc_tool.data.repositories.metric import MetricRepository
from risc_tool.data.repositories.options import OptionRepository
from risc_tool.data.repositories.scalar import ScalarRepository
from risc_tool.data.view_models.iterations import IterationsViewModel
from risc_tool.data.view_models.summary import SummaryViewModel


class NewRepoVMs(t.TypedDict):
    data_repository: DataRepository
    filter_repository: FilterRepository
    metric_repository: MetricRepository
    options_repository: OptionRepository
    scalar_repository: ScalarRepository
    iterations_repository: IterationsRepository
    iterations_view_model: IterationsViewModel
    summary_view_model: SummaryViewModel


class SessionArchiveViewModel(ChangeTracker):
    @property
    def _signature(self) -> Signature:
        return Signature.SESSION_ARCHIVE_VIEWMODEL

    def __init__(
        self,
        data_repository: DataRepository,
        filter_repository: FilterRepository,
        metric_repository: MetricRepository,
        options_repository: OptionRepository,
        scalar_repository: ScalarRepository,
        iterations_repository: IterationsRepository,
        iterations_view_model: IterationsViewModel,
        summary_view_model: SummaryViewModel,
    ):
        super().__init__()

        self.home_page_view: t.Literal["welcome", "import-json"] = "welcome"
        self.uploaded_file: UploadedFile | None = None
        self.validated_json: SessionArchiveRepositoryJSON | None = None
        self.data_source_correction: dict[DataSourceID, DataSource] = {}

        self.__data_repository = data_repository
        self.__filter_repository = filter_repository
        self.__metric_repository = metric_repository
        self.__options_repository = options_repository
        self.__scalar_repository = scalar_repository
        self.__iterations_repository = iterations_repository
        self.__iterations_view_model = iterations_view_model
        self.__summary_view_model = summary_view_model

    def create_dict(self) -> SessionArchiveRepositoryJSON:
        return SessionArchiveRepositoryJSON(
            data_repository=self.__data_repository.to_dict(),
            filter_repository=self.__filter_repository.to_dict(),
            metric_repository=self.__metric_repository.to_dict(),
            scalar_repository=self.__scalar_repository.to_dict(),
            options_repository=self.__options_repository.to_dict(),
            iteration_repository=self.__iterations_repository.to_dict(),
            iterations_view_model=self.__iterations_view_model.to_dict(),
            summary_view_model=self.__summary_view_model.to_dict(),
        )

    def from_dict(self, data: SessionArchiveRepositoryJSON) -> NewRepoVMs:
        data_repo_json = data.data_repository

        data_source_jsons: list[DataSourceJSON] = []

        for ds_json in data_repo_json.data_sources:
            uid = DataSourceID(ds_json.uid)

            if uid in self.data_source_correction:
                data_source_jsons.append(self.data_source_correction[uid].to_dict())
            else:
                data_source_jsons.append(ds_json)

        data_repo_json = data_repo_json.model_copy(
            update={"data_sources": data_source_jsons}
        )

        data_repository = DataRepository.from_dict(data_repo_json)
        options_repository = OptionRepository.from_dict(data.options_repository)
        scalar_repository = ScalarRepository.from_dict(data.scalar_repository)
        metric_repository, _ = MetricRepository.from_dict(
            data.metric_repository, data_repository, errors="ignore"
        )
        filter_repository, _ = FilterRepository.from_dict(
            data.filter_repository, data_repository, errors="ignore"
        )
        iterations_repository, _ = IterationsRepository.from_dict(
            data.iteration_repository,
            data_repository,
            filter_repository,
            metric_repository,
            options_repository,
            scalar_repository,
            errors="ignore",
        )

        iteration_view_model = IterationsViewModel.from_dict(
            data.iterations_view_model,
            data_repository,
            iterations_repository,
            options_repository,
            filter_repository,
            metric_repository,
            scalar_repository,
        )

        summary_view_model = SummaryViewModel.from_dict(
            data.summary_view_model,
            data_repository,
            iterations_repository,
        )

        return {
            "data_repository": data_repository,
            "filter_repository": filter_repository,
            "metric_repository": metric_repository,
            "scalar_repository": scalar_repository,
            "options_repository": options_repository,
            "iterations_repository": iterations_repository,
            "iterations_view_model": iteration_view_model,
            "summary_view_model": summary_view_model,
        }

    def on_dependency_update(self, change_ids: ChangeIDs) -> None:
        return

    def set_home_page_view(self, view: t.Literal["welcome", "import-json"]):
        self.home_page_view = view

        if view == "welcome":
            self.clear_uploaded_file()

    def clear_uploaded_file(self):
        self.uploaded_file = None
        self.validated_json = None
        self.data_source_correction = {}

    def validate_json(self, json_str: str) -> SessionArchiveRepositoryJSON:
        if self.validated_json is None:
            self.validated_json = SessionArchiveRepositoryJSON.model_validate_json(
                json_str
            )

        return self.validated_json

    def validate_data_sources(self, data: SessionArchiveRepositoryJSON):
        ds_edit_list: list[tuple[DataSource, DataSource | None, Exception | None]] = []

        for data_source_json in data.data_repository.data_sources:
            ds = DataSource.from_dict(data_source_json)

            if ds.uid in self.data_source_correction:
                ds_edit_list.append((ds, self.data_source_correction[ds.uid], None))
                continue

            try:
                ds.validate_read_config()

            except Exception as error:
                ds_edit_list.append((ds, None, error))

        return ds_edit_list

    def validate_data_source(self, data_source: DataSource):
        try:
            data_source.validate_read_config()
        except Exception:
            if data_source.uid in self.data_source_correction:
                self.data_source_correction.pop(data_source.uid)
        else:
            self.data_source_correction[data_source.uid] = data_source

    def validate_columns(self, data: SessionArchiveRepositoryJSON):
        data_repo_json = data.data_repository

        data_source_jsons: list[DataSourceJSON] = []

        for ds_json in data_repo_json.data_sources:
            uid = DataSourceID(ds_json.uid)

            if uid in self.data_source_correction:
                data_source_jsons.append(self.data_source_correction[uid].to_dict())
            else:
                data_source_jsons.append(ds_json)

        data_repo_json = data_repo_json.model_copy(
            update={"data_sources": data_source_jsons}
        )

        data_repository = DataRepository.from_dict(data_repo_json)

        # Filters
        filter_repository, invalid_filters = FilterRepository.from_dict(
            data.filter_repository,
            data_repository=data_repository,
            errors="raise",
        )

        # Metrics
        metric_repository, invalid_metrics = MetricRepository.from_dict(
            data.metric_repository,
            data_repository=data_repository,
            errors="raise",
        )

        # Scalars
        scalar_repository = ScalarRepository.from_dict(data.scalar_repository)

        # Options
        options_repository = OptionRepository.from_dict(data.options_repository)

        # Iterations
        _, invalid_iterations = IterationsRepository.from_dict(
            data.iteration_repository,
            data_repository=data_repository,
            filter_repository=filter_repository,
            metric_repository=metric_repository,
            options_repository=options_repository,
            scalar_repository=scalar_repository,
            errors="raise",
        )

        return invalid_filters, invalid_metrics, invalid_iterations


__all__ = ["SessionArchiveViewModel"]
