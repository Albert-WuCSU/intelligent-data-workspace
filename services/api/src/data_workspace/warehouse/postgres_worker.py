"""Owned PostgreSQL read-only process. Fixed operations; no user SQL or host credentials."""
from datetime import date,datetime
from decimal import Decimal
import hashlib,json,math,os,sys

class ResourceDenied(ValueError): pass

def table_id(schema,name):
    return 'pg_'+hashlib.sha256((schema+'\0'+name).encode()).hexdigest()[:24]

def navigate(payload,connect=None):
    from psycopg import connect as pg_connect,sql
    from data_workspace.remote_access import PostgresDraft
    draft=PostgresDraft.model_validate(payload['draft'])
    schemas=payload['schemas']
    if payload['operation'] not in {'tables','preview'} or not 1<=len(schemas)<=20: raise ValueError('operation')
    with (connect or pg_connect)(host=draft.host,hostaddr=draft.host,port=draft.port,dbname=draft.database,user=draft.username,password=payload['password'],sslmode=draft.sslmode,connect_timeout=4,passfile=os.devnull,sslcert=os.devnull,sslkey=os.devnull,sslrootcert='system',application_name='data_workspace_navigation') as con:
        con.execute('BEGIN READ ONLY')
        con.execute("SET LOCAL statement_timeout = '3000ms'")
        con.execute("SET LOCAL lock_timeout = '1000ms'")
        con.execute('SET LOCAL search_path = pg_catalog')
        # Only base/partitioned tables and SELECT allowed by this actual account.
        tables=con.execute("SELECT n.nspname,c.relname FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname = ANY(%s) AND c.relkind IN ('r','p') AND pg_catalog.has_table_privilege(c.oid,'SELECT') ORDER BY n.nspname,c.relname LIMIT 51",[schemas]).fetchall()
        if len(tables)>50: raise ValueError('catalog budget')
        mapping={table_id(s,n):(s,n) for s,n in tables}
        if payload['operation']=='tables': return {'source':'postgresql','tables':[{'id':t,'name':s+'.'+n} for t,(s,n) in mapping.items()]}
        if payload['table'] not in mapping: raise ResourceDenied()
        schema,name=mapping[payload['table']]
        fields=con.execute("SELECT a.attname,pg_catalog.format_type(a.atttypid,a.atttypmod) FROM pg_catalog.pg_attribute a JOIN pg_catalog.pg_class c ON c.oid=a.attrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relname=%s AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum LIMIT 101",[schema,name]).fetchall()
        if not 1<=len(fields)<=100: raise ValueError('column budget')
        rows=con.execute(sql.SQL('SELECT * FROM {}.{} LIMIT 101').format(sql.Identifier(schema),sql.Identifier(name))).fetchmany(101)
        def cell(v):
            if isinstance(v,(date,datetime)): return v.isoformat()
            if isinstance(v,Decimal): return str(v)
            if v is None or isinstance(v,(str,int,bool)): return v
            if isinstance(v,float) and math.isfinite(v): return v
            raise ValueError('unsupported value')
        result={'source':'postgresql','columns':[{'name':n,'type':t} for n,t in fields],'rows':[[cell(v) for v in row] for row in rows[:100]],'returned_row_count':min(len(rows),100),'truncated':len(rows)>100,'reported_total_rows':None,'currency':None,'quality':{'status':'WARN','limitations':['PostgreSQL read-only preview; semantics not certified','No filters or ordering guarantee; at most 100 rows']}}
        if len(json.dumps(result,ensure_ascii=False).encode())>200000: raise ValueError('result budget')
        return result

if __name__=='__main__':
    try:
        raw=sys.stdin.read(65537)
        if len(raw)>65536: raise ValueError('input budget')
        value={'ok':True,'data':navigate(json.loads(raw))}
    except ResourceDenied: value={'ok':False,'code':'RESOURCE_DENIED'}
    except Exception: value={'ok':False,'code':'CONNECTION_FAILED'}
    sys.stdout.write(json.dumps(value,ensure_ascii=False))
