from pathlib import Path
import bpy,importlib.util,hashlib,json
from mathutils import Vector
p=Path(__file__).resolve().parent;s=p/'sources'/(p.name+'.blend');before=hashlib.sha256(s.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(s))
spec=importlib.util.spec_from_file_location('generator',p/'generate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
scene=bpy.context.scene;scene.frame_set(1);scene.camera.data.ortho_scale=.80;target=Vector((0,0,.80));scene.camera.location=target+Vector((0,-.55,1.6));m.aim(scene.camera,target)
scene.render.filepath=str(p/'previews/detail.png');bpy.ops.render.render(write_still=True)
assert hashlib.sha256(s.read_bytes()).hexdigest()==before
(p/'reports/detail-preview.json').write_text(json.dumps({'frame':1,'source_sha256':before,'canonical_source_unchanged':True,'result':'PASS'},indent=2)+'\n')
