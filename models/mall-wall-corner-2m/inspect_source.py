"""Reopen the editable asset and compare each source level to a clean GLB reimport."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = "mall-wall-corner-2m"
STRAIGHT = "mall-wall-module-2m"
parser=argparse.ArgumentParser()
parser.add_argument("--straight-dir",type=Path,default=HERE.parent/STRAIGHT)
args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
SOURCE = HERE / "sources" / f"{SLUG}.blend"
LIMIT = 1e-6


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(objects, *, gltf=False):
    points, groups = [], {}
    uv_count = mesh_count = intentional_border_edges = 0
    for obj in objects:
        if obj.type!="MESH":
            continue
        arm, name = obj.name.split(" ",1)
        assert arm in ("West","Return"), obj.name
        mesh_count += 1
        uv_count += bool(obj.data.uv_layers)
        data=obj.data.copy()
        data.transform(obj.matrix_world)
        points.extend(vertex.co.copy() for vertex in data.vertices)
        # Per-arm trim is intentionally open only on the shared diagonal.
        # No internal cap is drawn and collision boxes stay inside each wing.
        mesh=bmesh.new()
        mesh.from_mesh(data)
        if gltf:
            bmesh.ops.remove_doubles(mesh,verts=list(mesh.verts),dist=5e-8)
        assert all(v.link_faces for v in mesh.verts), obj.name
        for edge in mesh.edges:
            if not edge.is_manifold:
                assert edge.is_boundary and all(abs(v.co.x-v.co.y)<1e-7 for v in edge.verts),obj.name
                intentional_border_edges+=1
        mesh.free()
        if name not in groups:
            groups[name]=bmesh.new()
        groups[name].from_mesh(data)
        bpy.data.meshes.remove(data)
    volumes=[]
    for name,combined in groups.items():
        bmesh.ops.remove_doubles(combined,verts=list(combined.verts),dist=5e-8)
        assert all(edge.is_manifold for edge in combined.edges), name
        volume=combined.calc_volume(signed=True)
        assert volume>0, (name,volume)
        volumes.append(volume)
        combined.free()
    low=[min(p[i] for p in points) for i in range(3)]
    high=[max(p[i] for p in points) for i in range(3)]
    for actual, expected in zip(low+high,[-2,-2,0,.075,.075,2.8]):
        assert abs(actual-expected)<LIMIT,(low,high)
    assert intentional_border_edges > 0
    return {"meshCount":mesh_count,"boundsXYZm":[low,high],"uvMeshCount":uv_count,
            "pairedFeatureGroups":len(volumes),"intentionalMiterBoundaryEdges":intentional_border_edges,
            "pairedFeaturesClosedAndPositiveVolume":True,"totalVolumeM3":sum(volumes)}


levels = ["LOD0","LOD1","LOD2"]
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
bpy.context.view_layer.update()
assert bpy.context.scene.unit_settings.system == "METRIC"
image=bpy.data.images["honed-limestone.png"]
assert list(image.size)==[512,512] and image.packed_file
assert image.filepath=="//../../mall-wall-module-2m/sources/honed-limestone.png"
assert all(p.filepath=="//../../mall-wall-module-2m/sources/honed-limestone.png" for p in image.packed_files)
allowed={"backlog_id","arm_m","front"}
for item in [*bpy.data.scenes,*bpy.data.objects,*bpy.data.images,*bpy.data.materials]:
    assert set(item.keys())==(allowed if item.name.startswith("ASSET_MallWallCorner2m") else set()), item.name
packed_sha=hashlib.sha256(bytes(image.packed_file.data)).hexdigest()
assert packed_sha == digest(args.straight_dir/"sources"/"honed-limestone.png")
report={"blenderVersion":bpy.app.version_string,"blendSha256":digest(SOURCE),"packedTextureSha256":packed_sha,
        "axis":"Blender XYZ; +Z up; front is -Y","levels":{}}
for level in levels:
    objects=list(bpy.data.collections[level].objects)
    info=inspect(objects)
    for side,coords in [("Left",(-2,0,0)),("Return",(0,-2,0))]:
        point=bpy.data.objects[f"CONNECTOR_{side}_{level}"].matrix_world.translation
        assert (point-Vector(coords)).length<LIMIT
    report["levels"][level]={"source":info}
assert report["levels"]["LOD0"]["source"]["uvMeshCount"]==16

for level in levels:
    suffix="" if level=="LOD0" else "-"+level.lower()
    file=HERE/"exports"/f"{SLUG}{suffix}.glb"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(file),merge_vertices=True)
    bpy.context.view_layer.update()
    info=inspect(bpy.context.scene.objects,gltf=True)
    entry=report["levels"][level]
    source=entry["source"]
    assert abs(source["totalVolumeM3"]-info["totalVolumeM3"])<2e-6
    entry.update(glbSha256=digest(file),reimport=info)
report["result"]="pass"
target=HERE/"reports"/"source-reimport.json"
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(report,indent=2)+"\n")
print(f"Verified reopened Blender source and three exported levels in {target}")
