"""Teman Tapir, a padded Malayan tapir reading bench with a browsable face-out picture-book bin.
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

def oval(name,x,y,z,rx,ry,rz,m,group='Sculpture',n=32):
    profile=[(max(.01,math.cos(a)),rz*math.sin(a)) for a in [PI*(i/16-.5) for i in range(17)]]
    return turned(name,x,y,z,profile,m,group,n,(rx,ry))

# Teman Tapir, a padded Malayan tapir reading bench with a browsable face-out picture-book bin.
TITLE='Teman Tapir | Reading nook'
reset()
black,grey,cream,welt,tan,green,orange,blue,paper=colors(CharcoalVinyl='303940 .49',Muzzle='4B5355',CloudVinyl='E1D9BE .57',Stitch='B9A98C',Beech='CE9B65',Canopy='42766A',Papaya='C66445',Lake='527389',BookPaper='F5E6CA')
# Four broad, rubber-footed legs support the padded deck, the shelf and armrests.
for x in (-.88,.88):
    for y in (-.225,.226):
        turned('Tapered foot',x,y,0,[(.103,0),(.114,.028),(.107,.078),(.122,.177),(.134,.256),(.115,.287)],black,'Animal body',32,stretch=(1,.84))
        if y<0:
            for j in range(3):oval('Toe inset',x+(j-1)*.050,y-.07,.034,.018,.015,.015,grey,'Animal body',16)
slab('Timber seat frame',0,0,.22,2.13,.76,.085,.24,tan,'Seat')
slab('Saddle upholstery',.045,-.085,.30,1.66,.744,.111,.19,cream,'Seat')
# Lozenged cross-sections carry one continuous silhouette from the drooping
# proboscis through the forehead and cheek into the black shoulder.
def loft(name,stations,m,group):
    vs=[];fs=[]; n=40
    for x,y,z,ry,rz in stations:
        for j in range(n):
            a=j*TAU/n; vs.append((x,y+ry*math.cos(a),z+rz*math.sin(a)))
    fs.append(tuple(reversed(range(n))))
    for k in range(len(stations)-1):
        for j in range(n):fs.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j))
    fs.append(tuple(range(len(vs)-n,len(vs))))
    return mesh(name,vs,fs,m,group=group,smooth=True)
loft('Sculpted tapir head',[(-1.63,-.21,.511,.044,.044),(-1.61,-.20,.531,.089,.081),(-1.565,-.183,.581,.098,.113),(-1.519,-.174,.65,.101,.132),(-1.47,-.157,.698,.115,.146),(-1.394,-.143,.735,.143,.159),(-1.303,-.114,.773,.174,.178),(-1.207,-.087,.80,.214,.209),(-1.12,-.063,.806,.240,.238),(-1.004,-.031,.782,.267,.253),(-.918,-.003,.725,.273,.264),(-.824,.038,.64,.244,.258),(-.749,.068,.548,.212,.222),(-.685,.110,.464,.176,.159),(-.655,.129,.428,.135,.099)],black,'Animal body')
# A padded shoulder anchors the sculptural armrest; the snout has a softer,
# broader nose pad and a swept embroidered mouth on each cheek.
loft('Shoulder pad',[(-1.115,-.015,.424,.105,.118),(-1.044,-.013,.451,.157,.154),(-.946,.010,.474,.182,.170),(-.823,.040,.478,.196,.171),(-.729,.092,.469,.185,.158),(-.657,.133,.468,.151,.138)],black,'Animal body')
loft('Soft muzzle',[(-1.663,-.211,.520,.038,.042),(-1.649,-.210,.528,.073,.063),(-1.617,-.205,.540,.093,.087),(-1.591,-.196,.552,.090,.088)],grey,'Tapir features')
for s in (-1,1):
    tube('Stitched mouth',[(-1.586,-.193+s*.083,.537),(-1.543,-.178+s*.089,.567),(-1.508,-.173+s*.093,.606),(-1.465,-.153+s*.102,.641),(-1.412,-.147+s*.135,.666),(-1.373,-.141+s*.153,.681)],.0036,grey,'Tapir features',8)
# Small tapered ears with pale tips, as on an adult Malayan tapir.
for s in (-1,1):
    xx=-1.034; yy=-.035+s*.147
    turned('Rounded ear',xx,yy,.949,[(.042,0),(.076,.043),(.082,.090),(.067,.127),(.050,.143)],black,'Tapir features',32,(.86,.60))
    turned('Pale ear tip',xx,yy,1.092,[(.050,0),(.045,.012),(.029,.023),(.006,.026)],cream,'Tapir features',32,(.86,.60))
    oval('Ear inset',xx-.015,yy+s*.037,1.045,.033,.011,.036,grey,'Tapir features',20)
    oval('Eye surround',-1.249,-.104+s*.192,.832,.044,.014,.041,grey,'Tapir features',24)
    oval('Eye',-1.258,-.104+s*.202,.838,.023,.009,.027,black,'Tapir features',20)
    oval('Eye glint',-1.267,-.104+s*.212,.848,.006,.003,.006,paper,'Tapir features',12)
    oval('Nostril',-1.630,-.208+s*.087,.545,.019,.007,.012,black,'Tapir features',16)
# The tapir's ivory saddle becomes a low bolster behind a clear child-sized seat.
loft('Ivory saddle bolster',[(-.745,.17,.509,.099,.13),(-.663,.19,.542,.147,.202),(-.49,.204,.567,.153,.221),(-.20,.214,.58,.156,.228),(.12,.214,.58,.155,.229),(.43,.20,.565,.151,.209),(.62,.185,.541,.149,.18),(.75,.157,.48,.101,.135)],cream,'Seat')
loft('Black haunch',[(.55,.189,.481,.096,.12),(.65,.192,.52,.147,.179),(.74,.176,.525,.17,.19),(.88,.148,.502,.19,.208),(1.02,.117,.467,.188,.192),(1.115,.095,.438,.16,.162),(1.17,.07,.40,.086,.092)],black,'Animal body')
# Saddle stitch on the front of the seat and tonal inset on its backrest.
for i in range(32):
    x=-.562+i*.037
    tube('Saddle stitch',[(x,-.458,.368),(x+.019,-.458,.368)],.0024,welt,'Seat',6)
label('T E M A N    T A P I R',(-.04,.052,.612),.050,grey,.55)
# Children's books lean back in a separate slotted bin integrated at the rump.
slab('Book bin base',.93,-.25,.284,.65,.51,.070,.067,tan,'Book bin')
for x in (.627,1.234):
    sec=[(-.491,.35),(-.013,.35),(-.013,.782),(-.087,.772),(-.23,.667),(-.491,.528)]
    prism('Raked end cheek',sec,x-.021,x+.021,tan,'X',.010,'Book bin')
box('Low book rail',(.93,-.479,.438),(.612,.034,.156),green,.014,'Book bin')
box('Book bin rear',(.93,-.020,.538),(.61,.040,.394),tan,.014,'Book bin')
for i,(x,y,z,w,h,m,title) in enumerate([(.789,-.127,.604,.243,.416,blue,'HUJAN'),(1.061,-.123,.626,.258,.456,orange,'RIMBA'),(.932,-.336,.526,.338,.328,green,'DAUN')]):
    # Printed covers stand proud of a pale block of pages.
    plaque('Page block',x,y,z,w-.014,h-.015,.042,.009,paper,'Picture books')
    for yy in (y-.025,y+.025):plaque('Cloth cover',x,yy,z,w,h,.009,.008,m,'Picture books')
    yf=y-.033
    label(title,(x,yf,z+h*.30),.043,paper,w*.82,group='Picture books')
    disc_front('Book cover sun',x-.055,yf,z+.028,.032,.005,tan,'Picture books',24)
    print_y=yf-.005
    polygon('Cover hills',[(x-w*.39,z-.063),(x-.035,z+.033),(x+.028,z-.024),(x+.074,z+.004),(x+w*.39,z-.063)],print_y,.003,paper,'Picture books')
label('B A C A    /    P A H A N G',(.93,-.499,.446),.037,paper,.57)
deliver((-.45,-1,.37),'BEBCA9',1.12)
