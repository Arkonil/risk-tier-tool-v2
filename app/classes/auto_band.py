from enum import StrEnum

import numpy as np
import pandas as pd

from classes.constants import LossRateTypes, RTDetCol, RangeColumn
from classes.scalars import Scalar


class DataColumns(StrEnum):
    VARIABLE = "Variable"
    NUMERATOR = "Numerators"
    DENOMINATOR = "Denominators"
    RATIO = "Ratio"
    VOLUME = "Volume"
    DLR_WRT_OFF = "$ Write Off"
    DLR_WRT_OFF_PCT = "$ Write Off %"
    UNT_WRT_OFF = "# Write Off"
    UNT_WRT_OFF_PCT = "# Write Off %"
    AVG_BAL = "Avg Balance"


def does_high_value_implies_high_risk(
    variable: pd.Series,
    numerators: pd.Series,
    denominators: pd.Series,
) -> bool:
    if len(variable) != len(numerators) or len(variable) != len(denominators):
        raise ValueError(
            f"Variable (length={len(variable)}),"
            f" Numerators (length={len(numerators)}),"
            f" and Denominators (length={len(denominators)}) must be the same length"
        )

    data = pd.DataFrame({
        DataColumns.VARIABLE: variable,
        DataColumns.NUMERATOR: numerators,
        DataColumns.DENOMINATOR: denominators,
    })

    mtc = (
        data.groupby(DataColumns.VARIABLE, observed=False)[
            [DataColumns.NUMERATOR, DataColumns.DENOMINATOR]
        ]
        .sum()
        .sort_index()
    )

    mtc[DataColumns.RATIO] = mtc[DataColumns.NUMERATOR] / mtc[DataColumns.DENOMINATOR]

    # hv_imp_lr = High Value of the variable implies Low risk
    x = np.nan_to_num(mtc.index)  # variable
    w = np.nan_to_num(mtc[DataColumns.RATIO])  # weights
    w /= np.sum(w)  # normalize weights

    m1 = np.sum(x * w)  # 1st raw moment
    m2 = np.sum(x * x * w)  # 2nd raw moment
    m3 = np.sum(x * x * x * w)  # 3rd raw moment

    u3 = m3 - 3 * m2 * m1 + 2 * m1 * m1 * m1  # 3rd central moment
    hv_imp_hr = u3 < 0  # Negatiavely skewed <=> High value implies high risk

    return hv_imp_hr


def create_auto_numeric_bands(
    variable: pd.Series,
    risk_tier_details: pd.DataFrame,
    loss_rate_type: LossRateTypes,
    numerators: pd.Series,
    denominators: pd.Series,
    hv_imp_hr: bool,
) -> pd.DataFrame:
    transformed_variable = not hv_imp_hr
    if transformed_variable:
        variable = -variable

    data = pd.DataFrame({
        DataColumns.VARIABLE: variable,
        DataColumns.NUMERATOR: numerators,
        DataColumns.DENOMINATOR: denominators,
    })

    grouped_data = (
        data.groupby(DataColumns.VARIABLE, observed=False)[
            [DataColumns.NUMERATOR, DataColumns.DENOMINATOR]
        ]
        .sum()
        .sort_index()
    )

    grouped_data[DataColumns.RATIO] = (
        grouped_data[DataColumns.NUMERATOR] / grouped_data[DataColumns.DENOMINATOR]
    )

    groups = pd.DataFrame(
        columns=[RangeColumn.LOWER_BOUND, RangeColumn.UPPER_BOUND],
        index=risk_tier_details.index,
    )

    if len(grouped_data) == 0:
        groups[RangeColumn.LOWER_BOUND] = -np.inf
        groups[RangeColumn.UPPER_BOUND] = np.inf
        return groups

    # negating a small positive number as intervals are left open & right closed
    delta = 1

    current_lower_bound = grouped_data.index[0] - delta
    last_value = current_lower_bound

    if loss_rate_type == LossRateTypes.DLR:
        rsf_column = RangeColumn.RISK_SCALAR_FACTOR_DLR
    else:
        rsf_column = RangeColumn.RISK_SCALAR_FACTOR_ULR

    for index, risk_tier_row in risk_tier_details.iterrows():
        upper_rate = risk_tier_row[RTDetCol.UPPER_RATE]
        rsf = risk_tier_row[rsf_column]

        mtc_mask = pd.Series(pd.NA, index=grouped_data.index, dtype="boolean")
        mtc_temp = grouped_data.copy()

        for _ in range(100):
            # Forward Pass
            if len(mtc_temp) == 0:
                break

            cumm_numerator = mtc_temp[DataColumns.NUMERATOR].cumsum()
            cumm_denominator = mtc_temp[DataColumns.DENOMINATOR].cumsum()
            cumm_loss_rates = (cumm_numerator / cumm_denominator) * rsf

            mask = (cumm_loss_rates < upper_rate).cummin()

            mtc_mask.loc[mask[~mask].index] = False

            mtc_temp = mtc_temp[mask]

            # Backward Pass
            if len(mtc_temp) == 0:
                break

            cumm_numerator = (
                mtc_temp[DataColumns.NUMERATOR].iloc[::-1].cumsum().iloc[::-1]
            )
            cumm_denominator = (
                mtc_temp[DataColumns.DENOMINATOR].iloc[::-1].cumsum().iloc[::-1]
            )
            cumm_loss_rates = (cumm_numerator / cumm_denominator) * rsf

            mask = (cumm_loss_rates < upper_rate).cummin()

            mtc_mask.loc[mask[mask].index] = True

            mtc_temp = mtc_temp[~mask]

        mtc_mask = mtc_mask.fillna(False)

        if len(grouped_data[mtc_mask]) > 0:
            last_value = grouped_data[mtc_mask].index[-1]

        groups.loc[index, RangeColumn.LOWER_BOUND] = current_lower_bound
        groups.loc[index, RangeColumn.UPPER_BOUND] = last_value

        grouped_data = grouped_data[~mtc_mask]
        current_lower_bound = last_value

    groups.loc[groups.index[-1], RangeColumn.UPPER_BOUND] = variable.max()

    if transformed_variable:
        lower_bound = groups[RangeColumn.LOWER_BOUND]
        upper_bound = groups[RangeColumn.UPPER_BOUND]

        groups[RangeColumn.LOWER_BOUND] = -upper_bound - delta
        groups[RangeColumn.UPPER_BOUND] = -lower_bound - delta

    return groups


