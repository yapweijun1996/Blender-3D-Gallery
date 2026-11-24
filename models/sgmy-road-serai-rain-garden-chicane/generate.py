"""SG/MY Jalan road kit: serai rain garden chicane.

Original geometry, materials and signs; no third-party inputs or downloads.
Rebuild both files with Blender 5.2.3 from any directory:
    blender -b --python-exit-code 1 --python path/to/generate.py
Blender's bundled glTF exporter with Draco is required. The same GLB needs a
Draco decoder at load time. One unit is one metre; Blender +Z is up and glTF
+Y is up. The origin is the base datum, +Y is the nominal Blender road axis,
and all mesh transforms are baked. Road sockets use the 16 m placement grid.
The renderer's stage and lighting are never included in the GLB.
"""

from math import atan2, ceil, cos, hypot, pi, sin, sqrt
from pathlib import Path
import struct
import tempfile
import zlib

import bpy
import numpy as np
from mathutils import Vector


# All dimensions are in metres. Local +Z is up; glTF export remaps to +Y up.
GRID = 16.0
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


def tile_image(name, kind, base_tone=None):
    # Bake deterministic, seamlessly wrapped sRGB tiles without external assets.
    rng = np.random.default_rng(2411)
    n = 512

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
    rgb = np.clip(tone[..., None] + (base_tone or base), 0, 255).astype('uint8')

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
    data.resolution_u = 4
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
    add(group, coords, [tuple(f.vertices) for f in mesh.loop_triangles if f.area > 1e-12], mat)
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


def setup(name):
    global ROOT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    ROOT = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(ROOT)
    ROOT['kit'] = 'SG/MY Jalan modular road kit'
    ROOT['origin_note'] = 'Base datum, local +Z up; port locators mark connection planes.'
    ROOT['grid_m'] = GRID
    ROOT['traffic'] = 'Left-hand traffic'


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
    scene.render.resolution_x, scene.render.resolution_y = 768, 600
    scene.render.resolution_percentage = 100
    bpy.context.view_layer.update()
    # Fit actual mesh vertices, not an oversized axis-aligned box around curved pieces.
    right, up = (cam.rotation_euler.to_matrix() @ Vector(v) for v in [(1,0,0), (0,1,0)])
    projections = [((v.co-target).dot(right), (v.co-target).dot(up)) for o in objs for v in o.data.vertices]
    xs, ys = zip(*projections)
    cam.location += right*((max(xs)+min(xs))/2) + up*((max(ys)+min(ys))/2)
    cam.data.ortho_scale = max((max(xs)-min(xs))/.88, (max(ys)-min(ys))*960/750/.84)
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
    scene.render.threads_mode, scene.render.threads = 'FIXED', 2
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.filepath = str(out / 'preview.png')
    bpy.ops.render.render(write_still=True)


def finish(direction):
    out = Path(__file__).resolve().parent
    ROOT['asset_slug'] = out.name
    ROOT['source_blender'] = bpy.app.version_string
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
    indexed_preview(out / 'preview.png')


def begin(name, *materials, road=False):
    setup(name)
    palette(road)
    for spec in materials:
        material(*spec)


def socket(name, xyz, angle=0, **metadata):
    # Local +Y points out of the module, even after Z-up to Y-up conversion.
    locator = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(locator)
    locator.parent = ROOT
    locator.location = xyz
    locator.rotation_euler.z = angle
    locator.empty_display_size = .45
    for key, value in metadata.items():
        locator[key] = value


def road_ports(entries):
    for name, x, y, z, angle, width, footway in entries:
        socket('Port ' + name, (x, y, z), angle, carriageway_width_m=width,
               footway_width_m=footway)


def surface_tile(mat_name, image_name, kind, tone):
    mat = MATS[mat_name]
    nt = mat.node_tree
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = tile_image(image_name, kind, tone)
    nt.links.new(tex.outputs['Color'],nt.nodes['Principled BSDF'].inputs['Base Color'])


