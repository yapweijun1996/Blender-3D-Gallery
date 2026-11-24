"""Selat Yellow-Top Taxi | original procedural SG/MY game asset.

Rebuild with Blender 5.2.3: blender -b --factory-startup --python build.py
Writes model.glb and preview.png alongside this script. No external inputs.
Blender: metres, Z-up, nose -Y. GLB: metres, Y-up, nose +Z.
The driver sits at -X (vehicle right) in both coordinate systems.
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


def sedan_body(police=False):
    standard()
    if police:
        material('paint','Pearl grey patrol paint','E9EDEE',.27,.28)
        material('accent','Patrol navy reflective enamel','153754',.36,.12)
        material('flash','Straits blue reflective enamel','36CAE2',.31,.10)
        material('blue','Signal blue lens','2474F8',.25,emission=.20)
        material('privacy','Patrol side privacy glazing','36536A',.38,alpha=.69)
        profile = [(-2.23,.35,.72,.70),(-2.194,.27,.77,.795),(-2.09,.237,.81,.871),
                   (-1.73,.224,.845,.887),(-1.05,.222,.907,.898),(-.88,.222,.923,.898),
                   (.82,.227,.931,.898),(1.39,.257,.947,.899),(1.92,.31,.908,.876),(2.20,.345,.86,.816),(2.25,.389,.801,.763)]
        stations = [(-1.015,.903,.820,-.522,1.408,.626),(-.910,.91,.823,-.444,1.415,.638),
                    (.055,.916,.826,.056,1.437,.671),(.159,.917,.826,.142,1.438,.670),
                    (1.055,.924,.817,.697,1.423,.644),(1.460,.933,.786,.843,1.398,.603)]
        axles = (-1.35,1.335)
        r, casing, track = .321,.210,.774
    else:
        material('paint','Jet graphite taxi enamel','303B46',.29,.35)
        roof_paint = material('roof','Golden taxi roof enamel','ECAA00',.43,.02)
        roof_paint.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value = .21
        material('accent','Taxi gold leaf vinyl','FFC53C',.44,.02)
        profile = [(-2.285,.345,.745,.677),(-2.248,.27,.791,.766),(-2.151,.255,.826,.823),
                   (-1.859,.228,.855,.869),(-1.27,.220,.888,.885),(-.98,.22,.902,.885),
                   (.95,.22,.922,.885),(1.56,.253,.944,.885),(1.948,.28,.920,.853),(2.224,.321,.872,.798),(2.29,.370,.822,.753)]
        stations = [(-1.019,.889,.814,-.614,1.457,.637),(-.922,.898,.814,-.517,1.475,.662),
                    (.028,.908,.815,.061,1.485,.690),(.137,.910,.815,.152,1.485,.689),
                    (1.04,.918,.811,.692,1.465,.651),(1.440,.93,.783,.805,1.438,.611)]
        axles = (-1.365,1.342)
        r, casing, track = .309,.194,.766
    body = body_loft('Stamped three-box sedan body','paint',profile)
    wells(body, axles, r, r+.050, .899 if police else .885,.245)
    wheels(axles,track,r,casing,'alloy' if police else 'steel')
    roof = 'paint' if police else 'roof'
    shell(stations,[None,.072,None,.08,None],paint=roof,side_tint='privacy' if police else 'glass')
    roof_profile = [(Y-.009,Z-.013,Z+.026,X+.007) for _,_,_,Y,Z,X in stations]
    body_loft('Crowned sedan roof',roof,roof_profile)
    for s in (-1,1):
        mirror(s*.931,-.830,1.023,s,.201)
        chair(s*.381,.032,.955,.418,.305)
        chair(s*.371,.727,.947,.423,.239)
        box('Under-door shadow skirt','black',(s*.851,.012,.282),(.086,1.87,.095),.032)
        box('Door handle bezel','black',(s*.883,-.103,.812),(.023,.130,.036),.008)
        box('Door handle bezel','black',(s*.883,.778,.825),(.023,.130,.036),.008)
        for y,z in [(-.103,.815),(.778,.828)]:
            box('Satin door pull','metal',(s*.895,y,z),(.012,.104,.015),.005)
        # The outer shoulder rolls in towards the glass. Shell seams follow it.
        for y,sgn in [(-.927,1),(.083,0),(.967,-1)]:
            line('Door shut line','black',symmetry([(.862,y,.900),(.884,y,.795),(.896,y+.037*sgn,.708),
                 (.895,y+.051*sgn,.495),(.895,y+.093*sgn,.349)],s),.0042,6)
        if police:
            x=s*.900
            face('Swept lower patrol sash','accent',[(x,-.94,.371),(x,-.94,.448),(x,.918,.729),
                 (x,.891,.592),(x,.348,.376)],(s,0,0))
            face('Cyan patrol sash edge','flash',[(x,-.94,.448),(x,-.94,.470),
                 (x,.924,.758),(x,.918,.729)],(s,0,0))
            sign('Patrol door wordmark','POLIS','accent',(s*.906,-.39,.668),.126,.62,(s,0,0))
            sign('Patrol sector door legend','RONDA BANDAR','accent',(s*.904,-.405,.561),.040,.56,(s,0,0))
        else:
            sign('Taxi door wordmark','SELAT TAXI','accent',(s*.889,-.405,.668),.101,.85,(s,0,0))
            sign('Taxi fleet door legend','KOTA  /  BANDAR','ivory',(s*.889,-.41,.540),.034,.65,(s,0,0))
            x=s*.888
            for k in range(4):
                b=.26+k*.095
                face('Taxi gold lozenge','accent',[(x,b,.582),(x,b+.064,.582),(x,b+.103,.684),(x,b+.040,.684)],(s,0,0))
            face('Taxi sill pinstripe','accent',[(x,-.99,.369),(x,.986,.369),(x,1.009,.385),(x,-1.001,.385)],(s,0,0))
    box('Dashboard','black',(0,-.788,.933),(1.425,.252,.127),.055)
    box('Driver binnacle','black',(-.399,-.756,1.006),(.39,.151,.081),.029)
    box('Instrument glass','seat',(-.399,-.678,1.006),(.277,.016,.052),.012)
    steer(-.399,-.659,1.020)
    box('Centre tunnel top','black',(0,.20,.929),(.266,1.10,.097),.034)
    rod('Shift lever','metal',(0,-.22,.953),(0,-.244,1.004),.012,8)
    for s in (-1,1):
        line('Parked wiper','black',[(s*.55,-.998,.937),(s*.45,-.977,.966),(s*.14,-.965,.979)],.009,6)
        box('Front fog recess','black',(s*.605,-2.206,.389),(.231,.092,.105),.039)
        box('Fog reflector','lamp',(s*.620,-2.251,.391),(.106,.018,.042),.012)
        if police:
            box('Front LED lamp scallop','black',(s*.594,-2.215,.689),(.450,.119,.152),.027,tilt=(0,-s*.13,s*.061))
            box('Ice LED blade','lamp',(s*.585,-2.275,.715),(.363,.024,.052),.015,tilt=(0,-s*.13,s*.061))
            box('LED projector','metal',(s*.653,-2.273,.662),(.173,.022,.031),.005,tilt=(0,-s*.13,s*.061))
            box('Rear light black border','black',(s*.608,2.210,.766),(.394,.140,.144),.030,tilt=(0,s*.085,-s*.068))
            box('Rear brake blade','red',(s*.608,2.282,.789),(.355,.023,.063),.018,tilt=(0,s*.085,-s*.068))
        else:
            box('Front lamp black bezel','black',(s*.602,-2.228,.696),(.401,.134,.173),.032,tilt=(0,-s*.086,s*.119))
            box('Twin-beam headlight lens','lamp',(s*.582,-2.296,.713),(.317,.021,.102),.023,tilt=(0,-s*.086,s*.119))
            box('Amber turn signal','amber',(s*.752,-2.279,.735),(.069,.026,.086),.015,tilt=(0,-s*.086,s*.119))
            box('Rear light black border','black',(s*.584,2.247,.761),(.422,.144,.143),.033,tilt=(0,s*.070,-s*.091))
            box('Red tail lamp','red',(s*.595,2.323,.773),(.355,.026,.090),.016,tilt=(0,s*.070,-s*.091))
            box('Tail lamp turn repeater','amber',(s*.704,2.323,.758),(.105,.025,.038),.010,tilt=(0,s*.065,-s*.09))
    y = profile[0][0]
    box('Upper radiator grille','black',(0,y-.003,.677),(.760,.079,.122),.034)
    box('Lower bumper intake','black',(0,y+.008,.438),
        (1.066 if police else .901,.123,.163 if police else .146),.040)
    if police:
        for x in (-.292,.292):
            box('Lower intake vanes','seat',(x,y-.057,.432),(.350,.019,.015),.004)
    for zz in (.643,.675,.707):
        box('Satin grille vane','metal',(0,y-.045,zz),(.672,.013,.010),.003)
    box('Lower apron splitter','black',(0,y+.034,.326),(1.359,.176,.076),.036)
    yr = profile[-1][0]
    box('Rear bumper insert','black',(0,yr-.010,.410),(1.43,.112,.118),.041)
    box('Brushed tailgate garnish','metal',(0,yr+.019,.765),(.753,.022,.035),.010)
    plate('WQX 6418' if police else 'STX 218Q',y-.059,.503,True)
    plate('WQX 6418' if police else 'STX 218Q',yr+.048,.598,False)
    if police:
        box('Roof lightbar mounting feet','black',(0,.003,1.481),(.70,.195,.088),.029)
        box('Low-profile roof lightbar','black',(0,.003,1.539),(1.13,.245,.106),.032)
        for s,k in [(-1,'blue'),(1,'red')]:
            box('Wraparound warning lens',k,(s*.384,-.001,1.555),(.334,.255,.067),.023)
            box('Lightbar clear LED strip','lamp',(s*.369,-.132,1.555),(.206,.012,.021),.005)
        for s in (-1,1):
            for i in range(3):
                x=s*(.510+.060*i)
                sign('Rear chevron stripe','/','flash',(x,yr+.052,.527),.077,.037,(0,1,0))
        sign('Rear patrol identification','POLIS','accent',(0,yr+.035,.712),.064,.43,(0,1,0))
    else:
        box('Roof hire sign gasket','black',(0,-.304,1.513),(.607,.287,.083),.040)
        box('Taxi hire lantern','roof',(0,-.304,1.585),(.584,.263,.143),.052)
        for d in (-1,1):
            sign('Taxi hire lantern inscription','TAXI','black',(0,-.304+d*.134,1.589),.079,.428,(0,d,0))
        sign('Rear taxi fleet identification','SELAT','accent',(0,yr+.019,.705),.051,.38,(0,1,0))


if __name__ == '__main__':
    reset()
    sedan_body()
    finish('Selat Yellow-Top Taxi', 4.7, (0, -0.12, 0.76), (-1.42, -1.85, 0.82), 1.09)
