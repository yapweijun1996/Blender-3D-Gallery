"""Inspect saved native geometry and optionally export a controlled edited copy."""
from pathlib import Path
import json
import sys
import importlib.util
import hashlib
import bpy

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('sign_generator', HERE / 'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources/led-strip-sign-module.blend'))
root = bpy.data.objects[generator.ROOT]
assert tuple(root.location) == (0, 0, 0)
assert bpy.context.scene.unit_settings.scale_length == 1
assert len(bpy.data.materials) == 3
meshes = [o for o in root.children_recursive if o.type == 'MESH']
assert len(meshes) == 16
assert not [o for o in bpy.data.objects if o.type in ['FONT', 'CAMERA', 'LIGHT']]
assert not bpy.data.images
parts = {}
deps = bpy.context.evaluated_depsgraph_get()
for o in meshes:
    evaluated = o.evaluated_get(deps)
    mesh = evaluated.to_mesh()
    assert not mesh.validate()
    assert all(all(__import__('math').isfinite(v) for v in vertex.co) for vertex in mesh.vertices)
    coords = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    parts[o.name] = {'delivery_mesh': o['delivery_mesh'], 'bounds_blender': {
        'min': [min(v[i] for v in coords) for i in range(3)],
        'max': [max(v[i] for v in coords) for i in range(3)]},
        'materials': [m.name for m in o.data.materials]}
    evaluated.to_mesh_clear()
report = {'result': 'PASS', 'blender_version': bpy.app.version_string, 'source_meshes': len(meshes),
          'materials': len(bpy.data.materials), 'external_images': len(bpy.data.images),
          'source_sha256': hashlib.sha256((HERE / 'sources/led-strip-sign-module.blend').read_bytes()).hexdigest(),
          'parts': parts}
(HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
if '--edit-copy' in sys.argv:
    face = bpy.data.objects['Face_Blank']
    face.location.x += .02
    led = bpy.data.materials['Warm white LED diffuser'].node_tree.nodes['Principled BSDF']
    led.inputs['Emission Strength'].default_value = 2
    destination = HERE / 'reports/source-edit'
    destination.mkdir(exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(destination / 'edited.blend'), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(destination / 'edited.blend'))
    assert abs(bpy.data.objects['Face_Blank'].location.x - .02) < 1e-6
    assert bpy.data.materials['Warm white LED diffuser'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value == 2
    generator.export(destination / 'edited.glb')
print(json.dumps({'result': 'PASS', 'source_meshes': len(meshes), 'materials': 3}))
