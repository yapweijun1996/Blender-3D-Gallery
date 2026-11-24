"""Kota Link Heartland City Bus | original procedural SG/MY game asset.

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


def city_bus():
    standard()
    material('paint','Kota Link deep lagoon paint','008677',.36,.14)
    material('roof','Warm porcelain upper panels','E1EEDD',.35,.10)
    material('accent','Lime belt and fleet vinyl','BEEA48',.45)
    material('display','Warm amber destination LEDs','FFAF42',.37,emission=.86)
    material('rail','Mustard safety rails','F3CF47',.40)
    material('dot','Dark jade seat backs','21575B',.48)
    # Turn the loft's upper edge inward to a true low-floor U section.
    section = [(.85,0),(.955,.042),(1,.14),(1,.91),(.99,.977),(.93,1),(.885,1),(.866,.277)]
    profile = [(-5.67,.40,1.359,1.074),(-5.615,.335,1.362,1.177),(-5.490,.298,1.37,1.239),
               (-5.27,.29,1.369,1.252),(5.25,.32,1.369,1.252),(5.49,.353,1.369,1.236),(5.63,.43,1.368,1.14)]
    body = body_loft('Low-floor monocoque and shaped bumpers','paint',profile,section)
    wheels_at = (-3.58,2.49)
    wells(body,wheels_at,.478,.559,1.251,.35)
    wheels(wheels_at,1.085,.478,.267,'lorry')
    for x in (-.81,.81):
        wheel(2.49,x,.478,.198,-1 if x<0 else 1,'lorry')
    # Continuous roof cap, tilted front screen and gently sloped rear header.
    Y = [-5.63,-5.39,-5.26,-4.04,-3.92,-2.34,-2.25,-1.62,-1.52,-.21,-.10,1.40,1.48,2.98,3.07,4.49,4.58,5.30,5.57]
    X = [1.067,1.203]+[1.243]*(len(Y)-4)+[1.214,1.103]
    roof_section = [(.93,0),(.994,.07),(1,.36),(.992,.60),(.964,.83),(.899,1)]
    top_y = [y+( .155 if i==0 else .075 if i==1 else -.108 if i==len(Y)-1 else 0) for i,y in enumerate(Y)]
    body_loft('Curved destination brow and roof','roof',
              [(y,2.643,2.964,x-.022) for x,y in zip(X,top_y)],roof_section)
    for s in (-1,1):
        for i, y in enumerate(Y[:-1]):
            y2 = Y[i+1]
            pts = [(s*X[i],y,1.36),(s*X[i+1],y2,1.36),
                   (s*(X[i+1]-.022),top_y[i+1],2.674),(s*(X[i]-.022),top_y[i],2.674)]
            if y2-y < .14 or i in (0,len(Y)-2):
                face('Charcoal window pillar','black',pts,(s,0,0))
            else:
                glazed('Tall passenger glazing',pts,(s,0,0),.065)
        stripe_x = s*1.254
        face('Unbroken lime waist stripe','accent',[(stripe_x,-5.27,1.246),(stripe_x,5.25,1.246),
                 (stripe_x,5.25,1.328),(stripe_x,-5.27,1.328)],(s,0,0))
        lo,hi = (-2.87,1.75) if s<0 else (.35,1.85)
        sign('Operator side wordmark','KOTA LINK','ivory',(s*1.257,(lo+hi)/2,1.018),.219,hi-lo,(s,0,0))
        sign('Transit side subline','BAS BANDAR','accent',(s*1.257,(lo+hi)/2,.778),.097,hi-lo,(s,0,0))
        for i in range(3):
            y = 3.51+i*.266
            face('Lime staggered route motif','accent',[(stripe_x,y,.796),(stripe_x,y+.18,.796),
                 (stripe_x,y+.33,1.171),(stripe_x,y+.158,1.171)],(s,0,0))
        for y,z in [(-4.19,.452),(-2.79,.499),(.84,.499),(4.78,.455)]:
            box('Amber side position light','amber',(s*1.256,y,z),(.022,.103,.043),.009)
        box('Shoulder-level mirror arm','black',(s*1.124,-5.50,2.663),(.435,.127,.076),.026)
        mirror(s*1.371,-5.54,2.460,s,.198,True)
        for yy in (3.45,4.62):
            box('Service hatch seam','black',(s*1.251,yy,.632),(.006,.014,.34))
    # Kerbside (+X) doors as tall two-leaf assemblies, opposite the driver.
    for lo,hi in [(-5.24,-4.055),(-1.514,-.223)]:
        center = (lo+hi)/2
        box('Kerbside door lower frame','black',(1.253,center,.918),(.032,hi-lo,1.024),.018)
        for a,b in [(lo,center), (center,hi)]:
            y = (a+b)/2
            box('Door foot kick plate','paint',(1.277,y,.593),(.024,b-a-.067,.274),.016)
            box('Lower door smoked infill','seat',(1.275,y,1.004),(.019,b-a-.069,.491),.017)
            box('Door safety marking','rail',(1.287,y,.778),(.011,b-a-.121,.030),.006)
        line('Door meeting stile','black',[(1.28,center,.448),(1.268,center,1.38),(1.233,center,2.61)],.026,8)
        box('Low-floor step edge','metal',(1.274,center,.424),(.105,hi-lo+.06,.074),.022)
    # Close the U-section at the nose and tail; the passenger well stays open above.
    face('Front centre apron','paint',[(-.952,-5.671,.66),(.952,-5.671,.66),
         (.952,-5.671,1.360),(-.952,-5.671,1.360)],(0,-1,0))
    face('Rear centre apron','paint',[(-1.011,5.631,.689),(1.011,5.631,.689),
         (1.011,5.631,1.369),(-1.011,5.631,1.369)],(0,1,0))
    # Use the lower part of the front windscreen for the real driver position.
    glazed('Panoramic windscreen',[(-1.067,-5.63,1.36),(1.067,-5.63,1.36),
           (1.045,-5.475,2.674),(-1.045,-5.475,2.674)],(0,-1,0),.040)
    glazed('Aft passenger window',[(-1.104,5.57,1.366),(1.104,5.57,1.366),
           (1.081,5.462,2.674),(-1.081,5.462,2.674)],(0,1,0),.12)
    box('Front destination sign cassette','black',(0,-5.559,2.474),(1.822,.104,.311),.040,tilt=(-.113,0,0))
    sign('Front route number','168','display',(-.633,-5.617,2.475),.162,.425,(0,-1,0))
    sign('Front route destination','PUSAT BANDAR','display',(.256,-5.617,2.496),.097,1.17,(0,-1,0))
    sign('Front route via','VIA  CAUSEWAY','display',(.253,-5.621,2.397),.048,.84,(0,-1,0))
    box('Kerbside LED board','black',(1.247,-2.78,2.401),(.064,1.337,.285),.036)
    sign('Kerbside route number','168','display',(1.281,-3.15,2.404),.134,.38,(1,0,0))
    sign('Kerbside route destination','PUSAT BANDAR','display',(1.281,-2.59,2.400),.055,.70,(1,0,0))
    box('Rear route pod','black',(0,5.593,2.419),(.684,.142,.293),.041)
    sign('Rear route number','168','display',(0,5.667,2.42),.172,.528,(0,1,0))
    box('Right driver dashboard','black',(-.57,-5.364,1.522),(.890,.451,.218),.052)
    box('Instrument cluster','seat',(-.589,-5.227,1.651),(.373,.139,.086),.020)
    chair(-.613,-4.74,1.313,.437,.510)
    steer(-.613,-5.077,1.648,.177)
    for y in [-3.48,-2.66,-1.84,-.05,.69,1.45,2.23,3.02,3.83,4.62]:
        for s in (-1,1):
            if s>0 and y in [-1.84,-.05]:
                continue
            h = 1.185 if y<1.4 else 1.330
            box('Passenger bench pedestal','black',(s*.791,y,.5*(h+.59)),(.245,.235,h-.59),.022,1)
            box('Passenger bench pad','seat',(s*.791,y,h),(.652,.401,.098),.026,1)
            box('Passenger bench shell','dot',(s*.791,y+.17,h+.251),(.658,.119,.467),.035,1,tilt=(.13,0,0))
    for y in [-3.71,-1.68,-.135,1.63,3.14,4.58]:
        rod('Standing grab rail','rail',(.389,y,.58),(.389,y,2.716),.018,8)
    for s in (-1,1):
        rod('Ceiling continuous hand rail','rail',(s*.382,-3.72,2.522),(s*.382,4.87,2.522),.018,8)
        line('Windscreen wiper','black',[(s*.87,-5.632,1.469),(s*.69,-5.610,1.571),(s*.23,-5.606,1.607)],.011,8)
        box('Dual headlamp housing','black',(s*.757,-5.631,.716),(.565,.158,.278),.062,tilt=(0,-s*.13,s*.064))
        box('Swept LED headlight','lamp',(s*.745,-5.711,.766),(.408,.028,.093),.024,tilt=(0,-s*.13,s*.064))
        box('Front directional lens','amber',(s*.907,-5.696,.663),(.129,.037,.052),.015,tilt=(0,-s*.13,s*.064))
        box('Rear pillar lamp housing','black',(s*.964,5.629,.966),(.188,.093,.520),.031)
        box('Rear tail and stop lens','red',(s*.964,5.677,1.047),(.131,.022,.277),.024)
        box('Rear indicator lens','amber',(s*.964,5.678,.834),(.129,.024,.080),.015)
    box('Front bumper inlet','black',(0,-5.673,.447),(1.231,.137,.115),.041)
    box('Lime front identity stripe','accent',(0,-5.669,1.238),(1.93,.018,.060),.011)
    sign('Front fleet wordmark','KOTA LINK','ivory',(0,-5.683,1.068),.139,1.01,(0,-1,0))
    box('Rear cooling grille','black',(0,5.64,.926),(1.443,.052,.418),.043)
    for z in [.798,.856,.914,.972,1.030,1.088]:
        box('Rear cooling louvre','seat',(0,5.668,z),(1.251,.017,.018),.004,1)
    plate('SBX 168K',-5.737,.576,True,.422,.115)
    plate('SBX 168K',5.678,.574,False,.423,.114)
    box('Roof refrigeration pack','roof',(0,1.07,3.014),(1.67,4.16,.266),.126,3)
    for y in [2.06,2.59]:
        box('Refrigeration fan shroud','black',(0,y,3.113),(1.05,.369,.032),.036)
        for yy in [y-.12,y-.06,y,y+.06,y+.12]:
            box('Refrigeration fan guard','seat',(0,yy,3.129),(.918,.023,.012),.003,1)


if __name__ == '__main__':
    reset()
    city_bus()
    finish('Kota Link Heartland City Bus', 11.48, (0, -0.18, 1.53), (1.72, -1.46, 0.62), 1.04)
