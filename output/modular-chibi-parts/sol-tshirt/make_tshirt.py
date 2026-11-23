"""Build the GJH chibi T-shirt in the folder containing this script.

Pass the source .blend path after Blender's "--" separator, or use the
default rigged master in the sibling master folder.
"""

import argparse
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils.bvhtree import BVHTree


OUTPUT_DIR = Path(__file__).resolve().parent
MASTER_BLEND = OUTPUT_DIR.parent / "master" / "GJH_Chibi_Master_rigged.blend"
NAME = "top_tshirt_v1"
STANDOFF = 0.008
THICKNESS = 0.004
MIN_CLEARANCE = 0.002
WAIST_EASE = 0.0025
SLEEVE_FRACTION = 0.40
HEM_ABOVE_HIPS = 0.037
WELD_TOLERANCE = 0.000001
FABRIC_COLOR = (0.075, 0.40, 0.37, 1.0)


def bone_head(rig, name):
    return rig.matrix_world @ rig.data.bones[f"mixamorig:{name}"].head_local


def clip_polygon(polygon, signed_distance):
    """Keep the positive side of the cut, interpolating along body edges."""
    if not polygon:
        return []
    clipped = []
    previous = polygon[-1]
    previous_distance = signed_distance(previous)
    for current in polygon:
        distance = signed_distance(current)
        if (distance > 0) != (previous_distance > 0):
            fraction = previous_distance / (previous_distance - distance)
            clipped.append(previous.lerp(current, fraction))
        if distance > 0:
            clipped.append(current)
        previous, previous_distance = current, distance
    return clipped


def keep_largest_island(mesh):
    remaining = set(mesh.faces)
    islands = []
    while remaining:
        island = [remaining.pop()]
        for face in island:
            for edge in face.edges:
                for neighbor in edge.link_faces:
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        island.append(neighbor)
        islands.append(island)
    if not islands:
        raise RuntimeError("The garment cuts removed the entire body surface.")
    garment = set(max(islands, key=len))
    unused = [face for face in mesh.faces if face not in garment]
    bmesh.ops.delete(mesh, geom=unused, context="FACES")


def count_openings(mesh):
    neighbors = {}
    for edge in mesh.edges:
        if not edge.is_boundary:
            continue
        first, second = edge.verts
        neighbors.setdefault(first, []).append(second)
        neighbors.setdefault(second, []).append(first)
    if any(len(adjacent) != 2 for adjacent in neighbors.values()):
        raise RuntimeError("The garment has a branched boundary.")
    remaining = set(neighbors)
    openings = 0
    while remaining:
        loop = [remaining.pop()]
        for vertex in loop:
            for neighbor in neighbors[vertex]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    loop.append(neighbor)
        openings += 1
    return openings


def smooth_shell(shell):
    for _ in range(3):
        bmesh.ops.smooth_vert(
            shell, verts=list(shell.verts), factor=0.35,
            use_axis_x=True, use_axis_y=True, use_axis_z=True,
        )


def restore_clearance(shell, body_surface):
    for vertex in shell.verts:
        position = vertex.co.copy()
        # The source torso has a deep waist crease. Feather in extra room so
        # the fabric bridges the crease and the inner wall can clear it.
        waist = max(0.0, min(1.0, (0.54 - position.z) / 0.035))
        target = STANDOFF + WAIST_EASE * waist
        for _ in range(16):
            nearest, normal, _, distance = body_surface.find_nearest(position)
            delta = position - nearest
            if delta.dot(normal) < 0:
                position += normal * (target + distance)
            elif distance < target:
                direction = delta.normalized() if distance > 0.000001 else normal
                position += direction * (target - distance + 0.000001)
            else:
                break
        vertex.co = position


def offset_shell(shell, body_surface):
    smooth_shell(shell)
    shell.normal_update()
    for vertex in shell.verts:
        vertex.co += STANDOFF * vertex.normal
    for _ in range(3):
        smooth_shell(shell)
        restore_clearance(shell, body_surface)


