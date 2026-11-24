"""Build a static, 30-degree SG/MY mall escalator module.
Origin: centre of the lower landing's approach edge at the base (0,0,0).
Landing surfaces: Z=.08 and Z=3.68; nominal rise 3.60 m, extending along +Y.
No motor animation, rider logic, or separate collision geometry.

Usage: blender -b --python generate.py
Blender 5.2.3; metres, Z up, customer side -Y (+Z in glTF).
Original deterministic geometry and artwork; built-in font, no external inputs.
Export requires a glTF KHR_draco_mesh_compression decoder at runtime.
"""

# Shared construction helpers, embedded to keep this generator standalone.
import math
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector

PI = math.pi
TAU = math.tau
PARTS = defaultdict(list)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0


def linear(channel):
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def mat(name, rgb, rough=0.47, metal=0.0, glow=0.0, alpha=1.0):
    color = tuple(linear(int(rgb[i:i+2], 16) / 255) for i in (0, 2, 4))
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, alpha)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    bsdf.inputs['Alpha'].default_value = alpha
    if glow:
        bsdf.inputs['Emission Color'].default_value = (*color, 1)
        bsdf.inputs['Emission Strength'].default_value = glow
    if alpha < 1.0:
        material.surface_render_method = 'BLENDED'
    return material


def add(name, data, material, group):
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(material)
    if group:
        PARTS[group].append(obj)
    return obj


def mesh(name, vertices, faces, material, bevel=0, group='Structure', smooth=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = add(name, data, material, group)
    if smooth:
        for p in data.polygons:
            p.use_smooth = True
    if bevel:
        edge = obj.modifiers.new('Machined edge', 'BEVEL')
        edge.width = bevel
        edge.segments = 2
        edge.harden_normals = True
    return obj


def box(name, at, dims, material, bevel=0.012, group='Structure'):
    x, y, z = at
    a, b, c = (v * 0.5 for v in dims)
    vs = [(x+sx*a, y+sy*b, z+sz*c) for sz in (-1,1)
          for sx, sy in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    return mesh(name, vs, [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),
                           (2,3,7,6),(3,0,4,7)], material, bevel, group)


def prism(name, outline, lo, hi, material, axis='Z', bevel=0, group='Structure'):
    # Outline is counterclockwise as viewed from the positive axis.
    n = len(outline)
    def xyz(u, v, w):
        return {'Z': (u,v,w), 'X': (w,u,v), 'NEG_Y': (u,-w,v)}[axis]
    vs = [xyz(u,v,w) for w in (lo,hi) for u,v in outline]
    fs = [tuple(reversed(range(n))), tuple(range(n,2*n))]
    fs += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name, vs, fs, material, bevel, group)


def rounded(w, h, r, center=(0,0), steps=5):
    cx, cy = center
    corners = [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,PI/2),
               (-w/2+r,-h/2+r,PI),(w/2-r,-h/2+r,1.5*PI)]
    return [(cx+x+r*math.cos(a+t*PI/(2*steps)), cy+y+r*math.sin(a+t*PI/(2*steps)))
            for x,y,a in corners for t in range(steps+1)]


def plaque(name, x, y, z, w, h, depth, radius, material, group='Graphics'):
    return prism(name, rounded(w,h,radius,(x,z)), -y-depth/2, -y+depth/2,
                 material, 'NEG_Y', min(depth*.23,.012), group)


def ring(name, x, y, z, w, h, r, thickness, depth, material, group='Structure'):
    outside = rounded(w,h,r,(x,z))
    inside = rounded(w-2*thickness,h-2*thickness,r-thickness,(x,z))
    n = len(outside)
    vs = [(u,k,v) for k in (y+depth/2, y-depth/2) for pts in (outside,inside) for u,v in pts]
    fs = []
    for i in range(n):
        j = (i+1)%n
        fs += [(i,i+2*n,j+2*n,j),(i+n,j+n,j+3*n,i+3*n),
               (i+2*n,i+3*n,j+3*n,j+2*n),(i,j,j+n,i+n)]
    return mesh(name, vs, [tuple(reversed(f)) for f in fs], material, min(thickness*.18,.012), group)


