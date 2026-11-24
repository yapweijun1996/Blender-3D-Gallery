"""Cherating | woven nipah cottage.
Original procedural SG/MY exterior; Blender 5.2, metre units, front -Y.
Rebuild: blender -b --python generate.py. No external art or textures.
GLB requires Draco. Studio, lights and camera are preview-only.
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


def beam(section, mat, a, b, width, depth=None, bevel=0):
    a, b = Vector(a), Vector(b)
    axis = b - a
    basis = axis.to_track_quat('Z','Y').to_matrix()
    box(section, mat, (a+b)/2, (width, depth or width, axis.length), bevel, basis=basis)


def prism(section, mat, poly, a, b, axis='Y'):
    # A simple cross-section, extruded along X or Y.
    verts = [(u,v,w) if axis == 'Y' else (v,u,w) for v in (a,b) for u,w in poly]
    n = len(poly)
    faces = [tuple(reversed(range(n))), tuple(range(n,2*n))]
    faces.extend((i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n))
    add(section, mat, verts, faces)


def rod(section, mat, a, b, radius, n=10, taper=1):
    a, b = Vector(a), Vector(b)
    basis = (b-a).to_track_quat('Z','Y').to_matrix()
    verts = [p+basis @ Vector((rad*math.cos(TAU*j/n),rad*math.sin(TAU*j/n),0))
             for p,rad in ((a,radius),(b,radius*taper)) for j in range(n)]
    faces = [(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
    faces.extend((tuple(reversed(range(n))),tuple(range(n,2*n))))
    add(section, mat, verts, faces, [True]*n+[False,False])


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
    root['role'] = 'Static building exterior'
    root['category'] = 'building'
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
        # Texture-free material palette; UV0 still provides an edit layout within each mesh.
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
    bpy.context.object.data.materials.append(MATS[material('Studio Limestone','b7b3a6',.9)])
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
    scene.cycles.samples = 16
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


def door(x,y,z,w=1.05,h=2.16,mat=None):
    s='Entrance joinery'; mat=mat or TIM
    B(s,DARK,x,y-.04,z,w+.13,.12,h+.08)
    for i in (-1,1):
        cx=x+i*w/4
        B(s,mat,cx,y-.12,z+.015,w/2-.022,.10,h-.02)
        for zz,hh in ((.14,h*.32),(h*.51,h*.40)):
            B(s,SEC,cx,y-.18,z+zz,w*.34,.04,hh,.015)
        B(s,SUN,x+i*.09,y-.235,z+.84,.032,.06,.21,.01)


def section(s, mat, points, z, height):
    """Extrude an XY footprint."""
    n=len(points)
    add(s,mat,[(x,y,zz) for zz in (z,z+height) for x,y in points],
        [tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])


def pole(s,mat,x,y,z,h,r,n=12):
    rod(s,mat,(x,y,z),(x,y,z+h),r,n)


def shutter(x,y,z,w,h,mat=None):
    s='Louvred shutters'; m=mat or ACC
    B(s,DARK,x,y-.025,z,w,.08,h,.014)
    for j in (-1,1):
        xx=x+j*w/4
        for k in (-1,1): B(s,m,xx+k*(w*.25-.04),y-.085,z,.077,.105,h)
        for a in (0,h*.48,h-.09): B(s,m,xx,y-.089,z+a,w*.5-.1,.105,.09)
        for i in range(1,max(3,int(h/.125))):
            zz=z+i*h/int(h/.125)
            box(s,m,(xx,y-.078,zz),(w*.5-.14,.08,.083),basis=Matrix.Rotation(.31,3,'X'))
    B(s,SNOW,x,y-.07,z-.075,w+.16,.22,.09,.012)


def pot(x,y,z,r=.36,h=.53):
    s='Potted pandan'; rod(s,TILE,(x,y,z),(x,y,z+h),r*.7,12,1/.7)
    pole(s,TILE,x,y,z+h-.08,.10,r*1.09); pole(s,EARTH,x,y,z+h+.015,.016,r*.91)
    for i in range(15):
        a=i*2.399; v=Vector((math.cos(a),math.sin(a),0)); u=Vector((-v.y,v.x,0)); p=Vector((x,y,z+h)); l=r*(1.04+.38*math.sin(i*7)); shoulder=p+v*l*.55+Vector((0,0,r*(1.25+(i%4)*.25))); tip=p+v*l*1.48+Vector((0,0,r*(.77+(i%5)*.29)))
        verts=[p,shoulder+u*r*.18,shoulder+Vector((0,0,.11*r)),shoulder-u*r*.18,tip]
        add(s,[MOSS,LEAF,FERN][i%3],verts,[(0,1,2),(0,2,3),(1,4,2),(2,4,3)])


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


def rail(x, y, z, length, height=.96, color=None):
    s='Verandah balustrades'; color=color or TIM
    B(s,color,x,y,z+height-.08,length,.12,.09,.015)
    B(s,color,x,y,z+.10,length,.085,.08)
    count=max(1,round(length/.24))
    for j in range(count+1):
        B(s,color,x+length*(j/count-.5),y,z+.15,.048,.062,height-.18)

SLUG = 'sgmy-building-cherating-nipah-screen-house'
TITLE = 'Cherating | woven nipah cottage'
VIEW = (.92,-1.55,.77)
SIZE = (750,635)


def thatch(x,y,w,d,z,rise):
    s='Layered palm thatch'; colors=[ROOF,material('Thatch | sun tips','b18b56'),material('Thatch | dry leaf','a08051')]
    prism(s,ROOF,[(y-d/2,z),(y,z+rise),(y+d/2,z)],x-w/2,x+w/2,'X')
    for side in (-1,1):
        for j in range(9):
            a=j/9; b=(j+1)/9; ya=y+side*d/2*(1-a); yb=y+side*d/2*(1-b); za=z+rise*a; zb=z+rise*b
            prism(s,colors[(j+1)%3],[(ya+side*.12,za-.045),(ya+side*.12,za+.11),(yb,zb+.11),(yb,zb-.025)],x-w/2-.07,x+w/2+.07,'X')
            # Visible combed ends of the bundled leaves below each lap.
            for k in range(round(w/.17)):
                xx=x-w/2+.09+k*.17
                jitter=math.sin(k*34.7+j*7.9)
                beam(s,colors[(j+k)%3],(xx,ya+side*(.135+.04*jitter),za+.128-.044*jitter),(xx+.033*jitter,yb,zb+.157),.045+.012*jitter,.047)
        for xx in (x-w/2-.10,x+w/2+.10): beam('Timber bargeboards',TIM,(xx,y+side*d/2,z-.02),(xx,y,z+rise+.17),.14,.19)
    rod(s,TIM,(x-w/2-.21,y,z+rise+.17),(x+w/2+.21,y,z+rise+.17),.145,12)


def weave(x,y,z,w,h):
    s='Woven bamboo wall panels'; B(s,SEC,x,y-.034,z,w,.07,h)
    # Clip crossing reed strips to a rectangular panel (no decal or alpha mask).
    for slope,m in ((1,WALL),(-1,SUN)):
        for k in range(-30,31):
            b=k*.41; lo=max(-w/2,min(-b/slope,(h-b)/slope)); hi=min(w/2,max(-b/slope,(h-b)/slope))
            if hi-lo>.02: beam(s,m,(x+lo,y-.087,z+slope*lo+b),(x+hi,y-.087,z+slope*hi+b),.049,.025)
    for xx in (x-w/2,x+w/2): B(s,TIM,xx,y-.095,z,.08,.11,h)


def build():
    palette('d4b783','537567','ad8b5c','9a7951','654735')
    s='Post and beam frame'; v='Shaded serambi'
    for x in (-4.4,-1.48,1.48,4.4):
        for y in (-2.28,.47,3.13):
            B(s,PAVE,x,y,0,.45,.47,.32,.025); B(s,TIM,x,y,.32,.27,.27,1.08)
    B(s,TIM,0,.43,1.31,9.27,6.05,.23); B(s,WALL,0,.43,1.54,9.0,5.62,2.70)
    for y in (-2.39,3.25):
        with frame(0,y,0 if y<0 else 180):
            for xx in (-3.27,-1.09,1.09,3.27):
                weave(xx,0,1.62,2.05,.70)
                if y<0 and xx==-1.09: door(xx,0,1.55,1.17,2.14)
                else: shutter(xx,-.03,2.47,1.27,1.29,ACC)
                B(s,TIM,xx-1.06,-.047,1.54,.10,.11,2.70)
    for side in (-1,1):
        with frame(side*4.51,.43,90*side):
            for xx in (-1.39,1.39): weave(xx,0,1.69,2.63,.70); shutter(xx,0,2.5,1.44,1.28)
    thatch(0,.43,10.47,7.20,4.24,2.98)
    for side in (-1,1):
        with frame(side*5.242,.43,side*90):
            B(s,TIM,0,-.038,4.24,7.24,.12,.14)
            for j in range(-6,7):
                u=j*.45; h=2.78-abs(u)*.83
                B(s,TIM,u,-.045,4.39,.077,.10,h)
            for j in (-1,0,1):
                u=j*.43
                for k in range(5-abs(j)): B(s,DARK,u,-.10,5.45+k*.139,.34,.08,.070)
    B(v,TIM,-1.34,-3.51,1.29,5.67,2.37,.22)
    for x in (-4.01,-1.3,1.33):
        B(v,PAVE,x,-4.50,0,.40,.40,.26,.02); B(v,TIM,x,-4.50,.26,.22,.22,3.35)
        beam(v,TIM,(x,-4.50,3.35),(x,-2.31,4.22),.13,.16)
    prism(v,ROOF,[(-4.89,3.35),(-4.89,3.52),(-2.32,4.46),(-2.32,4.25)],-4.43,1.80,'X')
    for i in range(26): beam(v,SEC,(-4.40+i*.24,-4.88,3.52),(-4.40+i*.24,-2.32,4.47),.039,.042)
    rail(-2.72,-4.50,1.51,2.55,.79); rail(.42,-4.50,1.51,1.65,.79)
    for j in range(8): B(v,TIM,-.91,-4.81-j*.255,1.39-j*.182,1.43,.287,.097,.013)
    for x in (-1.48,-.34): beam(v,TIM,(x,-6.67,.13),(x,-4.57,1.40),.125,.20)
    for x in (-1.63,-.19): beam(v,TIM,(x,-6.53,1.05),(x,-4.61,2.38),.089,.12); B(v,TIM,x,-6.54,.19,.11,.11,.91)
    pot(-3.62,-3.65,1.51,.27,.36)


if __name__ == "__main__":
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, SIZE)
    index_preview(OUT / "preview.png")
