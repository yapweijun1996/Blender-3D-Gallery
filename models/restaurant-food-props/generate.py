"""Original deterministic restaurant props. Blender 5.2.3; no external assets.

Blender: metres, +Z up, -Y front. GLB: +Y up, +Z front.
Rebuild: blender --background --python generate.py
Export saved edits: append -- --export-source [--skip-render].
"""
from pathlib import Path
import math
import random
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = "restaurant-food-props"
ROOT = "ASSET_RestaurantFoodProps"
SEED = 73129
TAU = math.tau
COLORS = {
    "tray": "315B5C", "rim": "477475", "ceramic": "E5E1CF",
    "teal": "416E70", "broth": "B97936", "noodle": "E8BF6E",
    "wood": "B98750", "wood_light": "D5AD72", "rice": "F1E7CF",
    "green": "4D8949", "light_green": "94B85B", "tomato": "C95C41",
    "crust": "B4773D", "bread": "E9C994", "filling": "C37A4F",
    "dumpling": "E7D2A3", "pleat": "C5AA79", "soup": "C99145",
    "orange": "D69348", "drink": "965A3B", "straw": "D7CBA7",
    "sauce": "784735", "cream": "F4E9D3", "dark": "443A2D",
}


def color(name):
    value = COLORS.get(name, name)
    rgb = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)


