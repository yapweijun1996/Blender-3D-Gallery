"""Render a 2 x 2 assembly of the actual GLB without modifying the source."""
from pathlib import Path
import sys
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent


def main():
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources/skylight-roof-module.blend'))
    old = bpy.data.objects['ASSET_SkylightRoofModule']
    for o in list(old.children_recursive) + [old]:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(HERE / 'exports/optimized.glb'))
    root = bpy.data.objects['ASSET_SkylightRoofModule']
    originals = list(root.children_recursive)
    for x, y in ((-2, -2), (-2, 2), (2, -2)):
        clone = root.copy()
        bpy.context.scene.collection.objects.link(clone)
        clone.location = (x, y, 0)
        for o in originals:
            c = o.copy()
            bpy.context.scene.collection.objects.link(c)
            c.parent = clone
    root.location = (2, 2, 0)
    s = bpy.context.scene
    s.camera.location = (10, -13, 14)
    s.camera.rotation_euler = (Vector((0, 0, .10)) - s.camera.location).to_track_quat('-Z', 'Y').to_euler()
    s.camera.data.ortho_scale = 12.6
    s.render.filepath = str(HERE / 'reports/tiled-2x2.png')
    bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
