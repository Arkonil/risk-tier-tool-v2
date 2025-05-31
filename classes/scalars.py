import typing as t
from dataclasses import dataclass

import numpy as np
import pandas as pd

from classes.common import Names

@dataclass
class Scalar:
    loss_rate_type: t.Literal["dlr", "ulr"]
    current_rate: float = np.nan
    lifetime_rate: float = np.nan
    _maturity_adjustment_factor: pd.Series = None

    def __post_init__(self) -> None:
        l = [130, 115, 100, 90, 80]

        if self._maturity_adjustment_factor is None:
            self._maturity_adjustment_factor = pd.Series([i for i in l for _ in range(2)]) / 100
            self._maturity_adjustment_factor.name = Names.MATURITY_ADJUSTMENT_FACTOR.value

    @property
    def maturity_adjustment_factor(self) -> pd.Series:
        return self._maturity_adjustment_factor

    @maturity_adjustment_factor.setter
    def maturity_adjustment_factor(self, value: pd.Series) -> None:
        if isinstance(value, pd.Series):
            self._maturity_adjustment_factor = value
            self._maturity_adjustment_factor.name = Names.MATURITY_ADJUSTMENT_FACTOR.value
        else:
            raise TypeError("Maturity adjustment factor must be a Series")

    @property
    def portfolio_scalar(self) -> float:
        return self.lifetime_rate / self.current_rate

    @property
    def risk_scalar_factor(self) -> pd.Series:
        risk_scalar = self.maturity_adjustment_factor * self.portfolio_scalar
        risk_scalar[risk_scalar < 1] = 1
        risk_scalar.name = Names.RISK_SCALAR_FACTOR.value
        return risk_scalar
