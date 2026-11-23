"""Reopen the artist source and verify its closed components and three exported scenes."""
import hashlib
import json
from pathlib import Path

import bmesh
import bpy

HERE = Path(__file__).resolve().parent
SLUG = "mall-product-security-tether"
SOURCE = HERE / "sources" / (SLUG + ".blend")


def geometry(objects, check_source=False):
    points=[]
    volume=0
    meshes=triangles=0
    for obj in objects:
        if obj.type!="MESH":
            continue
        data=obj.data
        meshes+=1
        data.calc_loop_triangles()
        triangles+=len(data.loop_triangles)
        geom=bmesh.new()
        geom.from_mesh(data)
        if check_source:
            assert all(edge.is_manifold and edge.is_contiguous for edge in geom.edges),obj.name
            assert all(v.link_faces for v in geom.verts),obj.name
            assert all(f.calc_area()>1e-13 for f in geom.faces),obj.name
        # The reimporter splits vertices across materials and crease normals.
        # Signed triangle volumes are additive even at those attribute seams.
        assert geom.calc_volume(signed=True)>0,obj.name
        for tri in data.loop_triangles:
            a,b,c=(data.vertices[i].co for i in tri.vertices)
            volume+=a.dot(b.cross(c))/6
        geom.free()
        points.extend(obj.matrix_world @ vert.co for vert in data.vertices)
    lo=[min(p[i] for p in points) for i in range(3)]
    hi=[max(p[i] for p in points) for i in range(3)]
    assert abs(lo[2])<1e-7 and .028<hi[2]<.032,(lo,hi)
    assert abs(lo[0]+.1665)<1e-6 and abs(hi[0]-.0265)<1e-6,(lo,hi)
    assert -.043<lo[1]<-.038 and abs(hi[1]-.0265)<1e-6,(lo,hi)
    return {"meshes":meshes,"triangles":triangles,"sumOfSignedMeshVolumesM3":volume,"blenderBounds":[lo,hi]}


bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
bpy.context.view_layer.update()
assert bpy.context.scene.unit_settings.system=="METRIC"
assert not bpy.data.libraries
assert not any(im.source=="FILE" and im.filepath for im in bpy.data.images)
for item in [*bpy.data.scenes,*bpy.data.objects,*bpy.data.meshes,*bpy.data.materials]:
    assert not list(item.keys()),(item.name,list(item.keys()))
report={"blender":bpy.app.version_string,"sourceSha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "externalImages":0,"linkedLibraries":0,"levels":{}}
for lod in range(3):
    label="LOD"+str(lod)
    col=bpy.data.collections[label]
    root=bpy.data.objects["ASSET_ProductSecurityTether_"+label]
    assert list(root.location)==[0,0,0] and list(root.scale)==[1,1,1]
    report["levels"][label]={"source":geometry(col.objects,True),"allSourceEdgesManifoldContiguous":True}
for lod in range(3):
    label="LOD"+str(lod)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    exported=HERE/"exports"/(SLUG+("-lod"+str(lod) if lod else "")+".glb")
    bpy.ops.import_scene.gltf(filepath=str(exported))
    bpy.context.view_layer.update()
    stats=geometry(bpy.context.scene.objects)
    source=report["levels"][label]["source"]
    assert abs(stats["sumOfSignedMeshVolumesM3"]-source["sumOfSignedMeshVolumesM3"])<1e-10,(source,stats)
    assert stats["triangles"]==source["triangles"],(source,stats)
    report["levels"][label]["glbReimport"]=stats
report["result"]="pass"
(HERE/"reports/source.json").write_text(json.dumps(report,indent=2)+"\n")
