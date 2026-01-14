import typing as t

import pandas as pd

from risc_tool.data.models.enums import Signature
from risc_tool.data.models.exceptions import InvalidFilterError
from risc_tool.data.models.filter import Filter
from risc_tool.data.models.types import ChangeIDs, FilterID
from risc_tool.data.repositories.base import BaseRepository
from risc_tool.data.repositories.data import DataRepository
from risc_tool.utils.duplicate_name import create_duplicate_name


class FilterRepository(BaseRepository):
    @property
    def _signature(self) -> Signature:
        return Signature.FILTER_REPOSITORY

    def __init__(self, data_repository: DataRepository) -> None:
        super().__init__(dependencies=[data_repository])
        # User defined filters
        self.filters: dict[FilterID, Filter] = {}

        # Cache
        self.__verified_filters: dict[str, Filter] = {}

        # Dependencies
        self.__data_repository: DataRepository = data_repository

    def __update_user_defined_filters(self):
        if not self.__data_repository.sample_loaded:
            self.filters.clear()
            return

        filter_ids_to_remove: list[FilterID] = []

        common_columns = self.__data_repository.common_columns

        for filter_id, filter_obj in self.filters.items():
            try:
                filter_obj.validate_query(available_columns=common_columns)
                data = self.__data_repository.load_columns(filter_obj.used_columns)
                filter_obj.create_mask(data)
            except InvalidFilterError:
                filter_ids_to_remove.append(filter_id)

        for filter_id in filter_ids_to_remove:
            del self.filters[filter_id]

    def __clear_cache(self):
        self.__verified_filters.clear()

    def on_dependency_update(self, change_ids: ChangeIDs):
        # Update use defined filters
        self.__update_user_defined_filters()

        # clear cache
        self.__clear_cache()

    def validate_filter(self, name: str, query: str) -> Filter:
        if query in self.__verified_filters:
            new_filter = self.__verified_filters[query].duplicate(name=name)

            return new_filter

        new_filter = Filter(uid=FilterID.TEMPORARY, name=name, query=query)

        # Validating query string
        new_filter.validate_query(
            available_columns=self.__data_repository.common_columns
        )

        # Creating mask
        df = self.__data_repository.load_columns(column_names=new_filter.used_columns)
        new_filter.create_mask(df)

        self.__verified_filters[query] = new_filter

        return new_filter

    def create_filter(self, name: str, query: str) -> None:
        new_filter = self.validate_filter(name, query)
        new_filter.uid = FilterID(self._get_new_id(current_ids=self.filters.keys()))

        self.filters[new_filter.uid] = new_filter

        self.notify_subscribers()

    def modify_filter(self, filter_id: FilterID, name: str, query: str) -> None:
        if filter_id not in self.filters:
            raise ValueError(f"Filter '{filter_id}' not found.")

        modified_filter = self.validate_filter(name, query)
        modified_filter.uid = filter_id

        self.filters[filter_id] = modified_filter

        self.notify_subscribers()

    def remove_filter(self, filter_id: FilterID):
        if filter_id in self.filters:
            del self.filters[filter_id]

        self.notify_subscribers()

    def duplicate_filter(self, filter_id: FilterID) -> None:
        filter_name = self.filters[filter_id].name
        existing_names = set(m.name for m in self.filters.values())

        new_name = create_duplicate_name(filter_name, existing_names)

        filter_obj = self.filters[filter_id].duplicate(
            uid=FilterID(self._get_new_id(current_ids=self.filters.keys())),
            name=new_name,
        )

        self.filters[filter_obj.uid] = filter_obj

        self.notify_subscribers()

    def get_mask(self, filter_ids: t.Iterable[FilterID]) -> pd.Series:
        index = self.__data_repository.index
        mask = pd.Series(True, index=index, dtype=bool)

        if not self.filters or not filter_ids:
            return mask

        for filter_id in filter_ids:
            if filter_id not in self.filters:
                continue

            filter_obj = self.filters[filter_id]

            if filter_obj.mask is None or not filter_obj.mask.index.equals(index):
                filter_obj.create_mask(
                    self.__data_repository.load_columns(
                        column_names=filter_obj.used_columns
                    )
                )

            current_mask = t.cast(pd.Series, filter_obj.mask)

            mask &= current_mask

        return mask.astype("boolean")

    def get_filters(self, filter_ids: list[FilterID] | None = None):
        filters = self.filters.copy()

        if filter_ids is None:
            return filters

        return {filter_id: filters[filter_id] for filter_id in filter_ids}
