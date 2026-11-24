"""Seremban crawler paver with open receiving hopper, feeder slats and extended finishing screed.

Original SG/MY static vehicle; no external art, fonts or textures.
Rebuild: blender -b --factory-startup -P build.py (add -- --export-only for GLB only).
Metres; base origin; Blender nose -Y, glTF nose +Z. Vehicle right is -X.
UV-mapped material batches; requires Draco. No animation or collision geometry.
"""

# Shared geometry and studio conventions from round two of the gallery vehicle set.
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
    ground = min(v.co.z for v in obj.data.vertices)
    for v in obj.data.vertices:
        v.co.z -= ground
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
    obj['operator_station'] = STATION
    obj['asset_id'] = ASSET_ID
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
    cam.clip_end = length*300
    scene.camera = camera
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 14
    scene.cycles.adaptive_min_samples = 4
    scene.cycles.adaptive_threshold = .10
    scene.cycles.max_bounces = 5
    scene.cycles.use_denoising = True
    scene.cycles.denoising_prefilter = 'ACCURATE'
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 3
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -1.65
    scene.render.resolution_x = 1120
    scene.render.resolution_y = 760
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 65
    return scene


def finish(name, length, target, direction, fill=1.13):
    out = Path(__file__).resolve().parent
    asset = consolidate(name)
    # Fit the actual silhouette to both image axes, including antennas and implements.
    look = Vector(direction).normalized()
    right = Vector((0,0,1)).cross(look).normalized()
    up = look.cross(right).normalized()
    xs = [v.co.dot(right) for v in asset.data.vertices]
    ys = [v.co.dot(up) for v in asset.data.vertices]
    target = Vector(target)
    target += right*((min(xs)+max(xs))/2-right.dot(target)) + up*((min(ys)+max(ys))/2-up.dot(target))
    fill = 1.12*max(max(xs)-min(xs),(max(ys)-min(ys))*1120/760)/length
    result = bpy.ops.export_scene.gltf(
        filepath=str(out/'model.glb'),export_format='GLB',use_selection=True,
        export_texcoords=True,export_normals=True,export_animations=False,export_extras=True,
        export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=7,
        export_draco_position_quantization=19,export_draco_texcoord_quantization=14)
    if result != {'FINISHED'}:
        raise RuntimeError(f'GLB export failed: {result}')
    options = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    if '--export-only' in options:
        return
    studio(length, target, direction, fill).render.filepath = str(out/'preview.png')
    bpy.ops.render.render(write_still=True)


def labels(s,x,y,z,main,sub,width,height,key='ivory',sub_key=None):
    sign('Side fleet title',main,key,(s*x,y,z),height,width,(s,0,0))
    if sub:
        sign('Side fleet subtitle',sub,sub_key or key,(s*x,y,z-height*1.05),height*.42,width,(s,0,0))


def palette(main, second, accent):
    material('paint','Primary fleet enamel',main,.32,.18)
    material('second','Secondary fleet enamel',second,.35,.14)
    material('accent','Contrasting fleet flash',accent,.34,.10)


