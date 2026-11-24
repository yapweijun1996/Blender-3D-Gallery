"""SG/MY Jalan kit | kallang mrt air scoop.

Original metre-scale procedural model; local Z up. No third-party assets.
Rebuild: blender -b --factory-startup --python-exit-code 1 --python generate.py
Writes the Draco GLB before setting up the Cycles studio for preview.png.
"""

from math import cos, pi, sin

from pathlib import Path

import struct

import tempfile

import zlib

import bpy

import numpy as np

from mathutils import Vector

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
    scene.render.resolution_x, scene.render.resolution_y = 832, 650
    scene.render.resolution_percentage = 100
    bpy.context.view_layer.update()
    # Fit actual mesh vertices, not an oversized axis-aligned box around curved pieces.
    right, up = (cam.rotation_euler.to_matrix() @ Vector(v) for v in [(1,0,0),(0,1,0)])
    projected = [((v.co-target).dot(right),(v.co-target).dot(up)) for o in objs for v in o.data.vertices]
    x0,x1=min(x for x,y in projected),max(x for x,y in projected)
    y0,y1=min(y for x,y in projected),max(y for x,y in projected)
    cam.location += right*((x0+x1)/2)+up*((y0+y1)/2)
    cam.data.ortho_scale = max((x1-x0)/.84,(y1-y0)/.82*960/750)
    bpy.ops.mesh.primitive_plane_add(size=span*250, location=(0,0,-.0007))
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
    ROOT['revision'] = 1
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

JADE = 'River Teal Enamel'

INK = 'Deep Prussian Enamel'

BRASS = 'Brushed Nyonya Brass'

CREAM = 'Ivory Porcelain'

STONE = 'Warm Granite'

DARK = 'Foundry Charcoal'

AQUA = 'Sea Glass'

def start(name, datum, road=False):
    setup(name)
    ROOT['origin_note'] = datum
    ROOT['facing_note'] = 'The principal view faces local -Y in Blender.'
    palette(road)
    for name, color, rough, metal in [
        ('River Teal Enamel','137D79',.43,.24),('Deep Prussian Enamel','163C4C',.45,.32),
        ('Brushed Nyonya Brass','C49143',.38,.68),('Ivory Porcelain','F2E8CC',.52,.05),
        ('Laksa Vermilion','D85737',.49,.18),('Oiled Chengal','A76538',.65,.02),
        ('Warm Granite','BEBAA9',.86,0),('Sea Glass','70CABC',.35,.15)]:
        material(name,color,rough,metal)

def plate(g,c,w,h,title,sub,mat=INK):
    x,y,z=c; box(g,c,(w,.065,h),BRASS,.025); box(g,(x,y-.039,z),(w-.035,.022,h-.033),mat,.011)
    words(g,title,(x,y-.052,z+h*.105),w*.88,h*.39,CREAM)
    words(g,sub,(x,y-.052,z-h*.245),w*.84,h*.105,CREAM)

def build():
    start('Kallang Reach MRT | Street Air Intake','Centre of raised flood sill at pavement level.')
    g='Flood Sill and Plinth'; box(g,(0,0,.12),(3.62,2.03,.24),STONE,.09);box(g,(0,0,.277),(3.45,1.88,.088),INK,.035)
    # The louvre cassette sits beneath two folded, counter-sloping canopy wings.
    def roof_z(x,y):return 2.48+.345*abs(x)+.19*y
    g='Standing Seam Butterfly Hood'
    for side in (-1,1):
        poly=[(.015*side,-1.08),(.34*side,-1.13),(1.95*side,-.94),(1.93*side,.91),(1.65*side,1.06),(.015*side,1.08)]
        poly=ccw(poly); n=len(poly); vs=[(x,y,roof_z(x,y)+off) for off in (0,.12) for x,y in poly]; fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        add(g,vs,fs,[INK,JADE]+[AQUA]*n)
        for k in range(1,8):
            x=side*(.12+k*.221); y=.92; tube(g,(x,-y,roof_z(x,-y)+.12),(x,y,roof_z(x,y)+.12),.013,JADE,sides=8)
    g='Rainproof Blade Bank'
    for s in (-1,1):
        panel=ccw([(0,-.65),(1.52*s,-.65),(1.52*s,.65),(0,.65)])
        add(g,[(x,y,z) for top in (False,True) for x,y in panel for z in [roof_z(x,y) if top else .32]],[(0,3,2,1),(4,5,6,7)]+[(i,(i+1)%4,(i+1)%4+4,i+4) for i in range(4)],DARK)
    for side in (-1,1):
        for end in (-1,1):
            x,y=1.63*side,.78*end; box('Frame Stiles',(x,y,roof_z(x,y)/2),(.115,.14,roof_z(x,y)),INK,.018)
        # Extruded blades: each has a folded drip hem and angled powder-coated face.
        for row in range(15):
            z=.48+.192*row
            def blade(xs,ys,wide_end=False):
                p=[(x,y,z+.16) for x,y in zip(xs,ys)]
                q=[(x*(1.088 if wide_end else 1),y*(1 if wide_end else 1.16),z) for x,y in zip(xs,ys)]
                # Clip the upper rows at the folded soffit, including their drip hems.
                poly=list(map(Vector,[p[0],p[1],q[1],q[0]])); clipped=[]
                def clearance(v): return roof_z(v.x,v.y)-.016-v.z
                for j,v in enumerate(poly):
                    w=poly[(j+1)%4]; a,b=clearance(v),clearance(w)
                    if a>=0: clipped.append(v)
                    if (a<0)!=(b<0): clipped.append(v.lerp(w,a/(a-b)))
                if len(clipped)>=3: add(g,clipped,[tuple(range(len(clipped)))],JADE if row%4 else INK)
                a,b=map(Vector,q); da,db=clearance(a),clearance(b)
                if max(da,db)>0:
                    c=a.lerp(b,da/(da-db)) if min(da,db)<0 else None
                    tube(g,c if da<0 else a,c if db<0 else b,.017,AQUA,sides=8)
            for s in (-1,1): blade([0,1.62*s],[side*.747]*2)
            blade([side*1.55]*2,[-.752,.752],True)
    g='Service Spine'; box(g,(-.68,-.887,1.306),(.87,.19,1.98),INK,.04);box(g,(-.68,-.993,1.31),(.74,.042,1.79),JADE,.02)
    for x in (-.96,-.40):tube(g,(x,-1.018,.462),(x,-1.018,2.15),.011,BRASS)
    plate(g,(-.68,-1.025,1.744),.65,.389,'KALLANG','MRT   /   VENT   08',INK)
    for j in range(7):box(g,(-.68,-1.021,.677+.075*j),(.46,.021,.029),INK,.009)
    box(g,(-.426,-1.038,1.352),(.043,.062,.134),BRASS,.014)
    finish((1.63,-2.92,1.07))


if __name__ == "__main__":
    build()
