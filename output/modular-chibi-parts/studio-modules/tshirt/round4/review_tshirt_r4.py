"""Inspect the exact GLB and render its rest and two lowest-clearance poses."""
import hashlib
import json
from pathlib import Path
from collections import Counter
import runpy
import sys

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

OUT = Path(__file__).resolve().parent
FIT = runpy.run_path(str(OUT / "fit_tshirt_r4.py"))
SOURCE, EXPORT, PARTS, CLIPS = (FIT[k] for k in ("SOURCE", "EXPORT", "PARTS", "CLIPS"))
PRIOR, R2, SHARED, PREVIOUS = (FIT[k] for k in ("PRIOR", "R2", "SHARED", "PREVIOUS"))
write_json, digest = FIT["write_json"], FIT["digest"]


def view_bytes(document, binary, view_id):
    view = document["bufferViews"][view_id]
    start = view.get("byteOffset", 0)
    return binary[start:start + view["byteLength"]]


def image_fingerprints(document, binary):
    return sorted(hashlib.sha256(view_bytes(document, binary, img["bufferView"])).hexdigest()
                  for img in document["images"])


def bind_matrices(document, binary):
    joint_list = document["skins"][0]["joints"]
    joint_names = [document["nodes"][i]["name"] for i in joint_list]
    matrices = document["skins"][0]["inverseBindMatrices"]
    view = document["accessors"][matrices]["bufferView"]
    return joint_names, view_bytes(document, binary, view)


def accessor_array(doc, binary, index):
    accessor = doc["accessors"][index]
    view = doc["bufferViews"][accessor["bufferView"]]
    dtype = np.dtype({5121: "u1", 5123: "<u2", 5125: "<u4", 5126: "<f4"}[accessor["componentType"]])
    width = {"SCALAR": 1, "VEC2": 2}[accessor["type"]]
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    return np.ndarray((accessor["count"], width), dtype=dtype, buffer=binary, offset=offset,
                      strides=(view.get("byteStride", width * dtype.itemsize), dtype.itemsize))


def uv_chart(doc, binary):
    triangles = Counter()
    for primitive in doc["meshes"][0]["primitives"]:
        uv = accessor_array(doc, binary, primitive["attributes"]["TEXCOORD_0"])
        indices = accessor_array(doc, binary, primitive["indices"]).reshape(-1, 3)
        for corners in np.rint(uv[indices] * 1e6).astype(int):
            triangles[tuple(sorted(map(tuple, corners)))] += 1
    return triangles


def master_contacts(clips):
    """Check body-only distal-arm/trunk overlap with rest adjacency excluded."""
    scene, arm, body = PRIOR["open_master"]()
    FIT["load_clips"](scene)
    names = tuple(bone.name for bone in arm.data.bones)
    triangles = FIT["faces_of"](body.data)
    weights = PRIOR["read_weights"](body, names)
    zones = np.array([name.split(":")[-1] for name in names])[weights[triangles].sum(axis=1).argmax(axis=1)]
    trunk = np.isin(zones, ("Hips", "Spine", "Spine1", "Spine2", "LeftUpLeg", "RightUpLeg"))
    mask = [trunk, *(np.isin(zones, (side + "ForeArm", side + "Hand")) for side in ("Left", "Right"))]
    original = FIT["coords"](body.data)
    _, welded = np.unique(np.rint(original / 1e-6).astype(int), axis=0, return_inverse=True)
    report = {}
    for clip, frames in clips.items():
        report[clip] = []
        for frame in frames:
            FIT["set_pose"](scene, arm, clip, frame)
            posed, evaluated_faces = FIT["geometry"](body, bpy.context.evaluated_depsgraph_get())
            assert np.array_equal(triangles, evaluated_faces)
            world = posed.tolist()
            trees = [BVHTree.FromPolygons(world, triangles[m].tolist(), all_triangles=True) for m in mask]
            counts = {}
            for i, side in enumerate(("left", "right"), 1):
                trunk_faces, arm_faces = triangles[mask[0]], triangles[mask[i]]
                counts[side] = sum(not np.isin(welded[trunk_faces[j]], welded[arm_faces[k]]).any()
                                   for j, k in trees[0].overlap(trees[i]))
            report[clip].append({"frame": frame, "forearm_or_hand_vs_trunk_pairs": counts})
    return report


def frames():
    yield "rest", 1.
    for clip in CLIPS:
        yield from ((clip, frame) for frame in FIT["sample_frames"](bpy.data.actions[clip]))


