from risc_tool.data.repositories.data import DataRepository
from risc_tool.data.repositories.filter import FilterRepository
from risc_tool.data.repositories.metric import MetricRepository
from risc_tool.data.view_models.data_explorer import DataExplorerViewModel
from risc_tool.data.view_models.data_importer import DataImporterViewModel
from risc_tool.data.view_models.filter import FilterViewModel
from risc_tool.data.view_models.metric import MetricViewModel
from risc_tool.data.view_models.variable_selector import VariableSelectorViewModel


class Session:
    def __init__(self, debug_mode: bool = False):
        self.reset()

        self.debug_mode = debug_mode

    def reset(self):
        self.data_repository = DataRepository()
        self.metric_repository = MetricRepository(self.data_repository)
        self.filter_repository = FilterRepository(self.data_repository)

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


__all__ = ["Session"]
