"""Terengganu | kedai tembaga and family gallery.
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

def tilewalk(x,y,z,w,d,pitch=.46):
    s='Five foot way mosaic'; B(s,SEC,x,y,z,w,d,.052)
    nx,ny=round(w/pitch),round(d/pitch)
    for j in range(nx):
        for k in range(ny):
            if (j+k)%2==0: B(s,SNOW,x+((j+.5)/nx-.5)*w,y+((k+.5)/ny-.5)*d,z+.052,w/nx-.016,d/ny-.016,.012)

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

def gable(s,x,y,z,w,d,rise,m=None):
    m=m or ROOF
    for a in (-1,1):
        edge=x+a*w/2
        prism(s,m,[(x,z+rise),(edge,z),(edge,z+.125),(x,z+rise+.125)],y-d/2,y+d/2)
        for i in range(round(d/.35)):
            yy=y+((i+.5)/round(d/.35)-.5)*d
            rod(s,m,(x,yy,z+rise+.13),(edge,yy,z+.13),.04,7)
        for yy in (y-d/2,y+d/2): beam(s,SNOW,(x,yy,z+rise+.07),(edge,yy,z+.07),.15,.15)
    rod(s,m,(x,y-d/2-.07,z+rise+.15),(x,y+d/2+.07,z+rise+.15),.115,10)

def fence(s,x,y,z,w,h,m=None):
    m=m or ACC
    for j in range(round(w/.27)+1):
        xx=x-w/2+w*j/round(w/.27);B(s,m,xx,y,z,.057,.068,h)
    for zz in (.09,h-.07): B(s,m,x,y,z+zz,w+.07,.10,.075,.015)

def planks(s,x,y,z,w,h,pitch=.235):
    for j in range(1,math.ceil(h/pitch)):
        B(s,TIM,x,y-.014,z+j*pitch,w,.047,.024)

def shopbase(w,d,ground,upper):
    """Covered public walkway below the projecting family floor."""
    s='Shop and residence'; front=-d/2
    B(s,PAVE,0,.02,0,w+.56,d+.66,.15,.03)
    B(s,WALL,0,.97,.15,w,d-1.94,ground-.15)
    B(s,WALL,0,0,ground,w,d,upper)
    tilewalk(0,front+.94,.15,w,2.32,.45)
    for x in (-w/2+.32,w/2-.32): piers('Arcade piers',ACC,x,front+.18,.213,.41,ground-.213)
    for zz,hh,ext,m in ((ground-.18,.16,.25,SEC),(ground-.02,.22,.39,SNOW),(ground+.21,.08,.28,ACC)):
        B(s,m,0,0,zz,w+ext,d+ext,hh,.025)
    for a in (-1,1):
        with frame(a*w/2,0,a*90):
            for i in (-1,0,1): shutter(i*d*.31,0,ground+.69,1.23,1.49,SEC)
            for i in (-1,1): win(i*d*.23,0,1.16,1.27,1.16,2,i)
    with frame(0,d/2,180):
        door(-w*.23,0,.15);win(w*.19,0,1.12,1.4,1.08);shutter(0,0,ground+.71,1.52,1.56)
    return front

SLUG = 'sgmy-building-terengganu-brassware-shophouse'

TITLE = 'Terengganu | kedai tembaga and family gallery'

VIEW = (.84,-1.86,.81)

SIZE = (740,656)

def vessel(s,x,y,z,k,brass):
    profile=[(0,.24),(.05,.29),(.12,.22),(.16,.21),(.23,.35),(.35,.44),(.48,.46),(.62,.36),(.72,.16),(.81,.13),(.84,.23),(.89,.22),(.91,.15)]
    turn(s,brass,x,y,[(z+a*k,b*k) for a,b in profile],28)
    disc_height=z+.915*k;turn(s,DARK,x,y,[(disc_height,.12*k),(disc_height+.005,.12*k)],16)

def pendant(s,x,y,z):
    rod(s,DARK,(x,y,z+.5),(x,y,z+.98),.018,8)
    turn(s,BRASS,x,y,[(z+.05,.42),(z+.12,.43),(z+.28,.26),(z+.34,.22),(z+.40,.10),(z+.53,.08)],32)
    turn(s,SNOW,x,y,[(z,.08),(z+.05,.14),(z+.09,.13)],16)

def build():
    global BRASS
    palette('a57c55','48645c','785542','784e46','634636');BRASS=material('Metal | hammered brass','cf9d4e',.31,.58)
    s='Balai gallery'; w=8.1;d=13.2;g=3.43;y=shopbase(w,d,g,2.82)
    # The living gallery has a projecting hipped bonnet and an independently ventilated roof monitor.
    hip('Lower tile hips',0,0,6.28,9.03,14.24,2.47,5.1)
    B(s,ACC,0,0,8.02,2.42,6.32,.97);hip('Monitor and crest',0,0,9.02,3.28,7.21,.98,4.02)
    for a in (-1,1):
        with frame(a*1.21,0,a*90):
            for j in range(5):B(s,TIM,0,-.04,8.19+j*.136,6.19,.09,.072)
    B(s,TIM,0,y-.35,g,8.51,1.43,.19,.025);B(s,SEC,0,y-.99,g+.19,8.51,.16,.31)
    for j in range(19):
        x=(j-9)*.44;prism(s,SNOW,[(x-.15,g+.46),(x,g+.26),(x+.15,g+.46)],y-1.09,y-1.02)
    for x in (-3.86,-1.32,1.32,3.86):
        piers(s,ACC,x,y-.90,g+.5,.20,1.84)
        for a in (-1,1):beam(s,TIM,(x,y-.9,g+1.92),(x+a*.37,y-.9,g+2.32),.105)
    for j in range(3):fence(s,[-2.58,0,2.58][j],y-.90,g+.49,2.35,.70,TIM)
    for x in (-2.52,0,2.52):shutter(x,y,g+.49,1.75,1.72,ACC)
    with frame(0,y-.10,90):gable('Balcony sunshade',0,0,g+2.39,2.51,8.91,.58)
    # Stacked profiles make the kettles and lamps recognizable, down to the flared rims.
    for x in (-1.91,1.91): B(s,TIM,x,y-.98,3.20,.09,.09,.27)
    B(s,ACC,0,y-.98,2.63,4.92,.15,.63,.025);label('KEDAI   TEMBAGA',0,y-1.065,2.95,4.45,.34,SUN)
    door(-2.52,y+1.94,.22,1.27,2.46);B(s,DARK,.91,y+1.92,.67,4.14,.14,2.10)
    for lev in range(2):
        h=.65+lev*.95;B(s,TIM,1.0,y+1.51,h,4.16,.81,.13,.02)
        for j in range(5):vessel('Hammered wares',-.58+.77*j,y+1.42,h+.13,.62+.06*((lev+j)%3),BRASS)
    for x in (-2.45,2.45):pendant('Arcade lamps',x,y+.39,2.38)
    B(s,TIM,2.67,y+.24,.22,1.12,.89,.37,.035);vessel('Show urn',2.67,y+.24,.59,1.13,BRASS)
    for a in (-1,1):
        with frame(a*w/2,0,a*90):planks(s,0,0,g+.3,d,2.43)


if __name__ == "__main__":
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, SIZE)
    index_preview(OUT / "preview.png")