def inspect():
    SHARED.update(times=frames, set_pose=FIT["set_pose"])
    PRIOR["verify"]()
    result = json.loads((OUT / "export_check.json").read_text())
    old, old_binary = PREVIOUS["glb_sections"](SOURCE)
    new, new_binary = PREVIOUS["glb_sections"](EXPORT)
    result["source_glb_sha256"] = digest(SOURCE)
    result["material_matches_round3"] = old["materials"] == new["materials"]
    result["embedded_images_match_round3"] = (
        image_fingerprints(old, old_binary) == image_fingerprints(new, new_binary))
    result["inverse_bind_matrices_match_round3"] = (
        bind_matrices(old, old_binary) == bind_matrices(new, new_binary))
    result["uv_triangle_charts_match_round3_at_1e_minus_6"] = (
        uv_chart(old, old_binary) == uv_chart(new, new_binary))
    blend = OUT / "tshirt_v4.blend"
    result["blend_sha256"] = digest(blend)
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False, use_scripts=False)
    arm, body, shirt = (bpy.context.scene.objects[n] for n in ("Armature", "Base_Body", "tshirt_v4"))
    assert len(arm.data.bones) == 65
    assert body.type == shirt.type == "MESH"
    assert len(FIT["faces_of"](shirt.data)) == result["triangles"]
    assert any(mod.type == "ARMATURE" and mod.object == arm for mod in shirt.modifiers)
    packed = {node.image for mat in shirt.data.materials for node in mat.node_tree.nodes
              if node.type == "TEX_IMAGE" and node.image and node.image.packed_file}
    assert len(packed) == 3
    result["blend_reopened"] = True
    write_json("export_check.json", result)
    report_path = OUT / "dense_check.json"
    report = json.loads(report_path.read_text())
    report.update(master_sha256=digest(FIT["MASTER"]), motion_sha256=digest(FIT["FIXED"]),
                  actions_sha256=digest(FIT["ACTIONS"]))
    key_frames = {"sit_down": {0.}, "sit_idle": {59.}, "stand_up": {30.}, "hold_item": {39.}}
    for clip, posed_frames in key_frames.items():
        posed_frames.add(report["clips"][clip]["minimum_vertex_frame"])
        key_frames[clip] = sorted(posed_frames)
    report["master_only_forearm_contacts"] = master_contacts(key_frames)
    write_json("dense_check.json", report)


def render():
    SHARED["RENDER_CLIPS"] = ()
    R2["render_evidence"].__globals__.update(OUT=OUT, GLB=EXPORT)
    R2["render_evidence"]()
    manifest = json.loads((OUT / "render_info.json").read_text())
    check = json.loads((OUT / "motion_check.json").read_text())
    assert manifest["glb_sha256"] == check["glb_sha256"] == digest(EXPORT)
    scene, arm, body, shirt = PRIOR["reimport"]()
    PRIOR["configure_render"](scene)
    scene.render.resolution_x, scene.render.resolution_y = 960, 880
    scene.cycles.samples = 20
    scene.camera = bpy.data.objects.new("Action QA", bpy.data.cameras.new("Action QA"))
    scene.collection.objects.link(scene.camera)
    camera = scene.camera
    camera.data.type = "ORTHO"
    actions_dir = PARTS / "actions-astra"
    chair, = (obj for obj in PRIOR["import_one"](actions_dir / "chair.glb") if obj.type == "MESH")
    cup, = (obj for obj in PRIOR["import_one"](actions_dir / "prop.glb") if obj.type == "MESH")
    mount = json.loads((actions_dir / "attachment.json").read_text())["blender_pose_bone_head_local"]
    x, y, z, w = mount["quaternion_xyzw"]
    attachment = Matrix.LocRotScale(Vector(mount["translation_m"]), Quaternion((w, x, y, z)),
                                    Vector((1, 1, 1)))
    for clip in ("sit_idle", "hold_item"):
        frame = check["clips"][clip]["combined"]["min_frame"]
        FIT["set_pose"](scene, arm, clip, frame)
        sitting = clip == "sit_idle"
        chair.hide_render, cup.hide_render = not sitting, sitting
        if not sitting:
            cup.matrix_world = arm.matrix_world @ arm.pose.bones["mixamorig:RightHand"].matrix @ attachment
        center, _ = FIT["geometry"](shirt, bpy.context.evaluated_depsgraph_get())
        focus = Vector((center.min(axis=0) + center.max(axis=0)) * .5)
        focus.z += .025
        direction = Vector((-.92 if sitting else -.70, -1, .14))
        camera.location = focus + 3 * direction.normalized()
        camera.rotation_euler = (focus - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.ortho_scale = .65 if sitting else .59
        path = OUT / (clip + ".png")
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        manifest["motion_frames"][clip] = frame
        manifest["png_sha256"][path.name] = digest(path)
    manifest.update(motion_sha256=digest(FIT["FIXED"]), actions_sha256=digest(FIT["ACTIONS"]))
    write_json("render_info.json", manifest)


if __name__ == "__main__":
    if "--renders" in sys.argv:
        render()
    else:
        inspect()
