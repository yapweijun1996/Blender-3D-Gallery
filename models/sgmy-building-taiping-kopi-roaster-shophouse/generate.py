"""Kopi Bara | Taiping roaster and upstairs rooms.
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


def hip(x,y,z,w,d,rise,cut,mat=None,metal=False):
    # Roof ridge runs east-west. Linear rows wrap consistently over all four planes.
    s='Roof covering'; mat=mat or ROOF
    ax,by=w/2,d/2; ridge=ax-cut
    corners=[(x-ax,y-by,z),(x+ax,y-by,z),(x+ax,y+by,z),(x-ax,y+by,z)]
    ends=[(x-ridge,y,z+rise),(x+ridge,y,z+rise)]
    add(s,mat,corners+ends,[(0,1,5,4),(1,2,5),(2,3,4,5),(3,0,4),(3,2,1,0)])
    for j in range(4): beam('Eave fascia',TIM,corners[j],corners[(j+1)%4],.14,.19)
    for i,k in ((0,0),(3,0),(1,1),(2,1)):
        if cut>.001: rod(s,mat,corners[i],ends[k],.084,8)
    rod(s,mat,ends[0],ends[1],.12,10)
    rows=max(5,round(math.hypot(by,rise)/.35))
    if not metal:
        for j in range(1,rows):
            f=j/rows; dx=ax-cut*f; dy=by*(1-f); zz=z+rise*f+.007
            for side in (-1,1):
                rod(s,mat,(x-dx,y+side*dy,zz),(x+dx,y+side*dy,zz),.028,6)
                if cut>.001: rod(s,mat,(x+side*dx,y-dy,zz),(x+side*dx,y+dy,zz),.024,6)
    # Raised roll tiles / standing seams; terminate each roll at its hip.
    for j in range(1,math.ceil(w/(.45 if metal else .50))):
        xx=-ax+j*w/math.ceil(w/(.45 if metal else .50)); f=min(1,(ax-abs(xx))/max(.001,cut))
        for side in (-1,1): rod(s,mat,(x+xx,y+side*by,z+.015),(x+xx,y+side*by*(1-f),z+rise*f+.015),.039 if not metal else .024,6)


def label(text,x,y,z,w,h,mat=None):
    sign('Cast lettering',mat or SNOW,text,(x,y,z),w,h)


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


def disc(s,mat,x,y,z,r,t=.07,n=32):
    rod(s,mat,(x,y+t/2,z),(x,y-t/2,z),r,n)


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


def turn(s,mat,x,y,rings,n=24):
    """Lathe a closed, faceted profile specified by (height, radius) pairs."""
    verts=[(x+r*math.cos(TAU*j/n),y+r*math.sin(TAU*j/n),z) for z,r in rings for j in range(n)]
    faces=[(i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j) for i in range(len(rings)-1) for j in range(n)]
    add(s,mat,verts,faces+[tuple(reversed(range(n))),tuple(range(len(verts)-n,len(verts)))], [True]*len(faces)+[False,False])


def condenser(x,y,z):
    s='Service fittings'; B(s,SNOW,x,y-.21,z,1.1,.46,.66,.035)
    disc(s,DARK,x-.16,y-.452,z+.33,.24,.032,16)
    for i in range(5): B(s,METAL,x-.16,y-.48,z+.16+i*.08,.37,.023,.022)
    for i in range(3): B(s,METAL,x+.31,y-.45,z+.17+i*.11,.20,.035,.036)


def tilewalk(x,y,z,w,d,pitch=.46):
    s='Five foot way mosaic'; B(s,SEC,x,y,z,w,d,.052)
    nx,ny=round(w/pitch),round(d/pitch)
    for j in range(nx):
        for k in range(ny):
            if (j+k)%2==0: B(s,SNOW,x+((j+.5)/nx-.5)*w,y+((k+.5)/ny-.5)*d,z+.052,w/nx-.016,d/ny-.016,.012)

SLUG = 'sgmy-building-taiping-kopi-roaster-shophouse'
TITLE = 'Kopi Bara | Taiping roaster and upstairs rooms'
VIEW = (.82,-1.55,.71)
SIZE = (740,675)


def build():
    palette('efcb96','49786c','bb794b','9f5341','744d37')
    s='Limewash and ashlar'; t='Cornices and pilasters'; f='Roasting flue'
    B(s,PAVE,0,0,0,8.42,14.2,.16,.03)
    B(s,ACC,0,1.35,.16,7.62,10.9,3.35); B(s,WALL,0,.18,3.51,7.62,13.23,3.55)
    hip(0,.18,7.06,7.94,13.62,2.14,1.7)
    B(t,SEC,0,.16,3.34,7.88,13.5,.22,.032); B(t,SNOW,0,.16,3.56,8.02,13.63,.14,.025)
    tilewalk(0,-5.3,.16,7.91,2.67)
    for x in (-3.52,3.52):
        piers('Arcaded walkway',WALL,x,-6.21,.22,.48,3.12)
        B(t,ACC,x,-6.48,3.69,.41,.27,3.38); B(t,SNOW,x,-6.65,6.57,.55,.23,.24,.024)
    for x in (-2.37,0,2.37):
        shutter(x,-6.454,4.13,1.52,1.73); fan(x,-6.472,5.88,1.55,.66,ACC)
        # Ochre keystones and a deep projecting sill unify the arched openings.
        B(t,SNOW,x,-6.63,6.47,.25,.25,.26,.017); B(t,SEC,x,-6.65,3.97,1.81,.38,.14,.016)
    for z,m,w,d,h in [(6.87,ACC,7.85,.38,.19),(7.05,SNOW,8.05,.45,.13),(7.18,SEC,7.91,.34,.19)]: B(t,m,0,-6.48,z,w,d,h,.024)
    B(t,WALL,0,-6.43,7.37,7.71,.38,.44); B(t,ACC,0,-6.43,7.81,7.89,.45,.12,.015)
    for j in range(15): B(t,SNOW,(j-7)*.49,-6.65,7.46,.23,.12,.23,.012)
    door(-2.52,-4.11,.22,1.37,2.43); win(1.03,-4.11,.88,4.31,1.59,5,2,SUN)
    B(t,TIM,.10,-6.58,2.84,5.5,.21,.67,.035); label('K O P I   B A R A',.10,-6.70,3.18,5.02,.39,SNOW)
    # The enamel cup is a moulded three-dimensional trade sign, not a texture.
    cx,cy=3.40,-6.90; pole(t,DARK,cx,cy,2.39,.57,.044)
    turn('Enamel cup sign',SUN,cx,cy,[(2.30,.22),(2.34,.51),(2.38,.55)],32)
    turn('Enamel cup sign',SNOW,cx,cy,[(2.37,.21),(2.44,.26),(2.75,.38),(2.79,.39)],32)
    pole('Enamel cup sign',TIM,cx,cy,2.785,.013,.35,32)
    archband('Enamel cup sign',SNOW,cx+.35,cy-.05,2.62,.16,.118,.056,.085,-90,90,16)
    for j,(x,y) in enumerate(((.57,-4.83),(1.19,-4.87),(1.85,-4.80))):
        turn('Jute coffee sacks',PAVE,x,y,[(.22,.21),(.29,.28),(.71,.32),(.88,.25),(.92,.26)],14)
        pole('Jute coffee sacks',TIM,x,y,.918,.023,.235,14)
    for side in (-1,1):
        with frame(side*3.815,0,side*90):
            for i,y in enumerate((-3.8,.25,4.26)):
                shutter(y,0,4.47,1.36,1.57); B(t,SEC,y,-.20,6.13,1.76,.60,.11,.02)
                if abs(y)<1: condenser(y,0,1.41)
    with frame(0,6.81,180):
        door(1.75,0,.16); win(-1.65,0,4.48,2.6,1.44,3)
    turn(f,SEC,2.68,3.68,[(6.84,.41),(7.35,.39),(7.4,.32),(9.99,.30),(10.04,.36),(10.28,.36)],20)
    turn(f,DARK,2.68,3.68,[(10.28,.26),(10.62,.26),(10.64,.49),(10.87,.07)],20)
    pot(-3.24,-4.85,.22,.32,.44)


if __name__ == "__main__":
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, SIZE)
    index_preview(OUT / "preview.png")
