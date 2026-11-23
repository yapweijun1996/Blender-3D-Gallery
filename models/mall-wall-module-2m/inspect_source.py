"""Reopen the editable asset and compare each source level to a clean GLB reimport."""
import hashlib
import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = "mall-wall-module-2m"
SOURCE = HERE / "sources" / f"{SLUG}.blend"
LIMIT = 1e-6


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(objects, *, gltf=False):
    points, uv_meshes, volumes = [], [], {}
    for obj in objects:
        if obj.type != "MESH":
            continue
        data = obj.data
        if len(data.uv_layers):
            uv_meshes.append(obj.name)
        mesh = bmesh.new()
        mesh.from_mesh(data)
        # glTF splits seam vertices for normals, UVs, colours and materials.
        # Weld only this checking copy, at less than a tenth of a micrometre.
        if gltf:
            bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=5e-8)
        assert all(edge.is_manifold for edge in mesh.edges), obj.name
        assert all(len(v.link_faces) > 0 for v in mesh.verts), obj.name
        volume = mesh.calc_volume(signed=True)
        assert volume > 0, (obj.name, volume)
        volumes[obj.name] = volume
        mesh.free()
        points.extend(obj.matrix_world @ vertex.co for vertex in data.vertices)
    low=[min(p[i] for p in points) for i in range(3)]
    high=[max(p[i] for p in points) for i in range(3)]
    for actual, expected in zip(low+high,[-1,-.075,0,1,.075,2.8]):
        assert abs(actual-expected)<LIMIT,(low,high)
    return {"meshCount":len(volumes),"boundsXYZm":[low,high],"uvMeshCount":len(uv_meshes),
            "closedPositiveVolumeMeshes":len(volumes),"totalVolumeM3":sum(volumes.values())}


levels = ["LOD0","LOD1","LOD2"]
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
bpy.context.view_layer.update()
assert bpy.context.scene.unit_settings.system == "METRIC"
image=bpy.data.images["honed-limestone.png"]
assert list(image.size)==[512,512] and image.packed_file
assert image.filepath=="//honed-limestone.png"
assert all(p.filepath=="//honed-limestone.png" for p in image.packed_files)
allowed={"backlog_id","pitch_m","front"}
for item in [*bpy.data.scenes,*bpy.data.objects,*bpy.data.images,*bpy.data.materials]:
    assert set(item.keys())==(allowed if item.name.startswith("ASSET_MallWall2m") else set()), item.name
packed_sha=hashlib.sha256(bytes(image.packed_file.data)).hexdigest()
assert packed_sha == digest(HERE/"sources"/"honed-limestone.png")
report={"blenderVersion":bpy.app.version_string,"blendSha256":digest(SOURCE),"packedTextureSha256":packed_sha,
        "axis":"Blender XYZ; +Z up; front is -Y","levels":{}}
for level in levels:
    objects=list(bpy.data.collections[level].objects)
    info=inspect(objects)
    for side,x in [("Left",-1),("Right",1)]:
        point=bpy.data.objects[f"CONNECTOR_{side}_{level}"].matrix_world.translation
        assert (point-Vector((x,0,0))).length<LIMIT
    report["levels"][level]={"source":info}
assert report["levels"]["LOD0"]["source"]["uvMeshCount"]==8

for level in levels:
    suffix="" if level=="LOD0" else "-"+level.lower()
    file=HERE/"exports"/f"{SLUG}{suffix}.glb"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(file),merge_vertices=True)
    bpy.context.view_layer.update()
    info=inspect(bpy.context.scene.objects,gltf=True)
    entry=report["levels"][level]
    source=entry["source"]
    assert abs(source["totalVolumeM3"]-info["totalVolumeM3"])<1e-6
    entry.update(glbSha256=digest(file),reimport=info)
report["result"]="pass"
target=HERE/"reports"/"source-reimport.json"
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(report,indent=2)+"\n")
print(f"Verified reopened Blender source and three exported levels in {target}")
