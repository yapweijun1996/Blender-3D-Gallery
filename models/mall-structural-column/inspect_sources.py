from pathlib import Path
import bpy,bmesh,json,hashlib,sys,shutil
root=Path(__file__).resolve().parent;source=root/'sources/mall-structural-column.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));asset=bpy.data.objects['ASSET_MallStructuralColumn']
meshes=[o for o in asset.children_recursive if o.type=='MESH']
assert tuple(asset.location)==(0,0,0) and bpy.context.scene.unit_settings.scale_length==1
assert len(meshes)==13
for obj in meshes:
    bm=bmesh.new();bm.from_mesh(obj.data);assert all(e.is_manifold for e in bm.edges),obj.name;assert bm.calc_volume()>0,obj.name;bm.free()
assert len(bpy.data.objects['CLADDING_IndependentPanels'].children)==8
assert tuple(bpy.data.objects['CONNECTOR_Floor'].location)==(0,0,0)
assert tuple(bpy.data.objects['CONNECTOR_Ceiling'].location)==(0,0,3)
report={'source_reopened':'PASS','editable_mesh_parts':13,'closed_manifold_meshes':13,'cladding_panels':8,'named_materials':sorted({m.name for o in meshes for m in o.data.materials}),'units':'metres','blender_version':bpy.app.version_string,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
(root/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if '--' in sys.argv:
    out=Path(sys.argv[sys.argv.index('--')+1]).resolve();assert out!=root and not out.exists()
    (out/'sources').mkdir(parents=True)
    shutil.copy(root/'generate.py',out/'generate.py')
    # Change real mesh width .50 -> .48 m. Other mesh vertices are untouched.
    for v in bpy.data.objects['CLADDING_Front_Lower'].data.vertices:v.co.x*=.96
    bpy.data.materials['Honed warm ivory cladding'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.72
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'sources/mall-structural-column.blend'),compress=True)
