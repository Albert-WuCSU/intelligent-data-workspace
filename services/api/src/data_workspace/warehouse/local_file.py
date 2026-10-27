"""Runtime table navigation of a trusted copied database. No user SQL/paths."""
import json
from datetime import date,datetime
from threading import Timer
from pathlib import Path
import duckdb
from .engine import ENGINE_CONFIG, WarehouseError
from .build import sha
from .request import PreviewRequest

class LocalFileWarehouse:
    def __init__(self,database):
        self.database=Path(database).resolve()
        manifest=json.loads(self.database.with_suffix('.manifest.json').read_text(encoding='utf-8'))
        if sha(self.database)!=manifest['database_sha256']:raise WarehouseError('snapshot integrity failure')
        self.version=manifest['version']
        self.tables=manifest['tables']
        self.catalog={key:[(c['name'],c['type']) for c in table['columns']] for key,table in self.tables.items()}

    def connect(self):
        con=duckdb.connect(str(self.database),read_only=True,config=ENGINE_CONFIG)
        con.execute('SET lock_configuration = true')
        return con

    def list_tables(self):
        with self.connect() as con:
            actual=set(con.execute("SELECT table_schema,table_name FROM information_schema.tables WHERE table_type='BASE TABLE'").fetchall())
        if actual!={(t['schema'],t['name']) for t in self.tables.values()}:raise WarehouseError('catalog mismatch')
        return {'source':'user_provided','dataset_version':self.version,'tables':[{'id':key,'name':f"{t['schema']}.{t['name']}"} for key,t in self.tables.items()]}

    def describe(self,table):
        if table not in self.tables:raise WarehouseError('table unavailable')
        t=self.tables[table]
        return {'table':f"{t['schema']}.{t['name']}",'fields':t['columns'],'source':'user_provided','timezone':None}

    def partitions(self,table):
        if table not in self.tables:raise WarehouseError('table unavailable')
        return {'table':table,'partitions':[],'supported':False,'note':'No partition or date meaning is inferred.'}

    def preview(self,request):
        request=PreviewRequest.model_validate(request)
        if request.table not in self.tables:raise WarehouseError('table unavailable')
        t=self.tables[request.table]
        available={c['name'] for c in t['columns']}
        names=request.columns or [c['name'] for c in t['columns']]
        if not set(names)<=available or len(names)>100:raise WarehouseError('columns unavailable')
        quote=lambda s:'"'+s.replace('"','""')+'"'
        sql=f"SELECT {','.join(quote(n) for n in names)} FROM {quote(t['schema'])}.{quote(t['name'])} LIMIT {request.limit+1}"
        with self.connect() as con:
            timer=Timer(3,con.interrupt)
            try:
                timer.start();cursor=con.execute(sql);columns=[{'name':n,'type':str(k)} for n,k,*_ in cursor.description];rows=cursor.fetchmany(request.limit+1)
            finally:timer.cancel();timer.join()
        converted=[[v.isoformat() if isinstance(v,(date,datetime)) else v if v is None or isinstance(v,(str,int,float,bool)) else str(v) for v in row] for row in rows[:request.limit]]
        if len(json.dumps(converted).encode())>200000:raise WarehouseError('preview too large')
        return {'source':'user_provided','dataset_version':self.version,'sql_dialect':'duckdb','columns':columns,'rows':converted,'returned_row_count':len(converted),'reported_total_rows':None,'truncated':len(rows)>request.limit,'retrieved_at':datetime.now().astimezone().isoformat(),'currency':None,'quality':{'status':'WARN','limitations':['User-provided local snapshot; business semantics and currency are not inferred','Preview of at most 100 rows, not a complete dataset; no guaranteed ordering']}}
