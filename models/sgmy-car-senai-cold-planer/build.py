"""sgmy-car-senai-cold-planer — Tracked cold milling machine with discharge conveyor and operator canopy.

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


def crown(name,key,x,y0,y1,w,z,rise,lip=.075,taper=.95):
    # Barrel-cambered sheet roof, with thin fascia and a shallow crown.
    cross=[(-1,0),(-.83,.52),(-.44,.88),(0,1),(.44,.88),(.83,.52),(1,0)]
    profile=cross+[(a,b-lip/rise) for a,b in reversed(cross)]; n=len(profile)
    v=[(x+a*w*k,y,z+b*rise+dz) for y,k,dz in [(y0,taper,0),(y0+.18,1,.018),(y1-.18,1,.018),(y1,taper,0)] for a,b in profile]
    f=[tuple(reversed(range(n))),tuple(range(3*n,4*n))]+[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(3) for i in range(n)]
    bevel(mesh(name,v,f,key,recalc=True),.014)


def rail(pts,h=.57):
    for x,y,z in pts:rod('Stanchion','metal',(x,y,z),(x,y,z+h),.024)
    for k in (.49,1):line('Safety rail','metal',[(x,y,z+h*k) for x,y,z in pts],.018 if k<1 else .032)


def legend(name,sub,x,y,z,w,h,s,key='ivory',board='paint'):
    box('Signboard',board,(s*x,y,z),(.038,w,h),.017)
    sign('Vessel name',name,key,(s*(x+.021),y,z+h*.11),h*.41,w*.9,(s,0,0))
    sign('Service and home port',sub,key,(s*(x+.021),y,z-h*.28),h*.17,w*.88,(s,0,0))


def arm(name,key,a,b,w,h):
    a,b=Vector(a),Vector(b);o=box(name,key,(a+b)*.5,(w,h,(b-a).length),min(w,h)*.095);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o


def yz_prism(name,key,x,w,profile,rad=0):
    n=len(profile);vs=[(x+s*w/2,y,z) for s in (-1,1) for y,z in profile];f=[tuple(range(n)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return bevel(mesh(name,vs,f,key,recalc=True),rad)


def track_pod(s,y):
    x=s*.97;z=.30;r=.27;dist=.80
    # Rollers sit inside a continuous tread with flat contact pads.
    for dy,key,rr in [(-.4,'paint',.218),(-.14,'metal',.122),(.14,'metal',.122),(.4,'paint',.218)]:
        zz=z if abs(dy)>.3 else z-.068
        rod('Crawler roller',key,(x-.17,y+dy,zz),(x+.17,y+dy,zz),rr,24)
        rod('Axle boss','black',(x+s*.160,y+dy,zz),(x+s*.193,y+dy,zz),rr*.38,16)
    box('Bogie beam','black',(x,y,z+.08),(.27,.93,.14),.052)
    path=[]
    for i in range(9):path.append((y-.4+i*dist/9,z+r))
    for i in range(10):
        a=math.pi*.5-math.pi*i/10;path.append((y+.4+r*math.cos(a),z+r*math.sin(a)))
    for i in range(9):path.append((y+.4-i*dist/9,z-r))
    for i in range(10):
        a=-math.pi*.5-math.pi*i/10;path.append((y-.4+r*math.cos(a),z+r*math.sin(a)))
    for (a,b),(c,d) in zip(path,path[1:]+path[:1]):
        o=box('Crawler shoe','tire',(x,(c+a)/2,(d+b)/2),(.41,math.hypot(c-a,d-b)*1.03,.060),.013);o.rotation_euler.x=math.atan2(d-b,c-a)
    pin('Steering kingpin','metal',x,y,.76,.125,.49)


def build():
    reset();palette('257479','E3AC40','89999B','F6BD53')
    for s in (-1,1):
        for y in (-1.47,2.39):track_pod(s,y)
    # Raised nose clears the pick-up belt. The cutter drum lies between the crawler bogies.
    yz_prism('Chassis belly','black',0,2.04,[(-2.28,.89),(-2.17,1.24),(2.98,1.24),(2.85,.76),(-1.90,.76)],.061)
    rod('Milling mandrel','metal',(-1.02,.13,.44),(1.02,.13,.44),.34,28)
    for i in range(32):
        x=-.90+i*.058;t=TAU*i/11;rod('Carbide pick','black',(x,.13+.32*math.cos(t),.44+.32*math.sin(t)),(x+.03,.13+.39*math.cos(t+.1),.44+.39*math.sin(t+.1)),.028,8)
    for s in (-1,1):
        yz_prism('Sliding cutter end plate','trim',s*1.105,.115,[(-.88,.14),(-.86,.71),(-.49,1.04),(.65,1.04),(1.02,.49),(1.03,.13)],.034)
        box('Skid shoe','black',(s*1.10,.08,.133),(.18,1.98,.085),.024)
        for y in (-.54,.62):pin('Levelling strut','metal',s*1.09,y,.87,.071,.56)
    yz_prism('Tapered engine enclosure','paint',0,2.18,[(-.30,1.15),(-.20,1.94),(.24,2.26),(1.93,2.26),(2.75,2.03),(3.03,1.68),(3.01,1.18)],.079)
    for s in (-1,1):
        box('Service grille shadow','black',(s*1.093,1.78,1.73),(.031,1.60,.53),.014)
        for i in range(14):box('Vent lamella','metal',(s*1.116,1.06+i*.111,1.73),(.026,.036,.46),.012,tilt=(-.21,0,0))
        legend('KISAR  12','SENAI  /  JALAN',1.103,.32,1.72,1.12,.47,s,'ivory','paint')
    pin('Exhaust stack','black',.77,1.08,2.55,.093,.72);pin('Rain cap','metal',.77,1.08,2.92,.132,.058)
    box('Operator deck','seat',(0,-1.26,1.30),(2.35,1.94,.14),.048)
    chair(-.53,-.91,1.70,.52,.51);box('Operator pedestal','black',(-.53,-.91,1.52),(.27,.33,.39),.046)
    box('Control console','paint',(-.53,-1.66,1.77),(.81,.35,.79),.076);steer(-.53,-1.48,2.12,.17)
    for i,key in enumerate(('lamp','amber','red')):pin('Control switch',key,-.34+i*.068,-1.67,2.176,.022,.035)
    for s in (-1,1):
        line('Canopy pillar','black',[(s*.97,-.56,1.36),(s*.97,-.50,2.49),(s*.92,-.70,3.02)],.055)
        rail([(s*1.11,-2.05,1.38),(s*1.11,-1.45,1.38)],.65)
        for k in range(3):box('Access step','metal',(s*(1.03+k*.044),-.57,.77+k*.19),(.26,.49,.045),.015)
    crown('Operator sun canopy','trim',0,-2.34,-.17,1.21,3.05,.104);pin('Beacon','amber',.84,-.47,3.23,.09,.18)
    # Articulated discharge conveyor; trough, rollers, lattice diagonals and flexible dust curtain.
    start=Vector((0,-1.82,1.14));end=Vector((0,-5.72,2.85));v=end-start;n=Vector((0,v.z,-v.y)).normalized()
    arm('Belt underside','black',start,end,.69,.12)
    for s in (-1,1):
        x=Vector((s*.399,0,0));a=start+x;b=end+x
        arm('Upper stringer','trim',a,b,.079,.115);arm('Lower stringer','paint',a-n*.30,b-n*.30,.075,.084)
        for i in range(12):
            A=a.lerp(b,i/12);B=a.lerp(b,(i+1)/12);arm('Lattice web','metal',A-n*.26*(i%2),B-n*.26*((i+1)%2),.037,.044)
        a=Vector((s*.73,-1.69,.93));b=Vector((s*.42,-3.56,1.77));rod('Conveyor lift ram','trim',a,a.lerp(b,.62),.096);rod('Chrome piston','metal',a.lerp(b,.59),b,.058)
    for i in range(24):
        q=start.lerp(end,(i+.35)/24)+n*.068;rod('Belt cleat','seat',q+Vector((-.31,0,0)),q+Vector((.31,0,0)),.017,8)
    box('Discharge hood','paint',(0,-5.69,2.86),(.96,.48,.29),.074,3)
    for j in range(7):box('Flexible dust skirt','black',((j-3)*.118,-5.89,2.60),(.115,.048,.38),.016,tilt=(-.10,0,0))
    finish('Senai Cold Planer',9.1,(0,-1.43,1.52),(-1,-.55,.49))


if __name__ == '__main__':
    build()
