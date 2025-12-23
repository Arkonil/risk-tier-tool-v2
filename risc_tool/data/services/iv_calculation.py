import numpy as np
import pandas as pd


def calculate_iv(variable: pd.Series, target: pd.Series) -> float:
    """
    Calculates the Information Value (IV) for a given variable against a binary target.

    Args:
        variable (pd.Series): The independent variable (predictor).
        target (pd.Series): The binary target variable (dependent).

    Returns:
        float: The Information Value (IV).
    """
    if not pd.api.types.is_numeric_dtype(target) or not target.isin([0, 1]).all():
        raise ValueError("Target variable must be binary (0 or 1).")

    if pd.api.types.is_numeric_dtype(variable):
        variable = pd.qcut(variable, q=20, duplicates="drop")

    # Create a DataFrame for convenience
    df = pd.DataFrame({"variable": variable, "target": target}).dropna()

    if df.empty:
        return 0.0

    # Calculate counts for good and bad
    total_good = df["target"].value_counts().get(0, 0)
    total_bad = df["target"].value_counts().get(1, 0)

    if total_good == 0 or total_bad == 0:
        return 0.0  # IV is undefined or 0 if one class is missing

    # Group by the variable and calculate counts
    grouped = df.groupby("variable", observed=True)["target"].agg(
        good_count=lambda x: (x == 0).sum(),
        bad_count=lambda x: (x == 1).sum(),
    )

    # Calculate % of Good and % of Bad
    grouped["pct_good"] = grouped["good_count"] / total_good
    grouped["pct_bad"] = grouped["bad_count"] / total_bad

    # Handle cases where pct_good or pct_bad might be zero to avoid log(0)
    # Add a small epsilon to avoid division by zero in WOE calculation
    epsilon = 1e-6
    grouped["pct_good"] = np.maximum(grouped["pct_good"], epsilon)
    grouped["pct_bad"] = np.maximum(grouped["pct_bad"], epsilon)

    # Calculate Weight of Evidence (WOE)
    grouped["woe"] = np.log(grouped["pct_good"] / grouped["pct_bad"])

    # Calculate Information Value (IV) for each group
    grouped["iv"] = (grouped["pct_good"] - grouped["pct_bad"]) * grouped["woe"]

    # Sum up the IVs for the final result
    iv_total = grouped["iv"].sum()

    return iv_total
