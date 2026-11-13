from pathlib import Path
import subprocess,json,sys
b=['/srv/agent-workstation/workspaces/blender-mall-four-20261112/blender-local.sh','--background','--threads','2','--python-exit-code','1','--python'];node='/home/ai-agent/.local/lib/node22/bin/node';rows=[]
for p in sorted(Path('fixtures/models').iterdir()):
 script=p/('inspect_sources.py' if (p/'inspect_sources.py').exists() else 'inspect_source.py')
 for phase,cmd in [('source',b+[str(script)]),('geometry',[node,str(p/'validate.mjs')]),('edit',[node,str(p/'verify_source_edit.mjs')])]:
  with open('review-results/full/'+p.name+'-'+phase+'.log','w') as f: code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
  rows.append({'asset':p.name,'phase':phase,'exitCode':code});print(p.name,phase,code,flush=True)
  if code: break
Path('review-results/full/results.json').write_text(json.dumps(rows,indent=2));sys.exit(0 if len(rows)==30 and all(x['exitCode']==0 for x in rows) else 1)
