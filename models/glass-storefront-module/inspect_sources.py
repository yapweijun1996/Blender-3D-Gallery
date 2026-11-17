"""Inspect saved source and test a saved-edit export without changing delivery."""
from pathlib import Path
import importlib.util
import json
import sys
import bpy

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources/glass-storefront-module.blend'))
roots = [bpy.data.objects['ASSET_GlassStorefrontModule'], bpy.data.objects['ASSET_GlassStorefrontModule_Open']]
assert bpy.context.scene.unit_settings.scale_length == 1
parts = {}
for root in roots:
    assert tuple(root.location) == (0, 0, 0)
    children = [o for o in root.children_recursive if o.type == 'MESH']
    assert all(o.data.validate() is False for o in children)
    assert all(len(o.data.materials) == 1 for o in children)
    parts[root.name] = [o.name for o in children]
for name in ['collider_box', 'collider_box_Open']:
    o = bpy.data.objects[name]
    assert o.hide_render and o.hide_get() and len(o.data.materials) == 0
report = {'result': 'PASS', 'blender_version': bpy.app.version_string,
          'unit_scale': 1, 'source_parts': parts, 'external_images': len(bpy.data.images)}
(HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
if '--source-edit' in sys.argv:
    bpy.context.preferences.filepaths.save_version = 0
    bpy.data.objects['HEADER_BlankSignBand_Closed'].location.z += .02
    proof = '/tmp/glass-storefront-module-source-edit.blend'
    bpy.ops.wm.save_as_mainfile(filepath=proof, compress=True)
    bpy.ops.wm.open_mainfile(filepath=proof)
    spec = importlib.util.spec_from_file_location('storefront_generator', HERE / 'generate.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    generator.export(Path('/tmp/glass-storefront-module-source-edit.glb'))
print(json.dumps(report))
