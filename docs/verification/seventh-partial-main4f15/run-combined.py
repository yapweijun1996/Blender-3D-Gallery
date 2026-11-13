#!/usr/bin/env python3
"""Prepared sequential fixed gate; does not authorize running itself."""
from pathlib import Path
import json,subprocess,os,sys,datetime
R=Path(__file__).resolve().parents[3];os.chdir(R)
D=R/'docs/verification/seventh-partial-main4f15';ready=json.loads((D/'gate-readiness.json').read_text());ledger=json.loads((D/'asset-ledger.json').read_text())
assert ready['run_authorized'] and ready['all_final_handoffs_received'] and ready['escalator_decision_received'],'HELD: final handoffs and escalator decision required'
suites=json.loads((D/'suites.json').read_text());assert not suites['pending_packets'],'Unconfigured final packet suites'
out=D/'integration';assert not out.exists(),'One fixed pass only; preserve previous evidence and arrange a distinct diagnostic, not retry-to-green'
out.mkdir();env=os.environ.copy();env['PATH']='/home/ai-agent/.local/lib/node22/bin:'+env.get('PATH','')
env.pop('MALL_QA_ASSETS',None);env.pop('BATCH_ASSET_IDS',None)
steps=[{'name':'preservation-start','command':['python3','docs/verification/seventh-partial-main4f15/verify-preservation.py']},{'name':'unit','command':['python3','docs/verification/seventh-partial-main4f15/unit-fixture.py']},{'name':'build','command':['npm','run','build']},{'name':'library','command':['node','scripts/test-library-browser.mjs'],'env':'TEST_ARTIFACT_DIR'},{'name':'lifecycle','command':['node','scripts/test-gallery-loading.mjs'],'env':'TEST_ARTIFACT_DIR'}]+suites['suites']+[{'name':'gallery-comparison','command':['python3','docs/verification/seventh-partial-main4f15/compare-gallery.py']},{'name':'legacy-preview','command':['node','scripts/test-preview-config.mjs','dist',str(out/'legacy-preview')]},{'name':'gjh-original-visual','command':['node','scripts/test-gjh-can-visual.mjs']},{'name':'gjh-codex-visual','command':['node','scripts/test-gjh-can-visual.mjs','--codex']},{'name':'preservation-end','command':['python3','docs/verification/seventh-partial-main4f15/verify-preservation.py']}]
results=[]
for step in steps:
 e=env.copy()
 if step.get('env'):e[step['env']]=str(out/step['name'])
 print('START',step['name'],datetime.datetime.now(datetime.timezone.utc).isoformat(),flush=True)
 with (out/(step['name']+'.log')).open('w') as log:rc=subprocess.run(step['command'],env=e,stdout=log,stderr=subprocess.STDOUT).returncode
 results.append({'step':step['name'],'exit_code':rc,'command':step['command']})
 (out/'status.json').write_text(json.dumps(results,indent=2)+'\n')
 print('END',step['name'],rc,flush=True)
 if rc:print('\n'.join((out/(step['name']+'.log')).read_text(errors='replace').splitlines()[-60:]),flush=True)
# A passing process pass never overrides known prior regressions or NEEDS REVIEW/DERIVED policies.
(out/'scope.json').write_text(json.dumps({'tested_base':ledger['base'],'new_registrations':len(ledger['assets']),'prior_regression_preserved':True,'asset_statuses_not_automatically_upgraded':True},indent=2)+'\n')
sys.exit(1 if any(x['exit_code'] for x in results) else 0)