def create_auto_categorical_bands(
    variable: pd.Series,
    risk_tier_details: pd.DataFrame,
    loss_rate_type: LossRateTypes,
    numerators: pd.Series,
    denominators: pd.Series,
) -> pd.Series:
    data = pd.DataFrame({
        DataColumns.VARIABLE: variable,
        DataColumns.NUMERATOR: numerators,
        DataColumns.DENOMINATOR: denominators,
    })

    mtc = data.groupby(DataColumns.VARIABLE, observed=False)[
        [DataColumns.NUMERATOR, DataColumns.DENOMINATOR]
    ].sum()

    mtc[DataColumns.RATIO] = mtc[DataColumns.NUMERATOR] / mtc[DataColumns.DENOMINATOR]

    mtc.sort_values(DataColumns.RATIO, inplace=True)

    groups = pd.Series(
        index=risk_tier_details.index, name=RangeColumn.GROUPS, dtype=object
    )

    if loss_rate_type == LossRateTypes.DLR:
        rsf_column = RangeColumn.RISK_SCALAR_FACTOR_DLR
    else:
        rsf_column = RangeColumn.RISK_SCALAR_FACTOR_ULR

    for index, risk_tier_row in risk_tier_details.iterrows():
        upper_rate = risk_tier_row[RTDetCol.UPPER_RATE]
        rsf = risk_tier_row[rsf_column]

        mtc[DataColumns.NUMERATOR + "_cum"] = mtc[DataColumns.NUMERATOR].cumsum()
        mtc[DataColumns.DENOMINATOR + "_cum"] = mtc[DataColumns.DENOMINATOR].cumsum()

        cumm_loss_rates = (
            mtc[DataColumns.NUMERATOR + "_cum"] / mtc[DataColumns.DENOMINATOR + "_cum"]
        ) * rsf
        mask = (cumm_loss_rates < upper_rate).cummin()

        groups.loc[index] = set(mtc[mask].index)
        mtc = mtc[~mask]

    groups.iloc[-1] |= set(mtc.index)

    return groups


