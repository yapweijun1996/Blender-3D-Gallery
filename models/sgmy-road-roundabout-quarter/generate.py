"""SG/MY Jalan road kit: One quarter of a clockwise roundabout with a radial approach.

Original procedural geometry and materials. No downloaded assets are used.
Rebuild with Blender 5.2.3: blender -b --python-exit-code 1 --python generate.py
Writes model.glb and preview.png next to this script.
One unit is one metre. Place the root at the subgrade (Z=0 in Blender).
Rotate copies about the root in 90-degree steps to complete the circle.
Ring seams mate only to other quarters; North Street mates to a standard road.
Port transforms are intentional locators; all rendered mesh transforms are baked.
"""

from math import atan2, ceil, cos, hypot, pi, sin, sqrt
from pathlib import Path
import json
import struct
import tempfile
import zlib

import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view


# All dimensions are in metres. Local +Z is up; glTF export remaps to +Y up.
GRID = 16.0
HALF_ROAD = 3.5
WALK = 1.75
GRADE = 0.22
PAINT = GRADE + 0.0035
WALK_Z = 0.352
ROOT = None
MATS = {}
BATCHES = {}


def linear(hex_color):
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v < .04045 else ((v + .055) / 1.055) ** 2.4
                 for v in rgb) + (1.0,)


