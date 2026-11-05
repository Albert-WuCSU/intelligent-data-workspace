"""Full-input bounded aggregation contract, separate from the accepted preview API."""
from datetime import date,datetime,time,timezone
from typing import Literal
import hashlib,json
from pydantic import Field,model_validator,StrictInt,StrictFloat
from ..contracts import Contract
from ..semantic_contracts import SemanticMetric,NUMERIC,TEMPORAL

class AggregateTime(Contract):
    column: str = Field(min_length=1,max_length=200)
    start: date
    end_exclusive: date
    @model_validator(mode='after')
    def valid(self):
        if self.start>=self.end_exclusive:raise ValueError('invalid time range')
        return self
class AggregateFilter(Contract):
    column: str = Field(min_length=1,max_length=200)
    operator: Literal['eq','in','gte','lt']
    values: list[str|StrictInt|StrictFloat] = Field(min_length=1,max_length=200)
    @model_validator(mode='after')
    def valid(self):
        if self.operator!='in' and len(self.values)!=1:raise ValueError('single value required')
        if any(type(v) is bool for v in self.values):raise ValueError('boolean filter not supported')
        return self
class AggregateRequest(Contract):
    table: str = Field(min_length=1,max_length=100)
    schema_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    metric: SemanticMetric
    grain: list[str] = Field(min_length=1,max_length=4)
    dimensions: list[str] = Field(default_factory=list,max_length=3)
    time_filter: AggregateTime | None = None
    filters: list[AggregateFilter] = Field(default_factory=list,max_length=5)
    @model_validator(mode='after')
    def unique(self):
        if len(set(self.grain))!=len(self.grain) or len(set(self.dimensions))!=len(self.dimensions):raise ValueError('duplicate fields')
        return self
class AggregateResult(Contract):
    source: str
    columns: list[dict]
    rows: list[list]
    input_rows: int
    matched_rows: int
    duplicate_grain_rows: int
    null_grain_rows: int
    null_metric_rows: int
    zero_denominator_groups: int
    null_denominator_groups: int
    returned_row_count: int
    truncated: Literal[False] = False
    full_input_aggregate: Literal[True] = True
    quality: Literal['PASS','WARN']
    unit: str
    sql_executed: Literal[True] = True
    limitations: list[str]

