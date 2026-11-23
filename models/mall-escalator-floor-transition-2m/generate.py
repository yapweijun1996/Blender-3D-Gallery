"""Build or re-export an original two-metre escalator terminal closure in metres."""

import argparse
import math
import sys
from itertools import product
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = "mall-escalator-floor-transition-2m"
SOURCE = HERE / "sources" / (SLUG + ".blend")
LEVELS = ("LOD0", "LOD1", "LOD2")
FINISHES = (
    ("Brushed terminal steel", "98A5A3", 0.70, 0.36),
    ("Champagne shoulder wear plate", "A58B64", 0.64, 0.35),
    ("Graphite traction inlay", "414C4B", 0.13, 0.59),
    ("Mineral bedding", "777872", 0.07, 0.76),
    ("Brushed fixing steel", "C3C7BB", 0.75, 0.32),
    ("Shadow gasket", "505653", 0.12, 0.55),
)
STEEL, BRONZE, GRIP, BED, FIXING, SEAL = range(len(FINISHES))


def material(name, hex_rgb, metallic, roughness):
    srgb = [int(hex_rgb[start : start + 2], 16) / 255 for start in (0, 2, 4)]
    linear = []
    for channel in srgb:
        if channel <= 0.04045:
            linear.append(channel / 12.92)
        else:
            linear.append(((channel + 0.055) / 1.055) ** 2.4)
    rgba = (*linear, 1)
    finish = bpy.data.materials.new(name)
    finish.diffuse_color = rgba
    finish.use_nodes = True
    shader = finish.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = rgba
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    return finish


class Boundary:
    def __init__(self):
        self.verts = []
        self.index = {}
        self.faces = []
        self.finish = []

    def vertex(self, p):
        # Coordinate identity also welds the boundary of the decorative face patches.
        key = tuple(round(v, 9) for v in p)
        if key not in self.index:
            self.index[key] = len(self.verts)
            self.verts.append((key[0], -key[2], key[1]))
        return self.index[key]

    def face(self, points, finish):
        self.faces.append(tuple(self.vertex(p) for p in points))
        self.finish.append(finish)

    def countersunk_fixing(self, x0, x1, y0, y1, segments):
        # The plate and the fixing head share the front plane. Only the seat recedes.
        corners = [(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)]
        centre_x = (x0 + x1) / 2
        centre_y = (y0 + y1) / 2

        def ring(radius, depth):
            points = []
            for index in range(segments):
                angle = -3 * math.pi / 4 + index * math.tau / segments
                x = centre_x + radius * math.cos(angle)
                y = centre_y + radius * math.sin(angle)
                points.append((x, y, depth))
            return points

        rim = ring(0.0087, 0)
        seat = ring(0.0068, 0.00055)
        head = ring(0.0058, 0)
        # Join each rectangular corner to one quarter of the rim without splitting the outer edges.
        for quarter, corner in enumerate(corners):
            first = quarter * segments // 4
            last = (quarter + 1) * segments // 4
            next_corner = corners[(quarter + 1) % 4]
            self.face([corner, next_corner, rim[last % segments]], BRONZE)
            for index in range(last, first, -1):
                self.face([corner, rim[index % segments], rim[index - 1]], BRONZE)

        for outside, inside, finish in [(rim, seat, SEAL), (seat, head, FIXING)]:
            for index in range(segments):
                following = (index + 1) % segments
                self.face(
                    [
                        outside[index],
                        outside[following],
                        inside[following],
                        inside[index],
                    ],
                    finish,
                )
        self.face(head, FIXING)


