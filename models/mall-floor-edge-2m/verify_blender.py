"""Inspect the saved editable profiles and clean reimports of all six GLBs."""
import hashlib
import json
from pathlib import Path

import bmesh
import bpy

BASE=Path(__file__).resolve().parent
SLUG="mall-floor-edge-2m"
SOURCE=BASE/"sources"/(SLUG+".blend")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def measure(objects,form,imported):
    merged=bmesh.new()
    coords=[];intentional_edges=0;meshes=0
    for obj in objects:
        if obj.type!="MESH":
            continue
        meshes+=1
        data=obj.data.copy();data.transform(obj.matrix_world)
        coords.extend(v.co.copy() for v in data.vertices)
        local=bmesh.new();local.from_mesh(data)
        if imported:bmesh.ops.remove_doubles(local,verts=list(local.verts),dist=5e-8)
        assert all(v.link_faces for v in local.verts),obj.name
        for edge in local.edges:
            if edge.is_manifold:
                continue
            assert form=="Mitre" and edge.is_boundary, obj.name
            assert all(abs(v.co.x+v.co.y)<1e-6 for v in edge.verts),obj.name
            intentional_edges+=1
        local.free()
        merged.from_mesh(data)
        bpy.data.meshes.remove(data)
    bmesh.ops.remove_doubles(merged,verts=list(merged.verts),dist=5e-8)
    assert all(e.is_manifold for e in merged.edges)
    assert all(f.calc_area()>1e-12 for f in merged.faces)
    volume=merged.calc_volume(signed=True);assert volume>0
    merged.free()
    low=[min(v[i] for v in coords) for i in range(3)]
    high=[max(v[i] for v in coords) for i in range(3)]
    exp=([-1,-.03,-.1,1,.03,0] if form=='Straight' else [-1,-1.06,-.1,1.06,1,0])
    assert all(abs(a-b)<1e-6 for a,b in zip(low+high,exp)),(low,high)
    return {"blenderXyzBoundsM":[low,high],"meshes":meshes,"assembledVolumeM3":volume,
            "closedAfterMiterSeamWeld":True,"individualMiterBoundaryEdges":intentional_edges}


bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
bpy.context.view_layer.update()
assert bpy.context.scene.unit_settings.system=="METRIC" and not bpy.data.libraries
assert not bpy.utils.blend_paths(absolute=False,packed=True)
for item in [*bpy.data.scenes,*bpy.data.objects,*bpy.data.meshes,*bpy.data.materials]:
    keys={"kit","form","width_m","depth_m"} if item.name.startswith("ASSET_MallFloorEdge2m") else set()
    assert set(item.keys())==keys,(item.name,list(item.keys()))
report={"blenderVersion":bpy.app.version_string,"sourceSha256":sha(SOURCE),"forms":{}}
for form in ("Straight","Mitre"):
    for level in ("LOD0","LOD1","LOD2"):
        col=bpy.data.collections[form+" "+level]
        report["forms"][form+level]={"source":measure(col.objects,form,False)}
for form in ("Straight","Mitre"):
    for level in ("LOD0","LOD1","LOD2"):
        name=SLUG+("-mitre" if form=="Mitre" else "")+("" if level=="LOD0" else "-"+level.lower())
        filepath=BASE/"exports"/(name+".glb")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(filepath),merge_vertices=True)
        bpy.context.view_layer.update()
        result=measure(bpy.context.scene.objects,form,True)
        row=report["forms"][form+level]
        assert abs(row["source"]["assembledVolumeM3"]-result["assembledVolumeM3"])<1e-7
        row.update(glbSha256=sha(filepath),reimport=result)
report["result"]="pass"
(BASE/"reports").mkdir(exist_ok=True)
(BASE/"reports"/"source-reimport.json").write_text(json.dumps(report,indent=2)+"\n")
print("Verified editable trim and six GLB reimports")
