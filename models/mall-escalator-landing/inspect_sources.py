from pathlib import Path
import bpy,bmesh,json,hashlib,sys,shutil
root=Path(__file__).resolve().parent;source=root/'sources/mall-escalator-landing.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));asset=bpy.data.objects['ASSET_MallEscalatorLanding'];meshes=[o for o in asset.children_recursive if o.type=='MESH']
assert tuple(asset.location)==(0,0,0) and bpy.context.scene.unit_settings.scale_length==1
assert len(meshes)==8
for o in meshes:
    bm=bmesh.new();bm.from_mesh(o.data);assert all(e.is_manifold for e in bm.edges),o.name;assert bm.calc_volume()>0,o.name;bm.free()
assert all(o.library is None for o in asset.children_recursive)
report={'source_reopened':'PASS','editable_mesh_parts':len(meshes),'closed_manifold_meshes':len(meshes),'external_links':0,'named_materials':sorted({m.name for o in meshes for m in o.data.materials}),'units':'metres','blender_version':bpy.app.version_string,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
(root/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if '--' in sys.argv:
    out=Path(sys.argv[sys.argv.index('--')+1]).resolve();assert out!=root and not out.exists();(out/'sources').mkdir(parents=True);shutil.copy(root/'generate.py',out/'generate.py')
    # Edit only the front plate's rib height, preserving its underside/support.
    for v in bpy.data.objects['MODULE_AccessPlate_Front'].data.vertices:
        if v.co.z>.029:v.co.z=.029
    bpy.data.materials['Satin aluminium access plates'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.5
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'sources/mall-escalator-landing.blend'),compress=True)