def make_shell(body, rig, body_surface):
    hips = bone_head(rig, "Hips")
    neck = bone_head(rig, "Neck")
    left = bone_head(rig, "LeftArm").lerp(bone_head(rig, "LeftForeArm"), SLEEVE_FRACTION)
    right = bone_head(rig, "RightArm").lerp(bone_head(rig, "RightForeArm"), SLEEVE_FRACTION)

    def collar_clearance(point):
        # Lower at the front, curving upward onto both shoulders.
        x = point.x - neck.x
        y = point.y - neck.y
        collar_height = neck.z - 0.014 + 0.36 * y + 11.0 * x * x
        return min(neck.z + 0.013, collar_height) - point.z

    cuts = (
        lambda point: point.z - (hips.z + HEM_ABOVE_HIPS),
        lambda point: left.x - point.x,
        lambda point: point.x - right.x,
        collar_clearance,
    )
    body_mesh = body.data
    body_mesh.calc_loop_triangles()
    positions = [body.matrix_world @ vertex.co for vertex in body_mesh.vertices]
    vertices, faces = [], []
    for triangle in body_mesh.loop_triangles:
        polygon = [positions[index] for index in triangle.vertices]
        for cut in cuts:
            polygon = clip_polygon(polygon, cut)
        if len(polygon) >= 3:
            first_index = len(vertices)
            vertices.extend(polygon)
            faces.append(tuple(range(first_index, len(vertices))))

    data = bpy.data.meshes.new(NAME)
    data.from_pydata(vertices, [], faces)
    shell = bmesh.new()
    try:
        shell.from_mesh(data)
        # The source has split vertices along shading and material boundaries.
        bmesh.ops.remove_doubles(shell, verts=list(shell.verts), dist=WELD_TOLERANCE)
        keep_largest_island(shell)
        bmesh.ops.triangulate(shell, faces=list(shell.faces))
        bmesh.ops.subdivide_edges(
            shell,
            edges=[edge for edge in shell.edges if edge.calc_length() > 0.024],
            cuts=1,
            use_grid_fill=True,
        )
        bmesh.ops.triangulate(shell, faces=list(shell.faces))
        if count_openings(shell) != 4:
            raise RuntimeError("Expected only the collar, hem, and two sleeve openings.")
        offset_shell(shell, body_surface)
        for face in shell.faces:
            face.smooth = True
        shell.to_mesh(data)
    finally:
        shell.free()
    data.update()
    shirt = bpy.data.objects.new(NAME, data)
    bpy.context.collection.objects.link(shirt)
    return shirt


def copy_weights(body, shirt):
    for group in body.vertex_groups:
        shirt.vertex_groups.new(name=group.name)

    transfer = shirt.modifiers.new("Transfer body weights", "DATA_TRANSFER")
    transfer.object = body
    transfer.use_vert_data = True
    transfer.data_types_verts = {"VGROUP_WEIGHTS"}
    transfer.vert_mapping = "POLYINTERP_NEAREST"
    transfer.layers_vgroup_select_src = "ALL"
    transfer.layers_vgroup_select_dst = "NAME"
    bpy.ops.object.modifier_apply(modifier=transfer.name)

    for vertex in shirt.data.vertices:
        weights = sorted(
            ((entry.group, entry.weight) for entry in vertex.groups if entry.weight > 0.0),
            key=lambda item: (-item[1], item[0]),
        )[:4]
        if not weights:
            raise RuntimeError(f"Data Transfer left vertex {vertex.index} unweighted.")
        for group in [entry.group for entry in vertex.groups]:
            shirt.vertex_groups[group].remove([vertex.index])
        total = sum(weight for _, weight in weights)
        for group, weight in weights:
            shirt.vertex_groups[group].add([vertex.index], weight / total, "REPLACE")


def finish_shirt(shirt, rig):
    solidify = shirt.modifiers.new("Fabric thickness", "SOLIDIFY")
    solidify.thickness = THICKNESS
    solidify.offset = -1.0
    solidify.use_rim = True
    bpy.ops.object.modifier_apply(modifier=solidify.name)

    fabric = bpy.data.materials.new("T-shirt | Sea Green")
    fabric.diffuse_color = FABRIC_COLOR
    surface = fabric.node_tree.nodes.get("Principled BSDF")
    surface.inputs["Base Color"].default_value = FABRIC_COLOR
    surface.inputs["Roughness"].default_value = 0.85
    shirt.data.materials.append(fabric)

    # Keep the mesh in the same world-space bind position used for transfer.
    bind_transform = shirt.matrix_world.copy()
    shirt.parent = rig
    shirt.matrix_world = bind_transform
    deform = shirt.modifiers.new("Armature", "ARMATURE")
    deform.object = rig


