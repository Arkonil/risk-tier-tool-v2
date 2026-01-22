import pandas as pd
import pytest

from risc_tool.data.models.metric import (
    Metric,
    Volume,
    element_wise_sum,
)
from risc_tool.data.models.types import MetricID


@pytest.fixture
def sample_data():
    return pd.DataFrame({
        "vol": [1, 1, 1],
        "bad": [0, 1, 0],
        "bal": [100, 200, 100],
    })


def test_metric_validation_simple(sample_data):
    m = Metric(uid=MetricID(1), name="M1", query="vol.sum()")
    m.validate_query(sample_data)
    assert m.used_columns == ["vol"]


def test_metric_validation_invalid_function(sample_data):
    m = Metric(uid=MetricID(1), name="M1", query="import os")
    with pytest.raises(SyntaxError):
        m.validate_query(sample_data)

    m2 = Metric(uid=MetricID(1), name="M1", query="os.system('ls')")
    # Validator checks allowed names
    with pytest.raises(ValueError, match="not appear to be a scalar"):
        # AST validator might reject it or is_result_scalar fails
        m2.validate_query(sample_data)


def test_metric_calculation(sample_data):
    m = Metric(uid=MetricID(1), name="M1", query="vol.sum()")
    m.validate_query(sample_data)
    res = m.calculate(sample_data)
    assert res == 3.0


def test_metric_custom_functions(sample_data):
    # Testing our custom element_wise_sum etc if reachable via query
    # "sum(vol)" -> scalar sum?
    # Metric logic adds scope['sum'] = element_wise_sum
    # element_wise_sum delegates to np.sum if not series op, or series sum?
    # But "sum(pd.Series)" -> element_wise_sum(series) -> _prepare -> list of series -> concat.sum(axis=1) -> element wise!
    # Wait, "vol.sum()" uses pandas method. "sum(vol, vol)" uses custom function?

    # Testing `sum(vol, bad)` -> element wise sum of columns
    m = Metric(uid=MetricID(1), name="M1", query="sum(vol, bad).sum()")
    m.validate_query(sample_data)
    # element_wise_sum(vol, bad) -> Series([1+0, 1+1, 1+0]) = [1, 2, 1]
    # .sum() -> 4
    res = m.calculate(sample_data)
    assert res == 4.0


def test_volume_metric(sample_data):
    v = Volume("vol", [])
    assert v.query == "`vol`.size"
    v.validate_query(sample_data)
    res = v.calculate(sample_data)
    assert res == 3.0


def test_element_wise_helpers():
    s1 = pd.Series([1, 2])
    s2 = pd.Series([3, 4])

    # Sum
    res_sum = element_wise_sum(s1, s2)
    pd.testing.assert_series_equal(res_sum, pd.Series([4, 6]))

    # Mixed scalar
    res_mix = element_wise_sum(s1, 10)
    pd.testing.assert_series_equal(res_mix, pd.Series([11, 12]))


def test_metric_format():
    m = Metric(
        uid=MetricID(1), name="M", query="1", is_percentage=True, decimal_places=1
    )
    # calculate() multiplies by 100 if is_percentage is True.
    # format() expects the value to be compatible with the format string.
    # {val:.1f}% -> takes val, formats to 1 decimal, adds %.
    # So if we want 12.3%, we must pass 12.345.
    assert m.format(12.345) == "12.3%"

    m2 = Metric(
        uid=MetricID(1), name="M", query="1", use_thousand_sep=True, decimal_places=0
    )
    assert m2.format(1234.56) == "1,235"
