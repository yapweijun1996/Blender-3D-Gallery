from pathlib import Path
import bpy,importlib.util,hashlib,json
from mathutils import Vector
p=Path(__file__).resolve().parent;s=p/'sources'/(p.name+'.blend');before=hashlib.sha256(s.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(s))
spec=importlib.util.spec_from_file_location('generator',p/'generate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
scene=bpy.context.scene;scene.frame_set(30);bpy.context.view_layer.update()
root=bpy.data.objects[m.ROOT];points=[o.matrix_world@Vector(c) for o in root.children_recursive if o.type in ['MESH','FONT'] for c in o.bound_box]
lo=Vector(tuple(min(v[i] for v in points) for i in range(3)));hi=Vector(tuple(max(v[i] for v in points) for i in range(3)));target=(lo+hi)/2;scale=max(m.SCALE,max(hi-lo)*1.6)
scene.camera.data.ortho_scale=scale;scene.camera.location=target+Vector((1.3,2,1))*scale;m.aim(scene.camera,target)
scene.render.filepath=str(p/'previews/open.png');bpy.ops.render.render(write_still=True)
assert hashlib.sha256(s.read_bytes()).hexdigest()==before
(p/'reports/open-preview.json').write_text(json.dumps({'frame':30,'source_sha256':before,'canonical_source_unchanged':True,'result':'PASS'},indent=2)+'\n')
