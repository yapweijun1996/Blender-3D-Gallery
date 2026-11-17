"""Original deterministic Deepavali display; Blender 5.2.3, metres, no assets."""
from pathlib import Path
import bisect
import json
import math
import sys
import traceback

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'deepavali-lamps-rangoli'
ROOT = 'ASSET_DeepavaliLampsRangoli'
TAU = math.tau
MATERIALS = []


def material(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    color = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
                  for v in rgb) + (1,)
    m.diffuse_color = color
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = color
    p.inputs['Roughness'].default_value = .76
    return m


def mesh(name, vertices, faces, parent, mat=0, smooth=False, indices=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    o = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    if indices is None:
        data.materials.append(MATERIALS[mat])
    else:
        for m in MATERIALS:
            data.materials.append(m)
    for i, face in enumerate(data.polygons):
        face.use_smooth = smooth
        if indices is not None:
            face.material_index = indices[i]
    return o


def empty(name, parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    return o


def loft(name, rings, parent, mat=0, smooth=True):
    """Closed tube with nonzero end rings and correctly wound caps."""
    n = len(rings[0])
    vertices = [p for ring in rings for p in ring]
    faces = [tuple(reversed(range(n)))]
    for j in range(len(rings) - 1):
        for k in range(n):
            q = (k + 1) % n
            faces.append((j*n+k, j*n+q, (j+1)*n+q, (j+1)*n+k))
    faces.append(tuple((len(rings)-1)*n+k for k in range(n)))
    o = mesh(name, vertices, faces, parent, mat, smooth)
    o.data.polygons[0].use_smooth = False
    o.data.polygons[-1].use_smooth = False
    return o


def tube(name, points, radius, parent, mat=0, sides=8):
    rings = []
    for j, p in enumerate(points):
        tangent = Vector(points[min(j+1, len(points)-1)]) - Vector(points[max(j-1, 0)])
        tangent.normalize()
        side = tangent.cross(Vector((0, 1, 0))).normalized()
        normal = tangent.cross(side).normalized()
        rings.append([Vector(p) + radius*(math.cos(TAU*k/sides)*side +
                       math.sin(TAU*k/sides)*normal) for k in range(sides)])
    return loft(name, rings, parent, mat)


def mosaic(root):
    # A single closed 8 mm plaque. Shared ring vertices form an exact tessellation:
    # no coplanar overlays, textures, decals, text, icons or hidden base planes.
    n = 120
    radius_functions = [
        lambda a: .12,
        lambda a: .16,
        lambda a: .31 + .105*math.cos(12*a),
        lambda a: .34 + .105*math.cos(12*a),
        lambda a: .72 + .23*math.cos(12*a),
        lambda a: .75 + .23*math.cos(12*a),
        lambda a: 1.04,
        lambda a: 1.065,
        lambda a: 1.14,
        lambda a: 1.165,
        lambda a: 1.2,
    ]
    vertices = [(0, 0, .008)]
    for f in radius_functions:
        vertices.extend((f(TAU*k/n)*math.cos(TAU*k/n),
                         f(TAU*k/n)*math.sin(TAU*k/n), .008) for k in range(n))
    faces, colors = [], []
    for k in range(n):
        faces.append((0, 1+k, 1+(k+1) % n))
        colors.append(2)
    bands = [1, 0, 2, 1, 2, 0, 2, 1, 2, 0]
    for j, color in enumerate(bands):
        for k in range(n):
            q = (k+1) % n
            faces.append((1+j*n+k, 1+(j+1)*n+k, 1+(j+1)*n+q, 1+j*n+q))
            # Repeated 24 geometric chevrons in the outer saffron band.
            colors.append(2 if j == 7 and k % 5 in (2, 3) else color)
    bottom = len(vertices)
    vertices.extend((1.2*math.cos(TAU*k/n), 1.2*math.sin(TAU*k/n), 0) for k in range(n))
    centre = len(vertices)
    vertices.append((0, 0, 0))
    last = 1+(len(radius_functions)-1)*n
    for k in range(n):
        q = (k+1) % n
        faces.extend([(last+k, bottom+k, bottom+q, last+q), (centre, bottom+q, bottom+k)])
        colors.extend([0, 0])
    o = mesh('RANGOLI_OriginalTwelvePetalMosaic', vertices, faces, root, indices=colors)
    o['pattern'] = 'Original concentric twelve-petal geometric rosette with 24 outer chevrons'
    o['diameter_m'] = 2.4
    o.location.z = .012
    return o


def diya(root, j):
    group = empty('DIYA_%02d' % (j+1), root)
    angle = TAU*j/12
    group.location = (.81*math.sin(angle), -.81*math.cos(angle), .020)
    group.rotation_euler.z = angle
    n = 20
    rings = []
    # Section runs from flat base up the outer wall, over the rolled clay lip,
    # then down the hollow inner wall. The top is genuinely open.
    for scale, z in [(.30, 0), (.58, .003), (.88, .027), (1, .055),
                     (.97, .068), (.85, .067), (.75, .047), (.43, .020)]:
        ring = []
        for k in range(n):
            a = TAU*k/n
            flute = 1 + .013*math.cos(12*a)
            nose = .044*max(0, -math.sin(a))**12
            ring.append((scale*.103*math.cos(a)*flute,
                         scale*(.081*math.sin(a)*flute-nose), z))
        rings.append(ring)
    loft('CLAY_Bowl_%02d' % (j+1), rings, group)
    oil = [[(.058*math.cos(TAU*k/n), .047*math.sin(TAU*k/n), z)
            for k in range(n)] for z in (.031, .033)]
    loft('OIL_Inset_%02d' % (j+1), oil, group, 1)
    tube('WICK_Cotton_%02d' % (j+1), [(0, -.060, .044), (0, -.099, .066),
         (0, -.119, .071)], .004, group, 0, 6)
    rings = []
    for z, r, bend in [(0, .007, 0), (.020, .024, 0), (.043, .020, .002),
                       (.068, .011, .006), (.090, .0008, .012)]:
        rings.append([(bend+r*math.cos(TAU*k/8), -.117+.8*r*math.sin(TAU*k/8),
                       .070+z) for k in range(8)])
    loft('FLAME_Teardrop_%02d' % (j+1), rings, group, 2)
    core = [[(bend+r*math.cos(TAU*k/6), -.135+.004*math.sin(TAU*k/6), z)
             for k in range(6)] for bend, z, r in [(0, .077, .003),
                 (.001, .091, .010), (.003, .116, .0006)]]
    loft('FLAME_Core_%02d' % (j+1), core, group, 1)


def flower(name, centre, phase, root, mat):
    # Three flared, scalloped petal tiers with recessed throats. The staggered
    # six-lobed rings create real folds and shadows instead of a beaded sphere.
    n = 18
    profile = [(.026, -.042), (.059, -.028), (.030, -.012),
               (.061, .002), (.023, .018), (.044, .033)]
    vertices = [(0, 0, -.047)]
    for j, (radius, z) in enumerate(profile):
        for k in range(n):
            a = TAU*k/n + .16*(j//2)
            fold = math.cos(6*a + phase*.13)
            r = radius*(1 + .19*fold)
            vertices.append((r*math.cos(a), r*math.sin(a), z + .006*fold))
    vertices.append((0, 0, .045))
    faces = [(0, 1+(k+1) % n, 1+k) for k in range(n)]
    for j in range(len(profile)-1):
        for k in range(n):
            q = (k+1) % n
            faces.append((1+j*n+k, 1+j*n+q, 1+(j+1)*n+q, 1+(j+1)*n+k))
    last = 1+(len(profile)-1)*n
    faces.extend((last+k, last+(k+1) % n, len(vertices)-1) for k in range(n))
    o = mesh(name, vertices, faces, root, mat, True)
    o.location = centre
    o.rotation_euler = (math.pi/2+.17*math.sin(phase), phase, .20*math.cos(phase))


def garland(root, index):
    group = empty('GARLAND_%02d' % (index+1), root)
    x0 = -1.04 if index == 0 else .14
    # Uniform arc-length distribution keeps the string densely covered.
    samples = [Vector((x0+.90*t/200, .76+.025*math.sin(math.pi*t/200),
                       1.86-.57*math.sin(math.pi*t/200))) for t in range(201)]
    lengths = [0]
    for a, b in zip(samples, samples[1:]):
        lengths.append(lengths[-1]+(b-a).length)
    points = []
    for j in range(21):
        distance = lengths[-1]*j/20
        k = min(199, max(0, bisect.bisect_right(lengths, distance)-1))
        p = samples[k].lerp(samples[k+1], (distance-lengths[k])/(lengths[k+1]-lengths[k]))
        points.append(p)
        flower('MARIGOLD_%02d_%02d' % (index+1, j+1), p,
               j*1.618+index*.37, group, 1)
    anchors = [Vector((p.x, p.y, 1.925)) for p in (points[0], points[-1])]
    tube('CORD_%02d' % (index+1), [anchors[0], *points, anchors[1]], .005, group, 0, 6)
    for j, p in enumerate([points[0], points[-1]]):
        # Loops interlock with the supplied crossbar and overlap the end heads.
        bpy.ops.mesh.primitive_torus_add(major_segments=12, minor_segments=6,
            location=(p.x, p.y, 1.955), major_radius=.030, minor_radius=.003)
        o = bpy.context.object
        o.name = 'HANGER_%02d_%02d' % (index+1, j+1)
        o.rotation_euler.x = math.pi/2
        o.parent = group
        o.data.materials.append(MATERIALS[2])


def floor_and_frame(root):
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    floor = loft('FLOOR_TwoMetreSquare',
                 [[(x, y, z) for x, y in corners] for z in (0, .012)], root, 2, False)
    floor['interface'] = 'Included 2 x 2 m floor; underside at ground Y=0 in glTF'
    frame = empty('FRAME_GarlandSupport', root)
    for j, x in enumerate([-.94, .94]):
        # Feet sit on the square floor; the poles carry the shared crossbar.
        loft('FRAME_Foot_%02d' % j,
             [[(x+.052*math.cos(TAU*k/12), .76+.052*math.sin(TAU*k/12), z)
               for k in range(12)] for z in (.012, .032)], frame, 0)
        tube('FRAME_Post_%02d' % j, [(x, .76, .032), (x, .76, 1.96)], .016, frame, 0)
    tube('FRAME_Crossbar', [(-1.085, .76, 1.96), (1.085, .76, 1.96)], .017, frame, 0)


def build():
    root = empty(ROOT)
    root['units'] = 'metres'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['scope'] = 'Static display including square floor and freestanding garland frame; no fire or light simulation'
    floor_and_frame(root)
    mosaic(root)
    for j in range(12):
        diya(root, j)
    for j in range(2):
        garland(root, j)
    return root


def export(path):
    """Batch evaluated source geometry into exactly three material primitives."""
    root = bpy.data.objects[ROOT]
    bpy.context.view_layer.update()
    vertices, faces, names = [[] for _ in range(3)], [[] for _ in range(3)], [set() for _ in range(3)]
    smooths = [[] for _ in range(3)]
    for o in sorted(root.children_recursive, key=lambda o: o.name):
        if o.type != 'MESH':
            continue
        o.data.calc_loop_triangles()
        for triangle in o.data.loop_triangles:
            mi = MATERIALS.index(o.data.materials[triangle.material_index])
            start = len(vertices[mi])
            vertices[mi].extend(o.matrix_world @ o.data.vertices[k].co for k in triangle.vertices)
            faces[mi].append(tuple(start+k for k in range(3)))
            smooths[mi].append(o.data.polygons[triangle.polygon_index].use_smooth)
            names[mi].add(o.name)
    batch_root = empty('DELIVERY_TEMP')
    batch_root.name = ROOT + '_Export'
    for key in root.keys():
        batch_root[key] = root[key]
    objects = []
    for mi, name in enumerate(['Clay', 'Marigold', 'Ivory']):
        o = mesh('DELIVERY_'+name, vertices[mi], faces[mi], batch_root, mi)
        for polygon, smooth in zip(o.data.polygons, smooths[mi]):
            polygon.use_smooth = smooth
        # Weld triangle-local vertices and recalculate outward normals without
        # smoothing the planar mosaic or destroying the source's editable parts.
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
        bm.to_mesh(o.data)
        bm.free()
        o['source_parts'] = sorted(names[mi])
        objects.append(o)
    original_name = root.name
    root.name = 'SOURCE_TEMP'
    batch_root.name = ROOT
    bpy.ops.object.select_all(action='DESELECT')
    batch_root.select_set(True)
    for o in objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
        export_apply=True, export_yup=True, export_animations=False,
        export_texcoords=False, export_extras=True, export_cameras=False, export_lights=False)
    for o in objects:
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(data)
    bpy.data.objects.remove(batch_root, do_unlink=True)
    root.name = original_name


def aim(o, target):
    o.rotation_euler = (Vector(target)-o.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    s = bpy.context.scene
    s.world = bpy.data.worlds.new('Warm charcoal studio')
    s.world.use_nodes = True
    s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.070, .085, .10, 1)
    s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .6
    for name, loc, power, size in [('Key', (-3, -4, 5), 750, 4),
                                  ('Fill', (4, -1, 3), 500, 3), ('Rim', (0, 4, 5), 850, 3)]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        o = bpy.context.object
        o.name = 'STUDIO_'+name
        o.data.energy, o.data.size = power, size
        aim(o, (0, 0, .5))
    bpy.ops.object.camera_add()
    s.camera = bpy.context.object
    s.camera.name = 'STUDIO_Camera'
    s.camera.data.type = 'ORTHO'
    s.camera.data.ortho_scale = 3.25
    s.render.engine = 'CYCLES'
    s.cycles.samples = 32
    s.cycles.use_denoising = True
    s.render.resolution_x = s.render.resolution_y = 900
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.view_settings.view_transform = 'AgX'
    s.view_settings.exposure = -.5


def render_views():
    s = bpy.context.scene
    for name, location, target in [
        ('hero', (2.9, -4.8, 4.3), (0, 0, .7)),
        ('front', (0, -5, 2.7), (0, 0, .75)),
        ('side', (5, -.1, 2.8), (0, 0, .75)),
        ('3q', (-3.5, -4, 3.5), (0, 0, .7)),
        ('top', (0, 0, 6), (0, 0, 0)),
        ('lamps', (0, -2.4, 4.8), (0, 0, .07))]:
        s.camera.location = location
        aim(s.camera, target)
        bpy.context.view_layer.update()
        points = [o.matrix_world @ v.co for o in bpy.data.objects[ROOT].children_recursive
                  if o.type == 'MESH' and (name != 'lamps' or o.parent.name.startswith('DIYA_'))
                  for v in o.data.vertices]
        right = s.camera.matrix_world.to_quaternion() @ Vector((1, 0, 0))
        up = s.camera.matrix_world.to_quaternion() @ Vector((0, 1, 0))
        horizontal = [p.dot(right) for p in points]
        vertical = [p.dot(up) for p in points]
        shift = right*((max(horizontal)+min(horizontal))/2-Vector(target).dot(right))
        shift += up*((max(vertical)+min(vertical))/2-Vector(target).dot(up))
        s.camera.location += shift
        s.camera.data.ortho_scale = 1.15*max(max(horizontal)-min(horizontal), max(vertical)-min(vertical))
        s.render.filepath = str(HERE/'previews'/(name+'.png'))
        bpy.ops.render.render(write_still=True)


def main():
    global MATERIALS
    for name in ['sources', 'exports', 'previews', 'reports', 'metadata']:
        (HERE/name).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')))
        MATERIALS = [bpy.data.materials[n] for n in ['Terracotta', 'MarigoldGold', 'RiceIvory']]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        s = bpy.context.scene
        s.unit_settings.system = 'METRIC'
        s.unit_settings.scale_length = 1
        MATERIALS = [material('Terracotta', (.63, .25, .13)),
                     material('MarigoldGold', (.96, .56, .055)),
                     material('RiceIvory', (.96, .90, .76))]
        build()
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')), compress=True)
    export(HERE/'exports'/'optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
