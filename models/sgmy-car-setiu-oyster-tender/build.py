"""Setiu Lantern Basket Tender | original SG/MY game vehicle | revision 1
A shallow-draft lagoon workboat with twin floats, stacked oyster lanterns and a lifting gantry.
Rebuild: blender -b --factory-startup --python-exit-code 1 -P build.py
Append -- --export-only to skip the Blender product render (PNG optimization: python3/Pillow).
Metres; base origin; Blender nose -Y, glTF +Z. Starboard helm.
Static material batches, UVs; Draco decoder required. Procedural, no downloaded assets.
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
    obj['category'] = 'vehicle'
    obj['theme'] = 'Singapore / Malaysia'
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


def cap(name,key,rows,sections=None):
    p = [(Y,Z-.009,Z+.04,X+.010) for _,_,_,Y,Z,X in rows]
    p = [(p[0][0]-.045,p[0][1]+.002,p[0][2]-.01,p[0][3]-.014)] + p + [
        (p[-1][0]+.04,p[-1][1]+.005,p[-1][2]-.008,p[-1][3]-.013)]
    return body_loft(name,key,p,sections)


def beam(name,key,a,b,width,depth=None):
    d=Vector(b)-Vector(a)
    obj=box(name,key,(Vector(a)+Vector(b))*.5,(width,depth or width,d.length),min(width*.12,.028))
    obj.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    return obj


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


def bitt(x,y,z,scale=1):
    box('Bollard base','metal',(x,y,z+.02),(.42*scale,.25*scale,.04),.018)
    for dx in (-.12,.12):
        pin('Mooring bitt','black',x+dx*scale,y,z+.12*scale,.062*scale,.24*scale);pin('Bitt head','black',x+dx*scale,y,z+.24*scale,.087*scale,.039*scale)


def legend(name,sub,x,y,z,w,h,s,key='ivory',board='paint'):
    box('Signboard',board,(s*x,y,z),(.038,w,h),.017)
    sign('Vessel name',name,key,(s*(x+.021),y,z+h*.11),h*.41,w*.9,(s,0,0))
    sign('Service and home port',sub,key,(s*(x+.021),y,z-h*.28),h*.17,w*.88,(s,0,0))


def translate_since(start,dx,dy=0,dz=0):
    for obj in ART[start:]: obj.location += Vector((dx,dy,dz))


def operator_cab(x,y,w,d,floor,waist,roof,roof_key='paint'):
    # Offset cabin for specialised machines: the column and instruments stay to driver's right.
    start=len(ART); front=y-d/2; back=y+d/2
    body_loft('Formed operator pod','paint',[(front,floor+.08,waist,w*.90),(front+.12,floor,waist+.015,w),(back-.09,floor,waist+.015,w),(back,floor+.05,waist,w*.96)])
    rows=[(front+.038,waist,w*.82,front+.24,roof-.04,w*.77),(front+.18,waist,w*.91,front+.34,roof,w*.85),(back-.16,waist,w*.93,back-.17,roof,w*.90),(back-.04,waist,w*.89,back-.055,roof-.025,w*.86)]
    shell(rows,[None,.10,None],.09,.13); cap('Floating roof visor',roof_key,rows)
    chair(-w*.26,y+.06,waist+.03,w*.74,(roof-waist)*.50)
    box('Instruments binnacle','black',(0,front+.16,waist+.042),(w*1.55,.27,.16),.045)
    steer(-w*.29,front+.38,waist+.17,.16)
    mirror(-w-.065,front+.23,waist+.36,-1,.15,True)
    box('Door catch','metal',(-w,back-.3,waist-.095),(.025,.15,.039),.008)
    translate_since(start,x)


def lantern(x,y,z,num):
    r=.36
    for j in range(4):
        zz=z+j*.20
        ring('Basket rim','sea',(x,y,zz),(0,0,1),r,.017,24)
        pin('Perforated tray insert','net',x,y,zz,r*.97,.018,24)
        if j<3:
            for i in range(9):
                t=TAU*(i+.27*j)/9
                oval('Clustered oyster shells','shell',(x+.24*math.cos(t),y+.24*math.sin(t),zz+.052),(.085,.054,.043),8,4)
    for i in range(14):
        a=TAU*i/14
        for turn in (-.29,.29):
            pts=[(x+r*math.cos(a+j*turn),y+r*math.sin(a+j*turn),z+j*.20) for j in range(4)]
            line('Braided lantern twine','net',pts,.008,5)
    for i in range(3):
        t=TAU*i/3
        rod('Basket bridle','rope',(x+r*math.cos(t),y+r*math.sin(t),z+.60),(x,y,z+.78),.012,7)
    pin('Cork float','warm',x,y,z+.788,.047,.103,12)


def build():
    palette('337F78','244A55','BD936B','EFA63F'); material('sea','Green basket rims','548E79',.57);material('net','Dark nylon net','30473F',.82);material('shell','Oyster shells','B1A28A',.77)
    for s in (-1,1):
        k=len(ART); vessel([(-3.20,.039,.86,.61),(-2.76,.27,.78,.35),(-2.03,.399,.78,.094),(-1.38,.435,.78,0),(1.97,.435,.78,0),(2.73,.375,.78,.09),(2.98,.32,.78,.19)],.6,True,False); translate_since(k,1.04*s)
    for i in range(5):box('Pontoon cross bearer','trim',(0,-2.36+i*1.24,.777),(2.64,.13,.16),.026)
    box('Working deck','deck',(0,.17,.85),(2.90,5.48,.136),.049)
    for i in range(19):box('Caulked deck joint','wood',(-1.34+i*.15,.17,.917),(.009,5.37,.005))
    # Half-wheelhouse leaves a continuous side passage on the port side.
    operator_cab(-.52,-1.51,.72,1.43,.93,1.49,2.49,'ivory')
    for s in (-1,1):
        legend('SETIU  08','TERNAKAN   /   TIRAM',1.468,-.84,.89,1.6,.29,s,'ivory','trim')
        for y in (-2.07,-.24,1.48):
            line('Suspended side fender','rope',[(s*1.38,y-.045,.94),(s*1.495,y,.70)],.015)
            oval('Working fender','black',(s*1.49,y,.54),(.093,.11,.235))
        bitt(s*1.03,-2.51,.93,.70); bitt(s*1.12,2.65,.93,.70)
    for i,(x,y) in enumerate([(-.86,-.23),(.02,-.23),(.90,-.23),(-.86,.67),(.02,.67),(.90,.67)]): lantern(x,y,.95,i)
    for s in (-1,1):
        for y in (1.50,2.62): beam('A-frame leg','paint',(s*1.21,y,.93),(s*1.21,2.20,2.57),.108)
        box('Bolted gantry shoe','metal',(s*1.21,1.52,.952),(.28,.31,.064),.011)
    beam('Hoist beam','warm',(-1.36,2.20,2.56),(1.36,2.20,2.56),.164)
    box('Chain block','trim',(0,2.20,2.38),(.28,.24,.25),.059)
    line('Hoist fall','black',[(0,2.20,2.27),(0,2.20,1.93)],.016)
    lantern(0,2.2,1.14,6)
    box('Outboard transom bracket','metal',(0,2.86,.78),(.44,.32,.31),.044)
    oval('Outboard cowling','trim',(0,3.03,.89),(.28,.36,.29)); box('Outboard leg','trim',(0,3.04,.50),(.17,.26,.56),.065)
    rod('Propeller hub','metal',(0,3.05,.22),(0,3.33,.22),.072,16)
    for i in range(3):
        t=TAU*i/3; o=oval('Propeller blade','metal',(.105*math.cos(t),3.27,.22+.105*math.sin(t)),(.131,.024,.061));o.data.transform(Matrix.Translation(Vector((.105*math.cos(t),3.27,.22+.105*math.sin(t)))) @ Matrix.Rotation(-t,4,'Y') @ Matrix.Translation(Vector((-.105*math.cos(t),-3.27,-.22-.105*math.sin(t)))))


if __name__ == '__main__':
    reset()
    build()
    finish('Setiu Lantern Basket Tender', 6.44,(0,0,1.4),(-1.5,-.89,.84))
