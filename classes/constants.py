from enum import EnumMeta, StrEnum
import typing as t

import numpy as np
import pandas as pd

from classes.singleton import Singleton


class RTDetCol(StrEnum):
    SELECTED = "Selected"
    ORIG_INDEX = "Original Index"
    RISK_TIER = "Risk Tier"
    LOWER_RATE = "Lower Loss Rate"
    UPPER_RATE = "Upper Loss Rate"
    BG_COLOR = "Background Color"
    FONT_COLOR = "Font Color"
    MAF_ULR = "Maturity Adjustment Factor (ULR)"
    MAF_DLR = "Maturity Adjustment Factor (DLR)"


class LossRateTypes(StrEnum):
    DLR = "$ Loss Rate"
    ULR = "# Loss Rate"


class ScalarTableColumn(StrEnum):
    RISK_TIER = "Risk Tier"
    MAF = "Maturity Adjustment Factor"
    RISK_SCALAR_FACTOR = "Risk Scalar Factor"


class StrEnumMeta(EnumMeta):
    def __contains__(cls, item):
        try:
            cls(item)
        except ValueError:
            return False
        return True


class VariableType(StrEnum, metaclass=StrEnumMeta):
    NUMERICAL = "numerical"
    CATEGORICAL = "categorical"


class IterationType(StrEnum, metaclass=StrEnumMeta):
    SINGLE = "single"
    DOUBLE = "double"


class Metric(StrEnum):
    VOLUME: str = "Volume"
    ANNL_WO_BAL_PCT: str = "$ Annualized Write off %"
    ANNL_WO_COUNT_PCT: str = "# Annualized Write off %"
    AVG_BAL: str = "$ Average Balance"
    WO_COUNT: str = "# Write off Count"
    WO_COUNT_PCT: str = "# Write off %"
    WO_BAL: str = "$ Write off Balance"
    WO_BAL_PCT: str = "$ Write off %"


class MetricTableColumn(StrEnum):
    METRIC = "Metric"
    ORDER = "Order"
    SHOWING = "Showing"


class RangeColumn(StrEnum):
    SELECTED = RTDetCol.SELECTED
    RISK_TIER = RTDetCol.RISK_TIER
    GROUPS = "Groups"
    LOWER_BOUND = "Lower Bound"
    UPPER_BOUND = "Upper Bound"
    CATEGORIES = "Categories"
    RISK_SCALAR_FACTOR_DLR = "Risk Scalar Factor (DLR)"
    RISK_SCALAR_FACTOR_ULR = "Risk Scalar Factor (ULR)"


class GridColumn(StrEnum):
    PREV_RISK_TIER = f"Previous {RTDetCol.RISK_TIER}"
    CURR_RISK_TIER = f"Current {RTDetCol.RISK_TIER}"
    GROUP_INDEX = "Group Index"


class IterationMetadata(t.TypedDict):
    editable: bool
    metrics: pd.DataFrame
    scalars_enabled: bool
    split_view_enabled: bool


class DefaultOptions(Singleton):
    def __init__(self):
        self._risk_tier_details = pd.DataFrame(
            [
                ["1A", 0, 0.02, "#3D8F3D", "#FFFFFF", 1.3, 1.3],
                ["1B", 0, 0.02, "#3D8F3D", "#FFFFFF", 1.3, 1.3],
                ["2A", 0.02, 0.04, "#7D9438", "#FFFFFF", 1.15, 1.15],
                ["2B", 0.02, 0.04, "#7D9438", "#FFFFFF", 1.15, 1.15],
                ["3A", 0.04, 0.07, "#948238", "#FFFFFF", 1.0, 1.0],
                ["3B", 0.04, 0.07, "#948238", "#FFFFFF", 1.0, 1.0],
                ["4A", 0.07, 0.1, "#8F663D", "#FFFFFF", 0.9, 0.9],
                ["4B", 0.07, 0.1, "#8F663D", "#FFFFFF", 0.9, 0.9],
                ["5A", 0.1, np.inf, "#8F3D3D", "#FFFFFF", 0.8, 0.8],
                ["5B", 0.1, np.inf, "#8F3D3D", "#FFFFFF", 0.8, 0.8],
            ],
            columns=[
                RTDetCol.RISK_TIER,
                RTDetCol.LOWER_RATE,
                RTDetCol.UPPER_RATE,
                RTDetCol.BG_COLOR,
                RTDetCol.FONT_COLOR,
                RTDetCol.MAF_DLR,
                RTDetCol.MAF_ULR,
            ],
        ).rename_axis(index=RTDetCol.ORIG_INDEX)
        self._max_iteration_depth = 10
        self._default_metrics = pd.DataFrame({
            MetricTableColumn.METRIC: list(Metric),
            MetricTableColumn.ORDER: [i for i, _ in enumerate(Metric)],
            MetricTableColumn.SHOWING: [i < 3 for i, _ in enumerate(Metric)],
        })

    @property
    def risk_tier_details(self) -> pd.DataFrame:
        return self._risk_tier_details.copy()

    @property
    def max_iteration_depth(self) -> int:
        return self._max_iteration_depth

    @property
    def default_metrics(self) -> pd.DataFrame:
        return self._default_metrics.copy()

    @property
    def default_iteation_metadata(self) -> IterationMetadata:
        return {
            "editable": True,
            "metrics": self.default_metrics,
            "scalars_enabled": True,
            "split_view_enabled": False,
        }


__all__ = [
    "DefaultOptions",
    "RTDetCol",
    "LossRateTypes",
    "ScalarTableColumn",
]
