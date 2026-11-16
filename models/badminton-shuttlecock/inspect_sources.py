"""Read-only source inspection and GLB reimport; never save the opened source."""
from pathlib import Path
import hashlib,json
import bpy
HERE=Path(__file__).resolve().parent
spec=json.loads((HERE/'backlog.json').read_text());SLUG=spec['slug'];SOURCE=HERE/'sources'/(SLUG+'.blend');GLB=HERE/'exports/optimized.glb'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(SOURCE)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));root=bpy.data.objects[spec['root']]
assert root.location.length<1e-9 and root['units']=='metres'
for feature in spec['features']:assert feature in bpy.data.objects,feature
mods={o.name:[dict(name=m.name,type=m.type) for m in o.modifiers] for o in root.children_recursive if o.modifiers}
if SLUG in ['american-football','rugby-ball']:
 for i in range(1,5):assert bpy.data.objects['PANEL_%02d'%i].modifiers[0].type=='SOLIDIFY'
 assert tuple(bpy.data.images['T_Grip_Normal'].size)==(1024,512)
elif SLUG=='badminton-shuttlecock':
 for i in range(1,17):assert bpy.data.objects['FEATHER_%02d'%i].modifiers[0].type=='SOLIDIFY'
else:
 for i in range(1,7):assert len(bpy.data.objects['STRIP_%02d'%i].data.vertices)>1000
source=dict(editable_objects=sorted(o.name for o in root.children_recursive),modifiers=mods,root_properties={k:root[k] for k in root.keys()})
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(GLB))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];triangles=0
for o in meshes:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
assert spec['root'] in bpy.data.objects and triangles>0
assets=json.loads((HERE/'reports/assets.json').read_text());assert triangles==assets['triangles']
assert sha(SOURCE)==before,'source must be unchanged'
report=dict(result='PASS',blender_version=bpy.app.version_string,source_reopened=True,source_sha256=before,original_source_unchanged=True,source=source,glb_reimported=True,glb_sha256=sha(GLB),reimport=dict(mesh_objects=len(meshes),triangles=triangles,objects=sorted(o.name for o in bpy.context.scene.objects)))
(HERE/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

# Avoid the supplied sandbox's PulseAudio shutdown hang after successful assertions.
if bpy.app.background:
 import os,sys
 sys.stdout.flush();sys.stderr.flush();os._exit(0)
