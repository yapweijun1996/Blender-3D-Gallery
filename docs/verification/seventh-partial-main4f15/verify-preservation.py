from pathlib import Path
import json,subprocess,hashlib
R=Path(__file__).resolve().parents[3];D=R/'docs/verification/seventh-partial-main4f15';d=json.loads((D/'import.json').read_text());base=d['base']
old=json.loads(subprocess.check_output(['git','-C',str(R),'show',base+':models/catalog.json']));current=json.loads((R/'models/catalog.json').read_text());assert current['collections'][:len(old['collections'])]==old['collections']
ids=[a['id'] for c in current['collections'] for a in c['assets']];assert len(ids)==len(set(ids))==431
rows=[x.split('\t',1) for x in subprocess.check_output(['git','-C',str(R),'diff','--name-status',base],text=True).splitlines()]
assert all(t=='A' or (t=='M' and p=='models/catalog.json') for t,p in rows)
for p,h in d['source_paths_sha256'].items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h,p
print(json.dumps({'status':'PASS','base':base,'prior_main_entries':398,'candidate_entries':33,'total_entries':431,'imported_paths_verified':len(d['source_paths_sha256']),'old_main_files':'unchanged except additive catalog','old_integration_evidence':'byte-for-byte preserved'}))
