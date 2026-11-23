"""Round-trip skin/contact audit. Geometric distances in output are millimetres."""
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from chibi import *
from render_actions import mount
from mathutils.bvhtree import BVHTree

CHECK=OUT/'checks'
MM=1000
RAY=Vector((.735,.339,.587)).normalized()


def triangles(ob):
    ob.data.calc_loop_triangles()
    return [tuple(t.vertices) for t in ob.data.loop_triangles]


def solids(points,faces):
    # glTF splits vertices at normal/material seams. Weld for component labels only.
    adjacent=defaultdict(list)
    for i,tri in enumerate(faces):
        for j in tri: adjacent[tuple(points[j].round(6))].append(i)
    unvisited=set(range(len(faces)))
    parts=[]
    while unvisited:
        queue=[unvisited.pop()]
        group=[]
        while queue:
            i=queue.pop()
            group.append(faces[i])
            for j in faces[i]:
                for neighbor in adjacent[tuple(points[j].round(6))]:
                    if neighbor in unvisited:
                        unvisited.remove(neighbor);queue.append(neighbor)
        p=points[np.array(group).ravel()]
        parts.append((p.min(0),p.max(0),BVHTree.FromPolygons(points.tolist(),group,all_triangles=True)))
    return parts


def penetration(points,parts):
    depths={}
    for lo,hi,tree in parts:
        for i in np.flatnonzero(((points>=lo)&(points<=hi)).all(1)):
            p=Vector(points[i])
            hit,normal,face,d=tree.ray_cast(p,RAY)
            if hit is None or normal.dot(RAY)<=0: continue
            depth=tree.find_nearest(p)[3]*MM
            depths[i]=max(depth,depths.get(i,0))
    return len(depths),sum(d>2 for d in depths.values()),max(depths.values(),default=0)


def inventory():
    d,_=glb(OUT/'actions.glb');ref,_=glb(BODY)
    names=[n['name'] for n in d['nodes']]
    roots={d['nodes'][j]['name']:n['name'] for n in d['nodes'] for j in n.get('children',[])}
    reference={ref['nodes'][j]['name']:n['name'] for n in ref['nodes'] for j in n.get('children',[])}
    differences=[n for n in names if n.startswith(N) and roots[n]!=reference[n]]
    inv={}
    for a in d['animations']:
        ch=Counter()
        tracks=[]
        for c in a['channels']:
            sampler=a['samplers'][c['sampler']]
            sample=d['accessors'][sampler['input']]
            kind=c['target']['path']
            ch[kind]+=1
            tracks.append([names[c['target']['node']],kind,sample['min'][0],sample['max'][0],sample['count']])
            assert sampler.get('interpolation','LINEAR')=='LINEAR'
            assert kind!='rotation' or d['accessors'][sampler['output']]['type']=='VEC4'
        inv[a['name']]=dict(seconds=round(max(t[3] for t in tracks)-min(t[2] for t in tracks),6),
                           samples=max(t[4] for t in tracks),channels=dict(ch),
                           hips_translation=any(t[:2]==[N+'Hips','translation'] for t in tracks))
    def static(filename):
        content,_=glb(OUT/filename)
        return dict(meshes=len(content['meshes']),triangles=sum(content['accessors'][p['indices']]['count']//3
                    for m in content['meshes'] for p in m['primitives']),materials=len(content['materials']))
    return dict(joints=sum(n.startswith(N) for n in names),nodes=len(names),hierarchy_differences=differences,
                meshes=len(d.get('meshes',[])),clips=inv,chair=static('chair.glb'),prop=static('prop.glb'))


def raw_channels(path):
    doc,buf=glb(path)
    widths={'SCALAR':1,'VEC3':3,'VEC4':4}
    def read(i):
        acc=doc['accessors'][i]
        bv=doc['bufferViews'][acc['bufferView']]
        assert acc['componentType']==5126
        width=widths[acc['type']]
        return np.ndarray((acc['count'],width),dtype='<f4',buffer=buf,
                          offset=bv.get('byteOffset',0)+acc.get('byteOffset',0),
                          strides=(bv.get('byteStride',4*width),4)).copy()
    banks={}
    for a in doc['animations']:
        tracks={}
        for c in a['channels']:
            s=a['samplers'][c['sampler']];t=c['target']
            tracks[(doc['nodes'][t['node']]['name'],t['path'])]=read(s['output'])
        banks[a['name']]=tracks
    return doc,banks


