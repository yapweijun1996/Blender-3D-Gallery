"""sgmy-car-tuas-yard-scissor-lift — original procedural SG/MY vehicle, no external inputs or brand marks.
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


def face(name, key, points, normal):
    vertices = [Vector(p) for p in points]
    n = (vertices[1]-vertices[0]).cross(vertices[-1]-vertices[0])
    if n.dot(Vector(normal)) < 0:
        vertices.reverse()
    return mesh(name, vertices, [tuple(range(len(vertices)))], key)


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


def compartment(x,y,z,w,h,s,fill='metal'):
    box('Equipment bay rubber reveal','black',(s*x,y,z),(.043,w+.038,h+.038),.020)
    box('Equipment panel',fill,(s*(x+.029),y,z),(.036,w,h),.017)
    box('Equipment bay latch recess','black',(s*(x+.05),y,z-h*.333),(.014,w*.28,.064),.012)
    box('Equipment latch pull','metal',(s*(x+.061),y,z-h*.332),(.013,w*.20,.021),.007)


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


def connect(name,key,p,q,w,t):
    """Rectangular stringer, with its width axis across the vehicle."""
    a,b=Vector(p),Vector(q); d=b-a
    o=box(name,key,(a+b)*.5,(w,d.length,t),min(w,t)*.13)
    o.rotation_euler=d.to_track_quat('Y','Z').to_euler()
    return o


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


ASSET_ID = 'sgmy-car-tuas-yard-scissor-lift'


def build():
    reset();palette('E07740','285D65','66777A','EFBB55')
    for y in (-1.24,1.24):
        for s in (-1,1):
            wheel(y,s*.89,.47,.32,s,'lorry')
            for j in range(24):
                a=TAU*(j+.5)/24;r=.463
                box('Cross-country tyre lug','tire',(s*.89,y+r*math.sin(a),.47+r*math.cos(a)),(.314,.084,.023),.008,tilt=(-a,0,s*.085))
    box('Hydrostatic chassis','trim',(0,0,.72),(1.67,3.46,.66),.09)
    for s in (-1,1):
        compartment(.905,0,.73,1.29,.55,s,'paint')
        for i in range(6):box('Engine air louvre','trim',(s*.981,-.49+i*.113,.82),(.014,.066,.097),.004)
        for y in (-1.71,1.71):
            box('Jack tower','paint',(s*.76,y,.80),(.29,.26,.66),.033);pin('Jack piston','metal',s*.76,y,.43,.069,.29);pin('Stowed footpad','trim',s*.76,y,.27,.177,.073)
    box('Scissor carriage','black',(0,0,1.14),(1.80,3.49,.17),.035)
    # Three linked pantograph stages; inner/outer bars pass on different planes.
    for s in (-1,1):
        for j in range(3):
            z=1.27+j*.81;inner=s*.565;outer=s*.725
            connect('Inner scissor link','trim',(inner,-1.38,z),(inner,1.38,z+.81),.123,.155);connect('Outer scissor link','trim',(outer,-1.38,z+.81),(outer,1.38,z),.125,.155)
            for y,h in ((-1.38,z),(1.38,z),(0,z+.405),(-1.38,z+.81),(1.38,z+.81)):
                rod('Clevis pin','metal',(inner-s*.08,y,h),(outer+s*.093,y,h),.076,18);rod('Yellow bearing cover','warm',(outer+s*.092,y,h),(outer+s*.104,y,h),.044)
        a,b=Vector((s*.44,1.23,1.24)),Vector((s*.44,-.62,2.70));rod('Hydraulic cylinder','paint',a,a.lerp(b,.64),.097);rod('Polished ram','metal',a.lerp(b,.63),b,.058)
    box('Extending work platform','paint',(0,0,3.79),(1.98,3.92,.22),.04);box('Non slip platform floor','deck',(0,0,3.91),(1.90,3.83,.045),.015)
    for s in (-1,1):
        box('Personnel toe board','paint',(s*.946,0,4.02),(.056,3.83,.23),.014)
        for y in (-1.85,-.65,.66,1.85):rod('Guardrail post','paint',(s*.94,y,4.10),(s*.94,y,4.95),.033)
        for z in (4.52,4.95):rod('Platform side rail','paint',(s*.94,-1.85,z),(s*.94,1.85,z),.038)
        legend('KERJA TINGGI','TUAS   /   PLANT 06',.987,0,3.89,1.53,.27,s,'ivory','trim')
    for y in (-1.85,1.85):
        for z in (4.52,4.95):rod('End guardrail','paint',(-.94,y,z),(.94,y,z),.036)
    box('Right-hand drive pendant','trim',(-.64,-1.78,4.81),(.46,.27,.22),.046)
    rod('Travel joystick','black',(-.67,-1.79,4.90),(-.65,-1.77,5.015),.022);pin('Emergency stop','red',-.49,-1.80,4.947,.032,.035)
    for y in (-1.91,):
        for z in (.47,.70,.93,1.16):rod('Lower access rung','metal',(-.25,y,z),(.25,y,z),.027)
        for x in (-.25,.25):rod('Access rail','trim',(x,y,.41),(x,y,1.21),.036)
    deliver('Tuas Rough Terrain Scissor Platform',5.1,(-1,-.69,.45),'Right-hand platform travel controls')


if __name__ == "__main__":
    build()
