"""Kedah Tracked Padi Combine | original SG/MY vehicle | revision 1
A crawler rice harvester for Kedah wet fields, with a bat reel, crop dividers, grain hopper and a stowed unloading auger.
Rebuild: blender -b --factory-startup --python-exit-code 1 --python build.py
Use -- --export-only to skip the Blender studio still (PNG optimization: python3/Pillow).
Metres; base origin; Blender nose -Y, glTF +Z. Right hand controls (-X).
Static UV-mapped material batches; Draco required. No third-party assets or marks.
Geometry and studio helpers adapted from the gallery's SG/MY vehicle series.
"""
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
    cam.clip_end = length*300
    scene.camera = camera
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 20
    scene.cycles.adaptive_min_samples = 4
    scene.cycles.adaptive_threshold = .10
    scene.cycles.max_bounces = 5
    scene.cycles.use_denoising = True
    scene.cycles.denoising_prefilter = 'ACCURATE'
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -1.65
    scene.render.resolution_x = 800
    scene.render.resolution_y = 552
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 65
    return scene


def finish(name, length, target, direction, fill=1.13):
    out = Path(__file__).resolve().parent
    obj = consolidate(name)
    floor_z = min(v.co.z for v in obj.data.vertices)
    obj.data.transform(Matrix.Translation((0,0,-floor_z)))
    obj['asset_id'] = out.name
    obj['origin_note'] = 'Base datum at ground or keel; Blender Z=0'
    obj['source'] = 'Original procedural SG/MY vehicle, revision 1'
    # Fit the actual silhouette rather than the axis-aligned box.
    view = Vector(direction).to_track_quat('Z', 'Y')
    right, up = view @ Vector((1,0,0)), view @ Vector((0,1,0))
    extents = [[v.co.dot(axis) for v in obj.data.vertices] for axis in (right,up)]
    (lx,hx),(ly,hy) = [(min(e),max(e)) for e in extents]
    target = right*((lx+hx)*.5) + up*((ly+hy)*.5)
    fill = max(hx-lx,(hy-ly)*800/552)*1.12/length
    result = bpy.ops.export_scene.gltf(
        filepath=str(out/'model.glb'),export_format='GLB',use_selection=True,
        export_texcoords=True,export_normals=True,export_animations=False,export_extras=True,
        export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=7,
        export_draco_position_quantization=20,export_draco_texcoord_quantization=14)
    if result != {'FINISHED'}:
        raise RuntimeError(f'GLB export failed: {result}')
    options = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    if '--export-only' in options:
        return
    studio(length, target, direction, fill).render.filepath = str(out/'preview.png')
    bpy.ops.render.render(write_still=True)
    # Quantize only the gallery still, not the model. Pillow can live outside Blender.
    path = str(out/'preview.png')
    if (out/'preview.png').stat().st_size > 250000:
        import subprocess
        subprocess.run(['python3', '-c', """
from PIL import Image
from pathlib import Path
import sys
p=Path(sys.argv[1]); im=Image.open(p).convert('RGB')
for width,step in [(800,2),(760,2),(720,2),(720,3),(680,4),(640,5)]:
    small=im.resize((width,round(width*im.height/im.width)),Image.Resampling.LANCZOS)
    small.point([min(255,round(i/step)*step) for i in range(256)]*3).save(p,optimize=True)
    if p.stat().st_size <= 250000: break
else:
    small.quantize(256).save(p,optimize=True)
""",path],check=True)
    assert (out/'preview.png').stat().st_size <= 250000


CAR_SECTION = [(.84,0),(.96,.07),(1,.22),(1,.70),(.986,.86),(.947,.97),(.904,1)]


def labels(s,x,y,z,main,sub,width,height,key='ivory',sub_key=None):
    sign('Side fleet title',main,key,(s*x,y,z),height,width,(s,0,0))
    if sub:
        sign('Side fleet subtitle',sub,sub_key or key,(s*x,y,z-height*1.05),height*.42,width,(s,0,0))


TRUCK_SECTION=[(.89,0),(.98,.08),(1,.24),(1,.83),(.983,.95),(.963,1)]