def nameboard(x,y,z,heading,title,subtitle,color='Guide Board Green',w=2.2):
    group='Wayfinding plaque'
    for dx in (-w*.34,w*.34):
        p=place((x,y),(dx,.055),heading)
        post(group,p,z,z+1.99,.045)
    f=frame_box(group,(x,y,z+1.72),(w,.1,.66),color,heading,.05)
    words(group,title,(f[0],f[1],f[2]+.078),w-.28,.215,angle=heading)
    words(group,subtitle,(f[0],f[1],f[2]-.152),w-.32,.094,angle=heading)


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


def rect_points(center, w, h, angle=0):
    return [place(center, p, angle) for p in [(-w/2, -h/2), (w/2, -h/2),
                                             (w/2, h/2), (-w/2, h/2)]]


def beam(group, a, b, w, d, mat, chamfer=.02):
    a, b = Vector(a), Vector(b)
    box(group, (a+b)/2, (w, d, (b-a).length), mat, chamfer, axis=b-a)


def plate(group, xy, z, width, length, mat, angle=0):
    slab(group, rect_points(xy, width, length, angle), None, z, mat)


def indexed_preview(path):
    """Median-cut the rendered display pixels; no external PNG utilities required."""
    image = bpy.data.images.load(str(path), check_existing=False)
    image.colorspace_settings.name = 'Non-Color'
    w,h = image.size
    buf = np.empty(w*h*4, np.float32)
    image.pixels.foreach_get(buf)
    rgb = (np.clip(buf.reshape(h,w,4)[::-1,:,:3],0,1)*255+.5).astype(np.int32).reshape(-1,3)
    bpy.data.images.remove(image)
    keys = (rgb[:,0]//4)*4096+(rgb[:,1]//4)*64+rgb[:,2]//4
    _, inverse, weights = np.unique(keys,return_inverse=True,return_counts=True)
    colors = np.stack([np.bincount(inverse,weights=rgb[:,j])/weights for j in range(3)],axis=1)
    boxes = [(np.arange(len(weights)),1.)]
    while len(boxes)<256:
        i=max(range(len(boxes)),key=lambda j:boxes[j][1]);ids,score=boxes.pop(i)
        if len(ids)==1:boxes.append((ids,0));break
        axis=np.argmax(np.ptp(colors[ids],axis=0)*[.9,1,.85]);ids=ids[np.argsort(colors[ids,axis])]
        cut=min(len(ids)-1,np.searchsorted(weights[ids].cumsum(),weights[ids].sum()/2)+1)
        for block in (ids[:cut],ids[cut:]):
            boxes.append((block,np.max(np.ptp(colors[block],axis=0))*weights[block].sum()**.45 if len(block)>1 else 0))
    lut=np.empty(len(weights),np.uint8);pal=[]
    for j,(ids,_) in enumerate(boxes):
        lut[ids]=j;pal.append(np.average(colors[ids],weights=weights[ids],axis=0))
    rows=lut[inverse].reshape(h,w)
    def chunk(k,d):return struct.pack('>I',len(d))+k+d+struct.pack('>I',zlib.crc32(k+d))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,3,0,0,0))+chunk(b'PLTE',np.round(pal).astype('uint8').tobytes())+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row.tobytes() for row in rows),9))+chunk(b'IEND',b''))
    if path.stat().st_size>250000:raise RuntimeError('Preview exceeds delivery budget')


WHITE='Road Paint White'
YELLOW='Road Paint Yellow'
PCC='Warm Precast Concrete'
IRON='Foundry Charcoal'
ZINC='Galvanised Steel'
ASPH='Dense Graded Asphalt'


def rect(group,x,y,lo,hi,w,l,top,side=None):
    slab(group,rect_points((x,y),w,l),lo,hi,top,side)


