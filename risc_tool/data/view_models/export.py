from risc_tool.data.models.changes import ChangeTracker
from risc_tool.data.models.enums import ExportTabName, Signature
from risc_tool.data.models.types import ChangeIDs, IterationID
from risc_tool.data.repositories.iterations import IterationsRepository


class ExportViewModel(ChangeTracker):
    @property
    def _signature(self) -> Signature:
        return Signature.EXPORT_VIEW_MODEL

    def __init__(
        self,
        iteration_repository: IterationsRepository,
    ):
        super().__init__(dependencies=[iteration_repository])

        self.__iteration_repository = iteration_repository

        self.tab_names: list[ExportTabName] = [
            ExportTabName.SESSION_ARCHIVE,
            ExportTabName.PYTHON_CODE,
            ExportTabName.SAS_CODE,
        ]
        self.current_tab_name = self.tab_names[0]

    def on_dependency_update(self, change_ids: ChangeIDs) -> None:
        pass

    @property
    def no_iteration(self):
        return len(self.__iteration_repository.iterations) == 0

    def get_python_code(self, iteration_id: IterationID, default: bool):
        return self.__iteration_repository.get_python_code(iteration_id, default)

    def get_sas_code(self, iteration_id: IterationID, default: bool, use_macro: bool):
        return self.__iteration_repository.get_sas_code(
            iteration_id, default, use_macro
        )


__all__ = ["ExportViewModel"]
