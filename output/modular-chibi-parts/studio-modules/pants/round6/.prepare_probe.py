import bpy
import runpy
from pathlib import Path

fit = runpy.run_path(str(Path(__file__).with_name('fit_pants_r6.py')))
scene, arm, body = fit['BASE']['load_master']()
bpy.ops.import_scene.gltf(filepath=str(fit['SOURCE']), merge_vertices=True)
garment, = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
names = tuple(arm.pose.bones.keys())
faces = fit['faces_of'](body.data)
points = fit['BASE']['evaluated_coordinates'](body)
rest = fit['tree_for'](points, faces.tolist())
print('BODY', len(points), len(faces), scene.render.fps, flush=True)
p, w, t = fit['prepare'](garment, rest, names, body, faces, points)
print('PREPARED', len(p), len(fit['faces_of'](garment.data)), t, flush=True)
fit['save'].__globals__['GLB'] = fit['HERE']/'.prepared.glb'
fit['save'](arm, body, garment, p, w, names)
