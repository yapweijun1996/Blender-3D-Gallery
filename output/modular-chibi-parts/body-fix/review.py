"""Inspect pose evidence and evaluate the foot and target-zone gates."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from bodycheck import *
from clearance import SIDES,kind,arm_contact,knee_contact


def zones(a,b):
    kinds={kind(a),kind(b)}
    if len(kinds)==2 and 'body' in kinds:
        if 'Leg' in a+b or 'Hips' in (a,b) or 'Foot' in a+b or 'Toe' in a+b:return 'arm_vs_lower_body'
        return 'arm_vs_torso_or_head'
    if any(knee_contact(a,b,s) for s in SIDES):return 'shin_vs_thigh'
    if 'Hand' in a and 'Hand' in b:return 'hand_internal'
    if a==b=='Head':return 'head_internal'
    if 'Foot' in a+b or 'Toe' in a+b:return 'foot_or_ankle'
    if a.endswith('UpLeg') or b.endswith('UpLeg') or 'Hips' in (a,b):return 'thigh_or_pelvis'
    return 'other_local_folds'


def aggregate(records):
    totals=Counter()
    worst=(0,None)
    for f in records:
        for label,reg in f['region_pairs'].items():
            totals[zones(*label.split(' / '))]+=reg['count']
            worst=max((reg['max_depth_mm'],(f['frame'],label)),worst)
    return {'groups':dict(totals),'deepest':worst}


def rest_components(body,checker,record):
    # Connect triangles via exact rest-position IDs, including chart twins.
    parent=list(range(len(body.data.vertices)))
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]
            i=parent[i]
        return i
    for ids in checker.surface_sets:
        first=next(iter(ids))
        for i in ids:
            a,b=root(first),root(i)
            parent[max(a,b)]=min(a,b)
    components=[root(next(iter(f))) for f in checker.surface_sets]
    counts=Counter()
    for label,region in record['region_pairs'].items():
        for i,j,d in region['triangles_and_depth_mm']:
            a,b=sorted((components[i],components[j]))
            counts[f'{label} | component {a} + {b}']+=1
    return {'component_triangle_counts':dict(Counter(components)),'pairs_in_neutral_pose':dict(counts)}


def verify_container():
    from bake import MotionFile
    a,b=MotionFile(SOURCE),MotionFile(OUT/'motion_fixed.glb')
    assert b.buffer[:len(a.buffer)]==a.buffer
    exempt={'accessors','bufferViews','animations','buffers'}
    assert {k:v for k,v in a.doc.items() if k not in exempt}=={k:v for k,v in b.doc.items() if k not in exempt}
    for key in ('accessors','bufferViews'):
        assert b.doc[key][:len(a.doc[key])]==a.doc[key]
    nodes=a.doc['nodes']
    assert len(a.doc['skins'])==1
    bones={nodes[i]['name'] for i in a.doc['skins'][0]['joints']}
    assert len(bones)==65
    stats={}
    for original,fixed in zip(a.doc['animations'],b.doc['animations'],strict=True):
        assert original['name']==fixed['name'] and original['channels']==fixed['channels']
        channels=fixed['channels']
        assert {nodes[c['target']['node']]['name'] for c in channels}==bones
        assert len(channels)==195
        changed=[]
        for c in channels:
            old,new=(d['samplers'][c['sampler']] for d in (original,fixed))
            if old==new: continue
            bone_name=nodes[c['target']['node']]['name']
            assert 'Hand' not in bone_name
            t0,t1=a.doc['accessors'][old['input']],b.doc['accessors'][new['input']]
            assert np.allclose([t0['min'],t0['max']],[t1['min'],t1['max']],atol=1e-6)
            changed.append((bone_name,c['target']['path']))
        stats[fixed['name']]={'joints':len(bones),'channels':195,'unchanged_channel_samplers':195-len(changed)}
    return {'source_binary_prefix_identical':True,'source_mesh_skin_hierarchy_materials_images_identical':True,
            'source_hand_and_finger_samplers_identical':True,'clips':stats}


def review():
    before,after=[json.loads((OUT/f'body_selfcheck_{s}.json').read_text()) for s in ['before','after']]
    result={}
    for cl in CLIPS:
        rows=[d['clips'][cl]['samples'] for d in (before,after)]
        assert [f['frame'] for f in rows[0]]==[f['frame'] for f in rows[1]]
        max_foot=max((abs(f['foot_min_z_mm'][s]-g['foot_min_z_mm'][s]),f['frame'],s)
                     for f,g in zip(*rows) for s in SIDES)
        result[cl]={'before':aggregate(rows[0]),'after':aggregate(rows[1]),'max_foot_delta_mm_frame_side':max_foot}
        print('REVIEW',cl,result[cl],flush=True)
    # Evaluate intermediate poses from actual input and output channels.
    mid={}
    for state,path in [('before',SOURCE),('after',OUT/'motion_fixed.glb')]:
        scene,arm,body,_=load(path);c=Checker(body)
        if state=='before':rest=rest_components(body,c,before['source_rest_pose'])
        for cl in CLIPS:
            fs=bind(arm,cl)
            records=[]
            for f in list(fs)[:-1]:
                scene.frame_set(f,subframe=.5);p=posed(body)
                pairs,_=c.overlap(p)
                hits=Counter(zones(c.regions[i],c.regions[j]) for i,j in pairs)
                rec={'frame':f+.5,'foot':{s:float(p[c.feet[s],2].min()*1000) for s in SIDES},
                     'key_contacts':{k:hits[k] for k in ('arm_vs_lower_body','arm_vs_torso_or_head','shin_vs_thigh')}}
                records.append(rec)
            mid[cl,state]=records
    for cl in CLIPS:
        maxerr=max((abs(b['foot'][s]-a['foot'][s]),b['frame'],s) for a,b in zip(mid[cl,'before'],mid[cl,'after']) for s in SIDES)
        result[cl]['half_frame_max_foot_delta_mm_frame_side']=maxerr
        hits={k:sum(r['key_contacts'][k] for r in mid[cl,'after']) for k in ('arm_vs_lower_body','arm_vs_torso_or_head','shin_vs_thigh')}
        result[cl]['half_frame_after_target_counts']=hits
        print('MID',cl,maxerr,hits,flush=True)
    target_zones=('arm_vs_lower_body','arm_vs_torso_or_head','shin_vs_thigh')
    target_integer=sum(c['after']['groups'].get(k,0) for c in result.values() for k in target_zones)
    target_half=sum(sum(c['half_frame_after_target_counts'].values()) for c in result.values())
    foot_max=max(max(c['max_foot_delta_mm_frame_side'][0],c['half_frame_max_foot_delta_mm_frame_side'][0]) for c in result.values())
    remaining=sum(c['sum_pairs'] for c in after['clips'].values())
    gates={'integer_target_pairs':target_integer,'half_frame_target_pairs':target_half,
           'foot_height_max_delta_mm_all_samples':foot_max,'all_body_integer_pairs':remaining,
           'whole_body_zero':remaining==0}
    (OUT/'verification.json').write_text(json.dumps({'gates':gates,'container':verify_container(),'rest_topology':rest,'clips':result},indent=2)+'\n')
    assert target_integer==0 and target_half==0 and foot_max<=1, gates


if __name__=='__main__':
    review()
