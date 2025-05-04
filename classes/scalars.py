import typing as t
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Scalar:
    period_options: t.ClassVar[t.List[float]] = [1.0, 1.5, 2.0, 2.5, 3.0]
    
    loss_rate_type: t.Literal["dlr", "ulr"]
    period1: float = 2
    period2: float = 3
    period1_rate: float = np.nan
    period2_rate: float = np.nan
    maturity_adjustment_factor: pd.Series = None

    def __post_init__(self) -> None:

        if self.period1 not in self.period_options:
            raise ValueError(
                f"Expected one of {', '.join(self.period_options)}. Got {self.period1} instead.")

        if self.period2 not in self.period_options:
            raise ValueError(
                f"Expected one of {', '.join(self.period_options)}. Got {self.period2} instead.")

        if self.maturity_adjustment_factor is None:
            self.maturity_adjustment_factor = pd.Series({
                1: 130,
                2: 115,
                3: 100,
                4: 90,
                5: 80
            }) / 100

    @property
    def portfolio_scalar(self) -> float:
        if self.period1 <= self.period2:
            return self.period2_rate / self.period1_rate
        else:
            return self.period1_rate / self.period2_rate

    @property
    def risk_scalar_factor(self):
        risk_scalar = self.maturity_adjustment_factor * self.portfolio_scalar
        risk_scalar[risk_scalar < 1] = 1
        return risk_scalar