def material(name, color, rough=.85, metal=0, emission=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = linear(color)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = mat.diffuse_color
    shader.inputs['Roughness'].default_value = rough
    shader.inputs['Metallic'].default_value = metal
    if emission:
        shader.inputs['Emission Color'].default_value = mat.diffuse_color
        shader.inputs['Emission Strength'].default_value = emission
    MATS[name] = mat
    return mat


def tile_image(name, kind):
    # Bake deterministic, seamlessly wrapped sRGB tiles without external assets.
    rng = np.random.default_rng(2411)
    n = 512 if kind == 'asphalt' else 384

    def noise(grid):
        p = rng.normal(0, 1, (grid, grid))
        f = np.arange(n) * grid / n
        x = f.astype(int)
        t = f - x
        t = t * t * (3 - 2 * t)
        x1 = (x + 1) % grid
        a = p[np.ix_(x, x)] * (1 - t) + p[np.ix_(x, x1)] * t
        b = p[np.ix_(x1, x)] * (1 - t) + p[np.ix_(x1, x1)] * t
        return a * (1 - t[:, None]) + b * t[:, None]

    if kind == 'asphalt':
        tone = (noise(4) * 2.2 + noise(16) * 1.8 + noise(77) * 3.3
                + noise(222) * 4.5 + rng.normal(0, 3.5, (n, n)))
        stone = rng.random((n, n))
        tone += np.where(stone > .978, (stone - .978) * 640, 0)
        base = [55, 59, 61]
    else:
        tone = noise(5) * 2.3 + noise(37) * 1.7 + rng.normal(0, 2.4, (n, n))
        row, col = np.indices((n, n))
        tone += np.take([1, -4, 3, -1], (row >= n / 2) * 2 + (col >= n / 2))
        joint = np.minimum(row % (n // 2), col % (n // 2))
        tone -= np.where(joint < 2, 37, 0)
        tone += np.where(joint == 2, 6, 0)
        base = [175, 170, 158]
    rgb = np.clip(tone[..., None] + base, 0, 255).astype('uint8')

    def chunk(tag, payload):
        return (struct.pack('>I', len(payload)) + tag + payload
                + struct.pack('>I', zlib.crc32(tag + payload)))

    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', n, n, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(b''.join(b'\x00' + row.tobytes() for row in rgb), 7))
           + chunk(b'IEND', b''))
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / (name + '.png')
        path.write_bytes(png)
        image = bpy.data.images.load(str(path))
        image.pack()
    return image


def palette(with_road):
    specifications = [
        ('Foundry Charcoal', '28343C', .64, .33),
        ('Galvanised Steel', '87999C', .51, .57),
        ('Iron Oxide Primer', '454E50', .78, .22),
        ('Porcelain White', 'EAEDE1', .56, 0),
        ('Reflective Amber', 'F2B935', .51, 0),
        ('Signal Amber Lens', 'FFAE28', .35, 0, .55),
        ('Signal Red Lens', 'E02A1C', .35, 0, .49),
        ('Warning Enamel Red', 'C42E26', .71, 0),
        ('Signal Green Lens', '20C277', .35, 0, .58),
        ('Dark Lens', '303830', .36, 0),
        ('Guide Board Blue', '12598B', .65, 0),
        ('Guide Board Green', '246A55', .64, 0),
        ('Glass Optics', '262D42', .22, .18),
        ('Warm Precast Concrete', 'B0AA97', .86, 0),
    ]
    if with_road:
        specifications.extend([
            ('Dense Graded Asphalt', '464A4C', .96, 0),
            ('Asphalt Cut Edge', '333B40', .97, 0),
            ('Brushed Footway Pavers', 'AFA89F', .91, 0),
            ('Road Paint White', 'ECEDE0', .82, 0),
            ('Road Paint Yellow', 'E7B73A', .84, 0),
            ('Painted Kerb White', 'DEDCCB', .88, 0),
            ('Painted Kerb Black', '30383C', .91, 0),
            ('Tactile Ochre', 'BC893A', .91, 0),
            ('Island Grass', '65804B', .97, 0),
            ('Mulch and Laterite', '65513F', .98, 0),
            ('Leaf Forest', '355D3B', .93, 0),
            ('Leaf Fern', '548043', .91, 0),
            ('Leaf Lime', '80A153', .91, 0),
            ('Palm Trunk', '80755C', .95, 0),
            ('Palm Growth Rings', '9C8C74', .94, 0),
            ('Copper Flower', 'DF6A3D', .86, 0),
        ])
    for spec in specifications:
        material(*spec)
    if with_road:
        for name, image_name, kind in [
            ('Dense Graded Asphalt', 'Asphalt Aggregate', 'asphalt'),
            ('Brushed Footway Pavers', 'Footway Slab Joints', 'concrete'),
        ]:
            nt = MATS[name].node_tree
            tex = nt.nodes.new('ShaderNodeTexImage')
            tex.image = tile_image(image_name, kind)
            nt.links.new(tex.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])


class Batch:
    """One mesh node per functional group; UVs remain editable per face corner."""

    def __init__(self):
        self.verts, self.faces, self.materials, self.uvs = [], [], [], []

    def add(self, verts, faces, mats, uvs=None):
        base = len(self.verts)
        self.verts.extend(tuple(v) for v in verts)
        self.faces.extend(tuple(base + i for i in f) for f in faces)
        self.materials.extend([mats] * len(faces) if isinstance(mats, str) else mats)
        self.uvs.extend([None] * len(faces) if uvs is None else uvs)

    def make(self, name):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.verts, [], self.faces)
        if mesh.validate(verbose=True):
            raise RuntimeError(f'Invalid source geometry in {name}')
        mesh.update()
        for mat in dict.fromkeys(self.materials):
            mesh.materials.append(MATS[mat])
        slots = {mat.name: i for i, mat in enumerate(mesh.materials)}
        uv = mesh.uv_layers.new(name='UVMap')
        for poly, mat, mapped in zip(mesh.polygons, self.materials, self.uvs):
            poly.material_index = slots[mat]
            if mapped is None:
                axis = max(range(3), key=lambda i: abs(poly.normal[i]))
                a, b = ((1, 2), (0, 2), (0, 1))[axis]
                tile = 3.8 if mat == 'Dense Graded Asphalt' else 1.6
                mapped = [(self.verts[i][a] / tile, self.verts[i][b] / tile)
                          for i in poly.vertices]
            for index, co in zip(poly.loop_indices, mapped):
                uv.data[index].uv = co
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.parent = ROOT
        return obj


def add(group, verts, faces, mats, uvs=None):
    if group not in BATCHES:
        BATCHES[group] = Batch()
    BATCHES[group].add(verts, faces, mats, uvs)


def turn(p, angle):
    return p[0] * cos(angle) - p[1] * sin(angle), p[0] * sin(angle) + p[1] * cos(angle)


def place(origin, p, angle=0):
    x, y = turn(p, angle)
    return origin[0] + x, origin[1] + y


def ccw(points):
    area = sum(x * v - y * u for (x, y), (u, v) in zip(points, points[1:] + points[:1]))
    return points if area > 0 else points[::-1]