def lathe(name, x, y, profile, material, sides=32, group='Structure', caps=True):
    # Profile runs from bottom to top on the outside, then back down any inside wall.
    vs = [(x+r*math.cos(TAU*i/sides), y+r*math.sin(TAU*i/sides), z)
          for r,z in profile for i in range(sides)]
    n = len(profile)
    fs = [tuple(reversed(range(sides))),tuple(range((n-1)*sides,n*sides))] if caps else []
    for k in range(n-1):
        for i in range(sides):
            j = (i+1)%sides
            fs.append((k*sides+i,k*sides+j,(k+1)*sides+j,(k+1)*sides+i))
    obj = mesh(name, vs, fs, material, group=group, smooth=True)
    if caps:
        for face in list(obj.data.polygons)[:2]:
            face.use_smooth = False
    return obj


def tube(name, points, radius, material, group='Structure', sides=10, vertical_scale=1.0, reference=None):
    path = [Vector(p) for p in points]
    vs = []
    for i,p in enumerate(path):
        tangent = (path[min(i+1,len(path)-1)]-path[max(0,i-1)]).normalized()
        ref = Vector(reference) if reference else (Vector((0,0,1)) if abs(tangent.z)<0.97 else Vector((0,1,0)))
        u = tangent.cross(ref).normalized()
        v = tangent.cross(u)
        for j in range(sides):
            a = TAU*j/sides
            vs.append(p+radius*(u*math.cos(a)+v*math.sin(a)*vertical_scale))
    fs = [tuple(reversed(range(sides))), tuple(range(len(vs)-sides,len(vs)))]
    for k in range(len(path)-1):
        for i in range(sides):
            j = (i+1)%sides
            fs.append((k*sides+i,k*sides+j,(k+1)*sides+j,(k+1)*sides+i))
    obj = mesh(name, vs, fs, material, group=group, smooth=True)
    for face in list(obj.data.polygons)[:2]:
        face.use_smooth = False
    return obj


def disc_front(name, x, y, z, r, depth, material, group='Graphics', sides=32):
    return prism(name, [(x+r*math.cos(TAU*i/sides),z+r*math.sin(TAU*i/sides))
                        for i in range(sides)], -y-depth/2, -y+depth/2,
                 material, 'NEG_Y', min(depth*.2, .004), group)


def pane(name, x, y, z, w, h, material):
    # Single sheet: no double tint on the back face of the panel.
    return mesh(name, [(x-w/2,y,z-h/2),(x+w/2,y,z-h/2),(x+w/2,y,z+h/2),
                       (x-w/2,y,z+h/2)], [(0,1,2,3)], material, group='Glazing')


def label(line, at, size, material, max_width=None, align='CENTER',
          group='Graphics', on_top=False, extrude=0.0):
    # Blender's built-in Bfont keeps lettering reproducible without an external font.
    data = bpy.data.curves.new(line, 'FONT')
    data.body = line
    data.align_x = align
    data.align_y = 'CENTER'
    data.size = size
    data.space_character = 1.05
    data.resolution_u = 5
    data.extrude = extrude
    obj = add(line, data, material, group)
    obj.location = at
    if not on_top:
        obj.rotation_euler.x = PI/2
    if max_width:
        x_min = min(v[0] for v in obj.bound_box)
        x_max = max(v[0] for v in obj.bound_box)
        # bound_box may not be evaluated yet; constrain the final width in bake().
        if x_max > x_min:
            obj.scale.x = min(1.0, max_width / (x_max-x_min))
        obj['max_width'] = max_width
    return obj


def line_front(name, xz, y, radius, material, group='Graphics'):
    return tube(name, [(x,y,z) for x,z in xz], radius, material, group, sides=8)


