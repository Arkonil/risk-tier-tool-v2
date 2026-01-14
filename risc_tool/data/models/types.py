import typing as t
from uuid import UUID

import pandas as pd
from pandas.io.formats.style import Styler

from risc_tool.data.models.enums import Signature
from risc_tool.data.models.sentinel_int import SentinelInt

ChangeID = tuple[Signature, UUID]
ChangeIDs = set[ChangeID]
CallbackID = UUID
Callback = t.Callable[[ChangeIDs], bool]


class DataSourceID(SentinelInt):
    TEMPORARY: "DataSourceID"
    EMPTY: "DataSourceID"


DataSourceID.TEMPORARY = DataSourceID(-1, name="TEMPORARY")
DataSourceID.EMPTY = DataSourceID(-2, name="EMPTY")


class MetricID(SentinelInt):
    TEMPORARY: "MetricID"
    VOLUME: "MetricID"
    UNT_BAD_RATE: "MetricID"
    DLR_BAD_RATE: "MetricID"
    EMPTY: "MetricID"


MetricID.TEMPORARY = MetricID(-1, name="TEMPORARY")
MetricID.VOLUME = MetricID(-2, name="VOLUME")
MetricID.UNT_BAD_RATE = MetricID(-3, name="UNT_BAD_RATE")
MetricID.DLR_BAD_RATE = MetricID(-4, name="DLR_BAD_RATE")
MetricID.EMPTY = MetricID(-5, name="EMPTY")


class FilterID(SentinelInt):
    TEMPORARY: "FilterID"
    EMPTY: "FilterID"


FilterID.TEMPORARY = FilterID(-1, name="TEMPORARY")
FilterID.EMPTY = FilterID(-2, name="EMPTY")


class IterationID(SentinelInt):
    INVALID: "IterationID"


IterationID.INVALID = IterationID(-1, name="INVALID")


class GridEditorViewComponents(t.TypedDict):
    styler: Styler
    lower_bound_pos: int | None
    upper_bound_pos: int | None
    categories_pos: int | None
    risk_segment_grid_col_pos: list[int]
    grid_options: list[str]
    show_prev_iter_details: bool


class GridMetricSummary(t.TypedDict):
    metric_grid: pd.DataFrame
    metric_name: str
    data_source_names: list[str]


class GridMetricView(t.TypedDict):
    metric_styler: Styler

    metric_name: str
    data_source_names: list[str]
