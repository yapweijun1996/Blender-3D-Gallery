"""SG/MY Jalan road kit: muar azur swing span.
A closed, equal-arm swing bridge on a toothed circular drum pier.

Original procedural meshes and packed textures; all mesh transforms baked.
Rebuild with Blender 5.2: blender -b --python-exit-code 1 --python generate.py
Writes model.glb (Draco decoder required) and a studio preview.png beside the script.
Metres, Z up, base datum at Z=0. Socket local +Y faces out; socket Z is the
road base datum, with a 0.22 m wearing course offset unless noted.
"""

from math import atan2, ceil, cos, hypot, pi, sin, sqrt
from pathlib import Path
import struct
import tempfile
import zlib
import bpy
import numpy as np
from mathutils import Vector
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
    ROOT['category'] = 'road'
    ROOT['rights_note'] = 'Original scripted geometry and procedural surfaces; no external assets.'
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
    cam.data.ortho_scale = max((max(xs)-min(xs))/.88, (max(ys)-min(ys))*768/600/.84)
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
    scene.cycles.samples = 10
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
    compact_png(out / 'preview.png')


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


def plate(group, xy, z, width, length, mat, angle=0):
    slab(group, rect_points(xy, width, length, angle), None, z, mat)


def sockets(length,datum=0,width=7,walk=0):
    road_ports([('South',0,-length/2,datum,pi,width,walk),('North',0,length/2,datum,0,width,walk)])
AS = 'Dense Graded Asphalt'
CUT = 'Asphalt Cut Edge'
CON = 'Warm Precast Concrete'
PAV = 'Brushed Footway Pavers'
WH = 'Road Paint White'
YL = 'Road Paint Yellow'
MET = 'Galvanised Steel'
COAL = 'Foundry Charcoal'
MILK = 'Porcelain White'
GOLD = 'Reflective Amber'
BLUE = 'Guide Board Blue'
GREEN = 'Guide Board Green'


def compact_png(filename):
    """Quantize the Blender render in sRGB, using an image-adaptive palette."""
    image = bpy.data.images.load(str(filename), check_existing=False)
    image.colorspace_settings.name = 'Non-Color'
    w, h = image.size[:]
    data = np.empty(w*h*4, dtype=np.float32)
    image.pixels.foreach_get(data)
    rgb = np.rint(255 * data.reshape(h,w,4)[::-1,:,:3]).clip(0,255).astype(np.int32)
    bpy.data.images.remove(image)
    keys = (rgb[:,:,0]//2)*16384 + (rgb[:,:,1]//2)*128 + rgb[:,:,2]//2
    bins, inverse, weight = np.unique(keys.ravel(), return_inverse=True, return_counts=True)
    rgb = rgb.reshape(-1,3)
    tones = np.stack([np.bincount(inverse, weights=rgb[:,i]) / weight for i in range(3)], axis=1)
    groups = [np.arange(len(bins))]
    for _ in range(8):
        children = []
        for group in groups:
            if len(group) < 2:
                children.append(group)
                continue
            axis = np.argmax(np.ptp(tones[group], axis=0) * [.9,1.1,.85])
            g = group[np.argsort(tones[group,axis])]
            t = np.cumsum(weight[g]**.54)
            split = min(len(g)-1,np.searchsorted(t,t[-1]/2)+1)
            children.extend((g[:split],g[split:]))
        groups = children
    colors = np.array([np.rint(np.average(tones[g],weights=weight[g],axis=0)) for g in groups])
    # Refine the assignment after splitting, in small bounded-memory chunks.
    nearest = np.zeros(len(bins),dtype=np.uint8)
    for step in range(4):
        for i in range(0,len(bins),256):
            diff = tones[i:i+256,None,:] - colors[None,:,:]
            nearest[i:i+256] = ((diff*diff) @ [.9,1.1,.85]).argmin(axis=1)
        if step < 3:
            for idx in range(len(colors)):
                mask = nearest == idx
                if mask.any():colors[idx] = np.rint(np.average(tones[mask],axis=0,weights=weight[mask]**.65))
    pixels = nearest[inverse].reshape(h,w)
    def chunk(tag, payload):
        return struct.pack('>I',len(payload))+tag+payload+struct.pack('>I',zlib.crc32(tag+payload))
    filename.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,3,0,0,0))+chunk(b'PLTE',colors.astype('uint8').tobytes())+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row.tobytes() for row in pixels),9))+chunk(b'IEND',b''))


def align_three_cells():
    """A three-cell tile has an off-centre origin so both ends land on grid lines."""
    for batch in BATCHES.values():
        batch.verts=[(x,y+8,z) for x,y,z in batch.verts]
    for locator in ROOT.children:locator.location.y+=8


def block(group,x,y,bottom,w,d,h,mat,bevel=.028):
    box(group,(x,y,bottom+h/2),(w,d,h),mat,bevel)


def stick(group,a,b,w,d,mat,bevel=.02):
    axis=Vector(b)-Vector(a)
    box(group,(Vector(a)+Vector(b))/2,(w,d,axis.length),mat,bevel,axis=axis)


def pier(x,y,z):
    block('Pile cap',x,y,0,2.05,1.9,.46,CON,.1)
    block('Chamfered pier',x,y,.42,1.06,1.18,z-.74,CON,.13)
    block('Bearing seat',x,y,z-.39,1.5,1.46,.29,CON,.07)
    block('Neoprene bearing',x,y,z-.11,.94,.86,.11,COAL,.01)


