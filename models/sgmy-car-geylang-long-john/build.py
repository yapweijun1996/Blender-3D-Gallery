"""sgmy-car-geylang-long-john — Two-wheeled long-john cargo cycle with a ventilated front carrier.

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
    obj['steering'] = 'Centreline handlebar'
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


def ring(name,key,center,normal,r,t,n=32):
    q=Vector(normal).to_track_quat('Z','Y'); c=Vector(center); m=8
    verts=[c+q@Vector(((r+t*math.cos(TAU*j/m))*math.cos(TAU*i/n),(r+t*math.cos(TAU*j/m))*math.sin(TAU*i/n),t*math.sin(TAU*j/m))) for i in range(n) for j in range(m)]
    obj=mesh(name,verts,[(i*m+j,((i+1)%n)*m+j,((i+1)%n)*m+(j+1)%m,i*m+(j+1)%m) for i in range(n) for j in range(m)],key,recalc=True)
    for p in obj.data.polygons:p.use_smooth=True
    return obj


def legend(name,sub,x,y,z,w,h,s,key='ivory',board='paint'):
    box('Signboard',board,(s*x,y,z),(.038,w,h),.017)
    sign('Vessel name',name,key,(s*(x+.021),y,z+h*.11),h*.41,w*.9,(s,0,0))
    sign('Service and home port',sub,key,(s*(x+.021),y,z-h*.28),h*.17,w*.88,(s,0,0))


def arm(name,key,a,b,w,h):
    a,b=Vector(a),Vector(b);o=box(name,key,(a+b)*.5,(w,h,(b-a).length),min(w,h)*.095);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o


def bike_wheel(y,r,w,deep=.025,rear_disc=False,spokes=24):
    z=r;rr=r-w*.74
    lathe('Supple road tyre','tire',0,y,z,[(w*.5*math.cos(i*TAU/12),r-w*.46+w*.46*math.sin(i*TAU/12)) for i in range(12)],48)
    lathe('Rim extrusion','black',0,y,z,[(-w*.38,rr),(w*.38,rr),(w*.32,rr-deep*.47),(0,rr-deep),(-w*.32,rr-deep*.47)],48)
    for s in (-1,1):ring('Rim edge','metal',(s*w*.37,y,z),(1,0,0),rr-.003,.0025,48)
    rod('Sealed axle','metal',(-.066,y,z),(.066,y,z),.018,20)
    if rear_disc:
        # Two dished aero skins close the wheel, with asymmetrical speed flashes.
        lathe('Dished disc wheel','paint',0,y,z,[(-.041,.026),(-.014,rr-deep+.004),(.014,rr-deep+.004),(.041,.026)],56)
        for s in (-1,1):
            for i in range(3):
                a=TAU*i/3+.14
                for lo,hi in [(0,.028),(.047,.056)]:
                    yz=[(.10,a+lo),(.26,a+.64+lo),(.26,a+.64+hi),(.10,a+hi)]
                    face('Disc flash','warm',[(s*(.042-(q-.026)*.027/(rr-deep-.026)),y+q*math.cos(t),z+q*math.sin(t)) for q,t in yz],(s,0,0))
    else:
        for s in (-1,1):
            rod('Spoke flange','metal',(s*.029,y,z),(s*.034,y,z),.034,20)
        for i in range(spokes):
            a=TAU*i/spokes;s=1 if i%2==0 else -1; b=a+(.56 if (i//2)%2 else -.56)
            rod('Laced spoke','metal',(s*.033,y+.03*math.cos(b),z+.03*math.sin(b)),(0,y+(rr-deep+.003)*math.cos(a),z+(rr-deep+.003)*math.sin(a)),.0019,6)
    for s in (-1,1):rod('Axle nut','metal',(s*.060,y,z),(s*.070,y,z),.013,6)


def saddle(y,z):
    # Narrow nose, relieved mid-section, flare toward rear sit-bone pads.
    for s in (-1,1):line('Saddle rail','metal',[(s*.021,y-.109,z-.01),(s*.022,y-.028,z-.044),(s*.023,y+.048,z-.044),(s*.052,y+.078,z-.01)],.004)
    body_loft('Sculpted saddle','black',[(y-.149,z,z+.022,.015),(y-.11,z-.003,z+.026,.024),(y-.033,z-.005,z+.022,.034),(y+.062,z-.006,z+.034,.074),(y+.093,z,z+.041,.077),(y+.116,z+.009,z+.040,.056)])


def drive(by,bz,ry,rz,track=False):
    # Drivetrain lies on cycling right (-X); crank arms are 180 degrees apart.
    r=.101 if track else .086;q=.040
    ring('Chainring','metal',(-.071,by,bz),(1,0,0),r-.008,.009,40)
    for j in range(5):
        a=j*TAU/5;arm('Spider','black',(-.072,by,bz),(-.072,by+r*.91*math.cos(a),bz+r*.91*math.sin(a)),.009,.016)
    rod('Sprocket','metal',(-.052,ry,rz),(-.059,ry,rz),q,24)
    top=[(-.071,by+r*math.cos(i*math.pi/10),bz+r*math.sin(i*math.pi/10)) for i in range(5,16)]
    end=[(-.059,ry+q*math.cos(i*math.pi/10),rz+q*math.sin(i*math.pi/10)) for i in range(-5,6)]
    line('Drive chain','black',top+end+[top[0]],.005,6)
    for s in (-1,1):
        a=(s*.078,by,bz);b=(s*.094,by+s*.123,bz+s*.115);arm('Crank arm','metal',a,b,.016,.025)
        box('Pedal','black',(s*.129,b[1],b[2]),(.075,.071,.025),.008)
    rod('Bottom bracket shell','paint',(-.068,by,bz),(.068,by,bz),.031)


def build():
    reset();palette('356D63','DC9A42','C49462','E9A345')
    fy,ry=-1.08,.96;fr,rr=.243,.331;bike_wheel(fy,fr,.049,.024,False,28);bike_wheel(ry,rr,.048,.025,False,32)
    bb=(0,.51,.293);seat=(0,.65,.772);head=(0,.20,.843)
    rod('Seat tube','paint',bb,seat,.027);rod('Short top tube','paint',seat,head,.024)
    for s in (-1,1):
        ax=(s*.055,ry,rr)
        rod('Chain stay','paint',(s*.036,.51,.293),ax,.015);rod('Seat stay','paint',ax,(s*.026,.65,.746),.014)
        # Stiff lowered twin spars pass beneath the front box to the remote head tube.
        line('Load spar','paint',[(s*.032,.51,.293),(s*.126,.24,.208),(s*.147,-.76,.208),(s*.044,-.95,.542)],.027)
        line('Fork blade','paint',[(s*.050,fy,fr),(s*.060,-1.014,.35),(s*.032,-.959,.53)],.018)
    rod('Steering mast tube','paint',(0,.12,.222),head,.038);rod('Rider stem','metal',head,(0,.238,1.025),.018)
    rod('Remote headset','metal',(0,-.982,.48),(0,-.934,.588),.030)
    line('Steering linkage','black',[(-.135,.17,.229),(-.247,.099,.217),(-.238,-.79,.229),(-.11,-.998,.31)],.010)
    rod('Seatpost','metal',seat,(0,.693,.894),.018);saddle(.69,.937);drive(.51,.293,ry,rr)
    # Laminated delivery box with cut-through gaps, capped posts, tee nuts and a number panel.
    box('Carrier floor','wood',(0,-.313,.31),(.618,.99,.052),.014)
    for s in (-1,1):
        for k in range(4):
            z=.373+k*.085;x=.312+k*.011
            box('Varnished side board','deck',(s*x,-.314,z),(.028,.99,.072),.010)
            box('Varnished end board','deck',(0,-.314+s*.482,z),(2*x,.033,.072),.010)
        for y in (-.78,.15):
            arm('Carrier post','paint',(s*.313,y,.30),(s*.362,y,.70),.033,.047)
            for z in (.39,.62):rod('Coach bolt','metal',(s*.341,y,z),(s*(.350+.012*(z>.5)),y,z),.009,8)
        box('Top rim','wood',(s*.359,-.311,.702),(.045,1.01,.044),.012)
        legend('GEYLANG','BEKAL   /   04',.363,-.31,.52,.69,.187,s,'ivory','paint')
    for s in (-1,1):
        line('Swept city bar','metal',[(0,.23,1.022),(s*.12,.19,1.030),(s*.236,.239,1.060),(s*.30,.313,1.061)],.012)
        rod('Handle grip','black',(s*.231,.231,1.059),(s*.31,.323,1.061),.017)
        line('Brake lever','black',[(s*.229,.230,1.054),(s*.24,.19,1.017),(s*.286,.221,1.021)],.006)
        line('Brake cable','black',[(s*.23,.21,1.039),(s*.104,.102,.90),(s*.066,.096,.61),(s*.055,.014,.316)],.0033)
        # Compact parcel shelf above the rear wheel.
        line('Rear carrier stay','metal',[(s*.069,ry,rr),(s*.088,ry+.23,.738),(s*.085,.80,.738),(s*.038,.642,.716)],.009)
        line('Centre stand','black',[(s*.102,.16,.226),(s*.160,.22,.034),(s*.185,.26,.022)],.011)
    box('Rear parcel rack','paint',(0,1.01,.741),(.206,.47,.024),.009)
    for y in (fy,ry):
        r=fr if y==fy else rr
        for s in (-1,1):line('Mudguard stay','metal',[(s*.056,y,r),(s*.036,y+r*.88,r+r*.47)],.0035)
        lat=[];n=25
        for j in range(n):
            a=math.radians(-18+178*j/(n-1));lat.extend([(x,y+(r+.012+dz)*math.cos(a),r+(r+.012+dz)*math.sin(a)) for x,dz in [(-.034,0),(-.022,.009),(.022,.009),(.034,0)]])
        mesh('Painted mudguard',lat,[(i*4+j,i*4+j+1,(i+1)*4+j+1,(i+1)*4+j) for i in range(n-1) for j in range(3)],'paint')
    rod('Headlamp shell','black',(0,-.95,.617),(0,-1.038,.617),.041);rod('Headlamp lens','lamp',(0,-1.039,.617),(0,-1.045,.617),.035)
    box('Tail reflector','red',(0,1.251,.737),(.076,.017,.039),.006)
    finish('Geylang Long John Cargo Bicycle',2.65,(0,0,.52),(-1,-.54,.38))


if __name__ == '__main__':
    build()
