"""Verify the delivered glTF transforms with the reimported, deformed female mesh."""
import hashlib
import heapq
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_geometry import *
from chair_fit import BASE_CHAIR, ChairFit, seated

THUMB_INDEX = ('Thumb', 'Index')
DEPTH_PRECISION_MM = .10
DEPTH_EARLY_BOUND_MM = .60

def unique_edges(f):
    return np.unique(np.sort(np.array(f)[:,[0,1,1,2,2,0]].reshape(-1,2),axis=1),axis=0)

def compact_tree(p, f):
    used, inverse = np.unique(f,return_inverse=True)
    return tree(p[used],inverse.reshape(-1,3).tolist())

def gap(p, pf, q, qf, qbvh):
    """Exact nearest triangle distance: intersection, vertex/face, and edge/edge."""
    vertices = p[np.unique(pf)]
    best = near(qbvh, vertices)
    lo, hi = vertices.min(0)-best,vertices.max(0)+best
    q_xyz = q[np.asarray(qf)]
    select = ((q_xyz.max(1)>=lo)&(q_xyz.min(1)<=hi)).all(1)
    if not select.any():
        return best
    relevant = np.asarray(qf)[select]
    pbvh = compact_tree(p,pf)
    small_q = compact_tree(q,relevant)
    if pbvh.overlap(small_q):
        return 0.
    v = q[np.unique(relevant)]
    best = min(best,near(pbvh,v))
    edges = q[unique_edges(relevant)]
    e_lo,e_hi=edges.min(1),edges.max(1)
    for a,b in p[unique_edges(pf)]:
        test = ((e_hi>=np.minimum(a,b)-best)&(e_lo<=np.maximum(a,b)+best)).all(1)
        v=edges[test,1]-edges[test,0]
        s=edges[test,0]
        u=b-a
        w=a-s
        aa=u@u
        ab=v@u
        bb=np.einsum('ij,ij->i',v,v)
        ac=w@u
        bc=np.einsum('ij,ij->i',v,w)
        determinant=aa*bb-ab**2
        finite=determinant>1e-12*aa*bb
        denominator=np.where(finite,determinant,1)
        first=(ab*bc-bb*ac)/denominator
        second=(aa*bc-ab*ac)/denominator
        finite &= (first>=0)&(first<=1)&(second>=0)&(second<=1)
        if finite.any():
            distances = w[finite]+first[finite,None]*u-second[finite,None]*v[finite]
            best=min(best,float(np.linalg.norm(distances,axis=1).min()))
    return best

def depth_bound(triangles, solid, lower):
    """Bound inward surface depth, including the interior of intersecting triangles."""
    queue = []
    serial = 0
    upper = lower

    def sample(a, b, c):
        nonlocal lower, serial, upper
        center = (a+b+c)/3
        dist = solid.bvh.find_nearest(center)[3]
        signed_distance = dist if dist < 1e-6 or interior(solid.bvh, center) else -dist
        lower = max(lower, signed_distance)
        # Signed distance to a closed solid is 1-Lipschitz.
        ceiling = signed_distance + max((a-center).length,(b-center).length,(c-center).length)
        if ceiling <= max(DEPTH_EARLY_BOUND_MM,lower+DEPTH_PRECISION_MM):
            upper = max(upper,ceiling)
        else:
            serial += 1
            heapq.heappush(queue, (-ceiling,serial,a,b,c))

    for tri in triangles:
        sample(*(Vector(v) for v in tri))
    splits = 0
    while queue and -queue[0][0] > max(DEPTH_EARLY_BOUND_MM,lower+DEPTH_PRECISION_MM) and splits < 1800:
        _,_,a,b,c = heapq.heappop(queue)
        ab,bc,ca=(a+b)*.5,(b+c)*.5,(c+a)*.5
        for tri in ((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)):
            sample(*tri)
        splits += 1
    unresolved = -queue[0][0] if queue else 0.
    return lower,max(lower,upper,unresolved)


