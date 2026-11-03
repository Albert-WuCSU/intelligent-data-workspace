"""Fixed stdio MCP bootstrap: no metadata read before parent Job assignment."""
import json
import os
from pathlib import Path
import sys

line=sys.stdin.buffer.readline(65537)
if len(line)>65536 or not line.endswith(b'\n'):raise SystemExit(2)
root=Path(__file__).resolve().parents[5]
site=root/'services/api/.venv/Lib/site-packages'
sys.path[:0]=[str(root/'services/api/src'),str(site),str(site/'win32'),str(site/'win32/lib'),str(site/'Pythonwin')]
_dll=os.add_dll_directory(str(site/'pywin32_system32'))
try:
    settings=json.loads(line.decode('utf-8'))
    if set(settings)!={'warehouse','database'}:raise ValueError('invalid bootstrap')
    from data_workspace.warehouse.aggregate_server import create_aggregate_server
    create_aggregate_server(settings['warehouse'],settings['database']).run(transport='stdio')
except Exception:raise SystemExit(2)
