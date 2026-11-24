"""Klang harbour tug with a belted working bow, elevated wheelhouse and stern towing winch.

Original SG/MY static vehicle; no external art, fonts or textures.
Rebuild: blender -b --factory-startup -P build.py (add -- --export-only for GLB only).
Metres; base origin; Blender nose -Y, glTF nose +Z. Vehicle right is -X.
UV-mapped material batches; requires Draco. No animation or collision geometry.
"""

# Shared geometry and studio conventions from round two of the gallery vehicle set.
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
    ground = min(v.co.z for v in obj.data.vertices)
    for v in obj.data.vertices:
        v.co.z -= ground
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
    obj['operator_station'] = STATION
    obj['asset_id'] = ASSET_ID
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
    scene.cycles.samples = 14
    scene.cycles.adaptive_min_samples = 4
    scene.cycles.adaptive_threshold = .10
    scene.cycles.max_bounces = 5
    scene.cycles.use_denoising = True
    scene.cycles.denoising_prefilter = 'ACCURATE'
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 3
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
    asset = consolidate(name)
    # Fit the actual silhouette to both image axes, including antennas and implements.
    look = Vector(direction).normalized()
    right = Vector((0,0,1)).cross(look).normalized()
    up = look.cross(right).normalized()
    xs = [v.co.dot(right) for v in asset.data.vertices]
    ys = [v.co.dot(up) for v in asset.data.vertices]
    target = Vector(target)
    target += right*((min(xs)+max(xs))/2-right.dot(target)) + up*((min(ys)+max(ys))/2-up.dot(target))
    fill = 1.12*max(max(xs)-min(xs),(max(ys)-min(ys))*1120/760)/length
    result = bpy.ops.export_scene.gltf(
        filepath=str(out/'model.glb'),export_format='GLB',use_selection=True,
        export_texcoords=True,export_normals=True,export_animations=False,export_extras=True,
        export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=7,
        export_draco_position_quantization=19,export_draco_texcoord_quantization=14)
    if result != {'FINISHED'}:
        raise RuntimeError(f'GLB export failed: {result}')
    options = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    if '--export-only' in options:
        return
    studio(length, target, direction, fill).render.filepath = str(out/'preview.png')
    bpy.ops.render.render(write_still=True)


def labels(s,x,y,z,main,sub,width,height,key='ivory',sub_key=None):
    sign('Side fleet title',main,key,(s*x,y,z),height,width,(s,0,0))
    if sub:
        sign('Side fleet subtitle',sub,sub_key or key,(s*x,y,z-height*1.05),height*.42,width,(s,0,0))


def palette(main, second, accent):
    material('paint','Primary fleet enamel',main,.32,.18)
    material('second','Secondary fleet enamel',second,.35,.14)
    material('accent','Contrasting fleet flash',accent,.34,.10)