def penetration(p, pf, body, prop_solids):
    """Check intersection and enclosure in both mesh directions."""
    max_lower=max_upper=0.
    pairs=skin_inside=prop_inside=0
    pfa=np.asarray(pf)
    for solid in prop_solids:
        if (body.hi < solid.lo).any() or (body.lo > solid.hi).any():
            continue
        overlaps=body.bvh.overlap(solid.bvh)
        skin=solid.enclosed(p)
        used=np.unique(solid.f)
        inside_prop=body.enclosed(solid.p[used])
        pairs+=len(overlaps)
        skin_inside+=len(skin)
        prop_inside+=len(inside_prop)
        if not (overlaps or skin or inside_prop):
            continue
        tri_a=np.asarray(sorted({a for a,_ in overlaps}),dtype=int)
        tri_b=np.asarray(sorted({b for _,b in overlaps}),dtype=int)
        if skin:
            tri_a=np.union1d(tri_a,np.flatnonzero(np.isin(pfa,list(skin)).any(1)))
        fa=np.asarray(solid.f)
        if inside_prop:
            tri_b=np.union1d(tri_b,np.flatnonzero(np.isin(fa,used[list(inside_prop)]).any(1)))
        a,b=depth_bound(p[pfa[tri_a]],solid,max(skin.values(),default=0.))
        c,d=depth_bound(solid.p[fa[tri_b]],body,max(inside_prop.values(),default=0.))
        max_lower=max(max_lower,a,c)
        max_upper=max(max_upper,b,d)
    return dict(triangle_pairs=pairs,body_inside_prop_vertices=skin_inside,
                prop_inside_body_vertices=prop_inside,depth_mm=max_lower,depth_upper_mm=max_upper)

def blend(a,b,u):
    t0,q0,_=a.decompose()
    t1,q1,_=b.decompose()
    return Matrix.LocRotScale(t0.lerp(t1,u),q0.slerp(q1,u),Vector((1,1,1)))

def fraction(f, a, b):
    u=np.clip((f-a)/(b-a),0.,1.)
    return u*u*(3-2*u)

def prop_pose(stage, clip, cfg, seconds, repeat=False):
    if clip=='take_item':
        shelf=cfg['shelf']
        f=seconds*shelf['fps']
        if f < shelf['attach_frame']-1e-9:
            pick=trs(shelf['pickup_stop_gltf'])
            if not repeat:
                return B @ pick @ G
            home=trs(shelf['return_stop_gltf'])
            release=trs(shelf['release_pose_gltf'])
            start,end=shelf['return_frames']
            lift_end=shelf.get('reset_lift_frame',0)
            lift=trs(shelf['reset_lift_stop_gltf']) if lift_end else release
            if f<lift_end:
                target=blend(release,lift,fraction(f,0,lift_end))
            elif f<start:
                target=blend(lift,home,fraction(f,lift_end,start))
            else:
                target=blend(home,pick,fraction(f,start,end))
            return B @ target @ G
    return stage.hand(seconds) @ trs(cfg['gltf_joint_local']) @ G

