"""Build a welded interior floor mitre from the editable 2 m straight edge."""

import argparse
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

BASE = Path(__file__).resolve().parent
SLUG = "mall-floor-inside-mitre-2m"
SOURCE = BASE / "sources" / (SLUG + ".blend")
KIT_SLUG = "mall-floor-edge-2m"
KIT_SOURCE = BASE.parent / KIT_SLUG / "sources" / (KIT_SLUG + ".blend")
ROOT = "ASSET_MallFloorInsideMitre2m"
LEVELS = ("LOD0", "LOD1", "LOD2")


def export_name(level):
    suffix = "" if level == "LOD0" else "-" + level.lower()
    return SLUG + suffix + ".glb"


def new_collection(name):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def add_object(name, data, collection, parent=None):
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.parent = parent
    if data is None:
        obj.empty_display_size = 0.035
    return obj


def read_straight_sources(path):
    names = ["Straight full-depth section " + level for level in LEVELS]
    names += ["Straight fascia buttons " + level for level in LEVELS[:2]]
    with bpy.data.libraries.load(str(path), link=False) as (available, imported):
        if not all(name in available.objects for name in names):
            raise ValueError("The source needs all three native sections and both fastener meshes")
        imported.objects = names
    return {obj.name: obj for obj in imported.objects}


def original_section(mesh):
    """Read the ordered end polygon and its adjacent original face finishes."""

    def is_positive_end(face):
        return all(mesh.vertices[i].co.x > 0.99 for i in face.vertices)

    cap = next(face for face in mesh.polygons if is_positive_end(face))
    ring = list(cap.vertices)
    faces = {}
    for face in mesh.polygons:
        if face.index == cap.index:
            continue
        pair = frozenset(vertex for vertex in face.vertices if vertex in ring)
        if len(pair) == 2:
            faces[pair] = face
    if len(faces) != len(ring):
        raise ValueError("Incomplete straight-edge section")
    inner = max(mesh.vertices[i].co.y for i in ring)
    profile = [(inner - mesh.vertices[i].co.y, mesh.vertices[i].co.z) for i in ring]
    finish = [faces[frozenset((i, ring[(n + 1) % len(ring)]))] for n, i in enumerate(ring)]
    return inner, profile, finish, cap


def build_section(source, level, collection, root):
    inner, profile, sides, end_cap = original_section(source)
    count = len(profile)
    # Blender coordinates are (glTF X, -glTF Z, glTF Y). The shared ring
    # indexes one physical edge at each profile break along the diagonal.
    vertices = (
        [(2, -radial, height) for radial, height in profile]
        + [(radial, -radial, height) for radial, height in profile]
        + [(radial, -2, height) for radial, height in profile]
    )
    faces = [tuple(range(count)), tuple(range(2 * count, 3 * count))]
    finishes = [end_cap, end_cap]
    for ring_start in (0, count):
        for index, original in enumerate(sides):
            a = ring_start + index
            b = ring_start + (index + 1) % count
            faces.append((a, b, b + count, a + count))
            finishes.append(original)
    name = "Welded inside mitre " + level
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    for material in source.materials:
        mesh.materials.append(material)
    original_colors = source.color_attributes.get("Metal finishes")
    if original_colors:
        colors = mesh.color_attributes.new(
            name=original_colors.name, type="FLOAT_COLOR", domain="CORNER"
        )
    for face, original in zip(mesh.polygons, finishes):
        face.material_index = original.material_index
        if original_colors:
            color = original_colors.data[original.loop_start].color
            for loop in face.loop_indices:
                colors.data[loop].color = color
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.normal_update()
    if bm.calc_volume(signed=True) <= 0 or not all(edge.is_manifold for edge in bm.edges):
        raise ValueError("The mitered body must be a closed outward shell")
    bm.to_mesh(mesh)
    bm.free()
    obj = add_object(name, mesh, collection, root)
    for label, indices in [
        ("East arm", range(2 * count)),
        ("Diagonal seam", range(count, 2 * count)),
        ("Positive Z arm", range(count, 3 * count)),
    ]:
        obj.vertex_groups.new(name=label).add(list(indices), 1, "REPLACE")
    return inner


def build_buttons(source, level, inner, collection, root):
    for arm in ("East", "Positive Z"):
        mesh = source.data.copy()
        name = arm + " fascia buttons " + level
        mesh.name = name
        for vertex in mesh.vertices:
            station, transverse, height = vertex.co
            radial = inner - transverse
            if arm == "East":
                vertex.co = (1 + station, -radial, height)
            else:
                # Rotate the original straight detail, preserving its winding.
                vertex.co = (radial, station - 1, height)
        add_object(name, mesh, collection, root)


