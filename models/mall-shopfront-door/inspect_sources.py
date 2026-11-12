from pathlib import Path
import bpy,bmesh,json,hashlib,sys,shutil,math
root=Path(__file__).resolve().parent;source=root/'sources/mall-shopfront-door.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));asset=bpy.data.objects['ASSET_MallShopfrontDoor']
meshes=[o for o in asset.children_recursive if o.type=='MESH']
assert tuple(asset.location)==(0,0,0) and bpy.context.scene.unit_settings.scale_length==1
assert len(meshes)==33
for obj in meshes:
    bm=bmesh.new();bm.from_mesh(obj.data);assert all(e.is_manifold for e in bm.edges),obj.name;assert bm.calc_volume()>0,obj.name;bm.free()
fixed=bpy.data.objects['FRAME_Fixed'];unchanged={o.name:[list(r) for r in o.matrix_world] for o in fixed.children}
for name,sign in [('Left',-1),('Right',1)]:
    pivot=bpy.data.objects['HINGE_'+name];assert tuple(round(v,4) for v in pivot.location)==(sign*.95,-.04,0)
    assert len(pivot.children)==13
    original=bpy.data.objects['GLASS_'+name].matrix_world.translation.copy()
    pivot.rotation_euler.z=sign*math.pi/2;bpy.context.view_layer.update()
    moved=bpy.data.objects['GLASS_'+name].matrix_world.translation
    assert moved.y<original.y-.4
    assert all([list(r) for r in o.matrix_world]==unchanged[o.name] for o in fixed.children)
    pivot.rotation_euler.z=0;bpy.context.view_layer.update()
report={'closed_manifold_meshes':33,'source_reopened':'PASS','editable_mesh_parts':33,'hinge_source_test':'PASS, left and right 90-degree rotations move leaf glass without moving fixed frame','named_materials':sorted({m.name for o in meshes for m in o.data.materials}),'units':'metres','blender_version':bpy.app.version_string,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
(root/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if '--' in sys.argv:
    out=Path(sys.argv[sys.argv.index('--')+1]).resolve();assert out!=root and not out.exists()
    (out/'sources').mkdir(parents=True);shutil.copy(root/'generate.py',out/'generate.py')
    for v in bpy.data.objects['HANDLE_Left_Front'].data.vertices:
        if v.co.z>0:v.co.z+=.02
    p=bpy.data.materials['Brushed stainless pull hardware'].node_tree.nodes['Principled BSDF'];p.inputs['Roughness'].default_value=.55
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'sources/mall-shopfront-door.blend'),compress=True)
