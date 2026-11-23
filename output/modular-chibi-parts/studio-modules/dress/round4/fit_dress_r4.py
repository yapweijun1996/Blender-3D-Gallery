"""Refit the shipped Round 3 dress on the master rig using Blender 5.1."""
from contextlib import redirect_stdout
from io import StringIO
import json
import math
import os
from pathlib import Path
import runpy
import sys

sys.dont_write_bytecode = True

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
R3 = runpy.run_path(str(HERE.parent / "round3/fit_dress_r3.py"))
R2, R1 = R3["R2"], R3["R1"]
MASTER, MOTION = R3["MASTER"], R3["MOTION"]
BANK = MASTER.parent.parent / "actions-astra/actions.glb"
ACT_CHECK = MOTION.parent / "act"
LEGACY = R3["CLIPS"]
ADDED = ("sit_down", "sit_idle", "stand_up", "hold_item")
SEED = HERE.parent / "round3/dress_v3.glb"
GLB, BLEND = HERE / "dress_v4.glb", HERE / "dress_v4.blend"
FLOOR, CAP = R3["FLOOR"], R3["CAP"]
mesh_points, triangulation = R3["mesh_points"], R3["triangulation"]
section, clearance = R3["section"], R3["clearance"]
clip_frames, sha = R3["clip_frames"], R2["sha"]


def action_bank(scene, arm, body, garment):
    actions = {"rest": None}
    for obj in scene.objects:
        if obj.type in {"MESH", "ARMATURE"} and obj not in (arm, body, garment):
            obj.hide_viewport = obj.hide_render = True
    for path, clips in ((MOTION, LEGACY), (BANK, ADDED)):
        if path == BANK:
            scene.render.fps = 30
            scene.render.fps_base = 1
        old_actions, old_objects = set(bpy.data.actions), set(scene.objects)
        bpy.ops.import_scene.gltf(filepath=str(path))
        imported = set(bpy.data.actions) - old_actions
        for name in clips:
            actions[name], = [act for act in imported
                              if act.name == name or act.name.startswith(name + ".")]
        for obj in set(scene.objects) - old_objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    return actions


def pose(scene, arm, action, frame):
    animation = arm.animation_data_create()
    if animation.action != action:
        animation.use_nla = False
        animation.action = None
        for bone in arm.pose.bones:
            bone.matrix_basis.identity()
        if action is not None:
            animation.action = action
            animation.action_slot = action.slots[0]
    scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.context.view_layer.update()


def import_scene(path, weld=False):
    scene, arm, body = R1["open_master"]()
    garment = R1["import_mesh"](path)
    if weld:
        mesh = bmesh.new()
        mesh.from_mesh(garment.data)
        bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=1e-7)
        mesh.to_mesh(garment.data)
        mesh.free()
        if garment.data.has_custom_normals:
            bpy.context.view_layer.objects.active = garment
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
        garment.data.update()
    R1["bind"](garment, arm)
    return scene, arm, body, garment, action_bank(scene, arm, body, garment)


def cache(scene, arm, body, names, actions):
    assert np.allclose(arm.matrix_world, np.eye(4), atol=1e-6)
    bones = [arm.pose.bones[name] for name in names]
    modes = tuple(bone.rotation_mode for bone in bones)
    inverse = [bone.bone.matrix_local.inverted() for bone in bones]
    samples, matrices = [], []
    faces = None
    for name, action in actions.items():
        for frame in clip_frames(action) if action else [1.]:
            pose(scene, arm, action, frame)
            xyz, polys = R1["posed_mesh"](body, bpy.context.evaluated_depsgraph_get())
            if faces is None:
                faces = np.asarray(polys, dtype=np.int32)
            samples.append((name, frame, BVHTree.FromPolygons(xyz, polys, all_triangles=True),
                            np.asarray(xyz, dtype=np.float32), faces))
            matrices.append(np.asarray([bone.matrix @ bind for bone, bind in zip(bones, inverse)],
                                       dtype=np.float32)[:, :3, :])
        print("CACHED", name, len(samples), flush=True)
    assert modes == tuple(bone.rotation_mode for bone in bones)
    return samples, np.asarray(matrices)


def setup_material(garment):
    # Use the authored material so Blender exports the original packed textures
    # and specular parameters after the GLB geometry round-trip.
    with bpy.data.libraries.load(str(SEED.with_suffix(".blend"))) as (_, target):
        target.objects = ["Dress"]
    ref, = target.objects
    authored = ref.data.materials[0]
    imported = garment.data.materials[0]
    garment.data.materials[0] = authored
    bpy.data.objects.remove(ref, do_unlink=True)
    if not imported.users:
        bpy.data.materials.remove(imported)
    authored.name = R2["glb_metadata"](SEED)[0]["materials"][0]["name"]


def export(scene, arm, body, garment, names, points, weights, draft=False, draft_name="candidate.glb"):
    pose(scene, arm, None, 1.)
    R1["mesh_coords"](garment, points)
    R1["write_weights"](garment, names, weights)
    garment.name = garment.data.name = "Dress"
    assert len(names) == 65 and len(triangulation(garment)) <= 8000
    bpy.ops.object.select_all(action="DESELECT")
    garment.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = garment
    garment.parent = None
    path = HERE / ".work" / draft_name if draft else GLB
    path.parent.mkdir(exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(path), use_selection=True,
                             export_animations=False, export_def_bones=False,
                             export_all_influences=False, export_tangents=True)
    garment.parent = arm
    if not draft:
        body.hide_render = False
        body.hide_set(False)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))


def run_checker(path, triangles, legacy, garment):
    """Retain the supplied numerical measure functions and extend frame sampling."""
    sys.path.insert(0, str(ACT_CHECK))
    try:
        source = path.read_text()
        namespace = {"__file__": str(path), "__name__": "__main__",
                     "clip_frames": clip_frames}
        argv = [str(path), "--", str(MASTER), str(MOTION), str(garment), str(HERE)]
        if legacy:
            source = source.split("sc.render.engine=", 1)[0]
            start = source.index("    f0,f1=a.frame_range")
            end = source.index("for k,v in res.items():", start)
            source = source[:start] + """    frames[name]=[]
    for fr in clip_frames(a):
        sc.frame_set(math.floor(fr),subframe=fr%1)
        frames[name].append([fr,*measure()])
    res[name]=(max(row[1] for row in frames[name]),min(row[2] for row in frames[name]))
""" + source[end:]
            source = source.replace("if not a:continue", "assert a is not None, name")
            source = source.replace("res['rest']=measure()",
                                    "res['rest']=measure()\nframes['rest']=[[1.,*res['rest']]]")
            source = source.replace(
                "sc.frame_set(1);arm.animation_data.action=None;bpy.context.view_layer.update()",
                "arm.animation_data.action=None\narm.animation_data.use_nla=False\n"
                "for bone in arm.pose.bones: bone.matrix_basis.identity()\n"
                "sc.frame_set(1);bpy.context.view_layer.update()")
            namespace["frames"] = {}
        else:
            argv.append(str(BANK))
            source = source.split("    # Retain the original checker previews", 1)[0]
            source = source.replace("            first,last=map(round,act.frame_range)\n", "")
            source = source.replace("for f in range(first,last+1):\n                scene.frame_set(f)",
                                    "for f in clip_frames(act):\n"
                                    "                scene.frame_set(math.floor(f), subframe=f%1)")
            start = source.index("    (out/(stem+'.json')).write_text")
            source = source[:start] + "    return res,detail\n"
            source += f"\nres, detail = garment_check(triangles={triangles!r})\n"
        stdout = StringIO()
        previous = sys.argv
        try:
            sys.argv = argv
            with redirect_stdout(stdout):
                exec(compile(source, str(path), "exec"), namespace)
        finally:
            sys.argv = previous
    finally:
        sys.path.pop(0)
    if legacy:
        return namespace["frames"]
    return {name: [[row["frame"], row["count"], row["min_signed_m"]]
                   for row in namespace["detail"][name]] for name in ADDED}


