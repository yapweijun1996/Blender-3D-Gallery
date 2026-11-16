"""Inspect saved watch features and persist a controlled source edit on a copy."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import bpy
import bmesh

HERE = Path(__file__).resolve().parent


def main():
    source = HERE / 'sources/watch-display-case.blend'
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    before = digest(source)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    root = bpy.data.objects['ASSET_WatchDisplayCase']
    objects = sorted((obj for obj in root.children_recursive if obj.type == 'MESH'), key=lambda obj: obj.name)
    assert bpy.context.scene.unit_settings.system == 'METRIC'
    assert bpy.context.scene.unit_settings.scale_length == 1
    assert tuple(root.location) == (0, 0, 0)
    assert tuple(root.scale) == (1, 1, 1)
    assert len({obj.data.materials[0].name for obj in objects}) == 3
    assert not any(obj.type == 'FONT' for obj in root.children_recursive)
    assert len(bpy.data.images) == 1
    image = next(iter(bpy.data.images))
    assert tuple(image.size) == (4, 2) and image.packed_file
    pixels = list(image.pixels)
    assert max(pixels[0:3]) < .001 and min(pixels[12:15]) > .3
    parts = {}
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        assert all(edge.is_manifold for edge in bm.edges), obj.name
        assert bm.calc_volume() > 0, obj.name
        bm.free()
        assert len(obj.data.materials) == 1
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        points = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
        parts[obj.name] = {
            'min': [min(point[i] for point in points) for i in range(3)],
            'max': [max(point[i] for point in points) for i in range(3)],
            'material': obj.data.materials[0].name,
        }
        evaluated.to_mesh_clear()
    watches = [obj for obj in root.children if obj.name.startswith('WATCH_')]
    assert len(watches) == 8
    assert len([obj for obj in watches if obj['face_shape'] == 'round']) == 4
    assert len([obj for obj in watches if obj['face_shape'] == 'square']) == 4
    assert len([name for name in parts if name.startswith('CUSHION_')]) == 8
    assert len([name for name in parts if name.startswith('STRAP_')]) == 8
    assert len([name for name in parts if name.startswith('DIAL_')]) == 8
    assert len([name for name in parts if name.startswith('MARKER_')]) == 96
    assert len([name for name in parts if name.startswith('HAND_')]) == 16
    assert len([name for name in parts if name.startswith('LIGHT_')]) == 2
    assert len([name for name in parts if name.startswith('GLASS_')]) == 5
    assert all(part['min'][2] >= -1e-6 for part in parts.values())
    assert abs(parts['BASE_Platform']['min'][2]) < 1e-6
    # Independent evaluated bounds: merchandise stays inside the glazed chamber.
    clearance = min(parts['GLASS_Top']['min'][2] - parts[obj.name]['max'][2]
                    for watch in watches for obj in watch.children if obj.type == 'MESH')
    assert clearance > .10
    for watch in watches:
        for obj in watch.children:
            part = parts[obj.name]
            assert part['min'][0] > -.475 and part['max'][0] < .475
            assert part['min'][1] > -.225 and part['max'][1] < .225
    spec = importlib.util.spec_from_file_location('asset_generator', HERE / 'generate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    scratch = HERE / 'reports/source-edit'
    scratch.mkdir(exist_ok=True)
    module.export(scratch / 'source-reexport.glb')
    assert digest(scratch / 'source-reexport.glb') == digest(HERE / 'exports/optimized.glb')
    target = bpy.data.objects['BASE_Platform']
    for vertex in target.data.vertices:
        vertex.co.x *= .92
    target.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .77
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(scratch / 'edited.blend'), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(scratch / 'edited.blend'))
    module.export(scratch / 'edited.glb')
    assert digest(source) == before
    report = {
        'result': 'PASS', 'source_reopened': True, 'editable_mesh_parts': len(objects),
        'closed_manifold_meshes': len(objects), 'asset_materials': 3,
        'watch_count': len(watches), 'round_faces': 4, 'square_faces': 4,
        'cushions': 8, 'edge_strips': 2, 'glass_panels': 5,
        'minimum_watch_to_top_glass_clearance_metres': clearance,
        'units': 'metres', 'blender_version': bpy.app.version_string, 'source_sha256': before,
        'unchanged_source_reexport_sha256': digest(scratch / 'source-reexport.glb'),
        'original_source_unchanged': True, 'edited_mesh': 'BATCH_Softsurfaces',
        'edit': 'BASE_Platform local mesh X scaled by 0.92; soft surface roughness to 0.77',
        'edited_glb_sha256': digest(scratch / 'edited.glb'),
        'parts_axis_order': 'Blender X,Y,Z (width,depth,height)', 'parts': parts,
    }
    (HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'parts'}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
