import typing as t

import pandas as pd

from classes.data import Data
from classes.filter import Filter
from classes.utils import integer_generator


__generator = integer_generator()


def new_id(current_ids: t.Iterable[str] = None) -> str:
    if current_ids is None:
        current_ids = []

    while True:
        new_id = str(next(__generator))
        if new_id not in current_ids:
            return new_id


class FilterContainer:
    def __init__(self):
        self.filters: dict[str, Filter] = {}
        self._verified_filters: dict[str, Filter] = {}

        self._current_filter_view_mode: t.Literal["view", "edit"] = "view"
        self._current_filter_edit_id: str | None = None

    @property
    def mode(self) -> t.Literal["view", "edit"]:
        return self._current_filter_view_mode

    @property
    def current_filter_edit_id(self) -> str | None:
        return self._current_filter_edit_id

    def set_mode(self, mode: t.Literal["view", "edit"], filter_id: str = None) -> None:
        self._current_filter_view_mode = mode
        self._current_filter_edit_id = filter_id

        if mode == "view":
            self._verified_filters = {}

    def validate_filter(
        self,
        filter_id: str,
        name: str,
        query: str,
        data: Data,
    ) -> Filter:
        if query in self._verified_filters:
            new_filter = self._verified_filters[query]
            new_filter.id = filter_id
            new_filter.name = name
            self._verified_filters[query] = new_filter

            return new_filter

        new_filter = Filter(id_=filter_id, name=name, query=query)

        # Validating query string
        new_filter.validate_query(available_columns=data.sample_df.columns)

        # Creating mask
        df = data.load_columns(column_names=new_filter.used_columns)
        new_filter.create_mask(df)

        self._verified_filters[query] = new_filter

        return new_filter

    def create_filter(
        self, filter_id: str | None, name: str, query: str, data: Data
    ) -> None:
        if filter_id is None:
            filter_id = new_id(current_ids=self.filters.keys())

        new_filter = self.validate_filter(filter_id, name, query, data)

        self.filters[filter_id] = new_filter

    def remove_filter(self, filter_id: str):
        if filter_id in self.filters:
            del self.filters[filter_id]

    def duplicate_filter(self, filter_id: str) -> None:
        filter_obj = self.filters[filter_id].copy()
        filter_obj.id = new_id(current_ids=self.filters.keys())
        self.filters[filter_obj.id] = filter_obj

    def get_mask(self, filter_ids: t.Iterable[str], index: pd.Index) -> pd.Series:
        mask = pd.Series(True, index=index, dtype=bool)

        if not self.filters or not filter_ids:
            return mask

        for filter_id in filter_ids:
            if filter_id in self.filters:
                mask &= self.filters[filter_id].mask

        return mask

    def to_dict(self) -> dict[str, t.Any]:
        """Serializes the FilterContainer object to a dictionary."""
        return {
            "filters": {
                filter_id: filter_obj.to_dict()
                for filter_id, filter_obj in self.filters.items()
            },
        }

    @classmethod
    def from_dict(cls, dict_data: dict[str, t.Any], data: Data) -> "FilterContainer":
        """Creates a FilterContainer object from a dictionary."""
        instance = cls()

        if "filters" in dict_data:
            for filter_id, filter_data in dict_data["filters"].items():
                instance.create_filter(
                    filter_id=filter_id,
                    name=filter_data["name"],
                    query=filter_data["query"],
                    data=data,
                )

        return instance
