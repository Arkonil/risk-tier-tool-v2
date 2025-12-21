import pathlib
import typing as t

from risc_tool.data.models.changes import ChangeTracker
from risc_tool.data.models.data_source import DataSource
from risc_tool.data.models.enums import Signature
from risc_tool.data.models.exceptions import DataImportError
from risc_tool.data.models.types import ChangeIDs, DataSourceID
from risc_tool.data.repositories.data import DataRepository


class ImportStatus(t.TypedDict):
    status: t.Literal["success", "error", "loading", "unset"]
    message: str


class DataSourceViewModel:
    def __init__(
        self,
        data_source: DataSource | None = None,
        import_status: ImportStatus | None = None,
    ):
        if data_source is None:
            data_source = DataSource(
                uid=DataSourceID.EMPTY,
                filepath=pathlib.Path("./data/test_data.csv"),
                label="New Data Source",
                read_mode="CSV",
                delimiter=",",
                sheet_name="0",
                header_row=0,
                sample_row_count=100,
            )

        if import_status is None:
            import_status = {"status": "unset", "message": ""}

        self.data_source: DataSource = data_source
        self.import_status: ImportStatus = import_status


class DataImporterViewModel(ChangeTracker):
    @property
    def _signature(self) -> Signature:
        return Signature.DATA_IMPORTER_VIEWMODEL

    def __init__(self, data_repository: DataRepository) -> None:
        super().__init__(dependencies=[data_repository])

        # Dependencies
        self.__data_repository: DataRepository = data_repository

        # File Importer States
        self.showing_empty_data_source = True
        self.empty_data_source_view = DataSourceViewModel()
        self.data_source_views: t.OrderedDict[DataSourceID, DataSourceViewModel] = (
            t.OrderedDict()
        )
        for ds_uid, ds in self.__data_repository.data_sources.items():
            self.data_source_views[ds_uid] = DataSourceViewModel(ds)

        # Data Preview
        self._current_ds_id: DataSourceID | None = None

    def on_dependency_update(self, change_ids: ChangeIDs) -> None:
        changed_dependencies = {sig for sig, _ in change_ids}

        if Signature.DATA_REPOSITORY in changed_dependencies:
            existing_ds_ids = set(self.__data_repository.data_sources.keys())
            removed_ds_ids = set(self.data_source_views.keys()) - existing_ds_ids

            for ds_id in existing_ds_ids:
                self.data_source_views[ds_id] = DataSourceViewModel(
                    self.__data_repository.data_sources[ds_id],
                    {
                        "status": "success",
                        "message": f"File imported successfully: {self.__data_repository.data_sources[ds_id].filepath}",
                    },
                )

            for ds_id in removed_ds_ids:
                del self.data_source_views[ds_id]

    @property
    def sample_loaded(self) -> bool:
        return self.__data_repository.sample_loaded

    def update_data_source(
        self,
        data_source_id: DataSourceID,
        filepath: pathlib.Path | None,
        label: str,
        read_mode: t.Literal["CSV", "EXCEL"],
        delimiter: str,
        sheet_name: str,
        header_row: int,
        sample_row_count: int,
    ):
        if (
            data_source_id not in self.data_source_views
            and data_source_id != DataSourceID.EMPTY
        ):
            return

        if data_source_id == DataSourceID.EMPTY:
            try:
                if filepath is None:
                    raise DataImportError("Filepath is required")

                new_data_source = self.__data_repository.add_data_source(
                    filepath=filepath,
                    label=label,
                    read_mode=read_mode,
                    delimiter=delimiter,
                    sheet_name=sheet_name,
                    header_row=header_row,
                    sample_row_count=sample_row_count,
                )
                self.showing_empty_data_source = False
                self.empty_data_source_view = DataSourceViewModel()
            except DataImportError as e:
                self.empty_data_source_view.data_source = (
                    self.empty_data_source_view.data_source.model_copy(
                        update={
                            "filepath": filepath or pathlib.Path(""),
                            "label": label,
                            "read_mode": read_mode,
                            "delimiter": delimiter,
                            "sheet_name": sheet_name,
                            "header_row": header_row,
                            "sample_row_count": sample_row_count,
                        }
                    )
                )
                self.empty_data_source_view.import_status = {
                    "status": "error",
                    "message": str(e),
                }

        else:
            try:
                new_data_source = self.__data_repository.update_data_source(
                    data_source_id=data_source_id,
                    filepath=filepath,
                    label=label,
                    read_mode=read_mode,
                    delimiter=delimiter,
                    sheet_name=sheet_name,
                    header_row=header_row,
                    sample_row_count=sample_row_count,
                )
                self._current_ds_id = new_data_source.uid
            except DataImportError as e:
                self.data_source_views[data_source_id].import_status = {
                    "status": "error",
                    "message": str(e),
                }
                self._current_ds_id = None

    def delete_data_source(self, data_source_id: DataSourceID):
        if data_source_id == DataSourceID.EMPTY:
            self.showing_empty_data_source = False
            self.empty_data_source_view = DataSourceViewModel()
            return

        if data_source_id not in self.data_source_views:
            return

        self.__data_repository.delete_data_source(data_source_id)

        if self._current_ds_id == data_source_id:
            self._current_ds_id = None

        if len(self.data_source_views) == 0:
            self.show_empty_data_source()
            self._current_ds_uid = None

    def show_empty_data_source(self):
        self.showing_empty_data_source = True
        self.empty_data_source_view = DataSourceViewModel()

    @property
    def current_ds_id(self) -> DataSourceID | None:
        if self._current_ds_id is not None:
            return self._current_ds_id

        for ds_uid, ds_vm in self.data_source_views.items():
            if ds_vm.import_status["status"] == "success":
                self._current_ds_id = ds_uid
                return ds_uid

        return None

    @current_ds_id.setter
    def current_ds_id(self, ds_uid: DataSourceID | None) -> None:
        if ds_uid is None:
            self._current_ds_id = None
            return

        if ds_uid not in self.data_source_views:
            return

        self._current_ds_id = ds_uid


__all__ = ["DataImporterViewModel"]
