import sys,json,subprocess,hashlib,shutil
from pathlib import Path
src=Path(sys.argv[1]);base=sys.argv[2];label=sys.argv[3];expected=sys.argv[4];dst=Path(__file__).parent/'repo'
def git(*args):return subprocess.check_output(['git','-C',str(src),*args]).decode()
assert git('rev-parse','HEAD').strip()==expected
dirty=set(git('diff','HEAD','--name-only').splitlines())
rows=[x.split('\t') for x in git('diff','--name-status',base,expected).splitlines()]
assert all(r[0]=='A' or r==['M','models/catalog.json'] for r in rows),rows
assert not dirty.intersection({r[1] for r in rows}),('dirty import paths',dirty)
old=json.loads((dst/'models/catalog.json').read_text());new=json.loads(git('show',expected+':models/catalog.json'));before=json.loads(git('show',base+':models/catalog.json'))
bmap={x['id']:x for x in before['collections']};nmap={x['id']:x for x in new['collections']};assert all(nmap[k]==v for k,v in bmap.items())
adds=[v for k,v in nmap.items() if k not in bmap];omap={x['id']:x for x in old['collections']};assert all(x['id'] not in omap for x in adds)
assetids=[a['id'] for c in old['collections']+adds for a in c['assets']];assert len(assetids)==len(set(assetids))
files=[r[1] for r in rows if r[0]=='A'];identical=[]
committed={x.split('\t',1)[1]:x.split('\t',1)[0].split()[2] for x in git('ls-tree','-r',expected).splitlines()}
actual=subprocess.check_output(['git','-C',str(src),'hash-object','--stdin-paths'],input=('\n'.join(files)+'\n').encode()).decode().splitlines()
assert all(committed[f]==h for f,h in zip(files,actual)), 'uncommitted file bytes'

for f in files:
 s=src/f;t=dst/f
 assert s.is_file() and not s.is_symlink(),f
 if t.exists():assert t.read_bytes()==s.read_bytes(),'would overwrite '+f;identical.append(f)
for f in files:
 s=src/f;t=dst/f
 if not t.exists():t.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(s,t)
raw=(dst/'models/catalog.json').read_text();tail='\n  ]\n}\n';assert raw.endswith(tail)
extra=',\n'.join('\n'.join('    '+line for line in json.dumps(c,indent=2,ensure_ascii=False).splitlines()) for c in adds)
(dst/'models/catalog.json').write_text(raw[:-len(tail)]+',\n'+extra+tail)
p=dst/'docs/verification/sgmy-fifty-04';p.mkdir(parents=True,exist_ok=True)
r={'producer':str(src),'baseline':base,'commit':expected,'new_collections':[c['id'] for c in adds],'new_assets':sum(len(c['assets']) for c in adds),'files':files,'identical_existing':identical}
(p/('import-'+label+'.json')).write_text(json.dumps(r,indent=2)+'\n');print(label,r['new_assets'],len(files),flush=True)
