"""Original SG/MY mall bak kwa concession: Bara Selat.
Nominal envelope 4.80 x 2.25 x 3.15 m; centre of the front threshold at Z=0,
customer side -Y (+Z in glTF). The 0.1 m base can be recessed into the floor.
Static visual asset. Original art and fixed detail seed; no external input.
Blender 5.2.3: blender -b --python generate.py
"""

# Shared construction helpers, embedded to keep this generator standalone.
import math
import random
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
        scene.cycles.samples = 28
        scene.cycles.use_denoising = True
    else:
        scene.eevee.taa_render_samples = 48
        scene.eevee.use_raytracing = True
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -.58
    scene.render.resolution_x = 1150
    scene.render.resolution_y = 920
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 65
    return scene


def deliver(direction, backdrop, margin=1.19, engine='CYCLES'):
    objs = bake()
    dest = Path(__file__).resolve().parent
    assert abs(min(v.co.z for o in objs for v in o.data.vertices)) < 1e-6
    objs[0]['asset_id'] = dest.name
    objs[0]['units'] = 'metre'
    objs[0]['role'] = 'Static visual mesh (no collider or clips)'
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
                                  export_animations=False, export_extras=True)
        assert (dest/'model.glb').stat().st_size <= 2_000_000
    scene = studio(direction, backdrop, margin, engine)
    scene.render.filepath = str(dest/'preview.png')
    bpy.ops.render.render(write_still=True)


# Purpose-built details. Unless stated otherwise, lettering faces the customer at -Y.
def palette(spec):
    return {name: mat(name, *properties.split()) if ' ' not in properties else
            mat(name, properties.split()[0], *map(float, properties.split()[1:]))
            for name, properties in spec.items()}


def band(x, y, z, w, h, lining, ink, line, size=None, group='Graphics'):
    plaque(line + ' | panel', x, y, z, w, h, .026, min(h*.34,.092), lining, group)
    label(line, (x,y-.015,z), size or h*.52, ink, w*.9, group=group)


def framed(x, y, z, w, h, rim, inner, title, detail, ink, accent):
    plaque(title+' | frame', x,y,z,w,h,.068,.059,rim)
    plaque(title+' | print', x,y-.036,z,w-.07,h-.07,.012,.037,inner)
    label(title,(x,y-.044,z+h*.19),h*.21,ink,w*.83)
    box(title+' | rule',(x,y-.045,z+h*.02),(w*.7,.004,.009),accent,.001,'Graphics')
    label(detail,(x,y-.044,z-h*.16),h*.113,ink,w*.81)


def bar(name, a, b, width, depth, material, group='Structure', bevel=.006):
    a,b = Vector(a),Vector(b)
    obj = box(name,(0,0,0),(width,depth,(b-a).length),material,bevel,group)
    obj.location = (a+b)/2
    obj.rotation_euler = (b-a).to_track_quat('Z','Y').to_euler()
    return obj


def rail(name, a, b, radius, material, group='Structure', sides=12):
    return tube(name,[a,b],radius,material,group,sides)


def patch(name, outline, y, material, group='Graphics'):
    return prism(name,outline,-y-.002,-y+.002,material,'NEG_Y',group=group)


def diamond(name,x,y,z,w,h,material):
    return patch(name,[(x+w/2,z),(x,z+h/2),(x-w/2,z),(x,z-h/2)],y,material)


def globe(name, xyz, radii, material, group='Fixtures', phase=0.0, sides=14, bands=8):
    x,y,z = xyz
    rx,ry,rz = radii
    co,si = math.cos(phase),math.sin(phase)
    points = [(x,y,z-rz)]
    for j in range(1,bands):
        t = -PI/2+PI*j/bands
        for i in range(sides):
            a = TAU*i/sides
            u,v = rx*math.cos(t)*math.cos(a), ry*math.cos(t)*math.sin(a)
            points.append((x+co*u-si*v,y+si*u+co*v,z+rz*math.sin(t)))
    points.append((x,y,z+rz))
    faces = []
    for i in range(sides):
        i1,j1 = i+1,(i+1)%sides+1
        faces.append((0,j1,i1))
        for q in range(bands-2):
            a,b = q*sides+i1,q*sides+j1
            faces.append((a,b,b+sides,a+sides))
        faces.append((i1+(bands-2)*sides,j1+(bands-2)*sides,len(points)-1))
    return mesh(name,points,faces,material,group=group,smooth=True)


