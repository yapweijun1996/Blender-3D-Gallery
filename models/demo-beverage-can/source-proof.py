"""Independent editable-source proof; opens the host-produced blend and edits it."""
import bpy, bmesh, hashlib, json
from pathlib import Path
H=Path(__file__).resolve().parent;R=H/'reports'/'source-proof';R.mkdir(exist_ok=True);src=H/'sources'/'demo-beverage-can.blend';original=hashlib.sha256(src.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(src));root=bpy.data.objects['ASSET_DemoBeverageCan'];body=bpy.data.objects['BODY_HollowShell'];top=bpy.data.objects['MOVABLE_Top']
bm=bmesh.new();bm.from_mesh(body.data);assert all(e.is_manifold for e in bm.edges);assert bm.calc_volume()>0;volume=bm.calc_volume();bm.free()
assert bpy.data.objects.get('TOP_InnerApertureWall');assert bpy.data.objects['MOVABLE_Tab'].parent==top;assert bpy.data.objects['MOVABLE_ScoreFlap'].parent==top
label=bpy.data.objects['LABEL_OriginalCitrusBand'];assert label.data.uv_layers.active and len(label.data.uv_layers.active.data)>0;assert bpy.data.images['beverage-label.png'].packed_file
before=tuple(body.data.vertices[0].co);body.data.vertices[0].co.x+=.00002;expected=tuple(body.data.vertices[0].co);mat=bpy.data.materials['Can satin teal'];mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.43
bpy.ops.wm.save_as_mainfile(filepath=str(R/'edited-copy.blend'));bpy.ops.wm.open_mainfile(filepath=str(R/'edited-copy.blend'));assert tuple(bpy.data.objects['BODY_HollowShell'].data.vertices[0].co)==expected;assert abs(bpy.data.materials['Can satin teal'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value-.43)<1e-6
assert hashlib.sha256(src.read_bytes()).hexdigest()==original
result={'status':'PASS','source_sha256':original,'body_volume_m3':volume,'body_manifold':True,'hollow_aperture_geometry':True,'packed_label':True,'mesh_vertex_before':before,'mesh_vertex_after_reopen':expected,'roughness_after_reopen':.43,'edited_source_sha256':hashlib.sha256((R/'edited-copy.blend').read_bytes()).hexdigest(),'generator_executed':False,'canonical_unchanged':True};(R/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
