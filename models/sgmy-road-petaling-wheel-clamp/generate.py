"""Petaling municipal car park: a deployed three-jaw tyre clamp with telescoping crown shoe.

Original procedural geometry, lettering and surfaces; no downloaded assets.
Static SG/MY road kit. Metres, base origin, -Y viewing front, +Z up.
Rebuild both files: blender -b --factory-startup --python-exit-code 1 -P generate.py
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
    setup('Petaling | Kunci Roda'); finishes()
    yellow='Safety Yellow';char='Moulded Graphite'; orange='Persimmon Enamel';al='Bead Blasted Alloy'
    for n,c,r,m in [(yellow,'edba36',.39,.20),(char,'34383b',.74,.10),(orange,'dc5b39',.42,.25),(al,'a4acac',.36,.68)]:material(n,c,r,m)
    # Front plate normal is -Y. Shoes wrap over the tyre shoulders, with padded
    # rear hooks. The clamp can be placed as a freestanding object on its two skids.
    cz=.372
    def pt(r,w,a,y):return (r*cos(a)-w*sin(a),y,cz+r*sin(a)+w*cos(a))
    def plate(name,outline,a,y,depth,mat):
        face(name,[(pt(r,w,a,0)[0],pt(r,w,a,0)[2]) for r,w in outline],y,depth,mat)
    for a in [-pi*.75,-pi*.25,pi*.5]:
        high=a>0;end=.484 if high else .418
        plate('Welded arm sockets',[(.10,-.062),(.273,-.062),(.291,-.048),(.291,.048),(.273,.062),(.10,.062)],a,-.048,.092,yellow)
        plate('Sliding jaw bars',[(.269,-.039),(end,-.039),(end+.008,.035),(.269,.039)],a,-.040,.064,al)
        for j in range(3 if high else 2):
            x,y,z=pt(.313+j*.044,0,a,0)
            tube('Ratchet apertures',(x,-.039,z),(x,-.043,z),.010,char,sides=16)
        for j in [-1,1]:
            x,y,z=pt(.242,.038*j,a,0);tube('Arm socket rivets',(x,-.048,z),(x,-.055,z),.009,al,sides=12)
        # Gusseted wrapping shoe, with a flared end and a folded return hook.
        plate('Jaw elbows',[(end-.041,-.052),(end+.018,-.069),(end+.032,-.051),(end+.032,.051),(end+.018,.069),(end-.041,.052)],a,-.043,.060,orange)
        plate('Across tyre shoes',[(end-.012,-.061),(end+.028,-.061),(end+.028,.061),(end-.012,.061)],a,.012,.202,orange)
        plate('Hooked returns',[(end-.087,-.044),(end-.060,-.064),(end+.026,-.061),(end+.026,.061),(end-.060,.064),(end-.087,.044)],a,.191,.039,orange)
        plate('Rubber contact pads',[(end-.086,-.041),(end-.034,-.050),(end-.034,.050),(end-.086,.041)],a,.177,.021,char)
    for x in [-.302,.302]:box('Parking skids',(x,.107,.017),(.117,.228,.034),char,.009)
    # The dished protector covers the wheel nuts. Concentric spun folds catch highlights.
    n=64;profile=[(.015,.176),(-.013,.182),(-.035,.190),(-.055,.189),(-.061,.181),(-.061,.166),(-.083,.150),(-.104,.121),(-.110,.098)]
    loft('Spun hub guard',[(r*cos(i*2*pi/n),y,cz+r*sin(i*2*pi/n)) for y,r in profile for i in range(n)],n,yellow)
    for r,y,d,mat in [(.089,-.108,.012,char),(.071,-.120,.015,orange),(.052,-.135,.015,char),(.036,-.150,.008,BRASS)]:
        tube('Lock boss',(0,y,cz),(0,y-d,cz),r,mat,sides=40)
    box('Lock keyway',(0,-.160,cz),(.009,.007,.034),char,.002)
    for a in [pi/6,5*pi/6,3*pi/2]:
        x=.14*cos(a);z=cz+.14*sin(a);tube('Dish fasteners',(x,-.088,z),(x,-.098,z),.013,al,sides=6)
    # A bent carrying loop sits alongside the tall arm, accessible from the front.
    chain('Carry loop',[(.042,-.008,.556),(.124,-.008,.576),(.149,-.008,.605),(.149,-.008,.723),(.128,-.008,.747),(.039,-.008,.757)],.014,al,12)
    tube('Carry sleeve',(.149,-.008,.607),(.149,-.008,.718),.022,char,sides=20)
    box('Top lock label',(0,-.053,.572),(.106,.013,.105),char,.008)
    text('Parking identity','PJ',0,-.061,.588,.085,.048,CREAM)
    text('Parking identity','P - 03',0,-.061,.545,.085,.023,yellow)
    box('Crown pad',(0,-.047,.815),(.131,.015,.042),char,.006)
    text('Crown legend','KUNCI RODA',0,-.056,.815,.119,.016,CREAM)
    finish((2.58,-4.26,1.75))


if __name__ == "__main__":
    build()
