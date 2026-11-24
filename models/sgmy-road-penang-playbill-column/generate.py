"""SG/MY Jalan kit | penang playbill column.

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

TAU = 2*pi

JADE = 'River Teal Enamel'

INK = 'Deep Prussian Enamel'

BRASS = 'Brushed Nyonya Brass'

CREAM = 'Ivory Porcelain'

STONE = 'Warm Granite'

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

def shell(group, center, axis, sections, materials, n=40):
    """Turn a section profile about an axis. Distances run from the back cap to the nose."""
    q=Vector(axis).to_track_quat('Z','Y'); c=Vector(center)
    vs=[c+q@Vector((r*cos(TAU*i/n),r*sin(TAU*i/n),z)) for z,r in sections for i in range(n)]
    if isinstance(materials,str):materials=[materials]*(len(sections)-1)
    faces=[tuple(reversed(range(n)))]; mats=[materials[0]]
    for j,mat in enumerate(materials):
        for i in range(n):
            a=j*n+i; b=j*n+(i+1)%n; faces.append((a,b,b+n,a+n)); mats.append(mat)
    faces.append(tuple(range(len(vs)-n,len(vs)))); mats.append(materials[-1]); add(group,vs,faces,mats)

def lathe(group,xy,sections,mats,n=48):
    shell(group,(*xy,0),(0,0,1),sections,mats,n)

def printed_sheets():
    """One original four-panel print atlas. Coordinates are in paper space, from upper left."""
    h,w=960,640; y,x=np.mgrid[0:h,0:w]; x=(x+.5)/w;y=(y+.5)/h
    def rgb(c):return tuple(bytes.fromhex(c))
    def circle(cx,cy,rx,ry):return ((x-cx)/rx)**2+((y-cy)/ry)**2<=1
    def poly(points):
        mask=np.zeros((h,w),bool)
        for (a,b),(c,d) in zip(points,points[1:]+points[:1]):
            if abs(d-b)>1e-7:mask^=((b>y)!=(d>y))&(x<(c-a)*(y-b)/(d-b)+a)
        return mask
    def rect(x0,y0,x1,y1):return (x>=x0)&(x<=x1)&(y>=y0)&(y<=y1)
    papers=[]; rng=np.random.default_rng(305)
    for n,(base,ink,accent,light) in enumerate([('993B32','472D3D','E3AC52','FADEAE'),('13696A','142F3B','ED9C54','E4E4BD'),('D29242','763842','EACD8B','FBE7B2'),('4B596F','233647','EA8F67','F4D8AD')]):
        pix=np.full((h,w,3),rgb(base),np.uint8)
        def fill(mask,c):pix[mask]=rgb(c)
        fill(rect(.017,.011,.983,.989),accent);fill(rect(.029,.019,.971,.981),base)
        fill(rect(.064,.088,.936,.091),light);fill(rect(.064,.756,.936,.76),accent)
        # Broad backlit disc and overprinted halftone field frame each illustration.
        fill(circle(.5,.495,.386,.204),accent); fill(circle(.5,.495,.366,.194),light)
        dots=((x*68)%1-.5)**2+((y*112)%1-.5)**2<.055
        fill(circle(.5,.495,.36,.19)&dots&(x+y>1.05),accent)
        if n==0:
            # A carved shadow puppet in profile: crown, hooked nose, articulated hands.
            fill(poly([(.24,.68),(.38,.54),(.35,.475),(.40,.45),(.31,.424),(.33,.376),(.284,.352),(.397,.366),(.42,.309),(.459,.377),(.52,.345),(.536,.4),(.609,.436),(.712,.457),(.616,.47),(.626,.49),(.561,.498),(.514,.486),(.49,.525),(.57,.57),(.508,.61),(.617,.689)]),ink)
            fill(poly([(.442,.52),(.616,.567),(.781,.486),(.801,.452),(.816,.505),(.639,.605),(.455,.57)]),ink);fill(circle(.535,.434,.013,.007),light)
            for a,b in [(0.415,.406),(.45,.418),(.466,.56),(.491,.58)]:fill(circle(a,b,.014,.008),accent)
        elif n==1:
            # Wau bulan crescent tail, twin wing curls and spine.
            fill(poly([(.49,.307),(.619,.418),(.875,.515),(.614,.547),(.532,.526),(.501,.586),(.46,.525),(.352,.549),(.135,.518),(.381,.416)]),ink)
            fill(circle(.50,.595,.233,.080),ink);fill(circle(.50,.55,.218,.066),light)
            fill(poly([(.501,.331),(.519,.626),(.496,.663),(.478,.628)]),accent)
            for s in (-1,1):
                fill(poly([(.5+s*.051,.411),(.5+s*.235,.499),(.5+s*.119,.487),(.5+s*.052,.509)]),accent)
                fill(circle(.5+s*.104,.507,.022,.012),light)
        elif n==2:
            # Two-sided theatre drum with a criss-cross tensioning cord.
            fill(poly([(.214,.452),(.719,.412),(.81,.557),(.300,.611)]),ink)
            for k in range(6):
                a=.24+k*.075;fill(poly([(a,.453-k*.005),(a+.035,.45-k*.005),(a+.085,.578-k*.006),(a+.119,.444-k*.005),(a+.142,.44-k*.005),(a+.105,.589-k*.006),(a+.075,.594-k*.006)]),accent)
            fill(circle(.268,.532,.094,.083),ink);fill(circle(.268,.532,.066,.066),light)
        else:
            # Twin reel projector, lens and tripod.
            for cx in (.32,.58):
                fill(circle(cx,.436,.13,.073),ink)
                for k in range(5):fill(circle(cx+.072*cos(TAU*k/5),.436+.041*sin(TAU*k/5),.026,.015),accent)
            fill(rect(.26,.48,.637,.577),ink);fill(poly([(.62,.521),(.78,.478),(.78,.582),(.62,.544)]),ink)
            for dx in (-.16,.16):fill(poly([(.41,.569),(.45,.569),(.45+dx,.668),(.409+dx,.668)]),ink)
        for j in range(5):fill(rect(.067+j*.084,.929,.125+j*.084,.938),accent if j%2 else light)
        grain=rng.normal(0,1.8,(h,w,1)); papers.append(np.clip(pix+grain,0,255).astype('uint8').reshape(h//2,2,w//2,2,3).mean(axis=(1,3)).astype('uint8'))
    image=np.concatenate(papers,axis=1);hh,ww=image.shape[:2]
    def chunk(tag,data):return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data))
    b=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',ww,hh,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row.tobytes() for row in image),8))+chunk(b'IEND',b'')
    with tempfile.TemporaryDirectory() as tmp:
        f=Path(tmp)/'Panggung Playbill Atlas.png';f.write_bytes(b); img=bpy.data.images.load(str(f));img.pack()
    mat=material('Lithographed Theatre Bills','F6E5C0',.86); nt=mat.node_tree;t=nt.nodes.new('ShaderNodeTexImage');t.image=img;nt.links.new(t.outputs['Color'],nt.nodes['Principled BSDF'].inputs['Base Color'])

def build():
    start('Penang | Panggung Playbill Column','Centre of octagonal column base at footway level. Static four-sided illustrated notice drum.');printed_sheets()
    g='Enamelled Drum';lathe(g,(0,0),[(0,.58),(.059,.58),(.109,.54),(.109,.48),(.17,.48),(.205,.43),(.265,.428),(.288,.502),(.327,.51),(.347,.486),(.414,.481),(1.88,.481),(1.914,.50),(1.95,.51),(1.968,.484),(2.08,.484),(2.103,.52),(2.135,.534),(2.15,.52)], [STONE,STONE,STONE,INK,BRASS,JADE,INK,BRASS,JADE,INK,INK,BRASS,INK,BRASS,JADE,BRASS,JADE,BRASS],64)
    g='Pagoda Crown';lathe(g,(0,0),[(2.147,.518),(2.167,.57),(2.196,.584),(2.213,.579),(2.23,.51),(2.264,.425),(2.312,.336),(2.369,.229),(2.407,.127),(2.425,.104),(2.453,.111),(2.477,.087),(2.492,.055),(2.565,.035),(2.61,.006)],[INK,JADE,BRASS,JADE,JADE,JADE,JADE,JADE,INK,BRASS,BRASS,INK,BRASS,BRASS],48)
    for i in range(20):
        a=i*TAU/20;d=Vector((cos(a),sin(a),0));t=Vector((-sin(a),cos(a),0));c=d*.486+Vector((0,0,2.024));add('Frieze Rosettes',[c+t*.038,c+Vector((0,0,.041)),c-t*.038,c-Vector((0,0,.041))],[(0,1,2,3)],BRASS)
    titles=[('WAYANG','KULIT','MALAM BAYANG','JUMAAT   /   20:00'),('WAU','BULAN','PESTA ANGIN','SABTU   /   16:00'),('RENTAK','KOTA','PALUAN SENJA','AHAD   /   18:30'),('LAYAR','SENJA','PANGGUNG TEPI','SABTU   /   20:30')]; width=.699; lo=.445;hi=1.858;r=.488
    for i,(a,b,c,e) in enumerate(titles):
        angle=(i-.5)*pi/2; n=24; vs=[];fs=[];uv=[]
        def bend(x,z,radius):
            t=angle+x/r;return (radius*sin(t),-radius*cos(t),z)
        for j in range(n+1):
            x=width*(j/n-.5);vs.extend([bend(x,lo,r),bend(x,hi,r)])
        for j in range(n):
            u=(i+j/n)/4;v=(i+(j+1)/n)/4;fs.append((2*j,2*j+2,2*j+3,2*j+1));uv.append([(u,0),(v,0),(v,1),(u,1)])
        add('Illustrated Paper Panels',vs,fs,'Lithographed Theatre Bills',uv)
        for title,y,w,h in [('P E N A N G   /   0'+str(i+1),.055,.50,.032),(a,.15,.58,.107),(b,.24,.54,.084),(c,.81,.57,.069),(e,.877,.54,.04)]:
            group='Letterpress Titles';start_index=len(BATCHES[group].verts) if group in BATCHES else 0;words(group,title,(0,0,hi-y*(hi-lo)),w,h,CREAM);vs=BATCHES[group].verts
            for j in range(start_index,len(vs)):vs[j]=bend(vs[j][0],vs[j][2],r+.0028)
        pos=bend(width/2+.018,lo,.487);tube('Brass Poster Beads',pos,(*pos[:2],hi),.009,BRASS,sides=8)
    finish((.22,-2.7,.98))


if __name__ == "__main__":
    build()