def prop_audit(stage, clip, cfg, patches):
    asset,node,_,fps,end=PROPS[clip]
    assert cfg['node']==node and cfg['bone']==N+'RightHand'
    assert abs(np.linalg.norm(cfg['gltf_joint_local']['quaternion_xyzw'])-1) < 1e-6
    objects=stage.asset(asset)
    prop=objects[node]
    prop_p=points(prop)*1000
    prop_f=faces(prop)
    part_faces=list(components(prop_p/1000,prop_f))
    grip_faces=prop_f
    if clip=='hold_bag':
        grip_faces=next(part for part in part_faces
                        if (bounds:=mesh_bounds(prop_p,part))[1][2]>-1
                        and bounds[0][2]>-22 and bounds[1][1]-bounds[0][1]>105)
    grip_tree=tree(prop_p,grip_faces)
    all_tree=tree(prop_p,prop_f)
    shelf_solids=[]
    if clip=='take_item':
        assert cfg['shelf']['fps']==fps and cfg['shelf']['cycle_frames']==end
        assert cfg['shelf']['attach_frame']==29 and cfg['shelf']['release_frame']==0
        shelf_obj=objects[cfg['shelf']['node']]
        raw=points(shelf_obj)
        scl=B @ trs(cfg['shelf']['world_gltf']) @ G
        shelf_p=transform(raw,scl)*1000
        shelf_f=faces(shelf_obj)
        shelf_solids=[Solid(shelf_p,part) for part in components(raw,shelf_f)]
        deck=[f for f in shelf_f if np.max(abs(raw[list(f),2]-.442))<1e-6]
        deck_tree=tree(shelf_p,deck)
    sides=['Right']+(['Left'] if clip=='hold_box' else [])
    head_faces=[f for f in stage.faces if any(stage.labels[i]==N+'Head' for i in f)]
    bone=stage.arm.pose.bones[N+'RightHand']
    conversion=(stage.arm.matrix_world @ bone.bone.matrix_local).inverted() @ B @ stage.motion.world(N+'RightHand')
    rows=[]
    for sample,t in enumerate(time_grid(fps,end)):
        if sample and sample%40==0:
            print('Sampled',clip,sample,flush=True)
        p=stage.frame(clip,t)*1000
        body=Solid(p,stage.faces)
        jraw=stage.hand(t)
        jimport=stage.arm.matrix_world @ bone.matrix @ conversion
        probes=((0.,0.,0.),(.25,0.,0.),(0.,.25,0.),(0.,0.,.25))
        replay_error=1000*max((jraw@Vector(w)-jimport@Vector(w)).length for w in probes)
        m=prop_pose(stage,clip,cfg,t)
        local=transform(p*.001,m.inverted())*1000
        posed=transform(prop_p*.001,m)*1000
        primary=penetration(p,stage.faces,body,[Solid(posed,f) for f in part_faces])
        row=dict(frame=t*fps,seconds=t,joint_replay_error_mm=replay_error,
                 prop=primary, up_from_vertical_deg=math.degrees(math.acos(float(np.clip(m[2][2],-1.,1.)))))
        if clip!='take_item' or t >= cfg['shelf']['attach_frame']/fps-1e-9:
            row['pad_gap_mm']={side:{d:gap(local,patches[side][d],prop_p,grip_faces,grip_tree)
                                     for d in THUMB_INDEX} for side in sides}
        if clip=='hold_box':
            row['head_clearance_mm']=gap(local,head_faces,prop_p,prop_f,all_tree)
        if shelf_solids:
            row['shelf']=penetration(p,stage.faces,body,shelf_solids)
            row['rail_contacts']=rail_contacts(posed,prop_f,shelf_solids)
            if t < cfg['shelf']['attach_frame']/fps-1e-9:
                repeat_pts=transform(prop_p*.001,prop_pose(stage,clip,cfg,t,repeat=True))*1000
                row['repeat_prop']=penetration(p,stage.faces,body,[Solid(repeat_pts,f) for f in part_faces])
                row['repeat_rail_contacts']=rail_contacts(repeat_pts,prop_f,shelf_solids)
                if cfg['shelf']['return_frames'][0]-1e-9 <= t*fps:
                    row['repeat_deck_gap_mm']=deck_gap(deck_tree,repeat_pts)
            elif abs(t*fps-cfg['shelf']['attach_frame'])<1e-7:
                wait=B @ trs(cfg['shelf']['pickup_stop_gltf']) @ G
                wait_pts=transform(prop_p*.001,wait)*1000
                row['attach_surface_snap_mm']=float(np.linalg.norm(wait_pts-posed,axis=1).max())
                wait_local=transform(p*.001,wait.inverted())*1000
                row['pickup_hand_gap_mm']={d:gap(wait_local,patches['Right'][d],prop_p,grip_faces,grip_tree) for d in THUMB_INDEX}
                row['pickup_deck_gap_mm']=deck_gap(deck_tree,wait_pts)
            if abs(t-end/fps)<1e-7:
                rel=B @ trs(cfg['shelf']['release_pose_gltf']) @ G
                release_pts=transform(prop_p*.001,rel)*1000
                row['release_surface_snap_mm']=float(np.linalg.norm(release_pts-posed,axis=1).max())
        rows.append(row)
    for o in objects.values():
        bpy.data.objects.remove(o,do_unlink=True)
    summary={'samples':len(rows),'source_fps':fps}
    summary['pad_triangles']={s:{d:len(patches[s][d]) for d in THUMB_INDEX} for s in sides}
    summary['pad_gap_max_mm']={s:{d:max(r['pad_gap_mm'][s][d] for r in rows if 'pad_gap_mm' in r)
                                for d in THUMB_INDEX} for s in sides}
    summary['joint_replay_error_max_mm']=max(r['joint_replay_error_mm'] for r in rows)
    summary['up_from_vertical_deg_range']=[min(r['up_from_vertical_deg'] for r in rows),max(r['up_from_vertical_deg'] for r in rows)]
    summary['pass_joint_replay']=summary['joint_replay_error_max_mm']<=.025
    summary['prop_contacts']={k:{field:max(r[k][field] for r in rows if k in r) for field in rows[0]['prop']}
                             for k in ('prop','repeat_prop','shelf') if any(k in r for r in rows)}
    summary['pass_grip']=all(g<=3 for ds in summary['pad_gap_max_mm'].values() for g in ds.values())
    summary['pass_penetration']=all(v['depth_upper_mm']<=1 for v in summary['prop_contacts'].values())
    if clip=='hold_box':
        summary['head_clearance_min_mm']=min(r['head_clearance_mm'] for r in rows)
        summary['pass_chin']=summary['head_clearance_min_mm']>=10
    if clip=='take_item':
        for row in rows:
            for k in ('attach_surface_snap_mm','pickup_hand_gap_mm','pickup_deck_gap_mm','release_surface_snap_mm'):
                if k in row:
                    summary[k]=row[k]
        deck_errors=[abs(r['repeat_deck_gap_mm']) for r in rows if r.get('repeat_deck_gap_mm') is not None]
        summary['repeat_deck_gap_abs_max_mm']=max(deck_errors,default=None)
        rail=[r[k] for r in rows for k in ('rail_contacts','repeat_rail_contacts') if k in r]
        summary['jar_rail_contact_max']={k:max(r[k] for r in rail) for k in rail[0]}
        summary['pass_pickup']=max(summary['pickup_hand_gap_mm'].values())<=3 and summary['attach_surface_snap_mm']<=.05
        summary['pass_release']=summary['release_surface_snap_mm']<=.05
        summary['pass_deck']=summary['pickup_deck_gap_mm'] is not None and abs(summary['pickup_deck_gap_mm'])<=.5 and summary['repeat_deck_gap_abs_max_mm'] is not None and summary['repeat_deck_gap_abs_max_mm']<=.5
    summary['pass_gates']=all(v for k,v in summary.items() if k.startswith('pass_'))
    return summary, rows

