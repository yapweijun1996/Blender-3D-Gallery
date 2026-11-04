"""Export selected asset roots from the saved Blender project to a chosen folder.
Usage: blender --background scene.blend --python scripts/export-selected-assets.py -- /tmp/asset-exports
The source .blend is not saved or modified.
"""
import bpy
import sys
from pathlib import Path

if '--' not in sys.argv:
    raise SystemExit('Provide an output directory after --')
out = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
out.mkdir(parents=True, exist_ok=True)
roots = sorted((o for o in bpy.context.scene.objects if o.name.startswith('ASSET_')), key=lambda o: o.name)
if len(roots) != 21:
    raise RuntimeError(f'Expected 21 asset roots, got {len(roots)}')
def export(path, selected_roots, center=False):
    positions = {o.name: o.location.copy() for o in selected_roots}
    if center:
        for o in selected_roots: o.location = (0, 0, 0)
        bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    for root in selected_roots:
        root.select_set(True)
        for ob in root.children_recursive: ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True, export_apply=True)
    for root in selected_roots: root.location = positions[root.name]
    bpy.context.view_layer.update()
export(out / 'billiards-scene.glb', roots)
for root in roots:
    export(out / (root.name.removeprefix('ASSET_').lower() + '.glb'), [root], center=True)
print('EXPORTED', len(roots), 'individual files and one scene to', out)
