"""Independently evaluate authored and imported toss, including stationary dishes."""
import bpy
import json
from math import hypot
from pathlib import Path
import sys

params=sys.argv[sys.argv.index("--")+1:]
glb=Path(params[0]).resolve()
assert Path(bpy.data.filepath).name == "loh-hei-yee-sang-platter.blend"
static_names=("Tabletop_lacquer","Serving_platter_unchanged","Two_sauce_dishes_and_rests_unchanged",
              "Sesame_scatter_unchanged")
ingredient_prefixes=("Carrot","Cucumber","White_radish","Pickled_ginger","Pomelo","Pillow_cracker","Fish_slices")
stick_names=("Left_paired_chopsticks","Right_paired_chopsticks")
ingredient_names=tuple(f"{name}_parcel_{i}" for name in ingredient_prefixes for i in range(1,4))
all_names=static_names+ingredient_names+stick_names

def sample(frame):
    bpy.context.scene.frame_set(frame)
    return {name:bpy.data.objects[name].matrix_world.copy() for name in all_names}

def confirm_motion():
    first=sample(0);middle=sample(22);last=sample(50)
    for name in static_names:
        assert (last[name].translation-first[name].translation).length < 1e-5
        assert (middle[name].translation-first[name].translation).length < 1e-5
        assert first[name].to_quaternion().rotation_difference(last[name].to_quaternion()).angle < 1e-5
    for name in ingredient_names:
        assert (last[name].translation-first[name].translation).length > .015, name
        assert middle[name].translation.z-first[name].translation.z > .048,name
        loc=last[name].translation
        assert hypot(loc.x,loc.y)<.190 and .070<=loc.z<=.079,name
    for name in stick_names:
        assert (last[name].translation-first[name].translation).length < 1e-5,name
        assert middle[name].translation.z-first[name].translation.z > .138,name
        assert first[name].to_quaternion().rotation_difference(last[name].to_quaternion()).angle < 1e-5,name
    return sum(1 for name in ingredient_names if (last[name].translation-first[name].translation).length>.015)

def bounds_over_frames():
    objects=[bpy.data.objects[name] for name in all_names]
    points=[]
    for f in (0,8,14,18,22,26,30,38,46,50):
        bpy.context.scene.frame_set(f)
        points.extend(o.matrix_world @ v.co for o in objects for v in o.data.vertices)
    lo=[min(v[i] for v in points) for i in range(3)]
    hi=[max(v[i] for v in points) for i in range(3)]
    return lo,hi

assert confirm_motion()==21
lo,hi=bounds_over_frames()
assert abs(lo[2])<1e-5 and .260<hi[2]<.320
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps=24
bpy.ops.import_scene.gltf(filepath=str(glb))
assert confirm_motion()==21
mesh_count=sum(o.type=="MESH" for o in bpy.context.scene.objects)
assert mesh_count==27
assert not any(o.type in ("CAMERA","LIGHT") for o in bpy.context.scene.objects)
lo2,hi2=bounds_over_frames()
assert max(abs(a-b) for a,b in zip(lo+hi,lo2+hi2))<.003,(lo,hi,lo2,hi2)
report={"blender":bpy.app.version_string,"mesh_count":mesh_count,"parcel_count":21,"chopstick_pairs":2,
        "fps":24,"frame_last":50,"animation_bounds_blender_m":[lo2,hi2],
        "maximum_animated_height_m":round(hi2[2],6),"static_tableware_groups":4}
print(json.dumps(report))
if len(params)>1:
    Path(params[1]).write_text(json.dumps(report,indent=2)+"\n")
