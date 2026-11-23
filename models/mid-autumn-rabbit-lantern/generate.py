"""Build the editable paper rabbit and export a standalone static GLB in Blender 5.1."""
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

BASE = Path(__file__).resolve().parent
SLUG = "mid-autumn-rabbit-lantern"
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
root = bpy.data.objects.new("ASSET_MidAutumnRabbitLantern", None)
bpy.context.collection.objects.link(root)


def material(name, color, roughness, emission=0, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Emission Color"].default_value = (*color, 1)
    shader.inputs["Emission Strength"].default_value = emission
    return mat


paper = material("Warm ivory paper", (0.97, 0.665, 0.29), 0.78, 0.24)
pink = material("Rose tissue", (0.96, 0.26, 0.23), 0.71, 0.16)
rattan = material("Honey bamboo ribs", (0.72, 0.31, 0.062), 0.66, 0.09)
ink = material("Tea brown ink", (0.12, 0.038, 0.015), 0.88)
eye = material("Dark lacquer eye", (0.035, 0.014, 0.009), 0.21)
coral = material("Vermilion paper", (0.64, 0.052, 0.024), 0.67, 0.10)
petal = material("Coral blossom highlights", (0.90, 0.17, 0.095), 0.74)
pollen = material("Golden blossom centres", (0.95, 0.46, 0.062), 0.68)


def finish(obj, name, mat):
    obj.name = name
    obj.parent = root
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def oval(name, center, radii, mat, rotation=0, detail=32):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=detail, ring_count=detail // 2, location=center
    )
    obj = finish(bpy.context.object, name, mat)
    obj.scale = radii
    obj.rotation_euler.y = rotation
    return obj


