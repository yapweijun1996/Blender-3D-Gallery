"""SG/MY Jalan road kit: work zone arrow trailer.

Original geometry, materials and signs; no third-party inputs or downloads.
Rebuild both files with Blender 5.2.3 from any directory:
    blender -b --python-exit-code 1 --python path/to/generate.py
Blender's bundled glTF exporter with Draco is required. The same GLB needs a
Draco decoder at load time. One unit is one metre; Blender +Z is up and glTF
+Y is up. The origin is the base datum, +Y is the nominal Blender road axis,
and all mesh transforms are baked. Road sockets use the 16 m placement grid.
The renderer's stage and lighting are never included in the GLB.
"""

from math import cos, pi, sin
from pathlib import Path
import struct
import tempfile
import zlib

import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view


# All dimensions are in metres. Local +Z is up; glTF export remaps to +Y up.
GRID = 16.0
GRADE = 0.22
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


def begin(name, *materials, road=False):
    setup(name)
    palette(road)
    for spec in materials:
        material(*spec)


def beam(group, a, b, w, d, mat, chamfer=.02):
    a, b = Vector(a), Vector(b)
    box(group, (a+b)/2, (w, d, (b-a).length), mat, chamfer, axis=b-a)


def tire(cx,cy,cz):
    # Revolved hollow tyre shell; the wheel hub closes the visible inner ring.
    n = 24
    section = [(-.098,.197),(-.119,.238),(-.104,.286),(-.072,.320),(.072,.320),
               (.104,.286),(.119,.238),(.098,.197),(.055,.188),(-.055,.188)]
    verts = [(cx+x,cy+r*cos(j*2*pi/n),cz+r*sin(j*2*pi/n))
             for x,r in section for j in range(n)]
    faces = [(i*n+j,i*n+(j+1)%n,((i+1)%len(section))*n+(j+1)%n,
              ((i+1)%len(section))*n+j) for i in range(len(section)) for j in range(n)]
    add('Rubber Tyres',verts,faces,'Tyre Rubber')
    tube('Wheel Hubs',(cx-.103,cy,cz),(cx+.103,cy,cz),.203,'Galvanised Steel',sides=20)
    sign = 1 if cx>0 else -1
    tube('Wheel Cap',(cx+.096*sign,cy,cz),(cx+.128*sign,cy,cz),.087,'Foundry Charcoal',sides=14)
    for i in range(6):
        a = i*pi/3
        y,z = cy+.128*cos(a),cz+.128*sin(a)
        tube('Wheel Nuts',(cx+.101*sign,y,z),(cx+.118*sign,y,z),.020,'Iron Oxide Primer',sides=6)
    for i in range(24):
        a = (i+.5)*pi/12
        for x in (-.043,.043):
            c = (cx+x,cy+.313*cos(a),cz+.313*sin(a))
            box('Tyre Tread Blocks',c,(.066,.048,.011),'Tyre Rubber',0,axis=(0,cos(a),sin(a)))


