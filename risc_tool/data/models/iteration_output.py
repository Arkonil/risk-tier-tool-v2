import pandas as pd
from pydantic import BaseModel, ConfigDict


class IterationOutput(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias=True,
        validate_by_alias=True,
        arbitrary_types_allowed=True,
    )

    risk_segment_column: pd.Series
    errors: list[str]
    warnings: list[str]
    invalid_groups: list[int]


__all__ = ["IterationOutput"]
