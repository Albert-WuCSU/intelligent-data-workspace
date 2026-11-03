"""Read actual governed metadata for semantics; never submits a preview/query."""
import hashlib,json
from pydantic import Field
from .contracts import Contract
from .auth import PublicError
from .retention import storage_operation

class SemanticColumn(Contract):
    name: str = Field(min_length=1,max_length=200)
    data_type: str = Field(min_length=1,max_length=128)
class SemanticSchema(Contract):
    source_id: str
    source_version: int
    table_id: str
    table_name: str
    columns: list[SemanticColumn]
    fingerprint: str
    rows_read: bool = False

@storage_operation
async def read_schema(store,auth,source_id,table_id):
    # storage_operation expects self.root etc: this function's first argument is the SourceStore.
    with store.lock:
        row=store.get(auth,source_id)
        if not row['enabled']:raise PublicError(409,'SOURCE_DISABLED','数据源已禁用，不能验证语义映射。')
        if store.active:raise PublicError(409,'SOURCE_BUSY','正在读取数据源，请稍后重试。')
        store.active=True;version=row['version']
    try:
        if row['kind']=='local_file':value=(await store.call(auth,row['database_path'],'describe_table',{'table':table_id}))['metadata']
        else:value=await store.remote_call(auth,row,'describe',table_id)
        fields=value.get('fields')
        if not isinstance(fields,list) or not 1<=len(fields)<=100:raise ValueError()
        columns=[];seen=set()
        for field in fields:
            if not isinstance(field,dict):raise ValueError()
            col=SemanticColumn(name=field['name'],data_type=field['type'])
            if col.name in seen:raise ValueError()
            seen.add(col.name);columns.append(col)
        table_name=value.get('table')
        if not isinstance(table_name,str) or not 1<=len(table_name)<=200:raise ValueError()
        with store.lock:
            current=store.get(auth,source_id)
            if not current['enabled'] or current['version']!=version:raise PublicError(409,'PROFILE_CHANGED','数据源已变更，需重新验证字段。')
        fingerprint=hashlib.sha256(json.dumps([source_id,version,table_id,table_name,[c.model_dump() for c in columns]],sort_keys=True).encode()).hexdigest()
        return SemanticSchema(source_id=source_id,source_version=version,table_id=table_id,table_name=table_name,columns=columns,fingerprint=fingerprint)
    except PublicError:raise
    except Exception:raise PublicError(422,'SEMANTIC_SCHEMA_INVALID','真实元数据不可用或超限，请检查字段权限与适配器；不会通过查询行数据代替。') from None
    finally:
        with store.lock:store.active=False
