"""Changi Airfield Guide | SG/MY vehicle series, revision 1.
High-visibility operations estate with a double-sided amber guidance board and airside checks.
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


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


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


def plate(words, y, z, front, width=.40, height=.108):
    d = -1 if front else 1
    box('Registration plate recess','black',(0,y,z),(width,.027,height),.013)
    sign('Fictional registration',words,'ivory',(0,y+d*.015,z),height*.54,width*.86,(0,d,0))


def mirror(x,y,z,s,size=.21, upright=False):
    dz = size*(.72 if not upright else 1.38)
    rod('Mirror stalk','black',(x-s*size*.42,y+.032,z-.05),(x,y,z),size*.090)
    box('Mirror housing','black',(x,y,z),(size,.12,dz),min(dz,.12)*.33)
    box('Silver mirror lens','metal',(x,y+.056,z),(size*.83,.012,dz*.79),.013)


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


def cabin_rows(profile, rows, section=CAR_SECTION):
    return [(y,station_at(profile,y)[1]-.004,station_at(profile,y)[2]*section[-1][0]-.003,Y,Z,X)
            for y,Y,Z,X in rows]


def cap(name,key,rows,sections=None):
    p = [(Y,Z-.009,Z+.04,X+.010) for _,_,_,Y,Z,X in rows]
    p = [(p[0][0]-.045,p[0][1]+.002,p[0][2]-.01,p[0][3]-.014)] + p + [
        (p[-1][0]+.04,p[-1][1]+.005,p[-1][2]-.008,p[-1][3]-.013)]
    return body_loft(name,key,p,sections)


def door_details(profile, positions, ends):
    for s in (-1,1):
        for y in ends:
            lo,hi,_ = station_at(profile,y)
            span = [mix(hi-.013,lo+.085,i/15) for i in range(16)]
            points = [(s*(side_x(profile,CAR_SECTION,y+.05*(hi-z),z)+.005),y+.05*(hi-z),z) for z in span]
            line('Door shut line','black',points,.0032,6)
        for y in positions:
            lo,hi,_ = station_at(profile,y)
            z = hi-.10
            x = s*side_x(profile,CAR_SECTION,y,z)
            box('Recessed handle pocket','black',(x,y,z),(.025,.146,.042),.012)
            box('Flush satin door handle','metal',(x+s*.014,y,z+.004),(.013,.105,.016),.005)


def car_interior(rows,w,cb,seat_rows,seat_keys='seat'):
    y,z,x,Y,Z,X = rows[0]
    for ys,zs,h,pair in seat_rows:
        for s in (-1,1):
            chair(s*w*.445,ys,zs,w*.45,h)
        if not pair:
            box('Rear bench centre cushion',seat_keys,(0,ys,zs),(w*.48,.41,.104),.036)
            box('Rear bench centre back',seat_keys,(0,ys+.18,zs+h*.49),(w*.48,.118,h),.034,tilt=(.10,0,0))
    box('Moulded dashboard','black',(0,y+.165,z+.018),(w*1.56,.31,.15),.05)
    box('Driver instrument brow','black',(-w*.44,y+.202,z+.098),(w*.44,.20,.09),.028)
    box('Driver instrument cluster','seat',(-w*.44,y+.298,z+.095),(w*.32,.015,.044),.008)
    steer(-w*.44,y+.384,z+.119,cb)
    box('Central console','black',(0,y+.64,z-.035),(w*.26,.55,.103),.031)
    rod('Gear selector','metal',(0,y+.54,z),(0,y+.51,z+.083),.018,10)
    for s in (-1,1):
        a = Vector((s*x*.77,y,z)).lerp(Vector((s*X*.77,Y,Z)),.10)
        b = Vector((s*x*.23,y,z)).lerp(Vector((s*X*.23,Y,Z)),.19)
        line('Parked wiper','black',[a+Vector((0,-.012,.009)),b+Vector((0,-.012,.012))],.008,8)


def rear_light(y,z,x,w=.24,h=.19, tilt=0):
    for s in (-1,1):
        angle=(0,0,-s*tilt)
        yt = y-math.sin(tilt)*w*.23
        box('Tail light surround','black',(s*x,yt,z),(w,.09,h),min(w,h)*.19,tilt=angle)
        box('Red tail light lens','red',(s*x,yt+.048,z+h*.19),(w*.82,.022,h*.42),.013,tilt=angle)
        box('Amber direction lens','amber',(s*x,yt+.046,z-h*.24),(w*.81,.019,h*.21),.009,tilt=angle)


def head_module(y,z,x,w,h,kind='strip',toe=.10):
    for s in (-1,1):
        angle=(0,-s*.06,s*toe)
        box('Recessed lighting cluster','black',(s*x,y,z),(w,.12,h),min(h*.26,.047),tilt=angle)
        if kind == 'round':
            for i,k in [(-.151,'lamp'),(.155,'amber')]:
                xx=s*(x+w*i)
                yy=y-.065+w*i*toe
                rod('Round projector bezel','metal',(xx,yy+.014,z),(xx,yy-.010,z),h*.343,20)
                rod('Round lamp optic',k,(xx,yy-.008,z),(xx,yy-.017,z),h*.271,20)
        else:
            box('Diffused daytime running optic','lamp',(s*(x-.016),y-.063,z+h*.19),(w*.84,.018,h*.31),.010,tilt=angle)
            box('Low beam reflector','metal',(s*(x-w*.11),y-.063,z-h*.20),(w*.50,.017,h*.24),.008,tilt=angle)
            box('Direction indicator','amber',(s*(x+w*.32),y-.063+w*.32*toe,z-h*.19),(.065,.017,h*.22),.008,tilt=angle)


def grille(y,z,w,h,count=3,key='metal'):
    box('Radiator opening','black',(0,y,z),(w,.112,h),min(.039,h*.32))
    for i in range(count):
        zz=z+h*.67*((i+1)/(count+1)-.5)
        box('Radiator vane',key,(0,y-.056,zz),(w*.87,.022,max(.009,h*.095)),.004)


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


def board_side(s,x,y,z,w,h,title,sub,base='paint',ink='ivory'):
    box('Screen printed fleet panel',base,(s*x,y,z),(.035,w,h),.015)
    labels(s,x+.020,y,z+h*.12,title,sub,w*.91,h*.42,ink)


def warning_dome(x,y,z):
    pin('Beacon foot','black',x,y,z+.027,.105,.054)
    pin('Amber warning dome','amber',x,y,z+.098,.087,.107)
    pin('Beacon cap','amber',x,y,z+.153,.072,.018)


def build():
    colors(paint=('Apron chartreuse','DBDB36'),dark=('Ink navy markings','172D41'),light=('Reflective pearl','F3F5E8'))
    ax=(-1.36,1.35);r=.326
    p=[(-2.34,.292,.778,.65),(-2.24,.255,.859,.78),(-2.04,.243,.914,.886),(-1.52,.241,.967,.919),(-.94,.235,1.016,.925),(.84,.240,1.057,.929),(1.78,.264,1.069,.916),(2.17,.284,1.034,.879),(2.29,.353,.950,.798)]
    core=body_loft('Longroof estate pressing','paint',p,CAR_SECTION);wells(core,ax,r,.371,.934,.305);wheels(ax,.823,r,.204,'alloy')
    rows=cabin_rows(p,[(-1.08,-.535,1.543,.706),(-.984,-.427,1.566,.732),(.24,.18,1.601,.755),(.345,.288,1.605,.758),(1.14,1.07,1.587,.75),(1.211,1.14,1.577,.744),(1.985,1.625,1.533,.710),(2.13,1.74,1.501,.68)])
    shell(rows,[None,.084,None,.08,None,.108,None],.068,.076);cap('Estate roof skin','dark',rows)
    car_interior(rows,.913,.147,[(-.47,.95,.392,True),(.61,.99,.409,False)])
    door_details(p,(.145,1.09),(-.92,.287,1.192));head_module(-2.25,.69,.603,.365,.133);grille(-2.34,.58,.81,.195,4,'seat');plate('CG 072',-2.36,.397,True)
    for s in (-1,1):
        mirror(s*.978,-.889,1.078,s,.163)
        for i in range(24):
            y=-2.02+i*.17
            for j in range(2):
                z=.685+j*.099
                body_side('Airfield checker square','dark' if (i+j)%2 else 'light',p,s,[(y,z),(y+.17,z),(y+.17,z+.099),(y,z+.099)])
        board_side(s,.926,-.36,.51,.966,.24,'CHANGI','AIRSIDE   /   07','dark','light')
        box('Roof rail foot','dark',(s*.51,.57,1.634),(.067,1.63,.063),.023)
        rod('Elevated roof rail','metal',(s*.51,-.21,1.68),(s*.51,1.38,1.68),.029)
        beam('Board prop','dark',(s*.48,.52,1.69),(s*.48,.78,1.91),.043)
        warning_dome(s*.521,-.17,1.67)
    box('Folding guidance display','dark',(0,.81,1.949),(1.32,.133,.51),.055)
    for d in (-1,1):
        sign('Amber dot display','FOLLOW ME','amber',(0,.81+d*.069,2.008),.159,1.14,(0,d,0))
        for i in range(10):box('Directional LED segment','amber',(-.48+i*.105,.81+d*.071,1.822),(.063,.009,.024),.004)
    box('Rear parcel blind','seat',(0,1.53,1.077),(1.53,.97,.052),.022)
    line('Rear screen wiper','black',[(.44,2.073,1.131),(.21,2.052,1.157),(-.26,2.016,1.205)],.012)
    box('Rear hatch garnish','dark',(0,2.275,.775),(1.59,.070,.093),.03);rear_light(2.255,.814,.665,.30,.143);plate('CG 072',2.295,.662,False)
    box('Scuff protector','dark',(0,2.28,.429),(1.67,.091,.115),.034)
    box('Roof spoiler','dark',(0,1.78,1.531),(1.40,.19,.056),.022)
    finish('Changi Airfield Guide',4.8,(0,0,1),(-1.34,1.17,.61))


if __name__ == '__main__':
    reset(); build()
