import pathlib
import typing as t
from collections import OrderedDict

import numpy as np
import pandas as pd
from pydantic import ValidationError

from risc_tool.data.models.data_config import DataConfig
from risc_tool.data.models.data_source import DataSource
from risc_tool.data.models.enums import Signature, VariableType
from risc_tool.data.models.metric import Metric
from risc_tool.data.repositories.base import BaseRepository


class MissingColumnError(Exception):
    """
    Exception raised when a specified column is not found in the data or has an invalid type.
    """

    def __init__(self, column_name: str):
        super().__init__(f"Column '{column_name}' not found in data.")


class VariableNotNumericError(Exception):
    """
    Exception raised when a variable is expected to be numeric but is not.
    """

    def __init__(self, variable_name: str, actual_type: str):
        super().__init__(
            f"Variable '{variable_name}' is not numeric. Found type: {actual_type}."
        )


class DataImportError(Exception):
    """
    Exception raised when there is an error during data import.
    """

    def __init__(self, message: str, data_source: DataSource | None = None):
        self.message = message
        self.data_source = data_source
        super().__init__(self.message)


class SampleDataNotLoadedError(Exception):
    """
    Exception raised when sample data is not loaded but is required for an operation.
    """

    def __init__(self, message: str = "Sample data is not loaded."):
        self.message = message
        super().__init__(self.message)


