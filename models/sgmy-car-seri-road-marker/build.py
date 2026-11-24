"""Seri Road Line Marking Lorry: original procedural game asset.

Run: blender -b --factory-startup --python build.py
Metres, ground origin, nose -Y; glTF nose +Z. No external inputs.
Static geometry, UVs and Draco-compressed GLB.
"""
import math
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
    return bevel(obj, radius, segments)


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


def symmetry(points, side):
    return [(p[0]*side, p[1], p[2]) for p in points]


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
    bevel(body, .013)


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


def wheels(axles, x, r, width, style='steel'):
    for y in axles:
        for s in (-1,1):
            wheel(y,s*x,r,width,s,style)


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


def plate(words, y, z, front, width=.40, height=.108):
    d = -1 if front else 1
    box('Registration plate recess','black',(0,y,z),(width,.027,height),.013)
    sign('Fictional registration',words,'ivory',(0,y+d*.015,z),height*.54,width*.86,(0,d,0))


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
    obj['origin_note'] = 'Base centre at ground level'
    obj['steering'] = 'Centred handlebars' if 'Kapcai' in name else 'Right-hand drive'
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
    box('Preview floor','studio',(0,0,-.113),(length*200,length*200,.22))
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
    scene.cycles.use_denoising = True
    scene.cycles.denoising_prefilter = 'ACCURATE'
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -1.65
    scene.render.resolution_x = 500
    scene.render.resolution_y = 340
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 65
    return scene


def finish(name, length, target, direction, fill=1.13):
    out = Path(__file__).resolve().parent
    consolidate(name)
    result = bpy.ops.export_scene.gltf(
        filepath=str(out/'model.glb'),export_format='GLB',use_selection=True,
        export_texcoords=True,export_normals=True,export_animations=False,export_extras=True,
        export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=7,
        export_draco_position_quantization=16,export_draco_texcoord_quantization=14)
    if result != {'FINISHED'}:
        raise RuntimeError(f'GLB export failed: {result}')
    studio(length, target, direction, fill).render.filepath = str(out/'preview.png')
    bpy.ops.render.render(write_still=True)



PAINT = 'E5A526'
ACCENT = '6E7D84'
# Original vehicles for a Singapore / Malaysia street scene.
# Coordinates are metres. Nose is -Y, right side is -X.

def palette():
    standard()
    material('paint','Fleet main paint', PAINT,.36,.15)
    material('roof','Warm white upper body','E5E9E1',.36,.07)
    material('accent','Fleet contrast colour',ACCENT,.4,.05)
    material('dark','Deep painted steel','30444B',.43,.12)
    material('safety','Safety yellow','F1BF38',.42)
    material('interior','Interior upholstery','6C858A',.72)


def chassis(length, axles, r=.48, width=1.15):
    box('Longitudinal chassis','black',(0,0,r+.12),(1.74,length-.5,.26),.07)
    for x in (-.68,.68):
        box('Frame rail','dark',(x,0,r-.06),(.15,length-.8,.18),.02)
    wheels(axles,width,r,.28,'lorry')
    for y in axles:
        rod('Axle housing','black',(-width,y,r),(width,y,r),.10,12)


def cab(front, rear, height=2.55):
    # Rigid forward-control cab, visible through glazing. Driver is on the right.
    b=.64; belt=1.43; hw=1.10
    body_loft('Forward control cab lower body','paint',[(front,b,belt,1.02),(front+.16,.53,belt,hw),(rear,.53,belt,hw)])
    rows=[(front+.13,belt,hw,front+.35,height-.16,1.00),
          (rear-.09,belt,hw,rear-.17,height-.16,1.00),
          (rear,belt,hw,rear,height-.16,1.00)]
    shell(rows,[.15,None],.07,0)
    box('Cab roof','paint',(0,(front+rear)/2,height-.10),(2.05,rear-front-.16,.22),.10,3)
    box('Cab dash','black',(0,front+.44,1.50),(1.88,.35,.16),.04)
    chair(-.55,front+.97,1.22,.43,.48)
    chair(.52,front+.97,1.22,.43,.48)
    steer(-.55,front+.65,1.59,.16)
    for s in (-1,1):
        mirror(s*1.22,front+.23,1.92,s,.19,True)
        box('Headlamp surround','black',(s*.74,front-.015,.86),(.46,.10,.24),.04)
        box('Headlamp lens','lamp',(s*.74,front-.071,.89),(.35,.02,.10),.02)
        box('Indicator lens','amber',(s*.91,front-.073,.79),(.10,.02,.07),.01)
        box('Cab side step','metal',(s*1.12,rear-.28,.61),(.16,.54,.08),.02)
        box('Door handle','black',(s*1.112,rear-.29,1.30),(.02,.22,.04),.01)
    box('Cab front grille','black',(0,front-.07,.72),(1.14,.08,.23),.025)
    for z in (.65,.71,.77): box('Grille slat','metal',(0,front-.115,z),(.94,.014,.014))
    box('Front bumper','dark',(0,front-.10,.51),(2.03,.18,.18),.04)
    plate('SXM 528',front-.20,.52,True,.39,.10)