def section(lod, materials):
    level = LEVELS[lod]
    root = bpy.data.objects.new("ASSET_EscalatorFloorTransition2m_" + level, None)
    collection = bpy.data.collections.new(level)
    bpy.context.scene.collection.children.link(collection)
    collection.objects.link(root)
    root.empty_display_size = 0.03

    # The shoulder begins at 775 mm, and its first 5 mm is the thin roof of the beam recess.
    fixing_centres = (0.810, 0.968) if lod < 2 else ()
    positive_x = {0, 0.775, 0.780, 1}
    for centre in fixing_centres:
        positive_x.update((round(centre - 0.010, 3), round(centre + 0.010, 3)))
    if lod < 2:
        positive_x.update((0.785, 0.986))
    xs = sorted(positive_x | {-x for x in positive_x})
    heights_per_level = (
        [-0.100, -0.076, -0.071, -0.060, -0.040, -0.022, -0.018, -0.015, 0],
        [-0.100, -0.074, -0.069, -0.060, -0.040, -0.015, 0],
        [-0.100, -0.074, -0.069, -0.015, 0],
    )
    ys = heights_per_level[lod]
    traction_bands = [(0.033, 0.039), (0.073, 0.079)]
    if lod < 2:
        traction_bands.insert(1, (0.053, 0.059))
    depths = {0, 0.025, 0.120}
    for start, end in traction_bands:
        depths.update((start, end))
    if lod == 0:
        depths.update((0.009, 0.013, 0.102, 0.106))
    zs = sorted(depths)
    x_cells, y_cells, z_cells = (
        range(len(xs) - 1),
        range(len(ys) - 1),
        range(len(zs) - 1),
    )

    def occupied(i, j, k):
        if i not in x_cells or j not in y_cells or k not in z_cells:
            return False
        inside_recess = (
            xs[i] >= -0.780
            and xs[i + 1] <= 0.780
            and ys[j + 1] <= -0.015
            and zs[k + 1] <= 0.025
        )
        return not inside_recess

    cell_faces = (
        ((-1, 0, 0), (0, 4, 6, 2)),
        ((1, 0, 0), (1, 3, 7, 5)),
        ((0, -1, 0), (0, 1, 5, 4)),
        ((0, 1, 0), (2, 6, 7, 3)),
        ((0, 0, -1), (0, 2, 3, 1)),
        ((0, 0, 1), (4, 5, 7, 6)),
    )
    boundary = Boundary()
    for i, j, k in product(x_cells, y_cells, z_cells):
        if not occupied(i, j, k):
            continue
        x0, x1 = xs[i : i + 2]
        y0, y1 = ys[j : j + 2]
        z0, z1 = zs[k : k + 2]
        x, y, z = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
        corners = [
            (vx, vy, vz) for vz in (z0, z1) for vy in (y0, y1) for vx in (x0, x1)
        ]
        for (dx, dy, dz), face_corners in cell_faces:
            if occupied(i + dx, j + dy, k + dz):
                continue
            outer_side = dx != 0 and i in (0, len(xs) - 2)
            shoulder = abs(x) >= 0.775 or outer_side
            waist_band = y0 < -0.070 <= y1
            facing = BRONZE if shoulder else STEEL
            finish = BRONZE if shoulder else BED
            if dy == 1:
                finish = facing
                if any(start < z < end for start, end in traction_bands):
                    finish = GRIP
                registration_line = 0.009 < z < 0.013 or 0.102 < z < 0.106
                if lod == 0 and not shoulder and registration_line:
                    finish = SEAL
                if lod < 2 and 0.780 < abs(x) < 0.785:
                    finish = SEAL
            elif dz == -1 and k == 0:
                finish = facing
                upper_band = lod == 0 and -0.022 < y < -0.018
                if shoulder and (waist_band or upper_band):
                    finish = SEAL
                at_fixing_x = any(
                    abs(abs(x) - centre) < 1e-6 for centre in fixing_centres
                )
                if at_fixing_x and abs(y + 0.050) < 1e-6:
                    boundary.countersunk_fixing(x0, x1, y0, y1, 16 if lod == 0 else 8)
                    continue
            elif (dx != 0 or dz == 1) and shoulder and waist_band:
                finish = SEAL
            elif not shoulder and dy != 1 and y > -0.015:
                finish = STEEL
            boundary.face([corners[index] for index in face_corners], finish)

    mesh = bpy.data.meshes.new("TerminalReturn_" + level)
    mesh.from_pydata(boundary.verts, [], boundary.faces)
    for finish in materials:
        mesh.materials.append(finish)
    for polygon, finish_index in zip(mesh.polygons, boundary.finish):
        polygon.material_index = finish_index

    editable_mesh = bmesh.new()
    editable_mesh.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(editable_mesh, faces=list(editable_mesh.faces))
    assert all(edge.is_manifold for edge in editable_mesh.edges)
    assert all(face.calc_area() > 1e-12 for face in editable_mesh.faces)
    full_volume = 2 * 0.120 * 0.100
    pocket_volume = 1.56 * 0.025 * 0.085
    assert (
        abs(editable_mesh.calc_volume(signed=True) - (full_volume - pocket_volume))
        < 0.0000006
    )
    editable_mesh.to_mesh(mesh)
    editable_mesh.free()

    source = bpy.data.objects.new("PROFILE_TerminalReturn_" + level, mesh)
    collection.objects.link(source)
    source.parent = root
    return root


