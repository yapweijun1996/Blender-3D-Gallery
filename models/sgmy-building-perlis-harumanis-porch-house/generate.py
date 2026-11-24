"""Perlis | harumanis sorting verandah.
Original SG/MY static exterior, 1 unit = 1 m; front -Y and origin at ground.
Rebuild: blender -b --python generate.py. No external artwork. Draco required.
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
    # Bake the measured footprint centre into the meshes, not a node transform.
    points = [p for vs,_,_,_ in PARTS.values() for p in vs]
    dx,dy = [(min(p[i] for p in points)+max(p[i] for p in points))*.5 for i in (0,1)]
    dz = min(p[2] for p in points)
    for vs,_,_,_ in PARTS.values():
        vs[:] = [(x-dx,y-dy,z-dz) for x,y,z in vs]
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
    scene.cycles.samples = 32
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

def label(text,x,y,z,w,h,mat=None):
    sign('Cast lettering',mat or SNOW,text,(x,y,z),w,h)

def section(s, mat, points, z, height):
    """Extrude an XY footprint."""
    n=len(points)
    add(s,mat,[(x,y,zz) for zz in (z,z+height) for x,y in points],
        [tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])

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

def hip(s,x,y,z,w,d,rise,ridge,mat=None):
    """Pitched tile roof; ridge along Y. Cover rolls meet each hip at its true height."""
    m=mat or ROOF
    outline=[(x-w/2,y-d/2,z),(x+w/2,y-d/2,z),(x+w/2,y+d/2,z),(x-w/2,y+d/2,z)]
    apex=[(x,y-ridge/2,z+rise),(x,y+ridge/2,z+rise)]
    add(s,m,outline+apex,[(0,1,4),(1,2,5,4),(2,3,5),(3,0,4,5),(3,2,1,0)])
    for i,p in enumerate(outline): rod(s,m,p,apex[0 if i<2 else 1],.085,8)
    rod(s,m,*apex,.11,10)
    for a in (-1,1):
        N=round(d/.37)
        for j in range(N):
            dy=((j+.5)/N-.5)*d
            t=min(1,(d/2-abs(dy))/((d-ridge)/2))
            rod(s,m,(x+a*w/2,y+dy,z+.016),(x+a*w/2*(1-t),y+dy,z+rise*t+.016),.037,7)
        N=round(w/.37)
        for j in range(N):
            dx=((j+.5)/N-.5)*w;t=1-abs(dx)/(w/2)
            rod(s,m,(x+dx,y+a*d/2,z+.016),(x+dx,y+a*(d/2-t*(d-ridge)/2),z+rise*t+.016),.037,7)
    B(s,TIM,x,y,z-.14,w,d,.14,.025)

def fence(s,x,y,z,w,h,m=None):
    m=m or ACC
    for j in range(round(w/.27)+1):
        xx=x-w/2+w*j/round(w/.27);B(s,m,xx,y,z,.057,.068,h)
    for zz in (.09,h-.07): B(s,m,x,y,z+zz,w+.07,.10,.075,.015)

def plant(s,x,y,z,r=.5):
    turn(s,TILE,x,y,[(z,.65*r),(z+.1*r,.66*r),(z+.94*r,r),(z+1.04*r,r)],16)
    turn(s,EARTH,x,y,[(z+r,.94*r),(z+1.06*r,.94*r)],16)
    for j in range(19):
        a=j*2.4; length=r*(1.36+.17*(j%4));h=r*(1.12+.19*(j%5));w=.19*r
        def p(u,v,dz): return (x+u*math.cos(a)-v*math.sin(a),y+u*math.sin(a)+v*math.cos(a),z+1.05*r+dz)
        add(s,[MOSS,LEAF,FERN][j%3],[p(0,0,0),p(length*.44,-w,h*.74),p(length*.56,0,h),p(length*.44,w,h*.74),p(length,0,h*.66)],[(0,1,2),(0,2,3),(1,4,2),(2,4,3)])

def stairs(s,x,front,z,w,n,rise=.17,run=.30,m=None):
    for j in range(n): B(s,m or PAVE,x,front+(j+.5)*run,z,w,run,(j+1)*rise,.014)

def planks(s,x,y,z,w,h,pitch=.235):
    for j in range(1,math.ceil(h/pitch)):
        B(s,TIM,x,y-.014,z+j*pitch,w,.047,.024)

SLUG = 'sgmy-building-perlis-harumanis-porch-house'

TITLE = 'Perlis | harumanis sorting verandah'

VIEW = (1.18,-1.86,.94)

SIZE = (750,640)

def fruitcrate(x,y,z):
    s='Slatted mango trays';B(s,TIM,x,y,z,1.03,.69,.11)
    for a in (-1,1):
        for h in (.09,.22):
            B(s,WALL,x,y+a*.34,z+h,1.09,.061,.092);B(s,WALL,x+a*.51,y,z+h,.06,.67,.093)
    for i in range(4):
        for j in range(2):
            xx=x+(i-1.5)*.241; yy=y+(j-.5)*.27
            turn(s,LEAF if (i+j)%3 else FERN,xx,yy,[(z+.10,.042),(z+.16,.093),(z+.28,.104),(z+.36,.077),(z+.40,.029)],10)

def build():
    palette('c99868','436f5d','915e42','597778','70503c');s='Raised plank house';t='Sorting porch'
    B(s,PAVE,-1.69,.43,0,6.51,9.22,.105,.025)
    for x in (-4.33,-1.75,.92,4.46):
        for y in (-3.70,.22,4.18):
            B(s,PAVE,x,y,0,.47,.47,.60,.032);B(s,TIM,x,y,.59,.28,.28,.87)
    B(s,TIM,-1.68,.27,1.31,6.62,9.53,.21,.018);B(s,WALL,-1.68,.44,1.52,6.28,8.92,2.69)
    hip('Main zinc bumbung',-1.68,.44,4.32,7.85,10.61,2.39,3.3)
    for a in (-1,1):
        with frame(-1.68,.44+a*4.46,0 if a<0 else 180):
            planks(s,0,0,1.54,6.26,2.62);door(.62,-.026,1.52,1.24,2.28,ACC)
            for xx in (-2.11,2.12):shutter(xx,-.036,2.14,1.23,1.38,ACC)
        with frame(-1.68+a*3.14,.44,a*90):
            planks(s,0,0,1.54,8.88,2.61)
            for xx in (-2.88,0,2.88):shutter(xx,-.035,2.12,1.55,1.39,ACC)
    # Front landing with a pierced timber apron, tread nosings and turned newels.
    B(s,SEC,-1.58,-4.65,1.34,6.84,1.56,.18)
    stairs(s,-1.07,-7.96,0,1.62,8,.19,.32,TIM)
    for a in (-1,1):
        x=-1.07+a*.85
        beam(s,ACC,(x,-7.80,.96),(x,-5.47,2.36),.093,.11)
        for j in (0,3,7):B(s,SNOW,x,-7.80+j*.32,(j+1)*.19,.11,.11,.82)
    fence(s,-3.43,-5.37,1.52,2.75,.82,ACC);fence(s,.68,-5.37,1.52,1.59,.82,ACC)
    # Open-sided lean-to. Scales and fruit boxes sit at working height beside the long sorting bench.
    B(t,SEC,3.12,.22,1.32,3.48,8.64,.20);B(t,PAVE,3.13,-4.19,0,3.59,.53,.13,.02)
    for j in range(13):B(t,TIM,1.5+j*.263,.22,1.52,.246,8.62,.042)
    for y in (-3.78,.24,4.14):
        B(t,ACC,4.61,y,1.55,.16,.16,1.99);beam(t,TIM,(4.61,y,3.0),(4.05,y,3.61),.12)
    prism(t,ROOF,[(1.15,4.22),(5.19,3.33),(5.19,3.46),(1.15,4.35)],-4.56,4.71)
    for i in range(32):beam(t,ROOF,(1.15,-4.51+i*.293,4.36),(5.19,-4.51+i*.293,3.47),.052,.07)
    B(t,SNOW,5.13,.075,3.26,.14,9.29,.16);B(t,TIM,3,.27,2.21,1.46,6.92,.13,.02)
    for x in (2.46,3.56):
        for y in (-2.91,.20,3.41):B(t,TIM,x,y,1.56,.12,.12,.66)
    for j in range(6):fruitcrate(3.04,-2.54+j*1.11,2.34)
    fruitcrate(4.02,-3.45,1.56);fruitcrate(2.74,-3.54,1.56)
    B(t,ACC,3.05,-4.54,3.14,2.77,.10,.41,.017);label('HARUMANIS',3.05,-4.609,3.35,2.44,.23)
    plant('Porch croton',-4.31,-4.74,1.52,.36)


if __name__ == "__main__":
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, SIZE)
    index_preview(OUT / "preview.png")
