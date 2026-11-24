"""Original SG/MY mall revolving entrance with accessible bypass leaf.
The drum axis is at (0,0) and the pivot is its base; approach is -Y (+Z in
glTF). Nominal envelope 5.63 x 3.25 x 3.17 m. Recess the platform 55 mm for
flush fit. Closed static sample with separate rotor meshes, no collisions
or door behaviours. Original geometry, Blender 5.2.3.
Rebuild: blender -b --python generate.py
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


TITLE = 'Pintu Putar | Revolving Mall Portal'
reset()
m = palette(dict(Navy='253F56', Oyster='D9D9BC', Glass='A0DADB .19 0 0 .12',
      RotorGlass='9DC5D0 .19 0 0 .20', Nickel='A5BABE .25 .63',
      Brass='BA9568 .32 .61', Dusk='597B8F', Blue='43718C', Rubber='3D4753',
      Gold='E3B06A', Lamp='E7FFDB .23 0 .72', Ink='253741', Access='BFDDCE'))
# Separate floor ribbing and static curved wall assemblies sit above the slab.
box('Flush threshold platform',(.43,0,.028),(5.63,3.22,.056),m['Oyster'],.009,'Threshold')
lathe('Segmented revolving threshold',0,0,[(1.36,.051),(1.39,.061),(1.38,.082),(1.35,.087)],
      m['Nickel'],80,'Threshold')
for start,end in [(-128,-52),(52,128)]:
    for k in range(10):
        a = math.radians(start+(end-start)*(k+.5)/10)
        p = (1.42*math.cos(a),1.52*math.sin(a),.061)
        rotated_box('Approach mat serration',p,(.026,.158,.013),a-PI/2,m['Rubber'],'Threshold',.003)
for z,r in [(.15,1.34),(2.44,1.34)]:
    for heading in (0,180):
        arc = [math.radians(heading-46+92*i/28) for i in range(29)]
        tube('Curved static drum rail',[(r*math.cos(a),r*math.sin(a),z) for a in arc],
             .042,m['Brass'],'Drum Frame',12,reference=(0,0,1))
for heading in (0,180):
    arc = [math.radians(heading-46+92*i/24) for i in range(25)]
    for a in (arc[0],arc[len(arc)//2],arc[-1]):
        x,y = 1.34*math.cos(a),1.34*math.sin(a)
        box('Curved drum upright',(x,y,1.324),(.071,.071,2.297),m['Navy'],.012,'Drum Frame')
    for i,(a,b) in enumerate(zip(arc,arc[1:])):
        r = 1.34
        x0,y0,x1,y1 = (r*math.cos(a),r*math.sin(a),r*math.cos(b),r*math.sin(b))
        mesh('Curved drum glazing',[(x0,y0,.182),(x1,y1,.182),(x1,y1,2.441),(x0,y0,2.441)],
             [(0,1,2,3)],m['Glass'],group='Drum Glass')
        for z in (1.010,1.085):
            if i in (2,3,8,9,14,15,20,21):
                bar('Visibility decal',(x0*1.005,y0*1.005,z),(x1*1.005,y1*1.005,z),.028,.008,
                    m['Oyster'],'Drum Graphics',.001)
# A three-wing rotor at rest. The entire centre mechanism shares its own group.
lathe('Stainless centre post',0,0,[(.103,.082),(.112,.115),(.091,.162),(.091,2.464)],
      m['Nickel'],32,'Rotor Frame')
for i in range(3):
    a = math.radians(8+120*i)
    c,s = math.cos(a),math.sin(a)
    for z in (.206,2.30):
        bar('Rotor leaf top/bottom',(c*.065,s*.065,z),(c*1.233,s*1.233,z),
            .055,.056,m['Navy'],'Rotor Frame')
    bar('Rotor door edge',(c*1.234,s*1.234,.205),(c*1.234,s*1.234,2.303),
        .061,.061,m['Navy'],'Rotor Frame')
    mesh('Rotor door leaf glass',[(.07*c,.07*s,.205),(1.234*c,1.234*s,.205),
         (1.234*c,1.234*s,2.3),(.07*c,.07*s,2.3)],[(0,1,2,3)],m['RotorGlass'],group='Rotor Glass')
    for side in (-1,1):
        q = Vector((-s*side,c*side,0))
        a0 = Vector((c*.395,s*.395,1.005))
        b0 = Vector((c*1.1,s*1.1,1.005))
        tube('Rotor push rail',[a0,a0+.087*q,b0+.087*q,b0],.025,m['Brass'],
             'Rotor Frame',12,reference=(0,0,1))
lathe('Coated circular drive crown',0,0,[(1.36,2.441),(1.46,2.468),(1.48,2.52),(1.48,2.706),
      (1.446,2.742),(1.38,2.751)],m['Navy'],80,'Drum Frame')
lathe('Warm circumferential inlay',0,0,[(1.478,2.532),(1.488,2.538),(1.488,2.564),(1.478,2.570)],
      m['Brass'],80,'Drum Frame',caps=False)
for x in (-.66,.66):
    ceiling_light(x,-.347,2.452,.77,m['Brass'],m['Lamp'])
# A glazed accessible side door and fixed sidelight sit either side of the drum.
for x in (-2.22,-1.46,1.47,3.08):
    box('Outer curtain wall mullion',(x,0,1.396),(.107,.157,2.68),m['Navy'],.016,'Outer Frame')
    box('Brass mullion face',(x,-.084,1.396),(.021,.024,2.59),m['Brass'],.006,'Outer Frame')
for x,w in ((-1.84,.82),(2.275,1.67)):
    for z in (.104,2.424):
        box('Doorway transom',(x,0,z),(w,.149,.092),m['Navy'],.012,'Outer Frame')
ring('Side swing door frame',2.275,-.026,1.29,1.40,2.23,.073,.065,.112,m['Dusk'],'Bypass Door')
pane('Side bypass door glass',2.275,-.076,1.29,1.28,2.10,m['RotorGlass'])
pane('Fixed court sidelight',-1.84,0,1.267,.697,2.23,m['Glass'])
box('Swing door pushplate',(2.673,-.089,1.06),(.37,.055,.166),m['Nickel'],.016,'Bypass Door')
rail('Horizontal push bar',(1.87,-.143,1.054),(2.79,-.143,1.054),.036,m['Brass'],'Bypass Door')
band(2.28,-.093,1.583,.99,.257,m['Access'],m['Ink'],'PINTU SISI',.158,'Bypass Door')
label('SIDE DOOR',(2.28,-.103,1.391),.086,m['Ink'],.89,group='Bypass Door')
for x,w in ((-1.83,.63),(2.29,1.54)):
    box('Fixed side head',(x,0,2.599),(w,.154,.357),m['Navy'],.027,'Outer Frame')
# Canopy ties the door and fixed wall together at the bulkhead.
box('Portal landing canopy',(.431,0,2.854),(5.43,2.94,.239),m['Navy'],.052,'Entry Canopy')
box('Champagne fascia undersill',(.431,-1.452,2.745),(5.35,.091,.101),m['Brass'],.017,'Entry Canopy')
for i in range(12):
    x = -1.93+.425*i
    box('Canopy shade fin',(x,.033,3.012),(.207,2.63,.091),m['Dusk'],.014,'Entry Canopy')
plaque('Suspended entrance fascia',.431,-1.496,2.916,5.43,.512,.183,.153,m['Navy'],'Entry Canopy')
plaque('Entrance inlay',.431,-1.594,2.916,5.20,.381,.031,.112,m['Dusk'],'Entry Canopy')
label('SELAMAT DATANG',(.431,-1.615,2.959),.254,m['Oyster'],3.18)
label('PINTU UTAMA  /  MAIN ENTRY',(.431,-1.615,2.805),.076,m['Lamp'],2.46)
for x in (-1.77,2.63):
    disc_front('Entry medallion',x,-1.621,2.918,.126,.033,m['Brass'])
    diamond('Entry medallion inlay',x,-1.642,2.918,.142,.142,m['Oyster'])
deliver((.335,-1,.247),'AAB8BF',margin=1.16)
