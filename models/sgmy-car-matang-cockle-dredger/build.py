"""sgmy-car-matang-cockle-dredger — Small Perak cockle boat with a suspended rake and working winch.

Original procedural SG/MY vehicle, with fictional service markings and no external assets.
Rebuild: blender -b --factory-startup --python-exit-code 1 --python build.py
Append -- --export-only to omit the preview. Metres, base pivot, nose -Y (+Z in glTF).
Static prop, UV-unwrapped, material batched; requires a Draco-capable loader.
"""
# Primitive, glazing, batching and studio helpers adapted from Round 1–3 vehicles.
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
    obj['steering'] = 'Starboard helm'
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


def band(name,key,rows):
    # Loft adjacent mirrored waterlines. Each row is (station Y, half-breadth, height).
    a,b=rows
    for s in (-1,1):
        v=[(s*w,y,z) for row in (a,b) for y,w,z in row]; n=len(a)
        f=[(j,j+n,j+n+1,j+1) for j in range(n-1)]
        mesh(name,v,[tuple(reversed(p)) if s==1 else p for p in f],key)


def vessel(stations,chine=.67,boot=True,planks=True):
    # Stations: longitudinal position, sheer half-beam, deck height, keel height.
    # Shared edges between the coloured strakes avoid decals floating off the curved hull.
    levels=[(.12,0,'bottom'),(.54,.18,'bottom'),(.86,chine*.77,'paint'),(.94,chine,'ivory' if boot else 'paint'),(.949,chine+.045,'paint'),(.994,.927,'trim'),(1,1,'deck')]
    rows=[[(y,w*k,z+(h-z)*f) for y,w,h,z in stations] for k,f,_ in levels]
    for j in range(len(rows)-1):band('Hull strake',levels[j][2],(rows[j],rows[j+1]))
    for j in [0,-1]:
        # Transom and stem caps, split at the paint break.
        for i in range(len(rows)-1):
            a,b=rows[i][j],rows[i+1][j]; face('Transom strake',levels[i][2],[(-a[1],a[0],a[2]),(a[1],a[0],a[2]),(b[1],b[0],b[2]),(-b[1],b[0],b[2])],(0,1 if j==-1 else -1,0))
    for row,key,norm in [(rows[0],'bottom',-1),(rows[-1],'deck',1)]:
        for (y,w,z),(Y,W,Z) in zip(row,row[1:]):face('Deck or keel panel',key,[(-w,y,z),(w,y,z),(W,Y,Z),(-W,Y,Z)],(0,0,norm))
    for s in (-1,1):line('Continuous rubbing wale','black',[(s*w*.999,y,z-.047) for y,w,z in rows[-1]],.041)
    if planks:
        for (y,w,z),(Y,W,Z) in zip(rows[-1],rows[-1][1:]):
            n=math.ceil((Y-y)/.185)
            for i in range(1,n+1):
                t=i/(n+1); d=(w+(W-w)*t)*.982; yy=y+(Y-y)*t; zz=z+(Z-z)*t
                rod('Caulked deck seam','wood',(-d,yy,zz),(d,yy,zz),.009,6)


def crown(name,key,x,y0,y1,w,z,rise,lip=.075,taper=.95):
    # Barrel-cambered sheet roof, with thin fascia and a shallow crown.
    cross=[(-1,0),(-.83,.52),(-.44,.88),(0,1),(.44,.88),(.83,.52),(1,0)]
    profile=cross+[(a,b-lip/rise) for a,b in reversed(cross)]; n=len(profile)
    v=[(x+a*w*k,y,z+b*rise+dz) for y,k,dz in [(y0,taper,0),(y0+.18,1,.018),(y1-.18,1,.018),(y1,taper,0)] for a,b in profile]
    f=[tuple(reversed(range(n))),tuple(range(3*n,4*n))]+[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(3) for i in range(n)]
    bevel(mesh(name,v,f,key,recalc=True),.014)


def house(y0,y1,w,z,sill,roof,n,base='ivory',top='paint',slope=.25):
    box('Wheelhouse coaming',base,(0,(y0+y1)/2,(sill+z)/2),(2*w,y1-y0,sill-z),.065)
    stations=[(y0+(y1-y0)*i/n,sill,w,y0+slope+(y1-y0-slope-.10)*i/n,roof,w-.075) for i in range(n+1)]
    shell(stations,[.12]*n,.09,.16,base)
    crown('Cambered coachroof',top,0,y0+slope-.22,y1+.13,w+.12,roof,.105)
    for s in (-1,1):
        box('Waist moulding',top,(s*w,(y1+y0)/2,sill-.065),(.036,y1-y0-.07,.055),.015)
    # Starboard helm, wheel and dashboard inside the glazing.
    box('Instrument console','black',(-w*.5,y0+.36,sill-.005),(w*.71,.32,.16),.04)
    steer(-w*.5,y0+.54,sill+.14,.19); chair(-w*.5,y0+1.01,sill-.20,.49,.45)


def ferry_ring(s,x,y,z):
    ring('Rescue buoy','warm',(s*x,y,z),(1,0,0),.26,.058)
    for i in range(4):
        a=TAU*(i+.5)/4; b=a+.32
        line('Rescue buoy binding','ivory',[(s*x,y+.26*math.cos(t),z+.26*math.sin(t)) for t in (a,(a+b)/2,b)],.061,12)


def bitt(x,y,z,scale=1):
    box('Bollard base','metal',(x,y,z+.02),(.42*scale,.25*scale,.04),.018)
    for dx in (-.12,.12):
        pin('Mooring bitt','black',x+dx*scale,y,z+.12*scale,.062*scale,.24*scale);pin('Bitt head','black',x+dx*scale,y,z+.24*scale,.087*scale,.039*scale)