def surface_triangles(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.data
    mesh.calc_loop_triangles()
    positions = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    triangles = [tuple(triangle.vertices) for triangle in mesh.loop_triangles]
    return positions, triangles


def verify_fit(body_surface, shirt, rig):
    shirt.data.calc_loop_triangles()
    triangle_count = len(shirt.data.loop_triangles)
    print(f"T-shirt triangles: {triangle_count}", flush=True)
    if not 1500 <= triangle_count <= 4000:
        raise RuntimeError("T-shirt triangle count is outside the requested range.")

    deform_groups = {
        group.index for group in shirt.vertex_groups
        if (bone := rig.data.bones.get(group.name)) is not None and bone.use_deform
    }
    for vertex in shirt.data.vertices:
        weights = [entry for entry in vertex.groups if entry.weight > 0.0]
        if (
            not 1 <= len(weights) <= 4
            or any(entry.group not in deform_groups for entry in weights)
            or abs(sum(entry.weight for entry in weights) - 1.0) > 0.00001
        ):
            raise RuntimeError(f"Invalid skin weights at vertex {vertex.index}.")

    shirt_positions, shirt_triangles = surface_triangles(shirt)
    shirt_surface = BVHTree.FromPolygons(shirt_positions, shirt_triangles, all_triangles=True)
    minimum_distance = float("inf")
    inward_vertices = 0
    for position in shirt_positions:
        nearest, normal, _, distance = body_surface.find_nearest(position)
        minimum_distance = min(minimum_distance, distance)
        inward_vertices += (position - nearest).dot(normal) < 0.0
    intersections = len(body_surface.overlap(shirt_surface))
    self_intersections = sum(
        not set(shirt_triangles[first]).intersection(shirt_triangles[second])
        for first, second in shirt_surface.overlap(shirt_surface)
        if first < second
    )
    passed = (
        minimum_distance >= MIN_CLEARANCE
        and not inward_vertices
        and not intersections
        and not self_intersections
    )
    print(
        f"T-pose poke-through: {'PASS' if passed else 'FAIL'}; "
        f"minimum vertex clearance {minimum_distance:.6f} (required {MIN_CLEARANCE:.3f}); "
        f"{inward_vertices} inward vertices; {intersections} shirt/body intersections; "
        f"{self_intersections} clothing self-intersections.",
        flush=True,
    )
    if not passed:
        raise RuntimeError("The T-shirt failed the T-pose fit check.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, default=MASTER_BLEND)
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    source = parser.parse_args(arguments).source.resolve()
    blend_path = OUTPUT_DIR / f"{NAME}.blend"
    glb_path = OUTPUT_DIR / f"{NAME}.glb"
    if source in {blend_path.resolve(), glb_path.resolve()}:
        raise ValueError("The source must be separate from the generated files.")

    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    body = bpy.data.objects["Base_Body"]
    rig = bpy.data.objects["Armature"]
    original_pose_mode = rig.data.pose_position
    rig.data.pose_position = "REST"
    bpy.context.view_layer.update()

    body_positions, body_triangles = surface_triangles(body)
    body_surface = BVHTree.FromPolygons(body_positions, body_triangles, all_triangles=True)
    shirt = make_shell(body, rig, body_surface)
    bpy.ops.object.select_all(action="DESELECT")
    shirt.select_set(True)
    bpy.context.view_layer.objects.active = shirt
    copy_weights(body, shirt)
    finish_shirt(shirt, rig)
    rig.data.pose_position = original_pose_mode
    bpy.context.view_layer.update()
    body_positions, body_triangles = surface_triangles(body)
    body_surface = BVHTree.FromPolygons(body_positions, body_triangles, all_triangles=True)
    verify_fit(body_surface, shirt, rig)
    rig.select_set(True)
    # Omit the Blender-only armature wrapper while retaining the joint tree.
    result = bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        use_selection=True,
        export_skins=True,
        export_animations=False,
        export_all_influences=False,
        export_armature_object_remove=True,
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"GLB export failed: {result}")
    rig.select_set(False)
    file_preferences = bpy.context.preferences.filepaths
    file_preferences.save_version = 0
    file_preferences.file_preview_type = "NONE"
    result = bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), copy=True)
    if "FINISHED" not in result:
        raise RuntimeError(f"Blend save failed: {result}")


if __name__ == "__main__":
    main()
