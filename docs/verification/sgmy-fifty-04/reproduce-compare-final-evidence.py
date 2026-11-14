from pathlib import Path
import json,hashlib
r=Path(__file__).parent/'repo';o=r/'docs/verification/sgmy-fifty-04';q=o/'integration';rows=[]
def load(p):return json.loads(p.read_text())
def compare(fresh,old):
 olds={(x['asset'],x['width']):x for x in old['results']}
 for x in fresh['results']:
  y=olds[(x['asset'],x['width'])]
  assert x['passed'] and y['passed'];assert x['sha256']==y['sha256'],('artifact differs',x['asset'])
  rows.append({'asset':x['asset'],'width':x['width'],'glb_sha256':x['sha256'],'initial_pixels_match_inspected_producer':x['pixels']['initial']==y['pixels']['initial'],'initial_sha256':x['pixels']['initial']})
old=load(r/'docs/verification/domestic011/browser/results.json');patch=load(r/'docs/verification/domestic011/browser-sink-fixed/results.json');changed={(x['asset'],x['width']):x for x in patch['results']};old['results']=[changed.get((x['asset'],x['width']),x) for x in old['results']]
compare(load(q/'domestic-browser/results.json'),old)
compare(load(q/'retail-browser/results.json'),load(r/'docs/verification/fifty04-retail/browser/results.json'))
compare(load(q/'carehotel-browser/results.json'),load(r/'docs/verification/carehotel04-gallery-final.json'))
assert len(rows)==150 and len({(x['asset'],x['width']) for x in rows})==150
(o/'pixel-comparison.json').write_text(json.dumps({'cases':150,'matching':sum(x['initial_pixels_match_inspected_producer'] for x in rows),'results':rows},indent=2)+'\n')
print('cases',len(rows),'matching',sum(x['initial_pixels_match_inspected_producer'] for x in rows));print([x for x in rows if not x['initial_pixels_match_inspected_producer']])
