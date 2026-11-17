"""Original deterministic atrium fountain; Blender 5.2.3, no external assets.

Layout/export convention follows self-checkout-machine. Blender metres/+Z up/
-Y front exports to glTF metres/+Y up/+Z front. --export-source preserves edits.
"""
from pathlib import Path
import math
import sys
import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'atrium-fountain'
ROOT = 'ASSET_AtriumFountain'
TARGET = (0, 0, .94)
STONE = (.76, .74, .67)
DARK = (.27, .31, .30)


def linear(rgb):
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb)


def material(name, rgb, roughness, metallic=0, alpha=1, vertex=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    rgba = (*linear(rgb), alpha)
    p.inputs['Base Color'].default_value = rgba
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Alpha'].default_value = alpha
    m.diffuse_color = rgba
    if alpha < 1:
        m.surface_render_method = 'BLENDED'
        m.use_backface_culling = False
        p.inputs['IOR'].default_value = 1.333
    if vertex:
        attr = m.node_tree.nodes.new('ShaderNodeVertexColor')
        attr.layer_name = 'Color'
        m.node_tree.links.new(attr.outputs['Color'], p.inputs['Base Color'])
    return m


def mesh(name, vertices, faces, mat, root, rgb=None, sector=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    o = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(o)
    o.parent = root
    data.materials.append(mat)
    for face in data.polygons:
        face.use_smooth = abs(face.normal.z) < .98
    if rgb:
        attr = data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
        for face in data.polygons:
            # Subtle, fixed sixteen-block stone variation, without image textures.
            angle = math.atan2(face.center.y, face.center.x) % math.tau
            block = int(angle / math.tau * 16)
            factor = (1, .986, 1.014, .995)[block % 4] if sector else 1
            color = (*linear(tuple(v * factor for v in rgb)), 1)
            for i in face.loop_indices:
                attr.data[i].color = color
    return o


def lathe(name, profile, mat, root, rgb=None, segments=96, sector=False):
    vertices, faces, rings = [], [], []
    for r, z in profile:
        ring = []
        for k in range(segments if r else 1):
            angle = math.tau * k / segments
            ring.append(len(vertices))
            vertices.append((r * math.cos(angle), r * math.sin(angle), z))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(segments):
            j = (k + 1) % segments
            if len(a) == 1:
                faces.append((a[0], b[k], b[j]))
            elif len(b) == 1:
                faces.append((a[k], b[0], a[j]))
            else:
                faces.append((a[k], b[k], b[j], a[j]))
    return mesh(name, vertices, faces, mat, root, rgb, sector)


def jet_mesh(root, water):
    vertices, faces = [], []
    steps, sides = 32, 8
    for jet in range(8):
        angle = math.tau * jet / 8 + math.pi / 8
        radial = Vector((math.cos(angle), math.sin(angle), 0))
        lateral = Vector((-math.sin(angle), math.cos(angle), 0))
        start = len(vertices)
        for step in range(steps + 1):
            t = step / steps
            r = 1.86 - 1.16 * t
            z = .69 + .60 * t + 3.5 * t * (1 - t)
            center = radial * r + Vector((0, 0, z))
            tangent = radial * -1.16 + Vector((0, 0, .60 + 3.5 * (1 - 2 * t)))
            across = tangent.normalized().cross(lateral).normalized()
            radius = .028 * (1 - .20 * t)
            for side in range(sides):
                theta = math.tau * side / sides
                vertices.append(tuple(center + radius * (lateral * math.cos(theta) + across * math.sin(theta))))
        for step in range(steps):
            for side in range(sides):
                j = (side + 1) % sides
                a, b = start + step * sides + side, start + step * sides + j
                faces.append((a, b, b + sides, a + sides))
        faces.append(tuple(start + k for k in reversed(range(sides))))
        faces.append(tuple(start + steps * sides + k for k in range(sides)))
    o = mesh('WATER_Jets', vertices, faces, water, root)
    o['jet_count'] = 8
    o['runtime_role'] = 'Eight disconnected static arcs; consumer may deform vertices or replace material'
    o['source_equation'] = 'r=1.86-1.16*t; z=0.69+0.60*t+3.5*t*(1-t); t in [0,1]'
    return o


def build():
    root = bpy.data.objects.new(ROOT, None)
    bpy.context.scene.collection.objects.link(root)
    root['units'] = 'metres'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['origin'] = 'floor centre'
    root['scope'] = 'Static visual water feature; runtime water animation supplied by consumer'
    stone = material('Honed stone palette', (1, 1, 1), .72, vertex=True)
    bronze = material('Satin bronze fittings', (.51, .40, .23), .32, metallic=.72)
    water = material('Translucent aqua water', (.32, .69, .71), .14, alpha=.49)

    lathe('STONE_RecessedFoot', [(0, 0), (2.34, 0), (2.39, .035), (2.39, .115),
          (2.35, .145), (0, .145)], stone, root, DARK)
    # Continuous closed stone shell: eased outer profile, broad coping and inner wall.
    lathe('STONE_Basin', [(0, .13), (2.41, .13), (2.46, .18), (2.46, .62),
          (2.485, .66), (2.50, .70), (2.50, .77), (2.47, .80),
          (2.22, .80), (2.18, .77), (2.17, .71), (2.17, .30),
          (2.10, .24), (0, .24)], stone, root, STONE, 128, True)
    lathe('STONE_ShadowReveal', [(2.461, .22), (2.464, .22), (2.464, .245),
          (2.461, .245), (2.461, .22)], stone, root, DARK, 128)
    lathe('STONE_CentralPedestal', [(0, .24), (.43, .24), (.43, .68), (.40, .74),
          (.30, .79), (.25, .87), (.25, 1.02), (.35, 1.09), (.38, 1.12),
          (0, 1.12)], stone, root, STONE, 64)
    lathe('STONE_LowerBowl', [(0, 1.07), (.36, 1.07), (.53, 1.10), (.73, 1.17),
          (.87, 1.27), (.91, 1.33), (.90, 1.37), (.85, 1.38),
          (.79, 1.31), (.67, 1.25), (.42, 1.19), (0, 1.19)], stone, root, STONE)
    lathe('STONE_UpperPedestal', [(0, 1.18), (.23, 1.18), (.23, 1.40),
          (.17, 1.46), (.15, 1.63), (.23, 1.70), (0, 1.70)], stone, root, STONE, 64)
    lathe('STONE_UpperBowl', [(0, 1.66), (.22, 1.66), (.34, 1.71), (.46, 1.79),
          (.53, 1.87), (.53, 1.92), (.50, 1.95), (.46, 1.94),
          (.40, 1.85), (.27, 1.79), (0, 1.79)], stone, root, STONE, 64)
    lathe('METAL_CenterFinial', [(0, 1.78), (.095, 1.78), (.095, 1.97),
          (.06, 2.02), (.035, 2.12), (0, 2.15)], bronze, root, segments=24)
    for k in range(8):
        angle = math.tau * k / 8 + math.pi / 8
        x, y = 1.86 * math.cos(angle), 1.86 * math.sin(angle)
        o = lathe(f'METAL_Nozzle_{k + 1:02}', [(0, .35), (.075, .35), (.075, .65),
                  (.055, .68), (0, .68)], bronze, root, segments=16)
        o.location.x, o.location.y = x, y
    lathe('WATER_Surface', [(0, .632), (2.163, .632), (2.163, .638),
          (0, .638)], water, root, segments=128)
    bpy.data.objects['WATER_Surface']['runtime_role'] = 'Shallow main-basin water disc; animate material or vertices'
    for name, radius, height in [('Lower', .78, 1.295), ('Upper', .405, 1.865)]:
        lathe('POOL_' + name, [(0, height - .004), (radius, height - .004),
              (radius, height), (0, height)], water, root, segments=64)
    jet_mesh(root, water)
    return root


def aim(o, point):
    o.rotation_euler = (Vector(point) - o.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    s = bpy.context.scene
    s.world = bpy.data.worlds.new('STUDIO_Neutral')
    s.world.use_nodes = True
    s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.19, .24, .27, 1)
    s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
    floor = material('STUDIO_Floor', (.63, .66, .65), .85)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.006))
    bpy.context.object.name = 'STUDIO_Floor'
    bpy.context.object.data.materials.append(floor)
    for name, loc, power, size in [('Key', (-4, -5, 8), 2200, 5),
            ('Fill', (5, -2, 5), 1500, 4), ('Rim', (1, 5, 7), 2600, 4)]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        o = bpy.context.object
        o.name = 'STUDIO_' + name
        o.data.energy, o.data.size = power, size
        aim(o, TARGET)
    bpy.ops.object.camera_add()
    s.camera = bpy.context.object
    s.camera.name = 'STUDIO_Camera'
    s.camera.data.type = 'ORTHO'
    s.render.engine = 'CYCLES'
    s.cycles.samples, s.cycles.seed = 24, 5283
    s.cycles.use_denoising = True
    s.render.resolution_x = s.render.resolution_y = 768
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.view_settings.view_transform = 'AgX'
    set_view('hero')


