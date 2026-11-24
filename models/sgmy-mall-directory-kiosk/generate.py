"""Build a static, bilingual directory kiosk for an original SG/MY mall.
Origin: centre of the pedestal mounting plate, Z=0. The screen graphics
are local mesh artwork, not an operable directory or a real mall map.

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


TITLE = 'Serambi Court Directory Kiosk'


def build():
    reset()
    navy = mat('Midnight Powder Coat','203A48',.41,.22)
    jade = mat('Jade Enamel Side Shell','3D817A',.35,.2)
    brushed = mat('Champagne Anodised Trim','C3A67D',.37,.48)
    rubber = mat('Rubber Mounting Pad','252F3A',.64)
    bezel = mat('Display Bezel Polymer','142E3A',.39)
    def oled(name, color):
        material = mat(name, color)
        nodes = material.node_tree.nodes
        nodes.remove(nodes['Principled BSDF'])
        swatch = nodes.new('ShaderNodeRGB')
        swatch.outputs[0].default_value = material.diffuse_color
        material.node_tree.links.new(swatch.outputs[0], nodes['Material Output'].inputs['Surface'])
        return material
    ink = oled('Display Ink','10232E')
    ivory = oled('Ivory Display Field','FCF0D8')
    blue = oled('OLED Teal Masthead','1E6D64')
    cream = oled('Warm White Display Type','FFF1D9')
    mint = oled('Map Jade Zone','62C5AF')
    coral = oled('Map Coral Zone','E99E83')
    yellow = oled('Map Honey Zone','E4BA67')
    lilac = oled('Map Lavender Zone','AC9CCA')
    gray = oled('Map Service Zone','B0C0B8')
    alert = oled('You Are Here Vermilion','D9523C')
    glow = mat('Information Night Light','7DEED0',.37,glow=1.65)
    shell = 'Kiosk Housing'
    ui = 'Directory Screen'

    prism('Rubber floor gasket',rounded(.955,.513,.119),0,.017,rubber,'Z',.005,shell)
    prism('Heavy rounded steel foot',rounded(.946,.504,.114),.012,.073,navy,'Z',.013,shell)
    prism('Champagne pedestal bead',rounded(.865,.439,.105),.067,.086,brushed,'Z',.006,shell)
    plaque('Jade interface housing',0,.031,1.032,.824,1.902,.282,.134,jade,shell)
    plaque('Lower armoured pedestal',0,.007,.459,.723,.763,.315,.078,navy,shell)
    plaque('Pedestal shoulder trim',0,-.127,.467,.584,.627,.036,.061,jade,shell)
    plaque('Upper face panel',0,-.121,1.32,.799,1.311,.212,.102,navy,shell)
    ring('Brushed steel display rim',0,-.237,1.270,.727,1.012,.072,.021,.028,brushed,shell)
    plaque('Black flush display edge',0,-.226,1.27,.680,.969,.038,.049,bezel,shell)
    plaque('Screen substrate',0,-.249,1.27,.639,.914,.016,.025,ivory,ui)
    for y in (-.157,.177):
        for j in range(6):
            for col in range(2):
                x=(col-.5)*.027
                disc_front('Lower speaker perforation',x,y,.225+j*.022,.006,.004,rubber,shell,12)
    plaque('Stamped access hatch',0,.177,.506,.529,.624,.016,.077,navy,shell)
    # Fastener dots on the service side, plus louvres near the monitor controller.
    for x in (-.202,.202):
        for z in (.250,.762):
            disc_front('Stainless service fastener',x,.189,z,.010,.008,brushed,shell,16)
    for i in range(8):
        box('Rear vent hood',(0,.181,1.369+i*.024),(.511,.019,.011),rubber,.003,shell)
    for side in (-1,1):
        for i in range(5):
            z = 1.32+i*.089
            p=[(-.014,z),(.027,z-.028),(.068,z),(.027,z+.028)]
            x=.410*side
            prism('Side enamel lozenge',p,x-.005,x+.005,brushed,'X',.001,shell)

    # Painted branding and an accessible, physical help button.
    disc_front('Information roundel',-.243,-.231,1.858,.078,.037,jade,shell)
    disc_front('Information roundel inset',-.243,-.253,1.858,.059,.011,blue,shell)
    disc_front('Lowercase i dot',-.243,-.262,1.878,.011,.009,glow,shell,16)
    plaque('Lowercase i stem',-.243,-.262,1.839,.018,.044,.009,.007,glow,shell)
    label('SERAMBI COURT',(.063,-.231,1.86),.071,cream,.449,group=shell)
    plaque('Help control rail',0,-.200,.697,.579,.123,.103,.052,jade,shell)
    disc_front('Help button bezel',-.201,-.260,.694,.037,.026,brushed,shell)
    disc_front('Help button',-.201,-.276,.694,.025,.014,glow,shell)
    label('BANTUAN / HELP',(.023,-.258,.697),.043,cream,.314,group=shell)
    # Tactile dots are decorative in this asset, not a claim of Braille compliance.
    for j in range(2):
        for i in range(6):
            disc_front('Raised tactile dot',.205+i*.008,-.259,.680+j*.009,.0027,.004,brushed,shell,10)

    # All map and type are physical, low-relief mesh art; GLB needs no image assets.
    def card(name,x,z,w,h,r,tone,y=-.265):
        plaque(name,x,y,z,w,h,.006,r,tone,ui)
    def text(line,x,z,size,tone,w=None,align='CENTER',y=-.273):
        label(line,(x,y,z),size,tone,w,align=align,group=ui)
    card('Teal directory title zone',0,1.650,.611,.123,.014,blue)
    text('DIREKTORI',-.279,1.675,.064,cream,.39,'LEFT')
    text('MALL DIRECTORY',-.279,1.622,.029,cream,.32,'LEFT')
    card('Active floor label',.218,1.652,.146,.056,.018,yellow,y=-.271)
    text('ARAS 1',.218,1.653,.032,ink,.126,y=-.276)
    card('Floor plan background',0,1.318,.605,.478,.019,gray,y=-.259)
    p=[(-.271,1.16),(-.071,1.16),(-.071,1.305),(.092,1.305),(.092,1.121),(.277,1.121),
       (.277,1.190),(.151,1.190),(.151,1.481),(.080,1.481),(.080,1.374),
       (-.133,1.374),(-.133,1.228),(-.271,1.228)]
    prism('Public concourse circulation',p,.266,.269,ivory,'NEG_Y',group=ui)
    for x,z,w,h,t,c,s in ((-.190,1.456,.158,.129,mint,'08','KOPI'),(-.018,1.456,.161,.129,coral,'09','TEH'),
                         (.218,1.445,.112,.143,lilac,'10','UBAT'),(.223,1.279,.107,.102,yellow,'02','LIF'),
                         (-.210,1.297,.119,.113,yellow,'01','WC'),(-.001,1.227,.101,.114,blue,'','ATRIUM')):
        card('Tinted tenant outline',x,z,w,h,.011,t)
        if c:
            text(c,x,z+.019,.036,ink,w*.84,y=-.271)
        text(s,x,z-.021 if c else z,.024,cream if t==blue else ink,w*.85,y=-.271)
    disc_front('You are here light edge',.113,-.275,1.315,.032,.010,cream,ui,24)
    disc_front('You are here marker',.113,-.282,1.315,.024,.007,alert,ui,24)
    disc_front('Legend locator dot',-.27,-.27,1.102,.011,.006,alert,ui,14)
    text('ANDA DI SINI',-.250,1.102,.028,ink,.198,'LEFT',-.272)
    text('YOU ARE HERE',.286,1.102,.025,ink,.23,'RIGHT',-.272)

    for i,(name,number,color) in enumerate((('Lorong Pagi Kopitiam','08',mint),('Titik Teh','09',coral),('Farmasi Selasar','10',lilac))):
        z=1.040-i*.052
        card('Tenant index floor pills',-.254,z,.087,.041,.015,color)
        text(number,-.254,z,.029,ink)
        text(name,-.193,z,.035,ink,.392,'LEFT')
    for i,word in enumerate(('G','1','2')):
        x=(i-1)*.136
        card('Floor selector button',x,.854,.114,.044,.012,blue if i==1 else gray)
        text(word,x,.854,.031,cream if i==1 else ink)
    deliver((.35,-1,.237),'ABBDC0',1.15,engine='BLENDER_EEVEE')


if __name__ == '__main__':
    build()