def rail(pts,h=.57):
    for x,y,z in pts:rod('Stanchion','metal',(x,y,z),(x,y,z+h),.024)
    for k in (.49,1):line('Safety rail','metal',[(x,y,z+h*k) for x,y,z in pts],.018 if k<1 else .032)


def mast(x,y,z,h):
    rod('Navigation mast','metal',(x,y,z),(x,y+.12,z+h),.046)
    rod('Signal yard','metal',(x-.46,y+.09,z+.72*h),(x+.46,y+.09,z+.72*h),.034)
    for s,key in [(-1,'paint'),(1,'red')]:pin('Running light',key,x+s*.41,y+.09,z+.72*h+.05,.065,.10)
    pin('Masthead lens','lamp',x,y+.12,z+h,.068,.13)


def legend(name,sub,x,y,z,w,h,s,key='ivory',board='paint'):
    box('Signboard',board,(s*x,y,z),(.038,w,h),.017)
    sign('Vessel name',name,key,(s*(x+.021),y,z+h*.11),h*.41,w*.9,(s,0,0))
    sign('Service and home port',sub,key,(s*(x+.021),y,z-h*.28),h*.17,w*.88,(s,0,0))


def coil(x,y,z,r=.25):
    for i in range(3):ring('Coiled hawser','rope',(x,y,z+.02),(0,0,1),r-i*.043,.023)


def drum(x,y,z,w,r,key='wood'):
    rod('Winding drum',key,(x-w/2,y,z),(x+w/2,y,z),r,28)
    for s in (-1,1):
        rod('Reel flange','trim',(x+s*w*.50,y,z),(x+s*(w*.50+.055),y,z),r*1.25,32)
        box('Axle pedestal','paint',(x+s*(w*.5+.084),y,z-r*.5),(.13,r*.9,r*1.26),.045)
    for i in range(18):ring('Cable turns','rope',(x+w*((i+.5)/18-.5),y,z),(1,0,0),r,.021)


def build():
    reset(); palette('294B81','35A99F','B59164','FA9A34')
    vessel([(-4.65,.08,1.43,.49),(-4.11,.97,1.24,.22),(-3.26,1.56,1.07,0),(-2.30,1.78,1.01,0),(2.64,1.78,1.01,0),(3.91,1.51,1.10,.16),(4.52,1.14,1.21,.26)],.55)
    house(1.03,3.48,1.32,1.00,1.85,2.73,3,'trim','ivory')
    for s in (-1,1):
        legend('MATANG','PERAK   /   KERANG  06',1.335,2.27,1.48,1.93,.48,s,'ivory','paint');ferry_ring(s,1.39,3.17,1.85)
        rail([(s*1.42,3.49,1.09),(s*1.21,4.16,1.16)],.52)
        # A hinged shear leg and the chain that supports the dredge basket.
        line('Dredging gantry','warm',[(s*1.47,-2.38,1.08),(s*1.13,-2.49,3.58),(s*1.49,-1.32,1.04)],.075)
        rod('Gantry heel pin','metal',(s*1.38,-2.38,1.18),(s*1.57,-2.38,1.18),.13)
        rod('Gantry stay','black',(s*1.13,-2.49,3.53),(s*1.49,.89,1.07),.022)
    rod('Derrick crosshead','trim',(-1.18,-2.49,3.56),(1.18,-2.49,3.56),.122)
    for x in (-.63,.63):
        rod('Sheave','black',(x-.06,-2.49,3.53),(x+.06,-2.49,3.53),.18)
        line('Lift wire','black',[(x,.47,1.59),(x,-2.45,3.68),(x,-2.72,2.07)],.021)
    drum(0,.47,1.48,1.27,.32)
    # Open rod basket: square lip, spaced longitudinal teeth, curved belly.
    for y,z in [(-3.17,1.48),(-2.24,1.49),(-2.50,1.09)]:rod('Basket tie bar','metal',(-.91,y,z),(.91,y,z),.052)
    for i in range(19):
        x=-.9+i*.1
        line('Cockle rake tine','metal',[(x,-3.39,1.36),(x,-3.17,1.48),(x,-2.83,1.08),(x,-2.50,1.09),(x,-2.22,1.26),(x,-2.24,1.49)],.024)
    for s in (-1,1):line('Rake bridle','black',[(s*.88,-3.17,1.48),(s*.63,-2.72,2.07),(s*.88,-2.24,1.49)],.026)
    # Slatted harvest boxes stacked on the working deck.
    for x,y,count in [(-1.0,-.38,2),(.93,-.45,2),(0,-1.16,1)]:
        for j in range(count):
            z=1.04+j*.39; key='trim' if j==0 else 'warm'
            box('Crate floor',key,(x,y,z+.036),(.74,.94,.07),.02)
            for s in (-1,1):
                for k in range(3):
                    box('Crate side slat',key,(x+s*.35,y,z+.105+.10*k),(.046,.92,.074),.012)
                    box('Crate end slat',key,(x,y+s*.45,z+.105+.10*k),(.68,.046,.074),.012)
                for t in (-1,1):box('Crate corner',key,(x+s*.334,y+t*.43,z+.18),(.061,.062,.36),.012)
    bitt(0,-3.85,1.19); mast(-.48,2.83,2.86,.93); coil(.57,3.82,1.12)
    finish('Matang Cockle Dredger',9.3,(0,0,1.66),(-1,-.75,.65))


if __name__ == '__main__':
    build()
