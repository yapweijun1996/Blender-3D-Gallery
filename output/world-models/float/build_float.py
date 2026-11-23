"""Build The Float, export it, and render six views of the reimported GLB."""

from math import cos, pi, sin
from pathlib import Path
import sys

import bpy
from mathutils import Vector


HERE = Path(__file__).resolve().parent
DECK_Z = 1.2
PALETTE = {
    "plate": ("b1b6b5", 0.12, 0.83),
    "metal": ("687681", 0.55, 0.45),
    "chrome": ("a7b4bc", 0.58, 0.37),
    "trim": ("343d42", 0.24, 0.72),
    "rubber": ("181f22", 0.0, 0.92),
    "roof": ("e1e4e4", 0.10, 0.64),
    "wall": ("b7c2c6", 0.18, 0.73),
    "paint": ("aa2337", 0.03, 0.62),
    "glass": ("242d38", 0.26, 0.35),
    "light": ("d6e4ed", 0.15, 0.29),
}


def linear_rgb(hex_color):
    srgb = [int(hex_color[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    return tuple(
        t / 12.92 if t < 0.04045 else ((t + 0.055) / 1.055) ** 2.4
        for t in srgb
    )


def material(name, color, metal, roughness):
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    rgba = (*linear_rgb(color), 1)
    result.diffuse_color = rgba
    shader = result.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = rgba
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = roughness
    return result


class Part:
    def __init__(self, name):
        self.name = name
        self.vertices = []
        self.faces = []
        self.face_materials = []

    def prism(self, bottom, top, wall, cap=None, closed=True):
        offset = len(self.vertices)
        count = len(bottom)
        self.vertices.extend(bottom)
        self.vertices.extend(top)
        if closed:
            self.faces.append(tuple(offset + i for i in reversed(range(count))))
            self.face_materials.append(wall)
            self.faces.append(tuple(offset + count + i for i in range(count)))
            self.face_materials.append(cap or wall)
        for i in range(count):
            a = offset + i
            b = offset + (i + 1) % count
            self.faces.append((a, b, b + count, a + count))
            self.face_materials.append(wall)

    def extrusion(self, outline, low, high, wall, cap=None):
        self.prism(
            [(x, y, low) for x, y in outline],
            [(x, y, high) for x, y in outline],
            wall, cap,
        )

    def box(self, center, size, wall, cap=None):
        x, y, z = center
        dx, dy, dz = [value / 2 for value in size]
        self.extrusion(
            [(x - dx, y - dy), (x + dx, y - dy), (x + dx, y + dy), (x - dx, y + dy)],
            z - dz, z + dz, wall, cap,
        )

    def member(self, a, b, width, mat, *, depth=None, closed=True, triangular=False):
        start, end = Vector(a), Vector(b)
        direction = (end - start).normalized()
        reference = Vector((0, 0, 1)) if abs(direction.z) < 0.95 else Vector((1, 0, 0))
        u = reference.cross(direction).normalized() * (width / 2)
        v = direction.cross(u).normalized() * ((depth or width) / 2)
        offsets = (-u - v, u - v, u + v, -u + v)
        if triangular:
            offsets = (-u - v, u - v, v)
        self.prism([start + d for d in offsets], [end + d for d in offsets], mat, closed=closed)

    def pipe(self, x, y, z0, z1, radius, mat, sides=12):
        self.extrusion([
            (x + radius * cos(i * 2 * pi / sides), y + radius * sin(i * 2 * pi / sides))
            for i in range(sides)
        ], z0, z1, mat)

    def build(self, materials):
        names = list(dict.fromkeys(self.face_materials))
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.update()
        for name in names:
            mesh.materials.append(materials[name])
        material_indices = {name: i for i, name in enumerate(names)}
        for face, name in zip(mesh.polygons, self.face_materials):
            face.material_index = material_indices[name]
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.collection.objects.link(obj)
        return obj


def clipped_rectangle(x, y, dx, dy, cut):
    return [
        (x - dx + cut, y - dy), (x + dx - cut, y - dy),
        (x + dx, y - dy + cut), (x + dx, y + dy - cut),
        (x + dx - cut, y + dy), (x - dx + cut, y + dy),
        (x - dx, y + dy - cut), (x - dx, y - dy + cut),
    ]


def platform():
    deck = Part("Platform_Deck")
    pontoons = Part("Steel_Pontoon_Array")
    edge = Part("Edge_Fascia_and_Fenders")
    for row in range(3):
        for column in range(5):
            x = (column - 2) * 16.6
            y = (row - 1) * 40
            # Keep the 40 mm joints internal to the nominal 120 by 83 metre deck.
            left = x - (8.3 if column == 0 else 8.28)
            right = x + (8.3 if column == 4 else 8.28)
            near = y - (20 if row == 0 else 19.98)
            far = y + (20 if row == 2 else 19.98)
            outline = [(left, near), (right, near), (right, far), (left, far)]
            deck.extrusion(outline, 1.09, DECK_Z, "plate")
            pontoons.extrusion(outline, 0.03, 1.09, "metal")
            pontoons.extrusion(outline, -0.285, 0.03, "trim")

    for side in (-1, 1):
        edge.box((41.425 * side, 0, 0.96), (0.15, 119.96, 0.29), "trim")
        edge.box((0, 59.925 * side, 0.96), (82.70, 0.15, 0.29), "trim")
        for y in (-50, -38, -25, -13, 0, 13, 25, 38, 50):
            edge.box((41.54 * side, y, 0.37), (0.22, 0.37, 0.64), "rubber")
        for x in (-33.2, -16.6, 0, 16.6, 33.2):
            edge.box((x, 60.04 * side, 0.40), (0.36, 0.22, 0.6), "rubber")
    for y in (-20, 20):
        for x in (-33.2, -16.6, 0, 16.6, 33.2):
            deck.box((x + 0.14, y, 1.201), (0.22, 0.56, 0.012), "metal")
    return deck, pontoons, edge


def moorings():
    mooring = Part("Detachable_Mooring_Pylons")
    points = [
        (-41.92, -30, 0.58, 1, 0), (-41.92, 28, 0.58, 1, 0),
        (41.92, -30, 0.58, -1, 0), (41.92, 28, 0.58, -1, 0),
        (24, -61.60, 0.90, 0, 1), (-24, 61.60, 0.90, 0, -1),
    ]
    for x, y, radius, ix, iy in points:
        mooring.pipe(x, y, -2.4, 4.05, radius * 0.92, "metal", 8)
        mooring.pipe(x, y, 3.95, 4.17, radius, "chrome", 8)
        for direction in (-1, 1):
            dx, dy = -iy * direction, ix * direction
            ox, oy = x + dx * (radius + 0.20), y + dy * (radius + 0.20)
            mooring.pipe(ox, oy, 0.50, 1.34, 0.22, "rubber", 6)
            width, length = (0.96, 0.36) if ix else (0.36, 2.03)
            inset = 0.43 if ix else 1.10
            mooring.box((ox + ix * inset, oy + iy * inset, 0.87),
                        (width, length, 0.29), "metal")
    return mooring


def safety_rails():
    rails = Part("Perimeter_Guardrails")
    # Open sections are reserved for boarding, handling, and event access.
    runs = [
        ((-40.95, -56), (-40.95, -35)), ((-40.95, -24), (-40.95, -5)),
        ((-40.95, 6), (-40.95, 22)), ((-40.95, 33), (-40.95, 58)),
        ((40.95, -56), (40.95, -35)), ((40.95, -25), (40.95, 22)),
        ((40.95, 33), (40.95, 58)), ((-40.95, -59.4), (-31, -59.4)),
        ((-16.5, -59.4), (16.5, -59.4)), ((30, -59.4), (40.95, -59.4)),
        ((-40.95, 59.4), (-29, 59.4)), ((-18, 59.4), (40.95, 59.4)),
    ]
    for a, b in runs:
        start, stop = Vector(a), Vector(b)
        count = round((stop - start).length / 4.6)
        for i in range(count + 1):
            x, y = start.lerp(stop, i / count)
            rails.member((x, y, 1.2), (x, y, 2.31), 0.073, "metal", closed=False)
        for z in (1.73, 2.31):
            rails.member((*a, z), (*b, z), 0.069, "chrome")
    return rails


def lattice(part, start, stop, u, v, bays, chord, brace, mat="metal"):
    a, b = Vector(start), Vector(stop)
    corners = [u + v, -u + v, -u - v, u - v]
    for offset in corners:
        part.member(a + offset, b + offset, chord, mat)
    # Brace ends terminate inside the closed chords, so hidden caps can be omitted.
    for face, c0 in enumerate(corners):
        c1 = corners[(face + 1) % 4]
        for i in range(bays + 1):
            point = a.lerp(b, i / bays)
            part.member(point + c0, point + c1, brace, mat, closed=False, triangular=True)
        for i in range(bays):
            p0 = a.lerp(b, i / bays)
            p1 = a.lerp(b, (i + 1) / bays)
            left, right = (c0, c1) if (face + i) % 2 == 0 else (c1, c0)
            part.member(p0 + left, p1 + right, brace, mat, closed=False, triangular=True)


def main_stage():
    frame = Part("Main_Stage_Proscenium")
    for x in (-28.6, 28.6):
        lattice(frame, (x, 45, 1.35), (x, 45, 29.85),
                Vector((1.02, 0, 0)), Vector((0, 1.22, 0)), 6, 0.34, 0.21)
        frame.box((x, 45, 1.37), (3.0, 3.6, 0.34), "trim")
        x += 1.02 if x > 0 else -1.02
        frame.box((x, 55, 1.36), (2.4, 2.8, 0.32), "trim")
        frame.member((x, 55, 1.55), (x, 55, 21.3), 0.47, "metal")
        frame.member((x, 55, 1.55), (x, 46.19, 27.8), 0.38, "metal")
        frame.member((x, 55, 21.3), (x, 46.19, 28.5), 0.35, "metal")
        frame.member((x, 55, 11), (x, 46.19, 11), 0.28, "metal")
        frame.member((x, 55, 21.3), (x, 46.19, 21.3), 0.28, "metal")

    lattice(frame, (-30.0, 45, 29.75), (30.0, 45, 29.75),
            Vector((0, 1.18, 0)), Vector((0, 0, 1.25)), 10, 0.40, 0.21)
    for z in (11, 17.8, 23.6):
        frame.member((-28.6, 45.75, z), (28.6, 45.75, z), 0.27, "metal")
    for x in (-18.7, -9.4, 0, 9.4, 18.7):
        frame.member((x, 45.75, 10.8), (x, 45.75, 29.7), 0.25, "metal")
        for z in (11, 17.8, 23.6):
            frame.member((x, 44.17, z), (x, 45.75, z), 0.19, "metal")
    for z in (7.8, 25.0):
        frame.box((0, 43.23, z), (60.4, 0.51, 0.42), "roof")
    for side in (-1, 1):
        frame.box((30.07 * side, 43.23, 16.43), (0.45, 0.51, 17.15), "roof")
    return frame


def stage_floor():
    floor = Part("Performance_Riser_and_Stairs")
    floor.extrusion(clipped_rectangle(0, 39.15, 33.9, 10.9, 3.3), 1.2, 2.03, "wall", "roof")
    floor.extrusion(clipped_rectangle(0, 39.15, 33.93, 10.93, 3.3), 1.35, 1.83, "paint")
    floor.extrusion(clipped_rectangle(0, 39.15, 33.95, 10.95, 3.3), 1.88, 1.97, "roof")
    floor.extrusion(clipped_rectangle(0, 43.6, 29.7, 5.1, 2.0), 2.03, 2.27, "wall", "plate")
    for x in (-21, 0, 21):
        for index in range(4):
            rise = 0.22 * (index + 1)
            floor.box((x, 26.50 + index * 0.5, DECK_Z + rise / 2),
                      (5.8 if x else 10.5, 0.5, rise), "wall", "roof")
    return floor


def screens():
    main = Part("LED_Screen_Main")
    # Cabinet divisions are on the back. The dark face represents an idle LED wall.
    main.box((0, 43.82, 16.42), (60.0, 0.82, 15.0), "trim")
    main.box((0, 43.38, 16.42), (59.82, 0.06, 14.80), "glass")
    for x in range(-27, 30, 3):
        main.box((x, 44.3, 16.42), (0.075, 0.16, 14.86), "metal")
    for z in (10.4, 13.4, 16.4, 19.4, 22.4):
        main.box((0, 44.4, z), (59.85, 0.20, 0.09), "metal")

    wings = Part("LED_Screens_Wings")
    surrounds = Part("Stage_Wing_Cladding")
    for sign in (-1, 1):
        x = 33.1 * sign
        wings.box((x, 43.1, 15.9), (4.15, 0.63, 10.9), "trim")
        wings.box((x, 42.76, 15.9), (3.94, 0.055, 10.63), "glass")
        panel = [(-2.25, 10.22), (2.30, 10.22), (2.72, 11.35),
                 (2.72, 21.3), (1.18, 23.35), (-2.25, 21.48)]
        # These raked returns sit behind the outer video panels.
        points = [(x + sign * dx, z) for dx, z in panel]
        if sign == 1:
            points.reverse()
        surrounds.prism([(px, 43.62, pz) for px, pz in points],
                        [(px, 43.89, pz) for px, pz in points], "roof")
        surrounds.member((x + sign * 2.38, 43.52, 11.5),
                         (x + sign * 2.54, 43.52, 20.7), 0.41, "paint", depth=0.20)
        for z in (15.1, 20.2):
            surrounds.member((x, 43.88, z), (sign * 37.2, 47.15, z), 0.20, "metal")
    return main, wings, surrounds


def side_tower(sign, side):
    x = sign * 37.6
    tower = Part(f"Stage_Tower_{side}")
    lattice(tower, (x, 44.1, 1.55), (x, 44.1, 25.88),
            Vector((1.16, 0, 0)), Vector((0, 1.27, 0)), 6, 0.25, 0.145)
    tower.box((x, 44.1, 1.39), (3.65, 3.65, 0.38), "trim")
    tower.box((x, 44.1, 26.07), (2.73, 2.85, 0.26), "metal")
    for z in (9.55, 17.6, 25.48):
        tower.box((x, 44.1, z), (2.2, 2.4, 0.10), "plate")
    for offset, index in enumerate(range(5)):
        # The line-array cabinets pull in toward the stage as the array curves.
        tower.box((x - sign * offset * 0.092, 42.50 - offset * 0.12, 20.7 - index * 0.68),
                  (1.18, 0.77, 0.61), "rubber")
    return tower


def overhead():
    rig = Part("Overhead_Lighting_Trusses")
    lamps = Part("Lighting_Fixtures")
    span = 37.6
    for y in (42.7, 37.55):
        lattice(rig, (-span, y, 24.25), (span, y, 24.25),
                Vector((0, 0.47, 0)), Vector((0, 0, 0.56)), 8, 0.20, 0.106)

    for x in (-span, -28.6, -15.0, 0, 15.0, 28.6, span):
        rig.member((x, 37.1, 24.8), (x, 45.25, 24.8), 0.22, "metal")
        rig.member((x, 37.1, 23.7), (x, 45.25, 23.7), 0.18, "metal")
        rig.member((x, 37.1, 23.7), (x, 43.15, 24.8), 0.15, "metal")
        if abs(x) == span:
            rig.member((x, 43, 20.5), (x, 37.2, 23.7), 0.29, "metal")
    for y, xs in ((36.99, range(-32, 33, 4)), (42.14, range(-27, 28, 6))):
        for x in xs:
            center = (x, y, 23.38)
            lamps.box(center, (0.46, 0.55, 0.61), "trim")
            lamps.box((x, y - 0.29, 23.33), (0.32, 0.045, 0.30), "light")
    return rig, lamps


def create_model():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    assert bpy.app.version == (5, 1, 2), bpy.app.version_string
    bpy.context.scene.unit_settings.system = "METRIC"
    materials = {name: material(name, *spec) for name, spec in PALETTE.items()}
    parts = [
        *platform(), moorings(), safety_rails(), stage_floor(), main_stage(),
        side_tower(-1, "Left"), side_tower(1, "Right"), *overhead(), *screens(),
    ]
    for part in parts:
        part.build(materials)
    bpy.ops.export_scene.gltf(
        filepath=str(HERE / "float.glb"), export_format="GLB", export_yup=True,
        export_animations=False, export_skins=False, export_cameras=False,
        export_lights=False, export_texcoords=False,
    )


def render_review():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(HERE / "float.glb"))
    scene = bpy.context.scene
    bounds = [
        obj.matrix_world @ Vector(corner)
        for obj in scene.objects if obj.type == "MESH"
        for corner in obj.bound_box
    ]
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    scene.render.resolution_percentage = 100
    scene.render.resolution_x = 720
    scene.render.resolution_y = 500
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "AgX"

    world = bpy.data.worlds.new("Review sky")
    scene.world = world
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.54, 0.66, 0.82, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.52

    bpy.ops.mesh.primitive_plane_add(size=6000)
    water = bpy.context.object
    water_material = material("Review water", "397183", 0.13, 0.39)
    water.data.materials.append(water_material)
    sun = bpy.data.lights.new("Review sun", "SUN")
    sun.energy = 2.15
    sun.angle = 0.095
    source = bpy.data.objects.new("Review sun", sun)
    scene.collection.objects.link(source)
    source.rotation_euler = Vector((0.60, 0.48, -0.76)).to_track_quat("-Z", "Y").to_euler()

    lens = bpy.data.cameras.new("Review camera")
    lens.type = "ORTHO"
    lens.clip_end = 4000
    camera = bpy.data.objects.new("Review camera", lens)
    scene.collection.objects.link(camera)
    scene.camera = camera

    renders = HERE / ".review"
    renders.mkdir(exist_ok=True)
    views = (
        ("iso", (1, -1.34, 0.95)), ("front", (0, -1, 0.10)), ("side_left", (-1, 0, 0.10)),
        ("top", (0, 0, 1)), ("rear", (0, 1, 0.12)), ("side_right", (1, 0, 0.10)),
    )
    aspect = scene.render.resolution_x / scene.render.resolution_y
    for name, coordinates in views:
        direction = Vector(coordinates).normalized()
        rotation = (-direction).to_track_quat("-Z", "Y")
        right = rotation @ Vector((1, 0, 0))
        up = rotation @ Vector((0, 1, 0))
        horizontal = [right.dot(point) for point in bounds]
        vertical = [up.dot(point) for point in bounds]
        center = right * ((min(horizontal) + max(horizontal)) / 2)
        center += up * ((min(vertical) + max(vertical)) / 2)
        camera.rotation_euler = rotation.to_euler()
        camera.location = center + direction * 680
        lens.ortho_scale = max(max(horizontal) - min(horizontal),
                               (max(vertical) - min(vertical)) * aspect) * 1.12
        scene.render.filepath = str(renders / f"{name}.png")
        bpy.ops.render.render(write_still=True)


if "--" not in sys.argv or "--render-only" not in sys.argv[sys.argv.index("--") + 1:]:
    create_model()
render_review()
