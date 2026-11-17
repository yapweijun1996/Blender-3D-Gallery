"""Original deterministic S16 countertop fixture; no external assets.

Metres, Blender +Z up / -Y front. Rebuild or export saved source edits.
"""
from pathlib import Path
import bpy
import bmesh
import math
import sys
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'vehicle-etag-display-stand'
ROOT = 'ASSET_VehicleEtagDisplayStand'
TARGET = (0, 0, .20)
SLOPE = math.radians(30)


def material(name, rgb, metallic=0, roughness=.45):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    color = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = color
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    mat.diffuse_color = color
    return mat


def empty(name, parent=None, location=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent, obj.location = parent, location
    return obj


def mesh(name, vertices, faces, mat, parent):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(data)
    bm.free()
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    data.materials.append(mat)
    return obj


def soften(obj, width, segments=2):
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new('Manufactured edge', 'BEVEL')
    mod.width, mod.segments = width, segments
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    mod = obj.modifiers.new('Corner normals', 'WEIGHTED_NORMAL')
    mod.keep_sharp = True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def box(name, loc, dims, mat, parent, bevel=.002):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.name, obj.dimensions = name, dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.parent, obj.location = parent, loc
    obj.data.materials.append(mat)
    return soften(obj, min(bevel, min(dims) * .35)) if bevel else obj


def rounded(name, width, depth, radius, profile, mat, parent):
    """Closed rounded rectangle; profile stores (height, edge inset)."""
    vertices, faces = [], []
    steps = 5
    for height, inset in profile:
        w, d, r = width / 2 - inset, depth / 2 - inset, radius - inset
        for cx, cy, start in [(w-r, -d+r, -math.pi/2), (w-r, d-r, 0),
                              (-w+r, d-r, math.pi/2), (-w+r, -d+r, math.pi)]:
            for i in range(steps + 1):
                a = start + math.pi / 2 * i / steps
                vertices.append((cx + r * math.cos(a), cy + r * math.sin(a), height))
    n = 4 * (steps + 1)
    faces.append(tuple(reversed(range(n))))
    for ring in range(len(profile) - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append((ring*n+i, ring*n+j, (ring+1)*n+j, (ring+1)*n+i))
    faces.append(tuple((len(profile)-1)*n+i for i in range(n)))
    obj = mesh(name, vertices, faces, mat, parent)
    for polygon in obj.data.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
    return obj


def build(root):
    blue = material('Satin Petrol Stand', (.23, .34, .37), .15, .44)
    ivory = material('Warm Ivory Polymer', (.88, .90, .87), 0, .36)
    dark = material('Blank Smoke Window and Pads', (.12, .17, .19), .05, .27)
    fixture = empty('FIXTURE', root)
    for x in [-.207, .207]:
        for y in [-.132, .132]:
            box('BASE_AntiSlipPad', (x, y, .004), (.045, .038, .008), dark, fixture)
    box('BASE_LowerPlinth', (0, 0, .018), (.50, .35, .024), blue, fixture, .007)
    box('BASE_IvoryReveal', (0, 0, .032), (.484, .334, .004), ivory, fixture, .001)
    box('BASE_UpperDeck', (0, 0, .037), (.478, .328, .006), blue, fixture)
    # Solid wedge: top rises at 30 degrees from front to rear.
    yf, yb, zf = -.148, .112, .064
    zb = zf + (yb-yf) * math.tan(SLOPE)
    vertices = [(-.228, yf, .040), (.228, yf, .040), (.228, yb, .040), (-.228, yb, .040),
                (-.228, yf, zf), (.228, yf, zf), (.228, yb, zb), (-.228, yb, zb)]
    faces = [(0,3,2,1), (0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7), (4,5,6,7)]
    soften(mesh('RISER_SolidSlopedWedge', vertices, faces, blue, fixture), .003)
    for x in [-.176, .176]:
        box('SIGN_RearStem', (x, .146, .146), (.012, .016, .220), blue, fixture)
        box('SIGN_StemSocket', (x, .146, .050), (.033, .031, .022), dark, fixture)
    box('SIGN_Frame', (0, .146, .324), (.452, .018, .152), blue, fixture, .004)
    box('SIGN_BlankCard', (0, .1355, .324), (.427, .003, .127), ivory, fixture, .001)
    # Two rows of three separate transponders, mounted flush to the riser.
    for row, y in enumerate([-.087, .033], 1):
        for col, x in enumerate([-.151, 0, .151], 1):
            index = (row-1)*3 + col
            tag = empty(f'TAG_{index:02d}', root, (x, y, zf+(y-yf)*math.tan(SLOPE)))
            tag.rotation_euler.x = SLOPE
            tag['role'], tag['row'], tag['column'] = 'generic windscreen-mount toll tag', row, col
            tag['has_blank_window'] = True
            for sx in [-.031, .031]:
                box(f'TAG{index:02d}_MountPad', (sx, 0, .0015), (.020, .026, .003), dark, tag, .0007)
            rounded(f'TAG{index:02d}_LowerShell', .108, .060, .010,
                    [(.003, .002), (.005, 0), (.009, 0)], ivory, tag)
            rounded(f'TAG{index:02d}_HousingSeam', .107, .059, .0095,
                    [(.009, 0), (.010, 0)], dark, tag)
            rounded(f'TAG{index:02d}_UpperShell', .108, .060, .010,
                    [(.010, 0), (.018, 0), (.022, .002), (.023, .003)], ivory, tag)
            rounded(f'TAG{index:02d}_BlankWindow', .064, .025, .0045,
                    [(.023, 0), (.0242, .0006)], dark, tag)
            box(f'CRADLE_{index:02d}_FrontStop', (0, -.035, .005), (.116, .007, .010), blue, tag, .001)


def export(path):
    """Batch evaluated copies by material; leave editable source parts intact."""
    source_root = bpy.data.objects[ROOT]
    temporary = []
    export_root = empty(ROOT + '_Export')
    for key in source_root.keys():
        export_root[key] = source_root[key]
    temporary.append(export_root)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    buckets = {}
    try:
        bpy.context.view_layer.update()
        for obj in source_root.children_recursive:
            if obj.type != 'MESH':
                continue
            data = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), depsgraph=depsgraph)
            copy = bpy.data.objects.new('EXPORT_' + obj.name, data)
            bpy.context.scene.collection.objects.link(copy)
            data.transform(obj.matrix_world)
            copy.parent = export_root
            temporary.append(copy)
            buckets.setdefault(obj.data.materials[0].name, []).append(copy)
        for name, objects in buckets.items():
            bpy.ops.object.select_all(action='DESELECT')
            for obj in objects:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = objects[0]
            bpy.ops.object.join()
            bpy.context.object.name = 'MESH_' + name.replace(' ', '')
        source_root.name, export_root.name = ROOT + '_Source', ROOT
        bpy.ops.object.select_all(action='DESELECT')
        export_root.select_set(True)
        for obj in export_root.children_recursive:
            obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                                  export_apply=True, export_yup=True, export_animations=False,
                                  export_texcoords=False, export_extras=True,
                                  export_cameras=False, export_lights=False)
    finally:
        for obj in reversed(temporary):
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except ReferenceError:
                pass
        source_root.name = ROOT


