"""Reopen source, inspect solids, and save/reopen/re-export a controlled mesh edit."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tempfile
import bpy
import bmesh

HERE = Path(__file__).resolve().parent


def main():
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    source = HERE / 'sources/speaker-soundbar.blend'
    before = digest(source)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    root = bpy.data.objects['ASSET_SpeakerSoundbar']
    assert tuple(root.location) == (0, 0, 0)
    assert bpy.context.scene.unit_settings.system == 'METRIC'
    assert bpy.context.scene.unit_settings.scale_length == 1
    assert {obj.name for obj in root.children} == {'SOUNDBAR', 'FLOOR_SPEAKER'}
    objects = [obj for obj in root.children_recursive if obj.type == 'MESH']
    assert all(obj.type in {'EMPTY', 'MESH'} for obj in root.children_recursive)
    assert len({obj.data.materials[0].name for obj in objects}) == 3
    for obj in objects:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        assert all(edge.is_manifold for edge in bm.edges), obj.name
        assert bm.calc_volume() > 0, obj.name
        bm.free()
    image = bpy.data.images['Original procedural plain weave']
    assert image.packed_file and tuple(image.size) == (128, 128)
    assert max(image.pixels) > min(image.pixels)
    # Check front driver depth and the intended editable features in source.
    assert bpy.data.objects['SPEAKER_Woofer_Cone'].location.y == 0
    assert all(vertex.co.y < -.12 for vertex in bpy.data.objects['SPEAKER_Woofer_Cone'].data.vertices)
    assert len([obj for obj in objects if obj.name.endswith('_Cone')]) == 5
    assert len([obj for obj in objects if 'Woven' in obj.name]) == 3
    spec = importlib.util.spec_from_file_location('audio_generator', HERE / 'generate.py')
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    scratch = Path(tempfile.gettempdir()) / 'speaker-soundbar-source-edit'
    scratch.mkdir(exist_ok=True)
    module.export(scratch / 'source-reexport.glb')
    # Reopening can round evaluated bevel UVs; the Node verifier compares every
    # geometry attribute with explicit tolerances instead of requiring byte identity.
    for vertex in bpy.data.objects['BAR_Enclosure'].data.vertices:
        vertex.co.x *= .92
    material = bpy.data.materials['Graphite enclosure and rubber']
    material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .77
    bpy.ops.wm.save_as_mainfile(filepath=str(scratch / 'edited.blend'), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(scratch / 'edited.blend'))
    module.export(scratch / 'edited.glb')
    assert digest(source) == before
    report = {
        'result': 'PASS', 'source_reopened': True, 'editable_mesh_parts': len(objects),
        'closed_manifold_meshes': len(objects), 'asset_materials': 3, 'driver_cones': 5,
        'cloth_panels': 3, 'packed_original_texture': [128, 128], 'units': 'metres',
        'blender_version': bpy.app.version_string, 'source_sha256': before,
        'unchanged_source_reexport_sha256': digest(scratch / 'source-reexport.glb'),
        'original_source_unchanged': True, 'edited_mesh': 'BAR_Enclosure',
        'edit': 'Scale enclosure local X vertices by 0.92; graphite roughness to 0.77',
        'edited_glb_sha256': digest(scratch / 'edited.glb'),
    }
    (HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