def tube(name, points, radius, mat, closed=False, sides=6):
    points = [Vector(p) for p in points]
    verts, faces = [], []
    count = len(points)
    normal = None
    for i, point in enumerate(points):
        prev = points[(i - 1) % count] if closed else points[max(0, i - 1)]
        nxt = points[(i + 1) % count] if closed else points[min(count - 1, i + 1)]
        tangent = (nxt - prev).normalized()
        if normal is None:
            normal = Vector((0, 0, 1)) if abs(tangent.z) < 0.9 else Vector((0, 1, 0))
        normal = (normal - tangent * tangent.dot(normal)).normalized()
        binormal = tangent.cross(normal)
        for j in range(sides):
            angle = math.tau * j / sides
            verts.append(point + radius * (normal * math.cos(angle) + binormal * math.sin(angle)))
    for i in range(count if closed else count - 1):
        for j in range(sides):
            a, b = i * sides, ((i + 1) % count) * sides
            k = (j + 1) % sides
            faces.append((a + j, a + k, b + k, b + j))
    if not closed:
        faces.extend((tuple(reversed(range(sides))), tuple(range(len(verts) - sides, len(verts)))))
    mesh = bpy.data.meshes.new(name + " mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return finish(obj, name, mat)


def lattice(name, center, radii, hoops, meridians, line):
    # Rings sit on the continuous paper shell instead of cutting gaps into it.
    a, b, c = (value + line * 0.38 for value in radii)
    x, y, z = center

    def surface(latitude, longitude):
        u = math.cos(latitude)
        return (
            x + a * u * math.cos(longitude),
            y + b * u * math.sin(longitude),
            z + c * math.sin(latitude),
        )

    for i, latitude in enumerate(hoops):
        points = [surface(latitude, math.tau * step / 64) for step in range(64)]
        tube(f"{name} hoop {i + 1}", points, line, rattan, closed=True)
    for i in range(meridians):
        longitude = math.tau * (i + 0.5) / meridians
        points = [surface(-1.43 + 2.86 * step / 32, longitude) for step in range(33)]
        tube(f"{name} upright rib {i + 1}", points, line, rattan)


body_center = (-0.081, 0, 0.206)
body_radii = (0.237, 0.154, 0.188)
head_center = (0.133, 0, 0.403)
head_radii = (0.142, 0.112, 0.119)
oval("Body paper shell", body_center, body_radii, paper, detail=48)
oval("Head paper shell", head_center, head_radii, paper, detail=48)
lattice("Body", body_center, body_radii, (-0.97, -0.47, 0.05, 0.57, 1.02), 10, 0.0021)
lattice("Head", head_center, head_radii, (-0.65, -0.10, 0.46, 0.96), 8, 0.0017)
oval("Tail paper", (-0.304, 0, 0.141), (0.044, 0.047, 0.050), paper)
lattice("Tail", (-0.304, 0, 0.141), (0.044, 0.047, 0.050), (-0.43, 0.26), 4, 0.0015)

for side, label in ((-1, "Near"), (1, "Far")):
    oval(f"{label} foreleg paper", (0.085, side * 0.074, 0.074),
         (0.043, 0.035, 0.057), paper, rotation=0.22, detail=24)
    for name, x, y, length, width, height in (
        ("Rear", -0.169, 0.096, 0.089, 0.057, 0.028),
        ("Front", 0.098, 0.078, 0.076, 0.043, 0.024),
    ):
        center = (x, side * y, height)
        radii = (length, width, height)
        oval(f"{label} {name} foot paper", center, radii, paper)
        lattice(f"{label} {name} foot", center, radii, (0.02,), 4, 0.0015)


def ear(label, center, radii, lean):
    oval(f"{label} ear shell", center, radii, paper, lean, detail=40)
    a, b, c = radii
    transform = Matrix.Rotation(lean, 3, "Y")
    origin = Vector(center)

    def point(r, angle):
        return origin + transform @ Vector((
            a * r * math.cos(angle),
            -b * math.sqrt(max(0, 1 - r * r)) - 0.0012,
            c * r * math.sin(angle),
        ))

    rings, sectors, extent = 7, 40, 0.80
    vertices = [point(0, 0)]
    for i in range(1, rings + 1):
        vertices.extend(point(extent * i / rings, j * math.tau / sectors) for j in range(sectors))
    faces = [(0, j + 1, (j + 1) % sectors + 1) for j in range(sectors)]
    for i in range(rings - 1):
        for j in range(sectors):
            a_row, b_row = 1 + i * sectors, 1 + (i + 1) * sectors
            k = (j + 1) % sectors
            faces.append((a_row + j, b_row + j, b_row + k, a_row + k))
    mesh = bpy.data.meshes.new(f"{label} ear inset mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    inset = bpy.data.objects.new(f"{label} ear inset", mesh)
    bpy.context.collection.objects.link(inset)
    finish(inset, inset.name, pink)
    tube(f"{label} ear inset binding", [point(extent, j * math.tau / 64) for j in range(64)],
         0.00165, rattan, closed=True)


ear("Far", (0.075, 0.053, 0.610), (0.043, 0.032, 0.139), -0.33)
ear("Near", (0.009, -0.057, 0.587), (0.051, 0.034, 0.142), -0.79)

for direction, label in ((-1, "Near"), (1, "Far")):
    oval(f"{label} lacquer eye", (0.200, direction * 0.094, 0.433), (0.014, 0.008, 0.014), eye, detail=24)
    oval(f"{label} eye catchlight", (0.205, direction * 0.101, 0.438), (0.0033, 0.0020, 0.0033),
         paper, detail=12)
oval("Vermilion nose", (0.271, 0, 0.406), (0.012, 0.022, 0.013), coral, detail=24)


def motif_point(x, z, side, offset):
    dx = (x - body_center[0]) / body_radii[0]
    dz = (z - body_center[2]) / body_radii[2]
    y = body_radii[1] * math.sqrt(max(0, 1 - dx * dx - dz * dz))
    return x, side * (y + offset), z


strokes = (
    ((-0.237, 0.102), (-0.209, 0.173), (-0.186, 0.235), (-0.150, 0.286)),
    ((-0.202, 0.196), (-0.148, 0.218), (-0.094, 0.232), (-0.057, 0.265)),
    ((-0.205, 0.184), (-0.240, 0.211), (-0.248, 0.245)),
    ((-0.157, 0.222), (-0.133, 0.253), (-0.121, 0.285)),
)
blossoms = ((-0.150, 0.290, 0.027), (-0.057, 0.267, 0.021),
            (-0.248, 0.246, 0.019), (-0.121, 0.284, 0.014), (-0.217, 0.171, 0.013))
for side, label in ((-1, "Near"), (1, "Far")):
    for i, stroke in enumerate(strokes):
        points = []
        for (x0, z0), (x1, z1) in zip(stroke, stroke[1:]):
            for k in range(8):
                f = k / 8
                points.append(motif_point(x0 + f * (x1 - x0), z0 + f * (z1 - z0), side, 0.0036))
        points.append(motif_point(*stroke[-1], side, 0.0036))
        tube(f"{label} blossom branch {i + 1}", points, 0.0034 if i == 0 else 0.0021, ink)
    for i, (x, z, size) in enumerate(blossoms):
        for k in range(5):
            angle = math.tau * k / 5
            px, pz = x + math.cos(angle) * size * 0.58, z + math.sin(angle) * size * 0.58
            oval(f"{label} blossom {i + 1} petal {k + 1}", motif_point(px, pz, side, 0.005),
                 (size * 0.53, 0.0040, size * 0.42), petal if k % 3 == 0 else coral,
                 -angle, detail=14)
        oval(f"{label} blossom {i + 1} centre", motif_point(x, z, side, 0.008),
             (size * 0.22, 0.0032, size * 0.22), pollen, detail=12)

sources, exports = BASE / "sources", BASE / "exports"
sources.mkdir(exist_ok=True)
exports.mkdir(exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = root
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(sources / f"{SLUG}.blend"))

# Export one mesh per material while retaining independent paper, ribs and motif in the source.
materials = {}
for obj in tuple(root.children):
    materials.setdefault(obj.data.materials[0].name, []).append(obj)
for name, group in materials.items():
    bpy.ops.object.select_all(action="DESELECT")
    for obj in group:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = group[0]
    if len(group) > 1:
        bpy.ops.object.join()
    group[0].name = name
bpy.ops.export_scene.gltf(filepath=str(exports / f"{SLUG}.glb"), export_format="GLB")
