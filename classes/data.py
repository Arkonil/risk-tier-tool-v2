import pathlib
import typing as t
import collections.abc

import numpy as np
import pandas as pd

from classes.common import Metric
from classes.metadata import Metadata

class Data:
    """
    This class stores the data and all reading attributes
    """

    def __init__(self):
        self.reset()

    @property
    def sample_loaded(self):
        return self.sample_df is not None

    @property
    def data_loaded(self):
        return self.df is not None

    def reset(self):
        self.filepath: pathlib.Path = None
        self.read_mode: t.Literal["CSV", "EXCEL"] = "CSV"
        self.delimiter: str = ","
        self.sheet_name: str = "0"
        self.header_row: int = 0
        self.sample_row_count: int = 100

        self.sample_df: pd.DataFrame | None = None
        self.raw_csv_lines: list[str] = []
        self.df: pd.DataFrame | None = None
        self.df_size: int | None = None

        self.var_unt_wrt_off: str | None = None
        self.var_dlr_wrt_off: str | None = None
        self.var_avg_bal: str | None = None
        self.current_rate_mob: int = 12
        self.lifetime_rate_mob: int = 36

        self.metadata: Metadata | None = None

    def get_col_pos(self, col_name: str | None) -> int:
        if col_name is None or col_name not in self.sample_df.columns:
            return None
        return self.sample_df.columns.get_loc(col_name)

    def validate_read_config(self, filepath: pathlib.Path, read_mode: t.Literal["CSV", "EXCEL"]) -> tuple[bool, str]:
        if not filepath or not filepath.is_file():
            return False, f"File not found: `{filepath}`"

        if read_mode == 'CSV' and filepath.suffix.lower() != '.csv':
            return False, f"Selected file is not a CSV: `{filepath}`"

        if read_mode == 'EXCEL' and filepath.suffix.lower() not in ['.xlsx', '.xls']:
            return False, f"Selected file is not a EXCEL: `{filepath}`"

        return True, f"Selected File: `{filepath}`"

    def _read_data(
        self,
        filepath: str,
        read_mode: t.Literal["CSV", "EXCEL"],
        delimiter: str,
        sheet_name: str,
        header_row: int,
        nrows: int | None = None,
        usecols: collections.abc.Callable[[str], bool] = None,
    ) -> pd.DataFrame:
        """
        This function reads data from a file into a pandas DataFrame based on the specified parameters.

        Parameters:
        - filepath (str): The path to the file to be read.
        - read_mode (typing.Literal["CSV", "EXCEL"]): The mode in which the file should be read.
        - delimiter (str): The delimiter used in CSV files.
        - sheet_name (typing.Union[str, int]): The name or index of the sheet to be read in Excel files.
        - header (int): The row index to use as the column names.
        - nrows (typing.Union[int, None], optional): The number of rows to read from the file. Default is None,
            which means all rows will be read.
        - usecols (typing.Callable[[str], bool], optional): A function that takes a column name and returns True
            if the column should be included, False otherwise. Default is None, which means all columns will be read.

        Returns:
        pd.DataFrame: The DataFrame containing the data read from the file.
        """

        if read_mode == "CSV":
            df = pd.read_csv(
                filepath, delimiter=delimiter, header=header_row, nrows=nrows, usecols=usecols).convert_dtypes()
        elif read_mode == "EXCEL":
            try:
                df = pd.read_excel(
                    filepath, sheet_name=sheet_name, header=header_row, nrows=nrows, usecols=usecols).convert_dtypes()
            except ValueError as error:
                if sheet_name.isdigit():
                    df = pd.read_excel(
                            filepath,
                            sheet_name=int(sheet_name),
                            header=header_row,
                            nrows=nrows,
                            usecols=usecols
                        ).convert_dtypes()
                else:
                    raise error
        else:
            raise ValueError(f"'read_mode' must be either 'CSV' or 'EXCEL'. {read_mode} was given.")

        return df

    def load_sample(
            self,
            filepath: str,
            read_mode: t.Literal["CSV", "EXCEL"],
            delimiter: str,
            sheet_name: str,
            header_row: int,
            nrows: int) -> None:
        """
        This function loads a sample of data from a specified file into memory. The sample is used to create metadata.

        Parameters:
        - filepath (str): The path to the file to be read.
        - read_mode (typing.Literal["CSV", "EXCEL"]): The mode in which the file should be read.
        - delimiter (str): The delimiter used in CSV files.
        - sheet_name (typing.Union[str, int]): The name or index of the sheet to be read in Excel files.
        - header (int): The row index to use as the column names.
        - nrows (int): The number of rows to read from the file.

        Returns:
        - None: The function modifies the internal state of the Data instance by loading the sample data and metadata.
        """

        if read_mode == 'CSV' and delimiter is None:
            delimiter = ","
        elif read_mode == 'EXCEL' and sheet_name is None:
            sheet_name = "0"

        self.sample_df = self._read_data(
            filepath, read_mode, delimiter, sheet_name, header_row, nrows)

        self.df_size = len(self._read_data(filepath, read_mode, delimiter, sheet_name, header_row, usecols=[0]))

        self.filepath = filepath
        self.read_mode = read_mode
        self.delimiter = delimiter if delimiter is not None else self.delimiter
        self.sheet_name = sheet_name if sheet_name is not None else self.sheet_name
        self.header_row = header_row
        self.sample_row_count = nrows if nrows is not None else self.sample_row_count

    def load_column(self, column_name: str | None) -> pd.Series:
        if column_name is None:
            return pd.Series(index=np.arange(self.df_size))

        if self.df is None:
            self.df = pd.DataFrame()

        if column_name in self.df.columns:
            return self.df[column_name]

        column = self._read_data(
            self.filepath,
            self.read_mode,
            self.delimiter,
            self.sheet_name,
            self.header_row,
            usecols=[column_name]
        )[column_name]

        if not pd.api.types.is_numeric_dtype(column):
            column = column.astype("category")

        self.df[column_name] = column
        return column

    def get_summarized_metrics(
        self,
        groupby_variable_1: pd.Series,
        groupby_variable_2: t.Optional[pd.Series] = None,
        data_filter: t.Optional[pd.Series] = None,
        metrics: t.Optional[list[Metric]] = None):

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

        # Creating a filter if not provided
        if data_filter is None:
            data_filter = pd.Series([True] * self.df_size, index=self.df.index)

        # Creating the base DataFrame with the groupby variables
        base_df = pd.DataFrame({
            groupby_variable_1.name: groupby_variable_1,
        })
        groupby_variables = [groupby_variable_1.name]

        if groupby_variable_2 is not None:
            base_df[groupby_variable_2.name] = groupby_variable_2
            groupby_variables.append(groupby_variable_2.name)

        if metrics is None:
            metrics = []

        metric_dependency_map = {
            Metric.VOLUME: [],
            Metric.WO_COUNT: [],
            Metric.WO_BAL: [],
            Metric.AVG_BAL: [],
            Metric.WO_COUNT_PCT: [Metric.VOLUME, Metric.WO_COUNT],
            Metric.WO_BAL_PCT: [Metric.AVG_BAL, Metric.WO_BAL],
            Metric.ANNL_WO_COUNT_PCT: [Metric.WO_COUNT_PCT],
            Metric.ANNL_WO_BAL_PCT: [Metric.WO_BAL_PCT],
        }

        required_metrics = set()

        def add_metric_and_dependencies(metric):
            if metric in required_metrics:
                return

            required_metrics.add(metric)
            dependencies = metric_dependency_map.get(metric, [])
            for dep in dependencies:
                add_metric_and_dependencies(dep)

        for metric in metrics:
            add_metric_and_dependencies(metric)

        if Metric.VOLUME in required_metrics:
            base_df[Metric.VOLUME.value] = 1

        if Metric.WO_COUNT in required_metrics:
            base_df[Metric.WO_COUNT.value] = self.load_column(self.var_unt_wrt_off)

        if Metric.WO_BAL in required_metrics:
            base_df[Metric.WO_BAL.value] = self.load_column(self.var_dlr_wrt_off)

        if Metric.AVG_BAL in required_metrics:
            base_df[Metric.AVG_BAL.value] = self.load_column(self.var_avg_bal)

        # Applying the filter to the base DataFrame
        filtered_df = base_df[data_filter].copy()

        # Grouping the DataFrame by the specified variables and aggregating the metrics
        grouped_df = filtered_df.groupby(groupby_variables).sum(numeric_only=True)

        if Metric.WO_COUNT_PCT in required_metrics:
            grouped_df[Metric.WO_COUNT_PCT.value] = 100 * grouped_df[Metric.WO_COUNT.value] / grouped_df[Metric.VOLUME.value]

        if Metric.WO_BAL_PCT in required_metrics:
            grouped_df[Metric.WO_BAL_PCT.value] = 100 * grouped_df[Metric.WO_BAL.value] / grouped_df[Metric.AVG_BAL.value]

        if Metric.ANNL_WO_COUNT_PCT in required_metrics:
            grouped_df[Metric.ANNL_WO_COUNT_PCT.value] = grouped_df[Metric.WO_COUNT_PCT.value] / (self.current_rate_mob / 12)

        if Metric.ANNL_WO_BAL_PCT in required_metrics:
            grouped_df[Metric.ANNL_WO_BAL_PCT.value] = grouped_df[Metric.WO_BAL_PCT.value] / (self.current_rate_mob / 12)

        return grouped_df