def bake():
    # Flatten by semantic group; each group uses zero transforms at the same floor pivot.
    dg = bpy.context.evaluated_depsgraph_get()
    output = []
    for group, objects in PARTS.items():
        vs, fs, ids, uvs, normals, materials = [], [], [], [], [], []
        for obj in objects:
            state = obj.evaluated_get(dg)
            src = state.to_mesh()
            transform = state.matrix_world.copy()
            if 'max_width' in obj and len(src.vertices):
                xs = [v.co.x for v in src.vertices]
                width = (max(xs)-min(xs))*transform.col[0].xyz.length
                if width > obj['max_width']:
                    for j in range(3):
                        transform[j][0] *= obj['max_width']/width
            normal_matrix = transform.to_3x3().inverted_safe().transposed()
            offset = len(vs)
            points = [transform @ v.co for v in src.vertices]
            vs.extend(points)
            material = obj.data.materials[0]
            if material not in materials:
                materials.append(material)
            material_id = materials.index(material)
            src.calc_loop_triangles()
            src_normals = src.corner_normals
            for tri in src.loop_triangles:
                a,b,c = (points[k] for k in tri.vertices)
                normal = (b-a).cross(c-a)
                if normal.length_squared < 1.0e-17:
                    continue
                fs.append(tuple(offset+k for k in tri.vertices))
                ids.append(material_id)
                axis = max(range(3), key=lambda k: abs(normal[k]))
                i,j = ((1,2),(0,2),(0,1))[axis]
                flip = -1 if normal[axis] < 0 else 1
                uvs.extend((p[i]*flip,p[j]) for p in (a,b,c))
                normals.extend((normal_matrix @ src_normals[k].vector).normalized() for k in tri.loops)
            state.to_mesh_clear()
        # Discard vertices referenced only by degenerate conversion triangles.
        used = sorted({i for f in fs for i in f})
        index = {old:new for new,old in enumerate(used)}
        data = bpy.data.meshes.new(group)
        data.from_pydata([vs[i] for i in used], [], [tuple(index[i] for i in f) for f in fs])
        data.update()
        for material in materials:
            data.materials.append(material)
        data.polygons.foreach_set('material_index', ids)
        data.polygons.foreach_set('use_smooth', [True]*len(ids))
        uv_layer = data.uv_layers.new(name='UV0')
        uv_layer.uv.foreach_set('vector', [n for pair in uvs for n in pair])
        data.normals_split_custom_set(normals)
        obj = bpy.data.objects.new(f'{TITLE} - {group}', data)
        bpy.context.collection.objects.link(obj)
        output.append(obj)
    for objects in PARTS.values():
        for obj in objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    return output


def studio(direction, backdrop, margin=1.19, engine='BLENDER_EEVEE'):
    scene = bpy.context.scene
    coords = [v.co for o in scene.objects if o.type == 'MESH' for v in o.data.vertices]
    center = Vector([(max(v[i] for v in coords)+min(v[i] for v in coords))/2 for i in range(3)])
    span = max(max(v[i] for v in coords)-min(v[i] for v in coords) for i in range(3))
    arm = Vector(direction).normalized()
    rotation = (-arm).to_track_quat('-Z','Y')
    projection = [rotation.inverted() @ (v-center) for v in coords]
    lo = Vector([min(p[i] for p in projection) for i in range(3)])
    hi = Vector([max(p[i] for p in projection) for i in range(3)])
    target = center + rotation @ Vector(((hi.x+lo.x)/2,(hi.y+lo.y)/2,0))
    camera = bpy.data.objects.new('Preview Camera', bpy.data.cameras.new('Orthographic Preview'))
    bpy.context.collection.objects.link(camera)
    camera.location = target + arm*span*3
    camera.rotation_euler = rotation.to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = max(hi.x-lo.x, (hi.y-lo.y)*1.25)*margin
    scene.camera = camera
    box('Preview Ground', (center.x,center.y,-0.035), (span*200,span*200,0.06),
        mat('Studio Backdrop',backdrop,.82), 0, None)
    world = bpy.data.worlds.new('Studio Ambient')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.37,.43,.52,1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .32
    def area(name, offset, watts, size, color):
        data = bpy.data.lights.new(name, 'AREA')
        light = bpy.data.objects.new(name,data)
        bpy.context.collection.objects.link(light)
        light.location = center + Vector(offset)*span
        light.rotation_euler = (center-light.location).to_track_quat('-Z','Y').to_euler()
        data.energy = watts*span**2
        data.shape = 'DISK'
        data.size = size*span
        data.color = color
    area('Soft Warm Key',(-.65,-.95,1.25),143,1.1,(1,.88,.73))
    area('Cool Front Fill',(.85,-.7,.58),62,1.1,(.75,.86,1))
    area('Overhead Rim',(.2,.9,1.30),186,.9,(1,.95,.86))
    scene.render.engine = engine
    if engine == 'CYCLES':
        scene.cycles.samples = 32
        scene.cycles.use_denoising = True
    else:
        scene.eevee.taa_render_samples = 48
        scene.eevee.use_raytracing = True
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -.58
    scene.render.resolution_x = 1250
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 65
    return scene


def deliver(direction, backdrop, margin=1.19, engine='BLENDER_EEVEE'):
    objs = bake()
    dest = Path(__file__).resolve().parent
    if '--' in sys.argv and '--preview-only' in sys.argv[sys.argv.index('--')+1:]:
        export = False
    else:
        export = True
    print(f'{TITLE}: {sum(len(o.data.polygons) for o in objs):,} triangles')
    if export:
        bpy.ops.export_scene.gltf(filepath=str(dest/'model.glb'), export_format='GLB',
                                  export_draco_mesh_compression_enable=True,
                                  export_draco_mesh_compression_level=6,
                                  export_draco_position_quantization=18,
                                  export_draco_normal_quantization=12,
                                  export_draco_texcoord_quantization=16,
                                  export_cameras=False, export_lights=False,
                                  export_animations=False)
        assert (dest/'model.glb').stat().st_size <= 2_000_000
    scene = studio(direction, backdrop, margin, engine)
    scene.render.filepath = str(dest/'preview.png')
    bpy.ops.render.render(write_still=True)


