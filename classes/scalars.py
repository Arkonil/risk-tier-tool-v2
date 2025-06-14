from dataclasses import dataclass

import numpy as np
import pandas as pd

from classes.constants import LossRateTypes, ScalarTableColumn


@dataclass
class Scalar:
    loss_rate_type: LossRateTypes
    current_rate: float = np.nan
    lifetime_rate: float = np.nan

    @property
    def portfolio_scalar(self) -> float:
        return self.lifetime_rate / self.current_rate

    def get_risk_scalar_factor(self, maf: pd.Series) -> pd.Series:
        risk_scalar = maf * self.portfolio_scalar
        risk_scalar[risk_scalar < 1] = 1
        risk_scalar.name = ScalarTableColumn.RISK_SCALAR_FACTOR
        return risk_scalar