def rail_contacts(jar,f,solids):
    rigid=tree(jar,f)
    hits=0
    depth=0.
    lo,hi=jar.min(0),jar.max(0)
    for solid in solids:
        if (lo>solid.hi).any() or (hi<solid.lo).any():
            continue
        hits+=len(rigid.overlap(solid.bvh))
        depth=max(depth,max(solid.enclosed(jar).values(),default=0.))
    return dict(triangle_pairs=hits,jar_vertex_depth_mm=depth)

def deck_gap(deck_tree, jar):
    min_z=jar[:,2].min()
    for x,y,z in jar[jar[:,2]<=min_z+.15]:
        hit,*_=deck_tree.ray_cast((x,y,z-900),(0,0,1))
        if hit is not None:
            return float(z-hit.z)
    return None

def chair_audit(stage, config):
    chair=ChairFit(stage)
    result={}
    samples={}
    for label,placement in [('origin',BASE_CHAIR),('fitted',config['world_gltf'])]:
        chair.placement(placement)
        result[label]={}
        samples[label]={}
        for clip,end in CHAIR.items():
            rows=[]
            for t in time_grid(30,end):
                p=stage.frame(clip,t)
                row=dict(frame=t*30, min_body_floor_mm=float(p[:,2].min()*1000),
                         **chair.contacts(p), feet=chair.floors(p))
                if seated(clip,t):
                    row['seat_gap_mm']=chair.gaps(p)
                rows.append(row)
            nearest=[min([g for g in r['seat_gap_mm'].values() if g is not None],default=math.inf)
                     for r in rows if 'seat_gap_mm' in r]
            seat_gaps={s:[r['seat_gap_mm'][s] for r in rows if 'seat_gap_mm' in r] for s in ('Left','Right')}
            bilateral={s:[min(a),max(a)] if a and all(v is not None for v in a) else None for s,a in seat_gaps.items()}
            floor={s:{part:max(abs(r['feet'][s][part]) for r in rows) for part in rows[0]['feet'][s]} for s in ('Left','Right')}
            summary=dict(samples=len(rows),inside_vertices_max=max(r['inside_vertices'] for r in rows),
                         depth_max_mm=max(r['depth_mm'] for r in rows),
                         chair_floor_min_mm=float(chair.posed[:,2].min()*1000),
                         triangle_pairs_max=max(r['triangle_pairs'] for r in rows),
                         nearest_seat_gap_range_mm=[min(nearest),max(nearest)],
                         seat_gap_range_by_side_mm=bilateral,
                         foot_abs_max_mm=floor,
                         body_floor_min_mm=min(r['min_body_floor_mm'] for r in rows))
            summary['pass_gates']=summary['inside_vertices_max']==0 and 0<=min(nearest)<=max(nearest)<=2 and max(f['sole_mm'] for f in floor.values())<=1
            result[label][clip]=summary
            samples[label][clip]=rows
    bpy.data.objects.remove(chair.chair,do_unlink=True)
    return result,samples

