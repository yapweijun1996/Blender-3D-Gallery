"""Serdang Horsebox | SG/MY vehicle series, revision 1.
Selangor equestrian transporter with overcab groom berth, barred drop windows and a split loading ramp.
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


def body_line(name,key,profile,side,yz,r=.004, section=CAR_SECTION):
    line(name,key,[(side*(side_x(profile,section,y,z)+.002),y,z) for y,z in yz],r,6)


def cabin_rows(profile, rows, section=CAR_SECTION):
    return [(y,station_at(profile,y)[1]-.004,station_at(profile,y)[2]*section[-1][0]-.003,Y,Z,X)
            for y,Y,Z,X in rows]


def cap(name,key,rows,sections=None):
    p = [(Y,Z-.009,Z+.04,X+.010) for _,_,_,Y,Z,X in rows]
    p = [(p[0][0]-.045,p[0][1]+.002,p[0][2]-.01,p[0][3]-.014)] + p + [
        (p[-1][0]+.04,p[-1][1]+.005,p[-1][2]-.008,p[-1][3]-.013)]
    return body_loft(name,key,p,sections)


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


TRUCK_SECTION=[(.89,0),(.98,.08),(1,.24),(1,.83),(.983,.95),(.963,1)]


def truck_cab(nose,back,width,datum,top,axle,r,registration,service):
    w=width*.5
    h=top-datum
    p=[(nose,.64,datum-.10,w*.84),(nose+.045,.555,datum-.045,w*.91),
       (nose+.15,.495,datum+.005,w*.971),(nose+.32,.487,datum+.022,w),
       (back-.19,.488,datum+.032,w),(back-.04,.55,datum+.032,w*.98),
       (back,.625,datum+.028,w*.938)]
    body=body_loft('Lower cab pressing','paint',p,TRUCK_SECTION)
    wells(body,(axle,),r,r+.078,w,.39)
    y=nose+.151
    xx=w*.908
    rows=cabin_rows(p,[(y,y+.299,top-.115,xx*.944),
                       (y+.139,y+.403,top-.082,xx*.976),
                       (back-.229,back-.228,top-.062,xx),
                       (back-.061,back-.076,top-.114,xx*.955)],TRUCK_SECTION)
    shell(rows,[None,.088,None],front_inset=.063,rear_inset=0)
    cap('Formed cab roof crown','paint',rows)
    car_interior(rows,w,.171,[(y+.67,datum+.038,h*.55,True)])
    for side in (-1,1):
        mirror(side*(w+.10),y+.091,datum+.39,side,.178,True)
        rod('Lower mirror support','black',(side*(w-.012),y+.095,datum+.05),(side*(w+.102),y+.09,datum+.31),.019,10)
        xx0=side_x(p,TRUCK_SECTION,back-.38,datum-.11)
        box('Cab door pull pocket','black',(side*xx0,back-.38,datum-.11),(.029,.16,.054),.010)
        box('Cab door latch','metal',(side*(xx0+.015),back-.38,datum-.106),(.011,.126,.017),.004)
        body_line('Cab door back reveal','black',p,side,[(back-.214,z) for z in (datum+.01,datum-.10,datum-.30,max(.96,r*2+.11))],.0045,TRUCK_SECTION)
        box('Non-slip tread below cab','black',(side*(w-.024),y+.24,.597),(.142,.49,.096),.025)
        box('Cab step traction edge','metal',(side*(w+.04),y+.24,.626),(.023,.397,.037),.009)
        box('Cab side marker','amber',(side*(w+.008),y+.48,datum-.57),(.016,.081,.047),.009)
    grille(nose-.014,datum-.28,w*1.09,.268,4,'seat')
    head_module(nose+.010,datum-.28,w*.735,w*.423,.211,'strip',.14)
    box('Full-width impact bumper','black',(0,nose+.006,.671),(w*1.92,.287,.257),.058)
    box('Bumper centre step','metal',(0,nose-.14,.643),(w*.88,.035,.083),.023)
    plate(registration,nose-.119,.865,True,.45,.109)
    sign('Cab service lettering',service,'ivory',(0,nose-.004,datum-.097),.069,w*.98,(0,-1,0))
    return back


def chassis(nose,tail,front_axle,rear_axles,half_width,r,wide):
    z=r+.243
    for s in (-1,1):
        box('Chassis ladder rail','black',(s*.424,(nose+tail)*.5,z),(.184,tail-nose,.285),.029)
    for axle in (front_axle,*rear_axles):
        rod('Axle tube','black',(-half_width,axle,r),(half_width,axle,r),r*.155,14)
        rod('Differential case','black',(-.165,axle,r),(.165,axle,r),r*.40,16)
        for s in (-1,1):
            wheel(axle,s*half_width,r,wide,s,'lorry')
            if axle in rear_axles:
                # One additional inset carcass per rear wheel for road-ready duals.
                lathe('Inner dual tyre','tire',s*(half_width-wide-.017),axle,r,
                      [(-wide*.40,r),(wide*.40,r),(wide*.48,r*.96),(wide*.5,r*.89),(wide*.5,r*.53),
                       (-wide*.5,r*.53),(-wide*.5,r*.89),(-wide*.48,r*.96)],24)
    for s in (-1,1):
        for axle in rear_axles:
            box('Rear wheel spray flap','black',(s*(half_width-.047),axle+r+.083,r*.79),(.365,.063,r*1.20),.014)


def truck_tail(y,z,span,registration):
    box('Rear underrun bumper','black',(0,y-.042,z),(span,.197,.192),.034)
    rear_light(y+.038,z,span*.400,.249,.133)
    plate(registration,y+.070,z,False,.453,.102)
    for s in (-1,1):
        box('Rear safety reflector','amber',(span*.264*s,y+.057,z),(.148,.012,.039),.008)


def mudguard(x,y,z,inner,outer,depth,s):
    """Form a deep wrap from outside tyre sidewall to the chassis side."""
    v=[]
    for i in range(21):
        a=math.pi*i/20
        for xx,r in [(x,inner),(x,outer),(x-depth,outer),(x-depth,inner)]:
            v.append((s*xx,y+r*math.cos(a),z+r*math.sin(a)))
    f=[(0,1,2,3),(80,81,82,83)]
    for i in range(20):
        for j in range(4):
            k=(j+1)%4
            f.append((4*i+j,4*i+k,4*(i+1)+k,4*(i+1)+j))
    return bevel(mesh('Formed wheel spray guard',v,f,'black',recalc=True),.008,1)


def compartment(x,y,z,w,h,s,fill='metal'):
    box('Equipment bay rubber reveal','black',(s*x,y,z),(.043,w+.038,h+.038),.020)
    box('Equipment panel',fill,(s*(x+.029),y,z),(.036,w,h),.017)
    box('Equipment bay latch recess','black',(s*(x+.05),y,z-h*.333),(.014,w*.28,.064),.012)
    box('Equipment latch pull','metal',(s*(x+.061),y,z-h*.332),(.013,w*.20,.021),.007)


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


def build():
    colors(paint=('Mulberry horsebox enamel','70485D'),cream=('Champagne coach enamel','EDDEC1'),trim=('Copper coachlining','C7966D'),inside=('Oiled stall lining','977451'))
    r=.468;nose=-3.94;tail=3.89;a0=-2.72;a1=2.11
    truck_cab(nose,-2.02,2.15,1.50,2.67,a0,r,'BHT 4602','SERDANG  /  03');chassis(-3.64,3.73,a0,(a1,),.961,r,.253)
    for s in (-1,1):mudguard(1.133,a1,r,.527,.603,.30,s)
    box('Raised stall floor','black',(0,.88,1.116),(2.31,5.83,.18),.051)
    # Coachbuilt Luton berth overhangs the cab without obscuring its screen.
    st=[(-3.91,2.79,2.96,.87),(-3.74,2.78,3.15,.99),(-3.33,2.76,3.42,1.068),(-2.61,2.74,3.525,1.118),(-1.96,2.73,3.53,1.15)]
    body_loft('Groom overcab berth','cream',st,TRUCK_SECTION)
    for s in (-1,1):
        for a,b in zip(st[2:],st[3:]):body_side('Berth golden accent', 'trim',st,s,[(a[0],2.90),(b[0],2.90),(b[0],2.941),(a[0],2.941)],TRUCK_SECTION)
    box('Coach front bulkhead','cream',(0,-1.98,2.32),(2.30,.103,2.33),.044)
    box('Lower horse accommodation','paint',(0,.907,1.813),(2.30,5.83,1.262),.047)
    # Each sidewall is built around actual open stall lights; no opaque wall behind bars.
    box('Rear lintel','cream',(0,3.786,3.16),(2.30,.107,.66),.045)
    crown('Arched insulated roof','cream',0,-2.04,3.89,1.185,3.46,.141,.088,.98)
    for s in (-1,1):
        for y,w in [(-1.50,.98),(-.877,.263),(.413,.263),(1.703,.263),(3.403,.83)]:box('Coach wall jamb','cream',(s*1.104,y,2.954),(.092,w,1.075),.022)
        for i in range(3):
            y=-.233+i*1.29
            box('Window upper rail','cream',(s*1.105,y,3.382),(.105,1.105,.218),.023)
            box('Drop light shutter','cream',(s*1.113,y,2.578),(.102,1.105,.325),.024)
            box('Drop light top weatherseal','black',(s*1.121,y,2.745),(.11,1.105,.044),.011)
            for k in range(5):rod('Stall protection bar','metal',(s*1.089,y-.418+k*.204,2.752),(s*1.089,y-.418+k*.204,3.287),.021,12)
            box('Window drip hood','paint',(s*1.15,y,3.29),(.12,1.104,.059),.015)
        box('Belt moulding','trim',(s*1.157,.917,2.411),(.022,5.73,.077),.008)
        for i in range(2):compartment(1.151,-1.17+i*1.09,1.515,.98,.47,s,'paint')
        board_side(s,1.15,.85,2.133,3.56,.40,'S E R D A N G','PENGANGKUT KUDA   /   SELANGOR','paint','cream')
        # Original angular horse-head motif in two enamel inlays, facing the cab.
        y=-1.51;z=2.951
        face('Horse head inlay','paint',[(s*1.153,y+a,z+b) for a,b in [(-.36,-.04),(-.28,-.14),(-.09,-.087),(-.15,-.30),(.26,-.30),(.19,.00),(.086,.17),(-.01,.31),(-.063,.16),(-.14,.233),(-.13,.098)]],(s,0,0))
        face('Mane inlay','trim',[(s*1.157,y+a,z+b) for a,b in [(.037,.21),(.156,.14),(.271,-.032),(.32,-.24),(.24,-.208),(.132,.01)]],(s,0,0))
    box('Rear ramp frame','cream',(0,3.811,2.075),(2.31,.127,1.91),.04)
    box('Closed folding ramp','inside',(0,3.895,1.98),(2.10,.068,1.66),.022)
    for i in range(7):box('Ramp anti slip cleat','metal',(0,3.936,1.28+i*.223),(2.01,.045,.047),.01)
    for s in (-1,1):beam('Spring assisted ramp arm','black',(s*1.114,3.71,1.20),(s*1.11,3.95,2.58),.071)
    for y in (-1.1,.79,2.71):
        pin('Roof ventilator neck','seat',0,y,3.63,.14,.12)
        pin('Mushroom extractor','metal',0,y,3.705,.222,.066)
    truck_tail(tail,.737,2.22,'BHT 4602')
    finish('Serdang Horsebox',8.1,(0,0,1.8),(-1.73,-1.08,.60))


if __name__ == '__main__':
    reset(); build()
