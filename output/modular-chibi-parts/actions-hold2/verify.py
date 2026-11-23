"""Fail on any missed gate. Compare the socket replay against raw glTF transform chains."""
import csv
import hashlib
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from module_checks import MODULES
from audit import set_time,triangles,group_labels,local_coords,apply
sys.path.insert(0,str(PARTS/'hand-gestures-astra/round2'))
from hand_surface import nearest

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def hierarchy(doc):
    nodes=doc['nodes']
    return {nodes[j]['name']:n['name'] for n in nodes for j in n.get('children',[])}

def read_float(doc,buf,i):
    a=doc['accessors'][i];v=doc['bufferViews'][a['bufferView']]
    width={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]
    assert a['componentType']==5126
    return np.ndarray((a['count'],width),dtype='<f4',buffer=buf,
                      offset=v.get('byteOffset',0)+a.get('byteOffset',0),
                      strides=(v.get('byteStride',4*width),4))

def load_tracks(doc,buf):
    banks={}
    for a in doc['animations']:
        tracks={}
        for channel in a['channels']:
            i=channel['target']['node'];sampler=a['samplers'][channel['sampler']]
            assert channel['target']['path']=='rotation'
            assert sampler.get('interpolation','LINEAR')=='LINEAR'
            t=read_float(doc,buf,sampler['input']).ravel()
            assert len(t)==49 and np.max(np.abs(t-np.arange(49)/FPS))<1e-7
            r=read_float(doc,buf,sampler['output'])
            assert i not in tracks and r.shape==(49,4)
            tracks[i]=r
        banks[a['name']]=tracks
    return banks

def quaternion(xyzw):
    x,y,z,w=xyzw
    return Quaternion((w,x,y,z))

def socket_chain(doc,chain,tracks,frame):
    whole=int(frame);half=frame-whole
    out=Matrix.Identity(4)
    for i in chain:
        n=doc['nodes'][i]
        if i in tracks:
            values=tracks[i];q=quaternion(values[whole])
            if half:
                # At exactly one half SLERP is the normalized sign-aligned sum.
                # A near-parallel, unnormalized lerp would scale the child chain.
                pair=np.array(values[whole:whole+2],dtype=float)
                if np.dot(pair[0],pair[1])<0:pair[1]*=-1
                middle=pair.sum(0)
                q=quaternion(middle/np.linalg.norm(middle))
        else:q=quaternion(n.get('rotation',[0,0,0,1]))
        local=Matrix.LocRotScale(Vector(n.get('translation',[0]*3)),q,Vector(n.get('scale',[1]*3)))
        out=out@local
    return out

