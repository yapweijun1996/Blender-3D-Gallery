from pathlib import Path
import bpy,bmesh,json,hashlib,sys,shutil
root=Path(__file__).resolve().parent;source=root/'sources/mall-floor-tile-module.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));asset=bpy.data.objects['ASSET_MallFloorTile']
assert tuple(asset.location)==(0,0,0) and bpy.context.scene.unit_settings.scale_length==1
assert len(asset.children)==5 and all(o.type=='MESH' for o in asset.children)
assert len([o for o in asset.children if o.name.startswith('MODULE_Tile_')])==4
assert len([i for i in bpy.data.images if i.packed_file])==1
for obj in asset.children:
    bm=bmesh.new();bm.from_mesh(obj.data);assert all(e.is_manifold for e in bm.edges),obj.name;assert bm.calc_volume()>0,obj.name;bm.free()
report={'closed_manifold_meshes':5,'source_reopened':'PASS','editable_mesh_parts':5,'named_materials':sorted({m.name for o in asset.children for m in o.data.materials}),'packed_original_textures':1,'units':'metres','blender_version':bpy.app.version_string,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
(root/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if '--' in sys.argv:
    out=Path(sys.argv[sys.argv.index('--')+1]).resolve();assert out!=root and not out.exists()
    (out/'sources').mkdir(parents=True);shutil.copy(root/'generate.py',out/'generate.py')
    # Genuine independent mesh edit: raise only top vertices of one tile by 4 mm.
    tile=bpy.data.objects['MODULE_Tile_1']
    for v in tile.data.vertices:
        if v.co.z>0:v.co.z+=.004
    finish=bpy.data.materials['Honed ivory terrazzo original seed 421']
    finish.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.48
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'sources/mall-floor-tile-module.blend'),compress=True)
    print('Isolated saved-source mesh and roughness edits created')
