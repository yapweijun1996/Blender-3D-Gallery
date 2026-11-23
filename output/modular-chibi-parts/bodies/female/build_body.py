"""Preserve the Studio mesh and bind, recompress the three packed PBR maps."""
import json
import os

import bpy

import sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import BODY, HERE, MASTER, NEUTRAL, RUNTIME, STUDIO, reset
from glb_io import Glb

BODY_LIMIT = int(1.2 * 2**20)


def reencode_images(glb, max_total, sizes, qualities):
    replacements = {}
    records = []
    scratch = RUNTIME / f"textures-{os.getpid()}"
    scratch.mkdir(exist_ok=True)
    for number, image in enumerate(glb.doc.get("images", [])):
        view = image["bufferView"]
        suffix = ".png" if image["mimeType"] == "image/png" else ".jpg"
        original = scratch / ("source-" + str(number) + suffix)
        original.write_bytes(glb.payload(view))
        tex = bpy.data.images.load(str(original), check_existing=False)
        tex.colorspace_settings.name = "Non-Color"
        max_size = sizes[min(number, len(sizes) - 1)]
        quality = qualities[min(number, len(qualities) - 1)]
        scale = min(1., max_size / max(tex.size))
        if not max_total or scale < 1:
            dims = tuple(max(1, round(n * scale)) for n in tex.size)
            tex.scale(*dims)
        choice = scratch / ("texture-" + str(number) + ".jpg")
        scene = bpy.context.scene
        settings = scene.render.image_settings
        settings.file_format = "JPEG"
        settings.color_mode = "RGB"
        settings.quality = quality
        scene.view_settings.view_transform = "Raw"
        tex.save_render(str(choice), scene=scene)
        payload = choice.read_bytes()
        if suffix == ".jpg" and scale == 1 and len(glb.payload(view)) <= len(payload):
            payload = glb.payload(view)
        replacements[view] = payload
        image["mimeType"] = "image/jpeg"
        records.append({"name": image.get("name", ""), "size": list(tex.size), "bytes": len(payload),
                        "jpeg_quality": quality})
        bpy.data.images.remove(tex)
        original.unlink()
        choice.unlink()
    scratch.rmdir()
    glb.repack_views(replacements)
    return records


def hierarchy(arm):
    return {b.name: b.parent.name if b.parent else None for b in arm.data.bones}


def main():
    bpy.ops.wm.open_mainfile(filepath=str(NEUTRAL), load_ui=False)
    reference = bpy.context.scene.objects["Base_Body"]
    neutral_height = max((reference.matrix_world @ v.co).z for v in reference.data.vertices)
    neutral_bones = hierarchy(bpy.context.scene.objects["Armature"])

    bpy.ops.wm.open_mainfile(filepath=str(STUDIO / "body_female_v1.blend"), load_ui=False)
    arm = bpy.context.scene.objects["Female_Rig"]
    body = bpy.context.scene.objects["Body_Female"]
    reset(arm)
    arm.name = "Armature"
    body.name = "Base_Body"
    assert hierarchy(arm) == neutral_bones and len(neutral_bones) == 65
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)

    source = STUDIO / "body_female_v1.glb"
    for size, q in [(1024, 86), (896, 85), (768, 85), (640, 85)]:
        glb = Glb(source)
        for node in glb.doc["nodes"]:
            node["name"] = {"Female_Rig": "Armature", "Body_Female": "Base_Body"}.get(node["name"], node["name"])
        glb.doc["meshes"][0]["name"] = "Base_Body"
        records = reencode_images(glb, BODY_LIMIT, (size, size, size), (q, q, q))
        glb.write(BODY)
        if BODY.stat().st_size <= BODY_LIMIT:
            break
    assert BODY.stat().st_size <= BODY_LIMIT
    lib = Glb(STUDIO / "hand_gestures_female.glb")
    expected = {f"hand_{p}_{s}" for p in ("fist", "open_relaxed", "point", "thumbs_up", "peace",
                                           "ok", "grip_small", "pinch", "open_wide") for s in "LR"}
    assert {a["name"] for a in lib.doc["animations"]} == expected
    gestures = HERE / "hand_gestures_female.glb"
    gestures.write_bytes((STUDIO / gestures.name).read_bytes())

    bpy.context.scene.render.fps = 30
    bpy.context.scene.view_settings.view_transform = "AgX"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.preferences.filepaths.file_preview_type = "NONE"
    bpy.ops.wm.save_as_mainfile(filepath=str(MASTER))
    prim, = glb.doc["meshes"][0]["primitives"]
    pos = glb.accessor(prim["attributes"]["POSITION"])
    height = float(pos[:, 1].max() - pos[:, 1].min())
    result = dict(neutral_height_m=neutral_height, female_height_m=height,
                  floor_y_m=float(pos[:, 1].min()), height_scale=1.0, joints=len(neutral_bones),
                  body_bytes=BODY.stat().st_size, triangles=glb.doc["accessors"][prim["indices"]]["count"] // 3,
                  images=records, gestures=sorted(expected), gesture_copy_exact=True)
    (HERE / "body_assets.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result, flush=True)


if __name__ == "__main__":
    main()
