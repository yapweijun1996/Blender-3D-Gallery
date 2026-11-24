"""Blok 41 Jalan Siku | junction-wedge HDB shop flats
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
    cam.data.ortho_scale = 1.135 * max(max(xx)-min(xx),(max(yy)-min(yy))*aspect) / min(1.0, aspect)
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

def sign(section, mat, text, pos, width, height):
    # Use only the Blender built-in font. Freeze the lettering to mesh for GLB.
    curve = bpy.data.curves.new('Sign artwork', 'FONT')
    curve.body, curve.align_x, curve.align_y = text, 'CENTER', 'CENTER'
    curve.resolution_u = 4
    curve.extrude = .009
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


def sash(x,y,z,w,h,n=3,seed=0,hood=False):
    """Framed opaque glazing; sill and a continuous high-level transom."""
    s='Casement assemblies'
    B(s,DARK,x,y-.04,z,w+.12,.12,h+.12)
    for i in range(n):
        xx=x+w*((i+.5)/n-.5); tone=(i+seed)%7
        B(s,GLASS[2 if tone==4 else 1 if tone%3 else 0],xx,y-.115,z+.06,w/n-.057,.045,h-.04)
    B(s,DARK,x,y-.146,z+h*.77,w,.045,.048)
    B(s,SNOW,x,y-.075,z-.07,w+.25,.26,.095,.013)
    if hood: B('Monsoon sunhoods',SEC,x,y-.22,z+h+.14,w+.4,.65,.11,.02)


def fascia(text,x,y,z,w,h,face=None):
    s='Street lettering'; B(s,face or ACC,x,y,z-h/2,w,.17,h,.032)
    sign(s,SNOW,text,(x,y-.11,z),w*.91,h*.67)

SLUG = 'sgmy-building-siku-junction-wedge-flats'
TITLE = 'Blok 41 Jalan Siku | junction-wedge HDB shop flats'
VIEW = (-.94,-1.66,.89)
SIZE = (790,610)


def build():
    palette('ecd4b5','a65946','617e70','848a7f','684d38'); s='Wedge plan walk-up'; a='Five foot shopping arcade'; t='Sunbreaks'; base=3.74; n=5; h=2.87; top=base+n*h
    # Two streets meet at an acute angle; bevel off the nose for the common stair.
    plan=[(-12.3,-4.29),(12.25,-4.29),(12.25,7.13),(9.51,7.13),(-11.97,-.89)]
    def collar(points,k): return [(x*k,y*k) for x,y in points]
    section(a,PAVE,collar(plan,1.094),0,.19); section(s,WALL,plan,base,n*h); section(a,ACC,collar(plan,1.03),base-.29,.29)
    inner=[(-10.58,-2.76),(11.47,-2.76),(11.47,5.88),(9.61,5.88),(-10.58,-1.69)]; section(s,GLASS[0],inner,.19,base-.19)
    shops=['KEDAI BUKU','KOPI SIKU','KEDAI BUNGA','DOBI 41']
    for j,cx in enumerate((-7.88,-2.26,3.36,8.98)):
        sash(cx-.65,-2.78,.44,3.21,2.0,3,j); door(cx+1.45,-2.78,.2,1.02,2.19)
        cloth=ACC if j%2 else SEC
        fascia(shops[j],cx,-4.49,3.25,5.24,.66,cloth)
        # Short striped canvas shades over the bookstall and the florist.
        if j in (0,2):
            for i in range(11):
                u=cx+5.14*((i+.5)/11-.5)
                prism(a,SNOW if i%2 else cloth,[(-4.40,2.99),(-5.13,2.69),(-5.13,2.57),(-4.40,2.87)],u-.233,u+.233,'X')
    pot(3.01,-3.70,.20,.32,.40); pot(3.72,-3.83,.20,.23,.31)
    for xx in (-11.73,-6.02,-.31,5.40,11.47): B(a,SNOW,xx,-4.20,.19,.41,.44,3.31,.035)
    for j in range(5): B(a,SNOW,-11.53+j*5.17,-.79+j*1.93,.19,.41,.44,3.31,.035)
    B(a,ACC,11.12,4.97,.19,1.64,3.13,3.31)
    for k in range(n):
        z=base+k*h; section(t,SNOW,collar(plan,1.024),z,.17)
        for j in range(6):
            u=(j-2.5)*3.92
            sash(u,-4.30,z+.72,2.89,1.42,3,j+k)
            if (j+k)%3==0:
                B(t,SEC,u,-4.61,z+.34,3.21,.77,.37); B(t,SNOW,u,-4.68,z+.69,3.35,.83,.095,.015)
            B(t,ACC,u-1.71,-4.48,z+.24,.12,.45,2.55)
        # Back elevation tracks the long diagonal lot line rather than being a blank wall.
        p,q=plan[3],plan[4]; dx,dy=q[0]-p[0],q[1]-p[1]
        with frame((p[0]+q[0])/2,(p[1]+q[1])/2,math.degrees(math.atan2(dy,dx))):
            for j in range(6): sash((j-2.5)*3.65,0,z+.77,2.44,1.37,3,k+j,True)
        with frame(12.26,1.42,90):
            for xx in (-3.66,0,3.66): sash(xx,0,z+.86,2.32,1.29,2,k)
        # Stair landing apertures carried by a continuous teal-painted prow.
        p,q=plan[-1],plan[0]; dx,dy=q[0]-p[0],q[1]-p[1]
        with frame((p[0]+q[0])/2,(p[1]+q[1])/2,math.degrees(math.atan2(dy,dx))):
            B(t,SEC,0,-.09,z,3.39,.23,h+.01)
            for j in range(3): B(t,DARK,0,-.222,z+.91+j*.23,2.26,.057,.118)
            if k==4: fascia('41',0,-.24,z+2.06,1.78,.86)
    section(s,ROOF,collar(plan,1.03),top,.22)
    for i,p in enumerate(plan):
        q=plan[(i+1)%len(plan)]; beam(s,SNOW,(*p,top+.43),(*q,top+.43),.18,.48)
    # Corrugated tank enclosure on a masonry stair-head plinth.
    B(s,SEC,6.82,.92,top+.20,5.49,3.44,1.65,.035); B(s,SNOW,6.82,.92,top+1.84,5.76,3.70,.18,.03)
    for x in (5.61,8.04):
        pole('Header tanks',ROOF,x,.92,top+2.03,1.38,1.05,32)
        for z in (.13,.61,1.18): pole('Header tanks',PAVE,x,.92,top+2.03+z,.062,1.08,32)
        pole('Header tanks',DARK,x,.92,top+3.41,.08,1.11,32)


if __name__ == "__main__":
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, SIZE)
    index_preview(OUT / "preview.png")
