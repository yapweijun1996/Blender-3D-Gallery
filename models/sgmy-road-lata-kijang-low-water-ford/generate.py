"""SG/MY Jalan road kit: lata kijang low water ford.

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


def follow(group, points, radii, mat, sides=12):
    """One continuous tube with its circular section aligned to path tangents."""
    points = [Vector(p) for p in points]
    rings = []
    for i, (p, r) in enumerate(zip(points, radii)):
        tangent = points[min(i+1, len(points)-1)] - points[max(i-1, 0)]
        q = tangent.to_track_quat('Z', 'Y')
        rings.extend(p + q @ Vector((r*cos(j*2*pi/sides), r*sin(j*2*pi/sides), 0))
                     for j in range(sides))
    loft(group, rings, sides, mat)


def fern(group, x, y, z, radius, seed, colors=('Leaf Forest', 'Leaf Fern', 'Leaf Lime')):
    # The fronds are creased and tapered, with separate pinnae for a readable silhouette.
    rng = np.random.default_rng(seed)
    for i in range(6):
        a = i*2*pi/6 + rng.uniform(-.16,.16)
        r = radius * rng.uniform(.68,1.03)
        d, n = Vector((cos(a),sin(a),0)), Vector((-sin(a),cos(a),0))
        base = Vector((x,y,z))
        def pt(t):
            return base+d*(r*t) + Vector((0,0,r*(.69*sin(t*2.33)+.16*t)))
        spine = [pt(j/4) for j in range(5)]
        follow(group, spine, [.013*radius*(1-.78*j/4) for j in range(5)], colors[0], 5)
        for j in range(1, 7):
            t = j/8
            p = pt(t)
            for s in (-1,1):
                w = radius * (.205*sin(pi*t)**.7 + .014)
                tip = p+n*(s*w) + d*(r*.115) + Vector((0,0,-.16*w))
                rib = p.lerp(tip,.48) + Vector((0,0,.10*w))
                verts = [p, rib-d*w*.23, tip, rib+d*w*.17, rib]
                faces = [(0,1,4), (1,2,4), (2,3,4), (3,0,4)]
                add(group, verts, [f[::-1] if s==1 else f for f in faces],
                    [colors[(i+j)%2], colors[1], colors[2], colors[1]])


def surface_tile(mat_name, image_name, kind, tone):
    mat = MATS[mat_name]
    nt = mat.node_tree
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = tile_image(image_name, kind, tone)
    nt.links.new(tex.outputs['Color'],nt.nodes['Principled BSDF'].inputs['Base Color'])


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


def rect_points(center, w, h, angle=0):
    return [place(center, p, angle) for p in [(-w/2, -h/2), (w/2, -h/2),
                                             (w/2, h/2), (-w/2, h/2)]]


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


# Geometry utilities shared with the Jalan kit. Curved surfaces follow the centreline.
def path_section(group, route, section, colors):
    verts = []
    for i, p in enumerate(route):
        v = Vector(route[min(len(route)-1,i+1)]) - Vector(route[max(0,i-1)])
        n = Vector((v.y,-v.x,0)).normalized()
        verts.extend(Vector(p)+n*x+Vector((0,0,z)) for x,z in section)
    n = len(section)
    faces = [(j+n*i,j+n*(i+1),(j+1)%n+n*(i+1),(j+1)%n+n*i) for i in range(len(route)-1) for j in range(n)]
    add(group, verts, [tuple(range(n)),*faces,tuple(reversed(range(len(verts)-n,len(verts))))], [colors[1],*(colors*(len(route)-1)),colors[1]])


def strip(group,route,left,right,lo,hi,top,side=None):
    path_section(group,route,[(left,lo),(right,lo),(right,hi),(left,hi)],[side or top,side or top,top,side or top])


def plaque(group, title, caption, loc, width, height, angle=0, color='Guide Board Green', trim='Porcelain White'):
    face = frame_box(group,loc,(width,.09,height),color,angle,.043,trim)
    words(group,title,(*face[:2],face[2]+height*.124),width*.87,height*.33,angle=angle)
    words(group,caption,(*face[:2],face[2]-height*.256),width*.81,height*.124,angle=angle)


def ring(group,center,outer,minor,mat,axis=(0,1,0),striped=None):
    # Profile lies normal to the mounting axis, with optional quartered livery.
    rot=Vector(axis).to_track_quat('Z','Y'); c=Vector(center); n,m=32,8
    verts=[];faces=[];colors=[]
    for i in range(n):
        a=2*pi*i/n
        for j in range(m):
            b=2*pi*j/m; r=outer-minor+minor*cos(b)
            verts.append(c+rot@Vector((r*cos(a),r*sin(a),minor*sin(b))))
            faces.append((i*m+j,((i+1)%n)*m+j,((i+1)%n)*m+(j+1)%m,i*m+(j+1)%m));colors.append(striped if striped and i%8<2 else mat)
    add(group,verts,faces,colors)


def build():
    """Vented low-water crossing, with a monsoon staff gauge on either approach."""
    green='River Jade';deep='Riverbed Shingle';stone='Warm Granite';grey='Wet Granite';foam='Pale River Glints';red='Flood Staff Red';bed='Scored Concrete';bank='Earth Bank'
    begin('Lata Kijang | Low Water Ford',(green,'498C87',.27,.11),(deep,'585C50',.96),(stone,'9F9781',.89),(grey,'77796C',.87),(foam,'A6CAC0',.34),(red,'B34B39',.62),(bed,'B3ADA0',.91),(bank,'997855',.97),road=True)
    surface_tile(bed,'Broom finish','asphalt',(169,164,148));route=[(0,y,z) for y,z in [(-16,1.55),(-12,1.55),(-5,.92),(-4,.81),(4,.81),(5,.92),(12,1.55),(16,1.55)]]
    strip('Concrete flood slab',route,-3.5,3.5,-.21,0,bed,stone)
    for s in (-1,1):
        r=route[:4] if s<0 else route[4:];strip('Ramp wearing course',r,-3.50,3.50,.001,.009,ASPH)
        for x in (-3.28,3.28):strip('Edge paint',r,x-.059,x+.059,.012,.018,WHITE)
        for yy,zz in [(14.5,1.57),(10,1.39),(6,1.028)]:
            if yy>12:plate('Centre marks',(0,s*yy),zz,.13,1.38,WHITE)
        # Longitudinal wedge under each sloping approach, including textured shoulders.
        rr=[(0,s*y,z) for y,z in [(4,.60),(5,.71),(12,1.34),(16,1.34)]]
        if s<0:rr.reverse()
        pts=[]
        for _,y,z in rr:pts.extend([(-4.55,y,0),(4.55,y,0),(3.82,y,z),(-3.82,y,z)])
        faces=[(0,1,2,3),tuple(reversed(range(12,16)))];colors=[bank,bank]
        for i in range(3):
            for j in range(4):
                a=4*i+j;b=4*i+(j+1)%4;faces.append((a,a+4,b+4,b));colors.append(bank if j!=2 else stone)
        add('Ramped fill',pts,faces,colors)
    for y in np.linspace(-3.53,3.53,6):
        pts=[(-3.56,y-.29),(3.48,y-.29),(3.85,y),(3.48,y+.29),(-3.56,y+.29),(-4.10,y)]
        slab('Vented cutwater webs',pts,.02,.60,grey)
    for y in np.linspace(-3.8,3.8,34):plate('Transverse traction grooves',(0,y),.814,6.84,.026,grey)
    # Faceted shallows are embedded scenery, not transparent alpha-blended glass.
    rng=np.random.default_rng(511);v=[];f=[];m=[];water=[green]
    for i,col in enumerate(['4A9089','508F88','51968F']):
        name=f'Shoal Tint {i+1}';material(name,col,.31,.10);water.append(name)
    for ix in range(21):
        for iy in range(11):
            x=-9+ix*.90;y=(iy-5)*.82+.20*sin(x*.8)+.16*cos(x*.53+iy*.26);v.append((x,y,.29+.018*cos(x*2+y*3)+rng.uniform(-.008,.008)))
    for ix in range(20):
        for iy in range(10):
            a=ix*11+iy;f.extend([(a,a+11,a+1),(a+11,a+12,a+1)]);m.extend([rng.choice(water),rng.choice(water)])
    add('River surface',v,f,m)
    outline=[v[11*i][:2] for i in range(21)]+[v[11*i+10][:2] for i in range(20,-1,-1)]
    slab('Cutaway riverbed',outline,0,.272,deep); rim=[v[11*i] for i in range(21)]+[v[11*i+10] for i in range(20,-1,-1)]
    for a,b in zip(rim,rim[1:]+rim[:1]):add('Waterline',[(a[0],a[1],.268),(b[0],b[1],.268),b,a],[(0,1,2,3)],green)
    for side in (-1,1):
        for sign in (-1,1):
            shoal=[(sign*x,side*y) for x,y in [(3.8,3.6),(5.1,2.8),(6.2,2.81),(7.41,3.59),(8.89,3.71),(8.92,4.30),(3.8,4.39)]]
            slab('Gravel bars',shoal,.15,.343,stone,grey)
            for j in range(9):
                x=sign*rng.uniform(4.21,8.61);y=side*rng.uniform(3.65,4.02);fern('Riverbank ferns',x,y,.338,rng.uniform(.27,.66),401+j+int(x*x))
    for s in (-1,1):
        for j in range(27):
            x=s*rng.uniform(3.85,8.88);y=(-1 if j%2 else 1)*rng.uniform(2.60,4.04) if j<20 else rng.uniform(-2.25,2.25);r=rng.uniform(.10,.52)
            oval_rock('River boulders',x,y,.21,r*1.22,r,r*rng.uniform(.56,1.25),504+j+31*(s+1),[stone,grey,deep]);
            if j%2==0:plate('Ripples',(x+r*1.22,y),.332,.29+r*.49,.031,foam,.11*sin(y))
        y=s*4.7;x=s*3.62
        box('Depth gauge base',(x,y,.795),(.42,.40,.37),stone,.048);box('Graduated flood staff',(x,y,1.79),(.28,.091,1.91),'Porcelain White',.012)
        for j in range(18):
            box('Staff graduations',(x-.062,y-.053,.93+j*.10),(.152 if j%5==0 else .089,.019,.038),red,.003)
        for j,n in enumerate(['0','0.5','1','1.5']):words('Staff numerals',n,(x+.050,y-.069,.94+j*.50),.119,.093,IRON)
        for yy in (-2,0,2):
            tube('Ford delineators',(s*3.39,yy,.81),(s*3.39,yy,1.62),.06,'Porcelain White',sides=10);tube('Delineator ring',(s*3.39,yy,1.44),(s*3.39,yy,1.58),.062,red,sides=10)
    x=-3.71;y=-8.4;tube('Gauge signpost',(x,y,1.08),(x,y,2.57),.048,ZINC,sides=10);plaque('Gauge sign','ARAS AIR','LATA KIJANG',(x,y,2.40),1.52,.56,0,red)
    road_ports([('North',0,16,1.33,0,7,0),('South',0,-16,1.33,pi,7,0)])
    finish((1.43,-1.38,1.04))

if __name__ == "__main__":
    build()
