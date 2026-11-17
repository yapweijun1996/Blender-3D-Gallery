"""Reopen source, inspect authored parts and test edits without modifying delivery."""
from pathlib import Path
import hashlib
import json
import runpy
import sys
import bpy

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = HERE / 'sources/atrium-fountain.blend'
    delivery = HERE / 'exports/optimized.glb'
    before = (sha(source), sha(delivery))
    bpy.ops.wm.open_mainfile(filepath=str(source))
    root = bpy.data.objects['ASSET_AtriumFountain']
    assert tuple(root.location) == (0, 0, 0)
    assert bpy.context.scene.unit_settings.scale_length == 1
    parts = [o for o in root.children_recursive if o.type == 'MESH']
    assert len({m.name for o in parts for m in o.data.materials}) == 3
    assert all(o.name.startswith(('STONE_', 'METAL_', 'WATER_', 'POOL_')) for o in parts)
    assert not bpy.data.images
    for o in parts:
        assert not o.data.validate(verbose=True), o.name
    assert abs(max(v.co.z for v in bpy.data.objects['STONE_Basin'].data.vertices) - .8) < 1e-6
    assert bpy.data.objects['WATER_Jets']['jet_count'] == 8
    module = runpy.run_path(str(HERE / 'generate.py'))
    bpy.data.objects['WATER_Jets'].location.z += .02
    module['export'](Path('/tmp/atrium-fountain-source-edit.glb'))
    assert before == (sha(source), sha(delivery)), 'original source and delivery preserved'
    report = {'result': 'PASS', 'blender_version': bpy.app.version_string,
              'source_sha256': before[0], 'delivery_sha256': before[1],
              'editable_meshes': len(parts), 'asset_materials': 3,
              'parts': [o.name for o in parts], 'source_mesh_validation': 'PASS',
              'edit': 'Reopened source; translated WATER_Jets upward 0.02 m; exported temporary copy.',
              'edited_glb': '/tmp/atrium-fountain-source-edit.glb',
              'original_source_and_glb_preserved': True}
    (HERE / 'reports/source.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