def build():
    """Portable solar highway arrow board, deployed with stabilisers down.

    Facing Blender -Y for approach traffic in +Y. Standalone equipment, no brand.
    """
    begin('Selat Highway - Work-Zone Arrow Trailer',('Traffic Orange Powdercoat','CE6732',.60,.10),
          ('Retroreflective White','F4EBDD',.60), ('Lamp Board Black','1C2428',.73),
          ('Amber Arrow Optic','FFB132',.38,0,1.2),('Off Arrow Optic','4C4230',.56),
          ('Tyre Rubber','303338',.89),('Solar Cell Indigo','293E68',.32,.37),
          ('Solar Cell Divider','738DAD',.49,.22))
    for x in (-.60,.60):
        box('Chassis Rails',(x,.05,.445),(.11,2.44,.14),'Galvanised Steel',.020)
    for y in (-1.12,.05,1.15):
        box('Chassis Crossmembers',(0,y,.446),(1.29,.118,.124),'Galvanised Steel',.017)
    tube('Axle and Suspension',(-.82,.28,.32),(.82,.28,.32),.052,'Iron Oxide Primer',sides=12)
    for x in (-.805,.805):
        tire(x,.28,.32)
        curve = [(x,.28+.396*cos(i*pi/12),.32+.396*sin(i*pi/12)) for i in range(13)]
        for a,b in zip(curve,curve[1:]):
            beam('Formed Mudguards',a,b,.289,.036,'Traffic Orange Powdercoat',.008)
    for x in (-.58,.58):
        beam('A Frame Towbar',(x,1.17,.455),(0,2.29,.422),.095,.091,'Galvanised Steel',.015)
    box('Tow Coupler',(0,2.28,.435),(.163,.36,.105),'Iron Oxide Primer',.024)
    tube('Jockey Stand',(.15,1.83,.08),(.15,1.83,.68),.041,'Galvanised Steel',sides=10)
    tube('Jockey Wheel',(.107,1.83,.084),(.193,1.83,.084),.084,'Tyre Rubber',sides=16)
    for s in (-1,1):
        for y in (-.94,1.08):
            beam('Deployed Corner Jacks',(s*.59,y,.46),(s*1.04,y,.22),.088,.084,'Iron Oxide Primer',.012)
            tube('Deployed Corner Jacks',(s*1.03,y,.028),(s*1.03,y,.295),.033,'Galvanised Steel',sides=8)
            box('Jack Pads',(s*1.03,y,.028),(.184,.16,.056),'Iron Oxide Primer',.024)
        box('Reflective Fender Markers',(s*.80,-.154,.465),(.175,.053,.07),'Warning Enamel Red',.011)
        box('Upright Frame',(s*.66,-.51,1.37),(.123,.127,1.84),'Traffic Orange Powdercoat',.016)
        beam('Rear Backstays',(s*.58,.98,.494),(s*.66,-.52,1.79),.092,.075,'Galvanised Steel',.010)
    box('Battery and Switch Box',(0,.51,.641),(.95,.58,.31),'Traffic Orange Powdercoat',.051)
    box('Battery and Switch Box',(0,.48,.802),(1.01,.62,.068),'Iron Oxide Primer',.023)
    board = (0,-.62,1.958)
    box('Arrow Board Frame',board,(2.08,.151,1.15),'Traffic Orange Powdercoat',.046)
    box('Arrow Board Back',(0,-.542,1.958),(1.91,.058,.98),'Iron Oxide Primer',.022)
    box('Optic Board',(0,-.707,1.958),(1.83,.045,.89),'Lamp Board Black',.023)
    for s in (-1,1):
        for z in (1.51,2.407):
            for i in range(5):
                x = s*(.925-i*.15)
                pts = [(x-s*.045,-.707,z+.045), (x+s*.032,-.707,z+.045),
                       (x+s*.065,-.707,z-.045), (x-s*.013,-.707,z-.045)]
                add('Border Reflective Slashes',pts,[(0,1,2,3)] if s<0 else [(3,2,1,0)],'Retroreflective White')
    # Live right directional arrow plus dormant left-direction optics on a shared board.
    lamps = set([(i,0) for i in range(-4,5)])
    lamps.update((s*i,j) for s in (-1,1) for i,j in [(1,-3),(2,-2),(3,-1),(3,1),(2,2),(1,3)])
    for i,j in sorted(lamps):
        x,z = i*.181,1.958+j*.115
        tube('LED Bezel Rings',(x,-.721,z),(x,-.773,z),.056,'Foundry Charcoal',.054,sides=12)
        tube('Directional LED Optics',(x,-.771,z),(x,-.788,z),.037,
             'Amber Arrow Optic' if j==0 or i>0 else 'Off Arrow Optic',.031,sides=12)
    face = frame_box('Work Zone Notice',(0,-.659,1.095),(1.57,.11,.465),'Traffic Orange Powdercoat',inset=.039)
    words('Work Zone Lettering','AWAS', (face[0],face[1],face[2]+.065),.94,.170,'Foundry Charcoal')
    words('Work Zone Lettering','KERJA JALAN', (face[0],face[1],face[2]-.101),1.30,.086,'Foundry Charcoal')
    # Panel on the rear stays tilted above the arrow board, with inset cell geometry.
    def solar(a,b,off):
        d = Vector((0,.94,-.342)); n = Vector((0,.342,.94))
        return Vector((a,.20,2.55))+b*d+off*n
    top = [solar(a,b,0) for a,b in [(-.74,-.38),(.74,-.38),(.74,.38),(-.74,.38)]]
    bottom = [p - Vector((0,.342,.94))*.044 for p in top]
    loft('Solar Module Frame',bottom+top,4,'Galvanised Steel')
    for j in range(4):
        for i in range(8):
            a,b = -.698+.175*i,-.337+.174*j
            pts = [solar(a+dx,b+dy,.003) for dx,dy in [(0,0),(.162,0),(.162,.154),(0,.154)]]
            add('Solar Cells',pts,[(0,1,2,3)],'Solar Cell Indigo')
            for v in (.027,.067,.107):
                pts = [solar(a+dx,b+v+dy,.004) for dx,dy in [(0,0),(.162,0),(.162,.003),(0,.003)]]
                add('Solar Cell Busbars',pts,[(0,1,2,3)],'Solar Cell Divider')
    for x in (-.56,.56):
        beam('Solar Panel Stays',(x,-.51,2.26),solar(x,-.28,-.031),.051,.051,'Galvanised Steel',.008)
        beam('Solar Panel Stays',(x,.42,.49),solar(x,.28,-.033),.054,.054,'Galvanised Steel',.009)
    finish((1.55,-2.42,1.53))


if __name__ == "__main__":
    build()
