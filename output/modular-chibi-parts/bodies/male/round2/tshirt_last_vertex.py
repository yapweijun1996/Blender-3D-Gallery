"""Resolve a last signed-nearest tie without re-exporting the garment skin."""
from micro_refit import *
from body_audit import posed, set_frame
import struct


def main():
    scene,arm,body,actions=load_body_motion(FIXED)
    use_action(arm,None)
    bpy.context.view_layer.update()
    names=[bone.name for bone in arm.data.bones]
    g,_=from_export('tshirt',body,arm,names)
    audit=json.loads((OUT/'qa/modules/tshirt.json').read_text())
    bad={r['worst_vertex'] for clip in audit['clips'].values() for r in clip['frames'] if 'worst_vertex' in r}
    if not bad:
        return
    if len(bad)!=1:
        raise RuntimeError(('Unexpected new witnesses',sorted(bad)))
    v=next(iter(bad))
    start=g.position[v].copy()
    directions=np.array([x for x in product((-1,0,1),repeat=3) if any(x)]+[g.guide[v].tolist()])
    directions=normalized(directions)
    lengths=np.array([.0001,.0002,.0003,.00045,.00065,.00090,.00125,.00165,.00225,.003,.004])
    candidates=np.concatenate((start[None,:],start+(directions[:,None,:]*lengths[None,:,None]).reshape(-1,3)))
    candidates=candidates[np.linalg.norm(candidates-g.base[v],axis=1)<=.03]
    moves=candidates-start
    worst=np.full(len(moves),1.)
    samples=sample_bank(body,names)
    body_faces=arrays(body)[1].tolist()
    focus={'run','walk','sit_down','stand_up'}
    transforms=[]
    for s in samples:
        b=(s.transforms[g.ids[v]]*g.packed[v,:,None,None]).sum(axis=0)
        if s.clip in focus:
            use_action(arm,actions[s.clip])
            set_frame(scene,s.frame)
            body_pts=posed(body)
            real=posed(g.obj)[v]
            body_tree=tree(body_pts,body_faces)
        else:
            real=b[:,:3]@start+b[:,3]
            body_tree=tree(s.body,s.faces)
        start_signed=signed_at(body_tree,real[None,:])[0]
        if start_signed>.0063:
            continue
        trial=real+moves@b[:,:3].T
        worst=np.minimum(worst,np.array(signed_at(body_tree,trial)))
    chosen=np.flatnonzero(worst>=.00064)
    if not len(chosen):
        print('LAST VERTEX NO CLEARANCE',v,worst[0],worst.max(),flush=True)
        return
    best=chosen[np.argmin(np.linalg.norm(moves[chosen],axis=1))]
    path=OUT/'male-tshirt-v2.glb'
    asset=GLB(path)
    doc=deepcopy(asset.doc)
    contents=bytearray(asset.binary)
    moved=0
    target=start@GLTF_TO_BPY[:3,:3]
    change=moves[best]@GLTF_TO_BPY[:3,:3]
    for mesh in doc['meshes']:
        for prim in mesh['primitives']:
            accid=prim['attributes']['POSITION']
            raw=asset.accessor(accid)
            ids=np.flatnonzero(np.linalg.norm(raw-target,axis=1)<2.e-7)
            if not len(ids):
                continue
            acc=doc['accessors'][accid]
            view=doc['bufferViews'][acc['bufferView']]
            base=view.get('byteOffset',0)+acc.get('byteOffset',0)
            new=raw.copy()
            for ix in ids:
                new[ix]+=change
                struct.pack_into('<3f',contents,base+int(ix)*view.get('byteStride',12),*new[ix])
            acc.update(min=new.min(axis=0).tolist(),max=new.max(axis=0).tolist())
            moved+=len(ids)
    assert moved>0
    data=Writer(doc)
    data.doc['bufferViews']=deepcopy(asset.doc['bufferViews'])
    data.binary.extend(contents[:asset.doc['buffers'][0]['byteLength']])
    stage=OUT/'.runtime/tshirt-last.glb'
    data.write(stage)
    stage.replace(path)
    row=dict(stage='one signed-distance witness',vertex=int(v),glb_vertices=int(moved),
             min_before_m=float(worst[0]),min_after_m=float(worst[best]),bind_shift_m=moves[best].tolist())
    fitfile=OUT/'qa/fit-tshirt.json'
    saved=json.loads(fitfile.read_text())
    saved['iterations'].append(row)
    saved['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    saved['max_baked_offset_mm']=max(saved['max_baked_offset_mm'],float(
        1000*np.linalg.norm(start+moves[best]-g.base[v])))
    write_json(fitfile,saved)
    print('LAST VERTEX',row,flush=True)


if __name__=='__main__':
    main()
