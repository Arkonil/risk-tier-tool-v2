from enum import Enum

import pandas as pd

class Metric(Enum):
    VOLUME: str = "Volume"
    ANNL_WO_BAL_PCT: str = "$ Annualized Write off %"
    ANNL_WO_COUNT_PCT: str = "# Annualized Write off %"
    AVG_BAL: str = "$ Average Balance"
    WO_COUNT: str = "# Write off Count"
    WO_COUNT_PCT: str = "# Write off %"
    WO_BAL: str = "$ Write off Balance"
    WO_BAL_PCT: str = "$ Write off %"

class Names(Enum):
    LOWER_BOUND: str = "Lower Bound"
    UPPER_BOUND: str = "Upper Bound"
    CATEGORIES: str = "Categories"
    GROUPS: str = "Groups"
    RISK_TIER: str = "Risk Tier"
    RISK_TIER_VALUE: str = "Risk Tier Value"
    GROUP_INDEX: str = "Group Index"
    MATURITY_ADJUSTMENT_FACTOR: str = "Maturity Adjustment Factor"
    RISK_SCALAR_FACTOR: str = "Risk Scalar Factor"

RISK_TIERS = list(map(str, range(1, 6)))
SUB_RISK_TIERS = pd.Series(sorted(
    [f'{rt}A' for rt in RISK_TIERS] + [f'{rt}B' for rt in RISK_TIERS], reverse=False), name=Names.RISK_TIER.value)
SUB_RT_INV_MAP = pd.Series(SUB_RISK_TIERS.index.values, index=SUB_RISK_TIERS)

color_map = {
    "5B": "hsl(0, 40%, 40%)",
    "5A": "hsl(0, 40%, 40%)",
    "4B": "hsl(30, 40%, 40%)",
    "4A": "hsl(30, 40%, 40%)",
    "3B": "hsl(48, 45%, 40%)",
    "3A": "hsl(48, 45%, 40%)",
    "2B": "hsl(75, 45%, 40%)",
    "2A": "hsl(75, 45%, 40%)",
    "1B": "hsl(120, 40%, 40%)",
    "1A": "hsl(120, 40%, 40%)",
}
