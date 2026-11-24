"""sgmy-car-seletar-belt-loader — original procedural SG/MY vehicle, no external inputs or brand marks.
Rebuild: blender -b --factory-startup --python-exit-code 1 --python build.py
Append -- --export-only to omit the studio preview. Static, metric, UV-mapped,
material-batched; nose -Y in Blender, +Z in glTF. Requires a Draco decoder.
"""
# Geometry and studio helpers adapted from previous gallery vehicles.
import math
import sys
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector
TAU = math.tau
ART = []
MAT = {}
TRUCK_SECTION = [(.89,0),(.98,.08),(1,.24),(1,.83),(.983,.95),(.963,1)]
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0


def rgb(value):
    v = [int(value[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c < .04045 else ((c + .055) / 1.055) ** 2.4 for c in v)


def material(key, name, color, rough=.42, metal=0, alpha=1, emission=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    rgba = (*rgb(color), alpha)
    m.diffuse_color = rgba
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = rgba
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    p.inputs['Alpha'].default_value = alpha
    if emission:
        p.inputs['Emission Color'].default_value = (*rgb(color), 1)
        p.inputs['Emission Strength'].default_value = emission
    if alpha < 1:
        m.surface_render_method = 'BLENDED'
    MAT[key] = m
    return m


def standard():
    material('black', 'Graphite trim and seals', '19252D', .42)
    material('tire', 'Soft carbon rubber', '242831', .79)
    material('metal', 'Satin aluminium', 'BBCAD3', .32, .56)
    material('glass', 'Smoked blue glazing', '5582A1', .22, .07, .38)
    material('seat', 'Slate woven upholstery', '45586B', .75)
    material('ivory', 'Ivory sign enamel', 'F2F5EC', .39)
    material('lamp', 'Ice-white lamp optics', 'DAF4FF', .23, .12, emission=.27)
    material('red', 'Vermilion lens', 'DA362B', .23, emission=.10)
    material('amber', 'Amber lens and marker', 'F1A329', .32, emission=.14)


def register(obj, name, key):
    obj.name = name
    obj.data.name = name
    obj.data.materials.append(MAT[key])
    ART.append(obj)
    return obj


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def mesh(name, vertices, faces, key, recalc=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    if recalc:
        bm = bmesh.new()
        bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(data)
        bm.free()
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    return register(obj, name, key)


def bevel(obj, radius, segments=2):
    if radius:
        mod = obj.modifiers.new('Formed edge radii', 'BEVEL')
        mod.width = radius
        mod.segments = segments
        mod.harden_normals = True
        normal = obj.modifiers.new('Area-weighted corner normals', 'WEIGHTED_NORMAL')
        normal.keep_sharp = True
    return obj


def box(name, key, loc, dim, radius=0, segments=2, tilt=None):
    x, y, z = (n/2 for n in dim)
    v = [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),
         (-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    obj = mesh(name, v, [(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)], key)
    obj.location = loc
    if tilt:
        obj.rotation_euler = tilt
    # Leave a flat area on the smallest face instead of collapsing bevels together.
    return bevel(obj, min(radius, .42*min(dim)), segments)


def rod(name, key, a, b, rad, sides=12):
    """Cylinder between two explicit attachment points."""
    a, b = Vector(a), Vector(b)
    d = b-a
    q = d.to_track_quat('Z', 'Y')
    ring = [q @ Vector((rad*math.cos(i*TAU/sides), rad*math.sin(i*TAU/sides), 0)) for i in range(sides)]
    v = [a+p for p in ring] + [b+p for p in ring]
    f = [tuple(reversed(range(sides))), tuple(range(sides, sides*2))]
    f.extend((i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides))
    obj = mesh(name, v, f, key)
    for p in list(obj.data.polygons)[2:]:
        p.use_smooth = True
    return obj


def line(name, key, points, rad=.01, sides=8):
    for a, b in zip(points, points[1:]):
        rod(name, key, a, b, rad, sides)


def face(name, key, points, normal):
    vertices = [Vector(p) for p in points]
    n = (vertices[1]-vertices[0]).cross(vertices[-1]-vertices[0])
    if n.dot(Vector(normal)) < 0:
        vertices.reverse()
    return mesh(name, vertices, [tuple(range(len(vertices)))], key)


def body_loft(name, key, stations, section=None):
    """Stations are (Y, min Z, max Z, half width); exterior runs nose to tail."""
    if section is None:
        section = [(.82,0),(.95,.045),(1,.17),(1,.70),(.992,.83),(.948,.95),(.85,1)]
    section = section + [(-x,z) for x,z in reversed(section)]
    v = [(x*w,y,b+(t-b)*z) for y,b,t,w in stations for x,z in section]
    n = len(section)
    f = [tuple(reversed(range(n)))]
    for a in range(0, len(v)-n, n):
        f += [(a+i,a+(i+1)%n,a+(i+1)%n+n,a+i+n) for i in range(n)]
    f += [tuple(range(len(v)-n, len(v)))]
    obj = mesh(name, v, f, key, recalc=True)
    return obj


def wells(body, axles, tire_r, cut_r, width, depth):
    # The wheel centre is lower than the upper pocket radius. Remove the sill below each arch.
    wheel_openings_at(body, axles, tire_r, cut_r, width-depth, width+.22)


def wheel_openings_at(body, axles, center, radius, inner, outer):
    for y in axles:
        for s in (-1,1):
            cut = rod('Wheel well cutter', 'black', (s*inner,y,center), (s*outer,y,center), radius, 32)
            activate(body)
            mod = body.modifiers.new('Open fender well', 'BOOLEAN')
            mod.operation = 'DIFFERENCE'
            mod.material_mode = 'TRANSFER'
            mod.object = cut
            bpy.ops.object.modifier_apply(modifier=mod.name)
            ART.remove(cut)
            bpy.data.objects.remove(cut, do_unlink=True)


def lathe(name, key, x, y, z, profile, n=32):
    """Lathe a closed cross-section around the lateral (X) axle."""
    v = [(x+a,y+r*math.cos(i*TAU/n),z+r*math.sin(i*TAU/n)) for a,r in profile for i in range(n)]
    f = [(j*n+i,j*n+(i+1)%n,((j+1)%len(profile))*n+(i+1)%n,((j+1)%len(profile))*n+i)
         for j in range(len(profile)) for i in range(n)]
    obj = mesh(name,v,f,key,recalc=True)
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def wheel(y, x, r, width, s, style='steel'):
    """Outer face points toward side s. Ground contact is Z=0."""
    a = width/2
    rim = r*(.61 if style != 'lorry' else .54)
    lathe('Rounded tyre', 'tire', x,y,r,
          [(-a*.65,r), (a*.65,r), (a*.90,r*.977), (a,r*.91), (a,rim),
           (-a,rim),(-a,r*.91),(-a*.90,r*.977)])
    lip = x+s*a
    rod('Brake drum shadow', 'black', (x-s*a*.82,y,r),(lip-s*.021,y,r),rim*.99,24)
    lathe('Rolled rim flange', 'metal', lip,y,r,
          [(s*p,q*rim) for p,q in [(-.025,.91),(-.019,1),(-.001,1.014),(.008,.96),(.006,.89),(-.017,.87)]], 24)
    if style in ('alloy', 'bike'):
        for i in range(5):
            a0 = TAU*i/5
            v = [(lip+s*xx,y+rr*math.cos(a0+ang),r+rr*math.sin(a0+ang)) for xx,rr,ang in
                 [(-.003,rim*.21,-.36),(-.007,rim*.92,-.13),(-.007,rim*.92,.16),(-.003,rim*.21,.40)]]
            face('Tapered alloy spoke','metal',v,(s,0,0))
        hub = .26
    else:
        hub = .66 if style == 'steel' else .49
        rod('Pressed steel dish','metal',(lip-s*.027,y,r),(lip-s*.017,y,r),rim*.90,24)
        for i in range(8):
            t = TAU*i/8
            yy,zz = y+rim*.72*math.cos(t),r+rim*.72*math.sin(t)
            rod('Vent pocket','black',(lip-s*.017,yy,zz),(lip-s*.013,yy,zz),rim*.095,8)
    rod('Axle cap','metal',(lip-s*.024,y,r),(lip+s*.011,y,r),rim*hub,16)
    for i in range(5):
        t = TAU*i/5
        yy,zz = y+rim*.405*math.cos(t),r+rim*.405*math.sin(t)
        if style not in ('alloy','bike'):
            rod('Lug recess','black',(lip+s*.010,yy,zz),(lip+s*.014,yy,zz),rim*.036,6)


def sign(name, words, key, loc, height, max_width, normal):
    """Use Blender's built-in Bfont. No external fonts or textures are needed."""
    data = bpy.data.curves.new(name,'FONT')
    data.body = words
    data.align_x = 'CENTER'
    data.align_y = 'CENTER'
    data.resolution_u = 2
    data.size = 1
    obj = bpy.data.objects.new(name,data)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    width, h = obj.dimensions.x, obj.dimensions.y
    scale = min(height/max(h, .001), max_width/max(width, .001))
    obj.scale = (scale, scale, scale)
    n, u = Vector(normal).normalized(), Vector((0,0,1))
    h_axis = u.cross(n).normalized()
    obj.rotation_euler = Matrix((h_axis,n.cross(h_axis),n)).transposed().to_euler()
    obj.location = loc
    register(obj,name,key)
    return obj


def chair(x,y,z,w=.42,h=.48):
    box('Seat cushion','seat',(x,y,z),(w,.41,.104),.042)
    box('Seat back','seat',(x,y+.18,z+h*.49),(w,.118,h),.044,tilt=(.10,0,0))
    box('Head restraint','seat',(x,y+.184+h*.04,z+h*1.09),(w*.56,.121,h*.29),.038)


def steer(x,y,z,r=.145):
    """True vehicle right is negative X when facing negative Y."""
    u, v = Vector((1,0,0)), Vector((0,-.54,.842)).normalized()
    n = u.cross(v).normalized()
    center = Vector((x,y,z))
    vertices = []
    steps, ring = 22, 6
    for i in range(steps):
        t = i*TAU/steps
        spoke = u*math.cos(t)+v*math.sin(t)
        for j in range(ring):
            a = j*TAU/ring
            vertices.append(center + spoke*(r+.013*math.cos(a)) + n*(.013*math.sin(a)))
    f = [(i*ring+j,((i+1)%steps)*ring+j,((i+1)%steps)*ring+(j+1)%ring,i*ring+(j+1)%ring)
         for i in range(steps) for j in range(ring)]
    m = mesh('Right-hand steering wheel rim',vertices,f,'black',recalc=True)
    for p in m.data.polygons:
        p.use_smooth=True
    rod('Right-hand steering column','black',center-n*.034,center+n*.18,r*.19)
    for t in (0,math.pi,1.5*math.pi):
        rod('Steering spoke','black',center,center+r*(u*math.cos(t)+v*math.sin(t)),.016,8)


def consolidate(name):
    """Static material batching: one node at the ground datum, no studio geometry."""
    bpy.ops.object.select_all(action='DESELECT')
    for obj in ART:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = ART[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    obj = bpy.context.object
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.name = obj.data.name = name
    # Every primitive gets a unique unwrap, including sign lettering and wheel wells.
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(island_margin=.0005)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.data.uv_layers.active.name = 'UVMap'
    obj['length_unit'] = 'metre'
    obj['facing'] = '+Z glTF / -Y Blender'
    obj['ground_plane'] = 'Y=0 glTF / Z=0 Blender'
    obj['steering'] = 'Right-hand drive'
    return obj


def studio(length, target, direction, fill):
    scene = bpy.context.scene
    # Neutral seamless backdrop, with broad softbox reflections and contact shadows.
    scene.world = bpy.data.worlds.new('Soft grey studio world')
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get('Background')
    bg.inputs[0].default_value = (.44,.52,.67,1)
    bg.inputs[1].default_value = .29
    material('studio','Backdrop only', '929FAE', .73)
    box('Preview floor','studio',(0,0,-.113),(length*200,length*200,.226))
    def light(name, p, watts, size, temperature, size_y=None):
        data = bpy.data.lights.new(name, 'AREA')
        data.energy = watts*length*length
        data.color = temperature
        if size_y:
            data.shape = 'RECTANGLE'
            data.size_y = size_y*length
        data.size = size*length
        o = bpy.data.objects.new(name,data)
        scene.collection.objects.link(o)
        o.location = Vector(p)*length
        o.rotation_euler = (Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    light('Large warm front softbox',(-.68,-.84,1.36),175,.93,(1,.92,.80),.68)
    light('Long roof strip',(.15,.45,1.10),133,.54,(.84,.93,1),1.15)
    light('Cool broad fill',(.88,-.39,.47),63,.85,(.75,.88,1))
    light('Rear edge',(-.75,.76,.66),84,.74,(1,.95,.84))
    cam = bpy.data.cameras.new('Product camera')
    cam.type = 'ORTHO'
    cam.ortho_scale = fill*length
    camera = bpy.data.objects.new('Product camera',cam)
    scene.collection.objects.link(camera)
    camera.location = Vector(target) + Vector(direction).normalized()*length*2.8
    camera.rotation_euler = (Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    verts = bpy.context.view_layer.objects.active.data.vertices
    axes = camera.rotation_euler.to_matrix()
    xy = [axes.transposed() @ (v.co - Vector(target)) for v in verts]
    lo_x, hi_x = min(v.x for v in xy), max(v.x for v in xy)
    lo_y, hi_y = min(v.y for v in xy), max(v.y for v in xy)
    camera.location += axes @ Vector(((lo_x+hi_x)/2,(lo_y+hi_y)/2,0))
    cam.ortho_scale = max(hi_x-lo_x,(hi_y-lo_y)*780/520)*1.13
    cam.clip_end = length*300
    scene.camera = camera
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 18
    scene.cycles.adaptive_min_samples = 4
    scene.cycles.adaptive_threshold = .10
    scene.cycles.max_bounces = 5
    scene.cycles.use_denoising = True
    scene.cycles.denoising_prefilter = 'ACCURATE'
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 4
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -1.65
    scene.render.resolution_x = 780
    scene.render.resolution_y = 520
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 65
    return scene


def rear_light(y,z,x,w=.24,h=.19, tilt=0):
    for s in (-1,1):
        angle=(0,0,-s*tilt)
        yt = y-math.sin(tilt)*w*.23
        box('Tail light surround','black',(s*x,yt,z),(w,.09,h),min(w,h)*.19,tilt=angle)
        box('Red tail light lens','red',(s*x,yt+.048,z+h*.19),(w*.82,.022,h*.42),.013,tilt=angle)
        box('Amber direction lens','amber',(s*x,yt+.046,z-h*.24),(w*.81,.019,h*.21),.009,tilt=angle)


def head_module(y,z,x,w,h,kind='strip',toe=.10):
    for s in (-1,1):
        angle=(0,-s*.06,s*toe)
        box('Recessed lighting cluster','black',(s*x,y,z),(w,.12,h),min(h*.26,.047),tilt=angle)
        if kind == 'round':
            for i,k in [(-.151,'lamp'),(.155,'amber')]:
                xx=s*(x+w*i)
                yy=y-.065+w*i*toe
                rod('Round projector bezel','metal',(xx,yy+.014,z),(xx,yy-.010,z),h*.343,20)
                rod('Round lamp optic',k,(xx,yy-.008,z),(xx,yy-.017,z),h*.271,20)
        else:
            box('Diffused daytime running optic','lamp',(s*(x-.016),y-.063,z+h*.19),(w*.84,.018,h*.31),.010,tilt=angle)
            box('Low beam reflector','metal',(s*(x-w*.11),y-.063,z-h*.20),(w*.50,.017,h*.24),.008,tilt=angle)
            box('Direction indicator','amber',(s*(x+w*.32),y-.063+w*.32*toe,z-h*.19),(.065,.017,h*.22),.008,tilt=angle)


def palette(paint, trim, deck='B78858', accent='E59F48'):
    standard()
    material('paint','Hull enamel',paint,.38,.12)
    material('trim','Coachwork enamel',trim,.37,.09)
    material('deck','Deck finish',deck,.65)
    material('warm','Signal accent',accent,.38,.08)
    material('bottom','Oxide keel paint','884638',.74)
    material('wood','Oiled hardwood','76503B',.67)
    material('rope','Manila cordage','BAA47A',.87)


def pin(name,key,x,y,z,r,h,n=24):
    return rod(name,key,(x,y,z-h/2),(x,y,z+h/2),r,n)


def ring(name,key,center,normal,r,t,n=32):
    q=Vector(normal).to_track_quat('Z','Y'); c=Vector(center); m=8
    verts=[c+q@Vector(((r+t*math.cos(TAU*j/m))*math.cos(TAU*i/n),(r+t*math.cos(TAU*j/m))*math.sin(TAU*i/n),t*math.sin(TAU*j/m))) for i in range(n) for j in range(m)]
    obj=mesh(name,verts,[(i*m+j,((i+1)%n)*m+j,((i+1)%n)*m+(j+1)%m,i*m+(j+1)%m) for i in range(n) for j in range(m)],key,recalc=True)
    for p in obj.data.polygons:p.use_smooth=True
    return obj


def legend(name,sub,x,y,z,w,h,s,key='ivory',board='paint'):
    box('Signboard',board,(s*x,y,z),(.038,w,h),.017)
    sign('Vessel name',name,key,(s*(x+.021),y,z+h*.11),h*.41,w*.9,(s,0,0))
    sign('Service and home port',sub,key,(s*(x+.021),y,z-h*.28),h*.17,w*.88,(s,0,0))


def arm(name,key,a,b,w,h):
    a,b=Vector(a),Vector(b);o=box(name,key,(a+b)*.5,(w,h,(b-a).length),min(w,h)*.095);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o


def connect(name,key,p,q,w,t):
    """Rectangular stringer, with its width axis across the vehicle."""
    a,b=Vector(p),Vector(q); d=b-a
    o=box(name,key,(a+b)*.5,(w,d.length,t),min(w,t)*.13)
    o.rotation_euler=d.to_track_quat('Y','Z').to_euler()
    return o


def spin(name,key,x,y,profile,n=40):
    """Turn a closed vertical profile. Profile runs from base to crown."""
    v=[(x+r*math.cos(TAU*i/n),y+r*math.sin(TAU*i/n),z) for r,z in profile for i in range(n)]
    f=[tuple(reversed(range(n))),tuple(range(len(v)-n,len(v)))]+[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(profile)-1) for i in range(n)]
    o=mesh(name,v,f,key,recalc=True)
    for p in list(o.data.polygons)[2:]:p.use_smooth=True
    return o


def beacon(x,y,z):
    pin('Beacon socket','black',x,y,z+.026,.087,.052)
    spin('Amber warning beacon','amber',x,y,[(.074,z+.049),(.074,z+.129),(.062,z+.148),(.041,z+.154)],20)


def compact_png(path):
    """Size-capped RGB PNG using only Blender's bundled NumPy and the standard library."""
    import struct, zlib
    import numpy as np
    raw=path.read_bytes()
    if len(raw)<=250000:return
    chunks=[]; i=8
    while i<len(raw):
        n,tag=struct.unpack('>I4s',raw[i:i+8]); data=raw[i+8:i+8+n]; i+=12+n
        if tag==b'IHDR':w,h,depth,mode,_,_,interlace=struct.unpack('>IIBBBBB',data)
        if tag==b'IDAT':chunks.append(data)
    assert (depth,mode,interlace)==(8,2,0)
    scan=np.frombuffer(zlib.decompress(b''.join(chunks)),dtype=np.uint8).reshape(h,1+w*3)
    px=np.zeros((h,w*3),dtype=np.uint8)
    for y,row in enumerate(scan):
        ft=int(row[0]); a=row[1:].astype(int).tolist(); b=px[y-1].astype(int).tolist() if y else [0]*len(a)
        if ft==2:px[y]=row[1:]+px[y-1];continue
        for x in range(len(a)):
            l=a[x-3] if x>=3 else 0; u=b[x]; ul=b[x-3] if x>=3 else 0
            if ft==1:p=l
            elif ft==3:p=(l+u)//2
            elif ft==4:
                t=l+u-ul; d,e,f=abs(t-l),abs(t-u),abs(t-ul);p=l if d<=e and d<=f else u if e<=f else ul
            else:p=0
            a[x]=(a[x]+p)&255
        px[y]=a
    # Keep RGB instead of palette mapping: a few low bits cost little visually,
    # while preserving the studio gradient and saturated small markings.
    def chunk(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    rgb=px.reshape(h,w,3).astype(np.int16)
    for step in (2,3,4,5,6,8,10):
        c=np.clip((rgb+step//2)//step*step,0,255).astype(np.uint8)
        rows=c.reshape(h,-1);left=np.zeros_like(c);left[:,1:]=c[:,:-1];left=left.reshape(h,-1)
        above=np.zeros_like(rows);above[1:]=rows[:-1]
        diffs=np.stack([rows-left,rows-above]);scores=np.abs(diffs.view(np.int8).astype(np.int16)).sum(axis=2);filt=scores.argmin(axis=0)
        data=b''.join(bytes([1+int(i)])+diffs[i,y].tobytes() for y,i in enumerate(filt))
        png=raw[:8]+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(data,9))+chunk(b'IEND',b'')
        if len(png)<=250000:path.write_bytes(png);return
    raise RuntimeError('Studio PNG over budget')


def deliver(title,length,view,control):
    out=Path(__file__).resolve().parent
    obj=consolidate(title)
    obj['steering']=control
    obj['origin_note']='Base centre; +Z forward in glTF, metres.'
    obj['asset_id']=ASSET_ID
    obj['role']='Static SG/MY game vehicle'
    result=bpy.ops.export_scene.gltf(filepath=str(out/'model.glb'),export_format='GLB',use_selection=True,export_texcoords=True,export_normals=True,export_animations=False,export_extras=True,export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=7,export_draco_position_quantization=20,export_draco_texcoord_quantization=14)
    assert result=={'FINISHED'}
    if '--export-only' not in sys.argv:
        preview=out/'preview.png';studio(length,(0,0,length*.2),view,1.13).render.filepath=str(preview);bpy.ops.render.render(write_still=True);compact_png(preview)


ASSET_ID = 'sgmy-car-seletar-belt-loader'


def build():
    reset();palette('D1B247','275D68','697E84','EF7B48')
    for y,r in ((-1.48,.34),(1.47,.36)):
        rod('Axle','black',(-.74,y,r),(.74,y,r),.079)
        for s in (-1,1):wheel(y,s*.76,r,.235,s)
    p=[(-2.29,.34,.73,.72),(-2.13,.31,.89,.89),(1.90,.31,.94,.92),(2.24,.36,.87,.84)]
    body=body_loft('Apron tractor tub','paint',p,TRUCK_SECTION);wells(body,(-1.48,1.47),.35,.415,.94,.41)
    box('Power pack bonnet','trim',(.33,.62,.985),(1.05,1.60,.24),.075)
    for y in [.16+i*.124 for i in range(9)]:box('Engine inlet vane','black',(.34,y,1.107),(.68,.046,.018),.006)
    head_module(-2.24,.60,.65,.30,.158,'round',.04);rear_light(2.20,.60,.67,.22,.15)
    chair(-.54,-.30,.99,.42,.45);box('Right driving console','trim',(-.55,-1.19,1.07),(.58,.39,.48),.06);steer(-.55,-.96,1.36,.16)
    for x in (-.85,-.21):
        for y in (-1.15,.17):rod('Driver canopy upright','trim',(x,y,.89),(x,y+.07,1.99),.029)
    box('Driver weather shade','ivory',(-.53,-.42,2.03),(.84,1.65,.11),.048);beacon(-.52,.16,2.081)
    for s in (-1,1):
        legend('BAGASI   12','SELETAR   /   RAMP',.923,.32,.69,1.57,.34,s,'ivory','trim')
        box('Impact block','black',(s*.78,2.19,.58),(.24,.14,.18),.031)
    # Belt traverses the entire chassis beside the low, offset cab.
    a,b=Vector((.31,-3.94,2.62)),Vector((.31,3.50,.74));d=(b-a).normalized();up=Vector((0,-d.z,d.y));side=Vector((1,0,0))
    connect('Continuous luggage belt','black',a,b,.90,.095)
    for j in range(39):
        p=a.lerp(b,(j+.5)/39)+up*.056;rod('Textured belt flight','seat',p-side*.422,p+side*.422,.010,8)
    for j in (0,1):
        p=a.lerp(b,j);rod('End roller','metal',p-side*.54,p+side*.54,.095,20)
        for s in (-1,1):rod('Non-marking buffer','black',p+s*side*.50,p+s*side*.59,.123,20)
    for s in (-1,1):
        shift=s*side*.505;connect('Conveyor box girder','trim',a+shift-up*.077,b+shift-up*.077,.12,.19)
        posts=[a.lerp(b,t)+shift for t in (.05,.19,.34,.48)]
        for p in posts:rod('Safety rail stanchion','metal',p,p+up*.47,.022)
        line('Belt safety rail','warm',[posts[0]+up*.05,posts[0]+up*.47,posts[-1]+up*.47,posts[-1]+up*.05],.030)
        base=Vector((.31,.87,1.03))+shift;top=a.lerp(b,.32)+shift-up*.14
        arm('Elevating linkage','paint',base,top,.12,.17)
        low=Vector((.31,-.86,.95))+shift;rod('Elevator ram','trim',low,low.lerp(top,.69),.072);rod('Chrome piston','metal',low.lerp(top,.65),top,.044)
    deliver('Seletar Apron Baggage Belt Loader',7.65,(-1,-.43,.49),'Offset right-hand driving station')


if __name__ == "__main__":
    build()
