"""Ipoh compact tracked excavator with offset boom, double-acting rams and a trenching bucket.

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


def rounded(points, factor=.10):
    """Three samples along each quadratic corner for low-poly panel reveals."""
    p = [Vector(v) for v in points]
    out = []
    for i, b in enumerate(p):
        a, c = b.lerp(p[i-1], factor), b.lerp(p[(i+1)%len(p)], factor)
        out.extend([a, a*.25 + b*.50 + c*.25, c])
    return out


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


def glazed(name, points, normal, inset=.09, tint='glass', frame='black'):
    """Make a physical border around a surface pane without overlaid coplanar faces."""
    p = [Vector(v) for v in points]
    n = (p[1]-p[0]).cross(p[-1]-p[0])
    if n.dot(Vector(normal)) < 0:
        p.reverse()
    center = sum(p, Vector())/len(p)
    inner = [q.lerp(center,inset) for q in p]
    b = rounded(inner,.07)
    m = len(b)
    # The outer ring reaches the pillar edges, so inset corners don't open holes into the cabin.
    a = [q for q in p for _ in range(3)]
    v = a+b
    f = []
    for i in range(m):
        j = (i+1)%m
        if (a[i]-a[j]).length < 1e-8:
            f.append((i,m+j,m+i))
        else:
            f.append((i,j,m+j,m+i))
    # Weld coincident seam vertices and keep the glass immediately inside its frame.
    o = mesh(name+' seal',v,f,frame)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bm.to_mesh(o.data)
    bm.free()
    face(name,tint,b,normal)


def shell(stations, panel_keys, front_inset=.08, rear_inset=.15, paint='paint', side_tint='glass'):
    """A greenhouse of planar strips. Stations: (belt Y,Z,X, roof Y,Z,X)."""
    def ends(row, s):
        y,z,x,Y,Z,X = row
        return Vector((s*x,y,z)),Vector((s*X,Y,Z))
    for s in (-1,1):
        for i, key in enumerate(panel_keys):
            a,d = ends(stations[i],s)
            b,c = ends(stations[i+1],s)
            if key is None:
                # A quad with slight twist is triangulated by the exporter.
                face('Pillar or quarter panel',paint,[a,b,c,d],(s,0,0))
            else:
                glazed('Side window',[a,b,c,d],(s,0,0),key,tint=side_tint)
    for row,d,amt in [(stations[0],-1,front_inset),(stations[-1],1,rear_inset)]:
        a,b = ends(row,-1)
        c,e = ends(row,1)
        p = [a,c,e,b]
        if amt:
            glazed('Front windscreen' if d<0 else 'Rear screen',p,(0,d,0),amt)
        else:
            face('Solid aft bulkhead',paint,p,(0,d,0))


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


def mirror(x,y,z,s,size=.21, upright=False):
    dz = size*(.72 if not upright else 1.38)
    rod('Mirror stalk','black',(x-s*size*.42,y+.032,z-.05),(x,y,z),size*.090)
    box('Mirror housing','black',(x,y,z),(size,.12,dz),min(dz,.12)*.33)
    box('Silver mirror lens','metal',(x,y+.056,z),(size*.83,.012,dz*.79),.013)


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


def cap(name,key,rows,sections=None):
    p = [(Y,Z-.009,Z+.04,X+.010) for _,_,_,Y,Z,X in rows]
    p = [(p[0][0]-.045,p[0][1]+.002,p[0][2]-.01,p[0][3]-.014)] + p + [
        (p[-1][0]+.04,p[-1][1]+.005,p[-1][2]-.008,p[-1][3]-.013)]
    return body_loft(name,key,p,sections)


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


def equipment_cab(x,y,base,width,length,height):
    """Cab with offset station, framed glazing, rain cap and two control levers."""
    w=width/2; f=y-length*.5; b=y+length*.5; z=base+.27; t=base+height
    rows=[(f,z,w,f+.17,t-.06,w-.04),(f+.10,z,w,f+.26,t-.035,w-.04),
          (b-.16,z,w,b-.17,t,w-.04),(b,z,w,b-.035,t-.025,w-.04)]
    start=len(ART)
    box('Cab plinth','second',(0,y,base+.137),(width,length,.29),.06)
    shell(rows,[None,.10,None],front_inset=.093,rear_inset=.14)
    cap('Overhanging rain visor','paint',rows)
    chair(-w*.17,y+.16,z+.19,width*.46,.44)
    steer(-w*.18,f+.35,z+.48,.125)
    for s in (-1,1):
        rod('Control stalk','black',(s*w*.72,y+.02,z+.05),(s*w*.72,y-.10,z+.31),.017)
        rod('Lever grip','seat',(s*w*.72,y-.10,z+.29),(s*w*.72,y-.13,z+.37),.027)
        mirror(s*(w+.065),f+.15,t-.22,s,.135)
    line('Windscreen wiper','black',[(-w*.82,f+.015,z+.12),(w*.2,f+.052,z+.39)],.011)
    for o in ART[start:]:o.location.x+=x


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


def bucket(x,width,outline,inner,edge_y,edge_z,direction=-1):
    """Bent scoop with a constant-thickness open mouth and separate cheek plates."""
    yz('Pressed scoop back','seat',x,width,outline+list(reversed(inner)),.009)
    for s in (-1,1):yz('Bucket end plate','seat',x+s*width*.497,.046,outline,.012)
    for i in range(6):
        yz('Replaceable tooth','metal',x+width*((i+.5)/6-.5),width*.08,[(edge_y-.09*direction,edge_z+.10),(edge_y+.18*direction,edge_z+.018),(edge_y+.16*direction,edge_z-.013),(edge_y-.08*direction,edge_z+.019)],.007)


def pin(x,y,z,width,r):
    shaft('Hardened hinge pin','black',x,y,z,width,r)
    for s in (-1,1):shaft('Hinge pin retainer','metal',x+s*width/2,y,z,.019,r*.68,16)



ASSET_ID = 'sgmy-car-ipoh-compact-excavator'
STATION = 'Right-side glazed operator cab'


def build():
    palette('2B9990','243F50','FFBA49')
    track_pair(.82,-.55,1.09,.343,.40)
    box('Crawler cross frame','seat',(0,.28,.55),(1.51,1.81,.26),.06)
    rod('Slewing ring','black',(0,.27,.65),(0,.27,.88),.73,40)
    body_loft('Upper carriage','second',[(-.87,.86,1.08,.78),(-.67,.80,1.17,.98),(1.28,.80,1.13,.99),(1.65,.88,1.11,.75)])
    body_loft('Rounded counterweight','paint',[(.50,1.06,1.60,.94),(.92,1.03,1.75,.99),(1.34,1.03,1.70,.94),(1.66,1.04,1.44,.69)])
    equipment_cab(-.43,-.02,1.13,1.00,1.54,1.51)
    strobe(-.72,.39,2.65)
    box('Hydraulic pump enclosure','paint',(.56,.06,1.35),(.76,1.29,.47),.073)
    slots(.946,.13,1.38,1,8,.69,.22)
    for s in (-1,1):
        box('Unit nameplate','second',(s*.980,.984,1.43),(.061,.70,.225),.016)
        box('Unit stripe','accent',(s*1.013,.984,1.356),(.012,.57,.024),.005)
        labels(s,1.013,.984,1.459,'IPOH','',.57,.086)
    x=.33
    yz('Gooseneck boom','paint',x,.34,[(-.63,1.00),(-1.83,2.44),(-2.27,2.84),(-3.01,2.62),(-3.14,2.77),(-2.37,3.28),(-2.13,3.29),(-1.72,2.95),(-.46,1.26)],.045)
    yz('Dipper stick','paint',x,.273,[(-3.17,3.06),(-3.02,3.08),(-2.88,2.65),(-3.11,.91),(-3.29,.71),(-3.43,.82),(-3.20,2.58)],.037)
    for s in (-1,1):
        ram((x+s*.254,-.74,1.17),(x+s*.254,-1.82,2.76),.078)
        line('Flexible oil hose','black',[(x+s*.097,-.61,1.24),(x+s*.11,-1.76,2.99),(x+s*.11,-2.16,3.32),(x+s*.11,-2.39,3.30),(x+s*.11,-2.84,3.04)],.019)
    ram((x,-2.18,3.29),(x,-3.12,3.03),.078)
    ram((x,-3.24,2.55),(x,-3.51,1.08),.066)
    yz('Bucket rocker','second',x,.24,[(-3.34,1.28),(-3.58,1.09),(-3.51,.76),(-3.33,.78),(-3.41,1.04),(-3.24,1.17)])
    for y,z,t,r in [(-.61,1.18,.51,.135),(-3.04,2.78,.39,.112),(-3.30,.83,.41,.11),(-3.50,1.08,.32,.074)]:pin(x,y,z,t,r)
    bucket(x,.74,[(-3.59,.93),(-3.77,.68),(-3.73,.31),(-3.50,.14),(-2.99,.16)], [(-3.51,.90),(-3.69,.65),(-3.65,.36),(-3.47,.22),(-2.98,.22)],-2.99,.16,1)
    sign('Boom fleet title','KINTA  06','ivory',(x-.173,-2.32,3.039),.105,.70,(-1,0,0))
    finish('Ipoh Compact Excavator',5.65,(0,-.98,1.56),(-1.35,-.65,.60),1.18)


if __name__ == "__main__":
    reset()
    standard()
    build()
