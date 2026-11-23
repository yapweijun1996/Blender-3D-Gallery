"""Audit and render the reimported Round 5 GLB in guarded Blender."""
from collections import Counter
import json
from pathlib import Path
import runpy
import subprocess
import sys

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

OUT = Path(__file__).resolve().parent
R5 = runpy.run_path(str(OUT / "fit_tshirt_r5.py"))
FIT, R2, PRIOR, R3 = (R5[key] for key in ("FIT", "R2", "PRIOR", "R3"))
SOURCE, EXPORT, PARTS, ACTIONS = (R5[key] for key in ("SOURCE", "EXPORT", "PARTS", "ACTIONS"))
write_json, digest = R5["write_json"], R5["digest"]
SHARED = FIT["SHARED"]


def view_bytes(document, binary, index):
    view = document["bufferViews"][index]
    start = view.get("byteOffset", 0)
    return binary[start:start + view["byteLength"]]


def bind_fingerprint(document, binary):
    skin, = document["skins"]
    names = [document["nodes"][i]["name"] for i in skin["joints"]]
    accessor = document["accessors"][skin["inverseBindMatrices"]]
    return names, view_bytes(document, binary, accessor["bufferView"])


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


def images(document, binary):
    return [view_bytes(document, binary, image["bufferView"]) for image in document["images"]]


def frames():
    yield "rest", 1.
    for clip in FIT["CLIPS"]:
        yield from ((clip, frame) for frame in FIT["sample_frames"](bpy.data.actions[clip]))


def body_only():
    path = ACTIONS.with_name("body_selfcheck_after.json")
    audit = json.loads(path.read_text())
    assert audit["master_sha256"] == digest(FIT["MASTER"])
    assert audit["action_sha256"] == digest(ACTIONS)
    summary = {}
    for name, clip in audit["clips"].items():
        rows = clip["samples"]
        summary[name] = {
            **clip["summary"],
            "peak_target_pairs": max(row["target_pairs"] for row in rows),
            "peak_all_pairs": max(row["all_pairs"] for row in rows),
            "peak_knee_pairs": max(sum(count for zone, count in row["target_regions"].items()
                                       if "UpLeg" in zone) for row in rows),
        }
    write_json("body_only_pairs.json", {
        "master_sha256": audit["master_sha256"], "actions_sha256": audit["action_sha256"],
        "source_audit": str(path.relative_to(PARTS)), "source_audit_sha256": digest(path),
        "count_type": "Body self-intersection pairs excluding rest-adjacent triangles",
        "clips": summary,
    })


def inspect():
    SHARED.update(times=frames, set_pose=FIT["set_pose"])
    PRIOR["verify"]()
    result_path = OUT / "export_check.json"
    result = json.loads(result_path.read_text())
    old, old_binary = R3["glb_sections"](SOURCE)
    new, new_binary = R3["glb_sections"](EXPORT)
    result.update(
        source_glb_sha256=digest(SOURCE),
        material_matches_round3=old["materials"] == new["materials"],
        embedded_images_match_round3=images(old, old_binary) == images(new, new_binary),
        inverse_bind_matrices_match_round3=bind_fingerprint(old, old_binary) == bind_fingerprint(new, new_binary),
        uv_triangle_charts_match_round3_at_1e_minus_6=uv_chart(old, old_binary) == uv_chart(new, new_binary),
    )
    assert result["material_matches_round3"] and result["embedded_images_match_round3"]
    assert result["inverse_bind_matrices_match_round3"]
    blend = OUT / "tshirt_v5.blend"
    result["blend_sha256"] = digest(blend)
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False, use_scripts=False)
    arm, body, shirt = (bpy.context.scene.objects[n] for n in ("Armature", "Base_Body", "tshirt_v5"))
    assert len(arm.data.bones) == 65 and body.type == shirt.type == "MESH"
    assert len(FIT["faces_of"](shirt.data)) == result["triangles"]
    assert any(mod.type == "ARMATURE" and mod.object == arm for mod in shirt.modifiers)
    packed = {node.image for mat in shirt.data.materials for node in mat.node_tree.nodes
              if node.type == "TEX_IMAGE" and node.image and node.image.packed_file}
    assert len(packed) == 3
    result["blend_reopened"] = True
    write_json("export_check.json", result)
    report = json.loads((OUT / "dense_check.json").read_text())
    report.update(master_sha256=digest(FIT["MASTER"]), motion_sha256=digest(FIT["FIXED"]),
                  actions_sha256=digest(ACTIONS))
    write_json("dense_check.json", report)
    body_only()


