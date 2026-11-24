"""sgmy-car-bedok-dragon-boat — Festival racing dragon boat with carved finials, drum and sweep oar.

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
    obj['steering'] = 'Sweep oar'
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


def band(name,key,rows):
    # Loft adjacent mirrored waterlines. Each row is (station Y, half-breadth, height).
    a,b=rows
    for s in (-1,1):
        v=[(s*w,y,z) for row in (a,b) for y,w,z in row]; n=len(a)
        f=[(j,j+n,j+n+1,j+1) for j in range(n-1)]
        mesh(name,v,[tuple(reversed(p)) if s==1 else p for p in f],key)


def ell(name,key,x,y,z,w,l,h):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,location=(x,y,z));o=bpy.context.object;o.scale=(w/2,l/2,h/2)
    for p in o.data.polygons:p.use_smooth=True
    return register(o,name,key)


def build():
    reset();palette('156957','E6AB3B','A76F47','D64538')
    st=[(-5.15,.045,1.02,.64),(-4.81,.29,.78,.29),(-4.16,.51,.62,.08),(-3.30,.62,.58,0),(-2.16,.66,.57,0),(2.19,.66,.57,0),(3.56,.59,.61,.03),(4.41,.38,.75,.23),(4.98,.06,1.04,.61)]
    outer=[[(y,w*k,b+(z-b)*t) for y,w,z,b in st] for k,t in [(.25,0),(.81,.28),(.98,.86),(1,1)]]; inner=[[(y,max(.018,w-.053),z) for y,w,z,b in st],[(y,w*.61,max(b+.08,z-.43)) for y,w,z,b in st]]
    for j,key in enumerate(('wood','paint','trim')):band('Carved hull strake',key,outer[j:j+2])
    band('Gunwale cap','trim',(outer[-1],inner[0]));band('Inner hull','wood',inner)
    for row,key,norm in [(outer[0],'wood',-1),(inner[1],'deck',1)]:
        for (y,w,z),(Y,W,Z) in zip(row,row[1:]):face('Bottom plank',key,[(-w,y,z),(w,y,z),(W,Y,Z),(-W,Y,Z)],(0,0,norm))
    for j in (0,-1):
        y,w,z,b=st[j];box('Endpost','trim',(0,y,(b+z)/2),(w*2,.09,z-b),.028)
    for i in range(10):
        y=-3.59+.77*i;w=.97 if i in (0,9) else 1.14
        box('Paddler thwart','deck',(0,y,.51),(w,.225,.061),.020)
        box('Floor stretcher','wood',(0,y-.24,.196),(w*.59,.082,.073),.023)
    # Repeating hull scales follow each longitudinal station, never crossing the chine.
    for s in (-1,1):
        for (a,w,h,b),(A,W,H,B) in zip(st[1:-2],st[2:-1]):
            n=round((A-a)/.30)
            for i in range(n):
                pts=[]
                for frac,d in [(0,.76),(.47,.41),(.99,.76),(.47,.57)]:
                    t=(i+frac)/n; pos=a+(A-a)*t;ww=w+(W-w)*t;base=b+(B-b)*t;zz=base+((h+(H-h)*t)-base)*d
                    pts.append((s*(ww*(.81+(.98-.81)*(d-.28)/.58)+.003),pos,zz))
                face('Gilt scale chevron','trim',pts,(s,0,0))
    # Figurehead: upswept neck, vermilion jaws, gold antlers, layered cheek fins and pearl eyes.
    ell('Carved dragon neck','paint',0,-5.10,1.09,.45,.63,.95);ell('Golden throat','trim',0,-5.34,1.22,.36,.31,.70)
    ell('Dragon crown','paint',0,-5.32,1.53,.60,.75,.54);ell('Upper muzzle','trim',0,-5.68,1.51,.46,.64,.24)
    ell('Lower jaw','warm',0,-5.63,1.33,.40,.60,.12)
    for s in (-1,1):
        ell('Pearl eye','ivory',s*.263,-5.45,1.59,.12,.20,.17);ell('Eye pupil','black',s*.318,-5.47,1.60,.045,.098,.107)
        line('Scarlet brow','warm',[(s*.27,-5.53,1.64),(s*.29,-5.43,1.70),(s*.25,-5.26,1.72)],.040)
        line('Forked horn','trim',[(s*.17,-5.20,1.72),(s*.25,-5.03,1.92),(s*.30,-4.80,2.03)],.052)
        rod('Antler tine','trim',(s*.24,-5.03,1.90),(s*.32,-5.08,2.06),.031)
        for i in range(3):
            face('Flame cheek fin','warm' if i%2==0 else 'trim',[(s*.235,-5.24,1.67-i*.12),(s*.36,-4.77-i*.02,1.82-i*.17),(s*.23,-5.10,1.50-i*.12)],(s,0,0))
        for y in (-5.63,-5.82):ell('Fang','ivory',s*.14,y,1.419,.045,.046,.095)
        line('Whisker scroll','trim',[(s*.19,-5.81,1.51),(s*.37,-5.68,1.47),(s*.43,-5.49,1.45),(s*.46,-5.40,1.52)],.017)
        ell('Nostril','paint',s*.108,-5.89,1.59,.063,.086,.024)
    # Flame tail is a carved slab with inset colour on both faces.
    profile=[(4.78,.77),(5.14,.94),(5.49,1.31),(5.68,1.76),(5.31,1.48),(5.28,1.79),(5.03,1.38),(4.94,1.55),(4.79,1.18)]
    n=len(profile);mesh('Carved tail',[ (x,y,z) for x in (-.073,.073) for y,z in profile],[tuple(range(n)),tuple(range(n,2*n))]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)],'trim',recalc=True)
    for s in (-1,1):face('Tail inlay','warm',[(s*.075,y,z) for y,z in [(4.87,1),(5.11,1.1),(5.48,1.49),(5.17,1.30),(5.17,1.46)]],(s,0,0))
    # Festival drum on foredeck, with top hide, bound hoops and brass tacks.
    box('Drum saddle','wood',(0,-4.0,.65),(.58,.68,.24),.034);ell('Lacquered drum','warm',0,-4.04,.96,.70,.70,.68)
    for z in (.72,1.20):pin('Drum hoop','trim',0,-4.04,z,.279,.053)
    pin('Drum skin','rope',0,-4.04,1.238,.277,.036)
    for i in range(16):
        t=TAU*i/16;ell('Brass tack','trim',.30*math.cos(t),-4.04+.30*math.sin(t),1.13,.045,.045,.045)
    rod('Sweep oar','wood',(-.42,3.22,.97),(-.56,4.84,.42),.030);ell('Sweep blade','deck',-.56,4.99,.39,.125,.52,.11)
    box('Team name plaque','paint',(0,-2.83,.55),(1.13,.229,.042),.016)
    # Local club name across the upper face of the front thwart.
    txt=sign('Crew name','BEDOK', 'ivory',(0,-2.83,.573),.122,.89,(0,-1,0));txt.rotation_euler=(0,0,0)
    finish('Bedok Festival Dragon Boat',11.7,(0,0,1),(-1,-.57,.55))


if __name__ == '__main__':
    build()
