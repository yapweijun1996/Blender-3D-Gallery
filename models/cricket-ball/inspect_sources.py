"""Inspect editable sources, then reimport GLB without saving the source."""
from pathlib import Path
import bpy,json,hashlib
HERE=Path(__file__).resolve().parent
CFG=json.loads((HERE/'config.json').read_text());SLUG=CFG['slug'];SOURCE=HERE/'sources'/(SLUG+'.blend');GLB=HERE/'exports/optimized.glb'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(SOURCE)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
root=bpy.data.objects[CFG['root']]
spec=json.loads((HERE/'backlog.json').read_text())
for name in spec['features']:assert name in bpy.data.objects,name
meshes=[o for o in root.children if o.type=='MESH']
for o in meshes:assert o.modifiers['Export triangulation'].type=='TRIANGULATE'
image=bpy.data.images['T_Surface_Normal'];assert tuple(image.size)==(1024,512)
assert (HERE/'sources/textures'/(SLUG+'_grain_normal.png')).is_file()
assert root['units']=='metres' and root['front_axis']=='Blender -Y / glTF +Z'
source=dict(editable_meshes=[o.name for o in meshes],modifiers={o.name:[m.type for m in o.modifiers] for o in meshes},root_properties={k:(list(root[k]) if hasattr(root[k], "to_list") else root[k]) for k in root.keys()},normal_map=dict(size=list(image.size),filepath=image.filepath))
if CFG['stitch_pairs']:
 name='STITCHES_SixRows' if SLUG=='cricket-ball' else 'STITCHES_Double'
 assert name in bpy.data.objects
 assert len(bpy.data.objects[name].data.vertices)==(6*72 if SLUG=='cricket-ball' else CFG['stitch_pairs']*2)*(15 if SLUG=='cricket-ball' else 24)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(GLB))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];triangles=0
for o in meshes:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
assets=json.loads((HERE/'reports/assets.json').read_text());assert triangles==assets['triangles']
assert CFG['root'] in bpy.data.objects
assert any(i.users for i in bpy.data.images)
assert sha(SOURCE)==before
report=dict(result='PASS',blender_version=bpy.app.version_string,source_reopened=True,source_sha256=before,original_source_unchanged=True,source=source,glb_reimported=True,glb_sha256=sha(GLB),reimport=dict(mesh_objects=len(meshes),triangles=triangles,images=[i.name for i in bpy.data.images if i.users]))
(HERE/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

# Match the generator: avoid this worker's hanging audio teardown after synchronous checks.
if bpy.app.background:
    import os,sys
    sys.stdout.flush();sys.stderr.flush();os._exit(0)
