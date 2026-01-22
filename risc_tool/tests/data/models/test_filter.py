import pandas as pd
import pytest

from risc_tool.data.models.exceptions import InvalidFilterError
from risc_tool.data.models.filter import Filter
from risc_tool.data.models.types import FilterID


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "A": [1, 2, 3, 4, 5],
        "B": ["x", "y", "x", "y", "x"],
        "C": [10.0, 20.0, 30.0, 40.0, 50.0],
    })


def test_filter_validation_simple(sample_df):
    f = Filter(uid=FilterID(1), name="Test", query="A > 2")
    f.validate_query(available_columns=sample_df.columns.tolist())
    assert f.used_columns == ["A"]


def test_filter_validation_backticks(sample_df):
    df_space = sample_df.rename(columns={"A": "Column A"})
    f = Filter(uid=FilterID(1), name="Test", query="`Column A` > 2")
    f.validate_query(available_columns=df_space.columns.tolist())
    assert f.used_columns == ["Column A"]


def test_filter_validation_invalid_syntax():
    f = Filter(uid=FilterID(1), name="Test", query="A > ")
    with pytest.raises(
        SyntaxError
    ):  # or InvalidFilterError depending on AST parse result?
        # ast.parse raises SyntaxError if invalid python
        f.validate_query()


def test_filter_validation_assignment_not_allowed():
    f = Filter(uid=FilterID(1), name="Test", query="A = 2")
    with pytest.raises(InvalidFilterError, match="Assignments"):
        f.validate_query()


def test_filter_validation_non_boolean():
    f = Filter(uid=FilterID(1), name="Test", query="A + 2")
    with pytest.raises(InvalidFilterError, match="not appear to be boolean"):
        f.validate_query()


def test_filter_validation_missing_column(sample_df):
    f = Filter(uid=FilterID(1), name="Test", query="D > 5")
    with pytest.raises(InvalidFilterError, match="not found"):
        f.validate_query(available_columns=sample_df.columns.tolist())


def test_create_mask(sample_df):
    f = Filter(uid=FilterID(1), name="Test", query="A > 2")
    f.create_mask(sample_df)
    assert f.mask is not None
    assert f.mask.tolist() == [False, False, True, True, True]


def test_duplicate():
    f = Filter(uid=FilterID(1), name="Test", query="A > 2")
    f.used_columns = ["A"]
    f2 = f.duplicate(uid=FilterID(2), name="Copy")
    assert f2.uid == FilterID(2)
    assert f2.name == "Copy"
    assert f2.query == "A > 2"
    assert f2.used_columns == ["A"]
