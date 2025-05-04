import pathlib
import typing as t

import pandas as pd

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
        self.raw_csv_lines: t.List[str] = []
        self.df: pd.DataFrame | None = None
        
        self.var_app_status: str | None = None
        self.var_app_status_accepted: set[str] = set()
        self.var_app_status_declined: set[str] = set()
        self.var_unt_wrt_off: str | None = None
        self.var_dlr_wrt_off: str | None = None
        self.var_avg_bal: str | None = None
        self.var_revenue: str | None = None
        self.mob: int = 12
        
        self.metadata: t.Union[Metadata, None] = None
        
    @property
    def var_app_status_values(self) -> set[str]:
        return self.var_app_status_accepted.union(self.var_app_status_declined)
    
    def all_variable_selected(self) -> bool:
        return all([
            self.var_app_status is not None,
            self.var_unt_wrt_off is not None,
            self.var_dlr_wrt_off is not None,
            self.var_avg_bal is not None,
            self.var_revenue is not None,
            self.mob is not None,
        ])
        
    def get_col_pos(self, col_name: str) -> int:
        if col_name is None or col_name not in self.sample_df.columns:
            return None
        return self.sample_df.columns.get_loc(col_name)

    def validate_read_config(self, filepath: pathlib.Path, read_mode: t.Literal["CSV", "EXCEL"]) -> t.Tuple[bool, str]:
        if not filepath:
            return
        
        if not filepath.is_file():
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
        nrows: t.Union[int, None] = None,
        usecols: t.Callable[[str], bool] = None,
    ) -> pd.DataFrame:
        """
        This function reads data from a file into a pandas DataFrame based on the specified parameters.

        Parameters:
        - filepath (str): The path to the file to be read.
        - read_mode (typing.Literal["CSV", "EXCEL"]): The mode in which the file should be read.
        - delimiter (str): The delimiter used in CSV files.
        - sheet_name (typing.Union[str, int]): The name or index of the sheet to be read in Excel files.
        - header (int): The row index to use as the column names.
        - nrows (typing.Union[int, None], optional): The number of rows to read from the file. Default is None, which means all rows will be read.
        - usecols (typing.Callable[[str], bool], optional): A function that takes a column name and returns True if the column should be included, False otherwise. Default is None, which means all columns will be read.

        Returns:
        pd.DataFrame: The DataFrame containing the data read from the file.
        """
        
        if read_mode == "CSV":
            df = pd.read_csv(filepath, delimiter=delimiter, header=header_row, nrows=nrows, usecols=usecols).convert_dtypes()
        elif read_mode == "EXCEL":
            try:
                df = pd.read_excel(filepath, sheet_name=sheet_name, header=header_row, nrows=nrows, usecols=usecols).convert_dtypes()
            except ValueError as error:
                if sheet_name.isdigit():
                    df = pd.read_excel(filepath, sheet_name=int(sheet_name), header=header_row, nrows=nrows, usecols=usecols).convert_dtypes()
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
        
        self.filepath = filepath
        self.read_mode = read_mode
        self.delimiter = delimiter if delimiter is not None else self.delimiter
        self.sheet_name = sheet_name if sheet_name is not None else self.sheet_name
        self.header_row = header_row
        self.sample_row_count = nrows if nrows is not None else self.sample_row_count
        
    def load_column(self, column_name) -> pd.Series:
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
        
        self.df[column_name] = column
        return column
    