def run(config):
    stage=Stage()
    p={side:pads(stage,side) for side in ('Right','Left')}
    result=dict(inputs_sha256={},clips={})
    frames={}
    for path in (FEMALE/'body_female.glb', FEMALE/'motion_female.glb', ASTRA/'chair.glb', *(v[0] for v in PROPS.values())):
        result['inputs_sha256'][str(path.relative_to(PARTS))]=hashlib.sha256(path.read_bytes()).hexdigest()
    selected = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    selected=set(selected)-{'--render','--render-only'}
    if '--render-only' not in sys.argv:
        for clip in PROPS:
            if selected and clip not in selected:
                continue
            result['clips'][clip],frames[clip]=prop_audit(stage,clip,config['sockets'][clip if clip!='take_item' else 'jar'],p)
            print('VERIFY',clip,result['clips'][clip],flush=True)
        if not selected or 'chair' in selected:
            result['chair'],frames['chair']=chair_audit(stage,config['chair'])
            print('VERIFY fitted chair',result['chair']['fitted'],flush=True)
        result['pass_gates']=all(v['pass_gates'] for v in result['clips'].values()) and all(v['pass_gates'] for v in result.get('chair',{}).get('fitted',{}).values())
        name='verification' if not selected else 'verification-'+ '-'.join(sorted(selected))
        result['sockets_sha256']=hashlib.sha256((HERE/'sockets_female.json').read_bytes()).hexdigest()
        (HERE/(name+'.json')).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        (HERE/(name+'-frames.json')).write_text(json.dumps(frames,separators=(',',':'),allow_nan=False)+'\n')
    if '--render' in sys.argv or '--render-only' in sys.argv:
        from render import render
        render(stage,config)
    return result.get('pass_gates',True)

if __name__=='__main__':
    config=json.loads((HERE/'sockets_female.json').read_text())
    if not run(config):
        raise SystemExit(2)
