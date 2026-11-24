"""Helai, a Geylang Serai philately counter with three perforated original nature stamps.
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

def disc_front(name, x, y, z, r, depth, material, group='Graphics', sides=32):
    return prism(name, [(x+r*math.cos(TAU*i/sides),z+r*math.sin(TAU*i/sides))
                        for i in range(sides)], -y-depth/2, -y+depth/2,
                 material, 'NEG_Y', min(depth*.2, .004), group)

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

def turned(name,x,y,z,profile,m,group='Turned work',n=48,stretch=(1,1),flutes=0,ripple=0):
    """Revolve a radial section, from underside to lip and optionally back inside."""
    vs=[]
    for r,h in profile:
        for j in range(n):
            a=TAU*j/n
            rr=r*(1+ripple*math.cos(flutes*a))
            vs.append((x+stretch[0]*rr*math.cos(a),y+stretch[1]*rr*math.sin(a),z+h))
    fs=[tuple(reversed(range(n)))]
    for k in range(len(profile)-1):
        for j in range(n):
            a=k*n+j; b=k*n+(j+1)%n
            fs.append((a,b,b+n,a+n))
    fs.append(tuple(range(len(vs)-n,len(vs))))
    obj=mesh(name,vs,fs,m,group=group,smooth=True)
    for i in (0,-1): obj.data.polygons[i].use_smooth=False
    return obj

def ring(name,x,y,z,r,wire,m,group='Metalwork',n=48):
    # Closed torus with no doubled seam or end caps.
    vs=[]; fs=[]; k=8
    for i in range(n):
        a=i*TAU/n
        for j in range(k):
            b=j*TAU/k; rr=r+wire*math.cos(b)
            vs.append((x+rr*math.cos(a),y+rr*math.sin(a),z+wire*math.sin(b)))
            fs.append((i*k+j,((i+1)%n)*k+j,((i+1)%n)*k+(j+1)%k,i*k+(j+1)%k))
    return mesh(name,vs,fs,m,group=group,smooth=True)

def button(name,x,y,z,r,h,m,group='Fittings',n=32):
    return turned(name,x,y,z,[(r*.94,0),(r,.12*h),(r,.86*h),(r*.94,h)],m,group,n)

def badge(title,subtitle,x,y,z,w,h,field,ink):
    plaque('Enamel tablet',x,y,z,w,h,.032,min(h*.20,.06),field)
    label(title,(x,y-.019,z+h*.115),h*.46,ink,w*.86)
    label(subtitle,(x,y-.019,z-h*.245),h*.17,ink,w*.86)

# Helai, a Geylang Serai philately counter with three perforated original nature stamps.
TITLE='Helai | Stamp folio counter'
reset()
navy,rice,salmon,gold,sky,teal,blue,berry,leaf,glass=colors(PostInk='263F50',Paper='F2E4C8 .64',Postmark='BD5947',AgedBrass='B99968 .32 .6',Airmail='8CC6C7',Mangrove='34685F',Indigo='466794',Fruit='694766',NewLeaf='A1B477',Lens='A6D5DD .15 0 0 .25')
slab('Cabinet foot',0,0,0,2.04,.82,.089,.11,navy)
slab('Archive cabinet',0,0,.089,2.16,.89,.73,.12,teal)
slab('Paper worktop',0,0,.819,2.23,.96,.059,.13,rice)
# Archival drawers with metal card holders and label slips.
for i in range(2):
    for j in range(2):
        x=-.72+.65*i;z=.284+.335*j
        plaque('Folio drawer',x,-.451,z,.607,.292,.020,.018,navy)
        plaque('Label holder',x,-.469,z+.042,.225,.091,.016,.009,gold)
        plaque('Inventory slip',x,-.479,z+.044,.180,.054,.009,.004,rice)
        label('S - '+str(12+j*2+i),(x,-.486,z+.044),.031,navy,.16)
        box('Drawer handle',(x,-.486,z-.062),(.14,.053,.025),gold,.009,'Archive')
badge('H E L A I','F I L A T E L I    /    S G',.661,-.458,.46,.64,.31,rice,navy)
for x,h in [(-.50,1.75),(.565,1.65)]:
    button('Desk flange',x,.263,.878,.081,.024,gold)
    tube('Print standard',[(x,.263,.90),(x,.263,h)],.026,navy,'Print stand')
# Inward half-round bites on every edge, retaining flat bridges between cuts.
def stamp(x,y,z,w,h,nx,ny,field):
    outside=[]; inside=[]
    inset=.045
    for (u,v),(dx,dz),length,n in [((-w/2,-h/2),(1,0),w,nx),((w/2,-h/2),(0,1),h,ny),((w/2,h/2),(-1,0),w,nx),((-w/2,h/2),(0,-1),h,ny)]:
        # Reserve a solid corner before the first scallop. Direct perpendicular
        # projections keep the lip quads from folding towards the short ends.
        step=(length-2*inset)/n;r=step*.34
        samples=[(0,0),(inset,0)]
        for i in range(n):
            for j in range(7):
                a=PI*j/6;samples.append((inset+(i+.5)*step-r*math.cos(a),r*math.sin(a)))
        samples.append((length-inset,0))
        for along,bite in samples:
            xx=u+dx*along;zz=v+dz*along
            outside.append((x+xx-dz*bite,z+zz+dx*bite))
            along=max(inset,min(length-inset,along))
            inside.append((x+u+dx*along-dz*inset,z+v+dz*along+dx*inset))
    # Explicit quad border around each perforation avoids thin concave cap ngons.
    n=len(outside); vs=[(a,yy,b) for yy in (y-.014,y+.014) for loop in (outside,inside) for a,b in loop]+[(x,y-.014,z),(x,y+.014,z)]
    fs=[]
    for i in range(n):
        j=(i+1)%n
        fs.extend([(i,j,n+j,n+i),(n+i,n+j,4*n),(2*n+j,2*n+i,3*n+i,3*n+j),(3*n+j,3*n+i,4*n+1),(j,i,2*n+i,2*n+j)])
    # Adjacent strips share their inside corner. Weld it before triangulation.
    unique={tuple(round(c,7) for c in v):None for v in vs}
    lookup={p:i for i,p in enumerate(unique)}
    indices=[lookup[tuple(round(c,7) for c in v)] for v in vs]
    faces=[tuple(dict.fromkeys(indices[j] for j in f)) for f in fs]
    mesh('Perforated rag paper',list(unique),[f for f in faces if len(f)>=3],rice,group='Print stock')
    box('Print mount',(x,(.263+y)/2,z),(.15,.263-y,.10),navy,.005,'Print stand')
    plaque('Printed field',x,y-.018,z,w-.122,h-.122,.008,.005,field,'Prints')

def print_poly(name,x,y,z,s,points,m):
    polygon(name,[(x+s*a,z+s*b) for a,b in points],y,.004,m,'Prints')
# Main commemorative: kingfisher, cut-paper colour separations and a rising sun.
x=-.493; z=1.63;stamp(x,.208,z,1.05,1.33,12,15,sky)
def main_art(name,points,m,d=.178):print_poly(name,x,d,z,1,points,m)
disc_front('Ochre sun',x-.16,.181,z+.18,.195,.006,gold,'Prints',48)
main_art('Branch',[(-.451,-.32),(.43,-.185),(.456,-.191),(.456,-.23),(-.451,-.364)],teal)
main_art('Bird silhouette',[(-.32,-.23),(-.16,.020),(-.10,.17),(.002,.228),(.093,.225),(.181,.169),(.182,.07),(.105,-.063),(.042,-.152),(-.08,-.183),(-.19,-.187)],navy,.171)
main_art('Ochre breast',[(.173,.091),(.102,-.064),(.042,-.152),(-.08,-.183),(-.115,-.141),(-.033,-.067),(.038,.063)],salmon,.165)
main_art('Cobalt wing',[(-.289,-.198),(-.17,.013),(-.069,.117),(.015,.119),(.033,.062),(-.091,-.085)],blue,.159)
main_art('Cream collar',[(.018,.126),(.153,.151),(.178,.119),(.065,.077)],rice,.158)
main_art('Long beak',[(.164,.179),(.381,.132),(.176,.137)],navy,.156)
disc_front('Kingfisher eye',x+.114,.153,z+.174,.015,.007,rice,'Prints',16)
for u in (-.06,.011):line_front('Bird foot',[(x+u,z-.145),(x+u-.010,z-.252),(x+u+.031,z-.258)],.154,.007,navy,'Prints')
label('S I N G A P U R A',(x,.167,z+.496),.075,navy,.82)
label('50',(x+.256,.166,z+.323),.159,navy,.23)
label('R A J A   U D A N G',(x,.168,z-.498),.062,navy,.83)
# Companion issues: a mangosteen botanical print and the evening strait.
x=.568;z=1.865;stamp(x,.218,z,.865,.706,10,8,berry)
disc_front('Mangosteen',x-.11,.191,z+.003,.159,.006,navy,'Prints',36)
for i in range(5):
    a=TAU*i/5; print_poly('Fruit calyx',x-.11,.181,z+.072,1,[(0,0),(.071*math.cos(a)-.026*math.sin(a),.071*math.sin(a)+.026*math.cos(a)),(.103*math.cos(a),.103*math.sin(a)),(.071*math.cos(a)+.026*math.sin(a),.071*math.sin(a)-.026*math.cos(a))],leaf)
label('30',(x+.20,.181,z+.11),.144,rice,.21)
label('M A N G G I S',(x,.180,z-.222),.053,rice,.63)
z=1.213;stamp(x,.162,z,.865,.595,10,7,blue)
disc_front('Setting sun',x+.05,.135,z+.047,.070,.006,salmon,'Prints',32)
print_poly('Island profile',x,.129,z,1,[(-.36,-.088),(-.212,.041),(-.12,-.003),(-.018,.079),(.111,-.048),(.208,.028),(.36,-.092)],teal)
label('20',(x+.259,.131,z+.123),.102,rice,.14);label('S E L A T',(x,.128,z-.163),.055,rice,.53)
# Collectors loupe and two closed albums sit on the public side of the counter.
for i,(w,d,m) in enumerate([(.57,.27,navy),(.50,.25,salmon)]):
    slab('Album cover',-.60+i*.033,-.23,.878+i*.060,w,d,.012,.012,m,'Albums')
    slab('Page block',-.60+i*.033,-.23,.890+i*.060,w-.017,d-.017,.033,.008,rice,'Albums')
    slab('Album cover',-.60+i*.033,-.23,.923+i*.060,w,d,.015,.012,m,'Albums')
label('F O L I O',(-.567,-.23,1.000),.045,rice,.36,on_top=True)
ring('Loupe rim',.59,-.18,.907,.112,.014,gold)
button('Loupe lens',.59,-.18,.899,.105,.012,glass)
tube('Loupe grip',[(.681,-.233,.907),(.872,-.342,.894)],.019,navy,'Archive',16)
deliver((.29,-1,.29),'B4B9B3',1.12)