def make_level(level, sources):
    collection = new_collection(level)
    root_name = ROOT if level == "LOD0" else ROOT + "_" + level
    root = add_object(root_name, None, collection)
    root["form"] = "90 degree inside mitre"
    root["grid_m"] = 2.0
    section = sources["Straight full-depth section " + level]
    inner = build_section(section.data, level, collection, root)
    if level != "LOD2":
        build_buttons(sources["Straight fascia buttons " + level], level, inner, collection, root)
    for arm, position in [("East", (2, -0.03, 0)), ("PositiveZ", (0.03, -2, 0))]:
        socket = add_object("CONNECTOR_InsideMitre_" + arm + "_" + level, None, collection, root)
        socket.location = position


def aim(obj, at):
    obj.rotation_euler = (Vector(at) - obj.location).to_track_quat("-Z", "Y").to_euler()


def studio():
    collection = new_collection("STUDIO")
    backdrop = bpy.data.meshes.new("Studio plane")
    backdrop.from_pydata(
        [(-25, -25, -0.1004), (25, -25, -0.1004), (25, 25, -0.1004), (-25, 25, -0.1004)],
        [],
        [(0, 1, 2, 3)],
    )
    material = bpy.data.materials.new("Studio warm neutral")
    material.diffuse_color = (0.27, 0.245, 0.20, 1)
    material.use_nodes = True
    material.node_tree.nodes["Principled BSDF"].inputs[
        "Base Color"
    ].default_value = material.diffuse_color
    backdrop.materials.append(material)
    add_object("Studio ground", backdrop, collection)
    target = (0.89, -0.88, -0.055)
    for name, position, power, size in [
        ("Softbox", (-2.7, -3.6, 4.3), 390, 3.0),
        ("Fascia fill", (3.5, -3.2, 1.5), 230, 1.9),
        ("Rim", (1.7, 3.3, 3.3), 470, 2.8),
    ]:
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size = power, "DISK", size
        light = add_object(name, data, collection)
        light.location = position
        aim(light, target)
    scene = bpy.context.scene
    camera = add_object("Studio camera", bpy.data.cameras.new("Studio camera"), collection)
    scene.camera = camera
    camera.data.type, camera.data.ortho_scale = "ORTHO", 3.35
    camera.location = (3.85, -4.60, 2.65)
    aim(camera, target)
    camera.location += camera.rotation_euler.to_quaternion() @ Vector((0, 0.22, 0))
    scene.world = bpy.data.worlds.new("Studio world")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.55, 0.58, 0.64, 1)
    bg.inputs["Strength"].default_value = 0.48
    scene.render.engine = "CYCLES"
    scene.cycles.samples, scene.cycles.use_denoising = 32, True
    scene.render.resolution_x, scene.render.resolution_y = 900, 560
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 94
    scene.view_settings.view_transform = "AgX"
    for obj in collection.objects:
        obj.hide_set(True)


def show(level):
    for name in LEVELS:
        for obj in bpy.data.collections[name].objects:
            obj.hide_set(name != level)
            obj.hide_render = name != level


def build(kit, source):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    originals = read_straight_sources(kit)
    for level in LEVELS:
        make_level(level, originals)
    for obj in list(bpy.data.objects):
        if not obj.users_collection:
            bpy.data.objects.remove(obj)
    bpy.data.orphans_purge(do_recursive=True)
    studio()
    show("LOD0")
    body = bpy.data.objects["Welded inside mitre LOD0"]
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            view = area.spaces.active
            view.region_3d.view_perspective = "ORTHO"
            view.region_3d.view_location = (0.89, -0.88, -0.05)
            view.region_3d.view_distance = 3.5
            view.region_3d.view_rotation = bpy.context.scene.camera.rotation_euler.to_quaternion()
            view.shading.color_type = "MATERIAL"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True, relative_remap=False)


def export_all(destination):
    destination.mkdir(parents=True, exist_ok=True)
    for level in LEVELS:
        show(level)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in bpy.data.collections[level].objects:
            obj.select_set(True)
        bpy.ops.export_scene.gltf(
            filepath=str(destination / export_name(level)),
            export_format="GLB",
            use_selection=True,
            export_yup=True,
            export_apply=True,
            export_animations=False,
            export_extras=False,
            export_cameras=False,
            export_lights=False,
        )
    show("LOD0")


def main():
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--build", action="store_true", help="Start a fresh source from the original straight kit"
    )
    modes.add_argument(
        "--export-source", action="store_true", help="Export the saved source including edits"
    )
    parser.add_argument("--kit-source", type=Path, default=KIT_SOURCE)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=BASE / "exports")
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if args.build:
        if args.source.exists():
            raise FileExistsError(
                "The source already exists. Use --export-source or select a new --source path."
            )
        args.source.parent.mkdir(parents=True, exist_ok=True)
        build(args.kit_source.resolve(), args.source.resolve())
    else:
        bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()), load_ui=False)
    export_all(args.out.resolve())
    if args.preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        bpy.context.scene.render.filepath = str(args.preview.resolve())
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
