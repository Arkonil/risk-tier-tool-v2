import pathlib
import typing as t

from pydantic import UUID4, BaseModel, ConfigDict

from risc_tool.data.models.enums import IterationType, LossRateTypes, VariableType
from risc_tool.data.models.types import (
    DataSourceID,
    FilterID,
    IteraionView,
    IterationID,
    MetricID,
)


# Base
class BaseJSON(BaseModel):
    model_config = ConfigDict(validate_assignment=True, ser_json_inf_nan="null")


# Common
class DataFrameTightJSON(BaseJSON):
    index: list[int] | list[str]
    columns: list[int] | list[str]
    index_names: list[str | None]
    column_names: list[str | None]
    data: list[list[str | float | None]]


# Data
class DataSourceJSON(BaseJSON):
    uid: DataSourceID
    label: str
    filepath: pathlib.Path
    read_mode: t.Literal["CSV", "EXCEL"]
    delimiter: str
    sheet_name: str
    header_row: int
    sample_row_count: int
    df_size: int | None


class DataRepositoryJSON(BaseJSON):
    data_sources: list[DataSourceJSON]


# Filter
class FilterJSON(BaseJSON):
    uid: FilterID
    name: str
    query: str
    used_columns: list[str]


class FilterRepositoryJSON(BaseJSON):
    filters: list[FilterJSON]


# Metric
class MetricJSON(BaseJSON):
    uid: MetricID
    name: str
    query: str
    data_source_ids: list[DataSourceID]
    used_columns: list[str]
    use_thousand_sep: bool
    is_percentage: bool
    decimal_places: int
    processed_query: str
    placeholder_map: dict[str, str]


class MetricRepositoryJSON(BaseJSON):
    metrics: list[MetricJSON]
    var_unt_bad: str | None
    var_dlr_bad: str | None
    var_avg_bal: str | None
    current_rate_mob: int
    lifetime_rate_mob: int
    data_source_ids: list[DataSourceID]


# Scalar
class ScalarJSON(BaseJSON):
    loss_rate_type: LossRateTypes
    current_rate: float
    lifetime_rate: float


class ScalarRepositoryJSON(BaseJSON):
    scalars: dict[LossRateTypes, ScalarJSON]


# Options
class OptionsRepositoryJSON(BaseJSON):
    risk_segment_details: DataFrameTightJSON
    max_iteration_depth: int
    max_categorical_unique: int


# Iterations
class IterationJSON(BaseJSON):
    var_type: VariableType
    iter_type: IterationType
    uid: IterationID
    name: str
    variable_name: str
    groups: dict[int, tuple[float, float]] | dict[int, set[str | float]]
    default_groups: dict[int, tuple[float, float]] | dict[int, set[str | float]]

    # Single
    risk_segment_details: DataFrameTightJSON | None = None

    # Double
    groups_mask: dict[int, bool] | None = None
    risk_segment_grid: DataFrameTightJSON | None = None
    default_risk_segment_grid: DataFrameTightJSON | None = None


class IterationGraphJSON(BaseJSON):
    connections: dict[IterationID, list[IterationID]]


class IterationRepositoryJSON(BaseJSON):
    iterations: list[IterationJSON]
    graph: IterationGraphJSON


class IteraionViewStatusJSON(BaseJSON):
    view: IteraionView = "graph"
    iteration_id: IterationID | None = None


class IterationMetadataJSON(BaseJSON):
    editable: bool
    scalars_enabled: bool
    split_view_enabled: bool
    show_prev_iter_details: bool
    loss_rate_type: LossRateTypes
    initial_filter_ids: list[FilterID]
    current_filter_ids: list[FilterID]
    metric_ids: list[MetricID]


class IterationsViewModelJSON(BaseJSON):
    view_status: IteraionViewStatusJSON
    metadata: dict[IterationID, IterationMetadataJSON]


# Summary
class SummaryViewModelJSON(BaseJSON):
    # Overview
    ov_metric_ids: list[MetricID]
    ov_filter_ids: list[FilterID]
    ov_selected_iteration_id: IterationID | None
    ov_selected_iteration_default: bool

    # Comparison Tab Data
    cv_metric_ids: list[MetricID]
    cv_filter_ids: list[FilterID]
    cv_scalars_enabled: bool
    cv_selected_iterations: dict[UUID4, tuple[IterationID, bool]]
    cv_view_mode: t.Literal["grid", "list"]


# Session Archive Repository
class SessionArchiveRepositoryJSON(BaseJSON):
    data_repository: DataRepositoryJSON
    filter_repository: FilterRepositoryJSON
    metric_repository: MetricRepositoryJSON
    scalar_repository: ScalarRepositoryJSON
    options_repository: OptionsRepositoryJSON
    iteration_repository: IterationRepositoryJSON
    iterations_view_model: IterationsViewModelJSON
    summary_view_model: SummaryViewModelJSON
