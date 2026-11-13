from pathlib import Path
import json,hashlib,subprocess
R=Path('.').resolve();D=R/'docs/verification/seventh-partial';L=json.loads((D/'asset-ledger.json').read_text());base=L['base']
old=json.loads(subprocess.check_output(['git','show',base+':models/catalog.json']));new=json.loads((R/'models/catalog.json').read_text());assert new['collections'][:len(old['collections'])]==old['collections']
ids=[a['id'] for c in new['collections'] for a in c['assets']];assert len(ids)==len(set(ids))==L['total_registrations']
changed=[x.split('\t',1) for x in subprocess.check_output(['git','diff','--name-status',base],text=True).splitlines()]
assert all(t=='A' or (t=='M' and p=='models/catalog.json') for t,p in changed)
replacements=json.loads((D/'intentional-replacements.json').read_text())['replacements']
checked=0
for p in (D/'imports').glob('*.json'):
 for name,sha in json.loads(p.read_text())['source_paths_sha256'].items():
  actual=hashlib.sha256((R/name).read_bytes()).hexdigest()
  if name in replacements and sha==replacements[name]['old_sha256']:
   q=replacements[name];assert hashlib.sha256((R/q['archive']).read_bytes()).hexdigest()==sha and actual==q['new_sha256']
  else:assert actual==sha,'Producer bytes changed: '+name
  checked+=1
for a in L['assets']:assert hashlib.sha256((R/a['glb']).read_bytes()).hexdigest()==a['glb_sha256']
assert len({a['slug'] for a in L['assets']})==len(L['assets'])
print(json.dumps({'status':'PASS','base':base,'old_registrations':L['prior_registrations'],'staged_registrations':len(L['assets']),'producer_files_hash_verified':checked,'old_tracked_modification':'models/catalog.json additive only','does_not_claim_integration_pass':True},indent=2))
