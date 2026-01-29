import typing as t

from risc_tool.data.models.changes import ChangeTracker
from risc_tool.data.models.enums import Signature
from risc_tool.data.models.exceptions import InvalidFilterError, format_error
from risc_tool.data.models.filter import Filter
from risc_tool.data.models.types import ChangeIDs, FilterID
from risc_tool.data.repositories.data import DataRepository
from risc_tool.data.repositories.filter import FilterRepository


class FilterViewModel(ChangeTracker):
    @property
    def _signature(self) -> Signature:
        return Signature.FILTER_VIEWMODEL

    def __init__(
        self, data_repository: DataRepository, filter_repository: FilterRepository
    ):
        super().__init__(dependencies=[data_repository, filter_repository])

        # Dependencies
        self.__data_repository = data_repository
        self.__filter_repository = filter_repository

        # Filter Editor States
        self.__view_mode: t.Literal["view", "edit"] = "view"
        self.__filter_cache = self.__empty_filter
        self.is_verified = False
        self.latest_editor_id = ""
        self.__errors: list[InvalidFilterError | ValueError | SyntaxError] = []

    def on_dependency_update(self, change_ids: ChangeIDs) -> None:
        self.__filter_cache = self.__empty_filter
        self.is_verified = False
        self.__errors = []

    @property
    def __empty_filter(self):
        return Filter(uid=FilterID.EMPTY, name="", query="")

    @property
    def mode(self) -> t.Literal["view", "edit"]:
        return self.__view_mode

    def set_mode(
        self, mode: t.Literal["view", "edit"], filter_id: FilterID = FilterID.EMPTY
    ) -> None:
        self.__view_mode = mode
        self.__errors.clear()
        self.is_verified = False

        if mode == "edit":
            if filter_id == FilterID.EMPTY:
                self.__filter_cache = self.__empty_filter
            else:
                self.__filter_cache = self.__filter_repository.filters.get(
                    filter_id, self.__empty_filter
                ).duplicate()
                self.is_verified = True

    # For Error View
    @property
    def sample_loaded(self) -> bool:
        return self.__data_repository.sample_loaded

    # For Editor
    @property
    def filter_cache(self):
        return self.__filter_cache

    def set_filter_property(
        self,
        *,
        name: str | None = None,
        query: str | None = None,
    ):
        if name is not None:
            self.__filter_cache.name = name
            self.is_verified = False

        if query is not None:
            self.__filter_cache.query = query
            self.is_verified = False

    def get_column_completions(self):
        completions = self.__data_repository.get_completions(common=True)
        return [c.model_dump(mode="python") for c in completions]

    def validate_filter(self, name: str, query: str, latest_editor_id: str):
        if query == "":
            self.__errors.append(ValueError("Filter query cannot be empty"))
            self.is_verified = False
            return

        if name == "":
            self.__errors.append(ValueError("Filter name cannot be empty"))
            self.is_verified = False
            return

        self.__errors.clear()

        try:
            current_id = self.filter_cache.uid

            for filter_obj in self.__filter_repository.filters.values():
                if name == filter_obj.name and current_id != filter_obj.uid:
                    raise ValueError("Filter name already exists")

            self.__filter_cache = self.__filter_repository.validate_filter(
                name=name,
                query=query,
            )
            self.__filter_cache.uid = current_id
            self.is_verified = True
            self.latest_editor_id = latest_editor_id
        except (InvalidFilterError, SyntaxError, ValueError) as e:
            self.__errors.append(e)
            self.is_verified = False

    def error_message(self) -> str:
        if not self.__errors:
            return ""

        messages: list[str] = []

        for error in self.__errors:
            messages.append(format_error(error))

        return "\n\n".join(messages)

    def save_filter(self):
        if not self.is_verified or self.__errors:
            raise RuntimeError("Filter is not verified")

        if self.__filter_cache.uid == FilterID.TEMPORARY:
            raise RuntimeError(
                f"FilterID should not be {FilterID.TEMPORARY}. This indicates a error in the logic."
            )

        if self.__filter_cache.uid == FilterID.EMPTY:
            self.__filter_repository.create_filter(
                name=self.__filter_cache.name,
                query=self.__filter_cache.query,
            )
        else:
            self.__filter_repository.modify_filter(
                filter_id=self.__filter_cache.uid,
                name=self.__filter_cache.name,
                query=self.__filter_cache.query,
            )

        self.set_mode("view")

    # For List View
    @property
    def filters(self):
        return self.__filter_repository.filters

    def duplicate_filter(self, filter_id: FilterID) -> None:
        self.__filter_repository.duplicate_filter(filter_id)

    def remove_filter(self, filter_id: FilterID) -> None:
        self.__filter_repository.remove_filter(filter_id)


__all__ = ["FilterViewModel"]
