import bpy,bmesh,json,hashlib,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H/'reports'/'source-proof';R.mkdir(exist_ok=True);src=H/'sources'/'demo-food-tin.blend';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();original=sha(src)
bpy.ops.wm.open_mainfile(filepath=str(src));root=bpy.data.objects['ASSET_DemoFoodTin'];body=bpy.data.objects['BODY_HollowShell'];bm=bmesh.new();bm.from_mesh(body.data);assert all(e.is_manifold for e in bm.edges);assert bm.calc_volume()>0;volume=bm.calc_volume();bm.free()
# Hollow cup cross section: no face bridges the opening, inner wall spans full depth.
assert any(abs(v.co.x**2+v.co.y**2-.0363**2)<1e-8 and v.co.z>.1 for v in body.data.vertices)
assert all(not(abs(p.center.z-.1079)<1e-5 and p.area>.0001) for p in body.data.polygons)
assert bpy.data.images['concept-label.png'].packed_file
uv=bpy.data.objects['LABEL_Wrap'].data.uv_layers.active;assert uv and len(uv.data)>0
before=list(body.data.vertices[0].co);body.data.vertices[0].co.x+=.00002;expected=list(body.data.vertices[0].co);mat=bpy.data.materials['Tin satin steel'];mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.43
bpy.ops.wm.save_as_mainfile(filepath=str(R/'edited-copy.blend'))
bpy.ops.wm.open_mainfile(filepath=str(R/'edited-copy.blend'));assert list(bpy.data.objects['BODY_HollowShell'].data.vertices[0].co)==expected;assert abs(bpy.data.materials['Tin satin steel'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value-.43)<1e-6
for n in ['MOVABLE_Lid','MOVABLE_PullRing']:
 for t in bpy.data.objects[n].animation_data.nla_tracks:t.mute=False
bpy.context.scene.frame_set(0);bpy.ops.object.select_all(action='DESELECT');root=bpy.data.objects['ASSET_DemoFoodTin'];root.select_set(True)
for o in root.children_recursive:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(R/'edited-copy.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_animations=True,export_nla_strips=True,export_frame_range=True,export_force_sampling=True,export_extras=True,export_cameras=False,export_lights=False)
assert sha(src)==original
r={'status':'PASS','source_sha256':original,'body_volume_m3':volume,'body_manifold':True,'hollow_cup':True,'packed_label':True,'mesh_vertex_before':before,'mesh_vertex_after_reopen':expected,'roughness_after_reopen':.43,'edited_source_sha256':sha(R/'edited-copy.blend'),'edited_glb_sha256':sha(R/'edited-copy.glb'),'generator_executed':False,'canonical_unchanged':True};(R/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
