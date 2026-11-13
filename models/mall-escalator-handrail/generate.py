"""V2.1 P0 430: original, static escalator handrail subsystem, metres.
No steps, motor, landing or manufacturer interface. --export-source preserves edits.
"""
from pathlib import Path
import math, json, struct, sys
import bpy, bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'mall-escalator-handrail'
ROOT = 'ASSET_MallEscalatorHandrail'
RADIUS = .8
ANGLE = math.pi / 6
RISE = 2.4
RUN = (RISE - 2 * RADIUS * (1 - math.cos(ANGLE))) / math.tan(ANGLE)
END = RUN / 2 + RADIUS * math.sin(ANGLE) + .8


def material(name, rgb, roughness=.4, metallic=0, alpha=1):
    m = bpy.data.materials.new(name); m.use_nodes = True
    def linear(v):
        v /= 255
        return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
    rgba = (*[linear(v) for v in rgb], alpha)
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = rgba
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Alpha'].default_value = alpha
    m.diffuse_color = rgba
    if alpha < 1:
        m.blend_method = 'BLEND'; m.use_backface_culling = False
        m.show_transparent_back = False
    return m


def mesh(name, vertices, faces, mat, smooth=False):
    data = bpy.data.meshes.new(name); data.from_pydata(vertices, [], faces); data.update()
    bm = bmesh.new(); bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(data); bm.free()
    obj = bpy.data.objects.new(name, data); bpy.context.scene.collection.objects.link(obj)
    data.materials.append(mat)
    for f in data.polygons: f.use_smooth = smooth
    return obj


def profile():
    # Analytic tangent transitions: horizontal, 800 mm radius, 30 degree slope,
    # 800 mm radius, horizontal. Samples retain a straight central section.
    pts = [(-END, 1)]
    x0 = -RUN / 2 - RADIUS * math.sin(ANGLE)
    for i in range(13):
        a = ANGLE * i / 12
        pts.append((x0 + RADIUS * math.sin(a), 1 + RADIUS * (1 - math.cos(a))))
    pts.append((RUN / 2, 1 + RISE - RADIUS * (1 - math.cos(ANGLE))))
    for i in range(1, 13):
        a = ANGLE * (1 - i / 12)
        pts.append((RUN / 2 + RADIUS * (math.sin(ANGLE) - math.sin(a)), 1 + RISE - RADIUS * (1 - math.cos(a))))
    pts.append((END, 1 + RISE))
    return pts


def loop_profile(top, radius=.4):
    # Continuous closed capsule following the incline, with smooth 180° returns.
    pts = list(top)
    x, z = top[-1]
    for i in range(1, 33):
        a = math.pi * i / 32
        pts.append((x + radius * math.sin(a), z - radius + radius * math.cos(a)))
    pts += [(x, z - 2 * radius) for x, z in reversed(top[:-1])]
    x, z = top[0]
    for i in range(1, 32):
        a = math.pi * i / 32
        pts.append((x - radius * math.sin(a), z - radius - radius * math.cos(a)))
    return pts


def swept(name, pts, half_width, half_depth, mat, closed=False, sections=12):
    verts, faces = [], []
    for i, (x, z) in enumerate(pts):
        prev = Vector(pts[(i - 1) % len(pts)] if closed or i else pts[0])
        nxt = Vector(pts[(i + 1) % len(pts)] if closed or i < len(pts) - 1 else pts[-1])
        tangent = (nxt - prev).normalized()
        # Planar normal; y is the section width, xz is its shallow crown.
        normal = Vector((-tangent.y, tangent.x))
        for j in range(sections):
            a = 2 * math.pi * j / sections
            d = math.sin(a) * half_depth
            verts.append((x + normal.x * d, math.cos(a) * half_width, z + normal.y * d))
    for i in range(len(pts) if closed else len(pts) - 1):
        ni = (i + 1) % len(pts)
        for j in range(sections):
            nj = (j + 1) % sections
            faces.append((i * sections + j, ni * sections + j, ni * sections + nj, i * sections + nj))
    if not closed:
        faces += [tuple(range(sections - 1, -1, -1)), tuple((len(pts) - 1) * sections + j for j in range(sections))]
    return mesh(name, verts, faces, mat, True)


def extrude(name, outline, y0, y1, mat):
    n = len(outline)
    verts = [(x, y, z) for y in (y0, y1) for x, z in outline]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    return mesh(name, verts, faces, mat)


def empty(name, parent=None, location=(0, 0, 0)):
    o = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(o)
    o.parent = parent; o.location = location
    return o


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def export(root, path):
    bpy.ops.object.select_all(action='DESELECT'); root.select_set(True)
    for o in root.children_recursive: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
        export_apply=True, export_yup=True, export_animations=False, export_extras=True,
        export_texcoords=False, export_cameras=False, export_lights=False)
    # Collapse byte-identical material definitions only; preserve each named mesh.
    data = path.read_bytes(); length = struct.unpack_from('<I', data, 12)[0]
    doc = json.loads(data[20:20 + length]); unique, mapping = [], {}
    for i, m in enumerate(doc['materials']):
        if m not in unique: unique.append(m)
        mapping[i] = unique.index(m)
    for m in doc['meshes']:
        for p in m['primitives']: p['material'] = mapping[p['material']]
    doc['materials'] = unique
    chunk = json.dumps(doc, separators=(',', ':')).encode(); chunk += b' ' * (-len(chunk) % 4)
    tail = data[20 + length:]
    path.write_bytes(struct.pack('<III', 0x46546c67, 2, 20 + len(chunk) + len(tail)) + struct.pack('<II', len(chunk), 0x4e4f534a) + chunk + tail)