def check(garment=GLB, destination=HERE, variants=(False, True)):
    checker_dir = Path(os.environ.get("DRESS_LEGACY_CHECKERS",
        "/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/"
        "26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular"))
    destination.mkdir(exist_ok=True)
    for triangles in variants:
        legacy_name = "motion_check_tri.py" if triangles else "motion_check_dense.py"
        legacy_path = checker_dir / legacy_name
        added_path = ACT_CHECK / "motion_check.py"
        stem = "motion_check_tri" if triangles else "motion_check"
        label = "triangle_overlap_pairs" if triangles else "vertices_inside"
        legacy = run_checker(legacy_path, triangles, True, garment)
        added = run_checker(added_path, triangles, False, garment)
        frames = {**legacy, **added}
        assert tuple(frames) == ("rest", *LEGACY, *ADDED)
        result = {}
        for name, rows in frames.items():
            frame, _, depth = min(rows, key=lambda row: row[2])
            peak = max(row[1] for row in rows)
            result[name] = {label: peak, "min_signed_m": depth,
                            "min_frame": frame, "samples": len(rows),
                            "failing_samples": sum(row[1] > 0 or row[2] < FLOOR for row in rows)}
        report = {
            "glb_sha256": sha(garment), "master_sha256": sha(MASTER),
            "motion_sha256": sha(MOTION), "actions_sha256": sha(BANK),
            "legacy_checker_sha256": sha(legacy_path), "added_checker_sha256": sha(added_path),
            "blender": bpy.app.version_string, "frame_columns": ["frame", label, "minimum_signed_m"],
            "results": result, "frames": frames,
        }
        report_text = "\n".join(
            f"RESULT {name:10} {label} {r[label]:4d}  min_signed_m {r['min_signed_m']:+.9f}"
            f"  frame {r['min_frame']:5g}  samples {r['samples']}"
            for name, r in result.items()) + "\n"
        (destination / f"{stem}.txt").write_text(report_text)
        (destination / f"{stem}.json").write_text(json.dumps(report, indent=2) + "\n")
        print(report_text, end="", flush=True)


