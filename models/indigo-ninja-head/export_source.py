"""Export the visible authored portrait mesh groups from an edited Indigo .blend."""
from pathlib import Path
import sys
import bpy


def export_portrait(destination):
    groups = ("01 | face and scarf", "02 | indigo hair", "03 | embossed headband")
    parts = [obj for name in groups for obj in bpy.context.scene.collection.children[name].objects]
    if not parts or any(obj.type != 'MESH' for obj in parts):
        raise ValueError("Expected the three Indigo portrait mesh collections")
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.export_scene.gltf(filepath=str(destination), export_format='GLB', use_selection=True,
                              export_apply=True, export_extras=False, export_cameras=False,
                              export_lights=False, export_animations=False)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    if len(args) != 1:
        raise SystemExit("Supply the output GLB path after --")
    export_portrait(Path(args[0]).resolve())
