"""Build the editable pastry tongs, three metre-scale GLBs and the studio thumbnail."""
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = "mall-bakery-serving-tongs"
SOURCES = HERE / "sources" / (SLUG + ".blend")

# Model dimensions are in glTF X/Y/Z. Blender rotates the vertical Y axis into +Z.
def xyz(x, y, z):
    return (x, -z, y)


def finish(name, rgb, roughness, metal=0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*rgb, 1)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*rgb, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metal
    return material


def solid(name, rings, material, parent, collection):
    n = len(rings[0])
    vertices = [point for ring in rings for point in ring]
    faces = [tuple(reversed(range(n)))]
    for row in range(len(rings) - 1):
        for i in range(n):
            a = row * n + i
            b = row * n + (i + 1) % n
            faces.append((a, b, b + n, a + n))
    faces.append(tuple(range(len(vertices) - n, len(vertices))))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    for edge in bm.edges:
        if edge.calc_face_angle(0) > math.radians(50):
            edge.smooth = False
    for face in bm.faces:
        face.smooth = True
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.parent = parent
    return obj


def section(width, height, steps):
    # Round the four corners while retaining faces on the lower and upper flats.
    r = min(width * .27, height * .23)
    for xc, yc, first in [(width / 2 - r, height - r, 0),
                          (-width / 2 + r, height - r, 90),
                          (-width / 2 + r, r, 180),
                          (width / 2 - r, r, 270)]:
        for i in range(steps + 1):
            angle = math.radians(first + 90 * i / steps)
            yield xc + r * math.cos(angle), yc + r * math.sin(angle)


def stations(name, profiles, material, parent, col, steps):
    rings = [[xyz(x, low + y, z + side) for side, y in section(width, high - low, steps)]
             for x, z, low, high, width in profiles]
    return solid(name, rings, material, parent, col)


def make_level(level, palette):
    label = "LOD" + str(level)
    col = bpy.data.collections.new(label)
    bpy.context.scene.collection.children.link(col)
    parent = bpy.data.objects.new("ASSET_BakeryServingTongs_" + label, None)
    col.objects.link(parent)
    steel, wood, silicone, brass = palette
    steps = [4, 2, 1][level]
    # The two handles and the return bend are a continuous formed strip.
    half = [(.068, .0146, .0060), (.055, .0142, .0065), (.025, .0127, .0080),
            (-.025, .0106, .0083), (-.064, .0080, .0062), (-.093, .007, .0022)]
    path = [(x, -z, low) for x, z, low in half]
    arc_steps = [24, 14, 8][level]
    for i in range(1, arc_steps):
        a = math.pi * i / arc_steps
        path.append((-.093 - .007 * math.sin(a), -.007 * math.cos(a),
                     max(0, .0022 * (1 - 1.7 * math.sin(a)))))
    path.extend(reversed(half))
    rings = []
    for i, (x, z, low) in enumerate(path):
        before, after = path[max(0, i - 1)], path[min(len(path) - 1, i + 1)]
        dx, dz = after[0] - before[0], after[1] - before[1]
        length = math.hypot(dx, dz)
        rings.append([xyz(x - dz / length * u, low + y, z + dx / length * u)
                      for u, y in section(.0028, .014, steps)])
    solid("Folded_spring_" + label, rings, steel, parent, col)

    for sign, side in [(-1, "Far"), (1, "Near")]:
        def shape(name, rows, material, resolution=steps):
            return stations(name + "_" + side + "_" + label,
                            [(x, sign * z, low, high, width) for x, z, low, high, width in rows],
                            material, parent, col, resolution)

        shape("Cherry_grip", [(-.066, .0082, .010, .018, .003),
              (-.060, .0096, .0065, .022, .0057), (-.048, .0104, .0058, .0232, .0065),
              (-.025, .0116, .0057, .0233, .0065), (.012, .0132, .0063, .0226, .0063),
              (.028, .0135, .0076, .0211, .0052), (.033, .0135, .010, .018, .0028)], wood)
        # Broad cup noses flare toward the pastry. A rounded end closes each jaw.
        shape("Soft_scalloped_jaw", [(.051, .0142, .0072, .0190, .0041),
              (.057, .0148, .0052, .0210, .0065), (.065, .0159, .0022, .0220, .0080),
              (.075, .0170, 0, .0223, .0098), (.087, .0174, 0, .0228, .0104),
              (.097, .0175, .0010, .0218, .0103), (.105, .0173, .0030, .0198, .0095),
              (.110, .0170, .0057, .0168, .0080), (.1125, .0169, .0085, .0140, .0052),
              (.1130, .0169, .0099, .0126, .0033)], silicone)
        if level < 2:
            for i, x in enumerate([.069, .078, .087, .096, .103]):
                z = .0129 if x < .074 else .0123
                shape("Rounded_contact_rib_" + str(i + 1),
                      [(x - .0014, z, .0073, .0175, .0010),
                       (x - .0008, z, .0052, .0190, .0028),
                       (x + .0008, z, .0052, .0190, .0028),
                       (x + .0014, z, .0073, .0175, .0010)], silicone, 2 if level == 0 else 1)
        if level < 2:
            for i, (x, middle) in enumerate([(-.047, .01045), (.014, .01323)]):
                count = 16 if level == 0 else 8
                rings = []
                for radius, outward in [(.0029, .0024), (.0033, .0034), (.0027, .0038)]:
                    rings.append([xyz(x + radius * math.cos(2 * math.pi * n / count),
                                      .0146 + radius * math.sin(2 * math.pi * n / count),
                                      sign * (middle + outward)) for n in range(count)])
                solid("Flush_pin_" + str(i + 1) + "_" + side + "_" + label,
                      rings, brass, parent, col)
    return col


