RISK_TIERS = list(map(str, range(1, 6)))
SUB_RISK_TIERS = list(sorted(
    [f'{rt}A' for rt in RISK_TIERS] + [f'{rt}B' for rt in RISK_TIERS], reverse=True))
