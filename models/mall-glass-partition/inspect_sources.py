from pathlib import Path
import bpy,bmesh,json,hashlib,sys,shutil
root=Path(__file__).resolve().parent;source=root/'sources/mall-glass-partition.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));asset=bpy.data.objects['ASSET_MallGlassPartition']
meshes=[o for o in asset.children_recursive if o.type=='MESH']
assert tuple(asset.location)==(0,0,0) and bpy.context.scene.unit_settings.scale_length==1
assert len(meshes)==15
for obj in meshes:
    bm=bmesh.new();bm.from_mesh(obj.data);assert all(e.is_manifold for e in bm.edges),obj.name;assert bm.calc_volume()>0,obj.name;bm.free()
for side,x in [('Left',-.57),('Right',.57)]:
    c=bpy.data.objects['CONNECTOR_'+side];assert tuple(round(v,4) for v in c.location)==(x,0,0)
assert len(bpy.data.objects['PANES_StaticGlazing'].children)==8
report={'closed_manifold_meshes':15,'source_reopened':'PASS','editable_mesh_parts':15,'connector_source_test':'PASS, two ground-plane named connectors at +/-0.57 m','named_materials':sorted({m.name for o in meshes for m in o.data.materials}),'units':'metres','blender_version':bpy.app.version_string,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
(root/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if '--' in sys.argv:
    out=Path(sys.argv[sys.argv.index('--')+1]).resolve();assert out!=root and not out.exists()
    (out/'sources').mkdir(parents=True);shutil.copy(root/'generate.py',out/'generate.py')
    # Demonstrate independently editable source mesh, not regeneration from constants.
    for v in bpy.data.objects['BAND_Left_Front'].data.vertices:
        if v.co.z>0:v.co.z+=.01
    p=bpy.data.materials['Satin charcoal aluminium'].node_tree.nodes['Principled BSDF'];p.inputs['Roughness'].default_value=.5
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'sources/mall-glass-partition.blend'),compress=True)