def create_auto_bands(
    variable: pd.Series,
    mask: pd.Series,
    risk_tier_details: pd.DataFrame,
    loss_rate_type: LossRateTypes,
    mob: int,
    dlr_scalar: Scalar = None,
    ulr_scalar: Scalar = None,
    dlr_wrt_off: pd.Series = None,
    unt_wrt_off: pd.Series = None,
    avg_bal: pd.Series = None,
    hv_imp_hr: bool = None,
):
    if mob is None:
        mob = 12

    if len(variable) != len(mask):
        raise ValueError(
            f"Variable (length={len(variable)}) and Mask (length={len(mask)}) must be the same length"
        )

    if loss_rate_type == LossRateTypes.DLR:
        if dlr_wrt_off is None or avg_bal is None:
            raise ValueError(
                '"$ Write Off" and "Avg Balance" must be provided for DLR loss rate type'
            )

        if dlr_scalar is not None and np.isnan(dlr_scalar.portfolio_scalar):
            raise ValueError('Scalars for "$ Write Off" are not set')

        if len(variable) != len(dlr_wrt_off) or len(variable) != len(avg_bal):
            raise ValueError(
                f"Variable (length={len(variable)}),"
                f" $ Write Off (length={len(dlr_wrt_off)}),"
                f" and Avg Balance (length={len(avg_bal)}) must be the same length"
            )

    if loss_rate_type == LossRateTypes.ULR:
        if unt_wrt_off is None:
            raise ValueError('"# Write Off" must be provided for ULR loss rate type')

        if ulr_scalar is not None and np.isnan(ulr_scalar.portfolio_scalar):
            raise ValueError('Scalars for "# Write Off" are not set')

        if len(variable) != len(unt_wrt_off):
            raise ValueError(
                f"Variable (length={len(variable)})"
                f" and # Write Off (length={len(unt_wrt_off)})"
                f" must be the same length"
            )

    variable_filtered = variable[mask]
    if loss_rate_type == LossRateTypes.DLR:
        dlr_wrt_off_filtered = dlr_wrt_off[mask]
        avg_bal_filtered = avg_bal[mask]

    if loss_rate_type == LossRateTypes.ULR:
        unt_wrt_off_filtered = unt_wrt_off[mask]

    volume = pd.Series(1, index=variable_filtered.index)

    if dlr_scalar is None:
        risk_tier_details[RangeColumn.RISK_SCALAR_FACTOR_DLR] = 1
    else:
        risk_tier_details[RangeColumn.RISK_SCALAR_FACTOR_DLR] = (
            dlr_scalar.get_risk_scalar_factor(risk_tier_details[RTDetCol.MAF_DLR])
        )

    if ulr_scalar is None:
        risk_tier_details[RangeColumn.RISK_SCALAR_FACTOR_ULR] = 1
    else:
        risk_tier_details[RangeColumn.RISK_SCALAR_FACTOR_ULR] = (
            ulr_scalar.get_risk_scalar_factor(risk_tier_details[RTDetCol.MAF_ULR])
        )

    risk_tier_details[RangeColumn.RISK_SCALAR_FACTOR_DLR] *= 12 / mob
    risk_tier_details[RangeColumn.RISK_SCALAR_FACTOR_ULR] *= 12 / mob

    # Adjusting risk_tier_details to get unique rates
    risk_tier_details = risk_tier_details.sort_values([
        RTDetCol.UPPER_RATE,
        RTDetCol.RISK_TIER,
    ])

    max_rate_range = (
        risk_tier_details[RTDetCol.UPPER_RATE]
        .diff()
        .mask(lambda v: np.isinf(v), np.nan)
        .max()
    )

    def create_intermidiate_rates(df):
        minimum = df[RTDetCol.LOWER_RATE].iloc[0]
        maximum = df[RTDetCol.UPPER_RATE].iloc[0]

        if np.isinf(maximum):
            maximum = minimum + max_rate_range

        df[RTDetCol.UPPER_RATE] = np.linspace(minimum, maximum, len(df) + 1)[1:]
        return df

    risk_tier_details = (
        risk_tier_details.groupby(RTDetCol.UPPER_RATE, observed=False)[
            risk_tier_details.columns
        ]
        .apply(create_intermidiate_rates)
        .droplevel(level=0, axis=0)
    )

    if loss_rate_type == LossRateTypes.DLR:
        numerators = dlr_wrt_off_filtered
        denominators = avg_bal_filtered
    else:
        numerators = unt_wrt_off_filtered
        denominators = volume

    if pd.api.types.is_numeric_dtype(variable):
        groups = create_auto_numeric_bands(
            variable=variable_filtered,
            risk_tier_details=risk_tier_details,
            loss_rate_type=loss_rate_type,
            numerators=numerators,
            denominators=denominators,
            hv_imp_hr=hv_imp_hr
            if hv_imp_hr is not None
            else does_high_value_implies_high_risk(
                variable=variable_filtered,
                numerators=numerators,
                denominators=denominators,
            ),
        )
    else:
        groups = create_auto_categorical_bands(
            variable=variable_filtered,
            risk_tier_details=risk_tier_details,
            loss_rate_type=loss_rate_type,
            numerators=numerators,
            denominators=denominators,
        )

    return groups
