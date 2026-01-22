import numpy as np
import pandas as pd

from risc_tool.data.models.enums import LossRateTypes, ScalarTableColumn
from risc_tool.data.models.scalar import Scalar


def test_scalar_properties():
    s = Scalar(loss_rate_type=LossRateTypes.DLR, current_rate=0.05, lifetime_rate=0.10)
    assert s.portfolio_scalar == 2.0  # 0.10 / 0.05


def test_scalar_defaults():
    s = Scalar(loss_rate_type=LossRateTypes.ULR)
    assert np.isnan(s.current_rate)
    assert np.isnan(s.lifetime_rate)


def test_get_risk_scalar_factor():
    s = Scalar(
        loss_rate_type=LossRateTypes.DLR, current_rate=0.02, lifetime_rate=0.04
    )  # Factor = 2.0

    maf = pd.Series([0.4, 0.6, 1.0])

    result = s.get_risk_scalar_factor(maf)

    # Expected: maf * 2.0 -> [0.8, 1.2, 2.0]
    # Then clamp < 1 to 1 -> [1.0, 1.2, 2.0]

    expected = pd.Series([1.0, 1.2, 2.0])
    pd.testing.assert_series_equal(result, expected, check_names=False)
    assert result.name == ScalarTableColumn.RISK_SCALAR_FACTOR
