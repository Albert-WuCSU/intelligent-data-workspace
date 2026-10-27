from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[str, Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9_.:-]+$")]

class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")

class TimeRange(Contract):
    start: date
    end_exclusive: date

    @model_validator(mode="after")
    def valid_range(self):
        if self.end_exclusive <= self.start:
            raise ValueError("end_exclusive must be after start")
        return self

class MetricRef(Contract):
    id: Identifier
    version: Identifier

class MetricTarget(Contract):
    kind: Literal["metric"]
    metric_refs: list[MetricRef] = Field(min_length=1, max_length=20)

class TableTarget(Contract):
    kind: Literal["table"]
    datasource_id: Identifier
    full_table_name: Annotated[str, Field(min_length=3, max_length=400, pattern=r"^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+$")]
    columns: list[Identifier] = Field(min_length=1, max_length=100)

class Filter(Contract):
    field: Identifier
    operator: Literal["eq", "in", "gte", "lte"]
    values: list[str | int | float | bool] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def arity(self):
        if self.operator != "in" and len(self.values) != 1:
            raise ValueError("single-value operator requires one value")
        return self

class QuerySpec(Contract):
    schema_version: Literal["1.0"] = "1.0"
    target: Annotated[MetricTarget | TableTarget, Field(discriminator="kind")]
    time_range: TimeRange
    timezone: str = Field(min_length=1, max_length=100)
    dimensions: list[Identifier] = Field(default_factory=list, max_length=30)
    filters: list[Filter] = Field(default_factory=list, max_length=50)

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("unknown timezone") from None
        return value

    @field_validator("dimensions")
    @classmethod
    def unique_dimensions(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("duplicate dimensions")
        return value

class AuthContext(Contract):
    principal_id: Identifier
    tenant_id: Identifier
    mode: Literal["development", "production"]

class ErrorEnvelope(Contract):
    code: str
    safe_message: str
    trace_id: str

class TaskStatus(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class Task(Contract):
    schema_version: Literal["1.0"] = "1.0"
    task_id: str
    tenant_id: Identifier
    principal_id: Identifier
    query_spec: QuerySpec
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    trace_id: str
    error: ErrorEnvelope | None = None

    def transition(self, status: TaskStatus, *, error: ErrorEnvelope | None = None):
        allowed = {
            TaskStatus.CREATED: {TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED},
            TaskStatus.RUNNING: {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED},
        }
        if status not in allowed.get(self.status, set()):
            raise ValueError("invalid task transition")
        if status == TaskStatus.FAILED and error is None:
            raise ValueError("failed task requires error")
        if status != TaskStatus.FAILED and error is not None:
            raise ValueError("error only allowed on failed task")
        self.status, self.error = status, error
        self.updated_at = datetime.now(timezone.utc)

class FieldSchema(Contract):
    name: Identifier
    type: Literal["string", "integer", "decimal", "boolean", "date", "datetime"]
    unit: str | None = None

class Provenance(Contract):
    source_class: Literal["DIRECT_CERTIFIED", "COMPUTED", "INFERRED", "UPLOADED_DATA"]
    query_id: str | None = None
    domain_pack_version: str | None = None

class Quality(Contract):
    status: Literal["PASS", "WARN", "FAIL"]
    limitations: list[str] = Field(default_factory=list)

class DatasetAsset(Contract):
    schema_version: Literal["1.0"] = "1.0"
    asset_id: Identifier
    asset_version: Identifier
    tenant_id: Identifier
    data_ref: Annotated[str, Field(pattern=r"^protected://[A-Za-z0-9_./:-]+$")]
    fields: list[FieldSchema] = Field(min_length=1)
    row_count: int = Field(ge=0)
    grain: str = Field(min_length=1)
    provenance: Provenance
    quality: Quality
    policy_ref: Identifier

    @model_validator(mode="after")
    def protected_scope(self):
        if not self.data_ref.startswith(f"protected://{self.tenant_id}/"):
            raise ValueError("data reference must be within asset tenant")
        if ".." in self.data_ref.split("/"):
            raise ValueError("invalid data reference")
        if len({f.name for f in self.fields}) != len(self.fields):
            raise ValueError("duplicate field names")
        return self

class ConnectorCapability(Contract):
    connector_id: Identifier
    configured: bool
    sql_dialect: str | None = None
    metadata: Literal["supported", "unsupported", "unknown"] = "unknown"
    asynchronous: Literal["supported", "unsupported", "unknown"] = "unknown"
    cancel: Literal["supported", "unsupported", "unknown"] = "unknown"
    query_cost: Literal["supported", "unsupported", "unknown"] = "unknown"
    column_acl: Literal["supported", "unsupported", "unknown"] = "unknown"

class SessionResponse(Contract):
    identity: AuthContext
    storage: Literal["memory_development"]
    warning: str

class ModuleCapability(Contract):
    id: str
    label: str
    available: bool
    milestone: str

class CapabilitiesResponse(Contract):
    modules: list[ModuleCapability]
    connectors: list[ConnectorCapability]

class ValidationResponse(Contract):
    valid: Literal[True] = True
    query_spec: QuerySpec
    execution_available: Literal[False] = False
    note: str
