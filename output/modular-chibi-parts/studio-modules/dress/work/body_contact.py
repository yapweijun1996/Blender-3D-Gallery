import bpy, json, runpy, numpy as np
from pathlib import Path
from mathutils.bvhtree import BVHTree
home=Path.cwd()
m=runpy.run_path(str(home/"fit_dress.py"))
scene, arm, body=m["open_master"]()
m["setup_motion"](scene,arm,body,None)
names=tuple(b.name for b in arm.data.bones)
zones=np.array(m["zone_names"](body,names))
f=np.array(m["mesh_triangles"](body.data))
v=m["mesh_points"](body.data)[f].mean(axis=1)
rows={}
trunk=np.array([any(s in n for s in ("Hips","Spine","UpLeg")) for n in zones]) & (v[:,2] < .53)
for clip,frame in [("rest",1),("walk",22),("run",9),("wave",19),("jump",38.5),("idle",66),("nod",0),("dance",50)]:
    m["set_pose"](scene,arm,clip,frame)
    posed,_=m["posed_mesh"](body,bpy.context.evaluated_depsgraph_get())
    b=BVHTree.FromPolygons(posed,f[trunk].tolist(),all_triangles=True)
    result={}
    for side in ("Left","Right"):
        arm_ids=np.array([n.startswith(side) and any(s in n for s in ("Arm","Hand")) for n in zones])
        arm_ids &= np.abs(v[:,0]) > .135
        a=BVHTree.FromPolygons(posed,f[arm_ids].tolist(),all_triangles=True)
        pairs=a.overlap(b)
        counts={}
        for i,j in pairs:
            k=zones[arm_ids][i]+" / "+zones[trunk][j]
            counts[k]=counts.get(k,0)+1
        result[side]={"pairs":len(pairs),"zones":counts}
    rows[clip]={"frame":frame,**result}
print(json.dumps(rows,indent=2))
(home/"work/body_contact.json").write_text(json.dumps(rows,indent=2)+"\n")
