"""Read-only native Blender and standard GLB round-trip checks."""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

source,glb=(str(Path(p).resolve()) for p in sys.argv[sys.argv.index("--")+1:])
frames=(0,4,12,20,28,36,39,45,51,60)
cam=Vector((1.42,-3.3,1.98))
def nested(o,root):
    while o:
        if o==root:return True
        o=o.parent
    return False
def measure(stage):
    can=stage.objects['BCR_SAMPLE_CAN'];flag=stage.objects['BCR_ACCEPT_FLAG']
    assert can.parent is None and flag.parent is None
    assert can!=flag
    positions=[];angles=[]
    report={}
    for f in frames:
        stage.frame_set(f);dg=bpy.context.evaluated_depsgraph_get()
        m=can.evaluated_get(dg).matrix_world
        q=flag.evaluated_get(dg).matrix_world
        p=m.translation; pt=q.translation
        assert abs(p.x)<.00001 and abs(p.z-1.09)<.00001
        assert (pt-Vector((.263,-.343,1.154))).length<.00001
        assert m.to_quaternion().angle<.00001
        quat=q.to_quaternion()
        assert abs(quat.x)<.00002 and abs(quat.y)<.00002
        theta=abs(2*math.atan2(quat.z,quat.w)*180/math.pi)
        if theta>180.001:theta=360-theta
        positions.append([f,round(p.y,6)]); angles.append([f,round(theta,5)])
        if f==0:
            v=m@Vector((0,-.0738,-.002));delta=v-cam
            ok,_,_,_,o,_=stage.ray_cast(dg,cam,delta.normalized(),distance=delta.length+.009)
            assert ok and nested(o,can),o
            report['readyCanFirstRay']=o.name
        if f==60:
            v=q@Vector((0,.0095,0));d=v-cam
            ok,_,_,_,o,_=stage.ray_cast(dg,cam,d.normalized(),distance=d.length+.013)
            assert ok and nested(o,flag),o
            report['acceptedSignalFirstRay']=o.name
            edge=max((o.evaluated_get(dg).matrix_world@vertex.co).y for o in stage.objects
                    if o.type=='MESH' and nested(o,can) for vertex in o.evaluated_get(dg).data.vertices)
            origin=Vector((0,edge+.00025,1.09))
            ok,p,_,_,o,_=stage.ray_cast(dg,origin,Vector((0,1,0)),distance=.04)
            assert ok and not nested(o,can) and not nested(o,flag),o
            gap=p.y-edge
            assert .010<gap<.015,(gap,edge)
            report['parkedSampleRearClearanceM']=gap
    assert all(b[1]>=a[1] for a,b in zip(positions,positions[1:])) and all(b[1]>=a[1] for a,b in zip(angles,angles[1:]))
    assert positions[0][1]==-.26 and positions[-1][1]==.165
    assert all(p==.165 for f,p in positions if f>=39)
    assert all(abs(a)<.001 for f,a in angles if f<=39)
    assert all(abs(a-180)<.001 for f,a in angles if f>=51)
    report.update({'canYBlenderFrames':positions,'flagZDegreesFrames':angles})
    return report
bpy.ops.wm.open_mainfile(filepath=source)
a=measure(bpy.context.scene)
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.render.fps=30;s.frame_start=0;s.frame_end=60
bpy.ops.import_scene.gltf(filepath=glb)
assert all(o.type not in {'LIGHT','CAMERA'} for o in s.objects)
b=measure(s)
for (_,u),(_,v) in zip(a['canYBlenderFrames'],b['canYBlenderFrames']):
    assert abs(u-v)<.000003
for (_,u),(_,v) in zip(a['flagZDegreesFrames'],b['flagZDegreesFrames']):
    assert abs(u-v)<.002
print('M21_NATIVE_PROOF',json.dumps({'source':a,'roundTripGLB':b,'Blender':bpy.app.version_string},sort_keys=True))