def slab(group, points, lo, hi, top, side=None):
    points = ccw(list(points))
    n = len(points)
    faces = [tuple(i + n for i in range(n))]
    verts = [(x, y, hi) for x, y in points]
    if lo is None:
        add(group, verts, [tuple(range(n))], top)
        return
    verts = [(x, y, lo) for x, y in points] + verts
    faces += [tuple(reversed(range(n)))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))
    add(group, verts, faces, [top] + [side or top] * (n + 1))


def deck(points):
    slab('Road Deck', points, 0, GRADE, 'Dense Graded Asphalt', 'Asphalt Cut Edge')


def unit(p):
    d = hypot(*p)
    return p[0] / d, p[1] / d


def offsets(path):
    normals = [unit((q[1] - p[1], p[0] - q[0])) for p, q in zip(path, path[1:])]
    result = [normals[0]]
    for a, b in zip(normals, normals[1:]):
        n = unit((a[0] + b[0], a[1] + b[1]))
        scale = 1 / (a[0] * n[0] + a[1] * n[1])
        result.append((n[0] * scale, n[1] * scale))
    return result + [normals[-1]]


def distances(path):
    total = [0.0]
    for a, b in zip(path, path[1:]):
        total.append(total[-1] + hypot(b[0] - a[0], b[1] - a[1]))
    return total


def densify(path, step):
    out = [path[0]]
    for a, b in zip(path, path[1:]):
        n = ceil(hypot(b[0] - a[0], b[1] - a[1]) / step)
        out.extend(tuple(x + (y - x) * i / n for x, y in zip(a, b)) for i in range(1, n))
        out.append(b)
    return out


def arc(center, radius, start, end, steps):
    return [(center[0] + radius * cos(start + (end - start) * i / steps),
             center[1] + radius * sin(start + (end - start) * i / steps))
            for i in range(steps + 1)]


def align_ends(normals, directions):
    # Arc chords approximate tangents; exact port normals prevent seam wedges.
    if directions:
        for i, normal in ((0, directions[0]), (-1, directions[1])):
            if normal is not None:
                normals[i] = normal


def pavement(path, ramps=(), banded=False, end_normals=None, inner=False):
    """Sweep an outward kerb and footway profile along a CCW deck boundary."""
    band_length = .86
    if banded:
        lengths = distances(path)
        cuts = [i*band_length for i in range(1, ceil(lengths[-1]/band_length))]
        refined = [path[0]]
        for p, q, a, b in zip(path, path[1:], lengths, lengths[1:]):
            for cut in cuts:
                if a+1e-6 < cut < b-1e-6:
                    t = (cut-a)/(b-a)
                    refined.append((p[0]+(q[0]-p[0])*t,p[1]+(q[1]-p[1])*t))
            refined.append(q)
        path = refined
    if ramps:
        path = densify(path, .28)
    lengths, normals = distances(path), offsets(path)
    align_ends(normals, end_normals)
    if inner:
        # A low rounded island kerb; the grass occupies its back edge.
        profile = [(0, 0), (0, GRADE), (0, .315), (.035, .36), (.18, .36),
                   (.23, .33), (.23, 0)]
    else:
        profile = [(0, 0), (0, GRADE), (0, .337), (.036, .375), (.17, .375),
                   (.20, WALK_Z), (1.71, WALK_Z), (WALK, .312), (WALK, 0)]
    n = len(profile)
    verts = []
    for (x, y), (nx, ny) in zip(path, normals):
        d = min((hypot(x - px, y - py) for px, py in ramps), default=10)
        t = min(1, max(0, (d - 1.02) / .74))
        dip = .13 * (1 - t * t * (3 - 2 * t))
        for k, (u, z) in enumerate(profile):
            if 2 <= k < n-1:
                # Preserve a small kerb reveal at the low point of the ramp.
                z -= dip * (.83 if k == 2 else 1)
            verts.append((x + u * nx, y + u * ny, z))
    faces, mats, uvs = [], [], []
    for i, (s0, s1) in enumerate(zip(lengths, lengths[1:])):
        light_kerb = int((s0 + s1) / 2 / band_length) % 2 == 0
        for k in range(n):
            j = (k + 1) % n
            faces.append((i*n + j, (i+1)*n + j, (i+1)*n + k, i*n + k))
            if k == 5 and not inner:
                mats.append('Brushed Footway Pavers')
                uvs.append([(profile[j][0]/1.6, s0/1.6), (profile[j][0]/1.6, s1/1.6),
                            (profile[k][0]/1.6, s1/1.6), (profile[k][0]/1.6, s0/1.6)])
            else:
                mats.append(('Painted Kerb White' if light_kerb else 'Painted Kerb Black')
                            if banded and 1 <= k <= 4 else 'Warm Precast Concrete')
                uvs.append(None)
    faces.extend([tuple(reversed(range(n))), tuple(range(len(verts)-n, len(verts)))])
    mats.extend(['Warm Precast Concrete'] * 2)
    uvs.extend([None, None])
    add('Island Kerbs' if inner else 'Kerbs and Footways', verts, faces, mats, uvs)


