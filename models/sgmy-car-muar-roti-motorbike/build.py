"""sgmy-car-muar-roti-motorbike — Small Johor bread-vending motorcycle with glazed display chest.

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
ASSET_ID = 'sgmy-car-muar-roti-motorbike'


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


def lathe(name, key, x, y, z, profile, n=32):
    """Lathe a closed cross-section around the lateral (X) axle."""
    v = [(x+a,y+r*math.cos(i*TAU/n),z+r*math.sin(i*TAU/n)) for a,r in profile for i in range(n)]
    f = [(j*n+i,j*n+(i+1)%n,((j+1)%len(profile))*n+(i+1)%n,((j+1)%len(profile))*n+i)
         for j in range(len(profile)) for i in range(n)]
    obj = mesh(name,v,f,key,recalc=True)
    for p in obj.data.polygons:
        p.use_smooth = True
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


def plate(words, y, z, front, width=.40, height=.108):
    d = -1 if front else 1
    box('Registration plate recess','black',(0,y,z),(width,.027,height),.013)
    sign('Fictional registration',words,'ivory',(0,y+d*.015,z),height*.54,width*.86,(0,d,0))


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
    obj['controls'] = 'Centreline handlebars, left-hand traffic'
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


def build():
    reset();palette('9D4742','E2B777','86989E','E8A04F');material('crust','Honey bread crust','D59957',.82);material('linen','Warm flour and linen','F2DEAF',.76);material('jade','Mint wrapper stripe','538C81',.55)
    a=-.626;b=.64;cyclewheel(a);cyclewheel(b);mudguard(a,'paint',.09,math.pi+.16);mudguard(b,'ivory',-.29,math.pi+.05)
    for s in (-1,1):
        rod('Front fork slider','metal',(s*.069,a,.284),(s*.083,-.550,.535),.026)
        rod('Painted fork housing','paint',(s*.083,-.553,.525),(s*.097,-.433,.812),.039)
        boom((s*.071,.09,.32),(s*.066,b,.286),'deck',.040,.05)
        A=Vector((s*.086,.604,.316));B=Vector((s*.113,.42,.677));rod('Shock absorber','black',A,B,.022)
        delta=B-A;perp=delta.cross(Vector((1,0,0))).normalized();line('Coil spring','metal',[A+delta*(.09+.78*j/52)+Vector((1,0,0))*.028*math.cos(TAU*j/8)+perp*.028*math.sin(TAU*j/8) for j in range(53)],.0055,6)
    yz_prism('Pressed step-through spine','paint',0,.16,[(-.536,.74),(-.48,.85),(-.40,.82),(-.17,.49),(.04,.47),(.20,.66),(.52,.66),(.58,.57),(.16,.40),(.08,.34),(-.22,.35)],.030)
    for s in (-1,1):
        yz_prism('Side cover','paint',s*.076,.058,[(.04,.47),(.18,.648),(.49,.65),(.54,.579),(.29,.47),(.13,.443)],.022)
        stripe('Paint pinstripe','trim',s,.107,[(.14,.52),(.44,.57),(.47,.59),(.22,.567)],)
    yz_prism('Sweeping leg shield','linen',0,.30,[(-.529,.787),(-.504,.808),(-.428,.741),(-.236,.489),(-.183,.418),(-.231,.406),(-.40,.574)],.023)
    rod('Gear case','deck',(-.131,.07,.344),(.128,.07,.344),.117,24)
    rod('Horizontal cylinder','black',(0,-.02,.342),(0,-.20,.301),.086,16)
    for j in range(7):box('Cylinder cooling fin','metal',(0,-.056-j*.021,.338-j*.0045),(.189,.011,.149),.004,tilt=(.18,0,0))
    box('Saddle pan','wood',(0,.20,.684),(.262,.441,.051),.022);box('Rider saddle','black',(0,.197,.724),(.288,.462,.104),.042,3)
    line('Exhaust header','metal',[(.074,-.18,.31),(.118,-.24,.240),(.146,-.13,.176),(.153,.24,.190)],.026)
    rod('Exhaust silencer','black',(.154,.18,.19),(.169,.77,.246),.047,16);rod('Chrome heat shield','metal',(.186,.23,.208),(.192,.69,.252),.031,12)
    for s in (-1,1):
        rod('Footpeg','black',(s*.09,.036,.322),(s*.215,.036,.322),.023);line('Handlebar','metal',[(0,-.44,.828),(s*.112,-.438,.863),(s*.196,-.408,.907),(s*.293,-.374,.907)],.016)
        rod('Ribbed handgrip','black',(s*.216,-.399,.907),(s*.305,-.370,.907),.022);line('Brake lever','metal',[(s*.207,-.407,.898),(s*.233,-.442,.883),(s*.304,-.426,.875)],.008)
        line('Mirror stem','metal',[(s*.199,-.416,.917),(s*.213,-.438,1.032),(s*.263,-.456,1.068)],.008);box('Rearview mirror','black',(s*.266,-.456,1.071),(.092,.031,.063),.013)
    rod('Headlight nacelle','paint',(0,-.487,.859),(0,-.58,.854),.084,24);rod('Round headlight','lamp',(0,-.576,.854),(0,-.590,.854),.072,24)
    # Glazed rear vendor cabinet, stocked on both shelves and supported by a triangulated carrier.
    for s in (-1,1):
        line('Load rack','black',[(s*.15,.37,.61),(s*.30,.49,.786),(s*.30,.981,.786),(s*.083,.69,.361)],.023)
    box('Baker cabinet base','jade',(0,.745,.807),(.784,.55,.077),.025)
    for tier in range(2):
        z=.853+tier*.168;box('Display board','trim',(0,.745,z),(.737,.506,.023),.008)
        for xx in (-.25,-.083,.083,.25):
            for yy in (.587,.734,.882):bun(xx,yy,z+.014,.142,.124,.083 if tier==0 else .073)
    for s in (-1,1):
        glazed('Case side glass',[(s*.378,.489,.847),(s*.378,1.004,.847),(s*.378,1.004,1.208),(s*.378,.489,1.208)],(s,0,0),.11,frame='metal')
    for d in (-1,1):
        y=.747+d*.259;glazed('Case door', [(-.374,y,.847),(.374,y,.847),(.374,y,1.208),(-.374,y,1.208)],(0,d,0),.09,frame='metal')
    crown('Vendor hood','paint',0,.434,1.061,.419,1.233,.067,.049);box('Header sign','jade',(0,.748,1.315),(.713,.13,.145),.028)
    for d in (-1,1):sign('Bakery trade sign','ROTI   MUAR','ivory',(0,.748+d*.066,1.316),.067,.63,(0,d,0))
    for s in (-1,1):
        for j in range(4):
            y=.533+j*.127;k=('trim','jade','paint','trim')[j];x=s*.407
            line('Snack packet hook','metal',[(s*.374,y,.825),(x,y,.842),(x,y,.792)],.006)
            box('Wrapped snack pack',k,(x,y,.735),(.037,.095,.132),.013,tilt=(.08,0,0));box('Packet paper band','linen',(x+s*.020,y,.735),(.005,.079,.041),.002)
    box('Rear marker','red',(0,1.030,.812),(.168,.03,.042),.010);plate('JRW 26',1.012,.747,False,.207,.060)
    finish('Muar Roti Motorbike',2.01,(0,.044,.67),(-1,-.70,.39))


def arm(name,key,a,b,w,h):
    a,b=Vector(a),Vector(b);o=box(name,key,(a+b)*.5,(w,h,(b-a).length),min(w,h)*.095);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o


def yz_prism(name,key,x,w,profile,rad=0):
    n=len(profile);vs=[(x+s*w/2,y,z) for s in (-1,1) for y,z in profile];f=[tuple(range(n)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return bevel(mesh(name,vs,f,key,recalc=True),rad)


def stripe(name,key,s,x,profile):
    face(name,key,[(s*x,y,z) for y,z in profile],(s,0,0))


def boom(a,b,key='trim',w=.18,h=.21):
    return arm('Fabricated box boom',key,a,b,w,h)


def cyclewheel(y,r=.286):
    z=r
    lathe('Pneumatic tyre','tire',0,y,z,[(-.019,r),(.019,r),(.039,r-.010),(.051,r-.032),(.050,r-.056),(.038,r-.069),(-.038,r-.069),(-.050,r-.056),(-.051,r-.032),(-.039,r-.010)],40)
    lathe('Chrome wheel rim','metal',0,y,z,[(-.033,r-.058),(.033,r-.058),(.038,r-.070),(.025,r-.083),(-.025,r-.083),(-.038,r-.070)],40)
    rod('Brake drum','deck',(-.047,y,z),(.047,y,z),.077,24)
    for s in (-1,1):
        for j in range(18):
            a=(j+.42*(s+1))*TAU/18;b=a+(.37 if j%2 else -.37)
            rod('Cross-laced spoke','metal',(s*.043,y+.058*math.cos(b),z+.058*math.sin(b)),(s*.017,y+(r-.078)*math.cos(a),z+(r-.078)*math.sin(a)),.0044,6)


def mudguard(y,key,a0,a1):
    n=22;r=.315;vs=[(x,y+rr*math.cos(a0+(a1-a0)*j/n),.286+rr*math.sin(a0+(a1-a0)*j/n)) for j in range(n+1) for x,rr in [(-.071,r-.019),(-.057,r-.004),(0,r+.009),(.057,r-.004),(.071,r-.019),(.065,r-.028),(0,r-.004),(-.065,r-.028)]]
    bevel(mesh('Rolled wheel mudguard',vs,[tuple(range(8)),tuple(range(8*n,8*n+8))]+[(j*8+i,j*8+(i+1)%8,(j+1)*8+(i+1)%8,(j+1)*8+i) for j in range(n) for i in range(8)],key,True),.004)


def bun(x,y,z,w,l,h):
    n=16;vs=[(x+w*.5*k*math.cos(i*TAU/n),y+l*.5*k*math.sin(i*TAU/n),z+h*zz) for k,zz in ((.78,0),(.98,.20),(1,.48),(.82,.79),(.48,.96),(.12,1)) for i in range(n)]
    o=mesh('Baked roll',vs,[tuple(range(n)),tuple(range(5*n,6*n))]+[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for i in range(n) for j in range(5)],'crust',True)
    for p in o.data.polygons:p.use_smooth=True
    for dy in (-.20,.14):line('Floured score','linen',[(x+w*k,y+l*(dy+.15*k),z+h*(.991-.65*abs(k))) for k in (-.28,0,.28)],.004,6)


if __name__ == '__main__':
    build()
