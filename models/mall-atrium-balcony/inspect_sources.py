from pathlib import Path
import bpy,bmesh,json,hashlib,sys,shutil
root=Path(__file__).resolve().parent;source=root/'sources/mall-atrium-balcony.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));asset=bpy.data.objects['ASSET_MallAtriumBalcony'];meshes=[o for o in asset.children_recursive if o.type=='MESH']
assert tuple(asset.location)==(0,0,0) and bpy.context.scene.unit_settings.scale_length==1
for o in meshes:
    bm=bmesh.new();bm.from_mesh(o.data);assert all(e.is_manifold for e in bm.edges),o.name;assert bm.calc_volume()>0,o.name;bm.free()
assert len([o for o in meshes if o.name.startswith('RAILING_')])==43
assert len([o for o in meshes if o.name.startswith('FLOOR_Tile_')])==8
assert all(o.library is None for o in asset.children_recursive)
images=[i for i in bpy.data.images if i.source=='FILE'];assert images and all(i.packed_file for i in images)
report={'source_reopened':'PASS','editable_mesh_parts':len(meshes),'closed_manifold_meshes':len(meshes),'railing_source_parts':43,'tiles':8,'external_links':0,'all_images_packed':True,'named_materials':sorted({m.name for o in meshes for m in o.data.materials}),'units':'metres','blender_version':bpy.app.version_string,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
(root/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if '--' in sys.argv:
    out=Path(sys.argv[sys.argv.index('--')+1]).resolve();assert out!=root and not out.exists();(out/'sources').mkdir(parents=True);shutil.copy(root/'generate.py',out/'generate.py')
    for v in bpy.data.objects['EDGE_Fascia'].data.vertices:v.co.z*=.9
    bpy.data.materials['Champagne anodised fascia'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.5
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'sources/mall-atrium-balcony.blend'),compress=True)
