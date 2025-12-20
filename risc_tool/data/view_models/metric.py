import typing as t

from risc_tool.data.models.changes import ChangeTracker
from risc_tool.data.models.metric import Metric
from risc_tool.data.models.types import ChangeIDs, DataSourceID, MetricID
from risc_tool.data.repositories.data import DataRepository
from risc_tool.data.repositories.metric import MetricRepository


def format_syntax_error(error: SyntaxError):
    error_msgs = [
        f"**SyntaxError**: {error.msg}",
        f"**Line**: {error.lineno}",
    ]

    if error.text:
        error_msgs.append(error.text.rstrip())

    if error.offset is not None and error.end_offset is not None:
        error_msgs.append(
            f"{' ' * (error.offset - 1)}{'^' * (error.end_offset - error.offset + 1)}"
        )

    return "\n\n".join(error_msgs)


def format_value_error(error: ValueError):
    return f"""
        **ValueError**: {error}
    """.replace("\n", "\n\n")


class MetricViewModel(ChangeTracker):
    def __init__(
        self, data_repository: DataRepository, metric_repository: MetricRepository
    ):
        super().__init__(dependencies=[data_repository, metric_repository])

        # Dependencies
        self.__data_repository = data_repository
        self.__metric_repository = metric_repository

        # Metric Editor States
        self.__view_mode: t.Literal["view", "edit"] = "view"
        self.__metric_cache = self.__empty_metric
        self._is_verified = False
        self.latest_editor_id = ""
        self.__errors: list[ValueError | SyntaxError] = []

    @property
    def __empty_metric(self):
        return Metric(uid=MetricID.EMPTY, name="", query="")

    def on_dependency_update(self, change_ids: ChangeIDs) -> None:
        self.__metric_cache = self.__empty_metric
        self._is_verified = False
        self.__errors.clear()

    @property
    def mode(self) -> t.Literal["view", "edit"]:
        return self.__view_mode

    def set_mode(
        self, mode: t.Literal["view", "edit"], metric_id: MetricID = MetricID.EMPTY
    ) -> None:
        self.__view_mode = mode
        self._is_verified = False
        self.__errors.clear()

        if mode == "edit":
            if metric_id == MetricID.EMPTY:
                self.__metric_cache = self.__empty_metric
            else:
                self.__metric_cache = self.__metric_repository.metrics.get(
                    metric_id, self.__empty_metric
                ).model_copy()
                self._is_verified = True

    # For Error View
    @property
    def sample_loaded(self) -> bool:
        return self.__data_repository.sample_loaded

    # For Editor
    @property
    def metric_cache(self):
        return self.__metric_cache

    def set_metric_property(
        self,
        *,
        name: str | None = None,
        query: str | None = None,
        use_thousand_sep: bool | None = None,
        is_percentage: bool | None = None,
        decimal_places: int | None = None,
    ):
        if name is not None:
            self.__metric_cache.name = name
            self._is_verified = False

        if query is not None:
            self.__metric_cache.query = query
            self._is_verified = False

        if use_thousand_sep is not None:
            self.__metric_cache.use_thousand_sep = use_thousand_sep

        if is_percentage is not None:
            self.__metric_cache.is_percentage = is_percentage

        if decimal_places is not None:
            self.__metric_cache.decimal_places = decimal_places

    @property
    def all_data_source_ids(self) -> list[DataSourceID]:
        return [ds_id for ds_id in self.__data_repository.data_sources]

    @property
    def selected_data_source_ids(self) -> list[DataSourceID]:
        return self.__metric_cache.data_source_ids

    @selected_data_source_ids.setter
    def selected_data_source_ids(self, value: list[DataSourceID]):
        self.__metric_cache.data_source_ids = value
        self._is_verified = False

    def get_data_source_label(self, data_source_id: DataSourceID):
        return self.__data_repository.data_sources[data_source_id].label

    def get_column_completions(self):
        data_source_ids = self.selected_data_source_ids
        available_columns = self.__data_repository.available_columns(data_source_ids)
        available_column_names = [col for col, _ in available_columns]
        completions = self.__data_repository.get_completions(
            columns=available_column_names
        )
        return [c.model_dump(mode="python") for c in completions]

    def validate_metric(self, name: str, query: str, latest_editor_id: str):
        if query == "":
            return

        if name == "":
            self.__errors.append(ValueError("Metric name cannot be empty"))
            self._is_verified = False
            return

        self.__errors.clear()

        try:
            current_id = self.__metric_cache.uid

            if current_id == MetricID.EMPTY:
                for metric in self.__metric_repository.metrics.values():
                    if name == metric.name:
                        raise ValueError("Metric name already exists")

            self.__metric_cache = self.__metric_repository.validate_metric(
                name=name,
                query=query,
                data_source_ids=self.__metric_cache.data_source_ids,
            )
            self.__metric_cache.uid = current_id
            self._is_verified = True
            self.latest_editor_id = latest_editor_id
        except (ValueError, SyntaxError) as e:
            self.__errors.append(e)
            self._is_verified = False

    def error_message(self) -> str:
        if not self.__errors:
            return ""

        messages: list[str] = []

        for error in self.__errors:
            if isinstance(error, ValueError):
                messages.append(format_value_error(error))
            elif isinstance(error, SyntaxError):
                messages.append(format_syntax_error(error))

        return "\n\n".join(messages)

    def save_metric(self):
        if not self._is_verified or self.__errors:
            raise RuntimeError("Metric is not verified")

        if self.__metric_cache.uid == MetricID.TEMPORARY:
            raise RuntimeError(
                f"MetricID should not be {MetricID.TEMPORARY}. This must a result of some fault in the logic"
            )

        if self.__metric_cache.uid == MetricID.EMPTY:
            self.__metric_repository.create_metric(
                name=self.__metric_cache.name,
                query=self.__metric_cache.query,
                use_thousand_sep=self.__metric_cache.use_thousand_sep,
                is_percentage=self.__metric_cache.is_percentage,
                decimal_places=self.__metric_cache.decimal_places,
                data_source_ids=self.__metric_cache.data_source_ids,
            )
        else:
            self.__metric_repository.modify_metric(
                metric_id=self.__metric_cache.uid,
                name=self.__metric_cache.name,
                query=self.__metric_cache.query,
                use_thousand_sep=self.__metric_cache.use_thousand_sep,
                is_percentage=self.__metric_cache.is_percentage,
                decimal_places=self.__metric_cache.decimal_places,
                data_source_ids=self.__metric_cache.data_source_ids,
            )

        self.set_mode("view")

    # For List View
    @property
    def metrics(self):
        return self.__metric_repository.metrics

    def duplicate_metric(self, metric_id: MetricID) -> None:
        self.__metric_repository.duplicate_metric(metric_id)

    def remove_metric(self, metric_id: MetricID) -> None:
        self.__metric_repository.remove_metric(metric_id)


__all__ = ["MetricViewModel"]
