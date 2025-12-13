import pathlib
import typing as t

import pandas as pd


def import_data(
    filepath: pathlib.Path,
    read_mode: t.Literal["CSV", "EXCEL"] = "CSV",
    delimiter: str = ",",
    sheet_name: str = "0",
    header_row: int = 0,
    nrows: int | None = None,
    usecols: list[str] | list[int] | None = None,
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
            filepath,
            delimiter=delimiter,
            header=header_row,
            nrows=nrows,
            usecols=usecols,
        )
    elif read_mode == "EXCEL":
        try:
            df = pd.read_excel(
                filepath,
                sheet_name=sheet_name,
                header=header_row,
                nrows=nrows,
                usecols=usecols,
            )
        except ValueError as error:
            if sheet_name.isdigit():
                df = pd.read_excel(
                    filepath,
                    sheet_name=int(sheet_name),
                    header=header_row,
                    nrows=nrows,
                    usecols=usecols,
                )
            else:
                raise error
    else:
        raise ValueError(
            f"'read_mode' must be either 'CSV' or 'EXCEL'. {read_mode} was given."
        )

    return df


__all__ = ["import_data"]
