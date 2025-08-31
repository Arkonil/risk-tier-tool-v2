from enum import EnumMeta, StrEnum
import typing as t

import numpy as np
import pandas as pd

from classes.singleton import Singleton

TAB = "    "


class RTDetCol(StrEnum):
    SELECTED = "Selected"
    ORIG_INDEX = "Original Index"
    RISK_TIER = "Risk Tier"
    LOWER_RATE = "Lower Bad Rate"
    UPPER_RATE = "Upper Bad Rate"
    BG_COLOR = "Background Color"
    FONT_COLOR = "Font Color"
    MAF_ULR = "Maturity Adjustment Factor (ULR)"
    MAF_DLR = "Maturity Adjustment Factor (DLR)"


class LossRateTypes(StrEnum):
    DLR = "$ Bad Rate"
    ULR = "# Bad Rate"


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
    NUMERICAL = "Numerical"
    CATEGORICAL = "Categorical"


class IterationType(StrEnum, metaclass=StrEnumMeta):
    SINGLE = "single"
    DOUBLE = "double"


class DefaultMetrics(StrEnum, metaclass=StrEnumMeta):
    VOLUME = "Volume"
    UNT_BAD_RATE = "Annl. # Bad Rate"
    DLR_BAD_RATE = "Annl. $ Bad Rate"


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
    metrics: list[str]
    scalars_enabled: bool
    split_view_enabled: bool
    loss_rate_type: LossRateTypes
    filters: set[str]


IterationMetadataKeys = t.Literal[
    "editable",
    "metrics",
    "scalars_enabled",
    "split_view_enabled",
    "loss_rate_type",
    "filters",
]


class Completion(t.TypedDict):
    caption: str
    value: str
    meta: str
    name: str
    score: int


class AssetPath(StrEnum):
    QUERY_REFERENCE = "app/assets/filter_query_reference.md"
    RT_ICON = "app/assets/rt-icon.svg"
    RT_LOGO_LIGHT = "app/assets/rt-logo-light.svg"
    RT_LOGO_DARK = "app/assets/rt-logo-dark.svg"
    NO_DATA_ERROR_ICON = "app/assets/no-data-error.svg"
    NO_FILTER_ICON = "app/assets/no-filter.svg"
    NO_METRIC_ICON = "app/assets/no-metric.svg"
    STYLESHEET = "app/assets/style.css"
    ARROW_RIGHT = "app/assets/arrow-right.svg"
    SESSION_EXPORT_DOC = "app/assets/session_export_doc.md"


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
        ).rename_axis(index=RTDetCol.ORIG_INDEX.value)
        self._risk_tier_details.columns = self._risk_tier_details.columns.map(str)

        self._max_iteration_depth = 10
        self._default_metrics = [
            DefaultMetrics.VOLUME,
            DefaultMetrics.UNT_BAD_RATE,
            DefaultMetrics.DLR_BAD_RATE,
        ]

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
            "split_view_enabled": True,
            "loss_rate_type": LossRateTypes.DLR,
        }


__all__ = [
    "DefaultOptions",
    "RTDetCol",
    "LossRateTypes",
    "ScalarTableColumn",
]