def set_view(name):
    s = bpy.context.scene
    positions = {'hero': (6, -9, 7), 'front': (0, -10, 3.3),
                 'side': (10, 0, 3.3), '3q': (-7, -8, 5.6)}
    s.camera.location = positions[name]
    s.camera.data.ortho_scale = 6.25
    aim(s.camera, TARGET)


def export(path):
    root = bpy.data.objects[ROOT]
    copies = []
    renamed = []
    groups = [('STONE_', 'STONE_BasinAndBowls'), ('METAL_', 'METAL_Fittings'),
              ('WATER_Jets', 'WATER_Jets'), ('WATER_Surface', 'WATER_Surface'),
              ('POOL_', 'WATER_BowlPools')]
    try:
        for prefix, name in groups:
            bpy.ops.object.select_all(action='DESELECT')
            group = []
            for source in list(root.children_recursive):
                if source.type != 'MESH' or not source.name.startswith(prefix):
                    continue
                o = source.copy()
                o.data = source.data.copy()
                bpy.context.scene.collection.objects.link(o)
                o.select_set(True)
                group.append(o)
            bpy.context.view_layer.objects.active = group[0]
            if len(group) > 1:
                bpy.ops.object.join()
            o = bpy.context.object
            # Release the source name temporarily to retain exact runtime node names.
            source = bpy.data.objects.get(name)
            if source and source not in group:
                renamed.append((source, source.name, source.data.name))
                source.name = 'SOURCE_' + name
                source.data.name = 'SOURCE_' + name
            o.name, o.data.name = name, name
            copies.append(o)
        bpy.ops.object.select_all(action='DESELECT')
        root.select_set(True)
        for o in copies:
            o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
            export_apply=True, export_yup=True, export_animations=False, export_texcoords=False,
            export_extras=True, export_cameras=False, export_lights=False)
    finally:
        for o in copies:
            data = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.meshes.remove(data)
        for source, object_name, data_name in renamed:
            source.name, source.data.name = object_name, data_name


def main():
    for folder in ('sources', 'exports', 'previews', 'metadata', 'reports'):
        (HERE / folder).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        s = bpy.context.scene
        s.unit_settings.system, s.unit_settings.scale_length = 'METRIC', 1
        build()
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    if '--render-only' not in sys.argv:
        export(HERE / 'exports' / 'optimized.glb')
    if '--skip-render' not in sys.argv:
        requested = next((arg.split('=', 1)[1].split(',') for arg in sys.argv if arg.startswith('--views=')), None)
        for name in ('hero', 'front', 'side', '3q'):
            if requested and name not in requested:
                continue
            set_view(name)
            bpy.context.scene.render.filepath = str(HERE / 'previews' / (name + '.png'))
            bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
