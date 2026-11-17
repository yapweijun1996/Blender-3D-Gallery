"""Original deterministic sign module. Blender 5.2.3; no external assets."""
from pathlib import Path
import math
import sys
import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'led-strip-sign-module'
ROOT = 'ASSET_LedStripSignModule'


def material(name, rgb, metal=0, rough=.42, emission=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    color = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = color
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    p.inputs['Emission Color'].default_value = color
    p.inputs['Emission Strength'].default_value = emission
    m.diffuse_color = color
    return m


def finish(o, name, mat, group, bevel=0):
    o.name = name
    o.data.materials.append(mat)
    o.parent = bpy.data.objects[ROOT]
    o['delivery_mesh'] = group
    if bevel:
        modifier = o.modifiers.new('Soft manufactured edges', 'BEVEL')
        modifier.width = bevel
        modifier.segments = 3
        o.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
    return o


def box(name, location, dimensions, mat, group, bevel=.002):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    o = bpy.context.object
    o.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, name, mat, group, bevel)


def outline(width, height, radius, cx=0, cz=.3):
    points = []
    for x, z, start in [(width / 2 - radius, height / 2 - radius, 0),
                         (-width / 2 + radius, height / 2 - radius, 90),
                         (-width / 2 + radius, -height / 2 + radius, 180),
                         (width / 2 - radius, -height / 2 + radius, 270)]:
        for i in range(7):
            angle = math.radians(start + i * 15)
            points.append((cx + x + radius * math.cos(angle), cz + z + radius * math.sin(angle)))
    return points


def ring(name, outer, inner, y, depth, mat, group, cx=0, cz=.3):
    """Closed extruded rounded ring with a real central opening."""
    outside = outline(*outer, cx, cz)
    inside = outline(*inner, cx, cz)
    n = len(outside)
    vertices = [(x, yy, z) for yy in [y - depth / 2, y + depth / 2] for loop in [outside, inside] for x, z in loop]
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.extend([(i, j, n + j, n + i), (2*n + i, 3*n + i, 3*n + j, 2*n + j),
                      (i, 2*n + i, 2*n + j, j), (n + i, n + j, 3*n + j, 3*n + i)])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(o)
    return finish(o, name, mat, group)


def build():
    root = bpy.data.objects.new(ROOT, None)
    bpy.context.scene.collection.objects.link(root)
    root['units'] = 'metres'
    root['origin'] = 'floor centre'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['led_node'] = 'SIGN_LedStrip'
    root['wall_plane_gltf_z'] = -.0725
    graphite = material('Satin graphite housing', (.15, .18, .20), .55, .34)
    porcelain = material('Warm porcelain face and bracket', (.85, .83, .77), .12, .36)
    led = material('Warm white LED diffuser', (1, .90, .73), 0, .28, 4)
    # The main enclosure is exactly 2.4 x 0.6 x 0.12 m. Rear cleats add 25 mm.
    box('Housing_Back', (0, -.0015, .3), (2.4, .098, .6), graphite, 'SIGN_Housing', .009)
    ring('Housing_ProtectiveLip', (2.4, .6, .018), (2.34, .54, .014), -.0615, .022, graphite, 'SIGN_Housing')
    box('Face_Blank', (0, -.0565, .3), (2.22, .012, .42), porcelain, 'SIGN_BlankFace', .005)
    strip = ring('SIGN_LedStrip', (2.30, .50, .020), (2.264, .464, .010), -.0625, .008, led, 'SIGN_LedStrip')
    strip['runtime_role'] = 'Independent emissive perimeter; select this mesh for scene-owned Bloom.'
    strip['recess_m'] = .006
    # Two wall cleats form one separate bracket assembly. Four actual slots stay blank.
    for z in [.15, .45]:
        for x in [-.75, .75]:
            ring('Bracket_SlottedTab', (.20, .07, .006), (.07, .014, .006), .0665, .012,
                 porcelain, 'SIGN_WallBracket', x, z)
        for x, width in [(-.9, .10), (0, 1.30), (.9, .10)]:
            box('Bracket_Rail', (x, .0665, z), (width, .012, .07), porcelain, 'SIGN_WallBracket', 0)
        # Stand-off flanges contact the enclosure and the rear slotted rails.
        box('Bracket_CleatFlange', (0, .054, z + (.024 if z < .3 else -.024)),
            (1.90, .013, .022), porcelain, 'SIGN_WallBracket', .001)


