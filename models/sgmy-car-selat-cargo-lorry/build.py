"""Selat Kargo Canvas Lorry | original procedural SG/MY game asset.

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


def cargo_lorry():
    standard()
    material('paint','Straits ocean-blue cab enamel','1879AE',.33,.19)
    material('bed','Slate blue drop-side steel','2E586B',.49,.23)
    material('canvas','Oat canvas tilt','CDAD77',.78)
    material('seam','Canvas edge webbing','AA8757',.70)
    material('accent','Yellow safety reflector','F2CD51',.37,emission=.09)
    material('ink','Marine-blue cargo lettering','234C60',.63)
    section = [(.82,0),(.967,.058),(1,.16),(1,.91),(.989,.978),(.950,1)]
    chassis = body_loft('Cab-over lower pressing and nose','paint',
             [(-3.34,.537,1.519,.927),(-3.28,.475,1.545,1.031),(-3.13,.422,1.588,1.098),
              (-2.953,.411,1.607,1.111),(-1.356,.418,1.607,1.112),(-1.222,.49,1.607,1.052)],section)
    rd=.428
    wells(chassis,(-2.222,),rd,.514,1.109,.297)
    wheels((-2.222,1.886),.955,rd,.265,'lorry')
    for s in (-1,1):
        wheel(1.886,s*.673,rd,.246,s,'lorry')
        box('Long ladder chassis rail','black',(s*.329,.572,.653),(.184,5.35,.242),.030)
        box('Rear mudflap','tire',(s*.854,2.416,.401),(.504,.080,.405),.016)
        box('Battery or tool locker','black',(s*.742,-.452,.716),(.300,.785,.379),.044)
        box('Tool locker latch','metal',(s*.899,-.424,.791),(.038,.105,.059),.011)
        box('Cargo side underrun rail','metal',(s*.891,.068,.473),(.075,1.83,.068),.018)
        box('Cargo side underrun rail','metal',(s*.891,.068,.590),(.075,1.83,.068),.018)
    rod('Front axle tube','black',(-.92,-2.222,rd),(.92,-2.222,rd),.085)
    rod('Rear axle tube','black',(-.95,1.886,rd),(.95,1.886,rd),.095)
    box('Rear differential casing','black',(0,1.886,rd),(.380,.359,.31),.080)
    box('Deck rear underrun rail','black',(0,3.187,.488),(2.054,.166,.173),.029)
    box('Steel flatbed deck','bed',(0,1.115,1.021),(2.232,4.393,.206),.056)
    for s in (-1,1):
        box('Short metal rear wheel splash guard','tire',(s*.887,1.883,.905),(.623,1.181,.124),.059)
    # Drop sides with broad stiffening folds and wrapped canvas on a hoop frame.
    for s in (-1,1):
        box('Cargo drop side','bed',(s*1.093,1.104,1.420),(.098,4.294,.667),.046)
        for z in (1.267,1.476,1.666):
            box('Cargo side pressed stiffener','bed',(s*1.144,1.104,z),(.040,4.22,.064),.016)
        for y in (-.915,.085,1.108,2.208,3.167):
            box('Lashing post','metal',(s*1.159,y,1.430),(.062,.062,.619),.015)
            box('Hinge knuckle','bed',(s*1.159,y,1.164),(.071,.121,.098),.019)
        for y in (-.888,3.133):
            box('Reflective strip','accent',(s*1.151,y,1.030),(.016,.224,.039),.009)
    canvas_section = [(.98,0),(1,.032),(1,.80),(.982,.897),(.937,.963),(.850,.990),(.65,1)]
    tarp_rows = [(-1.036,1.75,2.930,1.015),(-.943,1.72,3.007,1.081),(-.749,1.712,3.045,1.102),
                 (.269,1.713,3.050,1.102),(1.362,1.713,3.048,1.102),(2.431,1.715,3.045,1.102),
                 (3.117,1.730,3.026,1.087),(3.221,1.741,2.974,1.051)]
    body_loft('Hoop-supported cargo tilt','canvas',tarp_rows,canvas_section)
    for s in (-1,1):
        for y in (-.812,-.38,.177,.724,1.278,1.857,2.400,2.962):
            x=1.106 if y<2.75 else 1.096
            rod('Canvas tie-down webbing','seam',(s*x,y,1.842),(s*1.172,y+.049,1.692),.015,6)
        for y in (-.732,2.428):
            pts = [(s*(x*1.102+.004),y,1.712+f*1.335+.004) for x,f in canvas_section[1:]]
            line('Raised canopy seam','seam',pts,.009,6)
        box('Canvas hem strip','seam',(s*1.104,1.175,1.779),(.018,3.94,.076),.010)
        sign('Side cargo fleet mark','SELAT KARGO','ink',(s*1.110,1.055,2.51),.237,2.88,(s,0,0))
        sign('Side freight class','BARANG AM  /  GENERAL CARGO','ink',(s*1.109,1.052,2.217),.080,2.8,(s,0,0))
    box('Tailgate pressing','bed',(0,3.250,1.418),(2.151,.114,.673),.037)
    box('Tailgate top roll','bed',(0,3.294,1.682),(2.112,.071,.081),.025)
    line('Tail canvas flap seam','seam',[(0,3.226,1.783),(0,3.227,2.889)],.012,8)
    rod('Rolled rear canvas upper edge','seam',(-.937,3.228,2.854),(.937,3.228,2.854),.044,14)
    for s in (-1,1):
        box('Tailgate latch handle','metal',(s*.827,3.317,1.473),(.055,.066,.291),.016)
        box('Rear lamp cluster','black',(s*.806,3.266,.808),(.405,.111,.158),.040)
        box('Rear stop lens','red',(s*.887,3.325,.815),(.171,.021,.093),.021)
        box('Rear turn lens','amber',(s*.713,3.324,.816),(.107,.022,.083),.017)
        for j in range(3):
            x=s*(.660+j*.113)
            face('Rear underrun reflector stripe','accent',[(x-.047,3.272,.422),(x+.017,3.272,.422),
                 (x+.065,3.272,.547),(x+.001,3.272,.547)],(0,1,0))
    plate('JQX 7306',3.277,.836,False,.459,.121)
    sign('Generic freight speed legend','80 / 90 KM/J','ivory',(0,3.312,1.396),.090,.755,(0,1,0))
    stations = [(-3.301,1.535,.993,-3.065,2.474,.939),(-3.152,1.585,1.083,-2.944,2.512,1.023),
                (-2.181,1.605,1.102,-2.297,2.544,1.051),(-1.649,1.605,1.102,-1.694,2.543,1.050),
                (-1.236,1.605,1.053,-1.301,2.484,1.014)]
    shell(stations,[None,.064,None,None],front_inset=.065,rear_inset=0)
    body_loft('Cab-over crown','paint',[(Y,Z-.014,Z+.061,X+.013) for _,_,_,Y,Z,X in stations])
    box('Cab full-width dashboard','black',(0,-3.048,1.629),(1.947,.282,.168),.060)
    box('Right-hand instrument housing','black',(-.535,-2.996,1.746),(.455,.239,.121),.037)
    steer(-.544,-2.851,1.777,.170)
    for s in (-1,1):
        chair(s*.532,-2.461,1.629,.448,.510)
        mirror(s*1.246,-3.004,1.955,s,.235,True)
        box('Cab aluminium access step','metal',(s*1.048,-2.810,.593),(.204,.425,.116),.030)
        box('Door handle pocket','black',(s*1.112,-1.958,1.472),(.026,.176,.059),.013)
        box('Door pull','metal',(s*1.127,-1.960,1.477),(.012,.127,.022),.007)
        line('Cab door edge','black',symmetry([(1.098,-1.785,1.604),(1.114,-1.781,1.488),
             (1.116,-1.793,.703),(1.094,-1.850,.542)],s),.005,6)
        line('Parked cab wiper','black',[(s*.756,-3.282,1.667),(s*.597,-3.275,1.702),
             (s*.198,-3.251,1.746)],.011,8)
        box('Cab headlight housing','black',(s*.779,-3.301,.998),(.349,.155,.258),.053)
        box('Main lorry headlight lens','lamp',(s*.779,-3.382,1.034),(.250,.025,.096),.019)
        box('Below-headlamp indicator','amber',(s*.779,-3.382,.935),(.241,.023,.050),.012)
    box('Cab main black grille','black',(0,-3.344,1.064),(1.103,.086,.359),.061)
    for z in [.966,1.032,1.098,1.164]:
        box('Lorry grille slat','metal',(0,-3.392,z),(.927,.017,.017),.005)
    box('Lorry front bumper','black',(0,-3.314,.599),(1.942,.217,.194),.062)
    sign('Lorry nose fleet mark','SELAT KARGO','ivory',(0,-3.344,1.384),.091,1.35,(0,-1,0))
    plate('JQX 7306',-3.434,.639,True,.441,.116)


if __name__ == '__main__':
    reset()
    cargo_lorry()
    finish('Selat Kargo Canvas Lorry', 6.68, (0, -0.09, 1.5), (-1.74, -1.56, 0.66), 1.12)
