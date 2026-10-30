"""Point-in-time default loopback deployment verification, not a portable CI test."""
import hashlib,json,urllib.request
from pathlib import Path
root=Path.cwd();baseline=root/'tmp/retention-default-preenable/integrity.json'
original=json.loads(baseline.read_text(encoding='utf-8'))
for name,h in original.items():
    path=root/'data/connections'/name
    assert path.resolve().is_relative_to((root/'data/connections').resolve())
    assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==h
for url in ('http://127.0.0.1:5173','http://127.0.0.1:8000/health/live'):
    with urllib.request.urlopen(url,timeout=5) as response:assert response.status==200
with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/source-profiles/retention',timeout=5) as response:status=json.load(response)
with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/source-profiles/storage',timeout=8) as response:inventory=json.load(response)
assert status['automatic_cleanup'] and status['cycle_state']=='SUCCEEDED' and status['interval_seconds']==600
assert inventory['saved_profiles']==29 and inventory['automatic_cleanup']
print(json.dumps({'passed':True,'original_runtime_files_preserved':len(original),'saved_profiles':29,'enabled':True,'cycle_state':status['cycle_state'],'interval_seconds':600,'reclaimed':status['cycle_counts']['reclaimed'],'scope':'default current-code first cycle and preservation; not PG/production/natural24h'},ensure_ascii=False))
