"""Jurong Lake Hornbill Pedalo | original SG/MY vehicle | revision 1
A two-seat park hire craft with an oriental pied hornbill prow, moulded feather pontoons and a stern paddle drum.
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


def side_plate(name,key,outline,x0,x1,r=.018):
    n=len(outline)
    v=[(x,y,z) for x in (x0,x1) for y,z in outline]
    f=[tuple(range(n)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return bevel(mesh(name,v,f,key,recalc=True),r)


def colors(**kwargs):
    standard()
    for name,(label,color) in kwargs.items():
        material(name,label,color,.38,.12)


def oval(name,key,loc,sizes,n=16,rows=8):
    x,y,z=loc; a,b,c=sizes
    v=[(x,y,z-c)]+[(x+a*math.cos(t*math.pi/rows)*math.cos(i*TAU/n),y+b*math.cos(t*math.pi/rows)*math.sin(i*TAU/n),z+c*math.sin(t*math.pi/rows)) for t in [j-rows/2 for j in range(1,rows)] for i in range(n)]+[(x,y,z+c)]
    f=[(0,1+(i+1)%n,1+i) for i in range(n)]+[(1+j*n+i,1+j*n+(i+1)%n,1+(j+1)*n+(i+1)%n,1+(j+1)*n+i) for j in range(rows-2) for i in range(n)]+[(len(v)-1,len(v)-1-n+i,len(v)-1-n+(i+1)%n) for i in range(n)]
    o=mesh(name,v,f,key,recalc=True)
    for p in o.data.polygons: p.use_smooth=True
    return o


def ring(name,key,center,normal,r,t,n=32):
    q=Vector(normal).to_track_quat('Z','Y'); c=Vector(center); m=8
    verts=[c+q@Vector(((r+t*math.cos(TAU*j/m))*math.cos(TAU*i/n),(r+t*math.cos(TAU*j/m))*math.sin(TAU*i/n),t*math.sin(TAU*j/m))) for i in range(n) for j in range(m)]
    obj=mesh(name,verts,[(i*m+j,((i+1)%n)*m+j,((i+1)%n)*m+(j+1)%m,i*m+(j+1)%m) for i in range(n) for j in range(m)],key,recalc=True)
    for p in obj.data.polygons:p.use_smooth=True
    return obj


def plumage(name,key,levels):
    # Horizontal elliptical sections follow the changing neck centreline.
    n=32
    v=[(wx*math.cos(TAU*i/n),y+dy*math.sin(TAU*i/n),z) for z,y,wx,dy in levels for i in range(n)]
    f=[tuple(range(n)),tuple(range(len(v)-n,len(v)))]+[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(levels)-1) for i in range(n)]
    obj=mesh(name,v,f,key,True)
    for p in obj.data.polygons:p.use_smooth=True


def build():
    colors(paint=('Peacock teal gelcoat','148E93'),feather=('Hornbill ink plumage','253441'),cheek=('Porcelain white feathers','F2EDDA'),bill=('Mango bill enamel','F5B83F'),redtip=('Tangerine casque','EF7938'),pad=('Seafoam seat inserts','9FD3BE'))
    for s in (-1,1):
        p=[(-1.61,.22,.41,.028),(-1.48,.11,.44,.165),(-1.15,.033,.49,.248),(-.58,0,.49,.275),(.94,0,.52,.275),(1.39,.04,.48,.237),(1.57,.13,.42,.165)]
        hull=body_loft('Buoyant hull runner','paint',p,[(.36,0),(.75,.09),(1,.56),(.94,.88),(.73,1)])
        hull.location.x=s*.535
    box('Footwell bridge','paint',(0,.02,.401),(1.37,2.36,.199),.080,3)
    box('Sand resistant foot pan','black',(0,-.28,.503),(1.24,1.20,.055),.020)
    for s in (-1,1):
        # Swept jet-black wing with overlapping feather flashes above each float.
        p=[(-1.34,.379,.48,.041),(-1.16,.38,.67,.083),(-.73,.38,.76,.089),(-.12,.39,.677,.097),(.66,.40,.69,.092),(1.17,.46,.80,.079),(1.43,.58,.885,.066),(1.59,.759,.938,.037),(1.64,.92,.954,.009)]
        wing=body_loft('Sculpted wing coaming','feather',p);wing.location.x=s*.685
        for j in range(3):
            # Swept overlapping feathers mounted on the outside of the wing.
            yy=.06+j*.29; zz=.497+j*.048
            yz=[(yy,zz+.034),(yy+.07,zz+.062),(yy+.30,zz+.071),(yy+.55,zz+.132),
                (yy+.39,zz+.052),(yy+.17,zz+.014),(yy+.036,zz+.015)]
            side_plate('Pied primary feather', 'cheek',yz,s*(.778+j*.004),s*(.786+j*.004),.004)
        box('Rental seat base','paint',(s*.32,.47,.586),(.527,.49,.16),.062)
        box('Seat pad','pad',(s*.32,.47,.673),(.505,.44,.093),.039)
        box('Moulded seat back','paint',(s*.32,.718,.857),(.545,.129,.47),.055,tilt=(-.21,0,0))
        box('Foam back insert','pad',(s*.32,.660,.88),(.455,.094,.355),.039,tilt=(-.21,0,0))
        for k in (-1,1):
            x=s*.32+k*.135; y=-.31;z=.582+k*.089
            beam('Pedal crank','metal',(x,y,.582),(x,y-k*.090,z),.025)
            box('Non skid pedal','bill',(x+k*.039,y-k*.090,z),(.121,.076,.034),.009)
        box('Seat number plaque','bill',(s*.791,-.491,.585),(.022,.72,.139),.010)
        sign('Park boat fleet title','JURONG   /   07','feather',(s*.805,-.491,.586),.076,.63,(s,0,0))
    rod('Pedal cross shaft','metal',(-.49,-.31,.582),(.49,-.31,.582),.029)
    box('Right steering pedestal','paint',(-.45,-.38,.682),(.17,.198,.245),.034)
    steer(-.45,-.245,.814,.104)
    # Fibreglass breast, pied collar and domed cheek. Curving yellow bill points forward.
    plumage('Porcelain breast','cheek',[(.40,-1.04,.33,.41),(.48,-1.04,.355,.417),(.61,-1.06,.329,.355),(.78,-1.10,.265,.255),(.959,-1.11,.216,.20)])
    plumage('Hornbill neck','feather',[(.934,-1.105,.214,.20),(1.07,-1.11,.207,.184),(1.26,-1.15,.195,.186),(1.37,-1.18,.214,.209),(1.47,-1.19,.199,.210)])
    oval('Hornbill head','feather',(0,-1.22,1.485),(.261,.306,.245),32,16)
    for s in (-1,1):
        oval('Ivory eye patch','cheek',(s*.221,-1.285,1.529),(.052,.133,.089),20,10)
        oval('Warm amber iris','bill',(s*.264,-1.299,1.54),(.018,.047,.049),18,10)
        oval('Pupil','black',(s*.279,-1.303,1.54),(.012,.029,.033),16,8)
        oval('Eye glint','ivory',(s*.290,-1.316,1.552),(.006,.009,.009),12,6)
    sect=[(.28,0),(.80,.19),(1,.47),(.91,.74),(.61,.94),(.21,1)]
    body_loft('Long curved bill','bill',[(-2.135,1.39,1.418,.014),(-2.043,1.423,1.516,.064),(-1.88,1.454,1.579,.101),(-1.62,1.437,1.598,.144),(-1.422,1.432,1.575,.173),(-1.39,1.45,1.558,.149)],sect)
    body_loft('Raised casque','redtip',[(-1.95,1.535,1.56,.031),(-1.86,1.55,1.64,.068),(-1.76,1.56,1.732,.079),(-1.63,1.56,1.747,.097),(-1.44,1.55,1.677,.11),(-1.36,1.554,1.61,.088)],sect)
    body_loft('Ink dipped bill tip','feather',[(-2.146,1.382,1.409,.009),(-2.121,1.393,1.44,.032),(-2.069,1.414,1.49,.059),(-2.054,1.421,1.498,.060)],sect)
    for s in (-1,1):
        line('Bill split line','feather',[(s*.146,-1.46,1.475),(s*.139,-1.61,1.48),(s*.090,-1.87,1.49),(s*.033,-2.09,1.43)],.008)
    rod('Paddle axle','metal',(-.55,1.08,.369),(.55,1.08,.369),.043)
    for j in range(8):
        a=j*TAU/8
        box('Paddle blade','bill',(0,1.08+.162*math.sin(a),.369+.162*math.cos(a)),(.59,.049,.239),.017,tilt=(-a,0,0))
    for s in (-1,1):rod('Paddle drum end','paint',(s*.30,1.08,.369),(s*.33,1.08,.369),.273,24)
    box('Paddle splash shield','paint',(0,1.12,.667),(.77,.70,.087),.035)


if __name__ == '__main__':
    reset()
    build()
    finish('Jurong Lake Hornbill Pedalo', 3.65,(0,0,.8),(-1.73,-1.0,.64))
