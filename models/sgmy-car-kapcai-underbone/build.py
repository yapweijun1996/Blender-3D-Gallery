"""Kapcai Pasar Underbone | original procedural SG/MY game asset.

Rebuild with Blender 5.2.3: blender -b --factory-startup --python build.py
Writes model.glb and preview.png alongside this script. No external inputs.
Blender: metres, Z-up, nose -Y. GLB: metres, Y-up, nose +Z.
The bike has centred handlebars and the throttle grip on the rider’s right.
Static material-batched mesh with UVs; the GLB needs a Draco decoder.
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
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.cycles.denoising_prefilter = 'ACCURATE'
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
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


def kapcai():
    standard()
    material('paint','Coral kapcai lacquer','ED5036',.31,.22)
    material('accent','Warm stone racing enamel','FFE1B2',.43)
    material('case','Dark cast engine alloy','546470',.57,.34)
    material('saddle','Textured saddle vinyl','232833',.72)
    front_y,rear_y,r = -.651,.625,.282
    for y,w in [(front_y,.083),(rear_y,.103)]:
        wheel(y,0,r,w,-1,'bike')
        # Opposite hub face is separate from the tire, which is shared across the whole tread.
        lip = w/2
        rim = r*.61
        lathe('Inboard silver bead','metal',lip,y,r,[(-.012,rim*.93),(0,rim),( .006,rim*.93),(-.008,rim*.88)],24)
        for i in range(5):
            t=i*TAU/5
            face('Far alloy spoke','metal',[(lip-.009,y+d*math.cos(t+a),r+d*math.sin(t+a)) for d,a in
                 [(.039,-.35),(.162,-.17),(.162,.12),(.039,.37)]],(1,0,0))
        rod('Silver axle button','metal',(lip-.024,y,r),(lip+.024,y,r),.045,16)
    rod('Front brake disc carrier','metal',(.046,front_y,r),(.056,front_y,r),.109,24)
    lathe('Front brake disc rim','case',.060,front_y,r,[(-.006,.098),(-.006,.117),(0,.117),(0,.098)],24)
    box('Front brake caliper','case',(.063,front_y+.072,r+.072),(.060,.083,.057),.017,tilt=(.42,0,0))
    section=[(.72,0),(.898,.075),(1,.23),(1,.69),(.936,.88),(.79,1)]
    # The step-through body has a slim spine below the rider's knees and a sculpted rear cowl.
    body_loft('Low step-through underbone casing','paint',
              [(-.492,.443,.729,.156),(-.362,.379,.669,.164),(-.203,.326,.597,.149),
               (-.008,.331,.570,.132),(.158,.378,.606,.141),(.28,.449,.701,.17),(.367,.497,.766,.18)],section)
    body_loft('Aerodynamic two-up tail plastics','paint',[(y,b,t,w) for y,b,t,w in
              [(.045,.551,.690,.104),(.153,.508,.759,.158),(.326,.510,.783,.190),
               (.560,.540,.792,.190),(.756,.580,.768,.168),(.885,.626,.729,.128),(.927,.655,.704,.103)]],section)
    body_loft('Raised pillion saddle','saddle',
              [(.054,.654,.748,.076),(.138,.694,.803,.132),(.292,.728,.817,.155),(.474,.756,.856,.160),
               (.673,.752,.855,.152),(.801,.727,.821,.125),(.825,.724,.788,.100)],section)
    body_loft('Upper steering fairing','paint',[(-.695,.860,1.031,.146),(-.637,.815,1.082,.198),
              (-.520,.805,1.112,.193),(-.364,.844,1.087,.143),(-.315,.884,1.018,.107)],section)
    body_loft('Underbone forward knee apron','paint',[(-.596,.554,.785,.072),(-.523,.479,.903,.151),
               (-.432,.441,.960,.205),(-.320,.415,.880,.216),(-.255,.439,.757,.192)],section)
    box('Flat matte step-through tread','black',(0,-.091,.571),(.244,.301,.042),.022,tilt=(-.105,0,0))
    for s in (-1,1):
        # Axle-to-head tubes arranged behind the front fender arcs.
        rod('Lower fork casting','case',(s*.068,-.639,r),(s*.079,-.563,.506),.028,12)
        rod('Upper fork slider','metal',(s*.078,-.576,.477),(s*.071,-.432,.848),.018,10)
        line('Handlebar tube','black',[(s*.046,-.458,1.012),(s*.194,-.462,1.028),
             (s*.255,-.424,1.030),(s*.329,-.401,1.032)],.018,10)
        rod('Right throttle grip' if s<0 else 'Left handlebar grip','tire',
            (s*.242,-.429,1.028),(s*.347,-.396,1.033),.024,12)
        line('Hand lever','metal',[(s*.224,-.466,1.020),(s*.279,-.480,1.021),(s*.337,-.466,1.021)],.0075,8)
        line('Tall mirror stem','black',[(s*.218,-.458,1.044),(s*.259,-.453,1.206),(s*.314,-.442,1.243)],.009,8)
        box('Rounded motorcycle mirror','black',(s*.324,-.444,1.255),(.141,.047,.091),.020,tilt=(0,-s*.14,-s*.27))
        box('Motorbike mirror lens','metal',(s*.324,-.420,1.255),(.118,.010,.071),.015,tilt=(0,-s*.14,-s*.27))
        rod('Rear wheel swing arm','case',(s*.081,.149,.368),(s*.069,rear_y,r),.033,12)
        a,b = Vector((s*.110,.605,.310)),Vector((s*.123,.422,.582))
        rod('Twin rear damper','metal',a,b,.016,10)
        rod('Lower damper sleeve','case',a,a.lerp(b,.43),.023,10)
        axis=(b-a).normalized()
        u=Vector((1,0,0))
        v=axis.cross(u).normalized()
        pts=[]
        for i in range(29):
            t=i/28
            q=TAU*4.5*t
            pts.append(a.lerp(b,.28+t*.60)+.027*(u*math.cos(q)+v*math.sin(q)))
        line('Rear suspension coil','metal',pts,.0047,6)
        rod('Rider footpeg','black',(s*.103,.067,.333),(s*.263,.059,.333),.025,10)
        rod('Pillion footpeg','black',(s*.106,.453,.376),(s*.218,.454,.376),.016,10)
        line('Rear passenger grab bar','case',[(s*.123,.627,.792),(s*.170,.764,.813),
             (s*.144,.869,.796),(0,.889,.785)],.017,10)
        x=s*.194
        face('Rear cowl sweep','accent',[(x,.349,.597),(x,.713,.650),(x,.733,.690),
             (x,.498,.641),(x,.374,.655)],(s,0,0))
        sign('Rear fairing identity','KAPCAI','accent',(s*.191,.517,.707),.044,.265,(s,0,0))
    # Small air-cooled horizontal-cylinder engine, heel guard, and right-side exhaust.
    box('Cast engine crankcases','case',(0,.052,.319),(.289,.335,.239),.063,3)
    for y in (-.292,-.263,-.234,-.205,-.176):
        box('Cooling fin','metal',(0,y,.345),(.210,.018,.133),.006,1,tilt=(.12,0,0))
    for s in (-1,1):
        rod('Round engine case','case',(s*.134,.081,.327),(s*.163,.081,.327),.080,16)
        rod('Service cap','metal',(s*.161,.081,.327),(s*.170,.081,.327),.044,12)
    line('Exhaust header','case',[(-.080,-.283,.348),(-.136,-.269,.210),(-.165,-.161,.177),
         (-.172,.194,.190),(-.167,.430,.239)],.021,10)
    a,b = (-.149,.323,.221),(-.145,.823,.317)
    rod('Dark tapered exhaust canister','black',a,b,.054,14)
    rod('Satin heatshield','metal',(-.177,.374,.236),(-.173,.760,.313),.045,12)
    rod('Exhaust end cap','case',(-.145,.798,.312),(-.145,.834,.319),.051,14)
    rod('Exhaust outlet','black',(-.145,.832,.318),(-.145,.841,.320),.022,12)
    box('Main front headlight surround','black',(0,-.690,.967),(.326,.103,.118),.031)
    box('Main headlight lens','lamp',(0,-.743,.968),(.268,.026,.073),.021)
    for s in (-1,1):
        box('Front corner turn indicator','amber',(s*.160,-.701,.947),(.061,.034,.055),.014,tilt=(0,0,s*.27))
        box('Rear turn signal','amber',(s*.104,.919,.650),(.057,.047,.052),.013)
    box('Rear brake lens','red',(0,.933,.690),(.175,.040,.061),.015)
    box('Rear tyre splash fin','black',(0,.849,.489),(.147,.064,.278),.015,tilt=(-.23,0,0))
    plate('JXN 7024',.920,.495,False,.205,.075)
    # A real arc around each tyre instead of a flat slab.
    def fender(y, phase, extent, width, key):
        vertices=[]
        steps=14
        for i in range(steps+1):
            t=math.radians(phase+extent*i/steps)
            w=width*(.82+.18*math.sin(math.pi*i/steps))
            for x,rad in [(-w,.309),(-w*.63,.321),(w*.63,.321),(w,.309)]:
                vertices.append((x,y+rad*math.cos(t),r+rad*math.sin(t)))
        faces=[(j*4+k,(j+1)*4+k,(j+1)*4+k+1,j*4+k+1) for j in range(steps) for k in range(3)]
        obj=mesh('Curved tyre mudguard',vertices,faces,key)
        mod=obj.modifiers.new('Moulded mudguard thickness','SOLIDIFY')
        mod.thickness=.010
    fender(front_y,28,139,.073,'paint')
    fender(rear_y,14,124,.078,'black')
    # Small wet-market wire basket, with a tapered foot and an open upper rim.
    a,b,w,z = -.852,-.539,.154,.842
    c,d,w2,z2 = -.814,-.553,.112,.647
    for yy,yy2 in [(a,c),(b,d)]:
        rod('Basket broad top rail','black',(-w,yy,z),(w,yy,z),.012,8)
        rod('Basket welded lower rail','black',(-w2,yy2,z2),(w2,yy2,z2),.009,8)
        for i in range(9):
            fraction = i/4-1
            rod('Basket face wire','black',(w2*fraction,yy2,z2),(w*fraction,yy,z),.0048,6)
    for s in (-1,1):
        rod('Basket side top rail','black',(s*w,a,z),(s*w,b,z),.012,8)
        rod('Basket side lower rail','black',(s*w2,c,z2),(s*w2,d,z2),.009,8)
        for i in range(1,8):
            t=i/8
            rod('Basket side wire','black',(s*w2,c+(d-c)*t,z2),(s*w,a+(b-a)*t,z),.0048,6)
        rod('Basket mid-height side rail','black',(s*.133,(a+c)/2,(z+z2)/2),
            (s*.133,(b+d)/2,(z+z2)/2),.0058,6)
        line('Basket supporting bracket','case',[(s*.100,-.779,z2),(s*.095,-.574,z2),
             (s*.087,-.512,.770)],.010,8)
    for i in range(1,7):
        y=c+(d-c)*i/7
        rod('Basket base wire','black',(-w2,y,z2),(w2,y,z2),.0055,6)
    box('Instrument pod','black',(0,-.462,1.082),(.203,.149,.045),.024,tilt=(-.14,0,0))
    box('Instrument cover','seat',(0,-.462,1.107),(.159,.105,.013),.013,tilt=(-.14,0,0))


if __name__ == '__main__':
    reset()
    kapcai()
    finish('Kapcai Pasar Underbone', 2.01, (0, -0.033, 0.59), (-1.82, -1.32, 0.68), 1.18)