class Geometry:
    """Accumulate disconnected closed solids into one editable service mesh."""
    def __init__(self, name, pivot=(0, 0, 0)):
        self.name, self.pivot = name, Vector(pivot)
        self.vertices, self.faces, self.colors = [], [], []

    def add(self, vertices, faces, shade):
        offset = len(self.vertices)
        self.vertices.extend(tuple(Vector(v) - self.pivot) for v in vertices)
        self.faces.extend(tuple(i + offset for i in f) for f in faces)
        self.colors.extend([color(shade)] * len(faces))

    def lathe(self, xy, z, profile, shade, segments=32):
        vertices, rings, faces = [], [], []
        for row, (radius, height) in enumerate(profile):
            if row == len(profile) - 1 and profile[0] == profile[-1]:
                rings.append(rings[0])
                continue
            if radius == 0:
                rings.append([len(vertices)])
                vertices.append((xy[0], xy[1], z + height))
            else:
                rings.append(list(range(len(vertices), len(vertices) + segments)))
                vertices.extend((xy[0] + radius * math.cos(TAU * j / segments),
                                 xy[1] + radius * math.sin(TAU * j / segments), z + height)
                                for j in range(segments))
        for a, b in zip(rings, rings[1:]):
            for j in range(segments):
                k = (j + 1) % segments
                if len(a) == 1:
                    faces.append((a[0], b[k], b[j]))
                elif len(b) == 1:
                    faces.append((a[j], a[k], b[0]))
                else:
                    faces.append((a[j], a[k], b[k], b[j]))
        self.add(vertices, faces, shade)

    def bead(self, center, radii, shade, segments=12, rings=5):
        vertices = [(center[0], center[1], center[2] - radii[2])]
        for row in range(1, rings):
            phi = -math.pi / 2 + math.pi * row / rings
            vertices.extend((center[0] + radii[0] * math.cos(phi) * math.cos(TAU * j / segments),
                             center[1] + radii[1] * math.cos(phi) * math.sin(TAU * j / segments),
                             center[2] + radii[2] * math.sin(phi)) for j in range(segments))
        vertices.append((center[0], center[1], center[2] + radii[2]))
        faces = [(0, 1 + (j + 1) % segments, 1 + j) for j in range(segments)]
        for row in range(rings - 2):
            for j in range(segments):
                a, b = 1 + row * segments + j, 1 + row * segments + (j + 1) % segments
                faces.append((a, b, b + segments, a + segments))
        last = 1 + (rings - 2) * segments
        faces.extend((last + j, last + (j + 1) % segments, len(vertices) - 1) for j in range(segments))
        self.add(vertices, faces, shade)

    def tube(self, points, radius, shade, sides=6, tip=None):
        vertices, faces = [], []
        previous_axis = None
        closed = (Vector(points[0]) - Vector(points[-1])).length < 1e-8
        if closed:
            points = points[:-1]
        for i, p in enumerate(points):
            before = points[(i - 1) % len(points)] if closed else points[max(i - 1, 0)]
            after = points[(i + 1) % len(points)] if closed else points[min(i + 1, len(points) - 1)]
            tangent = Vector(after) - Vector(before)
            tangent.normalize()
            if previous_axis is None:
                ref = Vector((0, 0, 1)) if abs(tangent.z) < .9 else Vector((1, 0, 0))
                a = tangent.cross(ref).normalized()
            else:
                # Transport the frame continuously, avoiding twisted/bow-tie quads.
                a = (previous_axis - tangent * previous_axis.dot(tangent)).normalized()
            previous_axis = a
            b = tangent.cross(a).normalized()
            r = radius if tip is None else radius + (tip - radius) * i / (len(points) - 1)
            vertices.extend(tuple(Vector(p) + r * (a * math.cos(TAU * j / sides) + b * math.sin(TAU * j / sides)))
                            for j in range(sides))
        if not closed:
            faces.append(tuple(reversed(range(sides))))
        for i in range(len(points) if closed else len(points) - 1):
            for j in range(sides):
                a, b = i * sides + j, i * sides + (j + 1) % sides
                faces.append((a, b, (b + sides) % len(vertices), (a + sides) % len(vertices)))
        if not closed:
            faces.append(tuple((len(points) - 1) * sides + j for j in range(sides)))
        self.add(vertices, faces, shade)

    def triangle_prism(self, xy, z, size, height, shade, angle=0):
        points = [(-size / 2, -size / 2), (size / 2, -size / 2), (-size / 2, size / 2)]
        points = [(xy[0] + x * math.cos(angle) - y * math.sin(angle),
                   xy[1] + x * math.sin(angle) + y * math.cos(angle)) for x, y in points]
        vertices = [(x, y, zz) for zz in (z, z + height) for x, y in points]
        self.add(vertices, [(2, 1, 0), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)], shade)

    def rectangle_profile(self, profile, shade, corner=.025):
        vertices, faces = [], []
        count = 24
        for width, depth, z in profile:
            for cx, cy, start in ((width / 2 - corner, depth / 2 - corner, 0),
                                  (-width / 2 + corner, depth / 2 - corner, math.pi / 2),
                                  (-width / 2 + corner, -depth / 2 + corner, math.pi),
                                  (width / 2 - corner, -depth / 2 + corner, 3 * math.pi / 2)):
                vertices.extend((cx + corner * math.cos(start + j * math.pi / 10),
                                 cy + corner * math.sin(start + j * math.pi / 10), z) for j in range(6))
        faces.append(tuple(reversed(range(count))))
        for row in range(len(profile) - 1):
            for j in range(count):
                a, b = row * count + j, row * count + (j + 1) % count
                faces.append((a, b, b + count, a + count))
        faces.append(tuple((len(profile) - 1) * count + j for j in range(count)))
        self.add(vertices, faces, shade)

    def object(self, parent, material):
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.update()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        colors = mesh.color_attributes.new(name="Color", type="FLOAT_COLOR", domain="CORNER")
        for polygon, rgba in zip(mesh.polygons, self.colors):
            for loop in polygon.loop_indices:
                colors.data[loop].color = rgba
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = self.pivot
        obj.parent = parent
        mesh.materials.append(material)
        obj["role"] = self.name
        return obj


def plate(g, x, y, radius, z=.013):
    g.lathe((x, y), z, [(0, 0), (radius * .48, 0), (radius * .50, .004),
                        (radius * .89, .009), (radius, .019), (radius, .023),
                        (radius * .91, .023), (radius * .72, .011), (0, .011)], "ceramic")