def schema_hash(description):
    return hashlib.sha256(json.dumps([description['table'],[(c['name'],c['type']) for c in description['fields']]],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def quote(v):return '"'+v.replace('"','""')+'"'
def compile_aggregate(body,description):
    from .policy import QueryDenied
    b=AggregateRequest.model_validate(body) if isinstance(body,dict) else body
    if b.schema_hash!=schema_hash(description):raise QueryDenied('schema changed')
    fields={f['name']:f['type'].upper() for f in description['fields']}
    if len(fields)>100 or not set(b.grain+b.dimensions)<=set(fields):raise QueryDenied('field denied')
    m=b.metric
    for c in [m.column,m.numerator,m.denominator]:
        if c is not None and (c not in fields or fields[c].split('(')[0].strip() not in NUMERIC):raise QueryDenied('numeric field denied')
    conditions=[];params=[]
    if b.time_filter:
        t=b.time_filter
        if t.column not in fields or fields[t.column].split('(')[0].strip() not in TEMPORAL or fields[t.column].startswith('TIME') and not fields[t.column].startswith('TIMESTAMP'):raise QueryDenied('date range requires DATE/TIMESTAMP, not time-of-day')
        conditions.append(f'{quote(t.column)} >= ? AND {quote(t.column)} < ?')
        if fields[t.column] in ('TIMESTAMPTZ','TIMESTAMP WITH TIME ZONE'):
            params.extend([datetime.combine(v,time.min,tzinfo=timezone.utc).isoformat() for v in (t.start,t.end_exclusive)])
        else:params.extend([t.start.isoformat(),t.end_exclusive.isoformat()])
    for f in b.filters:
        if f.column not in fields:raise QueryDenied('filter field denied')
        kind=fields[f.column].split('(')[0].strip()
        if kind in NUMERIC:
            if any(type(v) is bool or not isinstance(v,(int,float)) for v in f.values):raise QueryDenied('filter type denied')
        elif kind in TEMPORAL:
            if kind.startswith('TIME') and not kind.startswith('TIMESTAMP'):raise QueryDenied('filter value denied')
            for value in f.values:
                if not isinstance(value,str):raise QueryDenied('filter type denied')
                try:
                    if kind in ('TIMESTAMPTZ','TIMESTAMP WITH TIME ZONE'):
                        parsed=datetime.fromisoformat(value)
                        if parsed.tzinfo is None:raise ValueError()
                    elif kind=='DATE':date.fromisoformat(value)
                    else:datetime.fromisoformat(value)
                except ValueError:raise QueryDenied('filter value denied') from None
        else:
            if any(not isinstance(v,str) or len(v)>200 for v in f.values):raise QueryDenied('filter type denied')
        if f.operator=='eq':conditions.append(f'{quote(f.column)} = ?');params.extend(f.values)
        elif f.operator=='in':
            conditions.append(f'{quote(f.column)} IN ({",".join("?" for _ in f.values)})');params.extend(f.values)
        elif f.operator=='gte':conditions.append(f'{quote(f.column)} >= ?');params.append(f.values[0])
        else:conditions.append(f'{quote(f.column)} < ?');params.append(f.values[0])
    where=' WHERE '+' AND '.join(conditions) if conditions else ''
    table=description['table'];pieces=table.split('.')
    if len(pieces)!=2 or any(not p for p in pieces):raise QueryDenied('table denied')
    target='.'.join(quote(p) for p in pieces)
    value='COUNT(*)' if m.operator=='count_rows' else f'SUM({quote(m.column)})' if m.operator=='sum' else f'SUM({quote(m.numerator)}) / NULLIF(SUM({quote(m.denominator)}), 0)'
    dims=','.join(quote(c) for c in b.dimensions)
    sql=f'SELECT {dims+"," if dims else ""}{value} AS "metric_value" FROM {target}{where}'
    if dims:sql+=f' GROUP BY {dims} ORDER BY {dims}'
    sql+=' LIMIT 101' # Bounds output groups only; input is never preview limited.
    validate_aggregate(sql,sql,description,b)
    return sql,params,where,target


def validate_aggregate(sql,expected_sql,description,body):
    from .policy import QueryDenied
    import sqlglot
    from sqlglot import exp
    ALLOWED={exp.Select,exp.Column,exp.Identifier,exp.From,exp.Table,exp.Limit,exp.Literal,exp.Count,exp.Sum,exp.Star,exp.Alias,exp.Div,exp.Nullif,exp.Group,exp.Order,exp.Ordered,exp.Where,exp.And,exp.EQ,exp.GTE,exp.LT,exp.In,exp.Tuple,exp.Placeholder}
    if sql!=expected_sql or len(sql)>16000:raise QueryDenied('compiler hash mismatch')
    try:trees=sqlglot.parse(sql,read='duckdb')
    except sqlglot.errors.ParseError:raise QueryDenied('parse denied') from None
    if len(trees)!=1 or type(trees[0]) is not exp.Select:raise QueryDenied('single SELECT required')
    tree=trees[0]
    if any(type(node) not in ALLOWED or node.comments for node in tree.walk()):raise QueryDenied('AST denied')
    tables=list(tree.find_all(exp.Table));schema,name=description['table'].split('.')
    if len(tables)!=1 or tables[0].name!=name or tables[0].db!=schema or tables[0].catalog:raise QueryDenied('table denied')
    names={c['name'] for c in description['fields']}
    if any(c.name not in names or c.table for c in tree.find_all(exp.Column)):raise QueryDenied('column denied')
    if any(c.args.get('distinct') for c in tree.find_all(exp.Count)):raise QueryDenied('unexpected distinct')
    return tree
