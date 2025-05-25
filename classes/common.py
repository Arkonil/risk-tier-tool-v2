import pandas as pd

class Names:
    VOLUME = "Volume"
    WO_BAL = "$ Write off Balance"
    WO_COUNT = "# Write off Count"
    AVG_BAL = "$ Average Balance"
    WO_BAL_PCT = "$ Write off %"
    WO_COUNT_PCT = "# Write off %"
    LOWER_BOUND = "Lower Bound"
    UPPER_BOUND = "Upper Bound"
    CATEGORIES = "Categories"
    GROUPS = "Groups"
    RISK_TIER = "Risk Tier"
    RISK_TIER_VALUE = "Risk Tier Value"
    GROUP_INDEX = "Group Index"

RISK_TIERS = list(map(str, range(1, 6)))
SUB_RISK_TIERS = pd.Series(sorted(
    [f'{rt}A' for rt in RISK_TIERS] + [f'{rt}B' for rt in RISK_TIERS], reverse=False), name=Names.RISK_TIER)
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
