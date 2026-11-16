"""Original deterministic unlabelled can display, metres, Blender 5.2.3.

Source cans share one editable ten-sided mesh. Export batches them into one
two-material mesh plus a neutral plinth, keeping the gallery asset at 3 draws.
"""
from pathlib import Path
import math
import sys
import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'stacked-can-pyramid'
ROOT = 'ASSET_StackedCanPyramid'
RADIAL_SEGMENTS = 10
PITCH = .182
CAN_HEIGHT = .28
BASE_HEIGHT = .12
TARGET = (0, 0, .88)


def material(name, rgb, metallic, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    color = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = color
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    mat.diffuse_color = color
    return mat


def mesh_object(name, vertices, faces, parent, materials):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    for mat in materials:
        mesh.materials.append(mat)
    return obj


def can_prototype(parent, steel, enamel):
    # A single closed lathed shell: rolled lower/upper seams and inset lid.
    profile = [(.079, 0), (.088, .003), (.088, .011), (.084, .015),
               (.084, .265), (.088, .269), (.088, .277), (.080, .280),
               (.076, .276), (.050, .275)]
    vertices = [(radius * math.cos(2 * math.pi * i / RADIAL_SEGMENTS),
                 radius * math.sin(2 * math.pi * i / RADIAL_SEGMENTS), height)
                for radius, height in profile for i in range(RADIAL_SEGMENTS)]
    faces = []
    for ring in range(len(profile) - 1):
        for i in range(RADIAL_SEGMENTS):
            j = (i + 1) % RADIAL_SEGMENTS
            faces.append((ring * RADIAL_SEGMENTS + i, ring * RADIAL_SEGMENTS + j,
                          (ring + 1) * RADIAL_SEGMENTS + j, (ring + 1) * RADIAL_SEGMENTS + i))
    faces += [tuple(reversed(range(RADIAL_SEGMENTS))),
              tuple((len(profile) - 1) * RADIAL_SEGMENTS + i for i in range(RADIAL_SEGMENTS))]
    obj = mesh_object('CAN_Prototype', vertices, faces, parent, [steel, enamel])
    for polygon in obj.data.polygons:
        polygon.material_index = 1 if polygon.index // RADIAL_SEGMENTS == 3 else 0
        polygon.use_smooth = polygon.index < (len(profile) - 1) * RADIAL_SEGMENTS
    return obj


def build():
    root = bpy.data.objects.new(ROOT, None)
    bpy.context.scene.collection.objects.link(root)
    root['units'] = 'metres'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['can_count'] = 91
    root['radial_segments'] = RADIAL_SEGMENTS
    root['scope'] = 'Static original unlabelled supermarket display; no external assets'
    steel = material('Satin tinplate', (.68, .72, .72), .82, .32)
    enamel = material('Blank muted jade band', (.30, .46, .41), .18, .42)
    neutral = material('Neutral warm grey plinth', (.37, .38, .36), .05, .52)
    # Chamfered square profiles keep every edge inside the 1.2 m footprint.
    vertices, faces = [], []
    for half, corner, z in [(.59, .035, 0), (.60, .04, .012),
                             (.60, .04, .108), (.588, .032, BASE_HEIGHT)]:
        vertices.extend([(x, y, z) for x, y in [
            (-half + corner, -half), (half - corner, -half),
            (half, -half + corner), (half, half - corner),
            (half - corner, half), (-half + corner, half),
            (-half, half - corner), (-half, -half + corner)]])
    faces.append(tuple(reversed(range(8))))
    for ring in range(3):
        faces.extend([(ring * 8 + i, ring * 8 + (i + 1) % 8,
                       (ring + 1) * 8 + (i + 1) % 8, (ring + 1) * 8 + i) for i in range(8)])
    faces.append(tuple(range(24, 32)))
    mesh_object('BASE_ChamferedPlinth', vertices, faces, root, [neutral])
    prototype = can_prototype(root, steel, enamel)
    first = True
    for tier, width in enumerate(range(6, 0, -1)):
        for row in range(width):
            for column in range(width):
                obj = prototype if first else bpy.data.objects.new('Can', prototype.data)
                if not first:
                    bpy.context.scene.collection.objects.link(obj)
                first = False
                obj.name = f'CAN_T{tier + 1:02d}_R{row + 1:02d}_C{column + 1:02d}'
                obj.parent = root
                obj.location = ((column - (width - 1) / 2) * PITCH,
                                (row - (width - 1) / 2) * PITCH,
                                BASE_HEIGHT + tier * CAN_HEIGHT)
                obj['tier'] = tier + 1
    return root


def export(path):
    root = bpy.data.objects[ROOT]
    cans = sorted((o for o in root.children if o.name.startswith('CAN_')), key=lambda o: o.name)
    bpy.context.view_layer.update()
    vertices, faces, face_materials, smooth = [], [], [], []
    for obj in cans:
        offset = len(vertices)
        vertices.extend([tuple(obj.matrix_world @ v.co) for v in obj.data.vertices])
        for polygon in obj.data.polygons:
            faces.append(tuple(offset + i for i in polygon.vertices))
            face_materials.append(polygon.material_index)
            smooth.append(polygon.use_smooth)
    batch = mesh_object('CANS_BatchedDisplay', vertices, faces, root, list(cans[0].data.materials))
    for polygon, mat_index, use_smooth in zip(batch.data.polygons, face_materials, smooth):
        polygon.material_index = mat_index
        polygon.use_smooth = use_smooth
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [root, batch, bpy.data.objects['BASE_ChamferedPlinth']]:
        obj.select_set(True)
    try:
        bpy.ops.export_scene.gltf(
            filepath=str(path), export_format='GLB', use_selection=True,
            export_apply=True, export_yup=True, export_animations=False,
            export_texcoords=False, export_extras=True, export_cameras=False,
            export_lights=False)
    finally:
        data = batch.data
        bpy.data.objects.remove(batch, do_unlink=True)
        bpy.data.meshes.remove(data)


def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new('Slate studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.10, .14, .18, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5
    for name, location, power, size in [
        ('Key', (-3, -4, 6), 950, 4), ('Fill', (4, -1, 3), 650, 3),
        ('Rim', (1, 4, 5), 1200, 3)]:
        bpy.ops.object.light_add(type='AREA', location=location)
        light = bpy.context.object
        light.name = 'STUDIO_' + name
        light.data.energy, light.data.size = power, size
        aim(light, TARGET)
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.name = 'STUDIO_Camera'
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = 2.45
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 40
    scene.cycles.seed = 0
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.render.film_transparent = False
    scene.camera.location = (3, -4.2, 3.0)
    aim(scene.camera, TARGET)


def render_views():
    scene = bpy.context.scene
    for name, position in [('hero', (3, -4.2, 3.0)), ('front', (0, -5, 1.03)),
                           ('side', (5, 0, 1.03)), ('3q', (-3, -4, 3.6))]:
        scene.camera.location = position
        aim(scene.camera, TARGET)
        scene.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)


def main():
    for folder in ['sources', 'exports', 'previews', 'reports', 'metadata']:
        (HERE / folder).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        assert bpy.app.version[:3] == (5, 2, 3), bpy.app.version_string
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.context.scene.unit_settings.system = 'METRIC'
        bpy.context.scene.unit_settings.scale_length = 1
        build()
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    export(HERE / 'exports' / 'optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