def studio():
    sc = bpy.context.scene
    bpy.ops.mesh.primitive_plane_add(size=100, location=(0, 0, -0.1003))
    plane = bpy.context.object
    plane.name = "Studio surface"
    plane.data.materials.append(material("Studio graphite", "666D6C", 0, 0.81))
    focus = Vector((0, -0.060, -0.040))
    bpy.ops.object.camera_add(location=(1.45, 1.9, 1.1))
    cam = bpy.context.object
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.93
    cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    for name, pos, energy, size in [
        ("Key", (-1.4, 2.8, 3.6), 330, 3.0),
        ("Fill", (3.0, 0.4, 2.0), 180, 2.8),
        ("Rim", (-0.8, -2.5, 2.2), 410, 2.8),
    ]:
        bpy.ops.object.light_add(type="AREA", location=pos)
        obj = bpy.context.object
        obj.name = "Studio " + name
        obj.rotation_euler = (focus - obj.location).to_track_quat("-Z", "Y").to_euler()
        obj.data.energy = energy
        obj.data.shape = "DISK"
        obj.data.size = size
    sc.world = bpy.data.worlds.new("Studio world")
    sc.world.color = (0.38, 0.38, 0.38)
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 24
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 900
    sc.render.resolution_y = 580
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality = 92
    sc.view_settings.view_transform = "AgX"


def show(selected):
    for level in LEVELS:
        for obj in bpy.data.collections[level].objects:
            obj.hide_set(level != selected)
            obj.hide_render = level != selected


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    materials = [material(*f) for f in FINISHES]
    for i in range(len(LEVELS)):
        section(i, materials)
    studio()
    show("LOD0")
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(
        filepath=str(SOURCE), compress=True, relative_remap=False
    )


def export():
    for i, level in enumerate(LEVELS):
        show(level)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in bpy.data.collections[level].objects:
            obj.select_set(True)
        suffix = "" if i == 0 else "-" + level.lower()
        bpy.ops.export_scene.gltf(
            filepath=str(HERE / "exports" / (SLUG + suffix + ".glb")),
            export_format="GLB",
            use_selection=True,
            export_yup=True,
            export_extras=False,
            export_animations=False,
            export_cameras=False,
            export_lights=False,
        )
    show("LOD0")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--rebuild", action="store_true")
    choice.add_argument("--export-source", action="store_true")
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    for f in ("sources", "previews", "exports", "reports"):
        (HERE / f).mkdir(exist_ok=True)
    if args.rebuild:
        build()
    else:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    export()
    if not args.skip_render:
        bpy.context.scene.render.filepath = str(HERE / "previews" / (SLUG + ".jpg"))
        bpy.ops.render.render(write_still=True)
