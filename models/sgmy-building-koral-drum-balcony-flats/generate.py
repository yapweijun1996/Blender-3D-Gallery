"""Blok 36 Koral | drum-balcony estate flats
Original deterministic exterior, built in metres, front toward -Y. No external assets.
Run: blender -b --python generate.py. Outputs the Draco GLB and studio PNG.
Mesh UV0 and opaque PBR materials; origin at grade. No collision or game logic.
"""

import math
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

TAU = 2 * math.pi
OUT = Path(__file__).resolve().parent
# Section batches keep the hierarchy editable without one draw call per prop.
PARTS = defaultdict(lambda: ([], [], [], []))
MATS = {}


def material(name, srgb, rough=.68, metallic=0):
    def linear(c):
        c = int(c, 16) / 255
        return c / 12.92 if c < .04045 else ((c + .055) / 1.055) ** 2.4
    rgb = tuple(linear(srgb[i:i+2]) for i in (0, 2, 4))
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*rgb, 1)
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = m.diffuse_color
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metallic
    MATS[name] = m
    return name


def add(section, mat, verts, faces, smooth=False):
    vs, fs, ms, ss = PARTS[section]
    offset = len(vs)
    vs.extend(tuple(POSE @ Vector(v)) for v in verts)
    fs.extend(tuple(i + offset for i in f) for f in faces)
    ms.extend([mat] * len(faces))
    ss.extend([smooth] * len(faces) if isinstance(smooth, bool) else smooth)