def contract():
    doc,buf=glb(BANK);reference,_=glb(BODY);banks=load_tracks(doc,buf)
    names={n['name']:i for i,n in enumerate(doc['nodes'])}
    ref={n['name']:i for i,n in enumerate(reference['nodes'])}
    joints={n for n in ref if n.startswith(N)}
    assert len(joints)==65 and joints=={n for n in names if n.startswith(N)}
    assert set(banks)==set(NAMES) and not doc.get('meshes')
    a,b=hierarchy(doc),hierarchy(reference)
    assert all(a[n]==b[n] for n in joints)
    rest_error=max(float(np.abs(np.array(node_world(doc,names[n]))-np.array(node_world(reference,ref[n]))).max()) for n in joints)
    assert rest_error<.00002
    chain=[];n=N+'RightHand'
    while True:
        chain.append(names[n])
        if n not in a:break
        n=a[n]
    chain.reverse()
    sc=setup();arm=armature(load(BODY));body=bpy.data.objects['Base_Body']
    body.data.calc_loop_triangles()
    geometry={'vertices':len(body.data.vertices),'triangles':len(body.data.loop_triangles),'height_m':float(np.ptp(coords(body)[:,2]))}
    assert geometry['triangles']==9512
    labels=group_labels(body)
    head=[tuple(t.vertices) for t in body.data.loop_triangles if any(labels[i]=='Head' for i in t.vertices)]
    load(BANK)
    rows={}
    for name,tracks in banks.items():
        assert set(tracks)=={names[n] for n in joints}
        qerr=float(max(np.max(abs(np.linalg.norm(q,axis=1)-1)) for q in tracks.values()))
        assert qerr<1e-5
        cfg=json.loads((HERE/'props'/(FILES[name]+'.attachment.json')).read_text())
        engine_mount=matrix(cfg['gltf_joint_local'])
        bind(arm,bpy.data.actions[name])
        moving=next(o for o in load(HERE/cfg['prop']) if o.name==cfg['node'])
        vertices=np.array([tuple(C@v.co) for v in moving.data.vertices])
        vertices=np.column_stack((vertices,np.ones(len(vertices))))
        max_probe=0
        max_integer=0
        witnesses=[Vector(p) for p in ((0,0,0),(.16,0,0),(0,.22,0),(0,0,-.25))]
        error=0;world=[];tilts=[]
        chin_gap=float('inf')
        if name=='hold_box':
            box_verts=local_coords(moving)
            demo_verts=len(body.data.vertices)
            box_faces=[tuple(i+demo_verts for i in face) for face in triangles(moving)]
        for f in [i/2 for i in range(97)]:
            set_time(sc,f)
            if name=='take_item' and f<GRIP:
                x=matrix(cfg['return_stop_gltf']);y=matrix(cfg['pickup_stop_gltf'])
                u=max(0,min(1,(f-cfg['return_frames'][0])/float(cfg['return_frames'][1]-cfg['return_frames'][0])))
                engine=x.lerp(y,u*u*(3-2*u))
            else:
                engine=socket_chain(doc,chain,tracks,f)@engine_mount
            physical=equipment(name,arm,f,cfg)
            blender=C@physical@C.inverted()
            delta=(np.array(engine)-np.array(blender))[:3]
            distance=float(np.linalg.norm(vertices@delta.T,axis=1).max()*1000)
            error=max(error,distance)
            if f==int(f):max_integer=max(max_integer,distance)
            max_probe=max(max_probe,max((engine@v-blender@v).length*1000 for v in witnesses))
            if name=='hold_box':
                body_pts=coords(body)
                box_pts=apply(box_verts,physical)
                # The omitted upper-head faces have a world-Z lower bound of 60 mm.
                top=box_pts[:,2].max()
                chin=[face for face in head if min(body_pts[i,2] for i in face)<top+.060]
                measurement=nearest(np.vstack((body_pts,box_pts)),chin,box_faces)['distance_mm']
                assert measurement<60
                chin_gap=min(chin_gap,measurement)
            world.append(physical.copy())
            tilts.append(math.degrees(physical.to_euler('XYZ').x))
        seam=max((world[0]@v-world[-1]@v).length*1000 for v in witnesses)
        print('ACTUAL SOCKET',name,error,max_probe,max_integer,flush=True)
        assert max(error,max_probe,max_integer,seam)<.01,(name,error,max_probe,seam)
        props,_=glb(HERE/cfg['prop'])
        prop_triangles=sum(props['accessors'][p['indices']]['count']//3 for m in props['meshes'] for p in m['primitives'])
        assert prop_triangles<=1500 and not props.get('textures')
        centers=np.array([m.translation[:] for m in world])
        rows[name]=dict(duration_s=2,fps=24,rotation_tracks=len(tracks),translation_tracks=0,scale_tracks=0,
                        prop_triangles=prop_triangles,prop_materials=len(props['materials']),prop_nodes=[n['name'] for n in props['nodes']],
                        max_quaternion_norm_error=qerr,prop_loop_seam_mm=seam,
                        gltf_vs_blender_vertex_max_mm=error,gltf_vs_blender_integer_max_mm=max_integer,
                        gltf_vs_blender_250mm_probe_max_mm=max_probe,prop_origin_travel_xyz_mm=(np.ptp(centers,axis=0)*1000).tolist(),
                        prop_x_tilt_range_deg=[min(tilts),max(tilts)])
        if name=='hold_box':
            assert chin_gap>0
            rows[name]['minimum_head_to_box_surface_mm']=chin_gap
        if name=='take_item':
            target=matrix(cfg['pickup_stop_blender'])
            transfer=max((world[2*GRIP]@v-target@v).length*1000 for v in witnesses)
            assert transfer<.01
            rows[name].update(attach_frame=GRIP,attach_snap_mm=transfer)
    return dict(bind_world_matrix_max_component_error=rest_error,demo=geometry,joints=65,clips=rows)

def measurements(name,model):
    p=HERE/'checks'/(name+('_master' if model=='master' else '')+'.csv')
    with p.open() as fp:rows=list(csv.DictReader(fp))
    assert [float(r['frame']) for r in rows]==[i/2 for i in range(97)]
    def peak(key):return max(float(r[key]) for r in rows)
    peak_target=int(peak('target_pairs'))
    pairs=max([int(peak('item_pairs'))]+([int(peak('shelf_pairs')),int(peak('first_pick_pairs'))] if name=='take_item' else []))
    enclosed=max([int(peak('item_enclosed'))]+([int(peak('shelf_enclosed')),int(peak('first_pick_enclosed'))] if name=='take_item' else []))
    floor=min(float(r['floor_mm']) for r in rows)
    drift=peak('sole_drift_mm');foot_ht=max(peak(side+part) for side in ('Left','Right') for part in ('_heel_mm','_toe_mm'))
    seam=float(rows[-1]['seam_mm'])
    grip={s:max(float(r[s+'_finger_mm']) for r in rows if name!='take_item' or float(r['frame'])>=GRIP)
          for s in (('Left','Right') if name=='hold_box' else ('Right',))}
    return dict(samples=len(rows),max_target_body_pairs=peak_target,peak_all_body_pairs=int(peak('all_pairs')),
                max_prop_body_pairs=pairs,max_enclosed_shells=enclosed,
                prop_penetration_mm=0 if pairs==enclosed==0 else None,grip_max_mm=grip,min_floor_mm=floor,
                sole_drift_mm=drift,sole_patch_max_height_mm=foot_ht,body_loop_seam_mm=seam,
                pass_gate=peak_target==pairs==enclosed==0 and max(grip.values())<3 and floor>=-1
                          and drift<.001 and foot_ht<1 and seam<.01)

def summarize():
    result=contract()
    validator=json.loads((HERE/'checks/khronos.json').read_text())
    required=['hold_actions.glb']+['props/'+v+'.glb' for v in FILES.values()]
    assert set(validator)==set(required)
    result['files']={p:dict(sha256=sha(HERE/p),errors=validator[p]['issues']['numErrors'],
                            warnings=validator[p]['issues']['numWarnings']) for p in required}
    result['inputs_sha256']={str(p.relative_to(PARTS.parents[1])):sha(p) for p in
                             [MASTER,BODY,GESTURES,FIXED,ASTRA/'actions.glb',*MODULES.values()]}
    passed=all(x['errors']==x['warnings']==0 for x in result['files'].values())
    for n,stats in result['clips'].items():
        stats['body_and_prop']={m:measurements(n,m) for m in ('demo','master')}
        stats['modules']={}
        for label in MODULES:
            folder=HERE/'checks'/label
            v,t=[json.loads((folder/(f+'_frames.json')).read_text())[n] for f in ('motion_check','motion_check_tri')]
            assert all([r['frame'] for r in a]==[i/2 for i in range(97)] for a in (v,t))
            stats['modules'][label]=dict(samples=len(v),inside_vertices=max(r['count'] for r in v),
                                         intersecting_pairs=max(r['count'] for r in t),
                                         min_gap_mm=min(r['min_signed_m'] for r in v)*1000,
                                         min_floor_mm=min(r['garment_min_z_m'] for r in t)*1000)
        mods=stats['modules']
        passed=passed and all(v['pass_gate'] for v in stats['body_and_prop'].values())
        passed=passed and all(v['inside_vertices']==v['intersecting_pairs']==0 for v in mods.values())
        footwear=json.loads((HERE/'checks/grounded.json').read_text())[n]
        stats['shod_scene']=footwear
        passed=passed and all(m['pass_gate'] for m in footwear.values())
    result['gates_pass']=passed
    (HERE/'checks/summary.json').write_text(json.dumps(result,indent=2)+'\n')
    for k,s in result['clips'].items():
        print('CHECK',k,s['body_and_prop'],flush=True)
    assert passed,'See checks/summary.json for failed gates'

if __name__=='__main__':summarize()
