"""Reopen the native asset and verify controlled saved edits without altering delivery."""
from pathlib import Path
import bpy
import hashlib
import importlib.util
import json
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('lounge_generator', HERE / 'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
source = HERE / 'sources/lounge-sofa-bench.blend'
canonical_hash = hashlib.sha256(source.read_bytes()).hexdigest()
glb_hash = hashlib.sha256((HERE / 'exports/optimized.glb').read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
report = generator.measure_source()
assert report['source_mesh_parts'] == 34
assert len(report['source_materials']) == 3
assert report['root_location'] == [0, 0, 0]
assert report['source_text_objects'] == 0
with tempfile.TemporaryDirectory(prefix='lounge-source-check-') as directory:
    temporary = Path(directory)
    generator.export(temporary / 'reopened.glb')
    reopened_hash = hashlib.sha256((temporary / 'reopened.glb').read_bytes()).hexdigest()
    assert reopened_hash == glb_hash, 'Reopened native source must reproduce the delivered GLB'
    obj = bpy.data.objects['SOFA_SeatCushion_1']
    before = obj.location.z
    obj.location.z += .01
    bpy.data.materials['GreigeFabric'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .91
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(temporary / 'edited.blend'), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(temporary / 'edited.blend'))
    assert abs(bpy.data.objects['SOFA_SeatCushion_1'].location.z - before - .01) < 1e-6
    assert abs(bpy.data.materials['GreigeFabric'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value - .91) < 1e-6
    generator.export(temporary / 'edited.glb')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(temporary / 'edited.glb'))
    fabric = next(m for m in bpy.data.materials if m.name.startswith('GreigeFabric'))
    assert abs(fabric.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value - .91) < 1e-6
    assert hashlib.sha256(source.read_bytes()).hexdigest() == canonical_hash
    assert hashlib.sha256((HERE / 'exports/optimized.glb').read_bytes()).hexdigest() == glb_hash
    result = {'result': 'PASS', 'native_source_sha256': canonical_hash,
              'delivered_glb_sha256': glb_hash, 'reopened_source_export_sha256': reopened_hash,
              'checks': ['34 separate editable source meshes', 'three asset materials',
                         'reopened source reproduces delivery byte for byte',
                         'seat height edit survives save and reopen',
                         'material roughness edit survives save, reopen, export and GLB reimport',
                         'canonical source and export unchanged']}
    (HERE / 'reports/source-edit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