def rear_lamps(y, width=1.0):
    for s in (-1,1):
        box('Tail lamp housing','black',(s*width,y,.68),(.28,.10,.19),.025)
        box('Tail lamp red','red',(s*width,y+.057,.71),(.19,.02,.09),.01)
        box('Tail indicator','amber',(s*width,y+.058,.63),(.19,.02,.045),.007)


def side_sign(words, y, z, width, size=.19):
    for s in (-1,1):
        sign('Fictional fleet lettering',words,'roof',(s*1.171,y,z),size,width,(s,0,0))


def bus():
    chassis(10.2,(-3.35,3.1),.49,1.10)
    body_loft('Lower bus monocoque','paint',[(-5.0,.44,1.35,1.03),(-4.78,.39,1.35,1.15),(4.76,.39,1.35,1.15),(5,.48,1.35,1.04)])
    for s in (-1,1):
        box('Lower deck passenger windows','black',(s*1.13,.2,1.93),(.08,9.1,1.17),.06)
        for i in range(8):
            y=-4.02+i*1.12
            box('Individual tinted passenger window','glass',(s*1.177,y,1.96),(.025,1.00,.95),.035)
            box('Lower window pillar','roof',(s*1.191,y+.54,1.96),(.04,.065,1.13),.01)
        box('Upper deck outer wall','paint',(s*1.105,.35,2.87),(.11,8.9,.55),.04)
        box('Upper deck guard rail','metal',(s*1.10,.35,3.76),(.045,8.9,.045),.01)
        for y in [i*.85-3.9 for i in range(11)]:
            rod('Upper deck rail stanchion','metal',(s*1.1,y,3.13),(s*1.1,y,3.77),.022,8)
            box('Upper deck seat','accent',(s*.57,y,3.14),(.67,.50,.12),.04)
            box('Upper deck seat back','accent',(s*.57,y+.23,3.42),(.67,.10,.57),.04,tilt=(.12,0,0))
        side_sign('JELAJAH',.0,.96,3.6,.22)
        box('Continuous side stripe','accent',(s*1.16,.0,.73),(.025,8.9,.12),.01)
        mirror(s*1.30,-4.65,2.22,s,.22,True)
    glazed('Driver front screen',[(-1.05,-4.94,1.39),(1.05,-4.94,1.39),(1.02,-4.78,2.51),(-1.02,-4.78,2.51)],(0,-1,0),.08)
    box('Lower deck ceiling','roof',(0,0,2.58),(2.20,9.7,.15),.05)
    box('Upper front wind deflector','glass',(0,-4.52,3.36),(2.04,.07,.64),.035,tilt=(-.14,0,0))
    box('Front fascia','black',(0,-5.02,.82),(1.60,.08,.30),.05)
    for s in (-1,1):
        box('Headlamp','lamp',(s*.77,-5.07,.84),(.32,.03,.12),.02)
        box('Rear lamp','red',(s*.93,5.03,.79),(.16,.04,.28),.02)
    plate('SJT 208',-5.09,.59,True)
    chair(-.58,-4.23,1.24); steer(-.58,-4.65,1.61)
    sign('Destination board','CITY LOOP','accent',(0,-4.96,2.36),.16,1.4,(0,-1,0))


