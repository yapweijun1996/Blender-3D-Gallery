from pathlib import Path
import bpy,bmesh,json,hashlib,sys,shutil
root=Path(__file__).resolve().parent;source=root/'sources/mall-ceiling-panel-module.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));asset=bpy.data.objects['ASSET_MallCeilingPanel']
meshes=[o for o in asset.children if o.type=='MESH'];connectors=[o for o in asset.children if o.type=='EMPTY']
assert tuple(asset.location)==(0,0,0) and bpy.context.scene.unit_settings.scale_length==1
assert len(meshes)==25 and len(connectors)==4
assert len([i for i in bpy.data.images if i.packed_file])==1
for obj in meshes:
    bm=bmesh.new();bm.from_mesh(obj.data);assert all(e.is_manifold for e in bm.edges),obj.name;assert bm.calc_volume()>0,obj.name;bm.free()
report={'closed_manifold_meshes':25,'source_reopened':'PASS','editable_mesh_parts':25,'connector_empties':4,'named_materials':sorted({m.name for o in meshes for m in o.data.materials}),'packed_original_textures':1,'units':'metres','blender_version':bpy.app.version_string,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
(root/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if '--' in sys.argv:
    out=Path(sys.argv[sys.argv.index('--')+1]).resolve();assert out!=root and not out.exists()
    (out/'sources').mkdir(parents=True);shutil.copy(root/'generate.py',out/'generate.py')
    panel=bpy.data.objects['PANEL_1']
    for v in panel.data.vertices:
        if v.co.z<0:v.co.z-=.002
    bpy.data.materials['Mineral fibre underside original seed 422'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.65
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'sources/mall-ceiling-panel-module.blend'),compress=True)
    print('Isolated saved-source mesh and material edits created')
