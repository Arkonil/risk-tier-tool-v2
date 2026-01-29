import re

from risc_tool.data.models.completion import Completion


class DataConfig:
    def __init__(
        self,
        common_columns: list[str] | None = None,
        all_columns: list[str] | None = None,
    ):
        self.common_columns: list[str] = common_columns or []
        self.all_columns: list[str] = all_columns or []

        self._completion_cache: dict[str, Completion] = {}

    @staticmethod
    def create_completion(column: str) -> Completion:
        return Completion(
            caption=column,
            value=f"`{column}`" if re.search(r"\s+", column) else column,
            meta="Column",
            name=column,
            score=100,
        )

    def refresh(self, common_columns: list[str], all_columns: list[str]) -> None:
        self.common_columns = common_columns
        self.all_columns = all_columns

        for col in all_columns:
            self._completion_cache[col] = self.create_completion(col)

    def get_completions(self, *, columns: list[str] | None = None, common: bool = True):
        if columns is not None:
            return [self._completion_cache[col] for col in columns]

        if common:
            return [self._completion_cache[col] for col in self.common_columns]
        else:
            return [self._completion_cache[col] for col in self.all_columns]


__all__ = ["DataConfig"]
