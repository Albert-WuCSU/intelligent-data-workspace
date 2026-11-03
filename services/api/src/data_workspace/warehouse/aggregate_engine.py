"""Whole-table aggregates in the same read-only engine/Job, never computed from preview rows."""
import json,math
from datetime import date,datetime,timezone
from decimal import Decimal
from threading import Timer
from .aggregate_contract import AggregateRequest,AggregateResult,compile_aggregate,quote
from .policy import QueryDenied

def execute_aggregate(warehouse,request):
    b=AggregateRequest.model_validate(request) if isinstance(request,dict) else request
    desc=warehouse.describe(b.table);sql,params,where,target=compile_aggregate(b,desc)
    with warehouse.connect() as con:
        timer=Timer(5,con.interrupt)
        try:
            timer.start()
            # Scan budget check reads at most 200001 rows in this bounded read-only job.
            size=con.execute(f'SELECT COUNT(*) FROM (SELECT 1 FROM {target} LIMIT 200001)').fetchone()[0]
            if size>200000:raise QueryDenied('input row budget')
            matched=con.execute(f'SELECT COUNT(*) FROM {target}{where}',params).fetchone()[0]
            keys=','.join(quote(c) for c in b.grain)
            unique=con.execute(f'SELECT COUNT(*) FROM (SELECT {keys} FROM {target}{where} GROUP BY {keys})',params).fetchone()[0]
            nulls=' OR '.join(quote(c)+' IS NULL' for c in b.grain)
            null_grain=con.execute(f'SELECT COUNT(*) FROM {target}{where+" AND ("+nulls+")" if where else " WHERE "+nulls}',params).fetchone()[0]
            metriccols=[c for c in [b.metric.column,b.metric.numerator,b.metric.denominator] if c]
            null_metric=0
            if metriccols:
                nc=' OR '.join(quote(c)+' IS NULL' for c in metriccols)
                null_metric=con.execute(f'SELECT COUNT(*) FROM {target}{where+" AND ("+nc+")" if where else " WHERE "+nc}',params).fetchone()[0]
            cursor=con.execute(sql,params);cols=[{'name':n,'type':str(t)} for n,t,*_ in cursor.description];raw=cursor.fetchmany(101)
            if len(raw)>100:raise QueryDenied('output group budget')
            zero=missing=0
            if b.metric.operator=='ratio':
                dims=','.join(quote(c) for c in b.dimensions)
                den=con.execute(f'SELECT SUM({quote(b.metric.denominator)}) FROM {target}{where}'+(f' GROUP BY {dims}' if dims else ''),params).fetchmany(101)
                zero=sum(v[0]==0 for v in den);missing=sum(v[0] is None for v in den)
            def cell(v):
                if isinstance(v,datetime) and v.tzinfo is not None:return v.astimezone(timezone.utc).isoformat()
                if isinstance(v,(date,datetime)):return v.isoformat()
                if isinstance(v,Decimal):return str(v)
                if type(v) is float and not math.isfinite(v):raise QueryDenied('nonfinite result')
                if v is None or isinstance(v,(str,int,float,bool)):return v
                raise QueryDenied('unsupported cell')
            rows=[[cell(v) for v in row] for row in raw]
            if len(json.dumps([cols,rows],ensure_ascii=False).encode())>200000:raise QueryDenied('result byte budget')
            warnings=[]
            if matched>unique:warnings.append('Declared grain has duplicate records; definition uniqueness is not certified')
            if null_grain:warnings.append('Declared grain has null fields')
            if null_metric:warnings.append('Aggregate ignored null inputs; see null_metric_rows')
            if zero or missing:warnings.append('Ratio denominator zero/null yields null, not zero')
            if not matched:warnings.append('No matching rows; empty result/NULL sum is not a zero business value')
            if getattr(warehouse,'manifest',{}).get('synthetic'):warnings.append('Independent synthetic fixture, not enterprise business data')
            return AggregateResult(source=desc['source'],columns=cols,rows=rows,input_rows=size,matched_rows=matched,duplicate_grain_rows=matched-unique,null_grain_rows=null_grain,null_metric_rows=null_metric,zero_denominator_groups=zero,null_denominator_groups=missing,returned_row_count=len(rows),quality='WARN' if warnings else 'PASS',unit=b.metric.unit,limitations=warnings)
        finally:timer.cancel();timer.join()
