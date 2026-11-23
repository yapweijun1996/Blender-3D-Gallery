"""Collision and flat-colour visibility checks for skinned Blender imports."""
import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
EXPOSURE_CLIPS = {"rest", "walk", "run", "wave"}
EXPOSURE_LIMIT = 0.002
RESOLUTION = 256
AZIMUTHS = tuple(range(0, 360, 45))
ELEVATIONS = (-12, 4, 28)


def import_glb(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
    objects = set(bpy.context.scene.objects) - before
    armatures = [obj for obj in objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise ValueError(f"{path}: expected one armature")
    armature = armatures[0]
    meshes = sorted((obj for obj in objects if obj.type == "MESH"
                     and any(mod.type == "ARMATURE" and mod.object == armature
                             for mod in obj.modifiers)), key=lambda obj: obj.name)
    return armature, meshes


def load_scene(body_path, garment_path, motion_path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    body, region_meshes = import_glb(body_path)
    garment_rig, garments = import_glb(garment_path)
    if not garments or len(body.data.bones) != 65 or set(body.data.bones.keys()) != set(garment_rig.data.bones.keys()):
        raise ValueError("Garment and body must use the same 65-joint rig")
    for mesh in garments:
        world = mesh.matrix_world.copy()
        mesh.parent = body
        mesh.matrix_world = world
        for mod in mesh.modifiers:
            if mod.type == "ARMATURE" and mod.object == garment_rig:
                mod.object = body
    bpy.data.objects.remove(garment_rig, do_unlink=True)

    source, source_meshes = import_glb(motion_path)
    for mesh in source_meshes:
        bpy.data.objects.remove(mesh, do_unlink=True)
    clips = {name: bpy.data.actions.get(name) for name in CLIPS}
    if any(action is None or len(action.slots) != 1 for action in clips.values()):
        raise ValueError("Motion GLB must provide all seven clips with one action slot each")
    source.animation_data.use_nla = False

    # Transfer rotations through the source and target rest bases. This matches
    # the dress-up rig's rest-relative rotations and vertical-only root travel.
    basis = []
    for bone in body.pose.bones:
        original = source.pose.bones.get(bone.name)
        if original is None or bone.rotation_mode != "QUATERNION":
            raise ValueError(f"Incompatible motion joint {bone.name}")
        target_rest = (body.matrix_world @ bone.bone.matrix_local).to_quaternion()
        source_rest = (source.matrix_world @ original.bone.matrix_local).to_quaternion()
        offset = target_rest.inverted() @ source_rest
        basis.append((bone, original.name, offset, offset.inverted()))
        if bone.name == "mixamorig:Hips":
            hips = (bone, original.name, target_rest.inverted(), source_rest)

    def put_pose(action, frame):
        if action is None:
            return
        animation = source.animation_data
        animation.action = action
        animation.action_slot = action.slots[0]
        scene = bpy.context.scene
        scene.frame_set(frame)
        evaluated = source.evaluated_get(bpy.context.evaluated_depsgraph_get())
        for target, name, offset, inverse in basis:
            target.rotation_quaternion = offset @ evaluated.pose.bones[name].rotation_quaternion @ inverse
        target, name, into_target, from_source = hips
        z = (from_source @ evaluated.pose.bones[name].location).z
        target.location = into_target @ Vector((0, 0, z))
        bpy.context.view_layer.update()

    return region_meshes, garments, clips, put_pose


def geometry(objects, depsgraph):
    vertices, triangles = [], []
    for obj in objects:
        posed = obj.evaluated_get(depsgraph)
        mesh = posed.to_mesh()
        try:
            mesh.calc_loop_triangles()
            start = len(vertices)
            vertices.extend(posed.matrix_world @ vertex.co for vertex in mesh.vertices)
            triangles.extend(tuple(start + idx for idx in tri.vertices) for tri in mesh.loop_triangles)
        finally:
            posed.to_mesh_clear()
    return vertices, triangles


def surface_tree(vertices, triangles):
    return BVHTree.FromPolygons(vertices, triangles, all_triangles=True)


def collisions(mode, body_vertices, body_faces, mask, garment_vertices, garment_faces):
    visible_faces = [tri for tri, hidden in zip(body_faces, mask) if not hidden]
    if not visible_faces:
        return 0, None

    # The original surface gives each point a nearest owning face. Classifying
    # against the open visible patches alone signs points beyond cut edges.
    full = surface_tree(body_vertices, body_faces)
    inside = 0
    min_signed = math.inf
    for point in garment_vertices:
        location, normal, face, distance = full.find_nearest(point)
        if mask[face]:
            continue
        signed = -distance if (point - location).dot(normal) < 0 else distance
        inside += signed < 0
        min_signed = min(min_signed, signed)

    if mode == "triangles":
        visible = surface_tree(body_vertices, visible_faces)
        garment = surface_tree(garment_vertices, garment_faces)
        count = len(visible.overlap(garment))
    else:
        count = inside
    return count, min_signed if math.isfinite(min_signed) else None


def exposure(body_vertices, body_faces, names, hides, garment_vertices, garment_faces):
    """One depth-tested flat-colour sample per orthographic pixel centre."""
    offset = len(body_vertices)
    vertices = body_vertices + garment_vertices
    faces = body_faces + [tuple(offset + vertex for vertex in tri) for tri in garment_faces]
    labels = [name if name in hides else None for name in names] + [None] * len(garment_faces)
    tree = surface_tree(vertices, faces)
    center = Vector(tuple((min(v[axis] for v in vertices) + max(v[axis] for v in vertices)) / 2
                          for axis in range(3)))
    relative = [vector - center for vector in vertices]
    scale = max(vertex.length for vertex in relative) * 2.08
    step = scale / RESOLUTION
    casts = []
    for degrees in ELEVATIONS:
        elevation = math.radians(degrees)
        for azimuth in AZIMUTHS:
            angle = math.radians(azimuth)
            toward_camera = Vector((math.sin(angle) * math.cos(elevation),
                                    -math.cos(angle) * math.cos(elevation), math.sin(elevation)))
            right = Vector((math.cos(angle), math.sin(angle), 0))
            up = toward_camera.cross(right)
            ray_origin = center + scale * toward_camera
            ray_direction = -toward_camera
            horizontal = [v.dot(right) for v in relative]
            vertical = [v.dot(up) for v in relative]

            def pixel_range(values):
                low = max(0, math.ceil(min(values) / step + RESOLUTION / 2 - 0.5))
                high = min(RESOLUTION, math.floor(max(values) / step + RESOLUTION / 2 - 0.5) + 1)
                return range(low, high)

            columns = [right * ((x + 0.5 - RESOLUTION / 2) * step) for x in pixel_range(horizontal)]
            silhouette = 0
            exposed = Counter()
            cast = tree.ray_cast
            for y in pixel_range(vertical):
                row = ray_origin + up * ((y + 0.5 - RESOLUTION / 2) * step)
                for column in columns:
                    _, _, face, _ = cast(row + column, ray_direction)
                    if face is not None:
                        silhouette += 1
                        label = labels[face]
                        if label is not None:
                            exposed[label] += 1
            if silhouette == 0:
                raise ValueError("Camera has no silhouette pixels")
            count = exposed.total()
            casts.append({"azimuth_deg": azimuth, "elevation_deg": degrees,
                          "exposed_pixels": count, "silhouette_pixels": silhouette,
                          "exposed_fraction": count / silhouette,
                          "exposed_by_region": dict(exposed)})
    return casts


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("body", type=Path, help="base_body_regions.glb (replaces the legacy master.blend)")
    parser.add_argument("motion", type=Path)
    parser.add_argument("garment", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--hide", help="Comma-separated region IDs; an empty string hides nothing")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if args.hide is None:
        with args.garment.with_suffix(".json").open() as sidecar:
            hides = json.load(sidecar)["hides"]
    else:
        hides = [part.strip() for part in args.hide.split(",")] if args.hide.strip() else []
    if not isinstance(hides, list) or any(not isinstance(name, str) or not name for name in hides):
        parser.error("hides must contain non-empty region names")
    if len(hides) != len(set(hides)):
        parser.error("hides must not contain duplicate regions")
    args.hides = set(hides)
    # Existing commands may keep passing master.blend as their first argument.
    if args.body.suffix.lower() == ".blend":
        args.body = HERE / "base_body_regions.glb"
    return args


def main(mode):
    args = arguments()
    region_meshes, garments, clips, put_pose = load_scene(args.body, args.garment, args.motion)
    counts = json.loads(args.body.with_name("regions.json").read_text())
    if {obj.name: len(obj.data.polygons) for obj in region_meshes} != counts:
        raise ValueError("Region geometry does not match regions.json")
    if args.hides - counts.keys():
        raise ValueError(f"Unknown hide regions: {sorted(args.hides - counts.keys())}")
    names = [obj.name for obj in region_meshes for _ in obj.data.polygons]
    mask = [name in args.hides for name in names]
    metric = "max_verts_inside" if mode == "vertices" else "tri_overlap_pairs"
    report = {"garment": args.garment.name, "hides": sorted(args.hides), "metric": metric,
              "exposure_limit": EXPOSURE_LIMIT, "resolution": RESOLUTION, "clips": {}}

    for name, action in [("rest", None), *clips.items()]:
        if action is None:
            collision_frames = [None]
            view_frames = [None]
        else:
            start, end = action.frame_range
            samples = sorted({int(start + (end - start) * k / 12) for k in range(12)})
            collision_frames = list(range(int(start), int(end) + 1, 3)) if mode == "triangles" else samples
            view_frames = samples if name in EXPOSURE_CLIPS else []

        measured, casts = [], []
        for frame in sorted(set(collision_frames + view_frames)):
            put_pose(action, frame)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            body_vertices, body_faces = geometry(region_meshes, depsgraph)
            garment_vertices, garment_faces = geometry(garments, depsgraph)
            if len(body_faces) != len(mask):
                raise ValueError("Triangulated body topology changed during evaluation")
            if frame in collision_frames:
                count, minimum = collisions(mode, body_vertices, body_faces, mask, garment_vertices, garment_faces)
                measured.append({"frame": frame, metric: count, "min_signed_dist": minimum})
            if frame in view_frames:
                views = exposure(body_vertices, body_faces, names, args.hides, garment_vertices, garment_faces)
                casts.extend({"frame": frame, **view} for view in views)
        distances = [result["min_signed_dist"] for result in measured if result["min_signed_dist"] is not None]
        result = {metric: max(sample[metric] for sample in measured), "collision_samples": measured,
                  "min_signed_dist": min(distances, default=None)}
        if casts:
            worst = max(casts, key=lambda cast: cast["exposed_fraction"])
            result.update(worst_exposure=worst, exposure_views=casts, exposure_pass=worst["exposed_fraction"] < EXPOSURE_LIMIT)
            print(f"EXPOSURE {name} {worst['exposed_pixels']}/{worst['silhouette_pixels']} "
                  f"({worst['exposed_fraction']:.3%}) frame={worst['frame']} "
                  f"azimuth={worst['azimuth_deg']} elevation={worst['elevation_deg']}", flush=True)
        report["clips"][name] = result
        print(f"RESULT {name} {metric} {result[metric]} min_signed_dist {result['min_signed_dist']}", flush=True)

    report["collision_pass"] = all(result[metric] == 0 for result in report["clips"].values())
    report["exposure_pass"] = all(report["clips"][name]["exposure_pass"] for name in EXPOSURE_CLIPS)
    report["pass"] = report["collision_pass"] and report["exposure_pass"]
    print(f"GATES collision={report['collision_pass']} exposure={report['exposure_pass']}", flush=True)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output = args.out_dir / ("motion_check_masked.json" if mode == "vertices" else "motion_check_tri_masked.json")
    output.write_text(json.dumps(report, indent=2) + "\n")
    if not report["pass"]:
        sys.exit(1)
