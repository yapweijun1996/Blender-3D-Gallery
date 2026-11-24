"""Rumah Ukir | Terengganu bachelor house with carved gable
Original deterministic exterior. From this directory: blender -b -P generate.py
Units: metres. Street front: -Y. Static, opaque PBR, UV0. No external assets.
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
    root['design'] = TITLE
    root['source_note'] = 'Original procedural design; no external assets'
    root['revision'] = 1
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


def steps(x,y,z,w,n,rise=.17,going=.29,mat=None):
    # Ascend from the street toward +Y; y is the building-side landing.
    for i in range(n):
        B('Stair treads',mat or PAVE,x,y-(n-i-.5)*going,z,w,going+.004,(i+1)*rise,.017)


def gable(x,y,z,w,d,rise,metal=False):
    # Ridge on Y, visible bargeboards on both gable ends.
    s='Pitched roof'; p=[(-w/2,0),(0,rise),(w/2,0),(w/2,-.11),(-w/2,-.11)]
    prism(s,ROOF,[(x+a,z+b) for a,b in p],y-d/2,y+d/2)
    for side in (-1,1):
        u=x+side*w/2
        for v in (y-d/2-.02,y+d/2+.02):
            beam('Raking bargeboards',SNOW,(u,v,z-.04),(x,v,z+rise-.04),.14,.18)
        rod(s,ROOF,(u,y-d/2,z),(u,y+d/2,z),.085)
        for j in range(1,math.ceil(w/.65)):
            f=j/math.ceil(w/.65)
            if not metal:
                rod(s,ROOF,(u+(x-u)*f,y-d/2,z+rise*f+.016),(u+(x-u)*f,y+d/2,z+rise*f+.016),.03,6)
        for j in range(1,round(d/(.48 if metal else .42))):
            yy=y-d/2+j*d/round(d/(.48 if metal else .42))
            rod(s,ROOF,(u,yy,z+.018),(x,yy,z+rise+.018),.028 if metal else .043,6)
    rod(s,ROOF,(x,y-d/2-.05,z+rise),(x,y+d/2+.05,z+rise),.095)


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


def archband(s,mat,x,y,z,rx,rz,thick,d,start=0,end=180,n=24):
    # Arc ribbon in elevation; no coincident end caps between segments.
    pts=[]; faces=[]
    for i in range(n+1):
        a=math.radians(start+(end-start)*i/n)
        for yy,rr in ((y,0),(y,thick),(y+d,thick),(y+d,0)):
            pts.append((x+(rx+rr)*math.cos(a),yy,z+(rz+rr)*math.sin(a)))
        if i:
            for j in range(4): faces.append(((i-1)*4+j,(i-1)*4+(j+1)%4,i*4+(j+1)%4,i*4+j))
    if end-start<360: faces.extend([(3,2,1,0),tuple(range(n*4,n*4+4))])
    add(s,mat,pts,faces)


def fan(x,y,z,w,h,mat=None):
    s='Radial fanlights'; pts=[(x+w*.5*math.cos(i*math.pi/24),z+h*math.sin(i*math.pi/24)) for i in range(25)]
    prism(s,GLASS[0],pts,y-.05,y+.02)
    archband(s,mat or SNOW,x,y-.13,z,w/2,h,.095,.13)
    for i in range(1,8):
        a=i*math.pi/8
        beam(s,mat or SNOW,(x,y-.085,z),(x+w*.5*math.cos(a),y-.085,z+h*math.sin(a)),.047,.04)
    B(s,mat or SNOW,x,y-.06,z-.06,w+.18,.16,.085)


def tile_border(x,y,z,w,h,n,mat=None):
    s='Encaustic tile frieze'; B(s,SNOW,x,y,z,w,.07,h)
    pitch=w/n
    for i in range(n):
        u=x-w/2+pitch*(i+.5); v=z+h/2
        prism(s,mat or ACC,[(u-pitch*.43,v),(u,v+h*.43),(u+pitch*.43,v),(u,v-h*.43)],y-.042,y-.036)
        if pitch>.27:
            prism(s,SUN,[(u-pitch*.14,v),(u,v+h*.17),(u+pitch*.14,v),(u,v-h*.17)],y-.051,y-.045)


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


def rail(x,y,z,w,h=.99,mat=None):
    s='Guard rails'; mat=mat or DARK
    for v in (.10,h): B(s,mat,x,y,z+v,w,.072,.067,.008)
    for i in range(1+math.ceil(w/.28)):
        u=x+w*(i/math.ceil(w/.28)-.5); B(s,mat,u,y,z+.10,.043,.049,h-.08)

SLUG = 'sgmy-building-terengganu-bujang-ukir-house'
TITLE = 'Rumah Ukir | Terengganu bachelor house with carved gable'
VIEW = (.91,-1.36,.68)
SIZE = (780,640)


def build():
    palette('916044','326b65','c18b55','874a39','573d30'); s='Post and beam frame'; g='Carved gable end'; v='Open side serambi'
    # One tall bay under a bumbung panjang and a continuous, lower side gallery.
    for x in (-3.7,-.96,1.79,4.02):
        for y in (-4.45,-1.43,1.60,4.63):
            B(s,PAVE,x,y,0,.43,.43,.41,.045); B(s,TIM,x,y,.40,.26,.26,1.32,.018)
    B(s,TIM,-1,.09,1.39,5.93,9.66,.28); B(s,WALL,-1,.09,1.66,5.7,9.46,2.90)
    for y in (-4.65,4.83):
        with frame(-1,y,0 if y<0 else 180):
            for i in range(26): B(s,SEC,(i-12.5)*.214,-.016,1.71,.026,.051,2.77)
            for xx in (-1.62,1.62):
                shutter(xx,-.052,2.28,1.36,1.36,ACC); tile_border(xx,-.083,3.80,1.47,.32,6,TIM)
            if y<0: door(0,-.059,1.68,1.08,2.10)
            else: shutter(0,-.052,2.43,.88,1.12)
    for x,angle in [(-3.855,-90),(1.855,90)]:
        with frame(x,.09,angle):
            for xx in (-3.05,0,3.05):
                if x>0 and xx==0: door(0,0,1.67,1.0,2.01)
                else: shutter(xx,0,2.24,1.50,1.47,ACC)
    gable(-1,.09,4.59,6.90,10.62,2.97)
    for yy,angle in ((-5.24,0),(5.42,180)):
        with frame(-1,yy,angle):
            # A layered tebar layar edged in notched fretwork and a central sunburst.
            prism(g,SEC,[(-3.29,4.60),(0,7.43),(3.29,4.60)],-.095,.03)
            prism(g,ACC,[(-2.68,4.78),(0,7.08),(2.68,4.78)],-.123,-.096)
            for j in range(-7,8):
                u=j*.31; rise=2.16-abs(u)*.86
                B(g,TIM,u,-.145,4.81,.073,.06,rise)
            fan(0,-.18,4.81,2.52,.93,SEC)
            for j in range(-10,11):
                u=.296*j; prism(g,SNOW,[(u-.115,4.61),(u+.115,4.61),(u+.078,4.39),(u,4.26),(u-.078,4.39)],-.125,-.052)
            for side in (-1,1):
                beam(g,SNOW,(side*3.48,-.14,4.57),(0,-.14,7.56),.10,.13)
                beam(g,SEC,(side*.37,-.15,7.22),(-side*.25,-.15,7.84),.087,.11)
    B(v,TIM,2.99,.09,1.44,2.57,9.68,.20)
    for i in range(13): B(v,WALL,1.85+i*.19,.09,1.64,.183,9.67,.035)
    for y in (-4.48,-1.43,1.60,4.63): B(v,TIM,4.02,y,1.64,.17,.17,2.36,.013)
    with frame(4.02,.09,90):
        for u in (-3.03,0,3.03):
            rail(u,0,1.66,2.9,.82,ACC); B(v,SEC,u,0,2.51,2.97,.13,.09)
    prism(v,ROOF,[(1.39,4.87),(4.64,3.99),(4.64,3.86),(1.39,4.74)],-5.01,5.17)
    for i in range(26): beam(v,ROOF,(1.39,-4.95+i*.40,4.89),(4.64,-4.95+i*.40,4.01),.055,.055)
    steps(2.99,-4.75,0,1.84,10,.166,.255,TIM)
    for side in (-1,1):
        x=2.99+side*.89; beam(v,SEC,(x,-7.18,1.02),(x,-4.74,2.53),.092,.10)
        for i in (0,3,6,9): B(v,ACC,x,-7.18+i*.26,(i+1)*.166,.10,.10,.86)
    B(v,TIM,-1,-4.95,1.45,3.6,.9,.21); steps(-1,-5.40,0,1.38,10,.166,.24,TIM)
    for x in (-2.32,.32): B(s,TIM,x,-5.20,.0,.21,.21,1.45)
    pot(3.6,-4.27,1.68,.23,.33)


if __name__ == "__main__":
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, SIZE)
    index_preview(OUT / "preview.png")
