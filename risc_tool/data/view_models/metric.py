import typing as t

from risc_tool.data.models.changes import ChangeTracker
from risc_tool.data.models.metric import Metric
from risc_tool.data.models.types import ChangeIDs, DataSourceID, MetricID
from risc_tool.data.repositories.data import DataRepository
from risc_tool.data.repositories.metric import MetricRepository


class MetricViewModel(ChangeTracker):
    def __init__(
        self, data_repository: DataRepository, metric_repository: MetricRepository
    ):
        super().__init__(dependencies=[data_repository, metric_repository])

        # Dependencies
        self.__data_repository = data_repository
        self.__metric_repository = metric_repository

        # Metric Editor States
        self.__current_metric_view_mode: t.Literal["view", "edit"] = "view"
        self.__metric_cache = self.__empty_metric
        self.is_verified = False
        self.__errors: list[ValueError | SyntaxError] = []

    @property
    def __empty_metric(self):
        return Metric(uid=MetricID.EMPTY, name="", query="")

    def on_dependency_update(self, change_ids: ChangeIDs) -> None:
        self.__metric_cache = self.__empty_metric
        self.is_verified = False
        self.__errors.clear()

    @property
    def mode(self) -> t.Literal["view", "edit"]:
        return self.__current_metric_view_mode

    def set_mode(
        self, mode: t.Literal["view", "edit"], metric_id: MetricID = MetricID.EMPTY
    ) -> None:
        self.__current_metric_view_mode = mode
        self.is_verified = False
        self.__errors.clear()

        if mode == "edit":
            if metric_id == MetricID.EMPTY:
                self.__metric_cache = self.__empty_metric
            else:
                self.__metric_cache = self.__metric_repository.metrics.get(
                    metric_id, self.__empty_metric
                ).model_copy()
                self.is_verified = True

    # For Error View
    @property
    def sample_loaded(self) -> bool:
        return self.__data_repository.sample_loaded

    # For Editor
    @property
    def metric_cache(self):
        return self.__metric_cache

    @property
    def all_data_source_ids(self) -> list[DataSourceID]:
        return [ds_id for ds_id in self.__data_repository.data_sources]

    @property
    def selected_data_source_ids(self) -> list[DataSourceID]:
        return self.__metric_cache.valid_data_source_ids

    @selected_data_source_ids.setter
    def selected_data_source_ids(self, value: list[DataSourceID]):
        self.__metric_cache.valid_data_source_ids = value
        self.is_verified = False

    def get_data_source_label(self, data_source_id: DataSourceID):
        return self.__data_repository.data_sources[data_source_id].label

    def set_name(self, name: str):
        self.__metric_cache.name = name
        self.is_verified = False

    def get_column_completions(self):
        data_source_ids = self.selected_data_source_ids
        available_columns = self.__data_repository.available_columns(data_source_ids)
        available_column_names = [col for col, _ in available_columns]
        completions = self.__data_repository.get_completions(
            columns=available_column_names
        )
        return [c.model_dump(mode="python") for c in completions]

    def set_query(self, query: str):
        self.__metric_cache.query = query
        self.is_verified = False

    def validate_metric(self):
        self.__errors.clear()

        try:
            self.__metric_repository.validate_metric(
                name=self.__metric_cache.name,
                query=self.__metric_cache.query,
                data_source_ids=self.__metric_cache.valid_data_source_ids,
            )
            self.is_verified = True
        except (ValueError, SyntaxError) as e:
            self.__errors.append(e)
            self.is_verified = False

    def error_message(self) -> str:
        if not self.__errors:
            return ""

        messages: list[str] = []

        for error in self.__errors:
            if isinstance(error, ValueError):
                messages.append(
                    f"""
                    **ValueError**: {error}
                """.replace("\n", "\n\n")
                )
            elif isinstance(error, SyntaxError):
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
                messages.extend(error_msgs)

        return "\n\n".join(messages)

    def save_metric(self):
        self.validate_metric()

        if not self.__errors:
            self.__metric_repository.create_metric(
                name=self.__metric_cache.name,
                query=self.__metric_cache.query,
                use_thousand_sep=self.__metric_cache.use_thousand_sep,
                is_percentage=self.__metric_cache.is_percentage,
                decimal_places=self.__metric_cache.decimal_places,
                data_source_ids=self.__metric_cache.valid_data_source_ids,
            )

            self.set_mode("view")

    @property
    def metrics(self):
        return self.__metric_repository.metrics

    def duplicate_metric(self, metric_id: MetricID) -> None:
        self.__metric_repository.duplicate_metric(metric_id)

    def remove_metric(self, metric_id: MetricID) -> None:
        self.__metric_repository.remove_metric(metric_id)


__all__ = ["MetricViewModel"]
