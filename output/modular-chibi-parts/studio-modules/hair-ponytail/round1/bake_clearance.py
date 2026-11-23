"""Bake body-clearance corrections in the head's rest coordinate system."""
from pathlib import Path
import sys,json
import bpy,numpy as np
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
H=Path(__file__).resolve().parent
P=H.parents[2]
MASTER=P/'master/GJH_Chibi_Master_rigged.blend'
CACHE=H/'.runtime/pose_samples.npz'
HEAD='mixamorig:Head'

def cache_poses():
    if CACHE.exists():return
    # Peak overlap and minimum clearance of each complete baseline clip sweep.
    records=json.loads((H/'checks/baseline/motion_extremes.json').read_text())
    banks={'shared':(P/'body-fix/motion_fixed.glb',None),'act':(P/'actions-fix/actions_fixed.glb',30),'act2':(P/'actions-hold2/hold_actions.glb',30)}
    positions=[];labels=[]
    for bank,(path,fps) in banks.items():
        bpy.ops.wm.open_mainfile(filepath=str(MASTER),use_scripts=False)
        sc=bpy.context.scene;arm=sc.objects['Armature'];body=sc.objects['Base_Body']
        if fps:sc.render.fps=fps;sc.render.fps_base=1
        body.data.calc_loop_triangles();faces=[t.vertices[:] for t in body.data.loop_triangles]
        prior=set(sc.objects);prior_actions=set(bpy.data.actions)
        bpy.ops.import_scene.gltf(filepath=str(path))
        actions=set(bpy.data.actions)-prior_actions
        for o in set(sc.objects)-prior:o.hide_viewport=True;o.hide_render=True
        data=arm.animation_data_create();data.use_nla=False
        for name,r in records.items():
            if r['bank']!=bank:continue
            data.action=None
            for b in arm.pose.bones:b.matrix_basis=Matrix.Identity(4)
            a=next(a for a in actions if a.name==name or a.name.startswith(name+'.'))
            data.action=a;data.action_slot=a.slots[0]
            for frame in sorted({r['peak_frame'],r['min_frame']}):
                sc.frame_set(int(frame),subframe=frame-int(frame))
                dg=bpy.context.evaluated_depsgraph_get()
                be=body.evaluated_get(dg);ae=arm.evaluated_get(dg)
                deform=ae.matrix_world@ae.pose.bones[HEAD].matrix@ae.data.bones[HEAD].matrix_local.inverted()@ae.matrix_world.inverted()
                transform=deform.inverted()@be.matrix_world
                coords=np.empty(len(be.data.vertices)*3,np.float32);be.data.vertices.foreach_get('co',coords)
                m=np.array(transform);positions.append((coords.reshape(-1,3)@m[:3,:3].T+m[:3,3]).astype('f'))
                labels.append(name+'@'+str(frame))
    np.savez_compressed(CACHE,positions=positions,faces=faces,labels=labels)

def apply_offsets(verts,faces,root,body_tree):
    cache=np.load(CACHE)
    tris=cache['faces'].tolist()
    tests=[('rest',body_tree)]+[(str(label),BVHTree.FromPolygons(pts.tolist(),tris,all_triangles=True)) for label,pts in zip(cache['labels'],cache['positions'])]
    shifts=np.zeros(len(verts));passes=[]
    for iteration in range(10):
        force=np.zeros(len(verts))
        hair=BVHTree.FromPolygons(verts,faces,all_triangles=True)
        peak=0
        for label,tree in tests:
            pairs=hair.overlap(tree);peak=max(peak,len(pairs))
            for i,v in enumerate(verts):
                q,n,_,_=tree.find_nearest(v);s=(v-q).dot(n)
                if s<.00087:force[i]=max(force[i],(.00112-s)/max(.45,n.dot((v-root).normalized())))
            for i in {i for i,_ in pairs}:
                ids=faces[i];a,b,c=(verts[j] for j in ids)
                probes=[a.lerp(b,t) for t in (.14,.33,.5,.67,.86)]+[a.lerp(c,t) for t in (.14,.33,.5,.67,.86)]+[b.lerp(c,t) for t in (.14,.33,.5,.67,.86)]+[(a+b+c)/3]
                step=.00055
                for v in probes:
                    q,n,_,_=tree.find_nearest(v);s=(v-q).dot(n)
                    step=max(step,(.00112-s)/max(.45,n.dot((v-root).normalized())))
                for j in ids:force[j]=max(force[j],step)
        passes.append(dict(peak_pairs=peak,moved=int((force>0).sum()),max_step_m=float(force.max())))
        if not np.any(force):break
        for i in np.flatnonzero(force):
            verts[i]+=(verts[i]-root).normalized()*float(force[i])
        shifts+=force
    (H/'offset_bake.json').write_text(json.dumps(dict(sampled_poses=[x for x,_ in tests],iterations=passes,max_baked_m=float(shifts.max()),moved_vertices=int((shifts>0).sum())),indent=2)+'\n')
    print('Motion offset bake',passes,flush=True)

