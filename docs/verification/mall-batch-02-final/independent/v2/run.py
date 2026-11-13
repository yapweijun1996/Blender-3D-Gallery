from pathlib import Path
import subprocess,json,sys
ids=['escalator-handrail','lift-call-panel','lift-floor-indicator','emergency-exit-door','fire-hose-reel-cabinet','sprinkler-head','cctv-camera','digital-advertising-screen','wayfinding-ceiling-sign','food-court-tray-station']
b=['/srv/agent-workstation/workspaces/blender-mall-four-20261112/blender-local.sh','--background','--threads','2','--python-exit-code','1','--python']
node='/home/ai-agent/.local/lib/node22/bin/node'
results=[]
def run(id,step,cmd):
 with open('review-results/v2/'+id+'-'+step+'.log','w') as f: code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 results.append({'asset':id,'step':step,'exitCode':code}); print(id,step,code,flush=True)
 Path('review-results/v2/results.json').write_text(json.dumps(results,indent=2))
 return code
for id in ids:
 p='review-fixtures/models/mall-'+id
 source=b+[p+'/inspect_sources.py']
 if id=='escalator-handrail': source+=['--',str(Path('review-fixtures/edited-430').resolve())]
 code=run(id,'source',source)
 run(id,'geometry',[node,p+'/validate.mjs'])
 if code: print('Fresh source failed: edit test must not consume stale fixture',id,flush=True);continue
 if id=='escalator-handrail':
  code=run(id,'edit-export',b+['review-fixtures/edited-430/generate.py','--','--export-source','--skip-render'])
  if code: continue
  run(id,'edit',[node,p+'/verify_source_edit.mjs','review-fixtures/edited-430/exports/optimized.glb'])
 else: run(id,'edit',[node,p+'/verify_source_edit.mjs'])
sys.exit(0 if len([r for r in results if r['step']=='edit' and r['exitCode']==0])==10 and all(r['exitCode']==0 for r in results) else 1)
