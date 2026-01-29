import pathlib as p
import re
import typing as t

import pandas as pd

from risc_tool.data.models.enums import VariableType
from risc_tool.data.models.json_models import DataSourceJSON
from risc_tool.data.models.types import DataSourceID
from risc_tool.data.services.local_data_import import import_data


class DataSource:
    _pattern = re.compile(r"(.+) \((Numerical|Categorical)\)")

    def __init__(
        self,
        uid: DataSourceID,
        label: str,
        filepath: p.Path,
        read_mode: t.Literal["CSV", "EXCEL"] = "CSV",
        delimiter: str = ",",
        sheet_name: str = "0",
        header_row: int = 0,
        sample_row_count: int = 100,
    ):
        self.uid: DataSourceID = uid
        self.label: str = label
        self.filepath: p.Path = filepath
        self.read_mode: t.Literal["CSV", "EXCEL"] = read_mode
        self.delimiter: str = delimiter
        self.sheet_name: str = sheet_name
        self.header_row: int = header_row
        self.sample_row_count: int = sample_row_count
        self.df_size: int | None = None

        self._sample_df: pd.DataFrame | None = None
        self._df: pd.DataFrame = pd.DataFrame()

    def to_dict(self) -> DataSourceJSON:
        return DataSourceJSON(
            uid=self.uid,
            label=self.label,
            filepath=self.filepath,
            read_mode=self.read_mode,
            delimiter=self.delimiter,
            sheet_name=self.sheet_name,
            header_row=self.header_row,
            sample_row_count=self.sample_row_count,
            df_size=self.df_size,
        )

    @classmethod
    def from_dict(cls, data: DataSourceJSON) -> "DataSource":
        """
        Creates a DataSource instance from a dictionary.
        Validates the input type and restores the object.
        """

        instance = cls(
            uid=data.uid,
            label=data.label,
            filepath=data.filepath,
            read_mode=data.read_mode,
            delimiter=data.delimiter,
            sheet_name=data.sheet_name,
            header_row=data.header_row,
            sample_row_count=data.sample_row_count,
        )

        return instance

    @property
    def sample_loaded(self) -> bool:
        return self._sample_df is not None

    @property
    def index(self):
        if not self._df.empty:
            return self._df.index

        if self.df_size is None:
            raise ValueError("Data not loaded")

        return pd.RangeIndex(start=0, stop=self.df_size, step=1)

    def validate_read_config(self) -> None:
        if not self.filepath or not self.filepath.is_file():
            raise FileNotFoundError(f"File not found: `{self.filepath}`")

        if self.read_mode == "CSV" and self.filepath.suffix.lower() != ".csv":
            raise ValueError(f"Selected file is not a CSV: `{self.filepath}`")

        if self.read_mode == "EXCEL" and self.filepath.suffix.lower() not in [
            ".xlsx",
            ".xls",
        ]:
            raise ValueError(f"Selected file is not a EXCEL: `{self.filepath}`")

    def load_sample(self) -> None:
        self._sample_df = import_data(
            self.filepath,
            self.read_mode,
            self.delimiter,
            self.sheet_name,
            self.header_row,
            self.sample_row_count,
        ).convert_dtypes()

        self.df_size = len(
            import_data(
                self.filepath,
                self.read_mode,
                self.delimiter,
                self.sheet_name,
                self.header_row,
                usecols=[0],
            )
        )

        self._df = pd.DataFrame()

    def load_data(self, column_names: list[str]) -> pd.DataFrame:
        return import_data(
            self.filepath,
            self.read_mode,
            self.delimiter,
            self.sheet_name,
            self.header_row,
            usecols=column_names,
        )

    @property
    def column_types(self) -> set[tuple[str, VariableType]]:
        _column_types: set[tuple[str, VariableType]] = set()

        if not self.sample_loaded:
            return _column_types

        sample_df = t.cast(pd.DataFrame, self._sample_df)

        for column in sample_df.columns:
            c_type: VariableType = (
                VariableType.NUMERICAL
                if pd.api.types.is_numeric_dtype(sample_df[column])
                else VariableType.CATEGORICAL
            )

            _column_types.add((column, c_type))

        return _column_types

    def _load_column_from_cache(self, column_name: str, column_type: VariableType):
        preferred_column_name = f"{column_name} ({column_type.capitalize()})"

        if preferred_column_name in self._df.columns:
            return self._df[preferred_column_name].copy()

        alternative_column_name = f"{column_name} ({column_type.other.capitalize()})"

        if (
            column_type == VariableType.CATEGORICAL
            and alternative_column_name in self._df.columns
        ):
            self._df[preferred_column_name] = self._df[alternative_column_name].astype(
                "category"
            )
            return self._df[preferred_column_name].copy()

        if (
            column_type == VariableType.NUMERICAL
            and alternative_column_name in self._df.columns
        ):
            try:
                temp_column = pd.to_numeric(
                    self._df[alternative_column_name], errors="raise"
                )
                self._df[preferred_column_name] = temp_column
                return self._df[preferred_column_name].copy()
            except ValueError:
                return self._df[alternative_column_name].copy()

        raise IndexError("Column not found")

    def load_columns(
        self, column_names: list[str], column_types: list[VariableType]
    ) -> pd.DataFrame:
        cached_columns: list[pd.Series] = []
        remaining_columns: list[tuple[str, VariableType]] = []

        for c_name, c_type in zip(column_names, column_types):
            try:
                cached_columns.append(self._load_column_from_cache(c_name, c_type))
            except IndexError:
                remaining_columns.append((c_name, c_type))

        if cached_columns:
            final_df = pd.concat(cached_columns, axis=1)
        else:
            final_df = pd.DataFrame(index=self.index)

        new_columns = pd.DataFrame(index=self.index)
        if remaining_columns:
            if self._sample_df is not None:
                all_columns: list[str] = self._sample_df.columns.to_list()
            else:
                all_columns: list[str] = []

            available_column_names = [
                column[0] for column in remaining_columns if column[0] in all_columns
            ]
            missing_column_names = [
                column[0]
                for column in remaining_columns
                if column[0] not in all_columns
            ]

            new_loaded_columns = self.load_data(available_column_names)
            new_generated_columns = pd.DataFrame(
                columns=missing_column_names,
                index=self.index,
            )

            new_columns = pd.concat([new_loaded_columns, new_generated_columns], axis=1)

        for c_name, c_type in remaining_columns:
            prf_column_name = f"{c_name} ({c_type.capitalize()})"
            alt_column_name = f"{c_name} ({c_type.other.capitalize()})"

            if c_type == VariableType.NUMERICAL:
                try:
                    temp_column = pd.to_numeric(new_columns[c_name], errors="raise")
                    self._df[prf_column_name] = temp_column.copy()
                    final_df[prf_column_name] = temp_column.copy()
                except ValueError:
                    self._df[alt_column_name] = new_columns[c_name].astype("category")
                    final_df[alt_column_name] = self._df[alt_column_name].copy()
            else:
                self._df[prf_column_name] = new_columns[c_name].astype("category")
                final_df[prf_column_name] = self._df[prf_column_name].copy()

        def rename_col(s: str) -> str:
            if m := self._pattern.match(s):
                return str(m.group(1))
            return s

        final_df.rename(columns=rename_col, inplace=True)

        return final_df


__all__ = ["DataSource"]
