import pandas as pd

RISK_TIERS = list(map(str, range(1, 6)))
SUB_RISK_TIERS = pd.Series(sorted(
    [f'{rt}A' for rt in RISK_TIERS] + [f'{rt}B' for rt in RISK_TIERS], reverse=False), name='risk_tier')