def clinic():
    chassis(7.8,(-2.55,2.55),.43,1.05)
    cab(-3.85,-1.75,2.48)
    box('Medical module','roof',(0,.77,1.67),(2.23,5.1,2.03),.12,3)
    box('Clinic insulated roof','roof',(0,.77,2.73),(2.14,4.9,.14),.07)
    for s in (-1,1):
        box('Teal lower stripe','paint',(s*1.125,.77,1.02),(.027,4.9,.26),.01)
        box('Long privacy window','glass',(s*1.13,-.15,2.03),(.03,1.34,.54),.04)
        box('Window surround','black',(s*1.12,-.15,2.03),(.025,1.46,.66),.05)
        box('Long privacy pane','glass',(s*1.145,-.15,2.03),(.018,1.34,.54),.03)
        side_sign('DERMA DARAH',1.47,1.83,2.1,.18)
        box('Service access door','dark',(s*1.13,2.48,1.52),(.04,.84,1.51),.03)
        box('Service access panel','roof',(s*1.16,2.48,1.52),(.025,.73,1.38),.02)
        box('Door grab handle','metal',(s*1.18,2.19,1.52),(.02,.04,.24),.01)
        box('Medical cross vertical','accent',(s*1.145,1.17,2.31),(.03,.14,.47),.01)
        box('Medical cross horizontal','accent',(s*1.146,1.17,2.31),(.03,.47,.14),.01)
    box('Rear entry door','dark',(0,3.34,1.54),(1.15,.04,1.80),.04)
    box('Rear entry inset','roof',(0,3.37,1.54),(1.03,.03,1.66),.03)
    rear_lamps(3.36)
    box('Roof air conditioning','dark',(0,.4,2.84),(1.18,1.65,.24),.09)
    for y in (-.15,.10,.35,.60,.85): box('Ventilation grille','metal',(0,y,2.968),(.95,.035,.015),.005)


def carrier():
    chassis(9.2,(-3.15,2.7,3.65),.46,1.08)
    cab(-4.55,-2.35,2.44)
    box('Loading platform','dark',(0,.70,1.07),(2.24,6.9,.18),.035)
    for s in (-1,1):
        box('Platform edge rail','safety',(s*1.13,.7,1.19),(.10,6.9,.22),.03)
        box('Riser post','dark',(s*1.02,-1.73,2.15),(.14,.16,2.13),.025)
        box('Rear riser post','dark',(s*1.02,3.55,2.15),(.14,.16,2.13),.025)
        box('Upper longitudinal rail','dark',(s*1.02,.85,3.18),(.16,5.6,.15),.02)
        rod('Diagonal truss brace','safety',(s*1.02,-1.6,1.2),(s*1.02,3.5,3.1),.045,8)
        rod('Diagonal truss brace','safety',(s*1.02,-1.6,3.1),(s*1.02,3.5,1.2),.045,8)
    box('Upper deck','dark',(0,.7,2.73),(2.15,5.9,.13),.025)
    # Two explicitly stylised cargo hatchbacks on separate decks.
    for z,y in [(1.22,.30),(2.83,.50)]:
        body_loft('Cargo hatchback body','accent',[(y-1.62,z+.14,z+.57,.71),(y-1.35,z+.10,z+.67,.79),(y+1.28,z+.10,z+.67,.79),(y+1.55,z+.16,z+.54,.68)])
        rows=[(y-.85,z+.66,.72,y-.47,z+1.16,.62),(y+.50,z+.66,.72,y+.35,z+1.16,.62),(y+.91,z+.66,.70,y+.68,z+1.09,.60)]
        shell(rows,[.12,.16],.10,.1,paint='accent')
        box('Cargo roof','accent',(0,y-.01,z+1.16),(1.23,.82,.08),.04)
        for yy in (y-1.00,y+1.05):
            for s in (-1,1):
                rod('Cargo wheel','tire',(s*.69,yy,z+.30),(s*.83,yy,z+.30),.28,20)
                rod('Cargo wheel hub','metal',(s*.835,yy,z+.30),(s*.845,yy,z+.30),.16,16)
    rear_lamps(4.2)
    for s in (-1,1):
        rod('Folded loading ramp','metal',(s*.65,4.15,1.18),(s*.65,4.30,2.35),.07,8)


