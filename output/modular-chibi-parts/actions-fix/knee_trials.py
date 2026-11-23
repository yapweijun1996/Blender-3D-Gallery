"""Reproduce representative rotation-only trials at the shared seated endpoint."""
import json
import math
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from mathutils import Quaternion
from validate_actions import triangles,solids,penetration

def test():
    scene,arm,body,actions=load()
    checker=Checker(body)
    rest=posed(body);chair,=chibi.load(ASSETS/'chair.glb')
    cp,ct=posed(chair),triangles(chair)
    tree=BVHTree.FromPolygons(cp.tolist(),ct,all_triangles=True)
    parts=solids(cp,ct)
    chibi.bind(arm,actions['sit_idle']);at(scene,0)
    original=posed(body)
    sole={s:np.flatnonzero((sg*rest[:,0]>0)&(rest[:,2]<.0011)) for s,sg in zip(SIDES,(1,-1))}
    zones={s:Zone(checker,lambda r:r==s+'UpLeg',lambda r:r==s+'Leg') for s in SIDES}
    def record():
        p=posed(body);hip=bone(arm,'Hips').head
        mask=(rest[:,2]>.21)&(rest[:,2]<.41)&(abs(p[:,0])<.142)&(abs(p[:,0])>.008)&(abs(p[:,1]-hip.y)<.054)&(abs(p[:,1])<.098)
        return {'knee_pairs':{s:len(z.pairs(p)) for s,z in zones.items()},
                'max_sole_xy_delta_mm':max(float(np.linalg.norm((p-original)[ids,:2],axis=1).max()*1000) for ids in sole.values()),
                'max_foot_height_delta_mm':max(abs(float((p[ids,2].min()-original[ids,2].min())*1000)) for ids in checker.feet.values()),
                'chair_body_pairs':len(tree.overlap(BVHTree.FromPolygons(p.tolist(),checker.faces,all_triangles=True))),
                'body_vertices_inside_chair':penetration(p,parts)[0],
                'seat_gap_mm':{s:float((p[mask&(sg*p[:,0]>0),2].min()-chair['seat_height_m'])*1000) for s,sg in zip(SIDES,(1,-1))}}
    result={'source':record(),'tested_frame':0,'clip':'sit_idle'}
    for s in SIDES:turn(bone(arm,s+'Leg'),Vector((-1,0,0)),15)
    bpy.context.view_layer.update()
    result['15_degree_knee_extension']=record()
    at(scene,0)
    # Two independent length constraints keep the old knee, shin, ankle and foot
    # poses reachable. Solve the far branch of the pelvis rotation at zero yaw.
    hip=bone(arm,'Hips');H=np.array(hip.head,dtype=float)
    A=[np.array(bone(arm,s+'UpLeg').head,dtype=float) for s in SIDES]
    B=[np.array(bone(arm,s+'Leg').head,dtype=float) for s in SIDES]
    lengths=[np.linalg.norm(a-b) for a,b in zip(A,B)]
    def mat(v):
        a,b=v;c,sn=math.cos(a),math.sin(a);d,e=math.cos(b),math.sin(b)
        return np.array([[d,0,e],[sn*e,c,-sn*d],[-c*e,sn,c*d]])
    def err(v):
        return np.array([np.linalg.norm(H+mat(v)@(a-H)-b)-l for a,b,l in zip(A,B,lengths)])
    v=np.radians([-145.,0.])
    for _ in range(8):
        e=err(v)
        J=np.stack([(err(v+.00001*d)-e)/.00001 for d in np.eye(2)],axis=1)
        v-=np.linalg.solve(J,e)
    assert np.max(abs(err(v)))<1e-7
    R=Matrix(mat(v)).to_quaternion()
    def rotate(pb,rot):
        basis=pb.bone.matrix_local if pb.parent is None else pb.parent.matrix@pb.parent.bone.matrix_local.inverted()@pb.bone.matrix_local
        base=basis.to_quaternion()
        pb.rotation_quaternion=base.inverted()@rot@base@pb.rotation_quaternion
        bpy.context.view_layer.update()
    rotate(hip,R);rotate(bone(arm,'Spine'),R.inverted())
    for side,a,b,angle in zip(SIDES,A,B,(-40.,20.)):
        upper=bone(arm,side+'UpLeg');shin=bone(arm,side+'Leg')
        direction=Vector(b-a).normalized()
        align=direction.rotation_difference((Vector(b)-upper.head).normalized())
        turn_leg=align@Quaternion(direction,math.radians(angle))
        rotate(upper,turn_leg@R.inverted())
        rotate(shin,turn_leg.inverted())
    result['fixed_shin_alternate_pelvis_solution']={**record(),'pelvis_euler_xy_degrees':np.degrees(v).tolist()}
    (OUT/'knee_trials.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':test()
