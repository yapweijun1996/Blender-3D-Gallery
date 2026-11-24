"""Roadside harbour bell on a timber jetty frame commemorating the old Kuala Kedah landing.

Original static SG/MY Jalan kit asset. All geometry, signage and surfaces are
procedural, in metres. No external inputs. Blender 5.2: run blender -b
--python-exit-code 1 --python generate.py to rebuild the Draco GLB and preview.
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

    if kind not in ('concrete',):
        tone = (noise(4) * 2.2 + noise(16) * 1.8 + noise(77) * 3.3
                + noise(222) * 4.5 + rng.normal(0, 3.5, (n, n)))
        stone = rng.random((n, n))
        tone += np.where(stone > .978, (stone - .978) * 640, 0)
        base = {'asphalt':[55,59,61], 'oxide':[162,78,57], 'cast':[182,178,160]}[kind]
        if kind == 'cast':
            tone *= .52
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


def setup(name):
    global ROOT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    ROOT = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(ROOT)
    ROOT['asset_id'] = Path(__file__).resolve().parent.name
    ROOT['origin_note'] = 'Base datum at local (0, 0, 0), local +Z up.'
    ROOT['kit'] = 'SG/MY Jalan modular road kit'
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
    scene.render.resolution_x, scene.render.resolution_y = 720, 576
    scene.render.resolution_percentage = 100
    bpy.context.view_layer.update()
    # Fit actual mesh vertices, not an oversized axis-aligned box around curved pieces.
    inverse = cam.rotation_euler.to_matrix().transposed()
    projected = np.array([tuple(inverse @ (v.co-target))[:2] for o in objs for v in o.data.vertices])
    low, high = projected.min(axis=0), projected.max(axis=0)
    mid = (low+high)*.5
    cam.location += cam.rotation_euler.to_matrix() @ Vector((mid[0],mid[1],0))
    cam.data.ortho_scale = max((high[0]-low[0])/.88, (high[1]-low[1])*720/576/.84)
    bpy.ops.mesh.primitive_plane_add(size=span*250, location=(0,0,-.001))
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
    scene.cycles.samples = 8
    scene.cycles.adaptive_threshold = .06
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 3
    scene.render.threads_mode, scene.render.threads = 'FIXED', 3
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
    indexed_preview(out / "preview.png")


def texture(mat, kind):
    nt = MATS[mat].node_tree
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = tile_image(kind.title() + ' - Kiln Finish',kind)
    nt.links.new(tex.outputs['Color'],nt.nodes['Principled BSDF'].inputs['Base Color'])


# The palette uses sRGB paint references; all dimensions below are metres.
INK = 'Midnight Enamel'
TEAL = 'Kingfisher Teal'
BRASS = 'Aged Brass'
GOLD = 'Harvest Enamel'
CREAM = 'Warm Porcelain'
IRON = 'Blued Iron'
STEEL = 'Satin Alloy'
RED = 'Vermilion'
CLAY = 'Baked Clay'
STONE = 'Honed Aggregate'
WOOD = 'Oiled Chengal'
PALE = 'Celadon'
LENS = 'Lemon Optic'

def finishes():
    for spec in [(INK,'183743',.48,.32),(TEAL,'007d79',.46,.24),(BRASS,'b8864c',.34,.66),
                 (GOLD,'efa92e',.46,.18),(CREAM,'f0e3c5',.56,.06),(IRON,'30383d',.62,.45),
                 (STEEL,'9eb2b4',.34,.66),(RED,'cb4b31',.5,.14),(CLAY,'aa5e43',.78,0),
                 (STONE,'b6afa0',.89,.05),(WOOD,'7c4530',.57,.08),(PALE,'9ad1bf',.49,.12),
                 (LENS,'ffe778',.34,.1,.46)]:
        material(*spec)
    # A packed, repeatable aggregate tile gives even a close-up plinth visible grain.
    texture(STONE, 'cast')


def spin(group, x, y, profile, mat, n=32, phase=0):
    loft(group, [(x+r*cos(phase+i*2*pi/n), y+r*sin(phase+i*2*pi/n), z)
                 for z,r in profile for i in range(n)], n, mat)


def face(group, poly, y, depth, mat):
    # Extrude a silhouette in the X/Z plane. The front reads toward local -Y.
    poly = ccw(list(poly))
    loft(group, [(x,dy,z) for dy in (y+depth,y) for x,z in poly], len(poly), mat)


def text(group, body, x,y,z, width,height, mat=CREAM, angle=0):
    words(group,body,(x,y,z),width,height,mat,angle)


def chain(group, path, radius, mat, n=12):
    for p,q in zip(path,path[1:]):
        tube(group,p,q,radius,mat,sides=n)


def bar(group,a,b,w,d,mat):
    a,b = Vector(a),Vector(b)
    box(group,(a+b)*.5,(w,d,(b-a).length),mat,min(w,d)*.16,axis=b-a)


def indexed_preview(path):
    """Re-encode the Blender render with an adaptive 8-bit palette, without Pillow."""
    img = bpy.data.images.load(str(path), check_existing=False)
    # Read the render's display-referred byte values, not scene-linear data.
    img.colorspace_settings.name = 'Non-Color'
    w,h = img.size
    rgb = np.empty(w*h*4,dtype=np.float32)
    img.pixels.foreach_get(rgb)
    v = rgb.reshape(h,w,4)[::-1,:,:3].clip(0,1)
    rng = np.random.default_rng(19)
    u = np.rint(255*v + rng.uniform(-1.4,1.4,(h,w,1))).clip(0,255).astype(np.int32)
    bpy.data.images.remove(img)
    keys = ((u[:,:,0]>>1)<<14) | ((u[:,:,1]>>1)<<7) | (u[:,:,2]>>1)
    unique, index = np.unique(keys,return_inverse=True); keys=index.reshape(h,w)
    f = np.bincount(keys.ravel()); used = np.arange(len(unique))
    avg = np.stack([np.bincount(keys.ravel(),weights=c.ravel())/f
                    for c in u.transpose(2,0,1)],axis=1)
    def stats(ix):
        mass = f[used[ix]]
        center = np.average(avg[ix],axis=0,weights=mass)
        variance = (mass[:,None]*(avg[ix]-center)**2).sum(axis=0)
        axis = int(variance.argmax())
        return variance[axis],axis,ix,center
    groups=[stats(np.arange(len(used)))]
    while len(groups)<256:
        i=max(range(len(groups)),key=lambda k: groups[k][0])
        score,axis,ix,center = groups.pop(i)
        if score<=0:
            groups.append((score,axis,ix,center));break
        ix=ix[np.argsort(avg[ix,axis])]; weight=np.cumsum(f[used[ix]])
        cut=min(len(ix)-1,1+weight.searchsorted(weight[-1]/2))
        groups.extend([stats(ix[:cut]),stats(ix[cut:])])
    palette=[]; lut=np.zeros(len(f),dtype=np.uint8)
    for i,(_,_,ix,center) in enumerate(groups):
        palette.extend(center.round().astype(int))
    colors = np.array(palette).reshape(-1,3)
    for k in range(0,len(avg),256):
        lut[k:k+256] = ((avg[k:k+256,None,:]-colors)**2).sum(axis=2).argmin(axis=1)
    def chunk(tag,payload):
        return struct.pack('>I',len(payload))+tag+payload+struct.pack('>I',zlib.crc32(tag+payload))
    png=(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,3,0,0,0))
         +chunk(b'PLTE',bytes(palette))+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row.tobytes() for row in lut[keys]),9))+chunk(b'IEND',b''))
    if len(png)>250000: raise ValueError('Preview exceeds PNG budget')
    path.write_bytes(png)


def build():
    setup('Kuala Kedah - Landing Bell'); finishes()
    # Masonry piers leave the ground between uprights open.
    for s in [-1,1]:
        x=.78*s
        box('Pier stones',(x,0,.104),(.61,.698,.208),STONE,.051)
        box('Rebated plinths',(x,0,.247),(.499,.563,.088),INK,.025)
        box('Pier necks',(x,0,.390),(.430,.490,.217),STONE,.036)
        box('Chengal uprights',(x,0,1.397),(.243,.28,1.824),WOOD,.019)
        for z in [.527,2.194]:box('Forged straps',(x,0,z),(.257,.297,.087),INK,.010)
        for z in [.528,2.194]:tube('Strap studs',(x,-.153,z),(x,-.172,z),.027,BRASS,sides=12)
        bar('Knee braces',(x,0,1.683),(x-s*.51,0,2.221),.106,.124,WOOD)
    face('Carved lifting beam',[(-1.094,2.202),(-1.18,2.446),(-.90,2.414),(-.52,2.372),(.52,2.372),(.90,2.414),(1.18,2.446),(1.094,2.202)],-.162,.324,WOOD)
    for i in [-1,1]:
        face('Beam end inlay',[(i*.78,2.308),(i*.98,2.358),(i*1.080,2.381),(i*1.025,2.300),(i*.917,2.332)],-.165,.009,BRASS)
    box('Bell headstock',(0,.012,2.098),(.435,.234,.173),INK,.027)
    for x in [-.16,.16]:bar('Hanger straps',(x,-.097,2.24),(x,-.097,2.022),.050,.040,BRASS)
    spin('Bell crown',0,0,[(1.907,.108),(2.00,.089),(2.059,.082)],BRASS)
    # Closed section of the hollow bronze casting: outward path rises from the lip,
    # returns along the inside wall. Keep the throat open to show the clapper.
    profile=[(1.21,.354),(1.232,.381),(1.264,.383),(1.300,.353),(1.36,.304),(1.46,.260),
             (1.58,.226),(1.75,.207),(1.835,.190),(1.893,.157),(1.929,.102),(1.942,.050),
             (1.900,.050),(1.886,.105),(1.842,.151),(1.765,.174),(1.574,.194),(1.439,.231),
             (1.331,.281),(1.254,.327)]
    n=64; vs=[(r*cos(i*2*pi/n),r*sin(i*2*pi/n),z) for z,r in profile for i in range(n)]
    fs=[]
    for j in range(len(profile)):
        m=(j+1)%len(profile)
        fs.extend([(j*n+i,j*n+(i+1)%n,m*n+(i+1)%n,m*n+i) for i in range(n)])
    add('Cast bronze bell',vs,fs,BRASS)
    for z,r in [(1.287,.367),(1.335,.325),(1.751,.210),(1.778,.205)]:
        levels=[(z,r-.006),(z+.005,r+.003),(z+.012,r-.007)]
        add('Turned mouldings',[(rad*cos(i*2*pi/n),rad*sin(i*2*pi/n),h) for h,rad in levels for i in range(n)],
            [(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(2) for i in range(n)],BRASS)
    spin('Iron tongue',0,0,[(1.11,.025),(1.13,.054),(1.177,.084),(1.227,.067),(1.25,.031),(1.87,.021)],IRON)
    # Two strands of a laid rope converge on the decorative turk's head knot.
    for off in [0,pi]:
        path=[]
        for i in range(56):
            t=i/55; a=off+12*pi*t
            path.append((.082*sin(pi*t)+.010*cos(a),-.037*sin(2*pi*t)+.010*sin(a),1.126-.488*t))
        chain('Bell pull',path,.0105,CREAM,8)
    spin('Rope knot',0,0,[(.603,.019),(.626,.037),(.655,.038),(.676,.019)],CREAM,16)
    box('Memorial panel',(0,-.246,.397),(1.623,.077,.292),TEAL,.018)
    text('Quayside inscription','LOCENG  PELABUHAN',0,-.288,.448,1.464,.095)
    text('Quayside inscription','K U A L A   K E D A H     /     J E T I   L A M A',0,-.288,.331,1.392,.041,GOLD)
    finish((1.21,-3.22,1.04))


if __name__ == "__main__":
    build()
