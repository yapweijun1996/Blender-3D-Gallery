"""Semporna Reef Outrigger | original SG/MY vehicle | revision 1
A day-dive outrigger launch with lashed twin floats, cylinder rack, a starboard helm and a stern swim ladder.
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


TRUCK_SECTION=[(.89,0),(.98,.08),(1,.24),(1,.83),(.983,.95),(.963,1)]


def beam(name,key,a,b,width,depth=None):
    d=Vector(b)-Vector(a)
    obj=box(name,key,(Vector(a)+Vector(b))*.5,(width,depth or width,d.length),min(width*.12,.028))
    obj.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    return obj


def slash(name,key,x,y,z,w,h,skew,s):
    face(name,key,[(s*x,y,z),(s*x,y+w,z),(s*x,y+w+skew,z+h),(s*x,y+skew,z+h)],(s,0,0))


def oval(name,key,loc,sizes,n=16,rows=8):
    x,y,z=loc; a,b,c=sizes
    v=[(x,y,z-c)]+[(x+a*math.cos(t*math.pi/rows)*math.cos(i*TAU/n),y+b*math.cos(t*math.pi/rows)*math.sin(i*TAU/n),z+c*math.sin(t*math.pi/rows)) for t in [j-rows/2 for j in range(1,rows)] for i in range(n)]+[(x,y,z+c)]
    f=[(0,1+(i+1)%n,1+i) for i in range(n)]+[(1+j*n+i,1+j*n+(i+1)%n,1+(j+1)*n+(i+1)%n,1+(j+1)*n+i) for j in range(rows-2) for i in range(n)]+[(len(v)-1,len(v)-1-n+i,len(v)-1-n+(i+1)%n) for i in range(n)]
    o=mesh(name,v,f,key,recalc=True)
    for p in o.data.polygons: p.use_smooth=True
    return o


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


def bitt(x,y,z,scale=1):
    box('Bollard base','metal',(x,y,z+.02),(.42*scale,.25*scale,.04),.018)
    for dx in (-.12,.12):
        pin('Mooring bitt','black',x+dx*scale,y,z+.12*scale,.062*scale,.24*scale);pin('Bitt head','black',x+dx*scale,y,z+.24*scale,.087*scale,.039*scale)


def legend(name,sub,x,y,z,w,h,s,key='ivory',board='paint'):
    box('Signboard',board,(s*x,y,z),(.038,w,h),.017)
    sign('Vessel name',name,key,(s*(x+.021),y,z+h*.11),h*.41,w*.9,(s,0,0))
    sign('Service and home port',sub,key,(s*(x+.021),y,z-h*.28),h*.17,w*.88,(s,0,0))


def tube(name,key,stations):
    verts=[];n=24
    for j,(x,y,z,r) in enumerate(stations):
        a=Vector(stations[max(0,j-1)][:2]);b=Vector(stations[min(j+1,len(stations)-1)][:2]);d=(b-a).normalized();normal=Vector((d.y,-d.x,0))
        verts += [Vector((x,y,z))+r*(normal*math.cos(TAU*i/n)+Vector((0,0,math.sin(TAU*i/n)))) for i in range(n)]
    N=len(verts);f=[tuple(range(n)),tuple(range(N-n,N))]+[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(stations)-1) for i in range(n)]
    o=mesh(name,verts,f,key,recalc=True)
    for p in list(o.data.polygons)[2:]:p.use_smooth=True


def build():
    palette('197D86','DA6646','CA9A6C','F5BA50'); material('hood','Indigo awning duck','35516B',.68);material('bamboo','Sealed bamboo spar','D4AD72',.52)
    stations=[(-4.31,.043,1.29,.85),(-3.68,.43,1.01,.40),(-2.83,.75,.86,.145),(-1.68,.96,.79,.032),(-.83,1.025,.78,0),(1.87,1.025,.78,0),(2.90,.88,.78,.085),(3.53,.68,.81,.22)]
    vessel(stations,.62,True,True)
    for y in (-1.75,1.83):
        rod('Main transverse spar','bamboo',(-1.14,y,.89),(1.14,y,.89),.087,20)
        for s in (-1,1):
            line('Bent outrigger strut','bamboo',[(s*.86,y,.89),(s*1.71,y,.93),(s*2.12,y,.75),(s*2.47,y,.43)],.075,16)
            beam('Outrigger knee brace','wood',(s*.91,y+.39,.83),(s*2.15,y,.70),.065)
            for k in range(4): ring('Spar seizing','rope',(s*(.88+.030*k),y,.89),(1,0,0),.09,.012,16)
    for s in (-1,1):
        st=[(s*2.47,y,z,r) for y,z,r in [(-3.45,.57,.020),(-3.19,.44,.082),(-2.78,.31,.131),(-2.01,.27,.147),(2.14,.27,.147),(2.80,.30,.116),(3.10,.355,.063),(3.22,.38,.021)]]
        tube('Double-ended stabiliser float','ivory',st)
        for y in (-1.75,1.83):
            for j in range(4):ring('Float binding','trim',(s*2.47,y-.074+.050*j,.27),(0,1,0),.149,.017,20)
        for y in (-1.95,1.41):
            rod('Awning stanchion','metal',(s*.81,y,.80),(s*.78,y+.18,2.36),.037,12)
            beam('Awning strut knee','metal',(s*.81,y+.14,1.90),(s*.78,y+(.56 if y<0 else -.22),2.35),.038)
        legend('TERUMBU  06','SEMPORNA   /   SELAM',1.018,.40,.612,1.94,.249,s,'ivory','paint')
        # White-over-coral name flash beside the wheelhouse.
        for j in range(3):slash('Reef pennant','warm',1.027,1.46+j*.118,.58,.067,.13,-.091,s)
    crown('Canvas shade fly','hood',0,-2.04,1.82,1.01,2.385,.17,.053)
    for s in (-1,1):rod('Awning edge binding','warm',(s*1.006,-1.88,2.385),(s*1.006,1.65,2.385),.023)
    box('Starboard helm console','ivory',(-.39,-1.38,1.12),(.68,.55,.67),.08)
    glazed('Helm spray shield',[(-.738,-1.66,1.45),(-.045,-1.66,1.45),(-.081,-1.52,1.81),(-.71,-1.52,1.81)],(0,-1,0),.105)
    steer(-.40,-1.01,1.47,.14);chair(-.40,-.61,1.12)
    box('Helm pedestal','paint',(-.40,-.61,.96),(.34,.32,.34),.03)
    box('Port diver bench locker','ivory',(.59,-.12,.99),(.47,2.57,.38),.055)
    box('Bench slat top','wood',(.59,-.12,1.19),(.49,2.58,.061),.022)
    for j in range(5):
        y=.02+j*.35; x=-.60
        pin('Cylinder boot','black',x,y,.906,.13,.235)
        pin('Brushed dive cylinder','metal',x,y,1.253,.124,.61)
        oval('Cylinder shoulder','warm',(x,y,1.55),(.124,.124,.100))
        pin('Pillar valve','metal',x,y,1.674,.048,.094,12)
        rod('Valve handwheel','black',(x,y,1.688),(x+.117,y,1.688),.038,12)
        ring('Cylinder restraint','hood',(x,y,1.36),(0,0,1),.126,.016,20)
    for z in (.98,1.36):beam('Tank rack cross rail','metal',(-.77,-.15,z),(-.77,1.64,z),.043)
    for y in (-.16,1.66):beam('Tank rack foot','metal',(-.77,y,.78),(-.77,y,1.45),.050)
    # Aft propulsion well and dive ladder stored above the keel.
    box('Outboard bracket','metal',(-.20,3.52,.81),(.42,.28,.16),.039)
    box('Outboard cowling','hood',(-.20,3.78,.99),(.43,.57,.47),.139,3)
    box('Outboard leg','black',(-.20,3.78,.50),(.15,.24,.63),.054)
    for x in (.31,.65):line('Boarding ladder rail','metal',[(x,3.20,.84),(x,3.45,1.07),(x,3.69,.99),(x,3.69,.30)],.030)
    for j in range(3):rod('Boarding ladder rung','metal',(.31,3.69,.39+j*.21),(.65,3.69,.39+j*.21),.026)
    bitt(0,-3.12,.955,.75)
    ring('Flotation ring','trim',(.70,2.00,1.25),(1,0,0),.239,.072)
    for y in (1.80,2.20):rod('Ring cradle','metal',(.70,y,.78),(.70,y,1.22),.027)


if __name__ == '__main__':
    reset()
    build()
    finish('Semporna Reef Outrigger', 8.4,(0,0,1.4),(-1.54,-1.07,.91))