def plant(x,y,z,scale,pot,soil,greens,seed):
    rng = random.Random(seed)
    lathe('Tapered planter',x,y,[(r*scale,z+h*scale) for r,h in
          ((.17,0),(.19,.02),(.23,.31),(.23,.35),(.205,.35),(.195,.30))],pot,24,'Planting')
    lathe('Potting bed',x,y,[(.209*scale,z+.301*scale),(.209*scale,z+.324*scale)],soil,24,'Planting')
    for i in range(12):
        a = TAU*i/12+rng.uniform(-.17,.17)
        d = Vector((math.cos(a),math.sin(a),0))
        e = Vector((-d.y,d.x,0))
        base = Vector((x,y,z+scale*.31))
        run, height = rng.uniform(.16,.49)*scale,rng.uniform(.36,.72)*scale
        root = base+.064*scale*d
        mid = base+run*.39*d+Vector((0,0,height*.89))
        tip = base+run*d+Vector((0,0,height))
        width = e*scale*rng.uniform(.066,.108)
        fold = mid+Vector((0,0,.034*scale))
        rail('Leaf stem',root,mid,.006*scale,greens[0],'Planting',6)
        fs = [(0,1,4),(0,4,3),(1,2,4),(4,2,3)]
        mesh('Folded tropical leaf',[root, mid-width,tip,mid+width,fold], fs+[
             tuple(reversed(f)) for f in fs],greens[i%len(greens)],group='Planting')


def rotated_box(name, center, dims, angle, material, group='Fixtures', bevel=.011):
    o = box(name,(0,0,0),dims,material,bevel,group)
    o.location = center
    o.rotation_euler.z = angle
    return o


def ceiling_light(x,y,z,w,frame,lens):
    box('Linear luminaire housing',(x,y,z),(w,.075,.045),frame,.009,'Lighting')
    box('Warm diffuser',(x,y,z-.024),(w-.06,.043,.010),lens,.003,'Lighting')


def seat(x,y,z,mat_frame,mat_shell,sw=.43):
    box('Seat foot frame',(x,y,z+.045),(sw,.43,.090),mat_frame,.026,'Seating')
    box('Seat pedestal',(x,y,z+.21),(sw*.54,.31,.34),mat_frame,.028,'Seating')
    box('Seat cushion',(x,y,z+.417),(sw,.45,.105),mat_shell,.047,'Seating')
    box('Seat back',(x,y-.19,z+.62),(sw,.10,.405),mat_shell,.046,'Seating')


TITLE = 'Bara Selat | Bak Kwa Concession'
reset()
m = palette(dict(Oxblood='762D2B', Cinnabar='AE463B', Clay='D17256', Gold='E8A85B',
                 Bone='F8E8CB', Ink='322830', BrushedBronze='B78348 .32 .48',
                 Ember='975138 .43', Glaze='572B25 .30', Smoke='B86F44 .45',
                 CaseGlass='E5E9ED .21 0 0 .09', Lamp='FFE0A5 .28 0 1.0',
                 Stone='A3998B', Ash='555059', Tray='5D4543'))
box('Lease-line curb',(0,.865,.048),(4.76,2.02,.096),m['Stone'],.013)
box('Rear shell',(0,1.83,1.527),(4.76,.124,2.87),m['Oxblood'],.031)
box('Canopy underside',(0,.868,2.894),(4.76,2.02,.205),m['Oxblood'],.033)
for s in (-1,1):
    box('Terracotta end post',(s*2.28,.045,1.52),(.195,.41,2.85),m['Oxblood'],.022)
    box('Apron return',(s*2.265,.80,.492),(.215,1.18,.791),m['Cinnabar'],.022)
    box('Bronze end reveal',(s*2.28,-.162,1.525),(.031,.02,2.66),m['BrushedBronze'],.006,'Trim')
plaque('Rounded enamel fascia',0,-.214,2.906,4.8,.49,.146,.152,m['Ink'])
plaque('Fascia face',0,-.291,2.907,4.6,.38,.035,.129,m['Oxblood'])
label('BARA SELAT',(-.075,-.312,2.945),.259,m['Bone'],2.65)
label('CHARCOAL BAK KWA  /  SERUNDING & GIFTS',(-.075,-.312,2.779),.080,m['Gold'],3.12)
band(1.83,-.317,2.927,.60,.18,m['Clay'],m['Bone'],'B1-17')
# Original ember emblem and curved flame strokes, not a copied mark.
disc_front('Ember emblem',-1.92,-.318,2.907,.146,.041,m['Gold'])
for dx,zoff in [(-.051,-.008),(0,.017),(.051,-.008)]:
    line_front('Ember curl',[(-1.92+dx-.019,2.84+zoff),(-1.92+dx+.003,2.874+zoff),
               (-1.92+dx-.012,2.905+zoff),(-1.92+dx+.014,2.943+zoff)],-.342,.011,m['Oxblood'])
