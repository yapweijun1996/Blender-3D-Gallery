"""Reimport the animation and validate sample-card travel, readout and fixture."""
import bpy
import json
from pathlib import Path
import sys

args=sys.argv[sys.argv.index("--")+1:]
glb=Path(args[0]).resolve()
assert Path(bpy.data.filepath).name=="malaysia-rail-reload-counter.blend"
authored=bpy.data.objects
labels={"Malay customer service title":"KHIDMAT PELANGGAN",
        "English customer service subheading":"CUSTOMER SERVICE",
        "Malay reload title":"TAMBAH NILAI","English reload subheading":"RELOAD"}
for name,body in labels.items():
    assert authored[name].data.body==body,name
for n in ("Low projecting traveler shelf","Wide transaction transfer tray floor","Wide recessed receipt mouth",
          "Blank staff monitor monitor case","Raised fictional reader indicator island","Shelf card rest shallow bottom"):
    assert n in authored,n
assert len([o for o in authored if o.name.startswith("Upper lapped translucent service glazing")])==2
assert {o.name for o in bpy.context.scene.objects if o.animation_data}=={"RAIL_DEMO_CARD","RAIL_READER_INDICATOR"}

checks=(0,6,21,33,36,48)
rest_x=.198
stop_x=.522
hide_z=.983
end_z=.9965
def sample():
    scene=bpy.context.scene
    frames={}
    for frame in checks:
        scene.frame_set(frame)
        card=bpy.data.objects["RAIL_DEMO_CARD"]
        led=bpy.data.objects["RAIL_READER_INDICATOR"]
        frames[frame]=(list(card.matrix_world.translation),list(led.matrix_world.translation))
    assert abs(frames[0][0][0]-rest_x)<.0002
    assert abs(frames[0][0][2]-.921)<.0002
    assert abs(frames[21][0][2]-1.083)<.0002
    assert abs(frames[48][0][0]-stop_x)<.0002
    assert abs(frames[48][0][2]-.993)<.0002
    assert abs(frames[33][1][2]-hide_z)<.0002
    assert abs(frames[36][1][2]-end_z)<.0002
    assert frames[48][1]==frames[36][1]
    return frames
authored_motion=sample()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps=24
bpy.ops.import_scene.gltf(filepath=str(glb))
measured=sample()
assert max(abs(va-vb) for frame in checks for ar,br in zip(authored_motion[frame],measured[frame]) for va,vb in zip(ar,br))<.0003
bpy.context.scene.frame_set(0)
meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
p=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
lo=[min(v[i] for v in p) for i in range(3)]
hi=[max(v[i] for v in p) for i in range(3)]
dims=[round(b-a,6) for a,b in zip(lo,hi)]
assert abs(lo[2])<.001
assert all(a<=x<=b for a,x,b in zip((2.24,1.09,2.10),dims,(2.32,1.25,2.16))),dims
assert not any(o.type in ("CAMERA","LIGHT") for o in bpy.context.scene.objects)
report={"blender":bpy.app.version_string,"mesh_count":len(meshes),"bounds_m":[lo,hi],"dimensions_m":dims,
        "source_frame_range":[0,48],"sample_pose_blender_m":measured}
print(json.dumps(report))
if len(args)>1:
    Path(args[1]).write_text(json.dumps(report,indent=2)+"\n")
