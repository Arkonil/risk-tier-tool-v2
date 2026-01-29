import pathlib
import typing as t
from collections import OrderedDict
from uuid import uuid4

import numpy as np
import pandas as pd
from pydantic import ValidationError

from risc_tool.data.models.data_config import DataConfig
from risc_tool.data.models.data_source import DataSource
from risc_tool.data.models.enums import Signature, VariableType
from risc_tool.data.models.exceptions import DataImportError, SampleDataNotLoadedError
from risc_tool.data.models.metric import Metric
from risc_tool.data.models.types import ChangeIDs, DataSourceID
from risc_tool.data.repositories.base import BaseRepository


class DataRepository(BaseRepository):
    """
    This class stores the data and all reading attributes
    """

    @property
    def _signature(self) -> Signature:
        return Signature.DATA_REPOSITORY

    def __init__(self) -> None:
        super().__init__()

        self.data_sources: OrderedDict[DataSourceID, DataSource] = OrderedDict()
        self.data_config: DataConfig = DataConfig()

    def on_dependency_update(self, change_ids: ChangeIDs):
        return

    @property
    def index(self):
        if not self.sample_loaded:
            raise ValueError("Data not loaded")

        indices: list[pd.Series] = []
        keys: list[DataSourceID] = []

        for ds_id, ds in self.data_sources.items():
            indices.append(pd.Series(index=ds.index))
            keys.append(ds_id)

        return pd.concat(indices, keys=keys).index

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

    def get_completions(self, *, columns: list[str] | None = None, common: bool = True):
        return self.data_config.get_completions(columns=columns, common=common)

    def available_columns(
        self, data_source_ids: list[DataSourceID]
    ) -> set[tuple[str, VariableType]]:
        if not self.sample_loaded or not data_source_ids:
            return set()

        columns = set.intersection(*[
            ds.column_types
            for ds in self.data_sources.values()
            if ds.uid in data_source_ids
        ])

        return columns

    def get_sample_df(self, data_source_ids: list[DataSourceID]):
        if not self.sample_loaded:
            raise SampleDataNotLoadedError()

        if not data_source_ids:
            return pd.DataFrame()

        sample_dfs = [
            ds._sample_df
            for ds in self.data_sources.values()
            if ds.uid in data_source_ids
        ]

        if not sample_dfs:
            return pd.DataFrame()

        return pd.concat(sample_dfs, axis=0)

    def refresh_data_config(self):
        self.data_config.refresh(
            common_columns=self._common_columns, all_columns=self._all_columns
        )

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
                uid=DataSourceID.TEMPORARY,
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

        data_source.uid = DataSourceID(
            self._get_new_id(current_ids=self.data_sources.keys())
        )
        self.data_sources[data_source.uid] = data_source
        data_source.load_sample()

        self.refresh_data_config()
        self.notify_subscribers()

        return data_source

    def update_data_source(
        self,
        data_source_id: DataSourceID,
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
        self.refresh_data_config()

        # Notify subscribers
        self.notify_subscribers()

        return new_data_source

    def delete_data_source(self, data_source_id: DataSourceID):
        del self.data_sources[data_source_id]

        self.refresh_data_config()

        self.notify_subscribers()

    def get_data_source_mask(self, data_source_ids: list[DataSourceID]) -> pd.Series:
        mask = pd.Series(False, index=self.index)
        mask.loc[data_source_ids] = True
        return mask

    def load_columns(
        self,
        column_names: list[str],
        column_types: list[VariableType] | None = None,
        data_source_ids: list[DataSourceID] | None = None,
    ):
        if not self.sample_loaded:
            raise SampleDataNotLoadedError()

        if column_types is None:
            column_types = [VariableType.NUMERICAL for _ in column_names]

        if len(column_names) != len(column_types):
            raise ValueError("column_names and column_types must have the same length")

        dataframes: list[pd.DataFrame] = []
        keys: list[int] = []

        for ds in self.data_sources.values():
            dataframes.append(ds.load_columns(column_names, column_types))
            keys.append(ds.uid)

        final_df = pd.concat(dataframes, axis=0, keys=keys)

        if data_source_ids is None:
            data_source_ids = list(self.data_sources.keys())

        data_source_mask = self.get_data_source_mask(data_source_ids)
        final_df.loc[~data_source_mask, :] = pd.NA

        final_df = final_df.convert_dtypes()

        for col in final_df.columns:
            if final_df[col].dtype == "object":
                final_df[col] = final_df[col].astype("string")

        return final_df

    def load_column(
        self,
        column_name: str | None = None,
        column_type: VariableType = VariableType.NUMERICAL,
        data_source_ids: list[DataSourceID] | None = None,
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
        - metrics list[METRIC]: A list of metrics to summarize. Defaults to None.
        Returns:
        - pd.DataFrame: A DataFrame containing the summarized metrics.
        """

        if metrics is None:
            metrics = []

        # Creating a filter if not provided
        if data_filter is None:
            data_filter = pd.Series(
                [True] * groupby_variable_1.size, index=groupby_variable_1.index
            )

        # Creating the base DataFrame with the groupby variables
        var_name_1 = uuid4().hex
        base_df = pd.DataFrame({
            var_name_1: groupby_variable_1,
        })
        groupby_variables = [var_name_1]
        orig_names = [groupby_variable_1.name]

        if groupby_variable_2 is not None:
            var_name_2 = uuid4().hex
            base_df[var_name_2] = groupby_variable_2
            groupby_variables.append(var_name_2)
            orig_names.append(groupby_variable_2.name)

        all_index = base_df.groupby(groupby_variables, observed=False).count().index

        metric_results: list[pd.Series] = []

        for metric in metrics:
            used_columns = metric.used_columns
            columns_to_load = list(set(used_columns) - set(base_df.columns))

            loaded_data = self.load_columns(
                columns_to_load, data_source_ids=metric.data_source_ids
            )

            metric_data = pd.concat([base_df, loaded_data], axis=1)

            filtered_data = metric_data[
                data_filter & self.get_data_source_mask(metric.data_source_ids)
            ]

            metric_result = (
                filtered_data.groupby(groupby_variables, observed=False)
                .apply(metric.calculate)
                .reindex(all_index)
            )
            metric_result.name = metric.pretty_name
            metric_results.append(metric_result)

        if metric_results:
            result_df = pd.concat(metric_results, axis=1)
        else:
            result_df = pd.DataFrame(index=all_index)

        result_df.rename_axis(mapper=orig_names, axis=0, inplace=True)

        return result_df


__all__ = ["DataRepository"]