# Slatted shop lining and bold prints behind the service line.
for i in range(30):
    x = -2.18+i*.1504
    box('Glazed ceramic batten',(x,1.749,1.50),(.094,.058,2.69),m['Cinnabar'],.014,'Cladding')
for x,t,d,board in [(-1.46,'BAK KWA','SLICED  /  CHILLI','Bone'),
                    (0,'PANGGANG','CHARCOAL GRILLED','Gold'),
                    (1.46,'HADIAH','PACKED TO GIFT','Bone')]:
    framed(x,1.697,1.91,1.31,.59,m['Ink'],m[board],t,d,m['Oxblood'],m['Clay'])
for x in (-1.15,1.17):
    ceiling_light(x,.71,2.757,1.77,m['BrushedBronze'],m['Lamp'])
# Display case, chopped into three trays, and an open gift collection point.
box('Counter body',(0,.33,.517),(4.20,.75,.842),m['Oxblood'],.043,'Counter')
box('Stone lip',(0,.315,.95),(4.34,.838,.09),m['Bone'],.025,'Counter')
box('Recessed kickplate',(0,-.029,.20),(4.21,.056,.17),m['Ink'],.008,'Counter')
for i in range(32):
    x = -2.03+i*.13
    plaque('Moulded apron scale',x,-.052,.526,.106,.503,.054,.041,
           m['Cinnabar'] if i<22 else m['Clay'],'Counter')
band(-.71,-.095,.584,1.32,.214,m['Ink'],m['Gold'],'PILIH  /  PICK')
band(1.48,-.095,.584,1.08,.214,m['Oxblood'],m['Bone'],'AMBIL  /  COLLECT')
for x in (-2.02,.81):
    for y in (-.009,.60):
        box('Case corner upright',(x,y,1.175),(.035,.035,.377),m['BrushedBronze'],.008,'Case Frame')
for z in (1.009,1.357):
    for y in (-.009,.60):
        box('Case horizontal frame',(-.605,y,z),(2.86,.034,.034),m['BrushedBronze'],.004,'Case Frame')
pane('Display front',-.605,-.006,1.184,2.82,.32,m['CaseGlass'])
mesh('Display glass top',[(-2.02,-.009,1.357),(.81,-.009,1.357),(.81,.60,1.357),(-2.02,.60,1.357)],
     [(0,1,2,3)],m['CaseGlass'],group='Glazing')
rng = random.Random(716)
for i,(x,name,material) in enumerate([(-1.55,'ASLI','Ember'),(-.60,'PEDAS','Glaze'),(.35,'MADU','Smoke')]):
    box('Enamel tray',(x,.31,1.015),(.85,.53,.041),m['Tray'],.017,'Food Display')
    for j in range(3):
        for k in range(3):
            dx = (j-1)*.232
            y = .184+k*.113+rng.uniform(-.013,.013)
            for layer in range(2):
                z = 1.047 + k*.016+layer*.019
                rotated_box('Glazed overlapping pork slice',(x+dx+rng.uniform(-.014,.014),y,z),
                            (.212,.162,.029),rng.uniform(-.14,.14),m[material],'Food Display',.013)
            for u in range(3):
                rotated_box('Dark grill stripe',(x+dx+(u-1)*.039,y,z+.015),(.012,.110,.003),
                            -.09,m['Glaze'],'Food Display',.001)
    band(x,-.032,1.089,.44,.122,m['Ink'],m['Bone'],name,.066)
for i,(x,material) in enumerate([(1.16,'Clay'),(1.67,'Cinnabar'),(1.57,'Oxblood')]):
    y,z = .39-i*.019, 1.07+(i==2)*.145
    box('Bak kwa gift tin',(x,y,z),(.43,.35,.145),m[material],.039,'Gift Display')
    box('Gift tin rolled lid',(x,y,z+.078),(.441,.356,.035),m['Gold'],.013,'Gift Display')
    diamond('Gift tin imprint',x,y-.176,z,.134,.073,m['Bone'])
box('Rear paper wrapping ledge',(1.20,1.47,.959),(2.05,.47,.077),m['Ink'],.018,'Gift Display')
for i in range(5):
    box('Folded paper order bag',(.93+i*.22,1.49,1.155),(.175,.110,.315),m['Bone'],.021,'Gift Display')
    diamond('Order bag seal',.93+i*.22,1.433,1.197,.065,.065,m['Cinnabar'])
deliver((-.22,-1,.215),'CCB9AC',margin=1.16)
