"""SG/MY Jalan kit: seremban pasar pitch marks.
Self-contained procedural rebuild: blender -b --factory-startup --python-exit-code 1 -P generate.py
Metres, +Z up, base origin. Draco GLB and an indexed Blender studio render.
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
    ROOT['role'] = 'Static roadside visual; no collision or scripted behaviour.'
    ROOT['revision'] = 1


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
    light('Warm Daylight', (-.72,-.78,1.05), 55, .60, (1,.90,.79))
    light('Cool Skylight', (.47,.35,.71), 29, .9, (.76,.89,1))
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 10
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
    coords = [Vector(co) for obj in objs for co in obj.bound_box]
    ROOT['dimensions_m_xyz'] = [round(max(v[i] for v in coords)-min(v[i] for v in coords),4) for i in range(3)]
    ROOT['rights_note'] = 'Original procedural design and materials. No external assets.'
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
    if (out / 'model.glb').stat().st_size > 2_000_000:
        raise ValueError('GLB exceeds delivery budget')
    if len(objs) == 0: raise ValueError('Empty model')
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
    u = np.rint(255*v + rng.uniform(-.7,.7,(h,w,1))).clip(0,255).astype(np.int32)
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


def tile(group, xy, base, top, mat):
    xy=ccw(list(xy)); loft(group,[(x,y,z) for z in (base,top) for x,y in xy],len(xy),mat)


def xwheel(group,x,y,z,r,w,mat):
    tube(group,(x-w*.5,y,z),(x+w*.5,y,z),r,mat,sides=32)


def build():
    setup('Seremban | Pasar malam pitch registry'); finishes()
    import json
    material('Dense Graded Asphalt','3B4245',.95);texture('Dense Graded Asphalt','asphalt')
    material('Footway brick','B4A899',.88);texture('Footway brick','concrete')
    material('Bay wash','385854',.91);material('Line ochre','FFC451',.78)
    ROOT['surface_height_m']=GRADE;ROOT['carriageway_width_m']=7.;ROOT['footway_width_m']=WALK
    ROOT['ports_blender_xy_m']=json.dumps({'South':[0,-16],'North':[0,16]})
    for y,label,a in [(-16,'South',pi),(16,'North',0)]:
        obj=bpy.data.objects.new('Port '+label,None);bpy.context.collection.objects.link(obj);obj.parent=ROOT;obj.location.y=y;obj.rotation_euler.z=a
    tile('Road deck',[(-3.5,-16),(3.5,-16),(3.5,16),(-3.5,16)],0,GRADE,'Dense Graded Asphalt')
    for s in [-1,1]:
        section=[(0,0),(0,.337),(.036,.375),(.17,.375),(.20,WALK_Z),(1.71,WALK_Z),(WALK,.312),(WALK,0)]
        poly=[(s*(3.5+u),z) for u,z in section];face('Kerbs and footways',poly,-16,32,'Footway brick')
        for i in range(15):
            y=-16+i*2+1.004
            box('Footway saw cuts',(s*4.45,y+.996,WALK_Z+.001),(1.49,.012,.004),STONE,.001)
        for v in [-11.3,-1.9,8.8]:
            box('Drain frames',(s*3.31,v,GRADE+.005),(.303,.62,.010),STEEL,.002)
            box('Drain wells',(s*3.31,v,GRADE+.012),(.241,.55,.007),IRON,.002)
            for k in range(7):box('Drain slots',(s*3.31,v+.07*(k-3),GRADE+.017),(.247,.021,.009),STEEL,.004)
    def paint(group,x,y,w,d,mat,z=PAINT):
        add(group,[(x-w/2,y-d/2,z),(x+w/2,y-d/2,z),(x+w/2,y+d/2,z),(x-w/2,y+d/2,z)],[(0,1,2,3)],mat)
    for i in range(6):
        y=(i-2.5)*4.36
        paint('Market pitch wash',1.756,y,2.50,3.75,'Bay wash')
        for s in [-1,1]:
            for t in [-1,1]:
                x=1.756+s*1.25;dy=y+t*1.872
                paint('Pitch keys',x,dy-t*.37,.102,.74,'Line ochre',PAINT+.002)
                paint('Pitch keys',x-s*.30,dy,.60,.104,'Line ochre',PAINT+.003)
        words('Pitch stencil',f'A{1+i:02}',(1.67,y,PAINT+.004),1.48,.73,CREAM,pi/2,True)
        for j in range(3):paint('Pitch gauge',2.78,y-.18+j*.18,.22,.057,PALE,PAINT+.003)
        for s in [-1,1]:
            spin('Flush canopy ferrules',2.91,y+s*1.72,[(PAINT+.004,.061),(PAINT+.009,.061)],BRASS,12)
            spin('Ferrule bungs',2.91,y+s*1.72,[(PAINT+.010,.037),(PAINT+.013,.037)],IRON,12)
    for i in range(11):paint('Loading aisle separator',.04,-14.25+2.85*i,.113,1.12,CREAM)
    for y in [-10.6,0,10.6]:
        words('Clear aisle stencil','LALUAN',(-1.94,y,PAINT+.002),2.18,.34,CREAM,pi/2,True)
        words('Clear aisle stencil','BEBAS',(-1.48,y,PAINT+.002),1.72,.34,CREAM,pi/2,True)
    for q in [.15,.34]:paint('No parking kerb lines',-3.5+q,0,.083,32,'Line ochre')
    # Paired pitches share a lockable power pedestal at the kerb. Keep the rear half of the footway clear.
    for idx,y in enumerate([-8.72,0,8.72],1):
        x=3.98
        box('Service pillar soles',(x,y,WALK_Z+.039),(.47,.51,.078),STONE,.017)
        box('Power pedestals',(x,y,WALK_Z+.485),(.366,.423,.856),TEAL,.035)
        box('Identification bands',(x,y,WALK_Z+.794),(.373,.43,.089),GOLD,.012)
        box('Hooded pillar caps',(x,y,WALK_Z+.946),(.403,.46,.089),INK,.019)
        box('Outlet recesses',(x+.183,y,WALK_Z+.482),(.024,.338,.402),INK,.01)
        for dy in (-.079,.079):
            xwheel('Socket lids',x+.207,y+dy,WALK_Z+.531,.057,.035,RED)
        text('Service pair IDs',f'{2*idx-1:02} / {2*idx:02}',x+.20,y,WALK_Z+.797,.30,.054,INK,pi/2)
    # Roll-out time board faces the walking route from the right footway.
    old=set(BATCHES)
    for x in (-.48,.48):
        spin('Board shoes',x,0,[(0,.14),(.055,.14),(.075,.093)],IRON,16)
        box('Board uprights',(x,0,.99),(.082,.10,1.88),TEAL,.012)
    box('Market sign',(0,0,1.50),(1.30,.153,.87),TEAL,.045)
    box('Ivory band',(0,-.083,1.30),(1.215,.018,.334),CREAM,.011)
    text('Sign legend','PASAR MALAM',0,-.083,1.695,1.13,.146)
    text('Sign legend','PETAK   A01 - A06',0,-.097,1.337,1.09,.10,INK)
    text('Sign legend','SEREMBAN     /     17:00 - 22:00',0,-.097,1.201,1.03,.058,TEAL)
    for j in range(9):
        x=(j-4)*.152;box('Striped sign pelmet',(x,-.025,1.978),(.152,.28,.109),RED if j%2==0 else CREAM,.006)
    a=pi*.49
    for group in set(BATCHES)-old:
        b=BATCHES[group];b.verts=[(4.42+x*cos(a)-y*sin(a),-3.0+x*sin(a)+y*cos(a),z+WALK_Z) for x,y,z in b.verts]
    finish((3.50,-3.88,4.18))


if __name__ == "__main__":
    build()