def beam(name,key,a,b,width,depth=None):
    d=Vector(b)-Vector(a)
    obj=box(name,key,(Vector(a)+Vector(b))*.5,(width,depth or width,d.length),min(width*.12,.028))
    obj.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    return obj


def side_plate(name,key,outline,x0,x1,r=.018):
    n=len(outline)
    v=[(x,y,z) for x in (x0,x1) for y,z in outline]
    f=[tuple(range(n)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return bevel(mesh(name,v,f,key,recalc=True),r)


def colors(**kwargs):
    standard()
    for name,(label,color) in kwargs.items():
        material(name,label,color,.38,.12)


def machine_cab(x,y,z,w,l,h):
    """Rubber-mounted enclosed operator station with a raked front and rain visor."""
    box('Platform sill','paint',(x,y,z+.08),(w,l,.16),.055)
    for s in (-1,1):
        p=[(x+s*w*.50,y-l*.50,z+.145),(x+s*w*.5,y+l*.50,z+.145),
           (x+s*w*.45,y+l*.47,z+h),(x+s*w*.45,y-l*.36,z+h)]
        glazed('Operator door glass',p,(s,0,0),.115)
        beam('Sliding window divider','black',Vector(p[0]).lerp(Vector(p[1]),.70),Vector(p[3]).lerp(Vector(p[2]),.70),.038)
        box('Operator door pull','metal',(x+s*(w*.50+.014),y+l*.34,z+.37),(.04,.13,.042),.015)
    for d,b,t in [(-1,-.50,-.36),(1,.50,.47)]:
        glazed('Cab windshield',[(x+s*w*f,y+l*v,z+u) for s,f,v,u in [(-1,.50,b,.145),(1,.50,b,.145),(1,.45,t,h),(-1,.45,t,h)]],(0,d,0),.09)
    box('Overhanging weather cap','paint',(x,y+.015*l,z+h+.045),(w+.10,l*.94,.13),.052)
    chair(x-.12*w,y+.10*l,z+.32,.45,h*.43)
    box('Operator binnacle','black',(x,y-.30*l,z+.47),(w*.84,.22,.17),.04)
    steer(x-.19*w,y-.18*l,z+.58,.14)
    for s in (-1,1):
        box('Work light bezel','black',(x+s*w*.34,y-l*.45,z+h+.026),(.19,.11,.108),.024)
        box('LED work light','lamp',(x+s*w*.34,y-l*.45-.058,z+h+.03),(.145,.014,.068),.006)


def build():
    colors(paint=('Harvest ivory enamel','EFE3C0'),redcoat=('Persimmon header enamel','C64D34'),tank=('Padi gold hopper','C6963D'),slate=('Dark machinery frame','3D4D4E'))
    # Closed, hollow endless tracks with pads around two large end wheels.
    for s in (-1,1):
        x=s*.97; r=.447; path=[]
        for y,phase in [(1.90,0),(-.96,math.pi)]:
            for j in range(15):
                a=phase+math.pi*j/14
                path.append((y+r*math.sin(a),.46+r*math.cos(a),math.sin(a),math.cos(a)))
        v=[(x+s*dx,y+offset*ny,z+offset*nz) for y,z,ny,nz in path for dx,offset in [(-.231,0),(.231,0),(.231,-.100),(-.231,-.100)]]
        f=[(i*4+k,((i+1)%len(path))*4+k,((i+1)%len(path))*4+(k+1)%4,i*4+(k+1)%4) for i in range(len(path)) for k in range(4)]
        mesh('Endless rubber crawler belt',v,f,'tire',True)
        for j in range(7):
            y=-.96+2.86*j/6; rr=.333 if j in (0,6) else .242; z=.46 if j in (0,6) else .34
            rod('Track bogie roller','slate',(x-.215,y,z),(x+.215,y,z),rr,24)
            rod('Pressed bogie hub','tank',(x+s*.213,y,z),(x+s*.241,y,z),rr*.65,18)
            rod('Hub cap','black',(x+s*.237,y,z),(x+s*.248,y,z),rr*.22,12)
        for j in range(19):
            for z in (.014,.908): box('Rice field traction cleat','black',(x,-.95+j*.158,z),(.49,.072,.028),.006)
        for j,(y,z,ny,nz) in enumerate(path):
            if j%2: box('End shoe','black',(x,y,z),(.49,.08,.03),.006,tilt=(-math.atan2(ny,nz),0,0))
    box('Crawler underframe','slate',(0,.44,.82),(1.92,3.49,.34),.083)
    body_loft('Separator housing','paint',[(-1.44,.96,1.86,.79),(-1.28,.93,2.12,1.07),(1.99,.93,2.15,1.11),(2.51,1.10,1.98,.99)])
    body_loft('Grain bin','tank',[(-.12,1.99,2.67,.86),(.18,1.98,2.93,1.13),(2.04,1.98,2.90,1.08),(2.31,2.00,2.67,.93)],[(.73,0),(1,.71),(1,.96),(.94,1)])
    box('Split grain tank lid','paint',(0,1.08,2.904),(1.97,1.78,.075),.031)
    box('Lid seam','slate',(0,1.08,2.941),(.03,1.74,.012),.004)
    machine_cab(-.46,-.97,1.65,1.26,1.37,1.39)
    for s in (-1,1):
        box('Separator inspection hatch','redcoat',(s*1.102,1.20,1.55),(.052,1.99,.68),.025)
        for j in range(9): box('Separator ventilation slot','slate',(s*1.133,.47+j*.18,1.57),(.015,.067,.35),.006,tilt=(.19,0,0))
        box('Grain hopper nameboard','tank',(s*1.127,.98,2.60),(.036,1.71,.41),.016)
        labels(s,1.150,.98,2.648,'PADI  09','JELAPANG  /  KEDAH',1.49,.177,'slate')
    rod('Folding grain discharge tube','paint',(.82,-.12,2.26),(.97,2.76,2.84),.147,24)
    rod('Angled grain sock','slate',(.97,2.75,2.84),(.98,3.02,2.56),.177,20)
    box('Elevator throat','slate',(0,-1.69,1.05),(1.25,1.68,.44),.065,tilt=(.30,0,0))
    box('Header collection pan','redcoat',(0,-2.65,.68),(3.83,1.16,.17),.049)
    box('Header back sheet','redcoat',(0,-2.10,.95),(3.79,.14,.59),.047,tilt=(.13,0,0))
    rod('Feed auger core','slate',(-1.84,-2.41,.92),(1.84,-2.41,.92),.13,20)
    for i in range(23):
        x=-1.77+i*.157
        rod('Auger segment paddle','metal',(x,-2.40,.92),(x+.072,-2.38,.92),.213,20)
    for s in (-1,1):
        side_plate('Pointed crop divider','redcoat',[(-3.74,.61),(-3.35,.85),(-2.30,1.30),(-2.09,.77),(-2.52,.59)],s*1.82,s*1.94,.024)
        beam('Reel lift arm','slate',(s*1.78,-2.14,1.07),(s*1.78,-2.99,1.43),.093)
    rod('Reel shaft','metal',(-1.86,-2.99,1.43),(1.86,-2.99,1.43),.081,20)
    for j in range(6):
        a=TAU*j/6; y=-2.99+.409*math.sin(a); z=1.43+.409*math.cos(a)
        for x in (-1.71,0,1.71): beam('Six spoke bat spider','redcoat',(x,-2.99,1.43),(x,y,z),.051)
        rod('Reel bat tube','redcoat',(-1.76,y,z),(1.76,y,z),.041,12)
        for i in range(18):
            x=-1.61+.19*i
            rod('Flexible pickup tine','black',(x,y,z),(x,y-.084,z-.166),.011,6)
    for j in range(30):
        x=-1.80+j*.124
        face('Knife section','metal',[(x-.063,-3.19,.74),(x,-3.40,.725),(x+.063,-3.19,.74)],(0,0,1))


if __name__ == '__main__':
    reset()
    build()
    finish('Kedah Tracked Padi Combine', 6.85,(0,0,1.6),(-1.45,-1.42,.95))
