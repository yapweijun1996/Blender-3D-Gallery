"""Inspect the shipped source and compare a deterministic rebuild separately."""
from pathlib import Path
import json
import sys
import bpy
import bmesh

HERE = Path(__file__).resolve().parent


def main():
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources/skylight-roof-module.blend'))
    root = bpy.data.objects['ASSET_SkylightRoofModule']
    parts = [o for o in root.children_recursive if o.type == 'MESH']
    assert bpy.context.scene.unit_settings.scale_length == 1
    assert tuple(root.location) == (0, 0, 0)
    assert len([o for o in parts if o.name.startswith('GLASS_')]) == 16
    assert len({m.name for o in parts for m in o.data.materials}) == 3
    bad_edges = 0
    for o in parts:
        assert o.type == 'MESH' and not o.modifiers
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bad_edges += sum(not e.is_manifold for e in bm.edges)
        bm.free()
    assert bad_edges == 0, 'Each editable frame, seal, pane and fixing is a closed solid'
    report = {
        'result': 'PASS', 'blender_version': bpy.app.version_string,
        'source_meshes': len(parts), 'panes': 16, 'asset_materials': 3,
        'nonmanifold_edges': bad_edges, 'units': 'metres',
        'origin': list(root.location), 'external_images': len(bpy.data.images),
        'source_edit_test': 'NOT RUN; native mesh components inspected only'
    }
    assert not any(i.filepath for i in bpy.data.images), 'No external image dependencies'
    (HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
