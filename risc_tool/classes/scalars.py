from dataclasses import dataclass
import typing as t

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

    def to_dict(self) -> dict[str, t.Any]:
        """Serializes the Scalar object to a dictionary."""
        return {
            "loss_rate_type": self.loss_rate_type.value,
            "current_rate": self.current_rate,
            "lifetime_rate": self.lifetime_rate,
        }

    @classmethod
    def from_dict(cls, data: dict[str, t.Any]) -> "Scalar":
        """Creates a Scalar object from a dictionary."""
        return cls(
            loss_rate_type=LossRateTypes(data["loss_rate_type"]),
            current_rate=data.get("current_rate", np.nan),
            lifetime_rate=data.get("lifetime_rate", np.nan),
        )
