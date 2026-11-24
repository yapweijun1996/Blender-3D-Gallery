"""Pandan Loop park connector: two-way oxide cycle track, pocket seat and parallel walk.
The 16 m module repeats along Y; ends at (0,-8) and (0,8) are one grid pitch apart.
Cycle clear width 3.0 m; adjoining pedestrian strip stays step-free.

Original SG/MY Jalan kit geometry, procedural surfaces and built-in Blender lettering.
Blender 5.2: blender -b --python-exit-code 1 --python generate.py
Rebuilds model.glb (Draco required) and preview.png in this directory.
Static, metre units, base origin; object geometry and planar metre UVs are baked.
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


def align_ends(normals, directions):
    # Arc chords approximate tangents; exact port normals prevent seam wedges.
    if directions:
        for i, normal in ((0, directions[0]), (-1, directions[1])):
            if normal is not None:
                normals[i] = normal


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


def finishes():
    palette(False)
    for spec in [
        ('Dense Graded Asphalt','353b40',.97,0), ('Asphalt Cut Edge','333a40',.96,0),
        ('Brushed Footway Pavers','aca89f',.93,0), ('Road Paint White','f2eee1',.82,0),
        ('Road Paint Yellow','ebba3e',.82,0), ('Painted Kerb White','d9d6c9',.86,0),
        ('Painted Kerb Black','354045',.88,0), ('Precast Sand','c7bfac',.92,0),
        ('Celadon Enamel','39877e',.47,.34), ('Deep Petrol','164d54',.54,.29),
        ('Marigold','edab41',.48,.18), ('Biscuit','e2d9bd',.77,0),
        ('Terracotta','bc6045',.89,0), ('Oiled Balau','84503b',.62,0),
        ('Harbour Blue','21547e',.54,.24), ('Slate Glass','437683',.21,.30),
        ('Pale Glass','89b8b5',.22,.26), ('Night Ink','23343b',.66,.25),
        ('Warm Lamp','fff0b7',.34,0,.6)]:
        material(*spec)


def texture(mat, kind):
    nt = MATS[mat].node_tree
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = tile_image(kind.title() + ' - Kiln Finish',kind)
    nt.links.new(tex.outputs['Color'],nt.nodes['Principled BSDF'].inputs['Base Color'])


def plaque(group,xy,z,w,h,mat,main,sub='',angle=0):
    face = frame_box(group,(*xy,z),(w,.09,h),mat,angle,inset=.045)
    words(group,main,(face[0],face[1],z+(h*.12 if sub else 0)),w*.88,h*(.34 if sub else .54),angle=angle)
    if sub:
        words(group,sub,(face[0],face[1],z-h*.22),w*.84,h*.17,'Biscuit',angle)


def arrow(group,x,y,z,angle=0,scale=1,mat='Road Paint White'):
    pts = [(-.11,-.82),(.11,-.82),(.11,.12),(.40,.12),(0,.87),(-.4,.12),(-.11,.12)]
    slab(group,[place((x,y),(a*scale,b*scale),angle) for a,b in pts],None,z,mat)


def label(group,body,x,y,z,w,h,mat='Porcelain White',angle=0):
    words(group,body,(x,y,z),w,h,mat,angle)


def build():
    setup('Pandan Loop - Segregated Cycleway'); finishes(); material('Oxide Cycle Resin','a24e39');texture('Oxide Cycle Resin','oxide');texture('Brushed Footway Pavers','concrete')
    material('Young Pandan','81a451'); material('Pandan Green','447353');material('Dark Mulch','514537')
    # A centred 16 m tile mates end-to-end without any end-cap projection.
    root=ROOT; root['repeat_axis']='Blender Y, 16 metres';root['cycle_surface_m']=.22
    slab('Resin Track',rect_points((0,0),3,16),0,.22,'Oxide Cycle Resin','Asphalt Cut Edge')
    slab('Walkway',rect_points((3.03,0),2.8,16),0,.232,'Brushed Footway Pavers','Precast Sand')
    for x in [-1.55,1.565,4.48]:box('Flush Edging',(x,0,.115),(.12,16,.23),'Precast Sand',.005)
    for y in [-6,-2,2,6]:stripe([(0,y-.68),(0,y+.68)],.075)
    def bike(x,y,ang):
        def xy(p):return place((x,y),p,ang)
        for cx in [-.34,.34]:
            path=[xy((cx+.207*cos(t*pi/16),.207*sin(t*pi/16))) for t in range(33)]
            ribbon('Cycle Stencils',path,.04,.228,'Road Paint White')
        for p,q in [((-.34,0),(-.15,.34)),((-.15,.34),(.01,.02)),((.01,.02),(-.34,0)),((.01,.02),(.23,.33)),((.23,.33),(-.15,.34)),((.34,0),(.19,.44)),((.19,.44),(.33,.44)),((-.15,.34),(-.19,.43)),((-.27,.43),(-.11,.43))]:ribbon('Cycle Stencils',[xy(p),xy(q)],.041,.231,'Road Paint White')
    for s in [-1,1]:
        bike(s*.74,s*4,pi if s==1 else 0); arrow('Cycle Stencils',s*.74,s*2.85,.23,pi if s==1 else 0,.72)
    # Slatted seat and integral planter at the outside of the walking strip.
    for y in [-2.4,2.4]:box('Seat Plinths',(4.07,y,.43),(.66,.42,.40),'Deep Petrol',.065)
    for i in range(5):box('Balau Seat',(3.79+i*.12,0,.686),(.108,5.52,.105),'Oiled Balau',.025)
    for y in [-4.17,4.17]:
        box('Planter Basins',(4.06,y,.45),(.71,1.95,.44),'Biscuit',.08)
        box('Planter Basins',(4.06,y,.68),(.60,1.8,.035),'Dark Mulch',.017)
        for j in [-.51,0,.51]:
            for i in range(11):
                a=i*2.4+j; r=.33+.16*cos(i*1.4);h=.53+.19*sin(i*1.1);cx=4.06;cy=y+j
                verts=[(cx,cy,.69),(cx+.50*r*cos(a)-.069*sin(a),cy+.50*r*sin(a)+.069*cos(a),.69+.78*h),(cx+.55*r*cos(a),cy+.55*r*sin(a),.69+.86*h),(cx+.50*r*cos(a)+.069*sin(a),cy+.50*r*sin(a)-.069*cos(a),.69+.78*h),(cx+r*cos(a),cy+r*sin(a),.69+h)]
                add('Pandan Rosettes',verts,[(0,1,2),(0,2,3),(1,4,2),(2,4,3)],['Pandan Green','Young Pandan','Pandan Green','Young Pandan'])
    x,y=1.88,6.15
    box('Trail Marker',(x,y,1.55),(.46,.17,2.65),'Deep Petrol',.085)
    box('Trail Marker',(x,y-.098,2.52),(.40,.035,.49),'Marigold',.035)
    label('Trail Marker','P3',x,y-.121,2.52,.32,.20,'Night Ink')
    plaque('Trail Marker',(x,y-.05),1.99,.93,.40,'Celadon Enamel','PANDAN','PARK CONNECTOR')
    finish((.93,-1.32,1.46))


if __name__ == "__main__":
    build()
