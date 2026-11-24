"""sgmy-car-taiping-road-grader — Six-wheel articulated grader with an angled curved moldboard, Perak.

Original static vehicle for SG/MY streets and waterways; fictional markings.
Self-contained rebuild: blender -b --factory-startup --python-exit-code 1 -P build.py
Append -- --export-only to skip the studio render. No downloads, textures or fonts needed.
Metres, grounded origin; nose -Y (+Z in glTF). UV-mapped PBR, Draco decoder required.
Geometry and studio helpers adapted from earlier SG/MY vehicles in this repository.
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
ASSET_ID = 'sgmy-car-taiping-road-grader'


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
    obj['origin_note'] = 'Vehicle base at ground datum, metres'
    obj['asset_id'] = ASSET_ID
    obj['bounds_m_xyz'] = list(obj.dimensions)
    obj['controls'] = 'Right-hand drive'
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
    cam.ortho_scale = max(hi_x-lo_x,(hi_y-lo_y)*1120/760)*1.13
    cam.clip_end = length*300
    scene.camera = camera
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 12
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
        export_draco_position_quantization=20,export_draco_texcoord_quantization=14)
    if result != {'FINISHED'}:
        raise RuntimeError(f'GLB export failed: {result}')
    options = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    if '--export-only' in options:
        return
    studio(length, target, direction, fill).render.filepath = str(out/'preview.png')
    bpy.ops.render.render(write_still=True)


def palette(paint, trim, deck='B78858', accent='E59F48'):
    standard()
    material('paint','Primary enamel',paint,.38,.12)
    material('trim','Coachwork enamel',trim,.37,.09)
    material('deck','Deck and fittings',deck,.65)
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


def build():
    reset();palette('DC9B3B','F9BE52','56616A','F3E2AF')
    rad=.625
    for y in (-3.45,1.77,3.37):
        wheels([y],1.03,rad,.39,'lorry');rod('Axle casing','black',(-1.01,y,rad),(1.01,y,rad),.12)
        for s in (-1,1):tread(y,s*1.03,rad,.39)
    for s in (-1,1):
        yz_prism('Tandem oscillating case','paint',s*.86,.21,[(1.52,.50),(1.49,.76),(2.42,1.06),(2.77,1.04),(3.63,.74),(3.62,.50),(2.54,.68)],.062)
        arm('Steering tie link','metal',(s*.83,-3.49,.66),(s*.41,-3.14,1.13),.067,.067)
    yz_prism('Swan-neck main frame','paint',0,.46,[(-3.98,.86),(-3.95,1.24),(-2.52,1.91),(-1.46,1.97),(.29,1.67),(.83,1.39),(.74,1.11),(-1.64,1.58),(-2.35,1.53),(-3.37,.91)],.067)
    box('Axle saddle','black',(0,-3.45,.86),(.86,.61,.34),.07)
    box('Rear backbone','black',(0,2.07,1.01),(1.24,3.85,.42),.092)
    yz_prism('Engine housing','paint',0,1.53,[(1.58,1.19),(1.64,2.15),(2.01,2.31),(3.33,2.18),(4.11,1.95),(4.17,1.29),(3.98,1.17)],.083)
    for s in (-1,1):
        vent(s,.773,3.37,1.73,.99,.55,11);legend('ARAS  60','TAIPING  /  PERAK',.781,2.23,1.85,1.05,.43,s,'black','paint')
    pin('Exhaust muffler','black',.43,2.60,2.57,.097,.72);pin('Exhaust tip','metal',.43,2.60,2.98,.065,.18)
    # Rear operator tower, independent of the angled front chassis.
    yz_prism('Operator platform','black',0,1.75,[(.02,1.24),(.12,1.48),(1.62,1.48),(1.64,1.20)],.036)
    cab(.12,.82,1.39,1.43,1.91,3.03,'trim',.04)
    for s in (-1,1):
        for j in range(3):box('Access ladder tread','metal',(s*(1.00-j*.056),.84,.65+j*.23),(.26,.44,.053),.014)
        line('Grab rail','black',[(s*.91,.57,1.37),(s*.91,.57,2.12),(s*.84,.66,2.15)],.029)
    pin('Rotating amber beacon','amber',.57,1.27,3.22,.091,.19)
    # Circle drive, triangular drawbar and concave tilted moldboard.
    pin('Circle turntable','black',0,-1.14,.78,.62,.17,40);ring('Circle bearing','metal',(0,-1.14,.707),(0,0,1),.53,.045)
    for s in (-1,1):
        boom((0,-3.35,1.02),(s*.54,-1.04,.85),'trim',.12,.15)
        boom((0,-1.36,1.86),(s*.67,-1.36,1.77),'paint',.13,.16)
        ram((s*.66,-1.36,1.78),(s*.60,-1.02,.74));boom((s*.45,-1.13,.78),(s*.72,-.95+s*.32,.46),'black',.12,.12)
    for key,pr in [('trim',[(-.18,.11),(-.08,.27),(-.04,.43),(-.075,.56),(-.20,.72),(-.13,.76),(.013,.59),(.06,.42),(.02,.26),(-.094,.12)]),('metal',[(-.22,.067),(-.155,.06),(-.07,.215),(-.135,.215)])]:
        o=yz_prism('Curved grading blade' if key=='trim' else 'Replaceable cutting edge',key,0,3.24,pr,.017);o.location.y=-1.14;o.rotation_euler.z=.38
    rod('Front work light bridge','black',(-.77,-3.63,1.34),(.77,-3.63,1.34),.046)
    for s in (-1,1):box('Work lamp','lamp',(s*.70,-3.66,1.40),(.17,.13,.13),.026)
    lampbar(4.15,1.48,.56);finish('Taiping Road Grader',8.3,(0,0,1.54),(1,-.69,.43))


def arm(name,key,a,b,w,h):
    a,b=Vector(a),Vector(b);o=box(name,key,(a+b)*.5,(w,h,(b-a).length),min(w,h)*.095);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o


def yz_prism(name,key,x,w,profile,rad=0):
    n=len(profile);vs=[(x+s*w/2,y,z) for s in (-1,1) for y,z in profile];f=[tuple(range(n)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return bevel(mesh(name,vs,f,key,recalc=True),rad)


def cab(y, w, depth, floor, belt, top, key='paint', overhang=.32):
    """Short glazed driving compartment. Front edge at y; controls on driver's right."""
    d=depth
    rows=[(y,floor+.08,belt-.04,w*.89),(y+.12,floor,belt,w),(y+d-.13,floor,belt,w),(y+d,floor+.04,belt,w*.96)]
    body_loft('Pressed cab waist',key,rows)
    stations=[(y,belt-.04,w*.89,y+overhang,top-.05,w*.85),(y+.12,belt,w,y+overhang+.13,top,w*.93),(y+d*.68,belt,w,y+d*.69,top,w*.93),(y+d,belt,w*.96,y+d-.08,top-.03,w*.91)]
    shell(stations,[None,.075,.17],.075,.23,key)
    body_loft('Pressed roof crown',key,[(Y-.012,Z-.015,Z+.09,X+.04) for _,_,_,Y,Z,X in stations]);box('Driver console','black',(0,y+.25,belt+.034),(w*1.66,.28,.14),.048)
    steer(-w*.48,y+.46,belt+.15,.16);chair(-w*.47,y+depth*.58,belt-.23,.45,.46)
    for s in (-1,1):
        mirror(s*(w+.12),y+.29,belt+.27,s,.19,True)
        box('Cab entry grip','black',(s*(w+.006),y+d*.61,belt-.13),(.03,.17,.049),.012)
        box('Front lamp surround','black',(s*w*.68,y-.008,belt-.27),(w*.34,.068,.155),.025)
        box('Lamp lens','lamp',(s*w*.68,y-.045,belt-.255),(w*.27,.011,.084),.004)
        box('Turn indicator','amber',(s*w*.68,y-.045,belt-.322),(w*.22,.012,.026),.005)
    box('Cooling intake','black',(0,y-.009,belt-.26),(w*.75,.077,.22),.03)
    for j in range(3):box('Intake slat','metal',(0,y-.05,belt-.32+.06*j),(w*.68,.016,.016),.004)
    box('Impact beam','black',(0,y-.012,floor+.075),(w*1.85,.13,.14),.042)


