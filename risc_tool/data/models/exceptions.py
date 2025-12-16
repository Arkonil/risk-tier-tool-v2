from risc_tool.data.models.data_source import DataSource


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
