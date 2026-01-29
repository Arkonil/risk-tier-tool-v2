from risc_tool.data.repositories.data import DataRepository
from risc_tool.data.repositories.filter import FilterRepository
from risc_tool.data.repositories.iterations import IterationsRepository
from risc_tool.data.repositories.metric import MetricRepository
from risc_tool.data.repositories.options import OptionRepository
from risc_tool.data.repositories.scalar import ScalarRepository
from risc_tool.data.view_models.config import ConfigViewModel
from risc_tool.data.view_models.data_explorer import DataExplorerViewModel
from risc_tool.data.view_models.data_importer import DataImporterViewModel
from risc_tool.data.view_models.export import ExportViewModel
from risc_tool.data.view_models.filter import FilterViewModel
from risc_tool.data.view_models.iterations import IterationsViewModel
from risc_tool.data.view_models.metric import MetricViewModel
from risc_tool.data.view_models.session_archive import SessionArchiveViewModel
from risc_tool.data.view_models.summary import SummaryViewModel
from risc_tool.data.view_models.variable_selector import VariableSelectorViewModel


class Session:
    def __init__(self, debug_mode: bool = False):
        self.reset()

        self.debug_mode = debug_mode

    def reset(self):
        # Repositories
        self.data_repository = DataRepository()
        self.options_repository = OptionRepository()
        self.scalar_repository = ScalarRepository()
        self.metric_repository = MetricRepository(self.data_repository)
        self.filter_repository = FilterRepository(self.data_repository)
        self.iterations_repository = IterationsRepository(
            data_repository=self.data_repository,
            filter_repository=self.filter_repository,
            metric_repository=self.metric_repository,
            options_repository=self.options_repository,
            scalar_repository=self.scalar_repository,
        )

        # View Models
        self.variable_selector_view_model = VariableSelectorViewModel(
            data_repository=self.data_repository,
            metric_repository=self.metric_repository,
        )
        self.data_importer_view_model = DataImporterViewModel(
            data_repository=self.data_repository,
        )
        self.data_explorer_view_model = DataExplorerViewModel(
            data_repository=self.data_repository,
            filter_repository=self.filter_repository,
        )
        self.metric_editor_view_model = MetricViewModel(
            data_repository=self.data_repository,
            metric_repository=self.metric_repository,
        )
        self.filter_editor_view_model = FilterViewModel(
            data_repository=self.data_repository,
            filter_repository=self.filter_repository,
        )
        self.config_view_model = ConfigViewModel(
            options_repository=self.options_repository,
            scalar_repository=self.scalar_repository,
            metric_repository=self.metric_repository,
        )
        self.iterations_view_model = IterationsViewModel(
            data_repository=self.data_repository,
            filter_repository=self.filter_repository,
            iterations_repository=self.iterations_repository,
            metric_repository=self.metric_repository,
            scalar_repository=self.scalar_repository,
            options_repository=self.options_repository,
        )
        self.summary_view_model = SummaryViewModel(
            data_repository=self.data_repository,
            iteration_repository=self.iterations_repository,
        )
        self.export_view_model = ExportViewModel(
            iteration_repository=self.iterations_repository,
        )

        # Import/Export
        self.session_archive_view_model = SessionArchiveViewModel(
            data_repository=self.data_repository,
            filter_repository=self.filter_repository,
            metric_repository=self.metric_repository,
            options_repository=self.options_repository,
            scalar_repository=self.scalar_repository,
            iterations_repository=self.iterations_repository,
            iterations_view_model=self.iterations_view_model,
            summary_view_model=self.summary_view_model,
        )

    def dangerously_set_repo_vm(
        self,
        data_repository: DataRepository,
        options_repository: OptionRepository,
        scalar_repository: ScalarRepository,
        metric_repository: MetricRepository,
        filter_repository: FilterRepository,
        iterations_repository: IterationsRepository,
        iterations_view_model: IterationsViewModel,
        summary_view_model: SummaryViewModel,
    ):
        self.data_repository = data_repository
        self.options_repository = options_repository
        self.scalar_repository = scalar_repository
        self.metric_repository = metric_repository
        self.filter_repository = filter_repository
        self.iterations_repository = iterations_repository

        self.variable_selector_view_model = VariableSelectorViewModel(
            data_repository=self.data_repository,
            metric_repository=self.metric_repository,
        )
        self.data_importer_view_model = DataImporterViewModel(
            data_repository=self.data_repository,
        )
        self.data_importer_view_model.showing_empty_data_source = False
        if data_repository.data_sources:
            self.data_importer_view_model._current_ds_id = next(
                iter(data_repository.data_sources)
            )

        self.data_explorer_view_model = DataExplorerViewModel(
            data_repository=self.data_repository,
            filter_repository=self.filter_repository,
        )
        self.metric_editor_view_model = MetricViewModel(
            data_repository=self.data_repository,
            metric_repository=self.metric_repository,
        )
        self.filter_editor_view_model = FilterViewModel(
            data_repository=self.data_repository,
            filter_repository=self.filter_repository,
        )
        self.config_view_model = ConfigViewModel(
            options_repository=self.options_repository,
            scalar_repository=self.scalar_repository,
            metric_repository=self.metric_repository,
        )
        self.iterations_view_model = iterations_view_model
        self.summary_view_model = summary_view_model
        self.export_view_model = ExportViewModel(
            iteration_repository=self.iterations_repository,
        )
        self.session_archive_view_model = SessionArchiveViewModel(
            data_repository=self.data_repository,
            filter_repository=self.filter_repository,
            metric_repository=self.metric_repository,
            options_repository=self.options_repository,
            scalar_repository=self.scalar_repository,
            iterations_repository=self.iterations_repository,
            iterations_view_model=self.iterations_view_model,
            summary_view_model=self.summary_view_model,
        )


__all__ = ["Session"]
