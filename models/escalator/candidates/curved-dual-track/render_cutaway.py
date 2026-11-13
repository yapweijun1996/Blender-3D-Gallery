from pathlib import Path
import bpy,hashlib,json
from mathutils import Vector
p=Path(__file__).resolve().parent;src=p/'sources/escalator-circulation.blend';before=hashlib.sha256(src.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(src));s=bpy.context.scene
# Diagnostic-only cutaway: conceal fixed opaque enclosure in memory, never save/export this state.
for o in bpy.data.objects:
 if o.name.startswith('TRUSS_'):o.hide_render=True
s.render.resolution_x=s.render.resolution_y=640;s.camera.data.ortho_scale=3.4
center=4.197
for frame,label,y,z in [(1,'lower-return-frame1',-center-.15,-.7),(15,'lower-return-frame15',-center-.15,-.7),(1,'upper-return-frame1',center+.15,2.3),(15,'upper-return-frame15',center+.15,2.3)]:
 s.frame_set(frame);target=Vector((0,y,z));s.camera.location=target+Vector((6,-.4,.25));s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(p/'previews'/('QA-cutaway-'+label+'.png'));bpy.ops.render.render(write_still=True)
assert hashlib.sha256(src.read_bytes()).hexdigest()==before
(p/'reports/cutaway-scope.json').write_text(json.dumps({'purpose':'Diagnostic view only. Fixed opaque TRUSS enclosure hidden in memory; every step/riser/wheel/rail remains visible. Canonical source and GLB retain full enclosure.','source_sha256':before,'canonical_unchanged':True},indent=2))
