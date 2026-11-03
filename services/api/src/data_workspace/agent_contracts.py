"""Governed single-table Agent contracts; model outputs never contain executable SQL/tools."""
from datetime import date
from typing import Literal
from pydantic import Field,model_validator
from .contracts import Contract
from .model_provider import ModelResponseDiagnostics
from .warehouse.aggregate_contract import AggregateRequest,AggregateResult

class AgentTimeRange(Contract):
    start: date
    end_exclusive: date
    @model_validator(mode='after')
    def valid(self):
        if self.start>=self.end_exclusive:raise ValueError('date range invalid')
        return self
class ModelQueryPlan(Contract):
    metric_id: str | None = Field(default=None,max_length=40)
    dimensions: list[str] = Field(default_factory=list,max_length=3)
    time_range: AgentTimeRange | None = None
    needs_clarification: Literal['none','metric','time','dimension','unsupported'] = 'none'
class AgentRequest(Contract):
    conversation_id: str = Field(default='',max_length=36)
    request_id: str = Field(pattern=r'^[a-f0-9-]{36}$')
    question: str = Field(min_length=1,max_length=1600)
    model_ref: str = Field(min_length=1,max_length=100)
    semantic_version_id: str = Field(pattern=r'^[a-f0-9-]{36}$')
    selected_source_refs: list[str] = Field(min_length=1,max_length=8)
    @model_validator(mode='after')
    def distinct_sources(self):
        if len(set(self.selected_source_refs))!=len(self.selected_source_refs):raise ValueError('duplicate sources')
        return self
    accept_model_egress: Literal[True]
    @model_validator(mode='before')
    @classmethod
    def explicit_consent(cls,value):
        if isinstance(value,dict) and value.get('accept_model_egress') is not True:raise ValueError('explicit consent required')
        return value
class AgentConfirm(Contract):
    plan_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    execution_generation: str
    confirm_execute: Literal[True]
    @model_validator(mode='before')
    @classmethod
    def explicit_confirm(cls,value):
        if isinstance(value,dict) and value.get('confirm_execute') is not True:raise ValueError('explicit confirmation required')
        return value
class AgentTask(Contract):
    conversation_id: str = ''
    id: str
    request_id: str
    execution_generation: str
    phase: Literal['PLANNING','NEEDS_CLARIFICATION','AWAITING_CONFIRMATION','VALIDATING','EXECUTING','CHECKING','SUCCEEDED','FAILED','UNKNOWN','EXPIRED','CANCELLED']
    model_ref: str
    semantic_version_id: str
    events: list[str] = Field(default_factory=list)
    plan_hash: str | None = None
    plan: AggregateRequest | None = None
    sql: str | None = None
    clarification: str | None = None
    error_code: str | None = None
    model_diagnostics: ModelResponseDiagnostics | None = None
    result: AggregateResult | None = None
    execution_receipt: dict | None = None
    sql_executed: bool = False
    storage: Literal['backend_session_memory'] = 'backend_session_memory'
    cost_mode: Literal['estimated_not_actual'] = 'estimated_not_actual'
    returned_model_id: str | None = None
class AgentTasks(Contract):
    tasks: list[AgentTask]
class AgentCapabilities(Contract):
    implementation: Literal['langgraph_governed_single_table_v1'] = 'langgraph_governed_single_table_v1'
    available: bool
    query_protocol: Literal['workspace_aggregate_v1'] = 'workspace_aggregate_v1'
    supported_sources: list[str] = ['local_file']
    join_available: Literal[False] = False
    durable_tasks: Literal[False] = False