def bowl(g, x, y, radius, height, shade="ceramic", z=.013):
    g.lathe((x, y), z, [(0, 0), (radius * .43, 0), (radius * .46, .006),
                        (radius * .76, height * .28), (radius * .98, height * .83),
                        (radius, height), (radius * .94, height + .0015),
                        (radius * .91, height * .84), (radius * .68, height * .29),
                        (radius * .35, .009), (0, .009)], shade)


def garnish(g, x, y, z, rng, spread=.04, count=8):
    for _ in range(count):
        xx, yy = x + rng.uniform(-spread, spread), y + rng.uniform(-spread, spread)
        g.bead((xx, yy, z), (.006, .004, .0025), "green", segments=6, rings=3)


def palette_material():
    material = bpy.data.materials.new("Restaurant shared vertex palette")
    material.use_nodes = True
    material.diffuse_color = color("ceramic")
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = .58
    bsdf.inputs["Specular IOR Level"].default_value = .28
    vertex = material.node_tree.nodes.new("ShaderNodeVertexColor")
    vertex.layer_name = "Color"
    material.node_tree.links.new(vertex.outputs["Color"], bsdf.inputs["Base Color"])
    return material


def build():
    rng = random.Random(SEED)
    root = bpy.data.objects.new(ROOT, None)
    bpy.context.scene.collection.objects.link(root)
    root["units"] = "metres"
    root["front_axis"] = "Blender -Y / glTF +Z"
    root["seed"] = SEED
    root["service_items"] = 10
    material = palette_material()
    tray = Geometry("TRAY_Serving")
    tray.rectangle_profile([(0.96, .56, 0), (1, .60, .007), (1, .60, .028),
                            (.984, .584, .032), (.955, .555, .013)], "tray")
    tray.object(root, material)

    x, y = -.34, .12
    g = Geometry("DISH_Noodles_Chopsticks", (x, y, .013))
    bowl(g, x, y, .101, .077, "teal")
    g.lathe((x, y), .076, [(0, 0), (.086, 0), (.086, .005), (0, .005)], "broth")
    for row in range(9):
        offset = (row - 4) * .014
        length = math.sqrt(max(.001, .073 ** 2 - offset ** 2))
        points = [(x - length + 2 * length * k / 19,
                   y + offset + .004 * math.sin(k * .85 + row),
                   .087 + .002 * math.cos(k * .65 + row)) for k in range(20)]
        g.tube(points, .0025, "noodle")
    for dx in (-.024, .010):
        g.bead((x + dx, y + .024, .095), (.016, .021, .009), "filling")
    garnish(g, x, y, .096, rng, .055)
    for i in range(2):
        g.tube([(x - .104, y + .054 + i * .017, .104),
                (x + .105, y - .035 + i * .017, .107)], .0034, "wood_light", sides=8, tip=.0021)
    g.object(root, material)

    x, y = -.105, .12
    g = Geometry("DISH_Rice_Plate", (x, y, .013))
    plate(g, x, y, .105)
    g.lathe((x - .012, y + .005), .025,
            [(0, 0), (.052, 0), (.055, .006), (.049, .025),
             (.036, .041), (.019, .049), (0, .052)], "rice", segments=24)
    for _ in range(36):
        a, rr = rng.uniform(0, TAU), math.sqrt(rng.random()) * .047
        dx, dy = rr * math.cos(a), rr * math.sin(a)
        zz = .025 + .052 * math.sqrt(max(0, 1 - (dx / .056) ** 2 - (dy / .055) ** 2))
        g.bead((x - .012 + dx, y + .005 + dy, zz), (.0035, .0015, .0012), "cream", segments=6, rings=3)
    for k in range(3):
        g.lathe((x + .049, y - .029 + k * .025), .031 + k * .002,
                [(0, 0), (.022, 0), (.022, .005), (0, .005)], "green", segments=16)
        g.lathe((x + .049, y - .029 + k * .025), .037 + k * .002,
                [(0, 0), (.017, 0), (.017, .001), (0, .001)], "light_green", segments=16)
    garnish(g, x - .012, y, .080, rng, .025, 5)
    g.object(root, material)

    x, y = .135, .12
    g = Geometry("DISH_Dumplings_Basket", (x, y, .013))
    bowl(g, x, y, .096, .038, "wood")
    g.lathe((x, y), .042, [(0, 0), (.081, 0), (.081, .004), (0, .004)], "wood_light")
    for level in (.025, .038, .049):
        points = [(x + .095 * math.cos(TAU * k / 48), y + .095 * math.sin(TAU * k / 48), level) for k in range(49)]
        g.tube(points, .002, "wood_light")
    for k in range(16):
        a = k * TAU / 16
        g.tube([(x + r * math.cos(a), y + r * math.sin(a), zz)
                for r, zz in ((.077, .026), (.090, .036), (.095, .049))], .0014, "wood_light")
    for dx, dy in ((-.034, -.025), (.032, -.025), (0, .029)):
        cx, cy = x + dx, y + dy
        g.bead((cx, cy, .061), (.028, .017, .019), "dumpling", segments=16, rings=6)
        seam = [(cx + .026 * math.cos(math.pi * k / 12), cy,
                 .057 + .026 * math.sin(math.pi * k / 12)) for k in range(13)]
        g.tube(seam, .0018, "dumpling")
        for j in range(7):
            xx = (j - 3) * .0065
            zz = .057 + .026 * math.sqrt(1 - (xx / .026) ** 2)
            g.tube([(cx + xx - .0025, cy - .012, zz - .009),
                    (cx + xx, cy, zz + .001),
                    (cx + xx + .0025, cy + .012, zz - .009)], .0015, "pleat", sides=5)
    g.object(root, material)

    x, y = -.35, -.145
    g = Geometry("DISH_Sandwich_Plate", (x, y, .013))
    plate(g, x, y, .104)
    for cx, cy, angle in ((x - .018, y - .008, -.15), (x + .034, y + .021, math.pi - .15)):
        g.triangle_prism((cx, cy), .025, .107, .012, "crust", angle)
        g.triangle_prism((cx, cy), .028, .099, .009, "bread", angle)
        g.triangle_prism((cx, cy), .039, .110, .004, "green", angle)
        g.triangle_prism((cx, cy), .044, .105, .005, "tomato", angle)
        g.triangle_prism((cx, cy), .050, .107, .012, "crust", angle)
        g.triangle_prism((cx, cy), .053, .099, .011, "bread", angle)
    g.object(root, material)

    x, y = -.125, -.145
    g = Geometry("DISH_Soup_Bowl", (x, y, .013))
    bowl(g, x, y, .083, .059)
    g.lathe((x, y), .060, [(0, 0), (.070, 0), (.070, .005), (0, .005)], "soup")
    garnish(g, x, y, .068, rng, .043, 11)
    for dx, dy in ((-.030, .020), (.020, -.021), (.027, .028)):
        g.bead((x + dx, y + dy, .066), (.009, .008, .004), "cream", segments=8, rings=3)
    g.object(root, material)

    for name, x, y, liquid in (("DRINK_Citrus", .355, .175, "orange"), ("DRINK_Tea", .355, .035, "drink")):
        g = Geometry(name, (x, y, .013))
        g.lathe((x, y), .013, [(0, 0), (.028, 0), (.030, .006), (.039, .132),
                              (.040, .139), (.036, .141), (.034, .132), (.025, .007), (0, .007)], "ceramic", segments=24)
        g.lathe((x, y), .128, [(0, 0), (.034, 0), (.034, .005), (0, .005)], liquid, segments=24)
        g.lathe((x, y), .061, [(.0315, 0), (.033, 0), (.035, .027), (.0335, .027), (.0315, 0)], "teal", segments=24)
        g.tube([(x + .008, y, .135), (x + .008, y, .209), (x + .032, y - .012, .227)], .0028, "straw", sides=8)
        g.object(root, material)

    x, y = .075, -.145
    g = Geometry("DISH_Salad_Bowl", (x, y, .013))
    bowl(g, x, y, .070, .038, "teal")
    for k in range(10):
        a = k * 2.4
        rr = .045 * math.sqrt((k + 1) / 10)
        g.bead((x + rr * math.cos(a), y + rr * math.sin(a), .051),
               (.022, .016, .010), "light_green" if k % 2 else "green", segments=7, rings=3)
    for dx, dy in ((-.021, -.020), (.027, -.010), (.003, .027)):
        g.bead((x + dx, y + dy, .062), (.013, .012, .010), "tomato", segments=10, rings=4)
    g.object(root, material)

    x, y = .25, -.145
    g = Geometry("DISH_Pastry_Plate", (x, y, .013))
    plate(g, x, y, .075)
    for k in range(7):
        t = (k - 3) / 3
        g.bead((x + t * .044, y - .018 * t * t, .038 + .007 * (1 - t * t)),
               (.017, .025 * (1 - .44 * abs(t)), .017 * (1 - .35 * abs(t))),
               "wood_light" if k % 2 else "crust", segments=10, rings=4)
    g.object(root, material)

    x, y = .407, -.145
    g = Geometry("DISH_Sauce_Ramekin", (x, y, .013))
    bowl(g, x, y, .039, .027)
    g.lathe((x, y), .034, [(0, 0), (.032, 0), (.032, .003), (0, .003)], "sauce", segments=24)
    for k in range(5):
        g.bead((x + .017 * math.cos(k * 2.4), y + .017 * math.sin(k * 2.4), .038),
               (.002, .001, .0008), "cream", segments=6, rings=3)
    g.object(root, material)
    return root, material


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def studio(material):
    scene = bpy.context.scene
    ground = Geometry("STUDIO_Ground")
    ground.rectangle_profile([(200, 200, -.012), (200, 200, -.002)], "D4D9D3")
    ground.object(None, material)
    scene.world = bpy.data.worlds.new("Neutral studio")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (.32, .36, .35, 1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = .5
    for name, position, energy, size in (("Key", (-1.8, -2.3, 3.5), 230, 2),
                                         ("Fill", (2, -1, 2), 100, 2),
                                         ("Rim", (.2, 2.4, 3), 180, 1.8)):
        bpy.ops.object.light_add(type="AREA", location=position)
        lamp = bpy.context.object
        lamp.name = "STUDIO_" + name
        lamp.data.energy, lamp.data.size = energy, size
        aim(lamp, (0, 0, 0))
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.name = "STUDIO_Camera"
    scene.camera.data.type = "ORTHO"
    scene.camera.data.ortho_scale = 1.28
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"


def export(destination):
    bpy.ops.object.select_all(action="DESELECT")
    root = bpy.data.objects[ROOT]
    root.select_set(True)
    for obj in root.children_recursive:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(destination), export_format="GLB", use_selection=True,
                              export_apply=True, export_yup=True, export_animations=False,
                              export_extras=True, export_texcoords=False, export_cameras=False,
                              export_lights=False)


def render_views():
    scene = bpy.context.scene
    target = Vector((0, 0, .055))
    for name, delta in (("hero", (1.15, -1.9, 2.2)), ("front", (0, -2.8, .6)),
                         ("side", (2.8, 0, .6)), ("3q", (-1.35, -1.8, 1.7))):
        scene.camera.location = target + Vector(delta)
        aim(scene.camera, target)
        scene.render.filepath = str(HERE / "previews" / (name + ".png"))
        bpy.ops.render.render(write_still=True)


def main():
    for folder in ("sources", "exports", "previews", "reports", "metadata"):
        (HERE / folder).mkdir(parents=True, exist_ok=True)
    if "--export-source" in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / "sources" / (SLUG + ".blend")))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        scene = bpy.context.scene
        scene.unit_settings.system = "METRIC"
        scene.unit_settings.scale_length = 1
        _, material = build()
        studio(material)
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "sources" / (SLUG + ".blend")), compress=True)
    export(HERE / "exports" / "optimized.glb")
    if "--skip-render" not in sys.argv:
        render_views()


if __name__ == "__main__":
    main()