@lru_cache(maxsize=256)
def box_template(w, d, h, bevel):
    x, y, z = w/2, d/2, h/2
    verts = [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),
             (-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    faces = [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    if not bevel:
        return verts, faces
    bm = bmesh.new()
    v = [bm.verts.new(p) for p in verts]
    for f in faces:
        bm.faces.new([v[i] for i in f])
    bm.normal_update()
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(bevel, .35*min(w,d,h)),
                    segments=1, affect='EDGES')
    bm.verts.index_update()
    result = ([tuple(p.co) for p in bm.verts],
              [tuple(p.index for p in f.verts) for f in bm.faces])
    bm.free()
    return result


def box(section, mat, pos, dims, b=0, yaw=0, basis=None):
    verts, faces = box_template(*dims, b)
    if yaw:
        basis = Matrix.Rotation(yaw, 3, 'Z')
    if basis is not None:
        verts = [basis @ Vector(v) for v in verts]
    x, y, z = pos
    add(section, mat, [(u+x, v+y, w+z) for u,v,w in verts], faces)


def rod(section, mat, a, b, radius, n=10, taper=1):
    a, b = Vector(a), Vector(b)
    basis = (b-a).to_track_quat('Z','Y').to_matrix()
    verts = [p+basis @ Vector((rad*math.cos(TAU*j/n),rad*math.sin(TAU*j/n),0))
             for p,rad in ((a,radius),(b,radius*taper)) for j in range(n)]
    faces = [(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
    faces.extend((tuple(reversed(range(n))),tuple(range(n,2*n))))
    add(section, mat, verts, faces, [True]*n+[False,False])


def sign(section, mat, text, pos, width, height):
    # Use only the Blender built-in font. Freeze the lettering to mesh for GLB.
    curve = bpy.data.curves.new('Sign artwork', 'FONT')
    curve.body, curve.align_x, curve.align_y = text, 'CENTER', 'CENTER'
    curve.resolution_u = 5
    ob = bpy.data.objects.new('Sign cutter', curve)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    mesh = ev.to_mesh()
    coords = [tuple(v.co) for v in mesh.vertices]
    w = max(p[0] for p in coords)-min(p[0] for p in coords)
    h = max(p[1] for p in coords)-min(p[1] for p in coords)
    s = min(width/w,height/h)
    x,y,z = pos
    mesh.calc_loop_triangles()
    add(section, mat, [(x+u*s, y-q*s, z+v*s) for u,v,q in coords],
        [tuple(t.vertices) for t in mesh.loop_triangles])
    ev.to_mesh_clear()
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.curves.remove(curve)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    return scene


def finalize(scene):
    root = bpy.data.objects.new(TITLE, None)
    scene.collection.objects.link(root)
    root['asset_id'] = SLUG
    root['origin_note'] = 'Ground contact plane, base-centred local frame'
    root['role'] = 'Static residential exterior'
    root['units'] = 'metres'
    root['facing'] = 'Blender -Y / glTF +Z'
    for name,(verts,faces,assets,smooth) in PARTS.items():
        mesh = bpy.data.meshes.new(name + ' Geometry')
        mesh.from_pydata(verts, [], faces)
        assert not mesh.validate(verbose=True), name
        slots = {m:i for i,m in enumerate(dict.fromkeys(assets))}
        for m in slots:
            mesh.materials.append(MATS[m])
        for p,m,s in zip(mesh.polygons,assets,smooth):
            p.material_index = slots[m]
            p.use_smooth = s
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        # Texture-free material palette; UV0 still provides a non-overlapping edit/lightmap layout.
        uv = mesh.uv_layers.new(name='Layout')
        cells = math.ceil(math.sqrt(len(mesh.polygons)))
        for i,p in enumerate(mesh.polygons):
            ids = list(p.loop_indices)
            coords = [mesh.vertices[mesh.loops[j].vertex_index].co for j in ids]
            edges = [b-a for a,b in zip(coords,coords[1:]+coords[:1])]
            u = max(edges,key=lambda v:v.length_squared).normalized()
            v = p.normal.cross(u).normalized()
            px = [c.dot(u) for c in coords]
            py = [c.dot(v) for c in coords]
            x0,y0 = min(px),min(py)
            scale = .84 / max(max(px)-x0,max(py)-y0,1e-6)
            for j,x,y in zip(ids,px,py):
                uv.uv[j].vector = ((i%cells + .08 + (x-x0)*scale)/cells,
                                   (i//cells + .08 + (y-y0)*scale)/cells)
        ob = bpy.data.objects.new(name, mesh)
        scene.collection.objects.link(ob)
        ob.parent = root
    bpy.ops.export_scene.gltf(filepath=str(OUT/'model.glb'), export_format='GLB',
                             export_yup=True, export_extras=True, export_animations=False,
                             export_draco_mesh_compression_enable=True,
                             export_draco_mesh_compression_level=6,
                             export_draco_position_quantization=18,
                             export_draco_normal_quantization=12,
                             export_draco_texcoord_quantization=16)
    assert (OUT/'model.glb').stat().st_size <= 2_000_000


def preview(scene, direction, resolution):
    # Studio is made only after the export and is not part of the game model.
    points = [Vector(v) for verts,_,_,_ in PARTS.values() for v in verts]
    mins = Vector(tuple(min(v[i] for v in points) for i in range(3)))
    maxs = Vector(tuple(max(v[i] for v in points) for i in range(3)))
    extent = max(maxs-mins)
    center = (mins+maxs)/2
    eye = Vector(direction).normalized()
    basis = (-eye).to_track_quat('-Z','Y')
    right,up = basis @ Vector((1,0,0)),basis @ Vector((0,1,0))
    xx = [(p-center).dot(right) for p in points]
    yy = [(p-center).dot(up) for p in points]
    aim = center + right*((max(xx)+min(xx))/2) + up*((max(yy)+min(yy))/2)
    cam = bpy.data.objects.new('Studio Camera',bpy.data.cameras.new('Studio Camera'))
    scene.collection.objects.link(cam)
    cam.location = aim + 2.8*extent*eye
    cam.rotation_euler = basis.to_euler()
    cam.data.type = 'ORTHO'
    cam.data.clip_end = extent*16
    aspect = resolution[0]/resolution[1]
    cam.data.ortho_scale = 1.135 * max(max(xx)-min(xx),(max(yy)-min(yy))*aspect)
    scene.camera = cam
    bpy.ops.mesh.primitive_plane_add(size=extent*220, location=(0,0,-.012))
    bpy.context.object.data.materials.append(MATS[material('Studio Limestone','b4afa2',.9)])
    world = bpy.data.worlds.new('Studio Ambient')
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    bg.inputs[0].default_value = (.65,.77,1,1)
    bg.inputs[1].default_value = .29
    def light(name,xyz,power,size,color):
        data = bpy.data.lights.new(name,'AREA')
        ob = bpy.data.objects.new(name,data)
        scene.collection.objects.link(ob)
        ob.location = center+extent*Vector(xyz)
        ob.rotation_euler = (center-ob.location).to_track_quat('-Z','Y').to_euler()
        data.energy, data.size, data.color = power*extent**2,size*extent,color
    light('Warm Daylight',(-.85,-1.05,1.5),155,.85,(1,.91,.82))
    light('Cool Facade Fill',(1,-.55,.55),46,.95,(.83,.91,1))
    light('Soft Rim',(.25,1.1,1.5),72,1.0,(1,.97,.91))
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -.75
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.resolution_x,scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(OUT/'preview.png')
    bpy.ops.render.render(write_still=True)

from contextlib import contextmanager

# A local frame lets the same joinery follow an angled or side elevation.
POSE = Matrix.Identity(4)
@contextmanager
def frame(x=0, y=0, angle=0, z=0):
    global POSE
    previous = POSE
    POSE = previous @ Matrix.Translation((x,y,z)) @ Matrix.Rotation(math.radians(angle),4,'Z')
    try:
        yield
    finally:
        POSE = previous

def palette(wall, accent, secondary, roof, wood):
    global WALL, ACC, SEC, ROOF, TIM, SNOW, DARK, GLASS, MOSS, LEAF, FERN, PAVE, METAL, TILE, SUN, EARTH
    WALL = material('Facade | body colour', wall)
    ACC = material('Facade | feature colour', accent)
    SEC = material('Facade | secondary colour', secondary)
    ROOF = material('Roof | weather face', roof)
    TIM = material('Carpentry | finished timber',wood)
    SNOW = material('Trim | rice porcelain','f3ebd4')
    DARK = material('Joinery | shadow bronze','303c3c')
    GLASS = [material('Glazing | '+n,c,.28,.19) for n,c in [('rain','3b5860'),('sky','769596'),('linen curtain','a2b1a5')]]
    MOSS = material('Garden | pandan shadow','3c634c')
    LEAF = material('Garden | palm green','638950')
    FERN = material('Garden | fresh shoot','9baf67')
    PAVE = material('Masonry | buff paving','b1a590')
    METAL = material('Metalwork | brushed pewter','697c7b',.42,.25)
    TILE = material('Ceramic | burnt sienna','b46b4c')
    SUN = material('Trim | gamboge','e8b05e')
    EARTH = material('Garden | potting mix','494335')

def B(part,mat,x,y,z,w,d,h,b=0):
    """Rectangle with its lower face at z."""
    box(part,mat,(x,y,z+h/2),(w,d,h),b)

def win(x,y,z,w,h,n=2,seed=0,trim=None):
    s='Casements and sills'; trim=trim or SNOW
    B(s,DARK,x,y-.036,z,w,.094,h,.012)
    pw=(w-.14)/n
    for j in range(n):
        xx=x-w/2+.07+pw*(j+.5)
        B(s,GLASS[(seed+2*j+(j//2))%3],xx,y-.09,z+.075,pw-.042,.038,h-.15)
    B(s,trim,x,y-.075,z-.07,w+.18,.25,.105,.014)
    B(s,trim,x,y-.07,z+h-.03,w+.10,.18,.08,.012)


def door(x,y,z,w=1.05,h=2.16,mat=None):
    s='Entrance joinery'; mat=mat or TIM
    B(s,DARK,x,y-.04,z,w+.13,.12,h+.08)
    for i in (-1,1):
        cx=x+i*w/4
        B(s,mat,cx,y-.12,z+.015,w/2-.022,.10,h-.02)
        for zz,hh in ((.14,h*.32),(h*.51,h*.40)):
            B(s,SEC,cx,y-.18,z+zz,w*.34,.04,hh,.015)
        B(s,SUN,x+i*.09,y-.235,z+.84,.032,.06,.21,.01)


def label(text,x,y,z,w,h,mat=None):
    sign('Cast lettering',mat or SNOW,text,(x,y,z),w,h)


def section(s, mat, points, z, height):
    """Extrude an XY footprint."""
    n=len(points)
    add(s,mat,[(x,y,zz) for zz in (z,z+height) for x,y in points],
        [tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])


def pole(s,mat,x,y,z,h,r,n=12):
    rod(s,mat,(x,y,z),(x,y,z+h),r,n)


def piers(s,mat,x,y,z,w,h):
    B(s,mat,x,y,z,w,w,h,.025)
    for dz,hh,k in ((0,.17,1.43),(.17,.41,1.19),(h-.30,.12,1.20),(h-.18,.18,1.43)):
        B(s,SNOW,x,y,z+dz,w*k,w*k,hh,.018)


def index_preview(path):
    """Encode Blender's RGB render with an adaptive palette; no external image tools."""
    import struct
    import zlib
    from collections import Counter
    data=path.read_bytes()
    if len(data)<=250000: return
    pos=8; chunks=[]
    while pos<len(data):
        size,tag=struct.unpack_from('>I4s',data,pos); contents=data[pos+8:pos+8+size]; pos+=size+12
        if tag==b'IHDR': w,h,depth,kind,_,_,interlace=struct.unpack('>IIBBBBB',contents)
        if tag==b'IDAT': chunks.append(contents)
    assert (depth,kind,interlace)==(8,2,0)
    raw=zlib.decompress(b''.join(chunks)); stride=3*w; prev=bytearray(stride); rows=[]; counts=Counter()
    for j in range(h):
        offset=j*(stride+1); mode=raw[offset]; row=bytearray(raw[offset+1:offset+1+stride]); ids=[]
        for i,a in enumerate(row):
            left=row[i-3] if i>=3 else 0; top=prev[i]; diag=prev[i-3] if i>=3 else 0
            if mode==4:
                p=left+top-diag; dl,dt,dd=abs(p-left),abs(p-top),abs(p-diag)
                v=left if dl<=dt and dl<=dd else top if dt<=dd else diag
            else: v=(0,left,top,(left+top)//2)[mode]
            row[i]=(a+v)&255
        for i in range(0,stride,3): ids.append(tuple(c>>2 for c in row[i:i+3]))
        counts.update(ids); rows.append(ids); prev=row
    # Reserve palette space for thin joinery and shadow details, not just the cyclorama.
    weights={c:n**.55 for c,n in counts.items()}
    def bucket(colors):
        spans=[(max(c[i] for c in colors)-min(c[i] for c in colors))*l for i,l in enumerate((1,1.12,.9))]
        axis=max(range(3),key=spans.__getitem__); mass=sum(weights[c] for c in colors)
        return max(spans)*mass**.24,axis,mass,colors
    def split(group):
        _,axis,mass,colors=group; colors.sort(key=lambda c:c[axis]); acc=0
        for i,c in enumerate(colors[:-1],1):
            acc+=weights[c]
            if acc>=mass/2: break
        return bucket(colors[:i]),bucket(colors[i:])
    def chunk(tag,payload):
        return struct.pack('>I',len(payload))+tag+payload+struct.pack('>I',zlib.crc32(tag+payload)&0xffffffff)
    for bits in (8,7,6,5):
        buckets=[bucket(list(counts))]
        while len(buckets)<min(len(counts),1<<bits):
            i=max(range(len(buckets)),key=lambda j:buckets[j][0]); buckets.extend(split(buckets.pop(i)))
        groups=[g[3] for g in buckets]
        lookup={c:i for i,g in enumerate(groups) for c in g}; pal=bytearray()
        for g in groups:
            mass=sum(counts[c] for c in g)
            pal.extend(min(255,round(1.5+sum(4*c[i]*counts[c] for c in g)/mass)) for i in range(3))
        indexed=b''.join(b'\0'+bytes(lookup[c] for c in row) for row in rows)
        result=data[:8]+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,3,0,0,0))+chunk(b'sRGB',b'\0')+chunk(b'PLTE',pal)+chunk(b'IDAT',zlib.compress(indexed,9))+chunk(b'IEND',b'')
        if len(result)<=250000:
            path.write_bytes(result); return
    raise ValueError('Preview exceeds the gallery byte budget')

SLUG = 'sgmy-building-koral-drum-balcony-flats'
TITLE = 'Blok 36 Koral | drum-balcony estate flats'
VIEW = (.68,-1.55,.58)
SIZE = (760,630)


def build():
    palette('ead6af','387a76','ba6b52','877d6a','70574a'); s='Flats and void deck'; a='Paired balcony drums'; c='Lift lantern'
    B(s,PAVE,0,-.10,0,29.2,10.4,.22,.08)
    for x in (-13,-9,-4.4,0,4.4,9,13):
        for y in (-3.68,3.61): piers(s,WALL,x,y,.22,.61,2.90)
    B(s,ACC,0,1.08,.22,8.9,4.66,2.93,.06); door(0,-1.26,.22,1.6,2.33,METAL)
    B(s,SNOW,0,0,3.1,28.4,8.72,.36,.055)
    # Drums project from both ends of the street elevation, with open interiors and rolled coping.
    for j in range(5):
        z=3.45+2.86*j; B(s,WALL,0,0,z,27.72,8.36,2.86,.035)
        B(s,SNOW,0,0,z+.01,27.9,8.50,.14,.025)
        for i,xx in enumerate((-11.45,-8.62,-5.53,-2.82,2.82,5.53,8.62,11.45)):
            win(xx,-4.18,z+.76,2.03,1.40,3,i+j)
        with frame(0,4.18,180):
            for i in range(10): win((i-4.5)*2.70,0,z+.90,1.71,1.20,2,i+j)
        for side in (-1,1):
            xx=side*11.50; yy=-4.13; rr=2.21
            poly=[(xx+rr*math.cos(math.pi+i*math.pi/24),yy+rr*math.sin(math.pi+i*math.pi/24)) for i in range(25)]
            section(a,SNOW,poly,z-.03,.22)
            for rad,zz,hh,mat in ((rr-.05,z+.16,.73,SEC),(rr-.035,z+.87,.12,SNOW)):
                arc=[(xx+rad*math.cos(math.pi+i*math.pi/24),yy+rad*math.sin(math.pi+i*math.pi/24)) for i in range(25)]
                inner=[(xx+(rad-.12)*math.cos(math.pi+i*math.pi/24),yy+(rad-.12)*math.sin(math.pi+i*math.pi/24)) for i in range(24,-1,-1)]
                section(a,mat,arc+inner,zz,hh)
            for i in range(16):
                p=math.pi+i*math.pi/15; u=xx+rr*.95*math.cos(p); v=yy+rr*.95*math.sin(p); pole(a,DARK,u,v,z+.98,.22,.028,8)
                if i:
                    rod(a,DARK,previous,(u,v,z+1.20),.044,8)
                previous=(u,v,z+1.20)
            with frame(side*13.86,0,side*90):
                for i in (-1,1): win(i*2.20,0,z+.85,2.14,1.43,3,i+j)
    top=3.45+2.86*5; B(s,ACC,0,0,top,28.14,8.68,.22,.04); B(s,SNOW,0,0,top+.22,28.68,9.18,.16,.035)
    # An address fin and vertically stacked vent slots mark the central entrance.
    B(c,ACC,0,-3.87,.22,2.74,2.46,top+.95,.05)
    door(0,-5.105,.22,1.61,2.30,METAL)
    for i in range(5):
        z=3.69+i*2.86; B(c,DARK,0,-5.13,z,1.82,.12,1.98)
        for k in range(6): B(c,SNOW,0,-5.25,z+.16+k*.29,2.01,.30,.122,.017)
    B(c,SEC,0,-4.01,top+.82,3.20,2.75,1.56,.08); label('36',0,-5.40,top+1.61,2.36,1.05); B(c,SNOW,0,-4.01,top+2.36,3.50,3.03,.18,.05)
    B(c,ACC,0,-5.24,2.64,5.42,1.75,.28,.09); label('BLOK   KORAL',0,-6.13,2.78,2.81,.19)
    for x in (-6.79,6.79):
        B('Roof services',WALL,x,1.22,top+.39,3.02,2.81,.99,.055); B('Roof services',SEC,x,1.22,top+1.34,3.23,3.06,.14,.04)
        for k in range(3): B('Roof services',METAL,x,-.23,top+.58+k*.20,2.22,.07,.10)


if __name__ == "__main__":
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, SIZE)
    index_preview(OUT / "preview.png")
