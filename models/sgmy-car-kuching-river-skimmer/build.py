"""Kuching River Skimmer | SG/MY vehicle series, revision 1.
Twin-pontoon debris collector with guide wings, an inclined cleated belt and a slatted catch basket.
Rebuild: blender -b --factory-startup --python-exit-code 1 --python build.py
Pass -- --export-only to skip the still. Optional preview optimizer: python3/Pillow.
Metres; base origin; nose -Y Blender, +Z glTF. Right-hand controls.
Static UV-mapped material batches; Draco decoder required. Original design,
no external artwork. Studio and fabrication helpers adapted from the gallery series.
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


def pin(name,key,x,y,z,r,h,n=24):
    return rod(name,key,(x,y,z-h/2),(x,y,z+h/2),r,n)


def ring(name,key,center,normal,r,t,n=32):
    q=Vector(normal).to_track_quat('Z','Y'); c=Vector(center); m=8
    verts=[c+q@Vector(((r+t*math.cos(TAU*j/m))*math.cos(TAU*i/n),(r+t*math.cos(TAU*j/m))*math.sin(TAU*i/n),t*math.sin(TAU*j/m))) for i in range(n) for j in range(m)]
    obj=mesh(name,verts,[(i*m+j,((i+1)%n)*m+j,((i+1)%n)*m+(j+1)%m,i*m+(j+1)%m) for i in range(n) for j in range(m)],key,recalc=True)
    for p in obj.data.polygons:p.use_smooth=True
    return obj


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


def mast(x,y,z,h):
    rod('Navigation mast','metal',(x,y,z),(x,y+.12,z+h),.046)
    rod('Signal yard','metal',(x-.46,y+.09,z+.72*h),(x+.46,y+.09,z+.72*h),.034)
    for s,key in [(-1,'paint'),(1,'red')]:pin('Running light',key,x+s*.41,y+.09,z+.72*h+.05,.065,.10)
    pin('Masthead lens','lamp',x,y+.12,z+h,.068,.13)


def arm(name,key,a,b,w,h):
    a,b=Vector(a),Vector(b); o=box(name,key,(a+b)*.5,(w,h,(b-a).length),.037);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o


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


CAR_SECTION = [(.84,0),(.96,.07),(1,.22),(1,.70),(.986,.86),(.947,.97),(.904,1)]


def mix(a,b,t):
    return a+(b-a)*t


def station_at(profile,y):
    for (a,b,c,d),(e,f,g,h) in zip(profile, profile[1:]):
        if y <= e:
            t = max(0,(y-a)/(e-a))
            return mix(b,f,t),mix(c,g,t),mix(d,h,t)
    return profile[-1][1:]


def side_x(profile, section, y, z):
    low, high, wide = station_at(profile,y)
    nz = max(0,min(1,(z-low)/(high-low)))
    for (a,b),(c,d) in zip(section,section[1:]):
        if nz <= d:
            return wide*mix(a,c,(nz-b)/(d-b))
    return wide*section[-1][0]


def body_side(name,key,profile,side,yz,section=CAR_SECTION,offset=.004):
    return face(name,key,[(side*(side_x(profile,section,y,z)+offset),y,z) for y,z in yz],(side,0,0))


def labels(s,x,y,z,main,sub,width,height,key='ivory',sub_key=None):
    sign('Side fleet title',main,key,(s*x,y,z),height,width,(s,0,0))
    if sub:
        sign('Side fleet subtitle',sub,sub_key or key,(s*x,y,z-height*1.05),height*.42,width,(s,0,0))


def beam(name,key,a,b,width,depth=None):
    d=Vector(b)-Vector(a)
    obj=box(name,key,(Vector(a)+Vector(b))*.5,(width,depth or width,d.length),min(width*.12,.028))
    obj.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    return obj


def colors(**kwargs):
    standard()
    for name,(label,color) in kwargs.items():
        material(name,label,color,.38,.12)


def shift(start, dx=0, dy=0, dz=0):
    for ob in ART[start:]:
        ob.location += Vector((dx,dy,dz))


def plank(name,key,side,x,points,thickness):
    n=len(points)
    vertices=[(side*(x+t),y,z) for t in (0,thickness) for y,z in points]
    faces=[tuple(range(n)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return bevel(mesh(name,vertices,faces,key,recalc=True),.012)


def board_side(s,x,y,z,w,h,title,sub,base='paint',ink='ivory'):
    box('Screen printed fleet panel',base,(s*x,y,z),(.035,w,h),.015)
    labels(s,x+.020,y,z+h*.12,title,sub,w*.91,h*.42,ink)


def build():
    colors(paint=('Estuary blue hull enamel','256677'),mint=('Sea glass wheelhouse','BCDFCF'),warm=('Coral marking enamel','EE8553'),belt=('Graphite belting','37484C'))
    p=[(-4.21,.64,1.07,.08),(-3.96,.46,1.09,.28),(-3.30,.13,1.04,.405),(-2.62,0,1.02,.419),(2.9,0,1.02,.419),(3.81,.14,1.07,.396),(4.08,.28,1.08,.352)]
    sec=[(.48,0),(.84,.14),(1,.51),(1,.90),(.95,1)]
    for s in (-1,1):
        start=len(ART);body_loft('Chined collector pontoon','paint',p,sec)
        for a,b in zip(p,p[1:]):
            body_side('Pontoon coral cove stripe','warm',p,s,[(a[0],.77),(b[0],.77),(b[0],.843),(a[0],.843)],sec)
        shift(start,s*1.39)
        for y in (-2.85,-1.14,.64,2.47,3.65):box('Rubbing block','black',(s*1.793,y,.91),(.129,.60,.129),.044)
        bitt(s*1.39,-2.81,1.04,.80);bitt(s*1.39,3.77,1.08,.80)
        # Hinged guide wing funnels floating litter to the leading roller.
        plank('Collection wing','warm',s,1.03,[(-4.27,.27),(-4.26,.85),(-2.94,1.00),(-2.58,.52)],.085)
        for j in range(5):rod('Wing deflector tine','metal',(s*1.066,-4.13+j*.26,.51+j*.044),(s*1.066,-4.24+j*.26,.282+j*.048),.019)
    box('Transverse working deck','mint',(0,1.29,1.015),(3.55,5.48,.165),.045)
    a,b=Vector((0,-4.04,.44)),Vector((0,-.12,2.02))
    arm('Inclined collection belt','belt',a,b,1.89,.12)
    for i in range(22):
        c=a.lerp(b,(i+.35)/22)
        box('Transverse cleat','metal',(0,c.y,c.z+.092),(1.87,.045,.097),.013,tilt=(.38,0,0))
    for s in (-1,1):
        arm('Belt side frame','warm',(s*1.015,a.y,a.z-.02),(s*1.015,b.y,b.z-.02),.114,.177)
        for y,z in [(-3.99,.44),(-.16,2.01)]:rod('Pulley boss','metal',(s*.943,y,z),(s*1.109,y,z),.119,20)
        beam('Belt support leg','paint',(s*.97,-.46,1.058),(s*1.012,-.14,1.99),.086)
    # Open-top removable basket behind discharge drum; gaps make fill level visible.
    box('Basket base','paint',(0,.75,1.148),(2.15,1.68,.115),.033)
    for x in (-1.04,1.04):
        for y in (-.062,1.57):box('Basket corner','paint',(x,y,1.59),(.082,.082,.95),.014)
        for j in range(5):box('Basket side louvre','mint',(x,.75,1.27+j*.158),(.042,1.65,.102),.015)
        box('Rolled basket lip','paint',(x,.75,2.035),(.099,1.73,.095),.028)
    for y in (-.062,1.57):
        for j in range(5):box('Basket end louvre','mint',(0,y,1.27+j*.158),(2.09,.045,.102),.012)
    house(1.76,3.73,1.25,1.096,1.92,2.87,2,'mint','paint',.23)
    for s in (-1,1):
        ferry_ring(s,1.30,3.10,1.69)
        board_side(s,1.802,-.25,.665,2.38,.39,'SUNGAI BERSIH','KUCHING  /  SK-09','paint','mint')
        for y in (-1.38,-.64,.25,1.19,1.75):rod('Safety rail stanchion','metal',(s*1.67,y,1.077),(s*1.67,y,1.61),.023)
        for z in (1.34,1.61):rod('Safety rail','metal',(s*1.67,-1.38,z),(s*1.67,1.75,z),.022)
    mast(0,3.33,2.99,.69);finish('Kuching River Skimmer',8.6,(0,0,1),(-1.18,-1.32,.84))


if __name__ == '__main__':
    reset(); build()
