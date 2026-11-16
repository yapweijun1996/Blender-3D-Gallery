"""Reopen source, inspect editable components, export a controlled unsaved edit."""
from pathlib import Path
import importlib.util
import json
import sys
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent


def main():
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources/aquarium-tank.blend'))
    root = bpy.data.objects['ASSET_AquariumTank']
    meshes = [o for o in root.children_recursive if o.type == 'MESH']
    assert tuple(root.location) == (0, 0, 0)
    assert bpy.context.scene.unit_settings.scale_length == 1
    prefixes = ('CABINET_', 'GLASS_', 'WATER_', 'SUBSTRATE_', 'ROCK_', 'LEAF_', 'LIGHT_', 'LID_')
    for prefix in prefixes:
        assert any(o.name.startswith(prefix) for o in meshes), prefix
    assert len({m.name for o in meshes for m in o.data.materials}) == 3
    assert not any('FISH' in o.name.upper() for o in meshes)
    for o in meshes:
        assert not o.data.validate(), o.name
    points = [o.matrix_world @ Vector(corner) for o in meshes
              if o.name.startswith(('GLASS_LongPane', 'GLASS_EndPane')) for corner in o.bound_box]
    native_dimensions = [max(p[i] for p in points) - min(p[i] for p in points) for i in range(3)]
    report = {'result': 'PASS', 'blender_version': bpy.app.version_string,
              'editable_mesh_objects': len(meshes), 'asset_materials': 3,
              'tank_enclosure_dimensions_metres': [native_dimensions[i] for i in (0, 2, 1)],
              'required_prefixes': list(prefixes), 'source_preserved': True}
    door = next(o for o in meshes if o.name.startswith('CABINET_Door'))
    door.location.y -= .04
    spec = importlib.util.spec_from_file_location('aquarium_generator', HERE / 'generate.py')
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    module.export(Path('/tmp/aquarium-tank-source-edit.glb'))
    (HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