class DataRepository(BaseRepository):
    """
    This class stores the data and all reading attributes
    """

    @property
    def _signature(self) -> Signature:
        return Signature.DATA_REPOSITORY

    def __init__(self) -> None:
        super().__init__()

        self.data_sources: OrderedDict[str, DataSource] = OrderedDict()
        self.data_config: DataConfig = DataConfig()

    @property
    def sample_loaded(self) -> bool:
        return bool(self.data_sources) and all(
            ds.sample_loaded for ds in self.data_sources.values()
        )

    @property
    def first_sample_df(self) -> pd.DataFrame:
        if not self.sample_loaded:
            raise SampleDataNotLoadedError()

        return t.cast(pd.DataFrame, next(iter(self.data_sources.values()))._sample_df)

    @property
    def _common_columns(self) -> list[str]:
        if not self.sample_loaded:
            return []

        common_cols_and_types: set[tuple[str, VariableType]] = set.intersection(*[
            ds.column_types for ds in self.data_sources.values()
        ])

        return list(sorted(str(col) for col, _ in common_cols_and_types))

    @property
    def common_columns(self) -> list[str]:
        return self.data_config.common_columns

    @property
    def _all_columns(self) -> list[str]:
        if not self.sample_loaded:
            return []

        all_cols_and_types: set[tuple[str, VariableType]] = set.union(*[
            ds.column_types for ds in self.data_sources.values()
        ])

        return list(sorted(str(col) for col, _ in all_cols_and_types))

    @property
    def all_columns(self) -> list[str]:
        return self.data_config.all_columns

    @property
    def get_completions(self, *, columns: list[str] | None = None, common: bool = True):
        return self.data_config.get_completions(columns=columns, common=common)

    def available_columns(
        self, data_source_ids: t.Iterable[str]
    ) -> set[tuple[str, VariableType]]:
        if not self.sample_loaded:
            return set()

        columns = set.intersection(*[
            ds.column_types
            for ds in self.data_sources.values()
            if ds.uid in data_source_ids
        ])

        return columns

    # def validate_metric_input_column(self, column_name: str):
    #     available_columns = self.available_columns(self.data_config.metric_data_source_ids)

    #     if (column_name, VariableType.CATEGORICAL) in available_columns:
    #         raise VariableNotNumericError(
    #             column_name,
    #             str(
    #                 self.data_sources[next(iter(self.data_config.metric_data_source_ids))]
    #                 .load_columns([column_name], [VariableType.CATEGORICAL])
    #                 .iloc[:, 0]
    #                 .dtypes
    #             ),
    #         )

    #     if (column_name, VariableType.NUMERICAL) not in available_columns:
    #         raise MissingColumnError(column_name)

    # @property
    # def var_unt_wrt_off(self) -> str | None:
    #     return self.data_config.var_unt_wrt_off

    # @var_unt_wrt_off.setter
    # def var_unt_wrt_off(self, value: str | None):
    #     if value is None:
    #         self.data_config.var_unt_wrt_off = None
    #         return

    #     self.validate_metric_input_column(value)

    #     self.data_config.var_unt_wrt_off = value

    # @property
    # def var_dlr_wrt_off(self) -> str | None:
    #     return self.data_config.var_dlr_wrt_off

    # @var_dlr_wrt_off.setter
    # def var_dlr_wrt_off(self, value: str | None):
    #     if value is None:
    #         self.data_config.var_dlr_wrt_off = None
    #         return

    #     self.validate_metric_input_column(value)

    #     self.data_config.var_dlr_wrt_off = value

    # @property
    # def var_avg_bal(self) -> str | None:
    #     return self.data_config.var_avg_bal

    # @var_avg_bal.setter
    # def var_avg_bal(self, value: str | None):
    #     if value is None:
    #         self.data_config.var_avg_bal = None
    #         return

    #     self.validate_metric_input_column(value)

    #     self.data_config.var_avg_bal = value

    # @property
    # def current_rate_mob(self) -> int:
    #     return self.data_config.current_rate_mob

    # @current_rate_mob.setter
    # def current_rate_mob(self, value: int):
    #     if value <= 0:
    #         raise ValueError("Current rate MOB must be a positive integer.")

    #     self.data_config.current_rate_mob = value

    def add_data_source(
        self,
        filepath: pathlib.Path,
        label: str,
        read_mode: t.Literal["CSV", "EXCEL"] = "CSV",
        delimiter: str = ",",
        sheet_name: str = "0",
        header_row: int = 0,
        sample_row_count: int = 100,
    ):
        try:
            data_source = DataSource(
                uid="",
                filepath=filepath,
                label=label,
                read_mode=read_mode,
                delimiter=delimiter,
                sheet_name=sheet_name,
                header_row=header_row,
                sample_row_count=sample_row_count,
            )
            data_source.validate_read_config()

            for ds in self.data_sources.values():
                if ds.label == data_source.label:
                    raise ValueError(
                        f"Data source with label '{label}' already exists."
                    )
                if ds.filepath == data_source.filepath:
                    raise ValueError(
                        f"Data source with filepath '{filepath}' already exists."
                    )

        except ValidationError as error:
            raise DataImportError(str(error).replace("\n", "\n\n"))
        except (FileNotFoundError, ValueError) as error:
            raise DataImportError(str(error))

        data_source.uid = self._get_new_id(current_ids=self.data_sources.keys())
        self.data_sources[data_source.uid] = data_source
        data_source.load_sample()

        self.data_config.refresh(
            common_columns=self._common_columns, all_columns=self._all_columns
        )

        self.notify_subscribers()

        return data_source

    def update_data_source(
        self,
        data_source_id: str,
        filepath: pathlib.Path | None = None,
        label: str | None = None,
        read_mode: t.Literal["CSV", "EXCEL"] | None = None,
        delimiter: str | None = None,
        sheet_name: str | None = None,
        header_row: int | None = None,
        sample_row_count: int | None = None,
    ):
        data_source = self.data_sources[data_source_id]

        if label is None:
            label = data_source.label
        if filepath is None:
            filepath = data_source.filepath
        if read_mode is None:
            read_mode = data_source.read_mode
        if delimiter is None:
            delimiter = data_source.delimiter
        if sheet_name is None:
            sheet_name = data_source.sheet_name
        if header_row is None:
            header_row = data_source.header_row
        if sample_row_count is None:
            sample_row_count = data_source.sample_row_count

        try:
            new_data_source = DataSource(
                uid=data_source_id,
                filepath=filepath,
                label=label,
                read_mode=read_mode,
                delimiter=delimiter,
                sheet_name=sheet_name,
                header_row=header_row,
                sample_row_count=sample_row_count,
            )
            data_source.validate_read_config()
        except ValidationError as error:
            raise DataImportError(str(error).replace("\n", "\n\n"), data_source)
        except (FileNotFoundError, ValueError) as error:
            raise DataImportError(str(error), data_source)

        # Store the new source
        self.data_sources[data_source_id] = new_data_source

        # Load the new sample
        new_data_source.load_sample()

        # Update the common columns
        self.data_config.refresh(
            common_columns=self._common_columns, all_columns=self._all_columns
        )

        # Notify subscribers
        self.notify_subscribers()

        return new_data_source

    def delete_data_source(self, data_source_id: str):
        del self.data_sources[data_source_id]

        self.data_config.refresh(
            common_columns=self._common_columns, all_columns=self._all_columns
        )

        self.notify_subscribers()

    def load_columns(
        self,
        column_names: list[str],
        column_types: list[VariableType] | None = None,
        data_source_ids: set[str] | None = None,
    ):
        if not self.sample_loaded:
            raise SampleDataNotLoadedError()

        if column_types is None:
            column_types = [VariableType.NUMERICAL for _ in column_names]

        if len(column_names) != len(column_types):
            raise ValueError("column_names and column_types must have the same length")

        dataframes: list[pd.DataFrame] = []
        keys: list[str] = []

        for ds in self.data_sources.values():
            dataframes.append(ds.load_columns(column_names, column_types))
            keys.append(ds.uid)

        final_df = pd.concat(dataframes, axis=0, keys=keys)

        if data_source_ids is None:
            data_source_ids = set(self.data_sources.keys())

        omitted_source_ids = set(self.data_sources.keys()) - data_source_ids
        final_df.loc[(list(omitted_source_ids),), :] = pd.NA

        final_df = final_df.convert_dtypes()

        for col in final_df.columns:
            if final_df[col].dtype == "object":
                final_df[col] = final_df[col].astype("string")

        return final_df

    def load_column(
        self,
        column_name: str | None = None,
        column_type: VariableType = VariableType.NUMERICAL,
        data_source_ids: set[str] | None = None,
    ) -> pd.Series:
        if not self.sample_loaded:
            raise SampleDataNotLoadedError()

        if column_name is not None:
            return self.load_columns(
                [column_name], [column_type], data_source_ids
            ).iloc[:, 0]

        index = pd.MultiIndex.from_arrays([[], []])

        for ds in self.data_sources.values():
            df_size = ds.df_size or 1
            index = index.append(
                pd.MultiIndex.from_arrays([[ds.uid] * df_size, np.arange(df_size)])
            )

        return pd.Series(index=index)

    def get_summarized_metrics(
        self,
        groupby_variable_1: pd.Series,
        groupby_variable_2: pd.Series | None = None,
        data_filter: pd.Series | None = None,
        metrics: list[Metric] | None = None,
    ):
        """
        Summarizes metrics based on the provided groupby variables and filter.
        Parameters:
        - groupby_variable_1 (pd.Series): The first variable to group by.
        - groupby_variable_2 (pd.Series, optional): The second variable to group by. Defaults to None.
        - filter (pd.Series, optional): A boolean mask to filter the data. Defaults to None.
        - metrics (list[METRIC], optional): A list of metrics to summarize. Defaults to None.
        Returns:
        - pd.DataFrame: A DataFrame containing the summarized metrics.
        """

        if metrics is None:
            raise ValueError("At least one metric must be provided.")

        # Creating a filter if not provided
        if data_filter is None:
            empty_column = self.load_column()
            data_filter = pd.Series(
                [True] * empty_column.size, index=empty_column.index
            )

        # Creating the base DataFrame with the groupby variables
        base_df = pd.DataFrame({
            groupby_variable_1.name: groupby_variable_1,
        })
        groupby_variables = [groupby_variable_1.name]

        if groupby_variable_2 is not None:
            base_df[groupby_variable_2.name] = groupby_variable_2
            groupby_variables.append(groupby_variable_2.name)

        # Loading all required columns for the metrics
        used_columns = set()
        for metric in metrics:
            used_columns.update(metric.used_columns)

        columns_to_load = list(set(used_columns) - set(base_df.columns))

        loaded_data = self.load_columns(columns_to_load)

        base_df = pd.concat([base_df, loaded_data], axis=1)

        # Applying the filter to the base DataFrame
        filtered_df = base_df[data_filter].copy()

        # Grouping the DataFrame by the specified variables and aggregating the metrics
        groupby_obj = filtered_df.groupby(groupby_variables, observed=False)
        all_index = groupby_obj.count().index
        metric_results: list[pd.Series] = []

        for metric in metrics:
            result: pd.Series = groupby_obj.apply(metric.calculate).reindex(all_index)  # type: ignore
            result.name = metric.name
            metric_results.append(result)

        grouped_df = pd.concat(metric_results, axis=1)

        return grouped_df


__all__ = ["DataRepository"]
