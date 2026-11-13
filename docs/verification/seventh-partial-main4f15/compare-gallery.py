#!/usr/bin/env python3
"""Compare future fixed-pass gallery evidence to immutable producer records."""
from pathlib import Path
import json,sys
D=Path(__file__).resolve().parent
expected=json.loads((D/'producer-gallery-index.json').read_text())
comparisons=[]; reports={}
for e in expected:
 suite=e['suite']
 if suite not in reports:
  p=D/'integration'/suite/'results.json'
  assert p.exists(),str(p)
  d=json.loads(p.read_text()); rows=d if isinstance(d,list) else d['results']
  reports[suite]={(r['asset'],r['width']):r for r in rows}
 r=reports[suite].get((e['asset'],e['width']))
 assert r is not None,(suite,e['asset'],e['width'])
 consumed=r.get('consumed',[])+r.get('initialConsumed',[])
 exact=bool(r.get('passed')) and r.get('sha256')==e['sha256'] and bool(consumed) and all(c.get('sha256')==e['sha256'] for c in consumed)
 changed=[k for k,v in e['pixels'].items() if r.get('pixels',{}).get(k)!=v]
 comparisons.append(dict(suite=suite,asset=e['asset'],width=e['width'],exact_final_bytes_and_test_pass=exact,changed_pixel_states=changed,visual_review='NEEDS REVIEW' if changed else 'Matches producer pixel hashes; independent review still required'))
out={'comparisons':comparisons,'physical_devices':'NOT TESTED','known_prior_failure_preserved':True}
(D/'integration/gallery-comparison.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'cases':len(comparisons),'exact_bytes_pass':sum(x['exact_final_bytes_and_test_pass'] for x in comparisons),'pixel_mismatches':sum(bool(x['changed_pixel_states']) for x in comparisons)}))
sys.exit(1 if any(not x['exact_final_bytes_and_test_pass'] or x['changed_pixel_states'] for x in comparisons) else 0)