def export_levels():
    for level in range(3):
        col = bpy.data.collections["LOD" + str(level)]
        col.hide_viewport = False
        # Merge temporary copies by material so a reused utensil costs at most four
        # draws. The saved artist source retains individually editable jaws and pins.
        original = bpy.data.objects["ASSET_BakeryServingTongs_LOD" + str(level)]
        root_name = original.name
        original.name = "SOURCE_" + root_name
        export_root = bpy.data.objects.new(root_name, None)
        bpy.context.scene.collection.objects.link(export_root)
        groups = {}
        for obj in col.objects:
            if obj.type == "MESH":
                mat = obj.data.materials[0]
                groups.setdefault(mat, []).append(obj)
        try:
            for mat, parts in groups.items():
                combined = bmesh.new()
                for part in parts:
                    # Apply edits to object transforms as well as the mesh vertices.
                    piece = part.data.copy()
                    piece.transform(original.matrix_world.inverted() @ part.matrix_world)
                    combined.from_mesh(piece)
                    bpy.data.meshes.remove(piece)
                mesh = bpy.data.meshes.new(mat.name)
                combined.to_mesh(mesh)
                combined.free()
                mesh.materials.append(mat)
                joined = bpy.data.objects.new(mat.name + "_LOD" + str(level), mesh)
                bpy.context.scene.collection.objects.link(joined)
                joined.parent = export_root
            bpy.ops.object.select_all(action="DESELECT")
            export_root.select_set(True)
            for part in export_root.children:
                part.select_set(True)
            suffix = "-lod" + str(level) if level else ""
            bpy.ops.export_scene.gltf(filepath=str(HERE / "exports" / (SLUG + suffix + ".glb")),
                                      export_format="GLB", use_selection=True,
                                      export_yup=True, export_animations=False, export_texcoords=False,
                                      export_cameras=False, export_lights=False, export_extras=False)
        finally:
            for obj in list(export_root.children):
                mesh = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                bpy.data.meshes.remove(mesh)
            bpy.data.objects.remove(export_root, do_unlink=True)
            original.name = root_name
        col.hide_viewport = bool(level)


def studio():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 28
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 800, 600
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 91
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (.42, .47, .51, 1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = .55
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -.00015))
    floor = bpy.context.object
    floor.name = "Studio_surface"
    floor.data.materials.append(finish("Studio pale warm grey", (.58, .54, .46), .62))
    for name, location, power, size in [
            ("Broad key", (-.12, -.16, .22), 1.9, .18),
            ("Strip rim", (.08, .12, .13), 1.0, .14),
            ("Soft fill", (.14, -.02, .15), .6, .12)]:
        bpy.ops.object.light_add(type="AREA", location=location)
        lamp = bpy.context.object
        lamp.name, lamp.data.energy, lamp.data.shape, lamp.data.size = name, power, "DISK", size
        lamp.rotation_euler = (-lamp.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.camera_add(location=(.125, -.175, .185))
    camera = bpy.context.object
    camera.data.type, camera.data.ortho_scale = "ORTHO", .24
    camera.data.clip_start = .001
    camera.rotation_euler = (Vector((.002, 0, .008)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera


def main():
    for name in ["sources", "exports", "previews", "reports"]:
        (HERE / name).mkdir(exist_ok=True)
    if "--export-source" in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCES), load_ui=False)
        export_levels()
        return
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.world = bpy.data.worlds.new("Studio world")
    palette = [finish("Brushed spring stainless", (.47, .53, .55), .28, .84),
               finish("Oiled cherry grip", (.32, .098, .040), .39),
               finish("Evergreen soft pastry tips", (.021, .105, .095), .55),
               finish("Satin brass grip pins", (.52, .34, .14), .30, .72)]
    for level in range(3):
        collection = make_level(level, palette)
        collection.hide_render = bool(level)
        collection.hide_viewport = bool(level)
    studio()
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCES), compress=True)
    export_levels()
    if "--skip-render" not in sys.argv:
        scene.render.filepath = str(HERE / "previews" / (SLUG + ".jpg"))
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