def line_truck():
    chassis(7.6,(-2.55,2.42),.43,1.05)
    cab(-3.75,-1.60,2.45)
    box('Service deck','dark',(0,.83,1.02),(2.18,5.15,.20),.04)
    for s in (-1,1):
        box('Deck edge','safety',(s*1.08,.83,1.17),(.08,5.15,.18),.02)
        sign('Service designation','GARIS JALAN','roof',(s*1.135,.3,1.46),.16,1.5,(s,0,0))
    for x in (-.55,.55):
        rod('Paint mixing kettle','paint',(x,-.14,1.18),(x,-.14,2.03),.44,24)
        rod('Kettle lid','metal',(x,-.14,2.03),(x,-.14,2.10),.46,24)
        rod('Kettle stirring drive','dark',(x,-.14,2.1),(x,-.14,2.35),.08,12)
        box('Kettle burner','black',(x,-.14,1.15),(.73,.73,.14),.03)
    box('Equipment locker','accent',(0,1.65,1.55),(1.93,1.36,.83),.07)
    for s in (-1,1):
        box('Locker inset panel','dark',(s*.98,1.65,1.55),(.025,1.14,.64),.03)
        box('Locker grip','metal',(s*1.0,1.65,1.58),(.02,.32,.04),.01)
    for x in (-.70,.70):
        rod('Applicator support arm','metal',(x,2.20,1.02),(x,3.45,.37),.05)
        rod('Marking applicator wheel','tire',(x-.12,3.44,.25),(x+.12,3.44,.25),.25,20)
    box('Marking spray bar','safety',(0,3.48,.36),(1.7,.14,.12),.025)
    for x in (-.6,-.3,0,.3,.6): box('Spray nozzle','metal',(x,3.48,.27),(.06,.07,.13),.01)
    for s in (-1,1):
        rod('Warning beacon','amber',(s*.82,-2.42,2.43),(s*.82,-2.42,2.62),.09,16)
    rear_lamps(3.41)


def cherry():
    chassis(8.0,(-2.7,2.5),.46,1.08)
    cab(-3.95,-1.7,2.50)
    box('Utility platform','dark',(0,.85,1.00),(2.18,5.55,.25),.05)
    box('Tool chest','paint',(0,-.95,1.45),(2.10,1.25,.82),.06)
    for s in (-1,1):
        box('Locker inset','roof',(s*1.065,-.95,1.48),(.03,1.02,.60),.025)
        box('Locker handle','black',(s*1.085,-.95,1.48),(.02,.25,.04),.01)
        for y in (-.30,2.2):
            box('Stabilizer beam','metal',(s*1.02,y,.82),(.42,.24,.17),.02)
            rod('Hydraulic stabilizer','dark',(s*1.18,y,.84),(s*1.18,y,.25),.075)
            box('Stabilizer foot','black',(s*1.18,y,.20),(.34,.34,.12),.025)
        side_sign('KERJA TINGGI',.75,.96,1.8,.13)
    rod('Turntable base','safety',(0,.68,1.15),(0,.68,1.48),.58,24)
    box('Boom pivot housing','paint',(0,.78,1.58),(.82,.88,.42),.07)
    rod('Telescopic boom outer','roof',(0,.65,1.68),(0,2.52,2.58),.24,8)
    rod('Telescopic boom inner','metal',(0,2.40,2.52),(0,3.15,2.88),.17,8)
    rod('Lift cylinder','dark',(-.40,.12,1.38),(-.40,1.91,2.33),.075,12)
    rod('Lift cylinder chrome','metal',(-.40,1.54,2.15),(-.40,2.01,2.40),.045,12)
    box('Work basket floor','safety',(0,3.25,2.93),(1.25,1.05,.12),.03)
    for s in (-1,1):
        rod('Basket guardrail','safety',(s*.60,2.76,2.99),(s*.60,2.76,4.03),.035,8)
        rod('Basket guardrail','safety',(s*.60,3.74,2.99),(s*.60,3.74,4.03),.035,8)
        rod('Basket guardrail','safety',(s*.60,2.76,4.03),(s*.60,3.74,4.03),.035,8)
    for y in (2.76,3.74): rod('Basket end rail','safety',(-.60,y,4.03),(.60,y,4.03),.035,8)
    rear_lamps(3.55)

if __name__ == '__main__':
    reset()
    palette()
    line_truck()
    finish('Seri Road Line Marking Lorry', 7.6, (0, 0, 1.35), (1.7, -1.5, .85), 1.14)
