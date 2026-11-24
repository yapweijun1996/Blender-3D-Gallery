"""Punggol twin-hull water taxi with a photovoltaic roof, glazed saloon and aft boarding gates.

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
    scene.cycles.samples = 10
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


def cap(name,key,rows,sections=None):
    p = [(Y,Z-.009,Z+.04,X+.010) for _,_,_,Y,Z,X in rows]
    p = [(p[0][0]-.045,p[0][1]+.002,p[0][2]-.01,p[0][3]-.014)] + p + [
        (p[-1][0]+.04,p[-1][1]+.005,p[-1][2]-.008,p[-1][3]-.013)]
    return body_loft(name,key,p,sections)


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



ASSET_ID = 'sgmy-car-punggol-solar-catamaran'
STATION = 'Starboard helm'


def build():
    marine_colors('2C858C','EFEFD9','F9B849','27576D','A8AD9A')
    material('solar','Deep blue photovoltaic cells','24446B',.23,.38)
    rows=[(-5.41,.025,.63,1.70),(-5.11,.19,.38,1.62),(-4.50,.39,.16,1.48),(-3.65,.535,0,1.33),(-2.10,.60,0,1.25),(2.85,.60,0,1.25),(4.44,.51,.13,1.29),(5.09,.43,.27,1.32)]
    for s in (-1,1):
        start=len(ART);ship(rows,.038)
        for o in ART[start:]:o.location.x+=s*1.52
        propeller(s*1.52,5.07,.157,.147)
        line('Bow safety rail','metal',[(s*1.77,-3.38,1.40),(s*1.77,-3.42,1.75),(s*1.56,-4.35,1.83),(s*1.56,-4.40,1.48)],.024)
        box('Bow compartment hatch','second',(s*1.52,-4.61,1.51),(.35,.39,.046),.017,tilt=(-.15,0,0))
        bitt(s*1.52,-3.99,1.42,.67);bitt(s*1.56,4.59,1.33,.75)
    body_loft('Bridgedeck wing','second',[(-3.78,1.28,1.39,1.67),(-3.40,1.13,1.41,2.02),(-2.84,1.07,1.42,2.09),(4.12,1.07,1.42,2.09),(4.77,1.17,1.39,1.89)],[(.90,0),(1,.6),(1,.88),(.97,1)])
    body_loft('Saloon skirt','paint',[(-3.37,1.39,1.85,1.32),(-3.04,1.37,1.96,1.59),(-2.39,1.38,2.01,1.76),(2.48,1.38,2.01,1.76),(3.19,1.38,1.96,1.57)],[(.98,0),(1,.17),(1,1)])
    rows2=[(-3.36,1.84,1.31,-2.60,2.91,1.25),(-3.04,1.953,1.59,-2.33,3.03,1.48),(-2.39,2.004,1.757,-1.98,3.08,1.65),(-.95,2.004,1.757,-.77,3.08,1.65),(.72,2.004,1.757,.75,3.08,1.65),(2.47,2.004,1.757,2.47,3.08,1.65),(3.19,1.955,1.57,3.15,3.03,1.49)]
    shell(rows2,[None,.13,.086,.086,.086,None],front_inset=.081,rear_inset=.13,paint='second');cap('Fairing around solar roof','second',rows2)
    for s in (-1,1):
        for y in (-.96,-.07,.82,1.71,2.57):chair(s*.81,y,2.02,.62,.50)
        box('Below-window line','accent',(s*1.764,.035,1.94),(.014,4.80,.044),.005)
        labels(s,1.766,-.14,1.77,'PUNGGOL   /   WATER TAXI','SOLAR ELECTRIC      03',3.76,.173,'ivory')
        x=s*1.87
        line('Aft boarding gate','metal',[(x,3.25,1.42),(x,3.25,2.16),(x,4.14,2.16),(x,4.14,1.42)],.037)
        rod('Gate lifeline','metal',(x,3.25,1.81),(x,4.14,1.81),.020)
        ring_buoy(x+s*.02,3.68,1.84,s,.252)
        box('Stern boarding step','deck',(s*.97,4.52,1.422),(1.34,.40,.07),.019)
    for s in (-1,1):
        line('Black pantograph wiper','black',[(s*.90,-3.32,1.92),(s*.76,-3.20,2.10),(s*.22,-3.13,2.20)],.016)
    chair(-.66,-2.23,2.05,.49,.50);steer(-.66,-2.75,2.15,.173)
    box('Helm dashboard','black',(0,-2.98,1.993),(2.31,.32,.18),.055)
    # Each blue module has a metal rim and two sun-catching busbars.
    for i in range(2):
        x=(i-.5)*1.42
        for j in range(6):
            y=-1.55+.79*j
            box('Photovoltaic frame','metal',(x,y,3.142),(1.38,.748,.057),.017)
            box('Photovoltaic laminate','solar',(x,y,3.174),(1.324,.69,.018),.006)
            for c in (-.42,0,.42):box('Cell interconnect','seat',(x+c,y,3.184),(.012,.66,.005),.001)
    box('Aft entry portal','second',(0,3.192,2.19),(.85,.05,1.49),.023)
    box('Sliding entry light','glass',(0,3.224,2.48),(.65,.019,.78),.007)
    sign('Front route number','PW   03','ivory',(0,-3.377,1.69),.112,.88,(0,-1,0))
    finish('Punggol Solar Catamaran',10.55,(0,0,1.45),(-.91,-1.08,.51),1.13)


if __name__ == "__main__":
    reset()
    standard()
    build()
