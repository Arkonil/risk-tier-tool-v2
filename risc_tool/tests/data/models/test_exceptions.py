from unittest.mock import MagicMock

from risc_tool.data.models.exceptions import (
    DataImportError,
    InvalidFilterError,
    MissingColumnError,
    SampleDataNotLoadedError,
    VariableNotNumericError,
    format_error,
)


def test_missing_column_error():
    err = MissingColumnError("col1")
    assert "Column 'col1' not found" in str(err)


def test_variable_not_numeric_error():
    err = VariableNotNumericError("var1", "str")
    assert "Variable 'var1' is not numeric" in str(err)
    assert "Found type: str" in str(err)


def test_data_import_error():
    ds_mock = MagicMock()
    err = DataImportError("failed", data_source=ds_mock)
    assert err.message == "failed"
    assert err.data_source == ds_mock


def test_sample_data_not_loaded_error():
    err = SampleDataNotLoadedError()
    assert "Sample data is not loaded" in str(err)


def test_invalid_filter_error_str():
    err = InvalidFilterError(query="x > 5", reason="syntax error")
    s = str(err)
    assert "**InvalidFilterError**: syntax error" in s
    assert "Query: `x > 5`" in s


def test_format_error_syntax_error():
    se = SyntaxError("invalid syntax", ("file.py", 10, 5, "code line"))
    fmt = format_error(se)
    assert "**SyntaxError**: invalid syntax" in fmt
    assert "**Line**: 10" in fmt
    assert "code line" in fmt


def test_format_error_value_error():
    ve = ValueError("wrong value")
    fmt = format_error(ve)
    assert "**ValueError**: wrong value" in fmt


def test_format_error_generic():
    e = Exception("generic")
    assert format_error(e) == "generic"