def validate():
    module = OUT.parents[4] / "node_modules/gltf-validator"
    program = """
const fs = require("node:fs");
const crypto = require("node:crypto");
const validator = require(process.argv[1]);
const glb = fs.readFileSync("tshirt_v5.glb");
validator.validateBytes(glb, {uri: "tshirt_v5.glb"}).then(report => {
    report.glb_sha256 = crypto.createHash("sha256").update(glb).digest("hex");
    fs.writeFileSync("gltf_validation.json", JSON.stringify(report, null, 2) + "\\n");
    if (report.issues.numErrors || report.issues.numWarnings) process.exitCode = 1;
});
"""
    subprocess.run(["node", "-e", program, str(module)], cwd=OUT, check=True)


def render():
    SHARED["RENDER_CLIPS"] = ()
    R2["render_evidence"].__globals__.update(OUT=OUT, GLB=EXPORT)
    R2["render_evidence"]()
    manifest = json.loads((OUT / "render_info.json").read_text())
    check = json.loads((OUT / "motion_check.json").read_text())
    dense = json.loads((OUT / "dense_check.json").read_text())
    assert manifest["glb_sha256"] == check["glb_sha256"] == dense["glb_sha256"] == digest(EXPORT)
    scene, arm, body, shirt = PRIOR["reimport"]()
    PRIOR["configure_render"](scene)
    scene.render.resolution_x, scene.render.resolution_y = 960, 880
    scene.cycles.samples = 20
    scene.camera = bpy.data.objects.new("Action QA", bpy.data.cameras.new("Action QA"))
    scene.collection.objects.link(scene.camera)
    camera = scene.camera
    camera.data.type = "ORTHO"
    props = PARTS / "actions-astra"
    chair, = (obj for obj in PRIOR["import_one"](props / "chair.glb") if obj.type == "MESH")
    cup, = (obj for obj in PRIOR["import_one"](props / "prop.glb") if obj.type == "MESH")
    mount = json.loads((props / "attachment.json").read_text())["blender_pose_bone_head_local"]
    x, y, z, w = mount["quaternion_xyzw"]
    attachment = Matrix.LocRotScale(Vector(mount["translation_m"]), Quaternion((w, x, y, z)),
                                    Vector((1, 1, 1)))
    for clip in ("sit_idle", "hold_item"):
        metrics = check["clips"][clip]["combined"]
        frame = metrics["min_frame"]
        clearance = metrics["min_signed_m"]
        source = "vertex"
        for zone, sample in dense["residuals"][clip].get("triangle witness", {}).items():
            if sample["min_signed_dist"] < clearance:
                frame, clearance = sample["frame"], sample["min_signed_dist"]
                source = f"triangle witness ({zone})"
        FIT["set_pose"](scene, arm, clip, frame)
        sitting = clip == "sit_idle"
        chair.hide_render, cup.hide_render = not sitting, sitting
        if not sitting:
            cup.matrix_world = arm.matrix_world @ arm.pose.bones["mixamorig:RightHand"].matrix @ attachment
        points, _ = FIT["geometry"](shirt, bpy.context.evaluated_depsgraph_get())
        focus = Vector((points.min(axis=0) + points.max(axis=0)) * .5)
        focus.z += .025
        direction = Vector((-.92 if sitting else -.70, -1, .14))
        camera.location = focus + 3 * direction.normalized()
        camera.rotation_euler = (focus - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.ortho_scale = .65 if sitting else .59
        path = OUT / (clip + ".png")
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        manifest["motion_frames"][clip] = {"frame": frame, "min_signed_m": clearance, "witness": source}
        manifest["png_sha256"][path.name] = digest(path)
    manifest.update(motion_sha256=digest(FIT["FIXED"]), actions_sha256=digest(ACTIONS))
    write_json("render_info.json", manifest)


if __name__ == "__main__":
    if "--renders" in sys.argv:
        render()
    elif "--validator" in sys.argv:
        validate()
    else:
        inspect()
