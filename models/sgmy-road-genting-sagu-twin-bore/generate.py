"""SG/MY Jalan road kit: genting sagu twin bore.

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


def beam(group, a, b, w, d, mat, chamfer=.02):
    a, b = Vector(a), Vector(b)
    box(group, (a+b)/2, (w, d, (b-a).length), mat, chamfer, axis=b-a)


def plate(group, xy, z, width, length, mat, angle=0):
    slab(group, rect_points(xy, width, length, angle), None, z, mat)


def swept_y(group, stations, section, mats):
    """Sweep a closed (X,Z) section counterclockwise as seen from -Y."""
    n = len(section)
    points = [(shift+x, y, h+z) for y, shift, h in stations for x, z in section]
    ring_faces = [(i+j, i+n+j, i+n+(j+1)%n, i+(j+1)%n)
                  for i in range(0, len(points)-n, n) for j in range(n)]
    add(group, points, [tuple(range(n)), *ring_faces,
                        tuple(reversed(range(len(points)-n, len(points))))],
        [mats[0], *mats*(len(stations)-1), mats[0]])


def indexed_preview(path):
    """Median-cut the rendered display pixels; no external PNG utilities required."""
    image = bpy.data.images.load(str(path), check_existing=False)
    image.colorspace_settings.name = 'Non-Color'
    w,h = image.size
    buf = np.empty(w*h*4, np.float32)
    image.pixels.foreach_get(buf)
    rgb = (np.clip(buf.reshape(h,w,4)[::-1,:,:3],0,1)*255+.5).astype(np.int32).reshape(-1,3)
    bpy.data.images.remove(image)
    keys = (rgb[:,0]//2)*16384+(rgb[:,1]//2)*128+rgb[:,2]//2
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
    # Median cut chooses representative colours; then reassign by true colour
    # distance to avoid box-boundary casts in near-neutral sky and concrete.
    centers=np.asarray(pal,dtype=np.float32)
    for start in range(0,len(colors),512):
        delta=(colors[start:start+512,None,:]-centers)*[.90,1.0,.91]
        lut[start:start+512]=np.argmin((delta*delta).sum(axis=2),axis=1)
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


def arrow(x,y,z,color=WHITE,scale=1,angle=0):
    p=[(-.10,-1.22),(.10,-1.22),(.10,.25),(.43,.19),(0,1.21),(-.43,.19),(-.10,.25)]
    slab('Direction arrows',[place((x,y),(a*scale,b*scale),angle) for a,b in p],None,z,color)


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
    """Paired two-lane bores with lined vaults, a patterned headwall and lane-control lamps."""
    tile='Glazed Jade Tile';blue='Petrol Blue Glaze';light='Celadon Glaze';chalk='Limestone Facing';lining='Soffit Concrete';terra='Weathered Clay'
    begin('Genting Sagu | Twin Bore Portal',(tile,'529889',.46,.12),(blue,'275D69',.48,.13),(light,'A5BE9B',.56),(chalk,'C8BFA5',.88),(lining,'938D7C',.95),(terra,'9B7A5C',.95),road=True)
    road_ports([('South',0,-16,0,pi,14,0),('North',0,16,0,0,14,0)])
    ROOT['median_width_m']=2.6
    for s in (-1,1):
        x=s*4.8;rect('Directional carriageways',x,0,0,GRADE,7,32,ASPH,'Asphalt Cut Edge')
        for t in (-1,1):
            plate('Fog lines',(x+t*3.25,0),PAINT,.13,32,WHITE)
            rect('Emergency margins',x+t*3.71,0,0,.34,.42,32,'Brushed Footway Pavers',PCC)
        for y in np.arange(-14,16,4):plate('Lane lines',(x,y),PAINT,.115,1.72,WHITE)
        for t in (-1,1):arrow(x+t*1.64,s*-12.8,PAINT,scale=1.06,angle=0 if s<0 else pi)
        # Cross section from invert to crown. Span between bores remains solid.
        a=4.2;b=3.33;spring=2.69;n=28
        inner=[(x+a,0),(x+a,spring)]+[(x+a*cos(pi*j/n),spring+b*sin(pi*j/n)) for j in range(1,n+1)]+[(x-a,0)]
        outer=[(x+4.8,0),(x+4.8,spring)]+[(x+4.8*cos(pi*j/n),spring+(b+.52)*sin(pi*j/n)) for j in range(1,n+1)]+[(x-4.8,0)]
        for j,(ia,ib,oa,ob) in enumerate(zip(inner,inner[1:],outer,outer[1:])):
            sect=[ia,oa,ob,ib];swept_y('Vault lining',[(-8.88,0,0),(8.88,0,0)],sect,[lining,chalk,lining,lining])
            for e in (-1,1):
                y=e*9.0;sec=[ia,oa,ob,ib];mat=tile if j in (0,n+1) else (chalk if j%4 else light)
                swept_y('Portal voussoirs',[(y-.16,0,0),(y+.16,0,0)],sec,[mat]*4)
        # Horizontal spandrel course follows the holes: no opaque solid blocking a bore.
        curve=outer[1:-1]
        for j,((xa,za),(xb,zb)) in enumerate(zip(curve,curve[1:])):
            sect=[(xb,zb),(xa,za),(xa,7.48),(xb,7.48)]
            swept_y('Headwall spandrels',[(-8.92,0,0),(8.92,0,0)],sect,[chalk,lining,chalk,lining])
        for t in (-1,1):
            xx=x+t*4.11
            for k in range(8):
                yy=-7.85+k*2.23
                box('Tunnel kick tiles',(xx,yy,1.02),(.098,2.18,1.61),light,.012)
                box('Guidance stripe',(xx-t*.052,yy,1.46),(.023,2.18,.16),tile,.004)
                box('Evacuation lights',(xx-t*.087,yy,2.07),(.106,.48,.12),'Porcelain White',.017)
        # Crossing arrows are luminous green, the opposite direction shows a red X.
        for e in (-1,1):
            y=e*9.24;ang=0 if e<0 else pi
            for t in (-1,1):
                xx=x+t*1.62;zz=5.19
                beam('Lane control hangers',(xx,y-e*.12,zz),(xx,y-e*.12,5.96),.10,.11,IRON)
                f=frame_box('Lane control boxes',(xx,y,zz),(.81,.19,.69),IRON,ang,.04,ZINC)
                fy=f[1]+e*.004
                if e==s:
                    for u,v in [((0,.19),(0,-.18)),((-.17,-.02),(0,-.18)),((.17,-.02),(0,-.18))]:beam('Lane arrows',(xx+u[0],fy,zz+u[1]),(xx+v[0],fy,zz+v[1]),.072,.047,'Signal Green Lens',.007)
                else:
                    for d in (-1,1):beam('Lane crosses',(xx-.15,fy,zz+d*.16),(xx+.15,fy,zz-d*.16),.074,.047,'Signal Red Lens',.007)
    # The woven two-colour lozenges are individual glazed stoneware insets.
    for e in (-1,1):
        y=e*9.09;ang=0 if e<0 else pi
        box('Frieze field',(0,y,6.99),(19.19,.38,.83),blue,.035)
        for k in range(-13,14):
            xx=k*.70
            if abs(xx)<2.32:continue
            for dx,z,m in [(-.16,7.09,tile),(.16,6.88,light)]:
                pts=[(xx+dx,y+e*.20,z+.195),(xx+dx-.29,y+e*.20,z),(xx+dx,y+e*.20,z-.195),(xx+dx+.29,y+e*.20,z)]
                add('Woven facade tiles',pts,[tuple(range(4)) if e<0 else (3,2,1,0)],m)
        f=frame_box('Portal lettering',(0,y+e*.22,6.99),(4.63,.10,.68),blue,ang,.047,light)
        words('Portal lettering','GENTING SAGU',f,4.25,.38,angle=ang)
    rect('Roof coping',0,0,7.48,7.64,19.34,18.1,chalk)
    # Vegetated cut-and-cover embankment. It narrows to meet the two tiled
    # portal faces but flares into stepped laterite shoulders midway through.
    surface_tile('Island Grass','Grass sward','asphalt',(106,133,78))
    surface_tile(terra,'Embankment earth','asphalt',(146,112,84))
    verts=[];faces=[];mats=[];ys=np.linspace(-8.61,8.61,25)
    for y in ys:
        t=max(0,cos(y*pi/17.22))**.68
        positive=[(0,7.71+t*(1.48+.12*cos(y))), (3.65,7.69+t*1.34),(7.72,7.68+t*.94),(9.54,7.68+.55*t),(9.72+1.8*t,6.04+.25*t),(9.74+2.65*t,5.92),(9.76+3.81*t,3.12),(9.79+4.59*t,2.95),(9.82+6.04*t,0)]
        sec=[(-x,z) for x,z in positive[1:][::-1]]+positive
        verts.extend([(x,y,z) for x,z in sec]);n=len(sec)
    colors=[terra,'Island Grass',terra,'Island Grass',terra,'Island Grass','Island Grass','Island Grass']
    colors+=colors[::-1]
    for i in range(len(ys)-1):
        for j in range(n-1):
            k=i*n+j;faces.append((k,k+1,k+1+n,k+n));mats.append(colors[j])
    # Close exposed sections above the coping and beside the headwalls.
    for i,e in [(0,-1),(len(ys)-1,1)]:
        for j in range(n-1):
            a,b=verts[i*n+j:i*n+j+2];base=7.64 if max(abs(a[0]),abs(b[0]))<9.65 else 0
            # The short sliver crossing the coping is already backed by concrete.
            if min(abs(a[0]),abs(b[0]))<9.65 and not base:continue
            q=list(dict.fromkeys([a,b,(b[0],b[1],base),(a[0],a[1],base)]));order=tuple(range(len(q)))
            add('Portal earth faces',q,[order[::-1] if e<0 else order],terra)
    add('Terraced overburden',verts,faces,mats)
    for s in (-1,1):
        for j in range(10):
            y=-6.94+j*1.48+.09*sin(j);t=cos(y*pi/17.22)**.68;ledge=j%3
            x,z=((9.74+2.35*t,5.94),(9.78+4.30*t,3.01),(7.72,7.68+t*.94))[ledge]
            fern('Fern banks',s*x,y,z,.79+.24*(1+cos(j)),213+j*3+s)
    # Exposed stone on the broad lower benches breaks up the wet clay slopes.
    for side in (-1,1):
        for j in range(16):
            y=-6.8+j*.88;t=cos(y*pi/17.22)**.68
            if j in (3,4,10,14):continue
            x=side*(9.78+(4.19+.13*sin(j))*t);r=.34+.14*cos(j*2.13)
            oval_rock('Laterite bench outcrops',x,y,2.97,r*.67,r,r*.61,404+j,['Warm Precast Concrete',lining,terra])
    rect('Median plinth',0,0,0,.29,1.75,32,PCC)
    for e in (-1,1):
        box('Median bollard footing',(0,e*14.15,.39),(.70,.90,.20),PCC,.045)
        box('Median bollards',(0,e*14.15,.94),(.36,.39,1.06),'Reflective Amber',.058)
        for z in (.75,1.13):box('Median bollards',(0,e*14.15,z),(.369,.399,.14),IRON,.018)
    finish((.82,-2.16,.78))


if __name__ == "__main__":
    build()