def street(half=16,w=7,z=0,edges=True,center=True,footway=0):
    rect('Carriageway',0,0,z,z+GRADE,w,2*half,ASPH,'Asphalt Cut Edge')
    road_ports([('South',0,-half,z,pi,w,footway),('North',0,half,z,0,w,footway)])
    if edges:
        for side in (-1,1):plate('Edge paint',(side*(w/2-.20),0),z+PAINT,.12,2*half,WHITE)
    if center:
        for y in np.arange(-half+2,half,4):plate('Centre dashes',(0,y),z+PAINT,.11,1.72,WHITE)


def oval_rock(g,x,y,z,rx,ry,rz,seed,mats):
    rng=np.random.default_rng(seed);n=8;points=[]
    for k,(rad,height) in enumerate([(.76,0),(1,.26),(.80,.70),(.42,1)]):
        for i in range(n):
            a=(i+.20*k+rng.uniform(-.09,.09))*2*pi/n;r=rad*rng.uniform(.89,1.12)
            points.append((x+rx*r*cos(a),y+ry*r*sin(a),z+rz*(height+(rng.uniform(-.06,.06) if k else 0))))
    faces=[tuple(reversed(range(n))),tuple(range(3*n,4*n))];colors=[mats[0],mats[1]]
    for k in range(3):
        for i in range(n):
            j=(i+1)%n;v=(k*n+i,k*n+j,(k+1)*n+j,(k+1)*n+i)
            faces.extend([(v[0],v[1],v[2]),(v[0],v[2],v[3])]);colors.extend([mats[rng.integers(len(mats))],mats[(k+i)%len(mats)]])
    add(g,points,faces,colors)


