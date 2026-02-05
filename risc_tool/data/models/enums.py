import typing as t
from enum import EnumMeta, IntEnum, StrEnum


class RowIndex(IntEnum):
    TOTAL = -1


class Colors(StrEnum):
    F_TABLE_TOTAL_LIGHT = "#000000"
    B_TABLE_TOTAL_LIGHT = "#EEF1F5"
    F_TABLE_TOTAL_DARK = "#FFFFFF"
    B_TABLE_TOTAL_DARK = "#292B34"


class StrEnumMeta(EnumMeta):
    def __contains__(cls, item: t.Any):
        try:
            cls(item)
        except ValueError:
            return False
        return True


class DefaultMetricNames(StrEnum, metaclass=StrEnumMeta):
    VOLUME = "Volume"
    UNT_BAD_RATE = "Annl. # Bad Rate"
    DLR_BAD_RATE = "Annl. $ Bad Rate"


class VariableType(StrEnum, metaclass=StrEnumMeta):
    NUMERICAL = "Numerical"
    CATEGORICAL = "Categorical"

    @property
    def other(self) -> "VariableType":
        return (
            VariableType.NUMERICAL
            if self == VariableType.CATEGORICAL
            else VariableType.CATEGORICAL
        )


class IterationType(StrEnum, metaclass=StrEnumMeta):
    SINGLE = "single"
    DOUBLE = "double"


class LossRateTypes(StrEnum):
    DLR = "$ Bad Rate"
    ULR = "# Bad Rate"


class RSDetCol(StrEnum):
    SELECTED = "Selected"
    ORIG_INDEX = "Original Index"
    RISK_SEGMENT = "Risk Segment"
    LOWER_RATE = "Lower Bad Rate"
    UPPER_RATE = "Upper Bad Rate"
    BG_COLOR = "Background Color"
    FONT_COLOR = "Font Color"
    MAF_ULR = "Maturity Adjustment Factor (ULR)"
    MAF_DLR = "Maturity Adjustment Factor (DLR)"


class RangeColumn(StrEnum):
    SELECTED = RSDetCol.SELECTED
    RISK_SEGMENT = RSDetCol.RISK_SEGMENT
    GROUPS = "Groups"
    LOWER_BOUND = "Lower Bound"
    UPPER_BOUND = "Upper Bound"
    CATEGORIES = "Categories"
    RISK_SCALAR_FACTOR_DLR = "Risk Scalar Factor (DLR)"
    RISK_SCALAR_FACTOR_ULR = "Risk Scalar Factor (ULR)"


class GridColumn(StrEnum):
    PREV_RISK_SEGMENT = f"Previous {RSDetCol.RISK_SEGMENT}"
    CURR_RISK_SEGMENT = f"Current {RSDetCol.RISK_SEGMENT}"
    GROUP_INDEX = "Group Index"


class ScalarTableColumn(StrEnum):
    RISK_SEGMENT = "Risk Segment"
    MAF = "Maturity Adjustment Factor"
    RISK_SCALAR_FACTOR = "Risk Scalar Factor"


class DataExplorerTabName(StrEnum, metaclass=StrEnumMeta):
    IV_ANALYSIS = "IV Analysis"


class SummaryPageTabName(StrEnum, metaclass=StrEnumMeta):
    OVERVIEW = "Overview"
    COMPARISON = "Comparison"
    PIVOT = "Pivot"


class ExportTabName(StrEnum, metaclass=StrEnumMeta):
    SESSION_ARCHIVE = "Session Archive"
    PYTHON_CODE = "Python Code"
    SAS_CODE = "SAS Code"


class Signature(StrEnum):
    # base
    CHANGE_TRACKER = "CHANGE_TRACKER"
    CHANGE_NOTIFIER = "CHANGE_NOTIFIER"
    BASE_REPOSITORY = "BASE_REPOSITORY"

    # Repositories
    DATA_REPOSITORY = "DATA_REPOSITORY"
    METRIC_REPOSITORY = "METRIC_REPOSITORY"
    FILTER_REPOSITORY = "FILTER_REPOSITORY"
    SCALAR_REPOSITORY = "SCALAR_REPOSITORY"
    OPTION_REPOSITORY = "OPTION_REPOSITORY"
    ITERATION_REPOSITORY = "ITERATION_REPOSITORY"

    # ViewModels
    DATA_IMPORTER_VIEW_MODEL = "DATA_IMPORTER_VIEW_MODEL"
    DATA_EXPLORER_VIEW_MODEL = "DATA_EXPLORER_VIEW_MODEL"
    VARIABLE_SELECTOR_VIEW_MODEL = "VARIABLE_SELECTOR_VIEW_MODEL"
    METRIC_VIEW_MODEL = "METRIC_VIEW_MODEL"
    FILTER_VIEW_MODEL = "FILTER_VIEW_MODEL"
    CONFIG_VIEW_MODEL = "CONFIG_VIEW_MODEL"
    ITERATION_VIEW_MODEL = "ITERATION_VIEW_MODEL"
    SUMMARY_VIEW_MODEL = "SUMMARY_VIEW_MODEL"
    EXPORT_VIEW_MODEL = "EXPORT_VIEW_MODEL"
    SESSION_ARCHIVE_VIEW_MODEL = "SESSION_ARCHIVE_VIEW_MODEL"


__all__ = [
    "DefaultMetricNames",
    "GridColumn",
    "IterationType",
    "LossRateTypes",
    "RangeColumn",
    "RSDetCol",
    "VariableType",
    "ScalarTableColumn",
    "DataExplorerTabName",
    "RowIndex",
    "Signature",
]
