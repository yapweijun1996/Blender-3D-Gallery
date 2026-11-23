"""Test a minimal walk thumb release against the skirt without moving the wrist."""
from motion_repair import *
from fit_module import influences, read_module
from fitting_geometry import tree
from mathutils.bvhtree import BVHTree


def main():
    _,arm,body,_=load_body_motion(MOTION)
    original=GLB(FIXED)
    engine=Repair(body,GLB(BODY_PATH))
    g=read_module(OUT/'male-dress-v2.glb',arm)
    p,f=arrays(g)
    names=['mixamorig:'+n for n in engine.abi.names]
    joint_ids,bone_weights=influences(weights(g,names))
    hom=np.column_stack((p,np.ones(len(p),dtype=np.float32)))
    local = np.einsum('vkij,vj->vki',engine.ib[joint_ids],hom)*bone_weights[:,:,None]
    regions=engine.c.check.regions
    hand_faces=[i for i,n in enumerate(regions) if n.startswith('LeftHand')]
    faces=engine.c.check.indices[hand_faces]
    verts, remapped=np.unique(faces,return_inverse=True)
    hand_faces=remapped.reshape(-1,3).tolist()
    frame_faces=f.tolist()
    action=next(a for a in original.doc['animations'] if a['name']=='walk')
    times=max((original.accessor(s['input']).ravel() for s in action['samplers']),key=len)
    states=engine.abi.sample(original,action,times)
    wrist,thumb,tip=[engine.joint('Left',x) for x in ('Hand','HandThumb1','HandThumb3')]
    before=[]
    report=[]
    edits=[]
    amplitude=[]
    def contact(state,geom=None):
        w=engine.abi.world(state)
        if geom is None:
            cloth=np.einsum('vkij,vkj->vi',(GLTF_TO_BPY@w)[joint_ids,:3,:],local)
            geom=tree(cloth,frame_faces)
        h=engine.posed(w,verts)
        ht=BVHTree.FromPolygons(h.tolist(),hand_faces,all_triangles=True)
        return len(geom.overlap(ht))
    def apply(state,degrees,axis_variant=0):
        w=engine.abi.world(state)
        ray=normalized(w[tip,:3,3]-w[thumb,:3,3])
        lateral=np.array([1.,0.,0.]) if axis_variant==0 else normalized(np.array([1.,.50,.16]))
        axis=np.cross(ray,lateral)
        engine.turn(state,w,thumb,axis,degrees)
    for i,(t,row) in enumerate(zip(times,zip(*states))):
        w=engine.abi.world(row)
        cloth=np.einsum('vkij,vkj->vi',(GLTF_TO_BPY@w)[joint_ids,:3,:],local)
        geom=tree(cloth,frame_faces)
        hit=contact(row,geom)
        before.append(hit)
        best=(hit,0.,0)
        if hit:
            for angle in (3,5,8,12,16,20,24,29,34,40):
                for variant in (0,1):
                    trial=[arr.copy() for arr in row]
                    apply(trial,angle,variant)
                    remaining=contact(trial,geom)
                    if remaining<best[0]:
                        best=(remaining,angle,variant)
                    if not remaining:
                        break
                if not best[0]:
                    break
        amplitude.append((best[1],best[2]))
    values=np.array([v[0] for v in amplitude])
    frames=times*24
    difference=abs(frames[:,None]-frames[None,:])
    curve=np.maximum(0,(values[None,:]-3.5*difference).max(axis=1))
    for i,(t,row) in enumerate(zip(times,zip(*states))):
        state=[arr.copy() for arr in row]
        if curve[i]>0:
            closest=np.argmax(values-3.5*difference[i])
            angle,variant=curve[i],amplitude[closest][1]
            apply(state,angle,variant)
            rem=contact(state)
            if rem:
                for a,v in [(max(angle,amplitude[i][0]),amplitude[i][1]),(angle+3,variant),(angle+5,1-variant)]:
                    trial=[arr.copy() for arr in row]
                    apply(trial,a,v)
                    test=contact(trial)
                    if test<rem:
                        state,rem,angle,variant=trial,test,a,v
            pts=engine.posed(engine.abi.world(state))
            if engine.c.target_pairs(pts):
                state=[arr.copy() for arr in row]
                angle=0.
                rem=before[i]
            report.append([float(t*24),before[i],rem,float(angle),int(variant)])
        edits.append(state[1][thumb])
    total_before=sum(before)
    total_after=sum(r[2] for r in report)+sum(b for b,c in zip(before,curve) if c==0)
    print('THUMB',total_before,total_after,'max degrees',max((r[3] for r in report),default=0.),flush=True)
    write_json(OUT/'qa/thumb_trial.json',dict(before=total_before,after=total_after,frames=report))
    if total_after>=total_before or not report:
        return
    source=deepcopy(original.doc)
    saved=deepcopy(source['bufferViews'])
    out=Writer(source)
    out.doc['bufferViews']=saved
    out.binary.extend(original.binary[:original.doc['buffers'][0]['byteLength']])
    walk=next(a for a in out.doc['animations'] if a['name']=='walk')
    channel=next(c for c in walk['channels'] if c['target']=={'node':original.ids['mixamorig:LeftHandThumb1'],'path':'rotation'})
    s=walk['samplers'][channel['sampler']]
    data=np.asarray(edits,dtype=np.float32)
    for i in range(1,len(data)):
        if np.dot(data[i-1],data[i])<0:
            data[i]*=-1
    s['input']=out.accessor(times,'SCALAR',bounds=True)
    s['output']=out.accessor(data,'VEC4')
    out.write(OUT/'.runtime/motion_thumb_trial.glb')


if __name__=='__main__':
    main()
