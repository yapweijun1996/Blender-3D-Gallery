"""Read-only Blender source/GLB geometry verification. Input paths are explicit."""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

source_arg, glb_arg = sys.argv[sys.argv.index("--") + 1:]
source, glb = map(lambda path: str(Path(path).resolve()), (source_arg, glb_arg))
bpy.ops.wm.open_mainfile(filepath=source)
A = bpy.data.objects["Hardwood body with scalloped wall and carved motif"]
B = bpy.data.objects["Fluted pastry with X-mirrored raised blossom and crescent"]
assert A.parent.name.startswith("HAND MOULD") and B.parent.name.startswith("STAMPED CAKE")
N, RINGS, AO, BO = 160, 22, 15, 7
mismatch = 0.0
asym = 0.0
depths = []
lift = []
for name, obj in (("mould", A), ("cake", B)):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(edge.is_manifold for edge in bm.edges), name
    assert bm.calc_volume(signed=True) > 0, name
    bm.free()
for r in range(RINGS):
    for j in range(N):
        k = (N//2 - j) % N
        a = A.data.vertices[(AO+r)*N+j].co
        b = B.data.vertices[(BO+r)*N+k].co
        raw = B.data.vertices[(BO+r)*N+j].co
        depth = .01815-a.z
        elevation = b.z-.03155
        mismatch = max(mismatch, abs(a.x+b.x), abs(a.y-b.y), abs(depth-elevation))
        asym = max(asym, abs(depth-(raw.z-.03155)))
        depths.append(depth)
        lift.append(elevation)
assert mismatch < .00000003, mismatch
assert asym > .002 and max(depths) > .004 and max(lift) > .004
rim_height = max(v.co.z for v in A.data.vertices[:15*N])
cavity_depth = rim_height-.01815
assert .025 < cavity_depth < .030
world_A, world_B = A.matrix_world.copy(), B.matrix_world.copy()
rim_point = A.data.vertices[10*N+N//4].co.copy()
def origin_for_matrix(matrix, x, y):
    return matrix @ Vector((x,y,.125))
ray_base = world_A @ Vector((0,0,.01815))
# Translate base or mirrored centre points into live asset world metres.
probe_pairs = []
for r in (3,6,10,15,19):
    for j in (0,10,25,50,62,69,95,108,139):
        a=A.data.vertices[(AO+r)*N+j].co.copy()
        x,y=a.x,a.y
        probe_pairs.append((origin_for_matrix(world_A,x,y),origin_for_matrix(world_B,-x,y),
                            (world_A @ a).z,(world_B @ Vector((-x,y,.03155 + .01815-a.z))).z))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
objects = list(bpy.context.scene.objects)
assert not any(o.name.startswith("Studio") or o.type in {"LIGHT","CAMERA"} for o in objects)
assert not bpy.data.actions
scene=bpy.context.scene
dg=bpy.context.evaluated_depsgraph_get()
def ray(pos, required):
    hit, point, _normal, _index, obj, _matrix=scene.ray_cast(dg,pos,Vector((0,0,-1)),distance=.15)
    assert hit and obj.name.startswith(required), (pos,obj)
    return point.z
h=ray(world_A @ Vector((rim_point.x,rim_point.y,.125)),"Hardwood body")
c=ray(origin_for_matrix(world_A,0,0),"Hardwood body")
assert h-c > .020 and c<=ray_base.z+.000001, (h,c)
expected_error=0
for aa,bb,a,b in probe_pairs:
    ah,bh=ray(aa,"Hardwood body"),ray(bb,"Fluted pastry")
    expected_error=max(expected_error,abs(ah-a),abs(bh-b))
assert expected_error < .000003, expected_error
verts=[o.matrix_world @ v.co for o in objects if o.type=="MESH" for v in o.data.vertices]
lower=[min(v[i] for v in verts) for i in range(3)]
upper=[max(v[i] for v in verts) for i in range(3)]
size=[upper[i]-lower[i] for i in range(3)]
assert abs(size[0]-.660)<.0001 and abs(size[1]-.430)<.0001 and .065<size[2]<.09,(lower,upper)
print("MOONCAKE_GEOMETRY",json.dumps({
    "blender_version":bpy.app.version_string,"negative_closed":True,"cake_closed":True,
    "mirrored_source_samples":N*RINGS,"mirror_error_m":mismatch,"mirrored_feature_asymmetry_m":asym,
    "carving_depth_m":max(depths),"cavity_lip_to_floor_m":cavity_depth,
    "exported_pair_rays":len(probe_pairs),"glb_ray_to_source_max_error_m":expected_error,
    "mesh_size_blender_xyz_m":size,"imported_static":True
},sort_keys=True))