TITLE = 'Serambi Court Escalator'


def build():
    reset()
    frame = mat('Escalator Brushed Aluminium','B5BFC4',.33,.55)
    inset = mat('Jade Cladding Enamel','39736D',.39,.25)
    cast = mat('Cast Step Aluminium','697578',.47,.38)
    tread = mat('Tread Rib High Surface','A3ADB0',.39,.5)
    deep = mat('Step Groove Shadow','374148',.54,.25)
    rail = mat('Charcoal Handrail Rubber','242D34',.30)
    gasket = mat('Glass Seat Gasket','374946',.47)
    glass = mat('Escalator Laminated Glass','9BDDD2',.19,alpha=.24)
    amber = mat('Safety Yellow Powder Coat','E2A733',.44)
    white = mat('Wayfinding Ivory','F9ECD9',.43)
    light = mat('Entry Arrow LED','84F09F',.4,glow=1.35)
    sign = mat('Indicator Black Nylon','123C40',.32)
    way = 'Wayfinding'
    steps = 'Tread and Landing'

    n, rise, front = 18, .2, 1.38
    slope = math.tan(PI/6)
    pitch = rise/slope
    top = front+n*pitch
    end = top+1.42
    low = .08
    high = low+n*rise
    width = 1.005
    def softmax(x):
        if x < -.29:
            return 0
        if x > .29:
            return x
        return (x+.29)**2/1.16
    def deck(y):
        return low+slope*(softmax(y-front+pitch/2)-softmax(y-top+pitch/2))
    profile = [(0,0),(1.36,0),(1.76,.012),(top-.30,high-.54),(end,high-.54),
               (end,high-.045),(top,high-.045),(1.38,low-.045),(0,low-.045)]
    prism('Full escalator truss housing',profile,-.655,.655,frame,'X',.012)
    box('Entry mounting shoe',(0,.66,.014),(1.58,1.32,.028),deep,.006)
    box('Upper saddle',(0,end-.67,high-.531),(1.58,1.34,.034),deep,.008)
    for z,y,d in ((low,front/2,front),(high,(top+end)/2,end-top)):
        box('Landing access floor plate',(0,y,z-.024),(1.39,d,.048),frame,.007,steps)
        for j in range(1,8):
            box('Recessed anti slip blade',(0,y+(j-4)*.103,z+.001),(1.032,.012,.004),deep,.001,steps)
        for side in (-1,1):
            box('Landing lateral caution rail',(side*.591,y,z+.001),(.048,d-.06,.006),amber,.002,steps)
    for y,z in ((front-.066,low),(top+.067,high)):
        box('Comb plate base',(0,y,z+.003),(1.07,.137,.012),amber,.004,steps)
        for k in range(34):
            box('Comb recess',((k-16.5)*.0301,y,z+.01),(.005,.091,.004),deep,0,steps)
    rib_vertices, rib_faces = [], []
    def rib(x,y,z,dx,dy,dz):
        a,b,c=len(rib_vertices),x-dx/2,y-dy/2
        rib_vertices.extend([(xx,yy,zz) for zz in (z,z+dz)
                             for xx, yy in ((b,c),(b+dx,c),(b+dx,c+dy),(b,c+dy))])
        rib_faces.extend(tuple(a+i for i in f) for f in ((3,2,1,0),(4,5,6,7),
                         (0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)))
    for i in range(n):
        y=front+(i+.5)*pitch
        z=low+(i+1)*rise
        box('Cast step body',(0,y,z-.117),(width,pitch-.004,.234),cast,.004,steps)
        box('Riser tread line',(0,y-pitch/2+.001,z-.116),(.945,.005,.115),deep,.002,steps)
        for k in range(31):
            rib((k-15)*.0306,y+.009,z,.015,pitch-.026,.004)
        for side in (-1,1):
            box('Step side caution stripe',(side*.487,y,z+.001),(.026,pitch-.012,.005),amber,.001,steps)
        box('Step nosing safety edge',(0,y-pitch*.5+.011,z+.004),(width,.014,.006),amber,.001,steps)
    mesh('Cast tread micro ribs',rib_vertices,rib_faces,tread,group=steps)

    a,b=.44,end-.47
    rail_level = 1.016
    samples = [0, .17, a] + [a+j*(b-a)/34 for j in range(1,34)] + [b,end-.17,end]
    deck_bottom = [(y,max(.014,deck(y)-.085) if 0<y<end else deck(y)-.042) for y in samples]
    deck_top = [(y,deck(y)+.218) for y in samples]
    def trim_straight(points):
        def bend(a,b,c):
            return abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])) > 1e-7
        return [points[0]]+[b for a,b,c in zip(points,points[1:],points[2:]) if bend(a,b,c)]+[points[-1]]
    def nose(yc,zbase,sign):
        return [(yc+sign*.265*math.sin(PI*i/18),zbase+rail_level-.322+.322*math.cos(PI*i/18))
                for i in range(19)]
    q0,q1=nose(a,low,-1),nose(b,high,1)
    for side in (-1,1):
        x = side*.718
        prism('Formed aluminium side skirt',trim_straight(deck_bottom)+trim_straight(deck_top)[::-1],
              x-.078,x+.078,frame,'X',.009)
        prism('Jade skirt inlay',[(y,z+.125) for y,z in trim_straight(deck_bottom[1:-1])]+
              [(y,z-.035) for y,z in trim_straight(deck_top[1:-1])[::-1]],x+side*.079-.004,x+side*.079+.004,
              inset,'X',.003)
        rail_path = (list(reversed(q0))+[(y,deck(y)+rail_level) for y in samples[3:-3]]+q1)
        tube('Continuous rounded handrail',[(x,y,z) for y,z in rail_path],.055,rail,
             sides=14,vertical_scale=.79,reference=(1,0,0))
        for y,z in ((a,low),(b,high)):
            box('Return newel cap',(x,y,z+.274),(.146,.323,.208),gasket,.039)
            box('Rail tail end seat',(x,y,z+.394),(.123,.109,.203),frame,.018)
        panel_breaks=[a]+[a+(b-a)*i/9 for i in range(1,9)]+[b]
        for i,(start,finish) in enumerate(zip(panel_breaks,panel_breaks[1:])):
            pts=[start+.004+j*(finish-start-.008)/6 for j in range(7)]
            upper=[(x,y,deck(y)+rail_level-.034) for y in pts]
            lower=[(x,y,deck(y)+.19) for y in pts]
            faces=[(j+7,j+8,j+1,j) for j in range(6)]
            mesh('Laminated panel segment',upper+lower,faces if side > 0 else [f[::-1] for f in faces],
                 glass,group='Glazing')
            if i<8:
                y=finish
                tube('Glazing join',[(x,y,deck(y)+.212),(x,y,deck(y)+rail_level-.036)],.007,
                     gasket,sides=8)
            for y in (start+.1,finish-.1):
                box('Glass saddle clamp',(x,y,deck(y)+.227),(.049,.074,.062),frame,.009)
        for which,(y,z,nose_pts) in enumerate(((a,low,q0),(b,high,q1))):
            curve=nose_pts[:11]
            edge=curve[-1][0]
            vertices=[(x,y,z+.21),(x,edge,z+.21)]+[(x,v,w-.027) for v,w in reversed(curve)]
            mesh('Curved end shield',vertices,[tuple(range(len(vertices)))],glass,group='Glazing')

    # Bilingual wayfinding is just geometry; the module has no gameplay logic.
    # Label placed on the visitor-facing bevel of the front finial.
    plaque('Escalator entry base badge',-.681,.017,.149,.199,.215,.027,.031,sign,way)
    label('NAIK',(-.681,.001,.164),.059,white,group=way)
    label('UP',(-.681,.001,.105),.043,light,group=way)
    for side in (-1,1):
        x=side*.713
        prism('Floor level indicator',rounded(.119,.215,.037,(x,.32)),low+.36,low+.382,sign,'Z',.005,way)
        p=[(x-.016,.25),(x+.016,.25),(x+.016,.322),(x+.047,.322),
           (x,.376),(x-.047,.322),(x-.016,.322)]
        prism('Direction arrow',p,low+.382,low+.386,light,'Z',group=way)
    prism('Side livery panel',rounded(1.02,.158,.028,(.769,.17)),.802,.818,sign,'X',.003,way)
    obj=label('KE ARAS 2',(0,0,0),.125,white,.92,group=way)
    obj.location=(.82,.77,.174)
    obj.rotation_euler=(PI/2,0,PI/2)
    deliver((1,-.91,.70),'A7B9BF',1.15)


if __name__ == '__main__':
    build()
