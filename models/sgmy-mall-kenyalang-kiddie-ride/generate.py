"""Kenyalang: coin-operated Sarawak hornbill ride for a mall arcade.
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

def rail(name, a, b, radius, material, group='Structure', sides=12):
    return tube(name,[a,b],radius,material,group,sides)

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


TITLE='Kenyalang | Hornbill kiddie ride'
reset()
ink,ivory,gold,orange,teal,foam,red,steel,rubber=colors(Feather='243640 .33',Porcelain='F5ECD4 .32',Casque='EEAF37 .28',Persimmon='DE7034 .30',Jungle='367777 .33',Lagoon='9DCAB9',Seat='AE554B .44',Nickel='ABB8AF .26 .65',Rubber='3F4643')
slab('Rubber skid',0,0,0,2.13,.93,.11,.31,rubber)
slab('Rocker drive base',0,0,.11,2.22,1.0,.267,.33,teal)
slab('Cream pinstripe',0,0,.364,2.19,.98,.033,.32,ivory)
slab('Motor hood',0,0,.394,2.14,.94,.076,.31,foam)
for x in (-.42,.41):
    lathe('Bellows root',x,0,[(.107,.464),(.107,.65)],rubber,24,'Motion mount')
    for j in range(4): lathe('Bellows rib',x,0,[(.10,.48+.034*j),(.126,.49+.034*j),(.118,.503+.034*j)],ink,24,'Motion mount')
# Rings perpendicular to X: taper the bird, tail and bill in two axes.
def loft(name,sections,material,n=32):
    vs=[(x,w*math.cos(TAU*i/n),z+h*math.sin(TAU*i/n)) for x,z,w,h in sections for i in range(n)]
    faces=[tuple(reversed(range(n))),tuple(range(len(vs)-n,len(vs)))]
    for k in range(len(sections)-1):
        for i in range(n):
            j=(i+1)%n; faces.append((k*n+i,k*n+j,(k+1)*n+j,(k+1)*n+i))
    return mesh(name,vs,faces,material,group='Fibreglass bird',smooth=True)
loft('Hornbill body',[(-.74,1.20,.08,.10),(-.65,1.14,.25,.34),(-.45,1.05,.34,.41),(-.18,.96,.36,.36),(.27,.91,.34,.30),(.57,.93,.26,.25),(.85,.99,.11,.10)],ink)
loft('Tail fan',[(.51,.96,.23,.10),(.78,.97,.23,.093),(1.13,1.01,.20,.077),(1.22,1.04,.16,.059)],ivory)
loft('Tail stripe',[(.94,.988,.226,.089),(1.05,1.00,.217,.086)],ink)
globe('Glossy head',(-.60,0,1.39),(.34,.279,.356),ink,'Fibreglass bird',sides=40,bands=18)
loft('Downcurved bill',[(-1.36,1.30,.012,.015),(-1.28,1.38,.055,.051),(-1.13,1.45,.094,.092),(-.93,1.46,.14,.119),(-.78,1.45,.163,.128)],gold)
loft('Sculpted casque',[(-1.23,1.75,.018,.023),(-1.16,1.702,.074,.084),(-1.02,1.652,.100,.092),(-.88,1.627,.124,.105),(-.73,1.63,.103,.074)],orange)
for s in (-1,1):
    globe('Ivory orbital patch',(-.735,s*.223,1.481),(.11,.046,.100),ivory,'Fibreglass bird',sides=26)
    globe('Gold iris',(-.75,s*.258,1.489),(.052,.021,.052),gold,'Fibreglass bird',sides=24)
    globe('Eye',(-.76,s*.272,1.496),(.029,.013,.031),ink,'Fibreglass bird',sides=20)
    # Individually moulded primary feathers sweep towards the tail.
    for j in range(3):
        ob=globe('Folded wing feather',(0,0,0),(.405-.044*j,.081,.092),ink if j==1 else teal,'Fibreglass bird',sides=22)
        ob.location=(.24+.042*j,s*(.278+.022*j),1.019-.090*j); ob.rotation_euler.y=-.14
    leg('Footboard bracket',(.04,s*.23,.73),(.04,s*.419,.69),.028,steel)
    slab('Ribbed foot plate',.015,s*.44,.683,.43,.145,.035,.054,rubber)
    for j in range(6): box('Foot tread',(-.143+j*.060,s*.445,.725),(.021,.103,.016),foam,.004)
    leg('Grab rail',(-.45,s*.16,1.33),(-.45,s*.377,1.36),.026,steel)
    leg('Rubber grip',(-.45,s*.31,1.354),(-.45,s*.447,1.37),.04,red)
globe('Saddle pad',(.12,0,1.232),(.399,.257,.094),red,'Saddle',sides=36,bands=14)
globe('Raised cantle',(.444,0,1.29),(.113,.247,.155),red,'Saddle',sides=32)
wall('Coin fascia',.60,-.507,.247,.34,.177,.033,.037,ink)
box('Token slot',(.60,-.529,.275),(.15,.008,.021),steel,.006)
label('TOKEN',(.60,-.527,.214),.047,ivory,.225)
label('KENYALANG',(-.305,-.503,.237),.142,ivory,1.14)
deliver((-.38,-1,.30),'C0C4B6',1.13)
