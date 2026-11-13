import json,subprocess
from pathlib import Path
r=Path(__file__).parent/'repo';base='3c41bcfd660c69a41fe3bb7f5f56baed6f4b4e0b'
def git(*a):return subprocess.check_output(['git','-C',str(r),*a])
old=json.loads(git('show',base+':models/catalog.json'));cur=json.loads((r/'models/catalog.json').read_text());cm={c['id']:c for c in cur['collections']}
assert all(cm[c['id']]==c for c in old['collections'])
assert {k:v for k,v in old.items() if k!='collections'}=={k:v for k,v in cur.items() if k!='collections'}
ids=[a['id'] for c in cur['collections'] for a in c['assets']];assert len(ids)==len(set(ids))
def tree(path,ref):
 return {x.split('\t',1)[1]:x.split('\t',1)[0].split()[2] for x in subprocess.check_output(['git','-C',str(path),'ls-tree','-r',ref]).decode().splitlines()}
oldfiles=tree(r,base);paths=[f for f in oldfiles if f!='models/catalog.json']
actual=git('hash-object','--stdin-paths') if False else subprocess.check_output(['git','-C',str(r),'hash-object','--stdin-paths'],input=('\n'.join(paths)+'\n').encode()).decode().splitlines()
assert len(actual)==len(paths)
for f,h in zip(paths,actual):assert h==oldfiles[f],('old file modified',f)
imports=[]
for p in sorted((r/'docs/verification/sgmy-fifty-06').glob('import-*.json')):
 d=json.loads(p.read_text());sourcefiles=tree(d['producer'],d['commit']);paths=d['files']
 hashes=subprocess.check_output(['git','-C',str(r),'hash-object','--stdin-paths'],input=('\n'.join(paths)+'\n').encode()).decode().splitlines()
 for f,h in zip(paths,hashes):assert h==sourcefiles[f],('import changed',f)
 imports.append({'commit':d['commit'],'assets':d['new_assets'],'files':len(paths)})
assert sum(x['assets'] for x in imports)==50
print(json.dumps({'base':base,'old_assets':sum(len(c['assets']) for c in old['collections']),'total_assets':len(ids),'imports':imports,'status':'PASS'},indent=2))