def aim(obj):
    obj.rotation_euler = (Vector(TARGET)-obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new('Slate studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.22, .25, .28, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
    floor = material('STUDIO_Floor', (.25, .28, .31), 0, .8)
    box('STUDIO_Floor', (0, 0, -.026), (200, 200, .05), floor, None, 0)
    for name, loc, energy, size in [('Key', (-3,-4,5), 650, 3), ('Fill', (3,-2,2.8), 450, 2.5),
                                    ('Rim', (1,3,4), 900, 2.5)]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        obj = bpy.context.object
        obj.name, obj.data.energy, obj.data.size = 'STUDIO_'+name, energy, size
        aim(obj)
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.name, scene.camera.data.type = 'STUDIO_Camera', 'ORTHO'
    scene.camera.data.ortho_scale = .69
    scene.camera.location = (.75, -1.30, .85)
    aim(scene.camera)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples, scene.cycles.seed, scene.cycles.use_denoising = 32, 0, True
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'


def render_views():
    scene = bpy.context.scene
    for name, position in [('hero', (.75,-1.30,.85)), ('front', (0,-1.5,.70)),
                           ('rear', (-.85,1.25,.80)), ('side', (1.5,-.04,.55)),
                           ('3q', (-.9,-1.30,.90))]:
        if '--view' in sys.argv and name != sys.argv[sys.argv.index('--view')+1]:
            continue
        scene.camera.location = position
        aim(scene.camera)
        scene.render.filepath = str(HERE/'previews'/(name+'.png'))
        bpy.ops.render.render(write_still=True)
        scene.render.image_settings.file_format = 'WEBP'
        scene.render.image_settings.quality = 90
        bpy.data.images['Render Result'].save_render(str(HERE/'previews'/(name+'.webp')), scene=scene)
        scene.render.image_settings.file_format = 'PNG'


def main():
    for directory in ['sources', 'exports', 'previews', 'reports', 'metadata']:
        (HERE/directory).mkdir(exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', 1
        root = empty(ROOT)
        root['units'], root['front_axis'] = 'metres', 'Blender -Y / glTF +Z'
        root['origin'], root['tag_count'] = 'Counter contact centre', 6
        root['scope'] = 'Static original unbranded S16 P2 e-tag display'
        build(root)
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')), compress=True)
    export(HERE/'exports'/'optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
