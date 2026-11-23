"""Build the 800 mm perimeter cassette from the owner's editable 1.2 m ceiling kit."""

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


HERE = Path(__file__).resolve().parent
SLUG = "mall-ceiling-infill-800"
ROOT = "ASSET_MallCeilingInfill800"
BASE = HERE.parent / "mall-ceiling-panel/sources/mall-ceiling-panel-module.blend"
STOCK_PANEL = 0.576
SHORT_PANEL = 0.176


def shorten_native_mesh(obj, depth):
    # Cut the two ends of the editable blank in local metres, before its bevel modifier.
    for vertex in obj.data.vertices:
        vertex.co.y = depth / 2 if vertex.co.y > 0 else -depth / 2
    obj.data.update()


def cut_panel(panel):
    shorten_native_mesh(panel, SHORT_PANEL)
    # The stock underside UV spans V=.50.. .75 in the long direction. Preserve its fibre density.
    uv = panel.data.uv_layers.active
    face = next(poly for poly in panel.data.polygons if poly.normal.z < -0.9)
    v0 = min(uv.data[i].uv.y for i in face.loop_indices)
    for index in face.loop_indices:
        coord = uv.data[index].uv
        coord.y = v0 + (coord.y - v0) * SHORT_PANEL / STOCK_PANEL


def build(source, reference):
    bpy.ops.wm.open_mainfile(filepath=str(reference.resolve()))
    root = bpy.data.objects["ASSET_MallCeilingPanel"]
    root.name = ROOT
    del root["repeat_pitch_m"]
    root["repeat_x_m"] = 1.2
    root["depth_m"] = 0.8
    root["field_depths_gltf_z_m"] = [0.6, 0.2]
    root["description"] = "Closed perimeter ceiling cassette; the 200 mm field faces glTF +Z."
    part = {obj.name: obj for obj in root.children}
    # Blender Y runs opposite glTF Z. Keep a stock 600 mm field against the original cassette.
    for number in [1, 2]:
        cut_panel(part[f"PANEL_{number}"])
    for number in [3, 4]:
        part[f"PANEL_{number}"].location.y = 0.1
    for i, y in enumerate([-0.394, -0.2, 0.394], 1):
        part[f"GRID_Main_{i}"].location.y = y
    for i in range(1, 4):
        shorten_native_mesh(part[f"GRID_Cross_{i}_1"], SHORT_PANEL)
        part[f"GRID_Cross_{i}_2"].location.y = 0.1
    for i, y in enumerate([-0.2, -0.2, 0.391, 0.391], 1):
        # The inner pair clamps to the full crossbar. The mating-edge plates stop 3 mm shy of the seam.
        for kind in ("Cleat", "Rod", "TopPlate"):
            part[f"HANGER_{kind}_{i}"].location.y = y
        # The untextured steel plate's bevel can interpolate unused UVs one float32 ULP differently per export.
        plate = part[f"HANGER_TopPlate_{i}"]
        for uv in list(plate.data.uv_layers):
            plate.data.uv_layers.remove(uv)
    for old, new, y in [("YP", "ZN", 0.4), ("YN", "ZP", -0.4)]:
        marker = part["CONNECTOR_" + old]
        marker.name = "CONNECTOR_" + new
        marker.location.y = y

    scene = bpy.context.scene
    scene.camera.location = (0.82, -1.32, -1.85)
    scene.camera.rotation_euler = (Vector((0, 0, 0.08)) - scene.camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera.data.ortho_scale = 1.64
    scene.render.resolution_x = 768
    scene.render.resolution_y = 576
    scene.cycles.samples = 32
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 94
    bpy.context.preferences.filepaths.save_version = 0
    # Retain the owner's exact pixels both packed and as an editable, relative texture.
    textures = source.parent.parent / "textures"
    textures.mkdir(exist_ok=True)
    for original in list(bpy.data.images):
        if original.packed_file:
            name = original.name
            texture = textures / name
            texture.write_bytes(original.packed_file.data)
            # Rebind the material to the identical pixels without inheriting a workstation-specific packed path.
            image = bpy.data.images.load(str(texture), check_existing=False)
            original.user_remap(image)
            bpy.data.images.remove(original)
            image.name = name
            image.pack()
            image.filepath = "//../textures/" + name
            for packed in image.packed_files:
                packed.filepath = image.filepath
    bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True, relative_remap=False)


def export_and_render(output, render):
    root = bpy.data.objects[ROOT]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [root, *root.children_recursive]:
        obj.select_set(True)
    destination = output / "exports" / (SLUG + ".glb")
    bpy.ops.export_scene.gltf(
        filepath=str(destination), export_format="GLB", use_selection=True, export_yup=True,
        export_apply=True, export_extras=True, export_animations=False, export_cameras=False, export_lights=False,
    )
    if render:
        for obj in [*root.children_recursive, root]:
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.ops.import_scene.gltf(filepath=str(destination))
        scene = bpy.context.scene
        scene.render.filepath = str(output / "previews" / (SLUG + ".jpg"))
        bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--rebuild", action="store_true")
    mode.add_argument("--export-source", action="store_true")
    parser.add_argument("--reference", type=Path, default=BASE)
    parser.add_argument("--source", type=Path, help="Edited .blend to reopen in export-source mode")
    parser.add_argument("--output", type=Path, default=HERE)
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    output = args.output.resolve()
    for folder in ("sources", "exports", "previews"):
        (output / folder).mkdir(parents=True, exist_ok=True)
    source = output / "sources" / (SLUG + ".blend")
    if args.export_source:
        bpy.ops.wm.open_mainfile(filepath=str((args.source or source).resolve()))
    else:
        if args.source:
            parser.error("--source is only used with --export-source")
        if source.exists() and not args.rebuild:
            parser.error("Use --export-source to export your saved edits or --rebuild to regenerate this source.")
        build(source, args.reference)
        # Reopen the saved meshes so the export never uses a stale evaluated bevel from the stock source.
        bpy.ops.wm.open_mainfile(filepath=str(source))
    export_and_render(output, not args.skip_render)


if __name__ == "__main__":
    main()
