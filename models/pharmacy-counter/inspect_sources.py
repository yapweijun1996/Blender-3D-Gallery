"""Inspect saved geometry and actual clearances; exercise edits in a disposable source copy."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import bpy
import bmesh

HERE = Path(__file__).resolve().parent


def main():
    source = HERE / 'sources/pharmacy-counter.blend'
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    before = digest(source)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    root = bpy.data.objects['ASSET_PharmacyCounter']
    objects = sorted(root.children_recursive, key=lambda obj: obj.name)
    assert all(obj.type == 'MESH' for obj in objects), 'No text, curves or external content'
    assert bpy.context.scene.unit_settings.system == 'METRIC'
    assert bpy.context.scene.unit_settings.scale_length == 1
    assert tuple(root.location) == (0, 0, 0)
    assert tuple(root.scale) == (1, 1, 1)
    assert len({obj.data.materials[0].name for obj in objects}) == 3
    assert not any(image.source == 'FILE' for image in bpy.data.images), 'No external images'
    parts = {}
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
    near = lambda a, b: abs(a - b) < 1e-5
    top = parts['COUNTER_Top']
    assert near(top['max'][2], .9)
    assert near(top['max'][0] - top['min'][0], 3)
    assert near(top['max'][1] - top['min'][1], .8)
    left, right = parts['PARTITION_WindowPost_Left'], parts['PARTITION_WindowPost_Right']
    opening_width = right['min'][0] - left['max'][0]
    opening_height = parts['PARTITION_PassThroughRail']['min'][2] - top['max'][2]
    assert opening_width > .8 and opening_height > .3
    assert parts['PICKUP_TrayBase']['min'][1] < parts['GLASS_CentreUpper']['min'][1]
    assert parts['PICKUP_TrayBase']['max'][1] > parts['GLASS_CentreUpper']['max'][1]
    assert near(parts['PICKUP_TrayBase']['min'][2], top['max'][2])
    assert parts['PICKUP_RearLip']['max'][2] < parts['PARTITION_PassThroughRail']['min'][2]
    shelves = [parts['DISPENSING_Shelf_' + str(i)] for i in range(4)]
    assert len(shelves) == 4
    for shelf in shelves:
        assert shelf['min'][1] > parts['GLASS_Left']['max'][1], 'Rack behind partition'
        assert shelf['min'][2] >= top['max'][2] - 1e-5
        assert shelf['max'][1] <= top['max'][1]
    assert parts['QUEUE_Housing']['min'][1] < parts['GLASS_Right']['min'][1], 'Queue faces customers'
    assert near(parts['QUEUE_Base']['min'][2], top['max'][2])
    assert all(part['min'][2] >= -1e-6 for part in parts.values()), 'Floor datum'
    spec = importlib.util.spec_from_file_location('asset_generator', HERE / 'generate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    scratch = HERE / 'reports/source-edit'
    scratch.mkdir(exist_ok=True)
    module.export(scratch / 'source-reexport.glb')
    assert digest(scratch / 'source-reexport.glb') == digest(HERE / 'exports/optimized.glb')
    # Change the shelf unit in a copy, then reopen it before exporting again.
    target = bpy.data.objects['DISPENSING_Shelf_1']
    target.location.z += .045
    target.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .71
    bpy.ops.wm.save_as_mainfile(filepath=str(scratch / 'edited.blend'), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(scratch / 'edited.blend'))
    module.export(scratch / 'edited.glb')
    assert digest(source) == before
    report = {
        'result': 'PASS', 'source_reopened': True, 'editable_mesh_parts': len(objects),
        'closed_manifold_meshes': len(objects), 'asset_materials': 3,
        'units': 'metres', 'blender_version': bpy.app.version_string, 'source_sha256': before,
        'unchanged_source_reexport_sha256': digest(scratch / 'source-reexport.glb'),
        'original_source_unchanged': True, 'edited_mesh': 'DISPENSING_Shelf_1',
        'edit': 'Shelf raised 0.045 m; graphite roughness changed to 0.71',
        'edited_glb_sha256': digest(scratch / 'edited.glb'),
        'service_height': top['max'][2], 'pass_through_width': opening_width,
        'pass_through_height_above_worktop': opening_height,
        'pass_through_clear_height_above_tray_lips': parts['PARTITION_PassThroughRail']['min'][2] - parts['PICKUP_Side_Left']['max'][2],
        'shelf_levels': len(shelves), 'shelf_top_heights': [shelf['max'][2] for shelf in shelves],
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
