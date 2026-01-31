import typing as t

from risc_tool.data.models.changes import ChangeTracker
from risc_tool.data.models.enums import Signature, VariableType
from risc_tool.data.models.types import ChangeIDs, DataSourceID
from risc_tool.data.repositories.data import DataRepository
from risc_tool.data.repositories.metric import MetricRepository


class VariableSelectorViewModel(ChangeTracker):
    @property
    def _signature(self) -> Signature:
        return Signature.VARIABLE_SELECTOR_VIEW_MODEL

    def __init__(
        self, data_repository: DataRepository, metric_repository: MetricRepository
    ):
        super().__init__(dependencies=[data_repository, metric_repository])

        self.__data_repository = data_repository
        self.__metric_repository = metric_repository

    def on_dependency_update(self, change_ids: ChangeIDs):
        pass

    # Data Source Selection
    @property
    def all_data_source_ids(self) -> list[DataSourceID]:
        return [ds_id for ds_id in self.__data_repository.data_sources]

    @property
    def selected_data_source_ids(self) -> list[DataSourceID]:
        return self.__metric_repository.data_source_ids

    @selected_data_source_ids.setter
    def selected_data_source_ids(self, value: list[DataSourceID]):
        self.__metric_repository.data_source_ids = value

    def get_data_source_label(self, data_source_id: DataSourceID):
        return self.__data_repository.data_sources[data_source_id].label

    # Variable Selectors
    @property
    def available_columns(self) -> list[str | None]:
        column_types = self.__data_repository.available_columns(
            self.__metric_repository.data_source_ids
        )
        return [None] + [
            c_name
            for (c_name, c_type) in column_types
            if c_type == VariableType.NUMERICAL
        ]

    def get_variable(self, usage: t.Literal["unt_bad", "dlr_bad", "avg_bal"]):
        if usage == "unt_bad":
            return self.__metric_repository.var_unt_bad
        elif usage == "dlr_bad":
            return self.__metric_repository.var_dlr_bad
        elif usage == "avg_bal":
            return self.__metric_repository.var_avg_bal
        else:
            return None

    def set_variable(
        self, usage: t.Literal["unt_bad", "dlr_bad", "avg_bal"], value: str | None
    ):
        if usage == "unt_bad":
            self.__metric_repository.var_unt_bad = value
        elif usage == "dlr_bad":
            self.__metric_repository.var_dlr_bad = value
        elif usage == "avg_bal":
            self.__metric_repository.var_avg_bal = value

    # MOB Selector
    def get_mob(self, mob_type: t.Literal["current", "lifetime"]):
        if mob_type == "current":
            return self.__metric_repository.current_rate_mob
        elif mob_type == "lifetime":
            return self.__metric_repository.lifetime_rate_mob
        else:
            return None

    def set_mob(self, mob_type: t.Literal["current", "lifetime"], value: int):
        if mob_type == "current":
            self.__metric_repository.current_rate_mob = value
        elif mob_type == "lifetime":
            self.__metric_repository.lifetime_rate_mob = value


__all__ = ["VariableSelectorViewModel"]
