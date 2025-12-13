from pydantic import BaseModel, ConfigDict


class Completion(BaseModel):
    model_config = ConfigDict(serialize_by_alias=True, validate_by_alias=True)

    caption: str
    value: str
    meta: str
    name: str
    score: int
