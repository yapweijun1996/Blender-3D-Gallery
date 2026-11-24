"""Anyam Cahaya: a freestanding showroom for hand-woven rattan pendant lamps.
Original static mall fixture; built-in font, procedural geometry and materials only.
Metres; shared floor pivot, customer side -Y. Run with blender -b -P generate.py.
"""

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
        scene.cycles.samples = 18
        scene.cycles.max_bounces = 5
        scene.cycles.use_denoising = True
    else:
        scene.eevee.taa_render_samples = 48
        scene.eevee.use_raytracing = True
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -.58
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 880
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
    flags = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    export = '--preview-only' not in flags
    print(f'{TITLE}: {sum(len(o.data.polygons) for o in objs):,} triangles')
    if export:
        bpy.ops.export_scene.gltf(filepath=str(dest/'model.glb'), export_format='GLB',
                                  export_draco_mesh_compression_enable=True,
                                  export_draco_mesh_compression_level=6,
                                  export_draco_position_quantization=19,
                                  export_draco_normal_quantization=12,
                                  export_draco_texcoord_quantization=16,
                                  export_cameras=False, export_lights=False,
                                  export_animations=False, export_extras=True)
        assert (dest/'model.glb').stat().st_size <= 2_000_000
    if '--export-only' in flags:
        return
    scene = studio(direction, backdrop, margin, engine)
    scene.render.filepath = str(dest/'preview.png')
    bpy.ops.render.render(write_still=True)

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

def colors(**swatches):
    return [mat(name, *([s.split()[0]] + [float(n) for n in s.split()[1:]])) for name,s in swatches.items()]

def slab(name,x,y,z,w,d,h,r,material,group='Cabinetry'):
    return prism(name,rounded(w,d,r,(x,y),7),z,z+h,material,bevel=min(.01,h*.14),group=group)

def leg(name,a,b,r,material):
    return rail(name,a,b,r,material,'Frame',16)

def wall(name,x,y,z,w,h,d,r,m):
    return plaque(name,x,y,z,w,h,d,r,m,'Shell')


TITLE='Anyam Cahaya | Woven lamp showroom'
reset()
wood,dark,cane,pale,tea,ivory,jade,bulb,brass=colors(Teak='8B624B',Char='343D39',Rattan='C39A60 .51',Heartwood='E3C38B',TeaDyed='AD7851',Linen='F0E3C1',Pandan='516E5B',Opal='FFF0C9 .31 0 .32',Brass='B79861 .33 .48')
slab('Soft corner platform',0,0,0,4.12,1.38,.124,.24,dark)
slab('Showroom decking',0,0,.124,4.10,1.36,.071,.23,wood)
for x in (-1.90,1.90):
    slab('Arch socket',x,.04,.195,.23,.55,.15,.077,brass)
    for y in (-.14,.22):
        bar('Twin hardwood upright',(x,y,.30),(x,y,2.90),.135,.13,wood,bevel=.024)
    for z in (.43,1.35,2.42): box('Rung',(x,.04,z),(.137,.44,.070),tea,.015)
slab('Crown beam',0,.04,2.85,4.12,.62,.20,.21,wood)
wall('Maker fascia',0,-.27,2.972,3.97,.37,.099,.157,jade)
label('A N Y A M   C A H A Y A',(0,-.323,3.004),.215,ivory,2.95)
label('BENGKEL  ROTAN     /     JOHOR',(0,-.323,2.849),.065,pale,2.32)
for x in (-1.72,1.72): diamond('Weave seal',x,-.324,2.98,.168,.150,pale)
# Profiled shades: opposite helical families interlace by alternating radial deflection.
for j,(x,base,height,profile,title) in enumerate([(-1.15,1.48,.66,[(0,.43),(.15,.51),(.46,.47),(.72,.30),(1,.11)],'LABU'),(0,1.17,.91,[(0,.185),(.20,.32),(.51,.33),(.78,.24),(1,.095)],'PADI'),(1.15,1.55,.54,[(0,.47),(.14,.53),(.39,.43),(.66,.22),(1,.115)],'PAYUNG')]):
    def radius(t):
        for (a,r),(b,s) in zip(profile,profile[1:]):
            if t<=b: return r+(s-r)*(t-a)/(b-a)
        return profile[-1][1]
    top=base+height
    leg('Braided flex',(x,.03,top),(x,.03,2.86),.011,dark)
    lathe('Ceiling rose',x,.03,[(.061,2.806),(.084,2.84),(.084,2.85)],brass,24,'Luminaires')
    lathe('Ferrule',x,.03,[(.059,top-.035),(.069,top+.016),(.045,top+.076)],brass,28,'Luminaires')
    leg('Lampholder drop',(x,.03,top),(x,.03,base+.50*height),.023,brass)
    globe('Opal diffuser',(x,.03,base+.39*height),(.123,.123,.143),bulb,'Luminaires',sides=32,bands=14)
    for side in (-1,1):
        for i in range(18):
            points=[]
            for k in range(29):
                t=k/28; a=TAU*(i/18+side*.142*t); r=radius(t)+side*.009*math.cos(t*PI*10.224)
                points.append((x+r*math.cos(a),.03+r*math.sin(a),base+t*height))
            tube('Split cane strand',points,.010 if j!=1 else .0085,cane if side==1 else pale,'Woven shades',6,reference=(0,0,1))
    for t in (0,.035,.18,.49,.79,.971,1):
        r=radius(t); coords=[(x+r*math.cos(TAU*k/48),.03+r*math.sin(TAU*k/48),base+t*height) for k in range(49)]
        tube('Bound hoop',coords,.014 if t in (0,1) else .009,tea if t in (0,1) else cane,'Woven shades',8)
    # Low plinth and engraved specimen card below each suspended light.
    slab('Display block',x,.05,.195,.89,.72,.193,.09,jade)
    label('0'+str(j+1)+'   /   '+title,(x,-.316,.292),.085,ivory,.77)
deliver((.29,-1,.19),'C0BAA8',1.13)
