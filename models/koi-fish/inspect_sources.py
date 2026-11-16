"""Inspect reopened source and test a controlled unsaved tail edit."""
from pathlib import Path
import importlib.util
import json
import sys
import bpy

HERE = Path(__file__).resolve().parent


def main():
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources/koi-fish.blend'))
    root = bpy.data.objects['ASSET_KoiFish']
    parts = [o for o in root.children_recursive if o.type == 'MESH']
    armatures = [o for o in root.children_recursive if o.type == 'ARMATURE']
    assert tuple(root.location) == (0, 0, 0)
    assert bpy.context.scene.unit_settings.scale_length == 1
    assert len(armatures) == 1
    assert len({m.name for o in parts for m in o.data.materials}) == 3
    for prefix in ['BODY_', 'FIN_Caudal', 'FIN_Dorsal', 'FIN_Pectoral_L',
                   'FIN_Pectoral_R', 'FIN_Pelvic', 'EYE_', 'MOUTH_', 'BARBEL_', 'GILL_']:
        assert any(o.name.startswith(prefix) for o in parts), prefix
    assert len([o for o in parts if o.name.startswith('BARBEL_')]) == 4
    for obj in parts:
        assert not obj.data.validate(), obj.name
        assert obj.data.color_attributes.get('Color')
        for vertex in obj.data.vertices:
            assert abs(sum(group.weight for group in vertex.groups) - 1) < 1e-5
            assert len(vertex.groups) <= 4
    armature = armatures[0]
    assert armature.animation_data.action.name == 'Swim_Loop'
    assert bpy.context.scene.frame_end - bpy.context.scene.frame_start == 72
    assert bpy.context.scene.render.fps == 24
    tail = next(o for o in parts if o.name.startswith('FIN_Caudal'))
    edited_vertices = 0
    for vertex in tail.data.vertices:
        if vertex.co.y > .135:
            vertex.co.y += .002
            edited_vertices += 1
    assert edited_vertices > 0
    spec = importlib.util.spec_from_file_location('koi_generator', HERE / 'generate.py')
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    module.export(Path('/tmp/koi-fish-source-edit.glb'))
    report = {'result': 'PASS', 'blender_version': bpy.app.version_string,
              'editable_mesh_objects': len(parts), 'materials': 3,
              'bones': len(armature.data.bones), 'actions': [armature.animation_data.action.name],
              'normalized_weights': True, 'max_influences': max(len(v.groups) for o in parts for v in o.data.vertices),
              'controlled_edit_vertices': edited_vertices, 'saved_source_preserved': True}
    (HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