def yz(name,key,xc,thick,profile,edge=.012):
    """Extrude a longitudinal silhouette across vehicle width."""
    n=len(profile)
    v=[(x,y,z) for x in (xc-thick/2,xc+thick/2) for y,z in profile]
    f=[tuple(range(n)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return bevel(mesh(name,v,f,key,True),edge,2)


def shaft(name,key,x,y,z,width,r,sides=32):
    return rod(name,key,(x-width/2,y,z),(x+width/2,y,z),r,sides)


def marine_colors(main,side,accent,water,deck):
    palette(main,side,accent)
    material('bottom','Antifouling below waterline',water,.58,.10)
    material('deck','Deck finish',deck,.62,.03)
    material('rope','Buff braided line','CBB487',.81)
    material('green','Starboard navigation lens','39B58A',.22,emission=.14)


def ship(stations,rub=.065):
    """Keel, hard chines, painted boot stripe, sheer and continuous cambered deck.
    Stations: longitudinal Y, beam radius, local keel Z, gunwale Z.
    """
    contour=[(0,0),(.53,.14),(.79,.27),(.90,.39),(.915,.417),(.973,.66),(1,.94),(.998,1),(.86,1.013),(0,1.025)]
    keys=['bottom','bottom','bottom','accent','paint','paint','second','deck','deck']
    def pt(row,s,p):
        y,w,b,t=row;return (s*p[0]*w,y,b+(t-b)*p[1])
    for s in (-1,1):
        for i,key in enumerate(keys):
            verts=[pt(row,s,p) for row in stations for p in contour[i:i+2]]
            # First axis is section rise, second goes sternward.
            faces=[(j,j+2,j+3,j+1) if s>0 else (j,j+1,j+3,j+2) for j in range(0,len(verts)-2,2)]
            surf=mesh('Hull strake' if i<7 else 'Cambered deck',verts,faces,key)
            for poly in surf.data.polygons:poly.use_smooth=True
        line('Continuous rubbing wale','black',[pt(row,s,(1.005,.929)) for row in stations],rub,12)
    for row,normal in [(stations[0],(0,-1,0)),(stations[-1],(0,1,0))]:
        path=[pt(row,1,p) for p in contour]+[pt(row,-1,p) for p in reversed(contour[1:-1])]
        face('Stem or transom', 'paint',path,normal)
    return stations


def hull_at(rows,y):
    for a,b in zip(rows,rows[1:]):
        if y<=b[0]:
            t=max(0,(y-a[0])/(b[0]-a[0]));return tuple(i+(j-i)*t for i,j in zip(a[1:],b[1:]))
    return rows[-1][1:]


def rail(rows,ys,h,fill='metal',scale=.94):
    for s in (-1,1):
        coords=[]
        for y in ys:
            w,b,t=hull_at(rows,y);x=s*w*scale
            rod('Guardrail stanchion',fill,(x,y,t),(x,y,t+h),.027,10);coords.append(Vector((x,y,t+h)))
        line('Top handrail',fill,coords,.029,12);line('Lifeline',fill,[p-Vector((0,0,h*.48)) for p in coords],.014,10)


def ring_buoy(x,y,z,s,r=.27):
    # Four contrasting bindings are integrated into the torus rather than decals.
    n=40;k=10;v=[];f=[]
    for i in range(n):
        a=i*TAU/n
        for j in range(k):
            b=j*TAU/k;rr=r*(.756+.244*math.cos(b))
            v.append((x+s*r*.244*math.sin(b),y+rr*math.cos(a),z+rr*math.sin(a)))
    for i in range(n):
        for j in range(k):f.append((i*k+j,i*k+(j+1)%k,((i+1)%n)*k+(j+1)%k,((i+1)%n)*k+j))
    obj=mesh('Rescue buoy with four lashings',v,f,'red',True);obj.data.materials.append(MAT['ivory'])
    for p in obj.data.polygons:p.use_smooth=True;p.material_index=int((p.index//k)%10 in (0,1,2))
    for dy in (-r*.54,r*.54):rod('Buoy hanger','metal',(x-s*.06,y+dy,z+r*.89),(x+s*.02,y+dy,z+r*.65),.016)


def bitt(x,y,z,scale=1):
    box('Mooring bitt base','black',(x,y,z+.03*scale),(.26*scale,.64*scale,.06*scale),.018*scale)
    for dy in (-.16*scale,.16*scale):
        rod('Mooring post','seat',(x,y+dy,z+.03*scale),(x,y+dy,z+.28*scale),.078*scale,16)
        rod('Post cap','black',(x,y+dy,z+.28*scale),(x,y+dy,z+.32*scale),.112*scale,16)


def house(y0,y1,w,base,sill,top,panels=3,rake=.21,key='second',roof='accent'):
    body_loft('Wheelhouse lower trunk',key,[(y0,base,sill,w),(y1,base,sill,w)],[(.98,0),(1,.12),(1,1)])
    for s in (-1,1):
        for i in range(panels):
            u=i/panels;v=(i+1)/panels
            def corner(t,upper):
                y=y0+(y1-y0)*t
                return (s*(w-.055 if upper else w),y+(rake*(1-t)-.05*t if upper else 0),top if upper else sill)
            glazed('Saloon side light',[corner(u,False),corner(v,False),corner(v,True),corner(u,True)],(s,0,0),.117,frame=key)
    for y,dy,d in [(y0,rake,-1),(y1,-.05,1)]:
        for i in range(3):
            u=-1+i*2/3;v=u+2/3
            glazed('Wheelhouse screen',[(u*w,y,sill),(v*w,y,sill),(v*(w-.055),y+dy,top),(u*(w-.055),y+dy,top)],(0,d,0),.112,frame=key)
    body_loft('Cabin roof visor',roof,[(y0+rake-.23,top-.03,top+.075,w+.09),(y0+rake+.03,top-.035,top+.14,w+.14),(y1-.09,top-.035,top+.14,w+.14),(y1+.16,top-.022,top+.08,w+.09)])
    chair(-w*.46,y0+.69,sill+.02,.45,.45);steer(-w*.46,y0+.36,sill+.24,.16)
    box('Helm instruments','black',(-w*.41,y0+.19,sill+.082),(w*.77,.30,.17),.04)
    for s in (-1,1):
        box('Navigation lamp shield','black',(s*(w+.073),y0+rake+.43,top+.16),(.16,.29,.095),.024)
        box('Sidelight', 'green' if s<0 else 'red',(s*(w+.143),y0+rake+.43,top+.21),(.057,.21,.071),.015)


def porthole(s,x,y,z,r):
    shaft('Portlight surround','metal',s*x,y,z,.043,r,32)
    shaft('Portlight glass','black',s*(x+.027),y,z,.018,r*.77,32)


def propeller(x,y,z,r):
    """Fixed pitched blades below a rising stern, with shaft strut and rudder."""
    rod('Propeller shaft','metal',(x,y-2.28*r,z+.74*r),(x,y+.10*r,z),r*.16,16)
    rod('Bearing strut','seat',(x,y-.50*r,z+.08*r),(x,y-.72*r,z+1.27*r),r*.125,12)
    rod('Boss','accent',(x,y-.20*r,z),(x,y+.18*r,z),r*.262,20)
    for i in range(4):
        a=i*TAU/4
        def point(h,t,d):
            return (x+r*(h*math.cos(a)-t*math.sin(a)),y+r*d,z+r*(h*math.sin(a)+t*math.cos(a)))
        pts=[point(*p) for p in [(.14,-.10,-.14),(.56,-.26,-.09),(.94,-.16,-.06),(.99,.11,.04),(.77,.35,.15),(.31,.22,.10)]]
        blade=face('Pitched propeller blade','accent',pts,(0,1,0));mod=blade.modifiers.new('Blade thickness','SOLIDIFY');mod.thickness=.031*r
    yz('Steering rudder','bottom',x,.14*r,[(y+.39*r,z+1.58*r),(y+1.44*r,z+1.64*r),(y+1.37*r,z-.69*r),(y+.52*r,z-.65*r)],.026*r)



ASSET_ID = 'sgmy-car-klang-harbour-tug'
STATION = 'Starboard helm'


def build():
    marine_colors('203C51','EFE6CC','E5A63D','A45245','697D78')
    rows=ship([(-7.12,.13,1.08,2.53),(-6.90,.95,.84,2.48),(-6.36,1.72,.52,2.39),(-5.48,2.20,.21,2.24),(-3.74,2.48,.03,2.07),(-1.84,2.54,0,1.95),(2.06,2.54,0,1.85),(4.86,2.30,.13,1.89),(6.27,1.76,.49,1.98),(6.90,1.15,.81,2.04)],.11)
    for s in (-1,1):
        for i in range(16):
            y=-7.08+3.16*(i/15)**1.57;w,b,t=hull_at(rows,y)
            line('Individual D-section bow fender','tire',[(s*w*.991,y,t-.06),(s*(w+.071),y,t-.21),(s*(w-.042),y+.02,t-.64)],.116)
        for y in (-3.5,-1.7,.18,2.2,4.23):
            w,b,t=hull_at(rows,y);x=s*(w+.025)
            lathe('Suspended tyre fender','tire',x,y,t-.37,[(-.11,.29),(-.10,.40),(-.06,.44),(.06,.44),(.10,.40),(.11,.26),(.07,.22),(-.07,.22)],32)
            for d in (-1,1):line('Fender chain','metal',[(s*w*.98,y+d*.31,t+.035),(x,y+d*.23,t-.13)],.028)
    body_loft('Tug forecastle','second',[(-4.76,1.88,2.93,1.28),(-4.08,1.91,3.13,1.79),(.94,1.84,3.13,1.78),(1.63,1.82,2.91,1.46)],[(.98,0),(1,.08),(1,.90),(.965,1)])
    for s in (-1,1):
        for y in (-3.47,-2.71,-1.95):porthole(s,1.795,y,2.71,.171)
        box('Bulkhead watertight door','accent',(s*1.789,-.34,2.52),(.056,.65,1.08),.025)
        box('Dogging handle','black',(s*1.828,-.15,2.49),(.044,.17,.035),.012)
    house(-4.03,-.35,1.51,3.05,3.76,4.74,4,rake=-.21,roof='accent')
    for s in (-1,1):
        labels(s,1.513,-2.23,3.53,'PELABUHAN  KLANG','TUNDA   /   08',2.91,.196,'paint')
        ring_buoy(s*1.84,.59,2.65,s,.33)
        # Sloping stacks stay outside the windows, on their own exhaust trunks.
        x=s*1.07
        yz('Exhaust stack','accent',x,.51,[(.18,3.03),(.84,3.03),(1.29,4.78),(.72,4.86)],.052)
        yz('Soot deflector','black',x,.52,[(.61,4.52),(1.23,4.46),(1.36,4.91),(.75,5.00)],.026)
        for i in range(3):box('Stack vent','paint',(s*1.334,.54+i*.14,3.45),(.020,.075,.36),.010,tilt=(-.24,0,0))
        bitt(s*1.65,4.99,1.96,1.25)
    # Towing winch, flanges, wound hawser and A-frame fairlead.
    for x in (-.91,.91):yz('Winch bearing frame','accent',x,.22,[(2.09,1.92),(3.62,1.92),(3.35,2.65),(3.0,2.98),(2.67,2.94)],.045)
    shaft('Tow drum','seat',0,2.92,2.65,1.82,.40)
    for x in (-.72,.72):shaft('Tow drum flange','second',x,2.92,2.65,.09,.63,36)
    for i in range(17):
        lathe('Hawser drum wrap','rope',-.66+.080*i,2.92,2.65,[(-.047,.45),(-.033,.511),(0,.533),(.034,.511),(.047,.45)],24)
    for s in (-1,1):
        yz('Fairlead cheek','accent',s*.66,.21,[(4.94,1.94),(5.72,1.97),(5.57,2.73),(5.15,2.70)],.032)
    for s in (-1,1):propeller(s*.64,6.27,.36,.344)
    shaft('Towing fairlead roller','metal',0,5.36,2.58,1.29,.135)
    rail(rows,[-5.86,-5.12,-4.15,-2.90,-1.65,-.56,.55,1.34],.69)
    rod('Mainmast','second',(0,-1.25,4.82),(0,-1.19,6.20),.075)
    rod('Signal yard','metal',(-.85,-1.21,5.75),(.85,-1.21,5.75),.036)
    for x in (-.77,0,.77):rod('Masthead lamp','lamp',(x,-1.21,5.78),(x,-1.21,5.91),.073)
    box('Scanner bar','ivory',(0,-1.17,6.25),(1.03,.17,.093),.027)
    finish('Klang Harbour Tug',14.22,(0,-.20,2.75),(-1.25,-.78,.63),1.17)


if __name__ == "__main__":
    reset()
    standard()
    build()
