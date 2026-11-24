"""Terompah Empat, an arched Melaka wooden-clog fitting wall with paired samples.
Rebuild: blender -b -P generate.py [-- --export-only | --preview-only].
Static mall fixture in metres. Built-in lettering, no external assets or scripts.
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
        scene.cycles.samples = 16
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
    root = bpy.data.objects.new(TITLE, None)
    bpy.context.collection.objects.link(root)
    for obj in objs:
        obj.parent = root
    root['asset_id'] = dest.name
    root['origin_note'] = 'Floor datum at local (0, 0, 0); customer side faces -Y in Blender.'
    root['theme'] = 'Singapore / Malaysia mall'
    root['source_note'] = 'Original procedural geometry, solid PBR materials, built-in lettering.'
    root['units'] = 'metre'
    root['role'] = 'Static visual mesh (no collider or clips)'
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

def colors(**swatches):
    return [mat(name, *([s.split()[0]] + [float(n) for n in s.split()[1:]])) for name,s in swatches.items()]

def slab(name,x,y,z,w,d,h,r,material,group='Cabinetry'):
    return prism(name,rounded(w,d,r,(x,y),7),z,z+h,material,bevel=min(.01,h*.14),group=group)

def polygon(name,xzs,y,depth,material,group='Decoration'):
    area=sum(a*d-b*c for (a,b),(c,d) in zip(xzs,xzs[1:]+xzs[:1]))
    return prism(name,xzs if area>0 else xzs[::-1],-y-depth/2,-y+depth/2,material,'NEG_Y',min(depth*.12,.008),group)

def arch(name,x,y,z,w,h,d,m,group='Joinery'):
    r=w/2; spring=z+h-r
    pts=[(x-r,z),(x+r,z)]+[(x+r*math.cos(PI*i/40),spring+r*math.sin(PI*i/40)) for i in range(41)]
    return polygon(name,pts,y,d,m,group)

def star(name,x,y,z,r,m,points=8):
    polygon(name,[(x+r*(.49 if i%2 else 1)*math.cos(i*PI/points),z+r*(.49 if i%2 else 1)*math.sin(i*PI/points)) for i in range(points*2)],y,.006,m)

def badge(title,subtitle,x,y,z,w,h,field,ink):
    plaque('Enamel tablet',x,y,z,w,h,.032,min(h*.20,.06),field)
    label(title,(x,y-.019,z+h*.115),h*.46,ink,w*.86)
    label(subtitle,(x,y-.019,z-h*.245),h*.17,ink,w*.86)

# Terompah Empat, an arched Melaka wooden-clog fitting wall with paired samples.
TITLE='Terompah Empat | Fitting wall'
reset()
clay,red,teal,cream,gold,wood,sole,dark=colors(Terracotta='A8533C',Lacquer='BB382F .29',Peacock='275754',Rice='F3DFC0',Brass='CB9D62 .32 .64',Beech='CB925D',Endgrain='975E3C',Cocoa='493833')
slab('Shadow plinth',0,0,0,2.32,.76,.09,.09,dark)
slab('Painted chest',0,0,.09,2.39,.80,.42,.09,clay)
slab('Chest rim',0,0,.51,2.42,.82,.06,.09,wood)
for s in (-1,1):
    plaque('Drawer',s*.58,-.403,.31,1.10,.30,.027,.034,cream)
    box('Recessed pull',(s*.58,-.431,.36),(.25,.036,.025),gold)
# Three round-headed niches retain their own stepped mouldings.
for i,x in enumerate((-.77,0,.77)):
    h=1.82 if i==1 else 1.60
    arch('Timber arcade',x,.23,.54,.78,h,.21,clay)
    arch('Inner gilt bead',x,.116,.58,.71,h-.10,.026,gold)
    arch('Enamel back',x,.093,.60,.65,h-.16,.034,teal)
    for z in (.62,1.02,1.42):
        slab('Rounded sample shelf',x,-.069,z,.68,.47,.033,.05,wood,'Shelving')
    label(['K E C I L','S E D E R H A N A','B E S A R'][i],(x,.070,1.74),.055,cream,.59)
    star('Carved rosette',x,.064,1.90 if i!=1 else 1.86,.067,gold)
# Foot-shaped soles: separate heel block, raised toe and domed lacquered leather strap.
def clog(x,y,z,m,k):
    outline=[(-.047,-.143),(.030,-.150),(.051,-.127),(.055,-.07),(.042,.008),(.037,.109),(.027,.135),(-.027,.135),(-.041,.108),(-.035,.025),(-.054,-.063),(-.058,-.118)]
    prism('Carved sole',[(x+k*u,y+k*v) for u,v in outline],z+.028*k,z+.051*k,wood,bevel=.008,group='Clogs')
    for v,d in [(-.082,.048),(.084,.052)]:box('Wooden foot',(x,y+k*v,z+.015*k),(.082*k,d*k,.030*k),sole,.004,'Clogs')
    vs=[];fs=[]
    for j in range(17):
        a=j*PI/16
        for v in (-.109,-.034):vs.append((x+k*.056*math.cos(a),y+k*(v+.010*math.sin(a)),z+k*(.043+.078*math.sin(a))))
        if j:fs.append((2*j-2,2*j-1,2*j+1,2*j))
    mesh('Curved vamp',vs,fs,m,group='Clogs',smooth=True)
    for v in (-.108,-.034):tube('Vamp piping',[(x+k*.056*math.cos(a),y+k*(v+.01*math.sin(a)),z+k*(.043+.078*math.sin(a))) for a in [j*PI/16 for j in range(17)]],.003*k,gold,'Clogs',8)
for i,x in enumerate((-.77,0,.77)):
    for j,z in enumerate((.653,1.053,1.453)):
        for sign in (-1,1):clog(x+sign*.103,-.077,z,(red,cream,clay)[(i+j)%3],(.94,1.05,1.14)[i])
badge('TEROMPAH','M E L A K A   /   N O .  0 4',0,-.011,2.095,.89,.254,cream,clay)
deliver((.38,-1,.37),'C5BAAA',1.12)
