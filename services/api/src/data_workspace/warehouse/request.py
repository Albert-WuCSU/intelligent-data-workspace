"""Read-only table navigation request. No implicit dates or filter semantics."""
from pydantic import BaseModel, ConfigDict, Field, model_validator

class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    table: str = Field(min_length=1,max_length=160)
    columns: list[str] = Field(default_factory=list,max_length=100)
    limit: int = Field(default=100,ge=1,le=100)

    @model_validator(mode="after")
    def unique(self):
        if len(set(self.columns)) != len(self.columns):
            raise ValueError("duplicate columns")
        return self
