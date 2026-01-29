import typing as t

import pandas as pd

from risc_tool.data.models.enums import DefaultMetricNames, Signature, VariableType
from risc_tool.data.models.exceptions import MissingColumnError, VariableNotNumericError
from risc_tool.data.models.json_models import MetricRepositoryJSON
from risc_tool.data.models.metric import (
    DefaultDollarBadRate,
    DefaultUnitBadRate,
    DefaultVolume,
    DollarBadRate,
    Metric,
    UnitBadRate,
    Volume,
)
from risc_tool.data.models.types import ChangeIDs, DataSourceID, MetricID
from risc_tool.data.repositories.base import BaseRepository
from risc_tool.data.repositories.data import (
    DataRepository,
    SampleDataNotLoadedError,
)
from risc_tool.utils.duplicate_name import create_duplicate_name


class MetricRepository(BaseRepository):
    @property
    def _signature(self) -> Signature:
        return Signature.METRIC_REPOSITORY

    def __init__(self, data_repository: DataRepository) -> None:
        super().__init__(dependencies=[data_repository])

        # User defined metrics
        self.metrics: dict[MetricID, Metric] = {}

        # Default metrics
        self._var_unt_bad: str | None = None
        self._var_dlr_bad: str | None = None
        self._var_avg_bal: str | None = None
        self._current_rate_mob: int = 12
        self._lifetime_rate_mob: int = 36
        self._data_source_ids: list[DataSourceID] = []

        # Cache
        self.__verified_metrics: dict[tuple[str, tuple[DataSourceID, ...]], Metric] = {}
        self.__unit_bad_rate_metric_cache: dict[
            tuple[str, int, tuple[DataSourceID, ...]], Metric
        ] = {}
        self.__dollar_bad_rate_metric_cache: dict[
            tuple[str, str, int, tuple[DataSourceID, ...]], Metric
        ] = {}
        self.__volume_metric_cache: Metric | None = None

        # Dependencies
        self.__data_repository: DataRepository = data_repository

    def _update_user_defined_metrics(self):
        metric_ids_to_remove: list[MetricID] = []

        for metric_id, metric in self.metrics.items():
            valid_data_source_ids: list[DataSourceID] = []

            for ds_id in self.__data_repository.data_sources:
                if ds_id not in metric.data_source_ids:
                    continue

                try:
                    metric.validate_query(self.__data_repository.get_sample_df([ds_id]))
                except (SyntaxError, ValueError, SampleDataNotLoadedError):
                    pass
                else:
                    valid_data_source_ids.append(ds_id)

            if valid_data_source_ids:
                metric.data_source_ids = valid_data_source_ids
            else:
                metric_ids_to_remove.append(metric_id)

        for metric_id in metric_ids_to_remove:
            del self.metrics[metric_id]

    def _update_default_metrics(self):
        if not self.__data_repository.sample_loaded:
            self._var_unt_bad = None
            self._var_dlr_bad = None
            self._var_avg_bal = None
            self._data_source_ids = []
            return

        self._data_source_ids = list(
            set(self.__data_repository.data_sources.keys()) & set(self._data_source_ids)
        )

        sample_df = self.__data_repository.get_sample_df(self._data_source_ids)
        common_columns = self.__data_repository.available_columns(self._data_source_ids)
        common_column_names = [col for col, _ in common_columns]

        if (
            self._var_unt_bad not in common_column_names
            or not pd.api.types.is_numeric_dtype(sample_df[self._var_unt_bad])
        ):
            self._var_unt_bad = None

        if (
            self._var_dlr_bad not in common_column_names
            or not pd.api.types.is_numeric_dtype(sample_df[self._var_dlr_bad])
        ):
            self._var_dlr_bad = None

        if (
            self._var_avg_bal not in common_column_names
            or not pd.api.types.is_numeric_dtype(sample_df[self._var_avg_bal])
        ):
            self._var_avg_bal = None

    def _clear_cache(self):
        self.__verified_metrics.clear()
        self.__unit_bad_rate_metric_cache.clear()
        self.__dollar_bad_rate_metric_cache.clear()
        self.__volume_metric_cache = None

    def on_dependency_update(self, change_ids: ChangeIDs):
        # Update use defined metrics
        self._update_user_defined_metrics()

        # Update default metrics
        self._update_default_metrics()

        # clear cache
        self._clear_cache()

    def validate_metric_input_column(self, column_name: str):
        available_columns = self.__data_repository.available_columns(
            self.data_source_ids
        )

        if (column_name, VariableType.CATEGORICAL) in available_columns:
            raise VariableNotNumericError(
                column_name,
                str(
                    self.__data_repository.data_sources[self.data_source_ids[0]]
                    .load_columns([column_name], [VariableType.CATEGORICAL])
                    .iloc[:, 0]
                    .dtypes
                ),
            )

        if (column_name, VariableType.NUMERICAL) not in available_columns:
            raise MissingColumnError(column_name)

    @property
    def var_unt_bad(self) -> str | None:
        return self._var_unt_bad

    @var_unt_bad.setter
    def var_unt_bad(self, value: str | None):
        if value is None:
            self._var_unt_bad = None
            return

        self.validate_metric_input_column(value)

        self._var_unt_bad = value

        self.notify_subscribers()

    @property
    def var_dlr_bad(self) -> str | None:
        return self._var_dlr_bad

    @var_dlr_bad.setter
    def var_dlr_bad(self, value: str | None):
        if value is None:
            self._var_dlr_bad = None
            return

        self.validate_metric_input_column(value)

        self._var_dlr_bad = value

        self.notify_subscribers()

    @property
    def var_avg_bal(self) -> str | None:
        return self._var_avg_bal

    @var_avg_bal.setter
    def var_avg_bal(self, value: str | None):
        if value is None:
            self._var_avg_bal = None
            return

        self.validate_metric_input_column(value)

        self._var_avg_bal = value

        self.notify_subscribers()

    @property
    def current_rate_mob(self) -> int:
        return self._current_rate_mob

    @current_rate_mob.setter
    def current_rate_mob(self, value: int):
        if value <= 0:
            raise ValueError("Current rate MOB must be a positive integer.")

        self._current_rate_mob = value

        self.notify_subscribers()

    @property
    def lifetime_rate_mob(self) -> int:
        return self._lifetime_rate_mob

    @lifetime_rate_mob.setter
    def lifetime_rate_mob(self, value: int):
        if value <= 0:
            raise ValueError("Lifetime rate MOB must be a positive integer.")

        self._lifetime_rate_mob = value

        self.notify_subscribers()

    @property
    def data_source_ids(self) -> list[DataSourceID]:
        return self._data_source_ids

    @data_source_ids.setter
    def data_source_ids(self, value: list[DataSourceID]):
        self._data_source_ids = value

        # Update use defined metrics
        self._update_user_defined_metrics()

        # Update default metrics
        self._update_default_metrics()

        # clear cache
        self._clear_cache()

        self.notify_subscribers()

    @property
    def unit_bad_rate(self) -> Metric:
        if self.var_unt_bad is None:
            return DefaultUnitBadRate(list(self.__data_repository.data_sources.keys()))

        if not self.__data_repository.sample_loaded:
            raise SampleDataNotLoadedError()

        key = (
            self.var_unt_bad,
            self.current_rate_mob,
            tuple(sorted(self.data_source_ids)),
        )

        if key in self.__unit_bad_rate_metric_cache:
            return self.__unit_bad_rate_metric_cache[key]

        sample_df = self.__data_repository.get_sample_df(self.data_source_ids)

        if sample_df.empty:
            return DefaultUnitBadRate(list(self.__data_repository.data_sources.keys()))

        metric = UnitBadRate(
            self.var_unt_bad, self.current_rate_mob, self.data_source_ids
        )
        metric.validate_query(sample_df)

        self.__unit_bad_rate_metric_cache[key] = metric
        return metric

    @property
    def dollar_bad_rate(self) -> Metric:
        if self.var_dlr_bad is None or self.var_avg_bal is None:
            return DefaultDollarBadRate(
                list(self.__data_repository.data_sources.keys())
            )

        if not self.__data_repository.sample_loaded:
            raise SampleDataNotLoadedError()

        key = (
            self.var_dlr_bad,
            self.var_avg_bal,
            self.current_rate_mob,
            tuple(sorted(self.data_source_ids)),
        )

        if key in self.__dollar_bad_rate_metric_cache:
            return self.__dollar_bad_rate_metric_cache[key]

        sample_df = self.__data_repository.get_sample_df(self.data_source_ids)
        if sample_df.empty:
            return DefaultDollarBadRate(
                list(self.__data_repository.data_sources.keys())
            )

        metric = DollarBadRate(
            self.var_dlr_bad,
            self.var_avg_bal,
            self.current_rate_mob,
            self.data_source_ids,
        )
        metric.validate_query(sample_df)

        self.__dollar_bad_rate_metric_cache[key] = metric
        return metric

    @property
    def volume(self) -> Metric:
        if self.__volume_metric_cache is not None:
            return self.__volume_metric_cache

        if not self.__data_repository.sample_loaded:
            raise SampleDataNotLoadedError()

        sample_df = self.__data_repository.get_sample_df(self.data_source_ids)
        if sample_df.empty:
            return DefaultVolume(list(self.__data_repository.data_sources.keys()))

        first_column = sample_df.columns[0]
        metric = Volume(first_column, self.data_source_ids)
        metric.validate_query(sample_df)

        self.__volume_metric_cache = metric
        return metric

    def validate_metric(
        self, name: str, query: str, data_source_ids: list[DataSourceID]
    ) -> Metric:
        # Validate Name
        if name in DefaultMetricNames:
            raise ValueError(f"Metric name '{name}' is reserved.")

        # Validate Query with Data Source
        key = (query, tuple(sorted(data_source_ids)))

        if key in self.__verified_metrics:
            new_metric = self.__verified_metrics[key].duplicate(name=name)

            return new_metric

        sample_df = self.__data_repository.get_sample_df(data_source_ids)
        if sample_df.empty:
            raise SampleDataNotLoadedError()

        new_metric = Metric(
            uid=MetricID.TEMPORARY,
            name=name,
            query=query,
            data_source_ids=data_source_ids,
        )

        # Validating query string
        new_metric.validate_query(data=sample_df)
        self.__verified_metrics[key] = new_metric

        return new_metric

    def create_metric(
        self,
        name: str,
        query: str,
        use_thousand_sep: bool,
        is_percentage: bool,
        decimal_places: int,
        data_source_ids: list[DataSourceID],
    ) -> None:
        new_metric = self.validate_metric(name, query, data_source_ids)

        new_metric.uid = MetricID(self._get_new_id(current_ids=self.metrics.keys()))
        new_metric.use_thousand_sep = use_thousand_sep
        new_metric.is_percentage = is_percentage
        new_metric.decimal_places = decimal_places

        self.metrics[new_metric.uid] = new_metric

        self.notify_subscribers()

    def modify_metric(
        self,
        metric_id: MetricID,
        name: str,
        query: str,
        use_thousand_sep: bool,
        is_percentage: bool,
        decimal_places: int,
        data_source_ids: list[DataSourceID],
    ) -> None:
        if metric_id not in self.metrics:
            raise ValueError(f"Metric '{metric_id}' not found.")

        modified_metric = self.validate_metric(name, query, data_source_ids)
        modified_metric.uid = metric_id
        modified_metric.use_thousand_sep = use_thousand_sep
        modified_metric.is_percentage = is_percentage
        modified_metric.decimal_places = decimal_places

        self.metrics[metric_id] = modified_metric

        self.notify_subscribers()

    def remove_metric(self, metric_id: MetricID) -> None:
        if metric_id in self.metrics:
            del self.metrics[metric_id]

        self.notify_subscribers()

    def duplicate_metric(self, metric_id: MetricID) -> None:
        metric_name = self.metrics[metric_id].name
        existing_names = set(m.name for m in self.metrics.values())

        new_name = create_duplicate_name(metric_name, existing_names)

        metric_obj = self.metrics[metric_id].duplicate(
            uid=MetricID(self._get_new_id(current_ids=self.metrics.keys())),
            name=new_name,
        )

        self.metrics[metric_obj.uid] = metric_obj

        self.notify_subscribers()

    def get_all_metrics(self) -> dict[MetricID, Metric]:
        all_metrics: dict[MetricID, Metric] = self.metrics.copy()

        all_metrics[self.unit_bad_rate.uid] = self.unit_bad_rate
        all_metrics[self.dollar_bad_rate.uid] = self.dollar_bad_rate
        all_metrics[self.volume.uid] = self.volume

        return all_metrics

    def to_dict(self) -> MetricRepositoryJSON:
        return MetricRepositoryJSON(
            metrics=[m.to_dict() for m in self.metrics.values()],
            var_unt_bad=self._var_unt_bad,
            var_dlr_bad=self._var_dlr_bad,
            var_avg_bal=self._var_avg_bal,
            current_rate_mob=self._current_rate_mob,
            lifetime_rate_mob=self._lifetime_rate_mob,
            data_source_ids=[ds_id for ds_id in self._data_source_ids],
        )

    @classmethod
    def from_dict(
        cls,
        data: MetricRepositoryJSON,
        data_repository: DataRepository,
        errors: t.Literal["ignore", "raise"],
    ):
        repo = cls(data_repository=data_repository)

        invalid_metrics: list[tuple[Metric, Exception]] = []

        for metric_json in data.metrics:
            metric_obj = Metric.from_dict(metric_json)

            try:
                metric_obj.validate_query(
                    data_repository.get_sample_df(metric_obj.data_source_ids)
                )
            except (SyntaxError, ValueError, SampleDataNotLoadedError) as error:
                if errors == "raise":
                    invalid_metrics.append((metric_obj, error))

                continue

            repo.metrics[metric_obj.uid] = metric_obj

        repo._var_unt_bad = data.var_unt_bad
        repo._var_dlr_bad = data.var_dlr_bad
        repo._var_avg_bal = data.var_avg_bal
        repo._current_rate_mob = data.current_rate_mob
        repo._lifetime_rate_mob = data.lifetime_rate_mob
        repo._data_source_ids = [DataSourceID(i) for i in data.data_source_ids]

        repo._update_user_defined_metrics()  # This cleans up invalid metrics if data repo has data
        repo._update_default_metrics()  # This cleans up default metrics config if invalid

        return repo, invalid_metrics
