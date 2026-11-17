"""Original metric sliding-lid freezer. Blender 5.2.3; no external inputs."""
from pathlib import Path
import math
import sys
import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'ice-cream-chest-freezer'
ROOT = 'ASSET_IceCreamChestFreezer'
GROUPS = ['Cabinet', 'Contents', 'Lid_Left', 'Lid_Right']


def material(name, rgb, roughness=.45, metallic=0, alpha=1):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    color = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (alpha,)
    m.diffuse_color = color
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = color
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Alpha'].default_value = alpha
    if alpha < 1:
        m.surface_render_method = 'DITHERED'
        m.use_backface_culling = True
    return m


def empty(name, parent=None, location=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    o.location = location
    return o


def finish(o, name, mat, parent, bevel=.003):
    o.name = name
    o.parent = parent
    o.data.materials.append(mat)
    if bevel:
        mod = o.modifiers.new('Manufactured radii', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        mod = o.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
        mod.keep_sharp = True
    return o


def box(name, location, dimensions, mat, parent, bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    o.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.location = location
    return finish(o, name, mat, parent, min(bevel, min(dimensions) * .22))


def lathe(name, profile, location, mat, parent, segments=24, ripple=False):
    vertices, rings, faces = [], [], []
    for radius, height in profile:
        ring = []
        for i in range(1 if radius == 0 else segments):
            a = i * 2 * math.pi / segments
            h = height + (.0025 * math.sin(a * 3) * radius / .115 if ripple else 0)
            ring.append(len(vertices))
            vertices.append((radius * math.cos(a), radius * math.sin(a), h))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            if len(a) == 1:
                faces.append((a[0], b[j], b[i]))
            elif len(b) == 1:
                faces.append((a[i], a[j], b[0]))
            else:
                faces.append((a[i], a[j], b[j], b[i]))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(o)
    o.location = location
    finish(o, name, mat, parent, 0)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return o


def build():
    root = empty(ROOT)
    root['units'] = 'metres'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['scope'] = 'P1 static display prop; independent sliding lids; no runtime interaction'
    ivory = material('Porcelain enamel - warm ivory', (.89, .88, .82), .33)
    teal = material('Powder coat - deep lagoon', (.14, .32, .33), .38, .12)
    dark = material('Rubber and vent recess', (.085, .11, .12), .72)
    tub = material('Plain tub - warm white', (.95, .93, .86), .42)
    glass = material('Blank glazing - pale aqua', (.68, .89, .88), .16, 0, .17)
    flavors = [material('Frozen cream - ' + name, color, .68) for name, color in [
        ('vanilla', (.94, .82, .56)), ('strawberry', (.86, .48, .52)),
        ('pistachio', (.60, .75, .50)), ('cocoa', (.39, .23, .16)),
        ('mango', (.96, .63, .26)), ('coconut', (.94, .93, .85))]]
    cabinet = empty('Cabinet', root)
    box('Plinth', (0, 0, .075), (1.43, .68, .09), dark, cabinet, .016)
    for x in [-.62, .62]:
        for y in [-.26, .26]:
            box('Foot', (x, y, .02), (.085, .085, .04), dark, cabinet, .009)
    box('Insulated floor', (0, 0, .285), (1.50, .75, .33), ivory, cabinet, .025)
    for x in [-.705, .705]:
        box('Insulated end', (x, 0, .645), (.09, .75, .39), ivory, cabinet, .018)
    for y in [-.33, .33]:
        box('Insulated wall', (0, y, .645), (1.32, .09, .39), ivory, cabinet, .016)
    box('Inner well floor', (0, 0, .456), (1.32, .57, .012), tub, cabinet, .004)
    for x in [-.72, .72]:
        box('Upper end rim', (x, 0, .87), (.06, .75, .06), teal, cabinet, .012)
    for y in [-.345, .345]:
        box('Upper long rim', (0, y, .87), (1.38, .06, .06), teal, cabinet, .009)
    # Recessed ventilation, drain and plain control bezel are geometry, not labels.
    box('Front vent recess', (.48, -.376, .235), (.30, .008, .105), dark, cabinet, .009)
    for i in range(7):
        box('Vent slat', (.365 + i * .038, -.382, .235), (.011, .008, .076), ivory, cabinet, .002)
    box('Blank thermostat bezel', (-.52, -.377, .735), (.115, .012, .045), teal, cabinet, .005)
    box('Blank thermostat inset', (-.537, -.384, .735), (.062, .003, .023), dark, cabinet, .002)
    lathe('Drain cap', [(0, 0), (.014, 0), (.014, .006), (0, .006)], (0, 0, 0), teal, cabinet, 16)
    drain = bpy.data.objects['Drain cap']
    drain.rotation_euler.x = math.pi / 2
    drain.location = (-.52, -.377, .20)
    contents = empty('Contents', root)
    for i, (x, y) in enumerate((x, y) for y in [-.142, .142] for x in [-.435, 0, .435]):
        loc = (x, y, .465)
        lathe('Tub_%02d' % (i + 1), [(0, 0), (.103, 0), (.109, .012), (.125, .226),
              (.129, .231), (.129, .237), (.119, .237), (.116, .225), (.097, .018), (0, .018)], loc, tub, contents)
        lathe('Frozen_%02d' % (i + 1), [(0, .04), (.096, .04), (.113, .205),
              (.110, .214), (.082, .222), (.042, .218), (0, .221)], loc, flavors[i], contents, ripple=True)
    # Both tracks stay within the 1.50 m cabinet envelope. Left is partly open.
    for name, x, z in [('Lid_Left', -.10, .853), ('Lid_Right', .345, .881)]:
        group = empty(name, root, (x, 0, z))
        group['axis'] = 'local X'
        group['closed_x_m'] = -.345 if name == 'Lid_Left' else .345
        group['open_x_m'] = .345 if name == 'Lid_Left' else -.345
        group['track_z_m'] = z
        for xx in [-.3375, .3375]:
            box(name + '_End', (xx, 0, 0), (.025, .616, .018), teal, group, .005)
        for y in [-.2955, .2955]:
            box(name + '_Rail', (0, y, 0), (.65, .025, .018), teal, group, .005)
        box(name + '_BlankGlass', (0, 0, 0), (.65, .566, .006), glass, group, .001)
        box(name + '_Handle', (-.235 if name == 'Lid_Left' else .235, -.20, .011),
            (.045, .13, .010), ivory, group, .004)
    return root


def export(destination):
    """Export evaluated copies per placement group without changing source meshes."""
    root = bpy.data.objects[ROOT]
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    temporary = []
    anchor = empty(ROOT + '_Export')
    temporary.append(anchor)
    for key, value in root.items():
        anchor[key] = value
    root.name = ROOT + '_Source'
    anchor.name = ROOT
    try:
        for name in GROUPS:
            group = bpy.data.objects[name]
            copies = []
            for source in group.children_recursive:
                if source.type != 'MESH':
                    continue
                mesh = bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph), depsgraph=depsgraph)
                mesh.transform(group.matrix_world.inverted() @ source.matrix_world)
                obj = bpy.data.objects.new(source.name + '_Export', mesh)
                bpy.context.scene.collection.objects.link(obj)
                copies.append(obj)
            bpy.ops.object.select_all(action='DESELECT')
            for obj in copies:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = copies[0]
            bpy.ops.object.join()
            obj = copies[0]
            obj.name = name + '_Geometry'
            obj.parent = anchor
            obj.matrix_basis = group.matrix_world.copy()
            for key, value in group.items():
                obj[key] = value
            obj['source_parts'] = [c.name for c in group.children_recursive if c.type == 'MESH']
            temporary.append(obj)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in temporary:
            obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(destination), export_format='GLB', use_selection=True,
            export_apply=True, export_yup=True, export_animations=False, export_texcoords=False,
            export_extras=True, export_cameras=False, export_lights=False)
    finally:
        for obj in reversed(temporary):
            mesh = obj.data if obj.type == 'MESH' else None
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        root.name = ROOT


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    scene = bpy.context.scene
    floor = material('STUDIO neutral floor', (.77, .78, .75), .85)
    box('STUDIO_Floor', (0, 0, -.025), (200, 200, .05), floor, None, 0)
    scene.world = bpy.data.worlds.new('Neutral studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.3, .34, .36, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5
    for name, location, energy, size in [('Key', (-3, -4, 5), 750, 3.5),
                                       ('Fill', (4, -1, 4), 500, 3), ('Rim', (1, 4, 5), 650, 2.5)]:
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.shape, data.size = energy, 'DISK', size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = location
        aim(obj, (0, 0, .4))
    data = bpy.data.cameras.new('Studio camera')
    obj = bpy.data.objects.new('Studio camera', data)
    scene.collection.objects.link(obj)
    scene.camera = obj
    data.type, data.ortho_scale = 'ORTHO', 2.25
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'


def render_views():
    scene = bpy.context.scene
    target = Vector((0, 0, .41))
    for name, direction in [('hero', (3, -4.2, 4.5)), ('front', (0, -5, 1.4)),
                            ('side', (5, 0, 2)), ('top', (-2.7, -3.7, 5.4))]:
        scene.camera.location = target + Vector(direction)
        aim(scene.camera, target)
        scene.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)


def main():
    for name in ['sources', 'exports', 'previews', 'reports', 'metadata']:
        (HERE / name).mkdir(parents=True, exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.context.scene.unit_settings.system = 'METRIC'
        bpy.context.scene.unit_settings.scale_length = 1
        build()
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    export(HERE / 'exports/optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