def check_contract(arm):
    doc,banks=raw_channels(OUT/'actions.glb')
    reference,gestures=raw_channels(GESTURES)
    body,_=glb(BODY)
    def trs(n,tracks,f):
        def value(k,default):
            a=tracks.get((n['name'],k))
            return a[min(len(a)-1,f)] if a is not None else n.get(k,default)
        x,y,z,w=value('rotation',(0,0,0,1))
        return Matrix.LocRotScale(Vector(value('translation',(0,0,0))),Quaternion((w,x,y,z)),Vector(value('scale',(1,1,1))))
    ref_nodes={n['name']:n for n in body['nodes']}
    rest_error=max(float(np.abs(np.array(trs(n,{},0))-np.array(trs(ref_nodes[n['name']],{},0))).max()) for n in doc['nodes'])
    grip={}
    for track,expected in gestures['hand_grip_small_R'].items():
        if track[1]!='rotation':continue
        q=banks['hold_item'][track]
        err=np.minimum(abs(q-expected[0]).max(1),abs(q+expected[0]).max(1))
        grip[track[0]]=float(err.max())
    rotation_errors=[abs(np.linalg.norm(a,axis=1)-1).max() for tracks in banks.values() for (n,k),a in tracks.items() if k=='rotation']
    # The game attaches the imported prop node below the right-hand glTF joint.
    # Compare that chain against the separately derived Blender-bone attachment.
    cfg=json.loads((OUT/'attachment.json').read_text())['gltf_joint_local']
    gmount=trs(dict(name='prop',translation=cfg['translation_m'],rotation=cfg['quaternion_xyzw']),{},0)
    nodes=doc['nodes'];index=next(i for i,n in enumerate(nodes) if n['name']==N+'RightHand')
    parents={child:i for i,n in enumerate(nodes) for child in n.get('children',[])}
    hierarchy=[]
    while True:
        hierarchy.append(index)
        if index not in parents:break
        index=parents[index]
    C=rot(X,-90).to_matrix().to_4x4()
    bind(arm,bpy.data.actions['hold_item'])
    attach_err=0
    for f in range(CLIPS['hold_item']+1):
        bpy.context.scene.frame_set(f)
        m=Matrix.Identity(4)
        for j in reversed(hierarchy):m=m@trs(nodes[j],banks['hold_item'],f)
        engine=m@gmount
        actual=C@arm.matrix_world@arm.pose.bones[N+'RightHand'].matrix@mount()@C.inverted()
        samples=[Vector((0,0,0)),Vector((0,.05,0)),Vector((.02,0,0))]
        attach_err=max(attach_err,max((engine@v-actual@v).length*MM for v in samples))
    return dict(max_rest_matrix_component_error=rest_error,
                max_quaternion_length_error=float(max(rotation_errors)),grip_bones=len(grip),
                max_grip_quaternion_component_error=max(grip.values()),
                max_gltf_socket_witness_error_mm=attach_err)