def rails(x,y0,y1,z,mat,height=1.06):
    n=ceil((y1-y0)/2.35)
    for i in range(n+1):
        y=y0+(y1-y0)*i/n
        block('Railing feet',x,y,z,.21,.23,.07,MET,.01)
        block('Railing stanchions',x,y,z+.05,.093,.10,height-.05,mat,.01)
    for h,r in [(.41,.035),(.72,.035),(height,.058)]:
        tube('Longitudinal handrails',(x,y0,z+h),(x,y1,z+h),r,mat,sides=8)


def nameboard(x,y,z,angle,label,mat=GREEN,sub=None,w=2.8):
    h=.66 if sub else .42
    p=frame_box('Enamel nameplates',(x,y,z),(w,.11,h),mat,angle,.048)
    words('Nameplate lettering',label,(p[0],p[1],p[2]+(.10 if sub else 0)),w-.26,h*.48,angle=angle)
    if sub: words('Nameplate lettering',sub,(p[0],p[1],p[2]-.17),w-.29,.12,angle=angle)


def straight(length,z=.22,half=3.5,walk=True):
    slab('Running course',rect_points((0,0),half*2,length),z-.22,z,AS,CUT)
    for s in (-1,1):
        plate('Edge lines',(s*(half-.19),0),z+.004,.105,length,YL)
        if walk:
            block('Walkway',s*(half+.875),0,z-.22,1.75,length,.352,PAV,.012)
    for y in np.arange(-length/2+2,length/2,5.33):
        plate('Centre dashes',(0,float(y)),z+.004,.125,2,WH)


def axial_y(group,x,stations,width,mat):
    # Constant-width vertical plate following a variable-height side elevation.
    rows=[(y,x-width/2,x+width/2,t,t) for y,b,t in stations]
    v=[]
    for (y,b,t),(_,a,c,_,_) in zip(stations,rows):v.extend([(a,y,b),(c,y,b),(c,y,t),(a,y,t)])
    f=[(0,1,2,3),tuple(reversed(range(len(v)-4,len(v))))]
    for j in range(0,len(v)-4,4):
        for k in range(4):f.append((j+k,j+4+k,j+4+(k+1)%4,j+(k+1)%4))
    add(group,v,f,mat)


def build():
    """A closed, equal-arm swing bridge on a toothed circular drum pier."""
    teal='Peacock bridge enamel'; cream='Ivory belt course'; brass='Brass running race'
    begin('Muar Azur | Jambatan Putar',(teal,'286B73',.54,.32),(cream,'E5D5AA',.67),(brass,'BA824B',.48,.54),road=True)
    sockets(48,4.8,7,.75);straight(48,5.02,walk=False)
    for lo,hi,r,mat in [(0,.46,4.2,CON),(.44,2.42,3.53,CON),(2.42,2.66,3.88,cream),(2.66,2.95,3.79,COAL),(2.95,3.15,3.73,brass),(3.15,3.52,3.56,teal)]:
        tube('Circular swing pier',(0,0,lo),(0,0,hi),r,mat,sides=64)
    for k in range(48):
        a=2*pi*k/48
        box('Ring gear teeth',(3.76*cos(a),3.76*sin(a),2.95),(.27,.14,.24),brass,.016,a)
    for s in (-1,1):
        x=s*3.71
        stations=[(y,4.65,5.63+1.60*max(0,1-(abs(y)/16)**1.5)) for y in np.linspace(-23.91,23.91,35)]
        axial_y('Fishbelly parapet girders',x,stations,.18,teal)
        axial_y('Flanged top plates',x,[(y,h-.06,h+.08) for y,_,h in stations],.38,cream)
        block('Lower flanges',x,0,4.62,.43,47.85,.15,teal)
        for y in range(-22,23,2):
            h=5.63+1.60*max(0,1-(abs(y)/16)**1.5)
            block('Riveted stiffener blades',x+s*.11,y,4.78,.16,.105,h-4.79,teal,.018)
            for z in (4.92,h-.18):
                tube('Brass rivet heads',(x+s*.19,y,z),(x+s*.22,y,z),.056,brass,sides=8)
        block('Maintenance walk',s*4.36,0,4.69,1.13,48,.29,PAV)
        rails(s*4.82,-23.86,23.86,4.98,teal)
        for y in (-22.5,22.5):pier(s*2.35,y,4.16)
    for y in range(-22,23,2):block('Floor cross bearers',0,y,4.16,9.38,.27,.59,teal)
    for x in (-2,2):block('Centre transfer beams',x,0,3.48,.56,8.3,.73,COAL)
    # A projecting operator bay is fixed to the rotating half, not the riverbed.
    block('Keeper balcony',-5.85,-1,4.60,3.63,3.8,.36,cream,.07)
    for y in (-2.35,.35):stick('Balcony knees',(-3.26,y,3.67),(-7.22,y,4.60),.17,.19,teal)
    for z,h,r,mat in [(4.96,.84,1.56,teal),(5.8,1.13,1.53,'Glass Optics'),(6.93,.16,1.62,cream)]:
        tube('Octagonal control cabin',(-5.91,-1,z),(-5.91,-1,z+h),r,mat,sides=8)
    for j in range(8):
        a=pi*j/4;x=-5.91+1.535*cos(a);y=-1+1.535*sin(a)
        tube('Window mullions',(x,y,5.78),(x,y,6.96),.062,cream,sides=8)
    tube('Keeper lantern roof',(-5.91,-1,7.04),(-5.91,-1,7.94),1.92,teal,.37,8)
    tube('Roof finial',(-5.91,-1,7.94),(-5.91,-1,8.29),.14,brass,.034,10)
    nameboard(3.84,0,6.02,pi/2,'JAMBATAN PUTAR',teal,'MUAR AZUR   /   03',3.56)
    align_three_cells()
    finish((-1.02,-1.28,.96))


if __name__ == "__main__":
    build()