def tread(y,x,r,w):
    """Chevron tyre shoulder lugs; outer envelope tangent to ground at nominal radius."""
    for j in range(28):
        a=(j+.5)*TAU/28
        for s in (-1,1):
            def pt(xx,t):return (x+xx,y+(r-.014)*math.cos(t),(r+.012)+(r-.014)*math.sin(t))
            arm('Chevron lug','tire',pt(s*.015,a-.043),pt(s*w*.47,a+.054),.040,.040)


def vent(s,x,y,z,w,h,n):
    box('Recessed ventilation opening','black',(s*x,y,z),(.031,w,h),.014)
    for j in range(n):box('Stamped vertical louvre','metal',(s*(x+.023),y+w*((j+.5)/n-.5),z),(.021,w/n*.26,h*.84),.007,tilt=(-.12,0,0))


def lampbar(y,z,half):
    for s in (-1,1):
        box('Rear optic housing','black',(s*half,y,z),(.32,.12,.135),.028)
        box('Tail lens','red',(s*(half+.05),y+.062,z),(.16,.021,.092),.009)
        box('Turn lens','amber',(s*(half-.081),y+.062,z),(.073,.022,.09),.009)


def boom(a,b,key='trim',w=.18,h=.21):
    return arm('Fabricated box boom',key,a,b,w,h)


def ram(a,b,r=.09):
    a,b=Vector(a),Vector(b);q=a.lerp(b,.57)
    rod('Hydraulic ram barrel','paint',a,q,r);rod('Ground piston rod','metal',q,b,r*.58)


if __name__ == '__main__':
    build()