def run():
    CHECK.mkdir(exist_ok=True)
    summary={'inventory':inventory(),'clips':{}}
    fresh();arm=armature(load(BODY));body=bpy.data.objects['Base_Body']
    btri=triangles(body)
    rest=coords(body)
    summary['body']={'vertices':len(rest),'triangles':len(btri),'height_m':float(np.ptp(rest[:,2]))}
    load(OUT/'actions.glb')
    chair,=load(OUT/'chair.glb');prop,=load(OUT/'prop.glb')
    cp=coords(chair);ct=triangles(chair)
    pp=coords(prop);pt=triangles(prop)
    parts=solids(cp,ct)
    summary['chair_closed_parts']=len(parts)
    ctree=BVHTree.FromPolygons(cp.tolist(),ct,all_triangles=True)
    # Use the hand library's fixed bind-space pad labels and vertex/face plus edge/edge distances.
    sys.path.insert(0,str(HANDS))
    from hand_common import rest_data
    from hand_check import hand_geometry
    from hand_surface import patches,nearest
    tips,*_=rest_data(body,arm,'Right')
    sets=patches(body,arm,'Right',tips,hand_geometry(body,'Right',-1,tips))
    ptri=[tuple(i+len(rest) for i in face) for face in pt]
    feet={}
    for side,sg in [('left',1),('right',-1)]:
        idx=np.where((sg*rest[:,0]>0)&(rest[:,2]<.0011))[0]
        feet[side]=dict(sole=idx,heel=idx[rest[idx,1]>.021],forefoot=idx[rest[idx,1]<-.05])
    summary['support_vertex_counts']={s:{k:len(v) for k,v in masks.items()} for s,masks in feet.items()}
    first={}
    last={}
    mnt=mount()
    for name in CLIPS:
        action=bpy.data.actions[name];bind(arm,action)
        rows=[]
        for f in range(round(action.frame_range[0]),round(action.frame_range[1])+1):
            bpy.context.scene.frame_set(f)
            p=coords(body)
            if f==0:first[name]=p
            hip=arm.pose.bones[N+'Hips'].head
            row={'frame':f,'top_z_mm':float(p[:,2].max()*MM),'hips_y_mm':float(hip.y*MM),'hips_z_mm':float(hip.z*MM),'floor_min_mm':float(p[:,2].min()*MM),'below_minus_1mm':int((p[:,2]<-.001).sum())}
            bt=BVHTree.FromPolygons(p.tolist(),btri,all_triangles=True)
            for side,selections in feet.items():
                for region in ['heel','forefoot']:
                    row[side+'_'+region+'_mm']=float(p[selections[region],2].min()*MM)
                ids=selections['sole']
                # Common reference is the standing pose of this sequence.
                ref=first['hold_item'] if name=='hold_item' else first['sit_down']
                row[side+'_sole_drift_mm']=float(np.linalg.norm(p[ids,:2]-ref[ids,:2],axis=1).max()*MM)
            if name!='hold_item':
                raw,over,depth=penetration(p,parts)
                row.update(chair_vertices_inside=raw,chair_vertices_over_2mm=over,chair_deepest_mm=depth,
                           chair_triangle_pairs=len(ctree.overlap(bt)))
                hip=arm.pose.bones[N+'Hips'].head
                for side,sg in [('Left',1),('Right',-1)]:
                    knee=arm.pose.bones[N+side+'Leg'].head
                    thigh=arm.pose.bones[N+side+'UpLeg'].head-knee
                    calf=knee-arm.pose.bones[N+side+'Foot'].head
                    row[side.lower()+'_thigh_from_horizontal_deg']=abs(math.degrees(math.asin(thigh.normalized().z)))
                    row[side.lower()+'_shin_from_vertical_deg']=math.degrees(math.atan2(math.hypot(calf.x,calf.y),calf.z))
                    # Flat area of the cushion under the buttock and proximal thigh.
                    sel=(rest[:,2]>.21)&(rest[:,2]<.41)&(sg*p[:,0]>.008)&(sg*p[:,0]<.142)&(abs(p[:,1]-hip.y)<.054)&(abs(p[:,1])<.098)
                    candidate=p[sel,2]-float(chair['seat_height_m'])
                    if len(candidate):
                        row[side.lower()+'_seat_gap_mm']=float(candidate.min()*MM)
                        row[side.lower()+'_seat_witnesses_2mm']=int((abs(candidate)<.002).sum())
                    else:
                        row[side.lower()+'_seat_gap_mm']=None
                        row[side.lower()+'_seat_witnesses_2mm']=0
            else:
                hand=arm.pose.bones[N+'RightHand']
                mat=np.array(arm.matrix_world@hand.matrix@mnt)
                cup=pp@mat[:3,:3].T+mat[:3,3]
                tree=BVHTree.FromPolygons(cup.tolist(),pt,all_triangles=True)
                row['cup_body_triangle_pairs']=len(tree.overlap(bt))
                combined=np.concatenate([p,cup])
                for key in ['Thumb','Index']:
                    contact=nearest(combined,sets[key],ptri)
                    row[key.lower()+'_pad_gap_mm']=contact['distance_mm']
                elbow=arm.pose.bones[N+'RightForeArm'].head
                row['elbow_flexion_deg']=180-math.degrees((arm.pose.bones[N+'RightArm'].head-elbow).angle(hand.head-elbow))
                row['cup_center_z_mm']=float(mat[2,3]*MM)
            rows.append(row)
        last[name]=p
        with (CHECK/(name+'.csv')).open('w') as fp:
            w=csv.DictWriter(fp,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
        metrics={}
        for k in rows[0]:
            values=[r[k] for r in rows if r[k] is not None]
            if k!='frame' and values:
                metrics[k]={'min':round(min(values),6),'max':round(max(values),6)}
        summary['clips'][name]=dict(frames=len(rows),measurements=metrics)
        print('CHECK',name,metrics,flush=True)
    # Blender replays the import continuously. Check the halfway points too,
    # where independently interpolated joint channels can move a planted sole.
    between={}
    ref=first['sit_down']
    sole=np.concatenate([m['sole'] for m in feet.values()])
    for name in ('sit_down','sit_idle','stand_up'):
        bind(arm,bpy.data.actions[name])
        floor_min=math.inf
        drift=0
        pairs=0
        for f in range(CLIPS[name]):
            bpy.context.scene.frame_set(f,subframe=.5)
            p=coords(body)
            floor_min=min(floor_min,float(p[:,2].min()*MM))
            drift=max(drift,float(np.linalg.norm(p[sole,:2]-ref[sole,:2],axis=1).max()*MM))
            bt=BVHTree.FromPolygons(p.tolist(),btri,all_triangles=True)
            pairs=max(pairs,len(ctree.overlap(bt)))
        between[name]=dict(samples=CLIPS[name],min_floor_mm=floor_min,max_sole_drift_mm=drift,
                           max_chair_triangle_pairs=pairs)
    summary['half_frame_checks']=between
    joins={}
    for a,b in [('sit_down','sit_idle'),('sit_idle','sit_idle'),('sit_idle','stand_up'),('stand_up','sit_down'),('hold_item','hold_item')]:
        joins[a+' -> '+b]=float(np.linalg.norm(last[a]-first[b],axis=1).max()*MM)
    summary['maximum_mesh_seam_mm']=joins
    summary['round_trip']=check_contract(arm)
    gates={}
    inv=summary['inventory']
    gates['contract']=inv['joints']==65 and not inv['hierarchy_differences'] and inv['meshes']==0
    gates['inventory']=set(inv['clips'])==set(CLIPS) and all(
        abs(inv['clips'][n]['seconds']-frames/FPS)<1e-6 and inv['clips'][n]['hips_translation']
        for n,frames in CLIPS.items())
    gates['triangle_budgets']=800<=inv['chair']['triangles']<=1500 and 200<=inv['prop']['triangles']<=600
    for n,clip in summary['clips'].items():
        m=clip['measurements']
        gates[n+'_floor']=m['below_minus_1mm']['max']==0
        if n!='hold_item':
            gates[n+'_chair']=m['chair_vertices_over_2mm']['max']==0 and m['chair_triangle_pairs']['max']==0
            gates[n+'_plant']=max(m[s+'_sole_drift_mm']['max'] for s in ['left','right'])<.01
        else:
            gates['grasp']=m['cup_body_triangle_pairs']['max']==0 and max(m[s+'_pad_gap_mm']['max'] for s in ['thumb','index'])<1
    seated=summary['clips']['sit_idle']['measurements']
    gates['pelvis_support']=all(seated[s+'_seat_witnesses_2mm']['min']>0 for s in ['left','right'])
    gates['loop_and_transition_continuity']=max(joins.values())<.01
    rt=summary['round_trip']
    gates['same_grip']=rt['grip_bones']==20 and rt['max_grip_quaternion_component_error']<1e-5
    gates['same_bind']=rt['max_rest_matrix_component_error']<.00001
    gates['socket']=rt['max_gltf_socket_witness_error_mm']<.01
    summary['gates']=gates
    (CHECK/'actions.json').write_text(json.dumps(summary,indent=2)+'\n')


    assert all(gates.values()),gates


if __name__=='__main__':run()
