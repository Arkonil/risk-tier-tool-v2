import re
import typing as t

from pydantic import BaseModel, ConfigDict, Field

from risc_tool.data.models.completion import Completion


class DataConfig(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        serialize_by_alias=True,
        validate_by_alias=True,
    )

    common_columns: list[str] = Field(default_factory=list)
    all_columns: list[str] = Field(default_factory=list)

    def model_post_init(self, context: t.Any) -> None:
        self._completion_cache: dict[str, Completion] = {}

        return super().model_post_init(context)

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

        if self.var_unt_wrt_off not in common_columns:
            self.var_unt_wrt_off = None

        if self.var_dlr_wrt_off not in common_columns:
            self.var_dlr_wrt_off = None

        if self.var_avg_bal not in common_columns:
            self.var_avg_bal = None

    def get_completions(self, *, columns: list[str] | None = None, common: bool = True):
        if columns is not None:
            return [self._completion_cache[col] for col in columns]

        if common:
            return [self._completion_cache[col] for col in self.common_columns]
        else:
            return [self._completion_cache[col] for col in self.all_columns]


__all__ = ["DataConfig"]