def export(path):
    root = bpy.data.objects[ROOT]
    deps = bpy.context.evaluated_depsgraph_get()
    groups = {}
    for source in list(root.children_recursive):
        if source.type != 'MESH':
            continue
        mesh = bpy.data.meshes.new_from_object(source.evaluated_get(deps), depsgraph=deps)
        o = bpy.data.objects.new('DELIVERY_' + source.name, mesh)
        bpy.context.scene.collection.objects.link(o)
        o.matrix_world = source.matrix_world.copy()
        groups.setdefault(source['delivery_mesh'], []).append(o)
    root.name = ROOT + '_Source'
    anchor = bpy.data.objects.new(ROOT, None)
    bpy.context.scene.collection.objects.link(anchor)
    for key, value in root.items():
        anchor[key] = value
    batches = []
    for name, objects in sorted(groups.items()):
        bpy.ops.object.select_all(action='DESELECT')
        for o in objects:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.join()
        o = bpy.context.object
        # Preserve the public LED name while the editable source exists in memory.
        source = bpy.data.objects.get(name)
        if source and source != o:
            source.name = name + '_Source'
        o.name = name
        source_mesh = bpy.data.meshes.get(name)
        if source_mesh and source_mesh != o.data:
            source_mesh.name = name + '_Source'
        o.data.name = name
        o.parent = anchor
        bpy.context.scene.cursor.location = (0, 0, 0)
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        if name == 'SIGN_LedStrip':
            o['runtime_role'] = 'Scene-owned selective Bloom target'
        batches.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    anchor.select_set(True)
    for o in batches:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
        export_apply=True, export_yup=True, export_animations=False, export_texcoords=False,
        export_extras=True, export_cameras=False, export_lights=False)
    for o in batches:
        mesh = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    bpy.data.objects.remove(anchor, do_unlink=True)
    root.name = ROOT
    source = bpy.data.objects.get('SIGN_LedStrip_Source')
    if source:
        source.name = 'SIGN_LedStrip'
    source_mesh = bpy.data.meshes.get('SIGN_LedStrip_Source')
    if source_mesh:
        source_mesh.name = 'SIGN_LedStrip'


def aim(o, point):
    o.rotation_euler = (Vector(point) - o.location).to_track_quat('-Z', 'Y').to_euler()


def render_views():
    # Render the delivered GLB after reimport; the saved native source stays intact.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(HERE / 'exports/optimized.glb'))
    s = bpy.context.scene
    s.world = bpy.data.worlds.new('Neutral slate studio')
    s.world.use_nodes = True
    s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.095, .12, .15, 1)
    s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5
    target = (0, 0, .3)
    for name, location, energy, size in [('Key', (-2, -3, 4), 420, 3),
                                          ('Fill', (3, -2, 1), 180, 2.5),
                                          ('Rim', (0, 3, 3), 400, 2)]:
        bpy.ops.object.light_add(type='AREA', location=location)
        o = bpy.context.object
        o.name = 'STUDIO_' + name
        o.data.energy = energy
        o.data.size = size
        aim(o, target)
    bpy.ops.object.camera_add()
    s.camera = bpy.context.object
    s.camera.data.type = 'ORTHO'
    s.render.engine = 'CYCLES'
    s.cycles.samples = 24
    s.cycles.use_denoising = True
    s.render.resolution_x = 1200
    s.render.resolution_y = 700
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.view_settings.view_transform = 'AgX'
    views = [('hero', (1.15, -3.8, 1.05), 2.95), ('front', (0, -4, 0), 2.85),
             ('side', (4, 0, .10), 1.35), ('3q', (-1.85, -3.6, 1.25), 2.95),
             ('rear', (1.3, 3.8, .95), 2.95)]
    for name, delta, scale in views:
        s.camera.location = Vector(target) + Vector(delta)
        s.camera.data.ortho_scale = scale
        aim(s.camera, target)
        s.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)
        if name == 'hero':
            s.render.image_settings.file_format = 'JPEG'
            s.render.image_settings.quality = 88
            bpy.data.images['Render Result'].save_render(str(HERE / 'previews/hero.jpg'), scene=s)
            s.render.image_settings.file_format = 'PNG'


def main():
    for folder in ['sources', 'exports', 'metadata', 'previews', 'reports']:
        (HERE / folder).mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        s = bpy.context.scene
        s.unit_settings.system = 'METRIC'
        s.unit_settings.scale_length = 1
        build()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    export(HERE / 'exports/optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
