"""Finite structured semantics, no arbitrary SQL, Python, tool names or execution policy."""
from typing import Literal,Annotated
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from pydantic import Field,field_validator,model_validator
from .contracts import Contract
from .semantic_metadata import SemanticSchema

Name=Annotated[str,Field(min_length=1,max_length=80,pattern=r'\S')]
Column=Annotated[str,Field(min_length=1,max_length=200)]
class TimeMeaning(Contract):
    column: Column
    meaning: Name
    timezone: str = Field(min_length=1,max_length=64)
    @field_validator('timezone')
    @classmethod
    def timezone_exists(cls,v):
        try:ZoneInfo(v)
        except ZoneInfoNotFoundError:raise ValueError('timezone must be an actual IANA timezone')
        return v
class SemanticMetric(Contract):
    id: str = Field(pattern=r'^[a-z][a-z0-9_]{0,39}$')
    name: Name
    aliases: list[Name] = Field(default_factory=list,max_length=8)
    operator: Literal['count_rows','sum','ratio']
    column: Column | None = None
    numerator: Column | None = None
    denominator: Column | None = None
    denominator_zero: Literal['null'] = 'null'
    unit: str = Field(min_length=1,max_length=40,pattern=r'\S')
    additive: bool = Field(strict=True)
    @model_validator(mode='after')
    def components(self):
        if self.operator=='count_rows' and any([self.column,self.numerator,self.denominator]):raise ValueError('count_rows cannot accept extra formula components')
        if self.operator=='sum' and (not self.column or self.numerator or self.denominator):raise ValueError('sum requires only column')
        if self.operator=='ratio' and (not self.numerator or not self.denominator or self.column or self.additive):raise ValueError('ratio requires numerator/denominator and cannot be additive')
        return self
class SemanticDraftInput(Contract):
    pack_id: str | None = Field(default=None,pattern=r'^[a-f0-9-]{36}$')
    expected_version: int = Field(default=0,ge=0,le=500)
    domain: str = Field(pattern=r'^[a-z][a-z0-9_-]{0,39}$')
    name: Name
    owner_note: Name
    source_id: str = Field(pattern=r'^[a-f0-9-]{36}$')
    table_id: str = Field(min_length=1,max_length=100)
    grain: list[Column] = Field(min_length=1,max_length=4)
    grain_note: Name
    time: TimeMeaning | None = None
    metrics: list[SemanticMetric] = Field(min_length=1,max_length=12)
    @field_validator('name','owner_note','grain_note')
    @classmethod
    def nonblank(cls,v):
        if not v.strip():raise ValueError('value cannot be blank')
        return v.strip()
class SemanticIssue(Contract):
    code: Literal['FIELD_MISSING','TYPE_MISMATCH','ALIAS_CONFLICT','METRIC_CONFLICT','GRAIN_DUPLICATE']
    message: str
class SemanticCheck(Contract):
    valid: bool
    issues: list[SemanticIssue]
    schema_snapshot: SemanticSchema
    requires_human_approval: Literal[True] = True
    rows_read: Literal[False] = False
class DraftReceipt(Contract):
    draft_id: str
    pack_id: str
    contract: SemanticDraftInput
    note: str = '语义草稿仅当前后端内存，尚未校验或批准；不会执行SQL。'
class CheckReceipt(Contract):
    draft_id: str
    validation_id: str
    result: SemanticCheck
class PublishInput(Contract):
    draft_id: str = Field(pattern=r'^[a-f0-9-]{36}$')
    validation_id: str = Field(pattern=r'^[a-f0-9-]{36}$')
    request_id: str = Field(pattern=r'^[a-f0-9-]{36}$')
    approve_definition: Literal[True]
    @field_validator('approve_definition',mode='before')
    @classmethod
    def actual_confirmation(cls,v):
        if type(v) is not bool or v is not True:raise ValueError('explicit Boolean approval required')
        return v
class PublishedSemantic(Contract):
    id: str
    pack_id: str
    version: int
    published_at: str
    approved_by: str
    contract: SemanticDraftInput
    schema_snapshot: SemanticSchema
    state: Literal['published_recheck_required','disabled','superseded'] = 'published_recheck_required'
    state_revision: int = 0
    execution_available: Literal[False] = False
class SemanticStateInput(Contract):
    expected_version: int = Field(ge=1,le=500)
    expected_state_revision: int = Field(ge=0)
    enabled: bool = Field(strict=True)

class SemanticList(Contract):
    versions: list[PublishedSemantic]
    note: str = '已发布结构定义可追溯；执行前必须重新核验真实字段。不是企业认证或已执行查询。'
class ResolvedSemantic(Contract):
    version: PublishedSemantic
    mapping_verified: Literal[True] = True
    sql_executed: Literal[False] = False

TEMPORAL=frozenset(('DATE','TIME','TIMETZ','TIMESTAMP','TIMESTAMPTZ','DATETIME','TIMESTAMP_NS','TIMESTAMP_MS','TIMESTAMP_S','TIME WITH TIME ZONE','TIME WITHOUT TIME ZONE','TIMESTAMP WITH TIME ZONE','TIMESTAMP WITHOUT TIME ZONE'))
NUMERIC=frozenset(('INT','INTEGER','INT2','INT4','INT8','TINYINT','SMALLINT','BIGINT','HUGEINT','UHUGEINT','UTINYINT','USMALLINT','UINTEGER','UBIGINT','DECIMAL','NUMERIC','REAL','DOUBLE','DOUBLE PRECISION','FLOAT','FLOAT4','FLOAT8'))
def check_contract(body,schema):
    fields={c.name:c.data_type.upper() for c in schema.columns};issues=[]
    def issue(code,message):issues.append(SemanticIssue(code=code,message=message))
    if len(set(body.grain))!=len(body.grain):issue('GRAIN_DUPLICATE','粒度字段重复，请选择实际唯一粒度字段。')
    for name in body.grain:
        if name not in fields:issue('FIELD_MISSING',f'粒度字段不存在：{name}')
    if body.time:
        if body.time.column not in fields:issue('FIELD_MISSING',f'时间字段不存在：{body.time.column}')
        elif fields[body.time.column].split('(')[0].strip() not in TEMPORAL:issue('TYPE_MISMATCH','时间字段类型不匹配；不会把文本字段自动转换为日期。')
    ids=set();terms={}
    for metric in body.metrics:
        if metric.id in ids:issue('METRIC_CONFLICT',f'指标ID重复：{metric.id}')
        ids.add(metric.id)
        for term in [metric.name,*metric.aliases]:
            key=term.strip().casefold()
            if not key or key in terms:issue('ALIAS_CONFLICT',f'指标名称或别名歧义：{term}')
            terms[key]=metric.id
        for column in [metric.column,metric.numerator,metric.denominator]:
            if column is None:continue
            if column not in fields:issue('FIELD_MISSING',f'指标字段不存在：{column}')
            elif fields[column].split('(')[0].strip() not in NUMERIC:issue('TYPE_MISMATCH',f'聚合字段必须为实际数值类型：{column}')
    return SemanticCheck(valid=not issues,issues=issues,schema_snapshot=schema)
