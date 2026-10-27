"""Compiler-only read-only preview: no WHERE, guessed date or business filter."""
import sqlglot
from sqlglot import exp
from .catalog import COLUMNS
from .request import PreviewRequest

class QueryDenied(ValueError):
    pass

ALLOWED={exp.Select,exp.Column,exp.Identifier,exp.From,exp.Table,exp.Limit,exp.Literal}

def validate_template(sql,table,catalog=None):
    catalog=COLUMNS if catalog is None else catalog
    if len(sql)>20000 or table not in catalog:raise QueryDenied("table denied")
    try:trees=sqlglot.parse(sql,read="duckdb")
    except sqlglot.errors.ParseError:raise QueryDenied("query denied") from None
    if len(trees)!=1 or type(trees[0]) is not exp.Select:raise QueryDenied("single preview SELECT required")
    tree=trees[0]
    if any(type(n) not in ALLOWED or n.comments for n in tree.walk()):raise QueryDenied("expression denied")
    tables=list(tree.find_all(exp.Table))
    if len(tables)!=1 or tables[0].name!=table or tables[0].db!='analytics' or tables[0].catalog or tables[0].alias:raise QueryDenied("table denied")
    names={name for name,_ in catalog[table]}
    if any(c.name not in names or c.table for c in tree.find_all(exp.Column)):raise QueryDenied("column denied")
    limit=tree.args.get('limit')
    if limit is None or not isinstance(limit.expression,exp.Literal) or limit.expression.is_string or not limit.expression.this.isdigit() or not 1<=int(limit.expression.this)<=101:raise QueryDenied("limit denied")
    return tree


def compile_preview(request,catalog=None):
    catalog=COLUMNS if catalog is None else catalog
    request=PreviewRequest.model_validate(request)
    if request.table not in catalog:raise QueryDenied("table unavailable")
    available=[name for name,_ in catalog[request.table]]
    selected=request.columns or available
    if len(selected)>100 or not set(selected)<=set(available):raise QueryDenied("columns unavailable or table exceeds supported 100-column preview")
    columns=','.join('"'+column.replace('"','""')+'"' for column in selected)
    table=request.table.replace('"','""')
    sql=f'SELECT {columns} FROM analytics."{table}" LIMIT {request.limit+1}'
    validate_template(sql,request.table,catalog)
    return sql,[],request