def build():
    """Bioretention build-outs alternately narrow a two-way estate street."""
    stone='Bluestone Apron'; soil='Composted Bark';flower='Heliconia Vermilion';tip='Bract Gold'
    begin('Serai | Rain Garden Chicane',(stone,'626E69',.97),(soil,'604E3D',.99),(flower,'DA623F',.83),(tip,'EDB646',.81),road=True)
    # Kerb and footing geometry runs up to both port planes. Inside each bed,
    # the planted soil is depressed relative to the precast inlet sill.
    street(center=False,edges=False,footway=WALK);surface_tile(soil,'Coir mulch','asphalt',(103,82,62))
    rng=np.random.default_rng(40)
    def pandan(x,y,z,r,h,seed):
        rd=np.random.default_rng(seed)
        for k in range(18):
            a=k*2.399;d=Vector((cos(a),sin(a),0));n=Vector((-sin(a),cos(a),0));p=Vector((x,y,z));extent=r*rd.uniform(.62,1.0);height=h*rd.uniform(.54,1.1);w=r*.19
            points=[]
            for j,(dist,lift,width) in enumerate([(.012,.02,.25),(.24,.68,.89),(.63,1.,1.),(1.,.72,.03)]):
                mid=p+d*(extent*dist)+Vector((0,0,height*lift));points+= [mid-n*w*width,mid+Vector((0,0,.057*r*width)),mid+n*w*width]
            faces=[(i+j,i+j+3,i+j+4,i+j+1) for i in (0,3,6) for j in (0,1)]
            add('Pandan leaf fans',points,faces,['Leaf Fern','Leaf Lime']*3)
    for s in (-1,1):
        x=s*3.5;cy=s*6.6
        pavement([(x,-16),(x,16)] if s>0 else [(x,16),(x,-16)],banded=False)
        def intrusion(y):
            t=min(1,max(0,(5.61-abs(y-cy))/1.9));return 1.78*t*t*(3-2*t)
        ys=np.linspace(cy-5.6,cy+5.6,43);arc=[(s*(3.48-intrusion(y)),y) for y in ys];back=[(s*3.5,cy+5.61),(s*3.5,cy-5.61)]
        slab('Filter bed bowls',arc+back,.22,.266,soil,stone)
        for i in range(len(arc)-1):
            a,b=arc[i:i+2];h=.151 if i not in (9,10,32,33) else .038
            beam('Inlet kerbstones',(*a,.226+h/2),(*b,.226+h/2),.17,h,PCC,.012)
        for y in np.linspace(cy-4.66,cy+4.66,20):
            width=intrusion(y);xx=s*(3.41-width*rng.uniform(.16,.80));r=rng.uniform(.105,.23)
            oval_rock('River cobbles',xx,y,.266,r,r*.81,r*.56,int((y+40)*81),[stone,PCC,'Mulch and Laterite'])
        for i,dy in enumerate((-3.65,-2.43,-1.11,.19,1.58,2.78,3.84)):
            y=cy+dy;x=s*(2.84+.18*cos(i*2))
            pandan(x,y,.269,.47+.12*cos(i),.62+.14*sin(i),i+55)
            if i%2==0:
                for t in (-1,1):
                    xx=x+t*.18;yy=y+.21;h=.92+.13*t;tube('Heliconia stalks',(xx,yy,.27),(xx+.045,yy,h+.27),.019,'Leaf Fern',sides=7)
                    for j in range(4):
                        zz=h+j*.076;tube('Lobster claw bracts',(xx,yy,zz),(xx+.15*(-1)**j,yy,zz+.074),.065,flower,tip=.019,sides=7)
                        tube('Bract tips',(xx+.13*(-1)**j,yy,zz+.06),(xx+.17*(-1)**j,yy,zz+.115),.026,tip,tip=.005,sides=6)
        # Young, staked street trees sit behind the swept kerb line. The leaf
        # clusters follow the tips of real forked branches, not a sphere stack.
        tx=s*2.96;ty=cy+.86;trunk='Palm Trunk';base=(tx,ty,.266);fork=(tx+.046,ty+.04,2.37)
        tube('Sapling trunks',base,fork,.103,trunk,tip=.067,sides=10)
        for k in range(3):
            a=k*2*pi/3;bx=tx+.41*cos(a);by=ty+.41*sin(a)
            tube('Nursery stakes',(bx,by,.265),(bx,by,1.52),.046,'Palm Growth Rings',sides=8)
            tube('Nursery ties',(bx,by,1.36),(tx,ty,1.55),.021,IRON,sides=6)
        for j in range(13):
            a=j*2.399+.48*s
            d=.38+.43*(1-j/13);z=2.68+.097*j;px=tx+cos(a)*d;py=ty+sin(a)*d
            tube('Sapling limbs',(fork[0],fork[1],1.86+j*.063),(px,py,z),.051-j*.0024,trunk,tip=.024,sides=8)
            foliage=['Leaf Forest','Leaf Fern','Leaf Lime'];leaf=foliage[(j//4)%3];n=7;pts=[]
            for k,(r,h) in enumerate([(.32,-.21),(.61,.02),(.49,.22),(.17,.35)]):
                for ii in range(n):
                    theta=2*pi*ii/n+.38*k;rr=r*(1+.19*sin(ii*7.21+j));pts.append((px+rr*cos(theta),py+rr*sin(theta),z+h+.06*cos(theta+j)))
            loft('Sapling leaf clusters',pts,n,leaf)
        for dy in (-3.21,3.21):
            # Amber-tipped kerb markers stand just inside the swept line.
            xx=s*1.91;yy=cy+dy;post('Delineator stems',(xx,yy),.27,1.19,.067,IRON)
            box('Reflective caps',(xx,yy,1.05),(.142,.15,.145),'Reflective Amber',.025)
        for k in range(2):
            ys=np.linspace(-16,16,129);path=[(s*(3.24-.16*k-intrusion(y)),y) for y in ys];stripe(path,.085,YELLOW)
    for y in np.arange(-14,16,4):
        def mid(y):return sum(-s*.75*min(1,max(0,(5.61-abs(y-s*6.6))/1.9)) for s in (-1,1))
        stripe([(mid(y+t),y+t) for t in np.linspace(-.71,.71,8)],.102,WHITE)
    nameboard(-4.47,-12.4,WALK_Z,0,'TAMAN SERAI','TAMAN HUJAN',w=1.88)
    finish((1.01,-1.42,1.67))


if __name__ == "__main__":
    build()
