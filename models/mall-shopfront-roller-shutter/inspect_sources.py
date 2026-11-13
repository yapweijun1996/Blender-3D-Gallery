from pathlib import Path
import bpy,bmesh,json,hashlib,sys,shutil,runpy
root=Path(__file__).resolve().parent;source=root/'sources/mall-shopfront-roller-shutter.blend';h=runpy.run_path(str(root/'generate.py'))
bpy.ops.wm.open_mainfile(filepath=str(source));asset=bpy.data.objects['ASSET_MallShopfrontRollerShutter'];meshes=[o for o in asset.children_recursive if o.type=='MESH']
assert tuple(asset.location)==(0,0,0) and bpy.context.scene.unit_settings.scale_length==1
assert len(meshes)==44
for obj in meshes:
    bm=bmesh.new();bm.from_mesh(obj.data);assert all(e.is_manifold for e in bm.edges),obj.name;assert bm.calc_volume()>0,obj.name;bm.free()
fixed=bpy.data.objects['FRAME_Fixed'];unchanged={o.name:[list(r) for r in o.matrix_world] for o in fixed.children}
for lift in [0,1.3,2.6,0]:
    h['pose'](lift)
    assert abs(bpy.data.objects['BOTTOM_Seal'].location.z-.005-lift)<1e-6
    assert all([list(r) for r in o.matrix_world]==unchanged[o.name] for o in fixed.children)
report={'closed_manifold_meshes':44,'source_reopened':'PASS','editable_mesh_parts':44,'source_pose_test':'PASS: closed, part-open, open, reset with fixed assembly unchanged','named_materials':sorted({m.name for o in meshes for m in o.data.materials}),'units':'metres','blender_version':bpy.app.version_string,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
(root/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if '--' in sys.argv:
    out=Path(sys.argv[sys.argv.index('--')+1]).resolve();assert out!=root and not out.exists()
    (out/'sources').mkdir(parents=True);shutil.copy(root/'generate.py',out/'generate.py')
    for v in bpy.data.objects['BOTTOM_Rail'].data.vertices:
        if v.co.z>0:v.co.z+=.002
    p=bpy.data.materials['Satin galvanized shutter slats'].node_tree.nodes['Principled BSDF'];p.inputs['Roughness'].default_value=.5
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'sources/mall-shopfront-roller-shutter.blend'),compress=True)