def ribbon(group, path, width, z, mat, end_normals=None):
    norms = offsets(path)
    align_ends(norms, end_normals)
    verts = [(x + nx * s * width/2, y + ny * s * width/2, z)
             for (x, y), (nx, ny) in zip(path, norms) for s in (-1, 1)]
    add(group, verts, [(i, i+1, i+3, i+2) for i in range(0, len(verts)-2, 2)], mat)


def stripe(path, width=.115, color='Road Paint White', end_normals=None):
    ribbon('Road Markings', path, width, PAINT, color, end_normals)


def road_arrow(c, angle, scale=1):
    profile = [(-.09, -.95), (.09, -.95), (.09, .3), (.29, .29),
               (0, 1.03), (-.29, .29), (-.09, .30)]
    slab('Road Markings', [place(c, (x*scale, y*scale), angle) for x, y in profile], None,
         PAINT, 'Road Paint White')


def yield_triangle(c, angle):
    verts = [(place(c, p, angle) + (PAINT,)) for p in
             [(-.49, .53), (.49, .53), (0, -.66), (-.29, .40), (.29, .40), (0, -.32)]]
    add('Road Markings', verts, [(0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], 'Road Paint White')


def box(group, center, dims, mat, bevel=.02, angle=0, axis=None):
    """A closed chamfered solid with bevels baked into the mesh."""
    w, d, h = [dimension / 2 for dimension in dims]
    b = min(bevel, w*.45, d*.45, h*.45)
    if b <= 0:
        rings = [[(-w,-d,z), (w,-d,z), (w,d,z), (-w,d,z)] for z in (-h,h)]
    else:
        rings = []
        for z, inset, chamfer in [(-h, b*.72, b*.38), (-h+b, 0, b),
                                  (h-b, 0, b), (h, b*.72, b*.38)]:
            a, c = w-inset, d-inset
            rings.append([(x, y, z) for x, y in [(-a+chamfer,-c),(a-chamfer,-c),(a,-c+chamfer),
                          (a,c-chamfer),(a-chamfer,c),(-a+chamfer,c),(-a,c-chamfer),(-a,-c+chamfer)]])
    q = Vector(axis).to_track_quat('Z', 'Y') if axis is not None else None
    verts = [Vector((x, y, z)) for ring in rings for x, y, z in ring]
    points = [Vector(center) + (q @ v if q is not None else Vector((*turn(v, angle), v.z)))
              for v in verts]
    loft(group, points, len(rings[0]), mat)


def loft(group, points, n, mat):
    faces = [tuple(reversed(range(n))), tuple(range(len(points)-n, len(points)))]
    for ring in range(0, len(points)-n, n):
        for i in range(n):
            j = (i + 1) % n
            faces.append((ring+i, ring+j, ring+j+n, ring+i+n))
    add(group, points, faces, mat)


def tube(group, a, b, radius, mat, tip=None, sides=12):
    delta = Vector(b) - Vector(a)
    if delta.length < 1e-7:
        raise ValueError('Zero-length tube')
    q = delta.to_track_quat('Z', 'Y')
    points = [Vector(c) + q @ Vector((r * cos(i*2*pi/sides), r * sin(i*2*pi/sides), 0))
              for c, r in [(a, radius), (b, tip if tip is not None else radius)]
              for i in range(sides)]
    loft(group, points, sides, mat)


def words(group, body, loc, width, height, mat='Porcelain White', angle=0, horizontal=False):
    # Use Blender's built-in font; bake signage to triangles with no font dependency.
    data = bpy.data.curves.new('Temporary Sign Lettering', 'FONT')
    data.body, data.align_x, data.align_y = body, 'CENTER', 'CENTER'
    data.resolution_u = 3
    obj = bpy.data.objects.new('Temporary Sign Lettering', data)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.update()
    mesh = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    mesh.calc_loop_triangles()
    points = [v.co.copy() for v in mesh.vertices]
    min_x, max_x = min(v.x for v in points), max(v.x for v in points)
    min_y, max_y = min(v.y for v in points), max(v.y for v in points)
    scale = min(width / (max_x-min_x), height / (max_y-min_y))
    coords = []
    for v in points:
        x = (v.x - (min_x+max_x)/2) * scale
        y = (v.y - (min_y+max_y)/2) * scale
        xy = place(loc, (x, y if horizontal else 0), angle)
        coords.append((*xy, loc[2] if horizontal else loc[2] + y))
    add(group, coords, [tuple(f.vertices) for f in mesh.loop_triangles], mat)
    obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.curves.remove(data)


def frame_box(group, loc, dims, panel, angle=0, inset=.06, trim='Porcelain White'):
    x, y, z = loc
    w, d, h = dims
    box(group, loc, dims, 'Foundry Charcoal', .04, angle)
    box(group, (*place((x,y), (0, -d/2-.006), angle), z), (w-.045, .023, h-.042), trim, .01, angle)
    box(group, (*place((x,y), (0, -d/2-.021), angle), z), (w-2*inset, .013, h-2*inset), panel, .006, angle)
    return (*place((x,y), (0, -d/2-.033), angle), z)


def post(group, xy, z, top, radius=.037, mat='Galvanised Steel'):
    x, y = xy
    tube(group, (x,y,z-.01), (x,y,z+.08), radius*1.7, 'Iron Oxide Primer')
    tube(group, (x,y,z+.04), (x,y,top), radius, mat)
    tube(group, (x,y,top-.07), (x,y,top+.014), radius*1.12, 'Foundry Charcoal')


def drain(c, angle=0):
    group = 'Drainage and Utility Covers'
    for w, d, z, mat in [(.37, .86, GRADE+.006, 'Galvanised Steel'),
                         (.29, .76, GRADE+.011, 'Foundry Charcoal')]:
        box(group, (*c, z), (w, d, .017), mat, .007, angle)
    for i in range(12):
        p = place(c, (0, (i-5.5)*.058), angle)
        box(group, (*p, GRADE+.020), (.286, .021, .010),
            'Galvanised Steel', .004, angle)


def manhole(c):
    group = 'Drainage and Utility Covers'
    x, y = c
    tube(group, (x,y,GRADE-.004), (x,y,GRADE+.007), .325, 'Iron Oxide Primer', sides=20)
    tube(group, (x,y,GRADE+.007), (x,y,GRADE+.011), .295, 'Foundry Charcoal', sides=20)
    for i in range(-3, 4):
        y0 = i*.071
        hx = sqrt(.273**2-y0**2) - .018
        box(group, (x, y+y0, GRADE+.014), (2*hx, .022, .009), 'Iron Oxide Primer', .003)


def setup(name):
    global ROOT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    ROOT = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(ROOT)
    ROOT['kit'] = 'SG/MY Jalan modular road kit'
    ROOT['grid_m'] = GRID
    ROOT['traffic'] = 'Left-hand traffic'


def ports(entries):
    # Socket local +Y points outward in Blender. Stored numbers are Blender XY metres.
    ROOT['surface_height_m'] = GRADE
    ROOT['carriageway_width_m'] = 2 * HALF_ROAD
    ROOT['footway_width_m'] = WALK
    ROOT['ports_blender_xy_m'] = json.dumps({name: xy for name, xy, _ in entries})
    for name, (x,y), angle in entries:
        socket = bpy.data.objects.new('Port ' + name, None)
        bpy.context.collection.objects.link(socket)
        socket.parent = ROOT
        socket.location = (x,y,0)
        socket.rotation_euler.z = angle
        socket.empty_display_size = .6


def studio(out, direction, objs):
    scene = bpy.context.scene
    points = [Vector(co) for obj in objs for co in obj.bound_box]
    lo = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    target = (lo + hi) / 2
    span = max(hi - lo)
    cam = bpy.data.objects.new('Preview Orthographic Camera', bpy.data.cameras.new('Preview Orthographic Camera'))
    scene.collection.objects.link(cam)
    cam.location = target + Vector(direction).normalized() * (span*2.9)
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO'
    cam.data.clip_end = max(200, span*8)
    cam.data.ortho_scale = span*1.5
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = 960, 750
    scene.render.resolution_percentage = 100
    bpy.context.view_layer.update()
    # Fit actual mesh vertices, not an oversized axis-aligned box around curved pieces.
    corners = [world_to_camera_view(scene, cam, v.co) for o in objs for v in o.data.vertices]
    minx, maxx = min(p.x for p in corners), max(p.x for p in corners)
    miny, maxy = min(p.y for p in corners), max(p.y for p in corners)
    right, up = (cam.rotation_euler.to_matrix() @ Vector(v) for v in [(1,0,0), (0,1,0)])
    cam.location += (right*((minx+maxx)/2-.5) + up*((miny+maxy)/2-.5)*750/960)*cam.data.ortho_scale
    cam.data.ortho_scale *= max((maxx-minx)/.83, (maxy-miny)/.80)
    bpy.ops.mesh.primitive_plane_add(size=span*250, location=(0,0,-.021))
    floor = bpy.context.object
    floor.name = 'Preview Cyclorama'
    floor.data.materials.append(material('Preview Limestone', 'ABBEB8', .92))
    scene.world = bpy.data.worlds.new('Preview Sky')
    scene.world.use_nodes = True
    sky = scene.world.node_tree.nodes.get('Background')
    sky.inputs[0].default_value = (.62,.74,.93,1)
    sky.inputs[1].default_value = .30

    def light(name, position, factor, size, color):
        lamp = bpy.data.lights.new(name, 'AREA')
        lamp.energy = span**2 * factor
        lamp.shape, lamp.size = 'DISK', span*size
        lamp.color = color
        obj = bpy.data.objects.new(name, lamp)
        scene.collection.objects.link(obj)
        obj.location = target + Vector(position)*span
        obj.rotation_euler = (target - obj.location).to_track_quat('-Z', 'Y').to_euler()
    light('Warm Daylight', (-.6,-.39,1.02), 35, .38, (1,.90,.79))
    light('Cool Skylight', (.47,.35,.71), 17, .83, (.76,.89,1))
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 12
    scene.cycles.adaptive_threshold = .06
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 3
    scene.render.threads_mode, scene.render.threads = 'FIXED', 1
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.filepath = str(out / 'preview.png')
    bpy.ops.render.render(write_still=True)


def finish(direction):
    out = Path(__file__).resolve().parent
    objs = [batch.make(name) for name, batch in BATCHES.items()]
    for obj in [ROOT, *ROOT.children]:
        obj.select_set(True)
    result = bpy.ops.export_scene.gltf(
        filepath=str(out / 'model.glb'), export_format='GLB', use_selection=True,
        export_extras=True, export_yup=True, export_texcoords=True, export_normals=True,
        export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
        export_draco_position_quantization=20, export_draco_normal_quantization=12,
        export_draco_texcoord_quantization=16, export_image_format='AUTO')
    if result != {'FINISHED'}:
        raise RuntimeError(f'GLB export failed: {result}')
    # Render only after export so the GLB contains no stage, lights or camera.
    studio(out, direction, objs)


def leaflet(group, a, b, width, mat):
    a, b = Vector(a), Vector(b)
    d = b-a
    cross = Vector((-d.y, d.x, 0)).normalized()*width
    mid = a+d*.48
    add(group, [a,mid-cross,mid+Vector((0,0,width*.52)),mid+cross,b],
        [(0,1,2),(0,2,3),(2,1,4),(3,2,4)], mat)


def fan_palm(x, y, height, seed):
    group = 'Island Palms'
    rng = np.random.default_rng(seed)
    base = .333
    lean = Vector((rng.uniform(-.40,.40),rng.uniform(-.36,.36),0))

    def axis(t):
        return Vector((x,y,base+height*t)) + lean*t*t

    n = 10
    trunk = []
    for t, r in [(0,.17),(.08,.136),(.29,.095),(.59,.080),(.84,.072),(1,.085)]:
        trunk.extend(axis(t) + Vector((r*cos(j*2*pi/n),r*sin(j*2*pi/n),0)) for j in range(n))
    loft(group, trunk, n, 'Palm Trunk')
    for t in np.linspace(.19,.96,15):
        r = .088 - t*.012
        tube(group, axis(t-.002), axis(t+.006),r, 'Palm Growth Rings', r*.95, 10)
    crown = axis(1)
    tube(group, crown-Vector((0,0,.10)), crown+Vector((0,0,.19)),.108,
         'Leaf Forest', .075, 10)
    for i in range(13):
        a = i*2.39996 + rng.uniform(-.15,.15)
        rad = rng.uniform(1.18,1.88) * (.70 if i>=9 else 1)
        rise = rng.uniform(.78,1.02) if i>=9 else rng.uniform(.33,.62)
        droop = rng.uniform(.50,.88) if i<9 else .36
        fwd = Vector((cos(a),sin(a),0))
        side = Vector((-sin(a),cos(a),0))

        def stem(t):
            return crown + fwd*rad*t + Vector((0,0,rise*sin(t*pi*.86)-droop*t*t))

        for j in range(5):
            tube(group, stem(j/5), stem((j+1)/5), .020-j*.0028, 'Leaf Lime', .018-j*.0028, 6)
        for j in range(11):
            t = .16 + j*.071
            for s in (-1,1):
                l = (.12 + .28*sin(pi*t)) * rad/.9
                tip = stem(t) + side*l*s + fwd*(l*.49) + Vector((0,0,-l*.35))
                mat = ['Leaf Forest','Leaf Fern','Leaf Lime'][(i + j + (s>0))%3]
                leaflet(group, stem(t), tip, .045*(.85+.31*sin(pi*t)), mat)


def undergrowth(x, y, seed, blooms):
    group = 'Rain Garden Planting'
    rng = np.random.default_rng(seed)
    c = Vector((x,y,.344))
    for i in range(10):
        a = i*2.39996
        f = Vector((cos(a),sin(a),0))
        mid = c + f*rng.uniform(.15,.34) + Vector((0,0,rng.uniform(.36,.55)))
        tip = mid + f*rng.uniform(.22,.51) + Vector((0,0,rng.uniform(-.19,.14)))
        mat = ['Leaf Forest','Leaf Fern','Leaf Lime'][i%3]
        tube(group,c,mid,.016,mat,.009,6)
        leaflet(group,mid-f*.065,tip,.080,mat)
        if blooms and i%3 == 0:
            rise = mid+Vector((0,0,.24))
            tube(group,c,rise,.014,'Leaf Forest',.009,6)
            for j in range(3):
                a0 = rise-Vector((0,0,j*.069))
                leaflet(group,a0,a0+f*(.19-j*.024)*(-1 if j%2 else 1)+Vector((0,0,.085)),
                        .031,'Copper Flower')


def round_sign(xy):
    group = 'Roundabout Signs'
    x, y = xy
    post(group, xy, .319, 2.55, .043)
    face = frame_box(group, (x,y+.076,1.74), (2.31,.12,.69),
                     'Guide Board Green', pi,.045)
    words(group,'Bulatan Seri Selat',(x,face[1],face[2]+.091),2.10,.164,angle=pi)
    words(group,'SELAT CIRCLE',(x,face[1],face[2]-.121),1.74,.119,angle=pi)
    tube(group,(x,y+.035,2.36),(x,y+.139,2.36),.265,'Galvanised Steel',.261,24)
    tube(group,(x,y+.137,2.36),(x,y+.150,2.36),.234,'Guide Board Blue',.232,24)
    # Three curved white arrows show clockwise circulation on the north-facing sign.
    for i in range(3):
        a0 = i*2*pi/3 + .63
        p = arc((0,0),.142,a0,a0-.94,10)
        arrowhead = p[-1]
        d = unit((p[-1][0]-p[-2][0],p[-1][1]-p[-2][1]))
        lo = (arrowhead[0]-d[0]*.04,arrowhead[1]-d[1]*.04)
        hi = (arrowhead[0]+d[0]*.038,arrowhead[1]+d[1]*.038)
        points = [hi,(lo[0]-d[1]*.036,lo[1]+d[0]*.036),(lo[0]+d[1]*.036,lo[1]-d[0]*.036)]
        norm = offsets(p)
        verts = [(x-u-du*s*.014,y+.154,2.36+v+dv*s*.014)
                 for (u,v),(du,dv) in zip(p,norm) for s in (-1,1)]
        add(group,verts,[(j,j+1,j+3,j+2) for j in range(0,len(verts)-2,2)],'Porcelain White')
        add(group,[(x-u,y+.155,2.36+v) for u,v in ccw(points)],[(0,1,2)],'Porcelain White')


def build():
    setup('Bulatan Seri Selat - Roundabout Quarter')
    palette(True)
    r = hypot(GRID,GRID)
    w = HALF_ROAD
    outer, inner = r+w, r-w
    ROOT['ring_centreline_radius_m'] = r
    ROOT['ring_travel'] = 'Clockwise, one circulating lane'
    ROOT['placement'] = 'Rotate identical quarters in 90-degree steps about this origin.'
    ROOT['port_types'] = 'North Street: standard cross-section. Diagonal ring seams: matching quarters only.'
    ports([('North Street',(0,32),0),('Ring East',(16,16),-3*pi/4),('Ring West',(-16,16),3*pi/4)])
    fillet = 2.55
    cx = w+fillet
    cy = sqrt((outer+fillet)**2-cx**2)
    a = atan2(cy,cx)
    west_seam, east_seam = (-sqrt(.5),sqrt(.5)), (sqrt(.5),sqrt(.5))
    bend = arc((0,0),outer,pi/4,a,29) + arc((cx,cy),fillet,a-pi,-pi,13)[1:]
    east = bend + [(w,32)]
    west = [(-x,y) for x,y in reversed(east)]
    curb_inner = arc((0,0),inner,3*pi/4,pi/4,62)
    deck(east + west + curb_inner)
    pavement(east, end_normals=(east_seam,(1,0)))
    pavement(west, end_normals=((-1,0),west_seam))
    pavement(curb_inner, banded=True, end_normals=((sqrt(.5),-sqrt(.5)),(-sqrt(.5),-sqrt(.5))), inner=True)
    slab('Island Ground',[(0,0)] + arc((0,0),inner-.227,pi/4,3*pi/4,62),
         0,.316,'Island Grass','Mulch and Laterite')
    lo, hi = 1.042, 2.10
    bed = arc((0,0),16.25,lo,hi,42) + arc((0,0),9.15,hi,lo,42)
    slab('Rain Garden Bed',bed,.312,.334,'Mulch and Laterite')
    for i, (x,y,h) in enumerate([(-5.1,11.85,3.9),(-1.23,14.31,4.72),(4.27,12.39,3.65)]):
        fan_palm(x,y,h,831+i)
    rng = np.random.default_rng(922)
    for j in range(22):
        a0 = rng.uniform(lo+.067,hi-.067)
        d = rng.uniform(9.9,15.6)
        undergrowth(d*cos(a0),d*sin(a0),1000+j,j%4==0)
    round_sign((.16,18.39))
    for s in (-1,1):
        for gap in (.14,.34):
            stripe([(s*(w-gap),29.23),(s*(w-gap),32)], .092, 'Road Paint Yellow')
        drain((s*(w-.205),30.78))
    for theta in [pi/4+.18,3*pi/4-.19]:
        road_arrow((r*cos(theta), r*sin(theta)), theta-pi, 1.22)
    yield_triangle((1.70,29.67),pi)
    for i in range(7):
        stripe([(.14+i*.461,27.68),(.438+i*.461,27.68)],.237)
    splitter = [(-.105,26.9),(-.245,27.55),(-.245,30.15),(0,31.25),(.245,30.15),(.245,27.55),(.105,26.9)]
    slab('Splitter Island',splitter,GRADE,.339,'Painted Kerb White','Painted Kerb Black')
    slab('Splitter Island',[(x*.76,29+(y-29)*.88) for x,y in splitter],.335,.350,'Tactile Ochre')
    manhole((-1.29,30.16))
    finish((.88,1.53,2.12))


if __name__ == "__main__":
    build()
