import numpy as np
import pandas as pd
from pydantic import BaseModel

from risc_tool.data.models.enums import LossRateTypes, ScalarTableColumn


class Scalar(BaseModel):
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
