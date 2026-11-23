"""Identify the visible surfaces at the waist strip and cuff shadows."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_shorts import GLB, HERE, SHA, load_actions, set_pose, write_json
from render_shorts import setup


def sample(scene, api, depsgraph, origin, direction):
    hit, position, _, face, obj, _ = scene.ray_cast(depsgraph, origin, direction)
    if not hit:
        return {"surface": "background"}
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.data
    polygon = mesh.polygons[face]
    corners = np.asarray([list(evaluated.matrix_world @ mesh.vertices[i].co) for i in polygon.vertices])
    source_uv = mesh.uv_layers.active
    if len(corners) != 3 or not source_uv:
        return {"surface": obj.name}
    uv = np.asarray([list(source_uv.uv[i].vector) for i in polygon.loop_indices])
    bary = api["barycentric"](corners[None], np.asarray(position)[None])[0]
    lookup = bary @ uv
    material = evaluated.material_slots[polygon.material_index].material
    bsdf = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    image = bsdf.inputs["Base Color"].links[0].from_node.image
    width, height = image.size
    x, y = np.clip(lookup * [width, height], [0, 0], [width - 1, height - 1]).astype(int)
    offset = 4 * (y * width + x)
    return dict(surface=obj.name, material=material.name, base_texel_rgb=list(image.pixels[offset:offset + 3]),
                point_m=list(position))


def main():
    manifest = json.loads((HERE / "render_manifest.json").read_text())
    assert manifest["glb_sha256"] == SHA(GLB)
    scene, arm, _, garment, api = setup()
    actions = load_actions(scene)
    set_pose(scene, arm, None, 1)
    dg = bpy.context.evaluated_depsgraph_get()
    waist = [dict(z_m=z, **sample(scene, api, dg, Vector((0, 2, z)), Vector((0, -1, 0))))
             for z in (.405, .409, .412, .415, .418, .422)]
    frames = {}
    for clip, pixels in (("run", [(267, 542), (273, 540), (283, 546), (291, 538)]),
                         ("sit_idle", [(307, 541), (314, 543), (325, 546), (475, 527)])):
        capture = next(item for item in manifest["captures"] if item["clip"] == clip)
        set_pose(scene, arm, actions[clip], capture["frame"])
        dg = bpy.context.evaluated_depsgraph_get()
        target = Vector(capture["target_m"])
        towards_camera = Vector(capture["direction"]).normalized()
        rotation = (-towards_camera).to_track_quat("-Z", "Y")
        camera_position = target + 3 * towards_camera
        right, up = rotation @ Vector((1, 0, 0)), rotation @ Vector((0, 1, 0))
        unit = capture["width_m"] / 720
        rows = []
        for x, y in pixels:
            origin = camera_position + unit * ((x + .5 - 360) * right + (360 - y - .5) * up)
            result = sample(scene, api, dg, origin, -towards_camera)
            rows.append({"pixel": [x, y], **result})
        frames[clip] = {"frame": capture["frame"], "samples": rows}
    write_json("render_detail_check.json", dict(glb_sha256=SHA(GLB), garment_object=garment.name,
               back_waist=waist, cuff_shadows=frames))


if __name__ == "__main__":
    main()
