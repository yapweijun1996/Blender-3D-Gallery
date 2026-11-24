"""Bentong Access Sidecar | original SG/MY game vehicle | revision 1
A step-in passenger sidecar on a small town motorcycle, with a folding entry ramp and rain canopy.
Rebuild: blender -b --factory-startup --python-exit-code 1 -P build.py
Append -- --export-only to skip the Blender product render (PNG optimization: python3/Pillow).
Metres; base origin; Blender nose -Y, glTF +Z. Motorcycle on the right, curbside passenger module on the left.
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


def chair(x,y,z,w=.42,h=.48):
    box('Seat cushion','seat',(x,y,z),(w,.41,.104),.042)
    box('Seat back','seat',(x,y+.18,z+h*.49),(w,.118,h),.044,tilt=(.10,0,0))
    box('Head restraint','seat',(x,y+.184+h*.04,z+h*1.09),(w*.56,.121,h*.29),.038)


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
    obj['steering'] = 'Motorcycle on the right, curbside passenger module on the left'
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


def legend(name,sub,x,y,z,w,h,s,key='ivory',board='paint'):
    box('Signboard',board,(s*x,y,z),(.038,w,h),.017)
    sign('Vessel name',name,key,(s*(x+.021),y,z+h*.11),h*.41,w*.9,(s,0,0))
    sign('Service and home port',sub,key,(s*(x+.021),y,z-h*.28),h*.17,w*.88,(s,0,0))


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


def colors(**kwargs):
    standard()
    for name,(label,color) in kwargs.items():
        material(name,label,color,.38,.12)


def translate_since(start,dx,dy=0,dz=0):
    for obj in ART[start:]: obj.location += Vector((dx,dy,dz))


def side_casting(name,key,x,thickness,outline,radius=.01):
    # A cast plate with an explicit side silhouette and a machined edge.
    v=[(x+d,y,z) for d in (-thickness/2,thickness/2) for y,z in outline]; n=len(outline)
    f=[tuple(range(n)),tuple(range(n,2*n))]+[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)]
    return bevel(mesh(name,v,f,key,recalc=True),radius,2)


def disk(name,key,x,y,z,r,thick,s=1):
    return rod(name,key,(x,y,z),(x+s*thick,y,z),r,24)


def handlebar(x,y,z,width):
    for s in (-1,1):
        line('Swept handlebar','metal',[(x,y,z),(x+s*width*.48,y+.035,z+.12),(x+s*width*.98,y+.11,z+.14)],.020,12)
        rod('Rubber hand grip','black',(x+s*width*.65,y+.063,z+.130),(x+s*width,y+.113,z+.142),.031,16)
        line('Brake lever','metal',[(x+s*width*.63,y+.043,z+.13),(x+s*width*.77,y-.037,z+.082),(x+s*width*.99,y-.018,z+.086)],.009,8)
        line('Mirror stalk','metal',[(x+s*width*.57,y+.06,z+.14),(x+s*width*.64,y+.04,z+.28),(x+s*width*.86,y+.042,z+.32)],.011,8)
        oval('Rear view mirror','black',(x+s*width*.87,y+.046,z+.333),(.078,.029,.053))
        oval('Mirror insert','metal',(x+s*width*.87,y+.061,z+.334),(.067,.021,.044))


def cycle_front(x,y,r,top,head_z):
    wheel(y,x,r,.112,1,'bike')
    # Also finish the inside face; the vehicle is viewable from both sides.
    for s in (-1,1):
        ring('Polished bead seat','metal',(x+s*.058,y,r),(s,0,0),r*.595,.009,32)
        for i in range(8):
            a=TAU*i/8
            rod('Radial wheel spoke','metal',(x+s*.062,y,r),(x+s*.059,y+r*.58*math.cos(a),r+r*.58*math.sin(a)),.010,8)
        disk('Hub flange','metal',x+s*.058,y,r,.063,.012,s)
        rod('Fork slider','metal',(x+s*.098,y,r),(x+s*.098,y+.115,r+.33),.031)
        rod('Painted fork shroud','paint',(x+s*.098,y+.105,r+.29),(x+s*.098,y+.21,top),.042)
        disk('Axle nut','metal',x+s*.105,y,r,.036,.015,s)
    beam('Top yoke','metal',(x-.11,y+.21,top),(x+.11,y+.21,top),.084)
    rod('Steering stem','black',(x,y+.21,top),(x,y+.245,head_z),.041)
    handlebar(x,y+.245,head_z,.35)
    # Form the fender as a shallow arch; keep a clear gap around the tyre.
    for i in range(14):
        a,b=[math.radians(-75+10*j) for j in (i,i+1)]
        vs=[(x+dx,y+(r+gap)*math.sin(t),r+(r+gap)*math.cos(t)) for t in (a,b) for dx,gap in [(-.08,.024),(-.06,.05),(.06,.05),(.08,.024)]]
        mesh('Pressed mudguard',vs,[(j,j+1,j+5,j+4) for j in range(3)],'paint',recalc=True)
    yy=y+.19
    rod('Headlight nacelle','paint',(x,yy+.03,head_z-.10),(x,yy-.105,head_z-.10),.106,24)
    rod('Headlight bezel','metal',(x,yy-.104,head_z-.10),(x,yy-.124,head_z-.10),.104,24)
    rod('Headlight optic','lamp',(x,yy-.123,head_z-.10),(x,yy-.135,head_z-.10),.088,24)


def build():
    colors(paint=('Mulberry enamel','763D51'),cream=('Rice-paper cream','EEDCBC'),gold=('Champagne stripe','C89753'),shell=('Sage rain canvas','648E80'))
    x=-.50; r=.30; cycle_front(x,-.98,r,.87,.994);wheel(.79,x,r,.151,-1,'alloy')
    for s in (-1,1):
        dx=x+s*.108
        line('Double cradle frame','black',[(dx,-.72,.84),(dx,-.49,.37),(dx,.11,.34),(dx,.51,.72),(dx,-.72,.84)],.031)
        beam('Swing arm','seat',(dx,.13,.386),(dx,.79,.30),.052)
        rod('Rear damper','metal',(dx,.78,.32),(dx,.54,.70),.027,14)
        for i in range(7):
            t=i/8;oval('Shock spring collar','black',(dx,.77-.20*t,.34+.31*t),(.039,.039,.022),12,4)
        rod('Footrest','black',(dx,-.05,.36),(x+s*.25,-.05,.36),.031)
    k=len(ART);body_loft('Teardrop petrol tank','paint',[(-.71,.735,.856,.085),(-.65,.704,.912,.147),(-.47,.681,.958,.176),(-.29,.709,.943,.183),(-.12,.738,.848,.151),(-.034,.738,.799,.094)]);translate_since(k,x)
    pin('Filler cap','metal',x,-.46,.96,.054,.013)
    box('Stitched saddle','seat',(x,.266,.799),(.35,.62,.115),.047,3)
    box('Pillion pad','black',(x,.73,.782),(.28,.27,.089),.035)
    oval('Gearcase','seat',(x,-.10,.488),(.173,.193,.141));disk('Clutch cover','metal',x-.154,-.13,.493,.106,.037,-1)
    for i in range(6):box('Cooling fin','metal',(x,-.344,.496+i*.033),(.283,.18,.017),.006,tilt=(.12,0,0))
    line('Polished exhaust header','metal',[(x-.11,-.429,.626),(x-.15,-.53,.55),(x-.18,-.51,.35),(x-.20,-.20,.291),(x-.20,.31,.32)],.026,14)
    rod('Silencer','metal',(x-.20,.21,.31),(x-.20,.95,.411),.06,20)
    for y in (-.46,.64):beam('Sidecar frame crossmember','black',(x+.09,y,.365),(.79,y,.365),.071)
    rod('Sidecar stub axle','seat',(.64,.39,.256),(.95,.39,.256),.043)
    beam('Sidecar trailing arm','black',(.796,-.16,.36),(.803,.39,.256),.054)
    wheel(.39,.899,.256,.117,1,'steel');mudguard(.977,.39,.256,.281,.333,.186,1)
    profile=[(-.97,.34,.515,.23),(-.81,.30,.62,.32),(-.58,.292,.684,.39),(.43,.292,.648,.393),(.84,.327,.572,.39)]
    k=len(ART);body_loft('Step-in tub','paint',profile);translate_since(k,.39)
    for s in (-1,1):
        face('Bonnet coachline','cream',[(.39+s*.11,-.964,.524),(.39+s*.154,-.964,.524),(.39+s*.154,-.812,.624),(.39+s*.11,-.812,.624)],(0,-1,1))
        face('Bonnet coachline continued','cream',[(.39+s*.11,-.812,.624),(.39+s*.154,-.812,.624),(.39+s*.154,-.58,.688),(.39+s*.11,-.58,.688)],(0,-1,1))
        side_casting('Cream side flash','cream',.39+s*.392,.014,[(-.46,.50),(.62,.46),(.74,.51),(-.45,.584)],.003)
        line('Tub grab rail','metal',[(.39+s*.34,-.60,.65),(.39+s*.34,-.58,.82),(.39+s*.34,.13,.82),(.39+s*.34,.18,.66)],.022,12)
        for yy in (-.57,.57):beam('Canopy stay','shell',(.39+s*.345,yy,.62),(.39+s*.38,yy+.057,1.42),.034)
    chair(.39,.18,.676,.51,.449)
    crown('Sidecar rain shade','shell',.39,-.68,.82,.46,1.418,.119,.05)
    for s in (-1,1):legend('BENTONG','AKSES  /  03',.457,-.02,1.401,.85,.15,s,'cream','shell');translate_since(len(ART)-3,.39)
    # Perforated, stowed access ramp and top latch bar.
    for j in range(7):box('Entry ramp tread','metal',(.39,.85,.58+j*.052),(.66,.047,.031),.007)
    for s in (-1,1):box('Ramp edge stiffener','paint',(.39+s*.327,.852,.733),(.041,.061,.42),.007)
    box('Lamp plinth','paint',(x,.954,.668),(.16,.15,.089),.026);box('Tail lens','red',(x,1.027,.674),(.13,.018,.056),.008)
    plate('CBT 7402',.995,.567,False,.25,.077);translate_since(len(ART)-2,x)


if __name__ == '__main__':
    reset()
    build()
    finish('Bentong Access Sidecar', 2.65,(0,0,1),(.99,-1.62,.85))
