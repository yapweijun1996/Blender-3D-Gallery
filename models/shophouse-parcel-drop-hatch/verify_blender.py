"""Read-only Blender geometry and exact native GLB animation acceptance."""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector

source,glb=(str(Path(p).resolve()) for p in sys.argv[sys.argv.index("--")+1:])
bpy.ops.wm.open_mainfile(filepath=source)

def descendant(o, ancestor):
    while o:
        if o==ancestor:return True
        o=o.parent
    return False

def run_samples(scene, target_report, imported=False):
    flap=scene.objects["PARCEL_DROP_FLAP"]
    sample=scene.objects["PARCEL_DROP_SAMPLE"]
    assert flap.parent is None and sample.parent is None and sample!=flap
    parts=[o for o in scene.objects if descendant(o,flap) and o.type=="MESH"]
    labels=[o for o in scene.objects if descendant(o,sample) and o.type in {"MESH","FONT"}]
    assert parts and labels
    opened=[]
    visual={}
    max_y=-math.inf
    box_min_y=math.inf
    anchor=None
    source_camera=Vector((1.68,-3.36,2.35))
    for f in (0,5,12,20,28,36,43,54):
        scene.frame_set(f)
        dg=bpy.context.evaluated_depsgraph_get()
        fe=flap.evaluated_get(dg)
        pe=sample.evaluated_get(dg)
        p=tuple(round(v,7) for v in pe.matrix_world.translation)
        angles=fe.matrix_world.to_euler('XYZ')
        assert abs(angles.y)<.00001 and abs(angles.z)<.00001
        theta=math.degrees(angles.x)
        if anchor is None:
            anchor=p
        else:
            assert anchor==p
        assert (fe.matrix_world.translation-Vector((0,-.175,.853))).length<.00001
        if f in (0,54):
            target=pe.matrix_world @ Vector((-.038,-.1186,.107))
            delta=target-source_camera
            yes,v,_,_,o,_=scene.ray_cast(dg,source_camera,delta.normalized(),distance=delta.length+.02)
            assert yes and o is not None,(f,target)
            if f==0:
                assert descendant(o,flap),(f,o.name)
            else:
                assert descendant(o,sample),(f,o.name)
            visual[f]=o.name
        for m in parts:
            ob=m.evaluated_get(dg)
            verts=ob.data.vertices
            y=max((ob.matrix_world@u.co).y for u in verts)
            max_y=max(max_y,y)
        for m in labels:
            if m.type != 'MESH':continue
            ob=m.evaluated_get(dg)
            y=min((ob.matrix_world@u.co).y for u in ob.data.vertices)
            box_min_y=min(box_min_y,y)
        opened.append([f,round(theta,5)])
    assert abs(opened[0][1])<.0001
    assert all(b[1]>=a[1]-.0001 for a,b in zip(opened,opened[1:]))
    assert all(abs(v-70)<.001 for f,v in opened if f>=36),opened
    assert box_min_y-max_y>.126,(box_min_y,max_y)
    target_report.update({'sourceFrameDegrees':opened,'flapToSampleYGapM':box_min_y-max_y,'sampleAnchorBlender':anchor,'sightHits':visual})

source_report={}
run_samples(bpy.context.scene,source_report)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.fps=30
scene.frame_start=0
scene.frame_end=54
bpy.ops.import_scene.gltf(filepath=glb)
assert all(o.type not in {"CAMERA","LIGHT"} and "Studio" not in o.name for o in scene.objects)
export_report={}
run_samples(scene,export_report,True)
for (_,a),(_,b) in zip(source_report['sourceFrameDegrees'],export_report['sourceFrameDegrees']):
    assert abs(a-b)<.002,(a,b)
print("PARCEL_NATIVE_PROOF",json.dumps({'source':source_report,'roundTripGLB':export_report,'blender':bpy.app.version_string},sort_keys=True))