def verify():
    scene, arm, body, garment, _ = import_scene(GLB)
    names = tuple(bone.name for bone in arm.data.bones)
    points, triangles = mesh_points(garment.data), triangulation(garment)
    weights = R3["read_weights"](garment, names)
    xyz, faces = R1["posed_mesh"](body, bpy.context.evaluated_depsgraph_get())
    tree = BVHTree.FromPolygons(xyz, faces, all_triangles=True)
    rest = clearance(tree, points)[0]
    probes = R2["rest_sample_positions"](points, triangles).reshape(-1, 3)
    probe_rest = clearance(tree, probes)[0]
    doc, raw = R2["glb_metadata"](GLB)
    old_doc, old_raw = R2["glb_metadata"](SEED)
    textures = R2["embedded_textures"](doc, raw)
    assert len(doc["skins"]) == 1 and len(doc["skins"][0]["joints"]) == len(names) == 65
    assert len(doc["meshes"]) == 1 and not doc.get("animations") and not doc.get("cameras")
    assert len(triangles) <= 8000 and all(max(t["size"]) <= 1024 for t in textures)
    assert int((weights > 0).sum(axis=1).max()) <= 4
    loops, non_manifold = R2["boundary_loops"](garment)
    audit = {
        "glb_sha256": sha(GLB), "blend_sha256": sha(BLEND), "seed_sha256": sha(SEED),
        "bytes": GLB.stat().st_size, "blend_bytes": BLEND.stat().st_size,
        "triangles": len(triangles), "vertices": len(points), "joints": len(names),
        "influences_max": int((weights > 0).sum(axis=1).max()),
        "max_weight_sum_error": float(np.abs(weights.sum(axis=1)-1).max()),
        "mesh_count": len(doc["meshes"]), "animation_count": len(doc.get("animations", [])),
        "material_equal": doc["materials"] == old_doc["materials"],
        "texture_bytes_equal": textures == R2["embedded_textures"](old_doc, old_raw),
        "textures": textures, "uv_audit": R3["uv_audit"](doc, raw, old_doc, old_raw),
        "boundary_loops": loops, "non_manifold_edges": non_manifold,
        "rest_clearance": R1["stats"](rest), "rest_probes": R1["stats"](probe_rest),
        "rest_verts_over_30mm": int((rest > CAP).sum()),
        "rest_probes_over_30mm": int((probe_rest > CAP).sum()),
    }
    audit["uv_audit"]["round3_unique"] = audit["uv_audit"].pop("round2_unique")
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False, use_scripts=False)
    saved = bpy.context.scene.objects["Dress"]
    saved_weights = R3["read_weights"](saved, names)
    assert saved.parent.type == "ARMATURE" and len(saved.parent.data.bones) == 65
    assert len(triangulation(saved)) == len(triangles)
    assert len(saved.data.uv_layers) == 1
    nodes = saved.data.materials[0].node_tree.nodes
    saved_images = {n.image for n in nodes if n.type == "TEX_IMAGE" and n.image}
    audit["blend_readback"] = {"garment_triangles": len(triangulation(saved)),
        "joints": len(saved.parent.data.bones), "max_influences": int((saved_weights>0).sum(axis=1).max()),
        "texture_count": len(saved_images), "textures_packed": all(img.packed_file for img in saved_images)}
    (HERE / "export_check.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2), flush=True)


def render():
    scene, arm, body, garment, actions = import_scene(GLB)
    report = json.loads((HERE / "motion_check.json").read_text())
    assert report["glb_sha256"] == sha(GLB)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "AgX"
    scene.world = bpy.data.worlds.new("Dress QA studio")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (.31, .35, .43, 1)
    background.inputs[1].default_value = .50
    for obj in list(scene.objects):
        if obj.type == "LIGHT":
            bpy.data.objects.remove(obj, do_unlink=True)
    light = R1["light"]
    light(scene, "Key", (-1, -2, 2.4), 200, 1.25, (0, 0, .5))
    light(scene, "Fill", (1.1, -1.5, .6), 85, 1.3, (0, 0, .5))
    light(scene, "Rim", (.4, 1.2, 1.5), 140, 1.1, (0, 0, .5))
    camera = bpy.data.cameras.new("Dress QA")
    camera.type = "ORTHO"
    view = bpy.data.objects.new("Dress QA", camera)
    scene.collection.objects.link(view)
    scene.camera = view

    def capture(path, direction, target, scale):
        target = Vector(target)
        view.location = target + Vector(direction).normalized() * 2.8
        view.rotation_euler = (target-view.location).to_track_quat("-Z", "Y").to_euler()
        camera.ortho_scale = scale
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    views = (("front", (0,-1,0)), ("back", (0,1,0)), ("left", (1,0,0)),
             ("right", (-1,0,0)), ("three-quarter", (.65,-1,.16)),
             ("dress only", (.37,-1,.30)))
    pose(scene, arm, None, 1.)
    tile = 500
    scene.render.resolution_x = scene.render.resolution_y = tile
    sheet = np.zeros((2*tile, 3*tile, 4), dtype=np.float32)
    temporary = HERE / ".rest_tile.png"
    try:
        for index, (name, direction) in enumerate(views):
            body.hide_render = name == "dress only"
            capture(temporary, direction, (0,-.011,.426), .59)
            image = bpy.data.images.load(str(temporary), check_existing=False)
            pixels = np.empty(tile*tile*4, dtype=np.float32)
            image.pixels.foreach_get(pixels)
            row, col = 1-index//3, index%3
            sheet[row*tile:(row+1)*tile, col*tile:(col+1)*tile] = pixels.reshape(tile,tile,4)
            bpy.data.images.remove(image)
    finally:
        temporary.unlink(missing_ok=True)
    image = bpy.data.images.new("Six dress views", width=3*tile, height=2*tile, alpha=True)
    image.pixels.foreach_set(sheet.ravel())
    image.filepath_raw = str(HERE / "six_view.png")
    image.file_format = "PNG"
    image.save()

    body.hide_render = False
    scene.render.resolution_x = scene.render.resolution_y = 720
    render_frames = {}
    for clip, direction in (("sit_idle", (.77,-1,.22)), ("hold_item", (-.62,-1,.13))):
        frame = report["results"][clip]["min_frame"]
        pose(scene, arm, actions[clip], frame)
        graph = bpy.context.evaluated_depsgraph_get()
        xyz, faces = R1["posed_mesh"](body, graph)
        garment_xyz, _ = R1["posed_mesh"](garment, graph)
        tree = BVHTree.FromPolygons(xyz, faces, all_triangles=True)
        signed, _, _ = clearance(tree, np.asarray(garment_xyz))
        vertex = int(signed.argmin())
        rest_points = mesh_points(garment.data)
        side = rest_points[vertex,0]
        if abs(side) > .015:
            direction = (math.copysign(direction[0], side), direction[1], direction[2])
        rotation = Vector(direction).to_track_quat("Z", "Y")
        axes = np.asarray(rotation.to_matrix())
        projected = np.asarray(xyz + garment_xyz) @ axes
        low, high = projected.min(axis=0), projected.max(axis=0)
        capture(HERE / f"{clip}.png", direction, axes @ ((low+high)*.5),
                max((high-low)[:2]) * 1.10)
        render_frames[clip] = {"frame": frame, "zone": str(section(rest_points)[vertex]),
                               "min_signed_m": float(signed[vertex]),
                               "camera_direction": direction}
    manifest = {
        "glb_sha256": sha(GLB), "renderer": "Cycles CPU", "samples": scene.cycles.samples,
        "six_view_order": [name for name, _ in views], "action_frames": render_frames,
        "sha256": {name: sha(HERE / name) for name in ("six_view.png", "sit_idle.png", "hold_item.png")},
    }
    (HERE / "renders.json").write_text(json.dumps(manifest, indent=2) + "\n")


def scan(points, weights, triangles, samples, matrices):
    coeff, cols = R2["sparse_weights"](weights)
    posed, skin = R2["skin_poses"](points, coeff, cols, matrices)
    signed = np.empty(posed.shape[:2], dtype=np.float32)
    normals = np.empty_like(posed)
    contacts = {}
    hits = np.zeros(len(triangles), dtype=np.int32)
    faces = triangles.tolist()
    report = {}
    zone = section(points)
    for i, (clip, frame, tree, *_) in enumerate(samples):
        signed[i], normals[i], _ = clearance(tree, posed[i])
        pairs = np.asarray(tree.overlap(BVHTree.FromPolygons(
            posed[i].tolist(), faces, all_triangles=True)), dtype=np.int32).reshape(-1, 2)
        if len(pairs):
            contacts[i] = pairs
            np.add.at(hits, pairs[:, 1], 1)
        entry = report.setdefault(clip, dict(samples=0, inside=0, pairs=0, total_pairs=0, min_m=1.))
        entry["samples"] += 1
        entry["inside"] = max(entry["inside"], int((signed[i] < 0).sum()))
        entry["pairs"] = max(entry["pairs"], len(pairs))
        entry["total_pairs"] += len(pairs)
        weakest = int(signed[i].argmin())
        if signed[i, weakest] < entry["min_m"]:
            entry.update(min_m=float(signed[i, weakest]), min_frame=frame, zone=str(zone[weakest]),
                         xyz=np.round(points[weakest]*1000, 2).tolist())
    return report, posed, skin, signed, normals, contacts, hits


def body_weight_targets(points, body, names, rest):
    tree, body_points, faces = rest[2:]
    body_weights = R3["read_weights"](body, names, validate=False)
    hits = [tree.find_nearest(point) for point in points.tolist()]
    loc = np.asarray([tuple(hit[0]) for hit in hits])
    near = faces[[hit[2] for hit in hits]]
    bary = R1["barycentric"](body_points[near], loc).clip(0, 1)
    anatomy = np.einsum("vk,vkn->vn", bary, body_weights[near])
    anatomy /= anatomy.sum(axis=1, keepdims=True).clip(1e-8)
    return anatomy


def select_support(weights, anatomy, smoothed, bones, points):
    """Include anatomical alternatives when the prior blend left empty slots."""
    preference = weights + .18 * anatomy + .09 * smoothed
    x, _, z = points.T
    side = x > 0
    for name, positive in (("Left", True), ("Right", False)):
        nearby = (side == positive) | (np.abs(x) < .035)
        preference[:, bones[name + "UpLeg"]] += .06 * (z < .42) * nearby
        preference[:, bones[name + "Leg"]] += .04 * (z < .305) * nearby
        preference[:, bones[name + "Arm"]] += .07 * (z > .445) * (np.abs(x) > .06) * (side == positive)
        preference[:, bones[name + "Shoulder"]] += .05 * (z > .49) * (np.abs(x) > .05) * (side == positive)
    preference[:, bones["Hips"]] += .05 * (z < .43)
    return R2["sparse_weights"](preference)[1]


def trial_fields(points, weights, samples, matrices, target, selected):
    """Measure independent vertex proposals on the chosen poses."""
    coeff, cols = R2["sparse_weights"](weights)
    posed, _ = R2["skin_poses"](points, coeff, cols, matrices[selected])
    maximum = np.zeros(len(points), dtype=np.float32)
    aggregate = maximum.copy()
    for i, f in enumerate(selected):
        signed = clearance(samples[f][2], posed[i])[0]
        gap = np.maximum(target - signed, 0.) * 1000
        maximum = np.maximum(maximum, gap)
        aggregate += np.square(gap)
    return np.square(maximum) + aggregate / len(selected) * 12.


def local_proposal(points, original, weights, anatomy, bones, links, samples, matrices,
                   triangles, skin, signed, normals, hits, step, seed_weights):
    """Transport clearance planes into rest space, then score the actual sweeps."""
    target = .002 if step < 5 else .0011
    gap = np.maximum(target - signed, 0)
    peak = gap.max(axis=0)
    active = peak > .00005
    active[triangles[hits>0].ravel()] = True
    ids = np.flatnonzero(active)
    if not len(ids):
        return points, weights
    avg = R2["average"]
    smooth_weights = avg(weights, links)
    columns = select_support(weights[ids], anatomy[ids], smooth_weights[ids], bones, points[ids])
    coeff = np.take_along_axis(weights[ids], columns, axis=1)
    coeff /= coeff.sum(axis=1, keepdims=True)

    # Evenly cover motion and also include the closest pose in each time bin.
    blocks = np.array_split(np.arange(1,len(samples)), 72)
    vertex = np.arange(len(ids))
    rows = np.stack([block[np.argmin(signed[block[:,None], ids], axis=0)] for block in blocks])
    rows = np.vstack((np.zeros(len(ids), dtype=np.int32), rows))
    frames = np.unique(np.r_[0, rows.ravel(), np.arange(0,len(samples),8)])
    gz = normals[rows, ids]
    local = np.einsum("fvi,fvij->fvj", gz, skin[rows, ids, :, :3])
    mats = matrices[rows[...,None], columns]
    positions = np.einsum("fvbij,vj->fvbi", mats[...,:3], points[ids]) + mats[...,3]
    shift = np.einsum("fvi,fvbi->fvb", gz, positions)
    shift -= shift.mean(axis=2, keepdims=True)
    shift *= 6.
    jacobian = np.concatenate((local, shift), axis=-1)
    rhs = target - signed[rows, ids]
    rhs[0] = .00065 - signed[0, ids]
    norm = np.square(jacobian).sum(axis=-1).clip(.10)
    move = np.zeros((len(ids), 7), dtype=np.float32)
    for _ in range(53):
        deficit = (rhs - np.einsum("fvi,vi->fv", jacobian, move)) / np.sqrt(norm)
        row = np.argmax(deficit, axis=0)
        response = (deficit[row, vertex].clip(0)/np.sqrt(norm[row, vertex]))[:,None]
        move += jacobian[row, vertex] * response * .66
        move[:,:3] = R2["bound_delta"](move[:,:3], .012 if step < 4 else .007)
        proposal = R2["simplex"](coeff + move[:,3:] * 6.)
        move[:,3:] = (proposal-coeff)/6.
    baked = np.zeros_like(points)
    worst = np.argmin(signed[:,ids],axis=0)
    rays = np.einsum("vi,vij->vj", normals[worst, ids], skin[worst, ids, :, :3])
    rays /= np.linalg.norm(rays,axis=1,keepdims=True).clip(1e-8)
    requirement = (R3["MARGIN"] - signed[worst, ids]).clip(0, CAP)
    baked[ids] = rays * requirement[:,None]
    for _ in range(3):
        baked += .27 * (avg(baked, links)-baked)
        baked[ids] += (requirement - np.einsum("vi,vi->v", baked[ids], rays)).clip(0)[:,None] * rays

    # Backtrack against actual surface distances. Near an arm/torso or thigh
    # fold the two closest surfaces can exchange as the garment moves.
    best_points, best_weights = points[ids].copy(), weights[ids].copy()
    best = trial_fields(best_points,best_weights,samples,matrices,target,frames)
    rest = samples[0][2]
    moved_weights = R2["full_weights"](proposal,columns,weights.shape[1])
    smooth_move = np.zeros_like(points)
    smooth_move[ids] = move[:,:3]
    smooth_move = .74*smooth_move + .26*avg(smooth_move,links)
    trials = [(fraction*smooth_move[ids], (1-fraction)*weights[ids]+fraction*moved_weights)
              for fraction in (.3,.62,1.)]
    trials.extend((baked[ids]*f,weights[ids]) for f in (.26,.55,.95))
    sources = (anatomy[ids], smooth_weights[ids], seed_weights[ids])
    trials.extend((d, weights[ids]*(1-a)+w*a)
                  for w in sources for a in (.25,.65) for d in (smooth_move[ids]*.6,))
    if step < 4:
        # Follow the closest body trajectory where round 3's leg and sleeve
        # blends pull in a different direction from the new pose.
        trials.extend((baked[ids]*.50, anatomy[ids]*a+weights[ids]*(1-a)) for a in (.5,1.))
    for d, trial_weights in trials:
        trial_points = R2["project_rest"](points[ids]+d, original[ids], rest)
        trial_weights = R2["limit_weights"](trial_weights)
        cost = trial_fields(trial_points,trial_weights,samples,matrices,target,frames)
        cost += .012*np.square((trial_points-points[ids])*1000).sum(axis=1)
        cost += .13*np.square((trial_weights-weights[ids])*10).sum(axis=1)
        better = cost < best - 1e-7
        best[better] = cost[better]
        best_points[better] = trial_points[better]
        best_weights[better] = trial_weights[better]
    next_points = points.copy()
    next_points[ids] = best_points
    points = R2["rest_guard"](next_points,points,original,triangles,rest)
    weights[ids] = best_weights
    return points, weights


def guarded(iterations, source=SEED):
    scene, arm, body, garment, actions = import_scene(source, weld=True)
    setup_material(garment)
    names = tuple(bone.name for bone in arm.data.bones)
    bones = {name.split(":")[-1]: i for i,name in enumerate(names)}
    points = mesh_points(garment.data)
    original = points.copy()
    triangles = triangulation(garment)
    links = R2["neighbors"](garment.data)
    weights = R3["read_weights"](garment, names)
    seed_weights = weights.copy()
    samples, matrices = cache(scene,arm,body,names,actions)
    anatomy = body_weight_targets(points,body,names,samples[0])
    best = float("inf")
    work = HERE / ".work"
    history = []
    for i in range(iterations+1):
        report, posed, skin, signed, normals, contacts, hits = scan(points,weights,triangles,samples,matrices)
        R3["display"](f"GUARDED {i}",report)
        history.append(report)
        (work/"guarded.json").write_text(json.dumps(history,indent=2)+"\n")
        value = R3["score"](report)
        passed = all(row["pairs"] == row["inside"] == 0 and row["min_m"] >= FLOOR
                     for row in report.values())
        if value < best or passed:
            best = value
            export(scene,arm,body,garment,names,points,weights,draft=True,draft_name="guarded.glb")
            np.savez(work/"guarded_state.npz",points=points,weights=weights,signed=signed,hits=hits,
                     faces=triangles,origin=original,names=names)
        if passed or i == iterations:
            break
        points,weights = local_proposal(points,original,weights,anatomy,bones,links,samples,matrices,
                                        triangles,skin,signed,normals,hits,i,seed_weights)


def fit_score(report):
    return sum(row["total_pairs"] * .002
               + row["inside"]*.5 + max(0.,FLOOR-row["min_m"])**2*2e6
               for row in report.values())


def trim_rest_probes(points, original, triangles, tree):
    bary = R2["REST_BARYCENTRICS"]
    for _ in range(7):
        locations = np.einsum("qj,fjk->fqk", bary, points[triangles])
        signed, normals, _ = clearance(tree, locations.reshape(-1,3))
        faces, probes = np.where(signed.reshape(-1,len(bary)) > CAP-.00005)
        if not len(faces):
            break
        flat = faces*len(bary)+probes
        pull = -normals[flat]*(signed[flat]-CAP+.0001)[:,None]
        ids = triangles[faces].ravel()
        w = bary[probes].ravel()
        correction = np.zeros_like(points)
        np.add.at(correction,ids,(pull[:,None]*bary[probes,:,None]).reshape(-1,3))
        correction /= np.bincount(ids,weights=w,minlength=len(points)).clip(1)[:,None]
        new = R2["project_rest"](points+correction,original,tree)
        points = R2["rest_guard"](new,points,original,triangles,tree)
    return points


def finalize(source):
    scene,arm,body,garment,_ = import_scene(source,weld=True)
    setup_material(garment)
    names = tuple(bone.name for bone in arm.data.bones)
    points = mesh_points(garment.data)
    pose(scene, arm, None, 1.)
    xyz, faces = R1["posed_mesh"](body, bpy.context.evaluated_depsgraph_get())
    tree = BVHTree.FromPolygons(xyz, faces, all_triangles=True)
    points = trim_rest_probes(points, points.copy(), triangulation(garment), tree)
    export(scene,arm,body,garment,names,points,R3["read_weights"](garment,names))


def patch_loss(points, weights, local_ids, in_patch, patch_faces, posed, samples, matrices,
               frames, goal=.00065):
    coeff, cols = R2["sparse_weights"](weights)
    move, _ = R2["skin_poses"](points,coeff,cols,matrices[frames])
    xyz = posed[frames[:,None],local_ids].copy()
    xyz[:,in_patch] = move
    total = old = 0.
    peak = 0.
    budget = 0
    for row, frame in enumerate(frames):
        name, _, tree, *_ = samples[frame]
        signed = clearance(tree,xyz[row])[0]
        gap = np.maximum(goal-signed,0.) * 1000
        overlaps = len(tree.overlap(BVHTree.FromPolygons(xyz[row].tolist(),patch_faces,
                                                        all_triangles=True)))
        peak = max(peak,float(gap.max()))
        value = overlaps*1.2 + float(gap@gap)*1.1
        total += value
        budget += overlaps
        if name in LEGACY or name == "rest":
            old += overlaps*5. + float(gap@gap)*5.
    return total + 18*peak**2, old, budget


def try_patch(points, origin, weights, anatomy, bones, triangles, posed, skin, signed, samples,
              matrices, pivot, radius, priority, classic):
    distance = np.linalg.norm(origin - origin[pivot],axis=1)
    ids = np.flatnonzero(distance < radius)
    mask = np.isin(triangles,ids).any(axis=1)
    local_ids, lookup = np.unique(triangles[mask].ravel(),return_inverse=True)
    faces = lookup.reshape(-1,3).tolist()
    inverse_ids = np.searchsorted(local_ids,ids)
    start = points[ids]
    start_w = weights[ids]
    base_tri = points[triangles[mask]]
    normal = np.cross(base_tri[:,1]-base_tri[:,0],base_tri[:,2]-base_tri[:,0])
    size = np.square(normal).sum(axis=1)
    p = np.clip(1-distance[ids]/radius,0,1)
    falloff = p*p*(3-2*p)
    rest = samples[0][2]
    tri_bary = R2["REST_BARYCENTRICS"]
    all_frames = np.arange(len(samples),dtype=np.int32)
    sample_rows = {0}
    heat = np.square(np.maximum(.001-signed[:,local_ids],0)).sum(axis=1)
    heat += priority[:,pivot]**2*3
    for clip in (*LEGACY,*ADDED):
        f = np.array([i for i,(name,*_) in enumerate(samples) if name==clip])
        sample_rows.update(f[[0,len(f)//2,-1]])
        picked = []
        for i in f[np.argsort(-heat[f],kind="stable")]:
            if all(abs(i-pos) > (8 if clip in ADDED else 11) for pos in picked):
                picked.append(i)
                if len(picked) == (5 if clip in ADDED else 2):
                    break
        sample_rows.update(picked)
    short_frames = np.array(sorted(sample_rows),dtype=np.int32)

    def trial(delta, revised, frames):
        trial_points = start + delta
        trial_face = posed[0,local_ids].copy()
        trial_face[inverse_ids] = trial_points
        trial_face = trial_face[lookup.reshape(-1,3)]
        shape = np.cross(trial_face[:,1]-trial_face[:,0],trial_face[:,2]-trial_face[:,0])
        if np.any(np.einsum("fi,fi->f",shape,normal) < size*.17):
            return (float("inf"),float("inf"),0)
        if delta.any():
            probes = np.einsum("qk,fki->fqi",tri_bary,trial_face).reshape(-1,3)
            signed = clearance(rest,np.vstack((trial_points,probes)))[0]
            if signed.min() < .00056 or signed.max() > CAP or np.linalg.norm(
                    trial_points-origin[ids],axis=1).max() > CAP:
                return (float("inf"),float("inf"),0)
        return patch_loss(trial_points,revised,local_ids,inverse_ids,faces,posed,
                          samples,matrices,frames)

    slopes = []
    for row in np.argsort(-priority[:,pivot],kind="stable")[:52]:
        target, n, _, _ = samples[row][2].find_nearest(posed[row,pivot].tolist())
        gradient = np.asarray(n) @ skin[row,pivot,:,:3]
        length = np.linalg.norm(gradient)
        if length > 1e-8:
            ray = (gradient/length).astype(np.float32)
            if all(abs(ray @ v) < .94 for v in slopes):
                slopes.append(ray)
    rest_normal = np.asarray(rest.find_nearest(points[pivot].tolist())[1],dtype=np.float32)
    slopes.extend((rest_normal,*np.eye(3,dtype=np.float32)))
    zero = np.zeros_like(start)
    shortlist = []
    base_cost, base_old, _ = trial(zero,start_w,short_frames)
    strengths = (.0018, -.0021, .0042, -.0046, .0075, -.0075)
    if not classic:
        strengths = (.00055, -.00055, *strengths)
        if priority[:, pivot].max() > .006:
            strengths += (.011, -.011, .016, -.016)
    for direction in slopes:
        for amount in strengths:
            delta = falloff[:,None]*direction*amount
            score, old, _ = trial(delta,start_w,short_frames)
            if score < base_cost and old <= base_old + .0005:
                shortlist.append((score,delta,start_w))
    side = "Left" if origin[pivot,0] > 0 else "Right"
    z = origin[pivot,2]
    if z < .415:
        names = ("Hips","Spine",side+"UpLeg",side+"Leg")
    elif z > .485:
        names = ("Spine1","Spine2",side+"Arm",side+"Shoulder")
    else:
        names = ("Spine","Spine1","Spine2","Hips",side+"Arm")
    typical = [anatomy[ids]]
    for name in names:
        values = np.zeros_like(start_w)
        values[:,bones[name]] = 1.
        typical.append(values)
    ranked = sorted(shortlist,key=lambda v: v[0])
    trial_deltas = [zero] + [d for _,d,_ in ranked[:2]]
    if not ranked:
        trial_deltas.extend((falloff[:,None]*rest_normal*.004, -falloff[:,None]*rest_normal*.003))
    for blend in (.25,.55,.83):
        factor = falloff[:,None]*blend
        for target in typical:
            revised = R2["limit_weights"](start_w*(1-factor)+target*factor)
            for delta in trial_deltas:
                score,old,_ = trial(delta,revised,short_frames)
                if score < base_cost and old <= base_old + .0005:
                    shortlist.append((score,delta,revised))
    if not shortlist:
        return None
    baseline, baseline_old, _ = trial(zero,start_w,all_frames)
    best = None
    for _,delta,revised in sorted(shortlist,key=lambda v: v[0])[:5]:
        loss, old, _ = trial(delta,revised,all_frames)
        if old <= baseline_old + .0005 and loss < baseline - .0005:
            best = ids, start + delta, revised, baseline-loss
            baseline = loss
    return best


def patches(passes, source, destination="patches.glb", *, classic=False):
    scene,arm,body,garment,actions = import_scene(source,weld=True)
    setup_material(garment)
    names = tuple(bone.name for bone in arm.data.bones)
    points = mesh_points(garment.data)
    original = points.copy()
    triangles = triangulation(garment)
    weights = R3["read_weights"](garment,names)
    samples,matrices = cache(scene,arm,body,names,actions)
    anatomy = body_weight_targets(points,body,names,samples[0])
    bones = {name.split(":")[-1]:i for i,name in enumerate(names)}
    for cycle in range(passes+1):
        report,posed,skin,signed,normals,contacts,hits=scan(points,weights,triangles,samples,matrices)
        R3["display"](f"PATCH {cycle}",report)
        export(scene,arm,body,garment,names,points,weights,draft=True,draft_name=destination)
        if fit_score(report)==0 or cycle==passes:
            break
        priority = np.maximum(.0012-signed,0)
        for f, pairs in contacts.items():
            np.add.at(priority[f],triangles[np.unique(pairs[:,1])].ravel(),.00038)
        hot = priority.max(axis=0)*36 + np.square(priority).sum(axis=0)**.5
        used=np.zeros(len(points),dtype=bool)
        for k in range(55):
            pivot=int(np.argmax(np.where(used,-1,hot)))
            if hot[pivot]<1e-8 or used[pivot]:
                break
            radius=(.028,.022,.018,.014)[min(cycle,3)]
            used |= np.linalg.norm(original-original[pivot],axis=1) < radius*.73
            result = try_patch(points,original,weights,anatomy,bones,triangles,posed,skin,
                               signed,samples,matrices,pivot,radius,priority,classic)
            if result is None:
                continue
            ids,p,w,gain=result
            points[ids],weights[ids]=p,w
            moved, blend = R2["skin_poses"](p,*R2["sparse_weights"](w),matrices)
            posed[:,ids],skin[:,ids]=moved,blend
            print("PATCH MOVE",k,pivot,np.round(original[pivot]*1000,1),round(gain),flush=True)
            if k%6 == 0:
                export(scene,arm,body,garment,names,points,weights,draft=True,draft_name=destination)


def failure_zones():
    vertex = json.loads((HERE/"motion_check.json").read_text())
    overlaps = json.loads((HERE/"motion_check_tri.json").read_text())
    assert vertex["glb_sha256"] == overlaps["glb_sha256"] == sha(GLB)
    scene,arm,body,garment,actions = import_scene(GLB)
    names = tuple(bone.name for bone in arm.data.bones)
    body_names = np.asarray(R1["zone_names"](body,names))
    points = mesh_points(garment.data)
    triangles = triangulation(garment)
    face_zones = section(points[triangles].mean(axis=1))
    vertex_zones = section(points)
    result = {}
    for name, rows in vertex["frames"].items():
        contact_rows = overlaps["frames"][name]
        failures = [(r[0],v[1]>0,r[1]>0)
                    for v,r in zip(rows,contact_rows) if r[1] or v[2] < FLOOR]
        if not failures:
            continue
        regions = {}
        for frame,_,overlap in failures:
            pose(scene,arm,actions[name],frame)
            graph = bpy.context.evaluated_depsgraph_get()
            xyz, body_polys = R1["posed_mesh"](body,graph)
            gar, _ = R1["posed_mesh"](garment,graph)
            tree = BVHTree.FromPolygons(xyz,body_polys,all_triangles=True)
            distance, _, face = clearance(tree,np.asarray(gar))
            for idx in np.flatnonzero(distance<FLOOR):
                zone = f"{vertex_zones[idx]} / {body_names[face[idx]]}"
                region = regions.setdefault(zone,{})
                if distance[idx] < region.get("vertex_min_m",math.inf):
                    region.update(vertex_min_m=float(distance[idx]), vertex_frame=frame)
            if not overlap:
                continue
            body_polys = np.asarray(body_polys,dtype=np.int32)
            pairs = np.asarray(tree.overlap(BVHTree.FromPolygons(gar,triangles.tolist(),
                                      all_triangles=True)),dtype=np.int32).reshape(-1,2)
            f,b = R1["pair_witnesses"](np.asarray(gar),triangles,np.asarray(xyz),
                                       body_polys,pairs[:,::-1])
            probes = np.einsum("nk,nki->ni",b,np.asarray(gar)[triangles[f]])
            probe_d,_,probe_face = clearance(tree,probes)
            keys = {}
            for body_id, gar_id in pairs:
                zone = f"{face_zones[gar_id]} / {body_names[body_id]}"
                keys[zone] = keys.get(zone,0)+1
            for zone,count in keys.items():
                region = regions.setdefault(zone,{})
                if count > region.get("max_overlap_pairs",0):
                    region.update(max_overlap_pairs=count, peak_pair_frame=frame)
            for i, g in enumerate(f):
                zone = f"{face_zones[g]} / {body_names[probe_face[i]]}"
                region = regions.setdefault(zone,{})
                if probe_d[i] < region.get("face_probe_min_m",math.inf):
                    region.update(face_probe_min_m=float(probe_d[i]), face_probe_frame=frame)
        result[name] = regions
        print("REMAINING",name,len(failures),"samples",len(regions),"zone pairs",flush=True)
    (HERE/"failure_zones.json").write_text(json.dumps(
        {"glb_sha256":sha(GLB),"results":result},indent=2)+"\n")


def protect(path, rounds=7):
    """Blend in proven local changes while retaining the seven-clip fit."""
    scene,arm,body,garment,actions = import_scene(SEED,weld=True)
    setup_material(garment)
    names = tuple(bone.name for bone in arm.data.bones)
    points = mesh_points(garment.data)
    triangles = triangulation(garment)
    weights = R3["read_weights"](garment,names)
    data = np.load(path)
    assert np.array_equal(data["origin"],points) and np.array_equal(data["faces"],triangles)
    target_points, target_weights = data["points"], data["weights"]
    samples,matrices = cache(scene,arm,body,names,actions)
    n_old = sum(1 for name,*_ in samples if name not in ADDED)
    old_samples, old_matrices = samples[:n_old], matrices[:n_old]
    rest = samples[0][2]
    links = R2["neighbors"](garment.data)

    # Round 3 has no intersections in the old bank and leaves a small walk
    # underarm gap below the new floor. Correct just that neighborhood first.
    original = points.copy()
    hold = scan(points,weights,triangles,old_samples,old_matrices)
    for k in range(4):
        _, _, skin, signed, normals, _, hits = hold
        required = np.maximum(.00068-signed,0)
        row = required.argmax(axis=0)
        active = np.flatnonzero(required.max(axis=0)>0)
        if not len(active):
            break
        direction = np.einsum("vi,vij->vj",normals[row[active],active],
                              skin[row[active],active,:,:3])
        dx = np.zeros_like(points)
        dx[active] = direction*required[row[active],active,None]
        for _ in range(3):
            dx += .28*(R2["average"](dx,links)-dx)
            need = required[row[active],active] - np.einsum("vi,vi->v",dx[active],direction)
            dx[active] += direction * need.clip(0)[:,None]
        candidate = R2["rest_guard"](points+dx,points,original,triangles,rest)
        hold = scan(candidate,weights,triangles,old_samples,old_matrices)
        if any(r["pairs"] for r in hold[0].values()):
            break
        points = candidate
    R3["display"]("PROTECT WALK",hold[0])

    start = points.copy()
    weight_base = weights.copy()
    amount = np.ones(len(points),dtype=np.float32)
    starts, ends, _ = links
    for k in range(rounds+1):
        points = start + amount[:,None]*(target_points-original)
        points = R2["rest_guard"](R2["project_rest"](points,original,rest),
                                  start,original,triangles,rest)
        points = trim_rest_probes(points,original,triangles,rest)
        weights = R2["limit_weights"](weight_base*(1-amount[:,None])+target_weights*amount[:,None])
        weights[amount==0] = weight_base[amount==0]
        report,_,_,signed,_,_,hits = scan(points,weights,triangles,old_samples,old_matrices)
        R3["display"](f"PROTECT {k}",report)
        active = np.min(signed,axis=0)<.000525
        active[triangles[hits>0].ravel()] = True
        if not active.any() or k==rounds:
            break
        neighbors = active.copy()
        neighbors[ends[active[starts]]] = True
        amount[neighbors] *= .57
        amount[active] *= .25
        amount[amount<.022] = 0
    full = scan(points,weights,triangles,samples,matrices)[0]
    R3["display"]("PROTECTED",full)
    export(scene,arm,body,garment,names,points,weights,draft=True,draft_name="protected.glb")

def micro_legacy(source, cycles=8, destination="micro.glb", fine=False):
    scene,arm,body,garment,actions=import_scene(source,weld=True)
    setup_material(garment)
    names=tuple(b.name for b in arm.data.bones)
    bones={name.split(":")[-1]:i for i,name in enumerate(names)}
    points=mesh_points(garment.data)
    weights=R3["read_weights"](garment,names)
    triangles=triangulation(garment)
    old_actions={k:v for k,v in actions.items() if k not in ADDED}
    samples,matrices=cache(scene,arm,body,names,old_actions)
    rng=np.random.default_rng(694500 if fine else 650440)
    all_frames=np.arange(len(samples))
    report,posed,skin,signed,_,_,hits=scan(points,weights,triangles,samples,matrices)
    R3["display"]("MICRO INPUT",report)
    for cycle in range(cycles):
        leakage=np.maximum(.00054-signed,0)
        priority=leakage.max(axis=0)
        priority[triangles[hits>0].ravel()]+=.00025
        ids=np.flatnonzero(priority>1e-8)
        if not len(ids):
            break
        changed=False
        for v in ids[np.argsort(-priority[ids],kind="stable")][:10]:
            patch_faces=triangles[(triangles==v).any(axis=1)]
            near,lookup=np.unique(patch_faces.ravel(),return_inverse=True)
            faces=lookup.reshape(-1,3).tolist()
            pivot=np.array([np.searchsorted(near,v)])
            base = points[v:v+1]
            baseline = patch_loss(base,weights[v:v+1],near,pivot,faces,posed,samples,matrices,all_frames)
            base_w = weights[v]
            close = np.flatnonzero(signed[:,v] < .0045)
            frames = np.unique(np.r_[close,np.arange(0,len(samples),11)])
            current_slots = np.argsort(-base_w,kind="stable")[:4]
            side = "Left" if points[v,0]>0 else "Right"
            optional = (bones["Spine1"],bones["Spine2"],bones[side+"Shoulder"],
                        bones[side+"Arm"],bones[side+"ForeArm"])
            count = 1500
            columns = np.tile(current_slots,(count,1))
            for j,bone in enumerate(optional):
                if bone not in current_slots:
                    columns[j*190:(j+1)*190,-1] = bone
            prior = base_w[columns]
            prior /= prior.sum(axis=1,keepdims=True)
            width = np.array([.00038,.00085,.0017,.0027,.0042],dtype=np.float32)
            deviation = rng.normal(size=(count,3)).astype(np.float32)*width[np.arange(count)%5,None]
            weight_span = np.array([.005,.017,.038,.070,.14],dtype=np.float32)
            perturb = rng.normal(size=(count,4)).astype(np.float32)*weight_span[np.arange(count)%5,None]
            perturb[:270]=0
            deviation[270:420]=0
            if fine:
                deviation *= .38
                perturb *= .32
                critical = int(signed[:, v].argmin())
                ray = clearance(samples[critical][2], posed[critical, v:v+1])[1][0]
                ray = ray @ skin[critical, v, :, :3]
                ray /= max(1e-8, float(np.linalg.norm(ray)))
                deviation[:18] = np.linspace(.00004, .0018, 18)[:, None]*ray
            trial_points = points[v]+deviation
            trial_weights = R2["simplex"](prior+perturb)
            rest = samples[0][2]
            gap = clearance(rest,trial_points)[0]
            valid = (gap >= .00056) & (gap <= CAP)
            size_pre = points[patch_faces]
            reference = np.cross(size_pre[:,1]-size_pre[:,0],size_pre[:,2]-size_pre[:,0])
            shape = np.broadcast_to(size_pre[None],(count,*size_pre.shape)).copy()
            shape[:,patch_faces==v] = trial_points[:,None]
            cross = np.cross(shape[:,:,1]-shape[:,:,0],shape[:,:,2]-shape[:,:,0])
            valid &= (np.einsum("cfi,fi->cf",cross,reference) > .14*np.sum(reference**2,axis=1)).all(axis=1)
            gap_peak = np.zeros(count,dtype=np.float32)
            gap_sum = gap_peak.copy()
            for f in frames:
                proj = np.einsum("cb,cbik,ck->ci",trial_weights,matrices[f,columns,:,:3],trial_points)
                proj += np.einsum("cb,cbi->ci",trial_weights,matrices[f,columns,:,3])
                w = np.maximum(.00063-clearance(samples[f][2],proj)[0],0)*1000
                gap_peak = np.maximum(gap_peak,w)
                gap_sum += w*w
            rank = gap_peak**2*20 + 5*gap_sum/len(frames)
            rank += np.square(deviation*1000).sum(axis=1)*.003
            rank[~valid]=np.inf
            best = None
            for trial in np.argsort(rank,kind="stable")[:34]:
                if not valid[trial]:
                    break
                w = np.zeros((1,len(names)),dtype=np.float32)
                w[0,columns[trial]]=trial_weights[trial]
                p = trial_points[trial:trial+1]
                trial_cost = patch_loss(p,w,near,pivot,faces,posed,samples,matrices,all_frames)
                if trial_cost[0] < baseline[0] - .00001 and trial_cost[2] <= baseline[2]:
                    baseline=trial_cost
                    best=(p,w)
                    if trial_cost[0]==0:
                        break
            if best is None:
                continue
            p,w=best
            points[v],weights[v]=p[0],w[0]
            moved,current_skin=R2["skin_poses"](p,*R2["sparse_weights"](w),matrices)
            posed[:,v],skin[:,v]=moved[:,0],current_skin[:,0]
            for f, sample in enumerate(samples):
                signed[f,v] = clearance(sample[2],moved[f])[0][0]
            print("MICRO MOVE",v,np.round(points[v]*1000,2),baseline,flush=True)
            changed=True
        print("MICRO CYCLE",cycle+1,"legacy minimum mm",round(1000*float(signed.min()),4),flush=True)
        if not changed:
            break
    report=scan(points,weights,triangles,samples,matrices)[0]
    R3["display"]("MICRO FINAL",report)
    export(scene,arm,body,garment,names,points,weights,draft=True,draft_name=destination)


def uv_keys(mesh):
    coords = mesh.uv_layers.active.data
    keys = [set() for _ in mesh.vertices]
    for loop in mesh.loops:
        keys[loop.vertex_index].add(tuple(round(float(x),7) for x in coords[loop.index].uv))
    return [tuple(sorted(values)) for values in keys]


def close_rest_cap(source):
    """Trim rest-limit witnesses at the front and rear hem."""
    scene, arm, body, garment, actions = import_scene(source, weld=True)
    setup_material(garment)
    names = tuple(b.name for b in arm.data.bones)
    points = mesh_points(garment.data)
    weights = R3["read_weights"](garment, names)
    triangles = triangulation(garment)
    samples, matrices = cache(scene, arm, body, names, actions)
    posed, skin = R2["skin_poses"](points, *R2["sparse_weights"](weights), matrices)
    tree = samples[0][2]
    frames = np.arange(len(samples))
    directions = np.array([(x,y,z) for x in (-1,0,1) for y in (-1,0,1)
                           for z in (-1,0,1) if x or y or z], dtype=np.float32)
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    for _ in range(4):
        probes = R2["rest_sample_positions"](points, triangles).reshape(-1,3)
        xyz = np.vstack((points, probes))
        signed, normals, _ = clearance(tree, xyz)
        excessive = np.flatnonzero(signed > CAP-.000035)
        print("REST CAP", float(signed.max()), len(excessive), flush=True)
        if not len(excessive):
            break
        worst = int(signed.argmax())
        region = excessive[(np.sign(xyz[excessive,1]) == np.sign(xyz[worst,1]))
                           & (np.linalg.norm(xyz[excessive]-xyz[worst],axis=1) < .043)]
        center = xyz[region].mean(axis=0)
        distance = np.linalg.norm(points-center,axis=1)
        radius = .019 if worst < len(points) else .030
        ids = np.flatnonzero(distance < radius)
        fraction = R1["smoothstep"](radius, 0., distance[ids])
        patch = triangles[np.isin(triangles, ids).any(axis=1)]
        loc, face_index = np.unique(patch.ravel(), return_inverse=True)
        faces = face_index.reshape(-1,3)
        local_ids = np.searchsorted(loc, ids)
        original = points[loc]
        shape = original[faces]
        cross = np.cross(shape[:,1]-shape[:,0],shape[:,2]-shape[:,0])
        delta_shape = np.square(cross).sum(axis=1)
        rays = np.vstack((-normals[region], directions))
        ranked = []
        for strength in (.00032,.00064,.00125,.0019,.0028,.0041,.0055,.007):
            for ray in rays:
                delta = strength*fraction[:,None]*ray
                local = original.copy()
                local[local_ids] += delta
                coords = local[faces]
                moved = np.cross(coords[:,1]-coords[:,0], coords[:,2]-coords[:,0])
                if np.any(np.einsum("ij,ij->i",moved,cross) < .20*delta_shape):
                    continue
                witness = R2["rest_sample_positions"](local, faces).reshape(-1,3)
                rest = clearance(tree,np.vstack((local,witness)))[0]
                if rest.min() >= .00055 and rest.max() <= CAP-.000035:
                    ranked.append((strength,rest.max(),delta))
        if not ranked:
            break
        results = []
        for strength,_,delta in sorted(ranked,key=lambda t:t[:2])[:24]:
            candidate = points[ids] + delta
            cost, old, _ = patch_loss(candidate, weights[ids], loc, local_ids, faces.tolist(),
                                      posed, samples, matrices, frames, goal=.000505)
            if old <= 1e-5:
                results.append((cost+.1*strength*1000, candidate))
        if not results:
            break
        _, selection = min(results,key=lambda t:t[0])
        points[ids] = selection
        posed[:,ids], skin[:,ids] = R2["skin_poses"](
            points[ids],*R2["sparse_weights"](weights[ids]),matrices)
    export(scene, arm, body, garment, names, points, weights, draft=True, draft_name="cap.glb")


def close_walk_patch(source, shoulder_reference):
    """Reconcile the remaining left armpit with the clean legacy fit."""
    scene, arm, body, garment, actions = import_scene(source, weld=True)
    setup_material(garment)
    names = tuple(b.name for b in arm.data.bones)
    points = mesh_points(garment.data)
    weights = R3["read_weights"](garment, names)
    triangles = triangulation(garment)
    other = R1["import_mesh"](shoulder_reference)
    mesh = bmesh.new()
    mesh.from_mesh(other.data)
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=1e-7)
    mesh.to_mesh(other.data)
    mesh.free()
    by_key = {key: i for i, key in enumerate(uv_keys(other.data))}
    match = np.array([by_key[key] for key in uv_keys(garment.data)], dtype=np.int32)
    target = mesh_points(other.data)[match]
    target_weights = R3["read_weights"](other, names)[match]
    bpy.data.objects.remove(other, do_unlink=True)
    samples, matrices = cache(scene, arm, body, names, actions)
    trim_center = np.array((.102, -.038, .510), dtype=np.float32)
    distance = np.linalg.norm(points-trim_center, axis=1)
    moved, _ = R2["skin_poses"](points, *R2["sparse_weights"](weights), matrices)
    frames = np.arange(len(samples))
    best = None
    for inner, outer in ((.012,.024),(.014,.030),(.017,.031),(.019,.035),(.022,.040),(.027,.045)):
        ids = np.flatnonzero(distance < outer)
        factor = R1["smoothstep"](outer, inner, distance[ids])[:,None]
        proposed = points[ids] + factor*(target[ids]-points[ids])
        proposed_w = R2["limit_weights"](weights[ids] + factor*(target_weights[ids]-weights[ids]))
        loc, face_ids = np.unique(triangles[np.isin(triangles, ids).any(axis=1)].ravel(),
                                  return_inverse=True)
        faces = face_ids.reshape(-1,3)
        index = np.searchsorted(loc, ids)
        loss, old, _ = patch_loss(proposed,proposed_w,loc,index,faces.tolist(),
                                  moved,samples,matrices,frames,goal=.000501)
        print("WALK PATCH",inner,outer,old,loss,flush=True)
        if old <= 1e-7 and (best is None or loss < best[0]):
            best = loss, ids, proposed, proposed_w
    if best is None:
        return False
    _,ids,p,w=best
    points[ids],weights[ids]=p,w
    export(scene,arm,body,garment,names,points,weights,draft=True,draft_name="walk_patch.glb")
    return True


def replay():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND),load_ui=False,use_scripts=False)
    scene = bpy.context.scene
    arm,body,garment = (scene.objects[name] for name in ("Armature","Base_Body","Dress"))
    names = tuple(b.name for b in arm.data.bones)
    export(scene,arm,body,garment,names,mesh_points(garment.data),
           R3["read_weights"](garment,names),draft=True,draft_name="replay.glb")
    result = {"source": BLEND.name, "blend_sha256": sha(BLEND),
              "glb_sha256": sha(GLB), "replay_sha256": sha(HERE/".work/replay.glb")}
    result["byte_identical"] = result["glb_sha256"] == result["replay_sha256"]
    (HERE/"blend_replay.json").write_text(json.dumps(result,indent=2)+"\n")
    print("BLEND REPLAY",result,flush=True)


def build():
    """Repeat the local fit and shoulder reconciliation from the shipped dress."""
    work = HERE / ".work"
    work.mkdir(exist_ok=True)
    guarded(6)
    protect(work / "guarded_state.npz")
    micro_legacy(work / "protected.glb", 3, "lower_micro.glb")
    patches(2, work / "lower_micro.glb", "hybrid.glb")
    micro_legacy(work / "hybrid.glb", 8, "final_hybrid.glb")
    micro_legacy(work / "final_hybrid.glb", 5, "fine_hybrid.glb", fine=True)
    patches(3, SEED, "upper.glb", classic=True)
    micro_legacy(work / "upper.glb", 8, "upper_micro.glb")
    if not close_walk_patch(work / "fine_hybrid.glb", work / "upper_micro.glb"):
        raise RuntimeError("Left armpit patch missed the legacy clearance floor")
    close_rest_cap(work / "walk_patch.glb")
    finalize(work / "cap.glb")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["build"]
    stage = args[0]
    if stage == "walk_patch":
        close_walk_patch(Path(args[1]).resolve(),Path(args[2]).resolve())
    elif stage == "cap":
        close_rest_cap(Path(args[1]).resolve() if len(args)>1 else GLB)
    elif stage == "finish":
        finalize(Path(args[1]).resolve())
    elif stage == "micro":
        micro_legacy(Path(args[1]).resolve(), int(args[2]) if len(args)>2 else 8,
                     args[3] if len(args)>3 else "micro.glb", fine="fine" in args[4:])
    else:
        stages = {"build": build, "check": check, "vertex": lambda: check(variants=(False,)),
                  "triangles": lambda: check(variants=(True,)), "verify": verify,
                  "render": render, "zones": failure_zones, "replay": replay,
                  "baseline": lambda: check(SEED, HERE / ".work")}
        for stage in args:
            stages[stage]()
