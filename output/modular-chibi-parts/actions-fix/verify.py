"""Verify the binary contract and compare all measured source/output frames."""
import json
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *

def container():
    orig,src=chibi.glb(SOURCE);out,buf=chibi.glb(FIXED)
    n=int.from_bytes(SOURCE.read_bytes()[12:16],'little')+28
    assert SOURCE.read_bytes()[:n]==FIXED.read_bytes()[:n] and orig==out and len(src)==len(buf)
    diff=np.frombuffer(src,dtype=np.uint8)!=np.frombuffer(buf,dtype=np.uint8)
    allowed=np.zeros_like(diff)
    bones=[orig['nodes'][i]['name'] for i in orig['skins'][0]['joints']]
    assert len(bones)==len(set(bones))==65 and len(orig['nodes'])==66
    clips={}
    for a in orig['animations']:
        changed=[]
        alltimes=[]
        kinds=[]
        for ch in a['channels']:
            idx=ch['sampler'];sam=a['samplers'][idx];path=ch['target']['path']
            kinds.append(path)
            ta=orig['accessors'][sam['input']]
            alltimes.append([ta['min'][0],ta['max'][0]])
            ac=orig['accessors'][sam['output']];v=orig['bufferViews'][ac['bufferView']]
            start=v.get('byteOffset',0);end=start+v['byteLength']
            if diff[start:end].any():
                assert path=='rotation' and ac['type']=='VEC4' and not ac.get('byteOffset')
                allowed[start:end]=True
                rows=np.frombuffer(buf[start:end],dtype='<f4').reshape(-1,4)
                assert np.max(abs(np.linalg.norm(rows,axis=1)-1))<1.e-5
                changed.append(orig['nodes'][ch['target']['node']]['name'])
        assert len(set(map(tuple,alltimes)))==1 and len(a['channels'])==72
        assert {k:kinds.count(k) for k in set(kinds)}=={'rotation':65,'translation':5,'scale':2}
        clips[a['name']]={'targets':len(kinds),'seconds':alltimes[0][1]-alltimes[0][0],
                          'changed_quaternion_outputs':changed}
    assert set(clips)==set(CLIPS) and not np.any(diff&~allowed)
    return {'byte_length':len(FIXED.read_bytes()),'identical_json_chunk_and_header':True,
            'all_differences_confined_to_rotation_output_values':True,'different_bytes':int(diff.sum()),
            'nodes':len(orig['nodes']),'joints':bones,'clips':clips}

def joins(path):
    scene,arm,body,actions=load(path)
    endpoints={}
    for clip,last in CLIPS.items():
        chibi.bind(arm,actions[clip])
        for f in (0,last):
            at(scene,f);endpoints[clip,f]=posed(body).copy()
    return {a+' -> '+b:float(np.linalg.norm(endpoints[a,CLIPS[a]]-endpoints[b,0],axis=1).max()*1000)
            for a,b in [('sit_down','sit_idle'),('sit_idle','stand_up'),('stand_up','sit_down'),('sit_idle','sit_idle'),('hold_item','hold_item')]}

def compare():
    before,after=[json.loads((OUT/f'body_selfcheck_{state}.json').read_text()) for state in ('before','after')]
    for report,path in [(before,SOURCE),(after,FIXED)]:
        assert report['action_sha256']==sha(path)
        assert report['master_sha256']==sha(MASTER)
        assert report['attachment_sha256']==sha(ASSETS/'attachment.json')
        assert report['authored_grip']['body_sha256']==sha(chibi.BODY)
    checks={'source_sha256':sha(SOURCE),'output_sha256':sha(FIXED),'container':container(),'clips':{}}
    for clip,last in CLIPS.items():
        a,b=[report['clips'][clip] for report in (before,after)]
        assert [r['frame'] for r in a['samples']]==[r['frame'] for r in b['samples']]==[t/2 for t in range(2*last+1)]
        base=a['samples'][0]
        result={'before':a['summary'],'after':b['summary']}
        rows=list(zip(a['samples'],b['samples']))
        def peak(fn):
            return max(float(fn(p,q)) for p,q in rows)
        result['max_hip_xyz_delta_mm']=peak(lambda p,q:np.linalg.norm(np.subtract(q['hips_mm'],p['hips_mm'])))
        result['max_foot_min_z_delta_mm']=peak(lambda p,q:max(abs(p['foot_min_z_mm'][s]-q['foot_min_z_mm'][s]) for s in SIDES))
        result['max_sole_xy_delta_mm']=peak(lambda p,q:max(np.linalg.norm(np.subtract(q['sole_xy_mm'][s],p['sole_xy_mm'][s]),axis=1).max() for s in SIDES))
        result['max_sole_xy_drift_from_start_mm']=peak(lambda p,q:max(np.linalg.norm(np.subtract(q['sole_xy_mm'][s],base['sole_xy_mm'][s]),axis=1).max() for s in SIDES))
        if clip!='hold_item':
            result.update(max_chair_body_pairs=peak(lambda p,q:q['chair_body_pairs']),
                          max_body_vertices_inside_chair=peak(lambda p,q:q['chair_vertices_inside']),
                          all_chair_solids_have_exterior_witness=all(q['all_chair_components_proven_exterior'] for p,q in rows))
            result['max_seat_gap_delta_mm']=peak(lambda p,q:max([abs(q['seat_gap_mm'][s]-p['seat_gap_mm'][s]) for s in SIDES if q['seat_gap_mm'][s] is not None and p['seat_gap_mm'][s] is not None] or [0]))
        else:
            for host,samples in [('master',rows),('authored_grip',list(zip(before['authored_grip']['samples'],after['authored_grip']['samples'],strict=True)))]:
                result[host]={'max_cup_body_pairs':max(q['cup_body_pairs'] for p,q in samples),
                              'pad_gap_delta_mm':{s:max(abs(q['pad_gap_mm'][s]-p['pad_gap_mm'][s]) for p,q in samples) for s in ('Thumb','Index')},
                              'after_pad_gap_range_mm':{s:[min(q['pad_gap_mm'][s] for p,q in samples),
                                                           max(q['pad_gap_mm'][s] for p,q in samples)] for s in ('Thumb','Index')}}
        checks['clips'][clip]=result
    checks['seams_mm']={label:joins(path) for label,path in [('before',SOURCE),('after',FIXED)]}
    cs=list(checks['clips'].values())
    checks['gates']={'target_zero_every_sample':all(c['after']['target_total']==0 for c in cs),
        'feet_height_delta_below_1mm':all(c['max_foot_min_z_delta_mm']<1 for c in cs),
        'sole_xy_drift_and_delta_below_1mm':all(max(c['max_sole_xy_delta_mm'],c['max_sole_xy_drift_from_start_mm'])<1 for c in cs),
        'hips_path_identical':all(c['max_hip_xyz_delta_mm']<.001 for c in cs),
        'chair_clear':all(c['all_chair_solids_have_exterior_witness'] and c['max_body_vertices_inside_chair']==c['max_chair_body_pairs']==0 for c in cs if 'max_chair_body_pairs' in c),
        'cup_clear_and_contact_delta_below_1mm':all(checks['clips']['hold_item'][s]['max_cup_body_pairs']==0 and max(checks['clips']['hold_item'][s]['pad_gap_delta_mm'].values())<1 for s in ('master','authored_grip'))}
    (OUT/'verification.json').write_text(json.dumps(checks,indent=2)+'\n')
    print('GATES',checks['gates'],flush=True)
    if not all(checks['gates'].values()):
        raise SystemExit(2)

if __name__=='__main__':compare()