def studio():
    s = bpy.context.scene
    floor = material('STUDIO matte backdrop', (221, 224, 218), .95)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.035))
    bpy.context.object.name = 'STUDIO_Floor'; bpy.context.object.data.materials.append(floor)
    target = (0, 0, 1.65)
    for name, position, power, size in [('Key', (-3, -5, 8), 1500, 7), ('Fill', (4, 2, 5), 1100, 6), ('Rim', (0, 4, 7), 1200, 5)]:
        bpy.ops.object.light_add(type='AREA', location=position); o = bpy.context.object
        o.name = 'STUDIO_' + name; o.data.energy = power; o.data.size = size; point_at(o, target)
    bpy.ops.object.camera_add(location=(7, -12, 6.4)); s.camera = bpy.context.object
    s.camera.name = 'STUDIO_Camera'; s.camera.data.type = 'ORTHO'; s.camera.data.ortho_scale = 8.1
    point_at(s.camera, target)
    s.world = bpy.data.worlds.new('Studio environment'); s.world.use_nodes = True
    s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.34, .38, .40, 1)
    s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
    s.render.engine = 'CYCLES'; s.cycles.samples = 32; s.cycles.use_denoising = False
    s.render.resolution_x = s.render.resolution_y = 768; s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'; s.view_settings.view_transform = 'AgX'


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene; s.unit_settings.system = 'METRIC'; s.unit_settings.scale_length = 1
    root = empty(ROOT)
    rubber = material('Black elastomer handrail belt', (25, 29, 32), .48)
    guide = material('Brushed stainless guide rails', (144, 160, 168), .30, .72)
    glass = material('Cool laminated glazing visual proxy', (139, 188, 198), .18, 0, .30)
    casing = material('Satin aluminium lower casing', (139, 152, 161), .40, .65)
    dark = material('Charcoal return channel end caps', (46, 56, 63), .55, .15)
    top = profile(); loop = loop_profile(top)
    parts = [swept('MODULE_ContinuousRubberBelt', loop, .04, .028, rubber, True)]
    parts.append(swept('MODULE_UpperGuideRail', [(x, z - .063) for x, z in top], .028, .020, guide))
    parts.append(swept('MODULE_LowerGlazingRail', [(x, z - .72) for x, z in top], .070, .020, guide))
    # One solid, 12 mm thick glazing sheet. Rounded ends sit inside belt returns.
    glass_outline = loop_profile([(x, z - .077) for x, z in top], .323)
    parts.append(extrude('MODULE_CurvedGlazing', glass_outline, -.006, .006, glass))
    casing_outline = [(x, z - .70) for x, z in top] + [(x, z - 1) for x, z in reversed(top)]
    parts.append(extrude('MODULE_Casing_Near', casing_outline, -.070, -.050, casing))
    parts.append(extrude('MODULE_Casing_Far', casing_outline, .050, .070, casing))
    # End covers occupy only below the rubber return; no blade crosses the loop.
    for label, x, z in [('Lower', -END, 1), ('Upper', END, 3.4)]:
        parts.append(extrude('MODULE_ChannelEnd_' + label, [(x-.012,z-1),(x+.012,z-1),(x+.012,z-.86),(x-.012,z-.86)], -.05, .05, dark))
    for o in parts: o.parent = root
    for name, loc in [('LowerDatum', (-END, 0, 0)), ('UpperDatum', (END, 0, RISE)), ('LowerBeltTangent', (-END, 0, 1)), ('UpperBeltTangent', (END, 0, 3.4)), ('PairPlane', (0, 0, 0))]:
        empty('CONNECTOR_' + name, root, loc)
    root['units'] = 'metres'; root['backlog'] = 'V2.1 P0 item 430'
    root['origin'] = 'Lower datum elevation, plan midpoint of the two horizontal end tangencies; +X ascends.'
    root['slope_degrees'] = 30.; root['nominal_rise_m'] = RISE
    root['scope'] = 'Static single-side handrail / glazing subsystem only. No full escalator 004, landing 429, stationary railing 006, motor, steps, physics or runtime animation.'
    root['interface'] = 'Generic visual envelope only; exact future 004 escalator integration is NOT VERIFIED. No manufacturer, mechanical, installation or safety certification.'
    root['pair_hint'] = 'Optional reuse at Blender Y=-0.64 and +0.64 leaves 1.14 m between casing inner edges. Not a separate asset type or a certified passenger clearance.'
    studio()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    return root


if __name__ == '__main__':
    for folder in ('sources', 'exports', 'previews', 'reports'): (HERE / folder).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
        root = bpy.data.objects[ROOT]
    else: root = build()
    export(root, HERE / 'exports' / 'optimized.glb')
    if '--skip-render' not in sys.argv:
        bpy.context.scene.render.filepath = str(HERE / 'previews' / (SLUG + '.png'))
        bpy.ops.render.render(write_still=True)
