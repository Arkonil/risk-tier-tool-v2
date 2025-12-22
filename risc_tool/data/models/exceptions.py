import textwrap

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


class InvalidFilterError(Exception):
    """
    Custom exception for invalid filter queries.
    """

    def __init__(self, query: str, reason: str):
        self.query = query
        self.reason = reason

    def __str__(self) -> str:
        return textwrap.dedent(f"""
            **InvalidFilterError**: {self.reason}
            Query: `{self.query}`
        """).replace("\n", "\n\n")


def format_error(error: Exception) -> str:
    if isinstance(error, SyntaxError):
        error_lines = [
            f"**SyntaxError**: {error.msg}",
            f"**Line**: {error.lineno}",
        ]

        if error.text:
            error_lines.append(error.text.rstrip())

        if error.offset is not None and error.end_offset is not None:
            error_lines.append(
                f"{' ' * (error.offset - 1)}{'^' * (error.end_offset - error.offset + 1)}"
            )

        return "\n\n".join(error_lines)

    if isinstance(error, ValueError):
        return textwrap.dedent(f"""
            **ValueError**: {error}
        """).replace("\n", "\n\n")

    return str(error)
