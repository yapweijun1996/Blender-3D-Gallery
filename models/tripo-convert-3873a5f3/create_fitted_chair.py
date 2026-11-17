"""Create a character-scale chair variant from the original dining chair GLB."""
import os
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

asset_dir = os.path.dirname(os.path.abspath(__file__))
source = os.path.join(asset_dir, '..', 'plastic-dining-chair', 'exports', 'optimized.glb')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=source)
parts = list(bpy.context.scene.objects)
root = bpy.data.objects.new('FittedChair', None)
bpy.context.collection.objects.link(root)
for part in parts:
    if part.parent is None:
        part.parent = root
# The chair and character share an origin; the original chair asset is unchanged.
root.scale = (.70, .35, .35)
root.location = (.01, .10, 0)
bpy.context.view_layer.update()
seat = next(o for o in parts if o.type == 'MESH' and o.name == 'SEAT')
seat_corners = [seat.matrix_world @ Vector(v) for v in seat.bound_box]
front = min(v.y for v in seat_corners)
back = max(v.y for v in seat_corners)
world = seat.matrix_world.copy()
inverse = world.inverted()
for vertex in seat.data.vertices:
    point = world @ vertex.co
    point.y += .10 * (point.y - front) / (back - front)
    point.z += .0071
    vertex.co = inverse @ point
for obj in parts:
    if obj.type != 'MESH':
        continue
    center = sum(((obj.matrix_world @ Vector(v)).y for v in obj.bound_box), 0.0) / 8
    is_back_support = obj.name.startswith(('LEG', 'FOOT')) and center > root.location.y
    if obj.name.startswith('BACK') or is_back_support:
        matrix = obj.matrix_world.copy()
        matrix.translation.y += .10
        obj.matrix_world = matrix
bpy.context.view_layer.update()
# Build a low, contoured cushion below the deformed seated character.  Sampling
# nearby points conservatively keeps the triangulated surface below the mesh.
existing = set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=os.path.join(asset_dir, 'character-motion.glb'))
character = set(bpy.context.scene.objects) - existing
rig = next(o for o in character if o.type == 'ARMATURE')
body = next(o for o in character if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers))
rig.animation_data.action = bpy.data.actions['Sit']
bpy.context.scene.frame_set(24)
graph = bpy.context.evaluated_depsgraph_get()
evaluated = body.evaluated_get(graph)
data = evaluated.to_mesh()
body_vertices = [evaluated.matrix_world @ v.co for v in data.vertices]
body_faces = [tuple(p.vertices) for p in data.polygons]
tree = BVHTree.FromPolygons(body_vertices, body_faces, epsilon=0)
evaluated.to_mesh_clear()
seat_top = max((seat.matrix_world @ Vector(v)).z for v in seat.bound_box)
base = seat_top - .001
nx, ny = 60, 24
xmin, xmax = -.095, .105
ymin, ymax = .026, .100
step_x = (xmax - xmin) / nx
step_y = (ymax - ymin) / ny
vertices = []
for j in range(ny + 1):
    y = ymin + j * step_y
    for i in range(nx + 1):
        x = xmin + i * step_x
        hits = []
        for dx in (-step_x / 4, 0, step_x / 4):
            for dy in (-step_y / 4, 0, step_y / 4):
                hit, _, _, _ = tree.ray_cast(Vector((x + dx, y + dy, .155)), Vector((0, 0, 1)), .14)
                if hit is not None:
                    hits.append(hit.z)
        safe = min(hits) - .0002 if hits else base
        edge = min(1, i / 3, (nx - i) / 3, (ny - j) / 3)
        height = base + max(0, min(.035, safe - base)) * edge
        vertices.append((x, y, height))
faces = []
for j in range(ny):
    for i in range(nx):
        a = j * (nx + 1) + i
        faces.extend(((a, a + 1, a + nx + 2), (a, a + nx + 2, a + nx + 1)))
# Lower only intersecting top cells, preserving close support elsewhere.
for attempt in range(16):
    cushion_tree = BVHTree.FromPolygons(vertices, faces, epsilon=1e-7)
    overlaps = tree.overlap(cushion_tree)
    if not overlaps:
        break
    changed = set(index for _, face in overlaps for index in faces[face])
    for index in changed:
        x, y, z = vertices[index]
        vertices[index] = (x, y, max(base, z - .0003))
else:
    raise RuntimeError('Could not remove cushion intersections')
# Close the cushion with a flat underside and perimeter faces.
top_count = len(vertices)
vertices.extend((x, y, base - .002) for x, y, _ in vertices[:top_count])
for j in range(ny):
    for i in range(nx):
        a = top_count + j * (nx + 1) + i
        faces.append((a + nx + 1, a + nx + 2, a + 1, a))
perimeter = [i for i in range(nx + 1)]
perimeter += [j * (nx + 1) + nx for j in range(1, ny + 1)]
perimeter += [ny * (nx + 1) + i for i in range(nx - 1, -1, -1)]
perimeter += [j * (nx + 1) for j in range(ny - 1, 0, -1)]
for a, b in zip(perimeter, perimeter[1:] + perimeter[:1]):
    faces.append((a, top_count + a, top_count + b, b))
cushion_mesh = bpy.data.meshes.new('ContouredSeatCushion')
cushion_mesh.from_pydata(vertices, [], faces)
cushion_mesh.update()
cushion = bpy.data.objects.new('Seat_Cushion', cushion_mesh)
bpy.context.collection.objects.link(cushion)
if seat.data.materials:
    cushion.data.materials.append(seat.data.materials[0])
for polygon in cushion_mesh.polygons:
    polygon.use_smooth = True
for obj in character:
    bpy.data.objects.remove(obj, do_unlink=True)
# Remove temporary character datablocks from the standalone chair source.
bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
bpy.context.view_layer.update()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(asset_dir, 'fitted-chair.blend'), compress=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.join(asset_dir, 'fitted-chair.glb'), export_format='GLB', use_selection=True)
