"""Inspect editable source and re-import delivery without modifying the .blend."""
from pathlib import Path
import bpy,json,hashlib
HERE=Path(__file__).resolve().parent
spec=json.loads((HERE/'backlog.json').read_text()); slug=spec['slug']
source=HERE/'sources'/(slug+'.blend');glb=HERE/'exports/optimized.glb'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(source);bpy.ops.wm.open_mainfile(filepath=str(source))
assert bpy.app.version_string=='5.3.0'
scene=bpy.context.scene
assert scene.render.engine=='CYCLES' and scene.cycles.samples==32
assert scene.render.resolution_x==scene.render.resolution_y==900 and scene.render.resolution_percentage==100
render_settings={'engine':scene.render.engine,'samples':scene.cycles.samples,'resolution':[scene.render.resolution_x,scene.render.resolution_y]}
root=bpy.data.objects[spec['root']];assert root['units']=='metres'
for name in spec['features']:assert name in bpy.data.objects,name
if slug=='bowling-ball':assert len([m for m in bpy.data.objects['BALL_Shell'].modifiers if m.type=='BOOLEAN'])==3
if slug=='ice-hockey-puck':assert bpy.data.objects['PUCK_Rubber'].modifiers[0].type=='BEVEL'
editable={n:len(bpy.data.objects[n].data.vertices) for n in spec['features']}
images=[{'name':i.name,'size':list(i.size),'path':i.filepath} for i in bpy.data.images if i.users and i.type=='IMAGE']
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(glb))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];triangles=0
for o in meshes:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
assets=json.loads((HERE/'reports/assets.json').read_text());assert triangles==assets['triangles'];assert spec['root'] in bpy.data.objects
assert sha(source)==before
report={'result':'PASS','blender_version':bpy.app.version_string,'source_reopened':True,'preview_render_settings':render_settings,'source_sha256':before,'original_source_unchanged':True,'editable_meshes':editable,'source_images':images,'glb_reimported':True,'glb_sha256':sha(glb),'triangles':triangles,'mesh_objects':len(meshes)}
(HERE/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

# Avoid this host's PulseAudio teardown hang after synchronous report writes.
if bpy.app.background:
    import os,sys
    sys.stdout.flush();sys.stderr.flush();os._exit(0)
