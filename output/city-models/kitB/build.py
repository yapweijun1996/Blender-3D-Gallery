"""Derive Kit B from the gallery generators and render the shipped GLBs against their source exports."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector
import numpy as np

HERE = Path(__file__).resolve().parent
MODELS = HERE.parents[2] / 'models'
ASSETS = {
    'hawker-stall': ('hawker_stall', 1500),
    'chicken-rice-stall': ('chicken_rice_stall', 1500),
    'bus-stop-shelter': ('bus_shelter', 900),
    'singapore-traffic-signal-pole': ('signal_pole', 500),
    'pedestrian-crossing': ('zebra_crossing', 300),
    'street-name-sign': ('street_sign', 150),
    'heritage-street-lamp': ('heritage_lamp', 500),
    'public-service-waiting-bench': ('bench', 300),
    'hdb-block-number-sign': ('block_sign', 150),
    'playground-slide': ('playground_slide', 700),
    'playground-swing': ('playground_swing', 500),
    'rain-tree': ('rain_tree_hd', 900),
    'angsana-tree': ('angsana_tree', 700),
    'tembusu-tree': ('tembusu_tree_hd', 700),
    'frangipani-tree': ('frangipani_tree', 600),
    'coconut-palm': ('coconut_palm', 600),
}
VIEWS = [(0,-1,0), (1,0,0), (0,1,0), (-1,0,0), (1,-1,.75), (0,0,1)]
TILE = 260


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.unit_settings.system = 'METRIC'


def mesh_object(name, vertices, faces, material, parent=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.parent = parent
    return obj


def apply(obj, modifier):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def decimate(obj, target):
    obj.data.calc_loop_triangles()
    if len(obj.data.loop_triangles) <= target:
        return
    modifier = obj.modifiers.new('Triangle budget', 'DECIMATE')
    modifier.ratio = target / len(obj.data.loop_triangles)
    modifier.use_collapse_triangulate = True
    apply(obj, modifier)


def cylinder(sides, name, a, b, r1, r2, material, parent, capped=True):
    a, b = Vector(a), Vector(b)
    delta = b-a
    bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=r1, radius2=r2,
                                    depth=delta.length, location=(a+b)/2,
                                    end_fill_type='NGON' if capped else 'NOTHING')
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = delta.to_track_quat('Z','Y').to_euler()
    obj.data.materials.append(material)
    obj.parent = parent
    for p in obj.data.polygons:
        p.use_smooth = len(p.vertices) == 4
    return obj


def leaf(name, a, b, width, material, parent, single=False, folded=False):
    a, b = Vector(a), Vector(b)
    direction = (b-a).normalized()
    cross = direction.cross(Vector((0,0,1))).normalized() * width/2
    center = (a+b)/2
    if single:
        shoulder = a.lerp(b,.34)
        return mesh_object(name, [shoulder-cross, shoulder+cross, b], [(0,2,1)], material, parent)
    if folded:
        ridge = center + Vector((0,0,.008))
        return mesh_object(name, [a,center-cross,b,center+cross,ridge],
                           [(0,4,1),(1,4,2),(2,4,3),(3,4,0)], material, parent)
    return mesh_object(name, [a,center-cross,b,center+cross], [(0,3,1),(1,3,2)], material, parent)


def geodesic_hull(vertex_count, phase, tilt):
    base = bmesh.new()
    fine = bmesh.new()
    bmesh.ops.create_icosphere(base,subdivisions=1,radius=1)
    bmesh.ops.create_icosphere(fine,subdivisions=2,radius=1)
    selected = [v.co.normalized() for v in base.verts]
    available = [v.co.normalized() for v in fine.verts]
    while len(selected) < vertex_count:
        point = max(available,key=lambda p:min((p-q).length_squared for q in selected))
        selected.append(point)
        available.remove(point)
    rotation = Matrix.Rotation(phase,3,'Z') @ Matrix.Rotation(tilt,3,'X')
    base.clear()
    for point in selected:
        base.verts.new(rotation @ point)
    bmesh.ops.convex_hull(base,input=list(base.verts))
    bmesh.ops.triangulate(base,faces=list(base.faces))
    bmesh.ops.recalc_face_normals(base,faces=list(base.faces))
    base.verts.index_update()
    result = [tuple(v.co) for v in base.verts], [tuple(v.index for v in f.verts) for f in base.faces]
    fine.free()
    base.free()
    return result


def tree_geometry(src, slug):
    original_ellipsoid = src.ellipsoid

    def ellipsoid(name, loc, dims, material, parent, ico=False):
        if slug == 'coconut-palm':
            obj = original_ellipsoid(name, loc, (2,2,2), material, parent, True)
            decimate(obj,10)
        else:
            count = {'rain-tree':18,'angsana-tree':32,'tembusu-tree':14}[slug]
            phase = (loc[0]*.71+loc[1]*.4+loc[2]*.8) % math.tau
            tilt = .12 if slug == 'rain-tree' else .35+.24*math.sin(phase)
            vertices, faces = geodesic_hull(count,phase,tilt)
            obj = mesh_object(name,vertices,faces,material,parent)
            obj.location = loc
        for v in obj.data.vertices:
            for k in range(3):
                v.co[k] *= dims[k]/2
        return obj

    def branch(name,a,b,r1,r2,m,p):
        if slug == 'tembusu-tree':
            # Hidden ends sit in the trunk and foliage, so only the branch sides remain.
            is_trunk = name == 'TRUNK'
            return cylinder(10 if is_trunk else 4,name,a,b,r1,r2,m,p,capped=is_trunk)
        return cylinder(7 if name == 'TRUNK' else 5,name,a,b,r1,r2,m,p)

    src.ellipsoid = ellipsoid
    src.branch = branch
    src.leaf = lambda name,a,b,w,m,p: leaf(name,a,b,w,m,p,folded=name!='PETAL')

    if slug == 'frangipani-tree':
        def ellipsoid_flower(name, loc, dims, material, parent, ico=False):
            x,y,z = loc
            rx,ry,rz = (d/2 for d in dims)
            return mesh_object(name, [(x-rx,y,z),(x,y-ry,z),(x+rx,y,z),(x,y+ry,z),(x,y,z+rz)],
                               [(0,1,4),(1,2,4),(2,3,4),(3,0,4)], material, parent)
        src.ellipsoid = ellipsoid_flower

    if slug != 'coconut-palm':
        return

    def frond(name, start, angle, length, rise, drop, material, parent):
        start = Vector(start)
        radial = Vector((math.cos(angle),math.sin(angle),0))
        side = Vector((-math.sin(angle),math.cos(angle),0))
        def spine(t):
            return start + radial*(length*t) + Vector((0,0,rise*math.sin(math.pi*t)-drop*t*t))
        vertices = [spine(j/7) + (-1)**j*side*(.027*(1-j/8)) for j in range(8)]
        faces = [(j,j+1,j+2) if j%2 == 0 else (j+1,j,j+2) for j in range(6)]
        pieces = [mesh_object('Rachis',vertices,faces,material,parent)]
        for j in range(1,13):
            t = j/13
            center = spine(t)
            for sign in [-1,1]:
                end = center+side*sign*.7*(math.sin(math.pi*t)**.65)+radial*.23+Vector((0,0,-.13))
                pieces.append(leaf('Leaflet',center,end,.12,material,parent,single=j in (1,2,11,12)))
        return src.group_meshes(name,pieces,parent)
    src.palm_frond = frond


def material_name(obj, mat, slug):
    name = obj.name
    color = mat.name.lower()
    if '_Lens_' in name or name == 'Warm_Diffuser':
        return 'light'
    if (name.startswith(('FLOOR','STALL_Base','BASE_Footing','Foot','Entry_Ramp'))
            and 'steel' not in color) or any(word in color for word in ('concrete','stone')):
        return 'concrete'
    if name.startswith(('ROOF','CANOPY','Pitched_Cap')) and 'leaf' not in color:
        return 'roof'
    if 'glass' in color or 'glazing' in color:
        return 'glass'
    if name.startswith(('REAR_Wall','SIDE_Wall')):
        return 'wall'
    if 'leaf' in color:
        return 'leaf'
    if 'bark' in color or slug == 'coconut-palm' and 'timber' in color:
        return 'trunk'
    if name.startswith(('EDITABLE_','LETTER_','NUM_','SIGN_','BUS_Label','Zebra_Stripe','STALL_Header','HEADER')):
        return 'plate'
    if 'steel' in color or 'brass' in color or 'charcoal pole' in color:
        return 'metal'
    if any(key in color for key in ('blue','yellow','pale')):
        return 'paint'
    return 'trim'


def material_key(obj, material, slug):
    category = material_name(obj, material, slug)
    shader = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    color = tuple(round(x,6) for x in shader.inputs['Base Color'].default_value)
    key = (category, color, shader.inputs['Metallic'].default_value,
           shader.inputs['Roughness'].default_value, shader.inputs['Alpha'].default_value)
    return key


def source(slug):
    spec = importlib.util.spec_from_file_location('gallery_asset', MODELS/slug/'generate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_candidate(slug):
    src = source(slug)
    if slug in ('heritage-street-lamp','public-service-waiting-bench','pedestrian-crossing'):
        return make_city_detail(src,slug)

    finish = src.finish
    def low_finish(obj,name,material,parent,bevel=.002):
        visible_bevel = {
            'hawker-stall': ('ROOF','HEADER','SERVICE_Counter','HOOD'),
            'chicken-rice-stall': ('COUNTER_Stainless','STALL_Header','DISPLAY_Base','PREP_RearWorktop'),
            'bus-stop-shelter': ('CANOPY','BENCH_Seat','BENCH_Back'),
            'singapore-traffic-signal-pole': ('VEHICLE_Backplate','VEHICLE_Housing','BUTTON_Housing'),
            'street-name-sign': (),
            'hdb-block-number-sign': ('SIGN_Panel',),
            'playground-slide': ('PLATFORM','CHUTE_'),
            'playground-swing': ('SEAT',),
        }.get(slug,())
        obj = finish(obj,name,material,parent,bevel if name.startswith(visible_bevel) else 0)
        for modifier in obj.modifiers:
            if modifier.type == 'BEVEL':
                modifier.segments = 1
        return obj

    src.finish = low_finish
    src.rod = lambda n,a,b,r,m,p: cylinder(
        {'street-name-sign':6,'playground-slide':8,'playground-swing':8}.get(slug,10), n,a,b,r,r,m,p)
    def disc(n,loc,r,depth,m,p):
        sides = 12 if '_Lens_' in n else (16 if slug == 'chicken-rice-stall' else 8)
        return cylinder(sides,n,(loc[0],loc[1],loc[2]-depth/2),
                        (loc[0],loc[1],loc[2]+depth/2),r,r,m,p)
    src.disc = disc
    if slug.endswith('-tree') or slug == 'coconut-palm':
        tree_geometry(src,slug)
    if slug == 'chicken-rice-stall':
        def orb(name,loc,scale,mat,parent):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=10,ring_count=5,radius=1,location=loc)
            obj = low_finish(bpy.context.object,name,mat,parent,0)
            obj.scale = scale
            for p in obj.data.polygons:
                p.use_smooth = True
            return obj
        src.orb = orb
        def clear_glass():
            mat = src.mat('Clear glass alpha',(.55,.76,.82),0,.20)
            mat.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = .18
            return mat
        src.clear_glass = clear_glass
    root = src.empty('source')
    src.build(root)
    if slug in ('hawker-stall','chicken-rice-stall'):
        make_walkable(src,slug,root)
    return root


def make_city_detail(src,slug):
    if slug == 'pedestrian-crossing':
        # Keep the original eight stripes and 2.6 m band depth; stretch the span to join the road tile.
        root = src.empty('source')
        white = src.material('White',(255,255,255),.6)
        dark = src.material('Charcoal',(38,46,48),.8)
        mesh_object('Road_Base',[(-5.5,-1.3,0),(5.5,-1.3,0),(5.5,1.3,0),(-5.5,1.3,0)],
                    [(0,1,2,3)],dark,root)
        for x in [-3.5,-2.5,-1.5,-.5,.5,1.5,2.5,3.5]:
            a,b = ((x+d)*11/8 for d in [-.25,.25])
            mesh_object('Zebra_Stripe',[(a,-1.3,.002),(b,-1.3,.002),(b,1.3,.002),(a,1.3,.002)],
                        [(0,1,2,3)],white,root)
        return root
    origin_box = src.box
    src.box = lambda n,p,d,m,bevel=0: origin_box(n,p,d,m,0)
    src.C = lambda n,p,r,d,m,parent=None: cylinder(16,n,(p[0],p[1],p[2]-d/2),
                                                 (p[0],p[1],p[2]+d/2),r,r,m,parent or src.root)
    return src.build()


def make_walkable(src,slug,root):
    objects = {o.name:o for o in root.children}
    if slug == 'hawker-stall':
        wall = objects['REAR_Wall']
        ivory = wall.data.materials[0]
        bpy.data.objects.remove(wall,do_unlink=True)
        for x in [-1.125,1.125]:
            src.box('REAR_Wall_Jamb',(x,1.25,1.42),(.65,.10,2.72),ivory,root,0)
        src.box('REAR_Wall_Lintel',(0,1.25,2.50),(1.60,.10,.56),ivory,root,0)
        # The grate keeps the original outline but sits flush with the walking surface.
        for obj in root.children:
            if obj.name.startswith('DRAIN_Channel'):
                obj.location.z -= .0197
            if obj.name.startswith('DRAIN_Grate'):
                obj.location.z -= .029
        entry_ramp(root, ivory, 0, 1.3)
        worktop = objects['BACK_Worktop']
        worktop.scale.x = .22
        worktop.location.x = 1.08
        return
    floor = objects['STALL_Base']
    floor.scale.y = 1.20
    floor.location.y = .20
    entry_ramp(root, floor.data.materials[0], -.14, 1.4)
    # Retain the back prep counter as a short side station and move its pot with it.
    top = objects['PREP_RearWorktop']
    top.scale.x = .27
    top.location.x = .98
    for obj in list(root.children):
        if obj.name.startswith('PREP_Support') and obj.location.x < 0:
            bpy.data.objects.remove(obj,do_unlink=True)


def entry_ramp(root, material, center_x, start_y):
    left, right = center_x-.75, center_x+.75
    end_y = start_y+.42
    vertices = [
        (left,start_y,0),(right,start_y,0),(left,end_y,0),(right,end_y,0),
        (left,start_y,.12),(right,start_y,.12),
    ]
    mesh_object('Entry_Ramp', vertices,
                [(4,5,3,2),(0,4,2),(1,3,5),(0,2,3,1)], material, root)


def front_only(mesh, direction):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.normal_update()
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.normal.dot(direction) < .95],
                     context='FACES')
    bmesh.ops.dissolve_limit(bm,angle_limit=.0001,verts=list(bm.verts),edges=list(bm.edges))
    bm.to_mesh(mesh)
    bm.free()


def prepare(slug, root):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    grouped = {}
    ground = float('inf')
    for obj in root.children_recursive:
        if obj.type not in ('MESH','FONT'):
            continue
        if obj.type == 'FONT':
            obj.data.extrude = 0
            obj.data.resolution_u = 1 if slug == 'street-name-sign' else 2
        if slug == 'coconut-palm' and obj.name.startswith('TRUNK_GrowthRing'):
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
        mesh.transform(evaluated.matrix_world)
        if slug == 'hdb-block-number-sign' and obj.name.startswith(('NUM_','FASTENER')):
            front_only(mesh,Vector((0,-1,0)))
        if slug == 'street-name-sign' and obj.type == 'FONT':
            front_only(mesh,Vector((0,-1,0)))
        if mesh.vertices:
            ground = min(ground,min(v.co.z for v in mesh.vertices))
        mesh.calc_loop_triangles()
        for tri in mesh.loop_triangles:
            mat = mesh.materials[tri.material_index]
            key = material_key(obj,mat,slug)
            name = 'light' if '_Lens_' in obj.name else key[0]
            group_id = (key,obj.name if name == 'light' else '')
            if group_id not in grouped:
                grouped[group_id] = {}
            part = grouped[group_id]
            for idx in tri.vertices:
                if idx not in part.setdefault(obj.name, {'vertices':{},'faces':[]} )['vertices']:
                    part[obj.name]['vertices'][idx] = tuple(mesh.vertices[idx].co)
            part[obj.name]['faces'].append((tuple(tri.vertices),tri.use_smooth))
        bpy.data.meshes.remove(mesh)
    return grouped, ground


def combine(slug, out, grouped, ground):
    reset()
    objects = []
    for (key,lens), geometry in grouped.items():
        category,color,metal,rough,alpha = key
        mat = bpy.data.materials.new(category)
        mat.use_nodes = True
        mat.use_backface_culling = alpha < 1
        shader = mat.node_tree.nodes.get('Principled BSDF')
        for field,value in [('Base Color',color),('Metallic',metal),('Roughness',rough),('Alpha',alpha)]:
            shader.inputs[field].default_value = value
        positions, faces, smoothing = [],[],[]
        for part in geometry.values():
            indices = {}
            for idx,(x,y,z) in part['vertices'].items():
                indices[idx] = len(positions)
                positions.append((x,y-(.20 if slug == 'chicken-rice-stall' else 0),z-ground))
            for tri, smooth in part['faces']:
                faces.append(tuple(indices[idx] for idx in tri))
                smoothing.append(smooth)
        obj = mesh_object(lens or category,positions,faces,mat)
        for polygon,smooth in zip(obj.data.polygons,smoothing):
            polygon.use_smooth = smooth
        if slug == 'street-name-sign' and category == 'plate' and len(faces)>100:
            decimate(obj,100)
        objects.append(obj)
    bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',export_yup=True,
                             export_animations=False,export_texcoords=False,export_extras=False,
                             export_cameras=False,export_lights=False)
    # glTF names are labels, so several independent PBR swatches may share an exact category.
    raw = out.read_bytes()
    n = int.from_bytes(raw[12:16],'little')
    gltf = json.loads(raw[20:20+n])
    for mat in gltf['materials']:
        mat['name'] = mat['name'].split('.')[0]
    for node in gltf['nodes']:
        if '_Lens_' in node['name']:
            lens_id = int(node['name'].rsplit('_',1)[1])
            node['name'] = 'light'
            node['extras'] = {'signalChannel':['red','amber','green'][lens_id]}
            gltf['meshes'][node['mesh']]['name'] = 'light'
    data = json.dumps(gltf,separators=(',',':')).encode()
    data += b' '*(-len(data)%4)
    payload = raw[20+n:]
    out.write_bytes(raw[:8]+(20+len(data)+len(payload)).to_bytes(4,'little')+
                    len(data).to_bytes(4,'little')+b'JSON'+data+payload)
    count = sum(gltf['accessors'][p['indices']]['count']//3 for m in gltf['meshes'] for p in m['primitives'])
    print(f'KITB {slug} {count} triangles',flush=True)


def render_pair(slug, original, candidate):
    rows = []
    scratch = HERE/'.render'
    scratch.mkdir(exist_ok=True)
    for path in [original,candidate]:
        reset()
        bpy.ops.import_scene.gltf(filepath=str(path))
        scene = bpy.context.scene
        coords = [o.matrix_world @ v.co for o in scene.objects if o.type=='MESH' for v in o.data.vertices]
        low = Vector([min(p[i] for p in coords) for i in range(3)])
        high = Vector([max(p[i] for p in coords) for i in range(3)])
        center = (low+high)/2
        extent = max(high-low)
        # Pin source and candidate framing to the original scale.
        if path == original:
            reference_extent = extent
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = 8
        scene.cycles.use_denoising = True
        scene.render.resolution_x = scene.render.resolution_y = TILE
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.film_transparent = True
        scene.view_settings.view_transform = 'Standard'
        scene.world = bpy.data.worlds.new('Neutral studio')
        scene.world.use_nodes = True
        bg = scene.world.node_tree.nodes['Background']
        bg.inputs[0].default_value = (.37,.40,.44,1)
        bg.inputs[1].default_value = .5
        for i,(x,y,z,power) in enumerate([(-3,-4,5,1),(4,-2,3,.6),(0,4,5,.8)]):
            light = bpy.data.lights.new(f'Area {i}','AREA')
            light.energy = power*reference_extent**2*550
            light.shape = 'DISK'
            light.size = reference_extent*3
            obj = bpy.data.objects.new(light.name,light)
            scene.collection.objects.link(obj)
            obj.location = center + Vector((x,y,z))*reference_extent
            obj.rotation_euler = (center-obj.location).to_track_quat('-Z','Y').to_euler()
        camera = bpy.data.cameras.new('Ortho')
        camera.type = 'ORTHO'
        camera.ortho_scale = reference_extent*1.22
        camera.clip_end = 1000
        obj = bpy.data.objects.new('Ortho',camera)
        scene.collection.objects.link(obj)
        scene.camera = obj
        panels = []
        for direction in VIEWS:
            obj.location = center + Vector(direction)*reference_extent*4
            rotation = (center-obj.location).to_track_quat('-Z','Y')
            obj.rotation_euler = rotation.to_euler()
            if slug in ('hawker-stall','chicken-rice-stall','playground-swing'):
                camera.ortho_scale = reference_extent*(1.47 if direction == VIEWS[4] else 1.24)
            scene.render.filepath = str(scratch/'tile.png')
            bpy.ops.render.render(write_still=True)
            im = bpy.data.images.load(scene.render.filepath,check_existing=False)
            pixels = np.empty(TILE*TILE*4,dtype=np.float32)
            im.pixels.foreach_get(pixels)
            bpy.data.images.remove(im)
            panels.append(pixels.reshape((TILE,TILE,4)))
        rows.append(panels)
    (HERE/'renders').mkdir(exist_ok=True)
    # Three columns, paired rows: original and export, first three then last three views.
    sheet = np.full((4*(TILE+4)+4,3*(TILE+4)+4,4),.17,np.float32)
    sheet[:,:,3] = 1
    for i in range(6):
        for row in range(2):
            y = 4+(3-(2*(i//3)+row))*(TILE+4)
            x = 4+(i%3)*(TILE+4)
            tile = rows[row][i]
            sheet[y:y+TILE,x:x+TILE,:3] = tile[:,:,:3]*tile[:,:,3:] + .26*(1-tile[:,:,3:])
    height,width = sheet.shape[:2]
    image = bpy.data.images.new('Contact sheet',width=width,height=height,alpha=False)
    image.pixels.foreach_set(sheet.ravel())
    image.filepath_raw = str(HERE/'renders'/f'{candidate.stem}.png')
    image.file_format = 'PNG'
    image.save()
    (scratch/'tile.png').unlink()
    scratch.rmdir()


if __name__ == '__main__':
    arguments = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    render = '--render' in arguments
    render_only = '--render-only' in arguments
    slugs = [arg for arg in arguments if not arg.startswith('--')] or list(ASSETS)
    for slug in slugs:
        output = HERE/(ASSETS[slug][0]+'.glb')
        if not render_only:
            reset()
            root = make_candidate(slug)
            grouped, ground = prepare(slug,root)
            combine(slug,output,grouped,ground)
        if render or render_only:
            original, = (MODELS/slug/'exports').glob('*.glb')
            render_pair(slug,original,output)