def yz(name,key,xc,thick,profile,edge=.012):
    """Extrude a longitudinal silhouette across vehicle width."""
    n=len(profile)
    v=[(x,y,z) for x in (xc-thick/2,xc+thick/2) for y,z in profile]
    f=[tuple(range(n)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return bevel(mesh(name,v,f,key,True),edge,2)


def shaft(name,key,x,y,z,width,r,sides=32):
    return rod(name,key,(x-width/2,y,z),(x+width/2,y,z),r,sides)


def ram(a,b,r):
    a,b=Vector(a),Vector(b)
    mid=a.lerp(b,.55)
    rod('Hydraulic barrel','second',a,mid,r)
    rod('Cylinder gland','black',mid,mid.lerp(b,.07),r*1.06)
    rod('Polished piston','metal',mid,b,r*.60)


def slots(x,y,z,s,count,length,h):
    for i in range(count):
        box('Cooling louvre','black',(s*x,y+(i-(count-1)/2)*length/count,z),(.022,length/count*.46,h),.01,tilt=(-.13,0,0))


def strobe(x,y,z):
    rod('Beacon foot','black',(x,y,z),(x,y,z+.048),.094,20)
    rod('Amber beacon','amber',(x,y,z+.043),(x,y,z+.169),.075,20)
    rod('Beacon lens crown','lamp',(x,y,z+.165),(x,y,z+.171),.06,20)


def track_pair(w,f,b,r,t):
    """Continuous racetrack belt with cast shoes sampled at equal arc distance."""
    z=r+.047; span=b-f; loop=2*span+2*math.pi*r
    def path(d,rad):
        d%=loop
        if d<span:return f+d,z+rad,0
        d-=span
        if d<math.pi*r:
            a=d/r;return b+math.sin(a)*rad,z+math.cos(a)*rad,-a
        d-=math.pi*r
        if d<span:return b-d,z-rad,-math.pi
        a=(d-span)/r;return f-math.sin(a)*rad,z-math.cos(a)*rad,-math.pi-a
    for s in (-1,1):
        x=s*w; verts=[]; n=64
        for i in range(n):
            for side,rad in [(-1,r),(1,r),(1,r-.095),(-1,r-.095)]:
                y,h,_=path(i*loop/n,rad);verts.append((x+side*t*.5,y,h))
        faces=[(4*i+j,4*i+(j+1)%4,4*((i+1)%n)+(j+1)%4,4*((i+1)%n)+j) for i in range(n) for j in range(4)]
        mesh('Continuous track carcass',verts,faces,'tire',True)
        for i in range(40):
            y,h,a=path(i*loop/40,r+.019)
            box('Cast track grouser','black',(x,y,h),(t+.046,loop/40*.78,.056),.010,tilt=(a,0,0))
        for i in range(6):
            y=f+span*i/5; rr=r*.76 if i in (0,5) else r*.46; h=z-r+.094+rr
            shaft('Idler wheel','seat',x,y,h,t*.90,rr,24)
            shaft('Idler cap','metal',x+s*t*.45,y,h,.026,rr*.55,16)
            shaft('Axle boss','black',x+s*(t*.45+.017),y,h,.024,rr*.27,12)
        yz('Track frame','second',x,t*.61,[(f,z+.03),(b,z+.03),(b-.21,z+.17),(f+.16,z+.17)])


def pin(x,y,z,width,r):
    shaft('Hardened hinge pin','black',x,y,z,width,r)
    for s in (-1,1):shaft('Hinge pin retainer','metal',x+s*width/2,y,z,.019,r*.68,16)



ASSET_ID = 'sgmy-car-seremban-asphalt-paver'
STATION = 'Right-side open driving console'


def build():
    palette('496CA1','233B53','FFC854')
    track_pair(.96,-1.17,1.17,.40,.42)
    box('Feeder spine','second',(0,-.18,.79),(1.58,4.09,.36),.054)
    box('Engine cowling','paint',(0,.03,1.29),(2.13,1.72,.90),.10)
    for s in (-1,1):
        slots(1.07,.30,1.32,s,7,.60,.33)
        labels(s,1.075,-.40,1.41,'TURAP','SEREMBAN',.56,.084)
        # Folded hopper wing: three slopes and a rolled steel lip.
        v=[(s*x,y,z) for x,y,z in [(.54,-2.92,.82),(.54,-.88,1.20),(1.10,-.88,1.81),(1.45,-2.63,1.64),(1.28,-2.94,1.43)]]
        liner=face('Receiving hopper wing','seat',v,(0,0,1)); m=liner.modifiers.new('Wing gauge','SOLIDIFY');m.thickness=.055
        line('Painted hopper coaming','accent',v[2:]+[v[0]],.05)
        face('Triangular hopper bulkhead','paint',[(s*.54,-.89,1.16),(s*.54,-.89,1.79),(s*1.10,-.89,1.81)],(0,-1,0))
        ram((s*.76,-1.70,.84),(s*1.24,-2.12,1.46),.074)
        yz('Push roller bearing arm','second',s*.49,.14,[(-3.07,.62),(-2.99,.48),(-2.72,.53),(-1.94,.79),(-2.06,.91),(-2.79,.76)],.019)
        shaft('Push roller spindle','metal',s*.82,-2.96,.61,.72,.061,16)
        rod('Truck push roller','black',(s*.54,-2.96,.61),(s*1.19,-2.96,.61),.139,24)
        yz('Floating screed tow arm','accent',s*1.14,.146,[(.08,.85),(.43,.80),(2.44,.40),(2.41,.60),(.43,1.06),(.08,1.07)],.023)
        pin(s*1.14,.23,.96,.183,.091)
    yz('Hopper conveyor bed','black',0,1.11,[(-2.93,.72),(-.77,1.08),(-.77,1.20),(-2.93,.83)])
    for i in range(12):
        u=i/12;box('Feeder flight','metal',(0,-2.89+1.99*u,.849+.346*u),(1.07,.047,.036),.007)
    box('Operator platform','second',(0,1.35,1.36),(2.22,1.19,.20),.043)
    box('Seat pedestal','paint',(-.62,1.53,1.60),(.36,.33,.38),.025)
    chair(-.62,1.56,1.84,.48,.48)
    box('Console pod','second',(-.62,1.00,1.88),(.48,.32,.67),.03)
    steer(-.62,1.16,2.32,.141)
    for s in (-1,1):
        line('Canopy upright','metal',[(s*.84,1.77,1.44),(s*.84,1.77,2.81),(s*.84,1.49,2.98)],.045)
        line('Platform handrail','accent',[(s*1.03,1.77,1.45),(s*1.03,1.77,2.18),(s*1.03,1.13,2.18),(s*1.03,1.02,2.06)],.030)
    body_loft('Station weather hood','accent',[(.33,2.96,2.99,.96),(.48,2.96,3.06,1.12),(1.87,2.96,3.06,1.12),(2.05,2.96,3.00,.99)])
    strobe(.76,1.61,3.055)
    box('Main screed shoe','seat',(0,2.30,.17),(3.12,.80,.27),.043)
    box('Screed heater housing','paint',(0,2.29,.41),(2.92,.56,.32),.044)
    box('Screed catwalk','black',(0,2.70,.42),(3.04,.27,.09),.017)
    for s in (-1,1):
        ram((s*.83,1.64,1.31),(s*.94,2.28,.51),.071)
        box('Screed wing end gate','second',(s*1.57,2.26,.37),(.085,.91,.57),.026)
        line('Screed grab bar','accent',[(s*1.37,2.37,.56),(s*1.37,2.37,1.05),(s*.87,2.37,1.05),(s*.87,2.37,.56)],.026)
    finish('Seremban Asphalt Paver',5.87,(0,-.12,1.36),(-1.22,-.93,.73),1.27)


if __name__ == "__main__":
    reset()
    standard()
    build()
