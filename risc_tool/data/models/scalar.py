import numpy as np
import pandas as pd

from risc_tool.data.models.enums import LossRateTypes, ScalarTableColumn
from risc_tool.data.models.json_models import ScalarJSON


class Scalar:
    def __init__(
        self,
        loss_rate_type: LossRateTypes,
        current_rate: float = np.nan,
        lifetime_rate: float = np.nan,
    ):
        self.loss_rate_type: LossRateTypes = loss_rate_type
        self.current_rate: float = current_rate
        self.lifetime_rate: float = lifetime_rate

    def to_dict(self) -> ScalarJSON:
        return ScalarJSON(
            loss_rate_type=self.loss_rate_type,
            current_rate=self.current_rate,
            lifetime_rate=self.lifetime_rate,
        )

    @classmethod
    def from_dict(cls, data: ScalarJSON) -> "Scalar":
        return cls(
            loss_rate_type=data.loss_rate_type,
            current_rate=data.current_rate,
            lifetime_rate=data.lifetime_rate,
        )

    @property
    def portfolio_scalar(self) -> float:
        return self.lifetime_rate / self.current_rate

    def get_risk_scalar_factor(self, maf: pd.Series) -> pd.Series:
        risk_scalar = maf * self.portfolio_scalar
        risk_scalar[risk_scalar < 1] = 1
        risk_scalar.name = ScalarTableColumn.RISK_SCALAR_FACTOR
        return risk_scalar
