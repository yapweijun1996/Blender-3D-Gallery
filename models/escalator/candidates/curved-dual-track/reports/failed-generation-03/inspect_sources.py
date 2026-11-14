from pathlib import Path
import bpy,bmesh,json,hashlib,importlib.util
p=Path(__file__).resolve().parent;spec=json.loads((p/'backlog.json').read_text());slug='escalator-circulation';source=p/'sources'/(slug+'.blend');before=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source));root=bpy.data.objects[spec['root']];meshes=[o for o in root.children_recursive if o.type=='MESH'];assert bpy.context.scene.unit_settings.scale_length==1 and bpy.context.scene.unit_settings.system=='METRIC';assert tuple(root.location)==(0,0,0)
for o in meshes:
 bm=bmesh.new();bm.from_mesh(o.data);assert all(e.is_manifold for e in bm.edges),o.name;assert bm.calc_volume()>0,o.name;bm.free()
tracks={}
for o in meshes:
 if o.name.startswith('TRACK_'):
  vs=[tuple(o.matrix_world@v.co)for v in o.data.vertices]
  tracks[o.name]={'vertices':vs,'centers':[[sum(v[j]for v in vs[i:i+8])/8 for j in range(3)]for i in range(0,len(vs),8)]}
(p/'reports/track-source-geometry.json').write_text(json.dumps(tracks))
# Exercise a real saved mesh edit and material edit without regenerating geometry.
target=sorted(meshes,key=lambda x:x.name)[0];name=target.name
for vertex in target.data.vertices:vertex.co.x*=.92
expected=[tuple(v.co)for v in target.data.vertices]
material=target.data.materials[0];material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.77
out=p/'reports/source-edit';out.mkdir(exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'-edited.blend')),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(out/(slug+'-edited.blend')))
assert all((v.co-__import__('mathutils').Vector(e)).length<1e-7 for v,e in zip(bpy.data.objects[name].data.vertices,expected))
assert bpy.data.objects[name].data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value>.769
s=importlib.util.spec_from_file_location('asset_generator',p/'generate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.export(out/'edited.glb')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
report={'source_reopened':'PASS','editable_mesh_parts':len(meshes),'closed_manifold_meshes':len(meshes),'units':'metres','blender_version':bpy.app.version_string,'source_sha256':before,'edited_mesh':name,'edit':'local mesh X vertices scaled by 0.92; material roughness to 0.77','original_source_unchanged':True,'edited_glb_sha256':hashlib.sha256((out/'edited.glb').read_bytes()).hexdigest()};(p/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
