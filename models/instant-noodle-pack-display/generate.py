"""Original deterministic hanging pillow-bag rack. Blender 5.2.3; no external assets."""
from pathlib import Path
import math
import sys
import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'instant-noodle-pack-display'
ROOT = 'ASSET_InstantNoodlePackDisplay'
TARGET = (0, 0, .90)
IVORY = (.83, .84, .80)
GRAPHITE = (.19, .23, .25)
SILVER = (.68, .73, .75)
COLORS = [(.78, .51, .25), (.66, .33, .25), (.26, .49, .47)]


def linear(rgb):
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)


def material(name, metallic=0, roughness=.45):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    color = mat.node_tree.nodes.new('ShaderNodeVertexColor')
    color.layer_name = 'Color'
    mat.node_tree.links.new(color.outputs['Color'], shader.inputs['Base Color'])
    return mat


def finish(obj, name, mat, parent, color, bevel=0):
    obj.name = name
    obj.parent = parent
    obj.data.materials.append(mat)
    attr = obj.data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
    for entry in attr.data:
        entry.color = linear(color)
    if bevel:
        mod = obj.modifiers.new('Soft manufactured edge', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        obj.modifiers.new('Corner normals', 'WEIGHTED_NORMAL')
    return obj


def box(name, loc, dims, mat, parent, color=IVORY, bevel=.002):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, name, mat, parent, color, min(bevel, min(dims) * .2))


def mesh_object(name, verts, faces, mat, parent, color, loc=(0, 0, 0), smooth=False):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = loc
    for face in mesh.polygons:
        face.use_smooth = smooth
    return finish(obj, name, mat, parent, color)


def tube(name, points, radius, mat, parent):
    # Continuous eight-sided tube with capped ends and shared bend rings.
    points = [Vector(p) for p in points]
    verts, faces, sides = [], [], 8
    for i, p in enumerate(points):
        direction = points[min(i + 1, len(points) - 1)] - points[max(0, i - 1)]
        direction.normalize()
        u = Vector((1, 0, 0))
        v = direction.cross(u).normalized()
        verts.extend(tuple(p + radius * (u * math.cos(j * math.tau / sides) +
                                        v * math.sin(j * math.tau / sides))) for j in range(sides))
    faces.extend([tuple(range(sides - 1, -1, -1)),
                  tuple((len(points) - 1) * sides + j for j in range(sides))])
    for i in range(len(points) - 1):
        for j in range(sides):
            a, b = i * sides + j, i * sides + (j + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    return mesh_object(name, verts, faces, mat, parent, SILVER, smooth=True)


def top_seal(parent, mat, color):
    # Closed octagonal hang hole through a flat, heat-sealed flange.
    w, h, radius = .064, .011, .0042
    outer = [(w, 0), (w, h), (0, h), (-w, h), (-w, 0), (-w, -h), (0, -h), (w, -h)]
    inner = [(radius * math.cos(i * math.pi / 4), radius * math.sin(i * math.pi / 4))
             for i in range(8)]
    verts = [(x, y, z) for y in (-.001, .001) for x, z in outer + inner]
    faces = []
    for i in range(8):
        j = (i + 1) % 8
        faces.extend([(i, j, 8 + j, 8 + i), (16 + i, 24 + i, 24 + j, 16 + j),
                      (8 + i, 8 + j, 24 + j, 24 + i), (i, 16 + i, 16 + j, j)])
    return mesh_object('SEAL_TopWithHangHole', verts, faces, mat, parent, color, (0, 0, -.011))


def pillow(parent, mat, color):
    # Two gently folded convex surfaces, stitched at the thin sides and end seals.
    nx, nz = 8, 8
    verts, faces = [], []
    for side in (-1, 1):
        for row in range(nz + 1):
            v = row / nz
            z = -.022 - .192 * v
            width = .064 * (.94 + .06 * math.sin(math.pi * v) ** .6)
            for col in range(nx + 1):
                u = col / nx
                puff = math.sin(math.pi * u) ** .65 * math.sin(math.pi * v) ** .65
                fold = .0014 * math.sin(8 * math.pi * u) * math.sin(math.pi * u) * (
                    math.exp(-v * 12) + math.exp(-(1 - v) * 12))
                verts.append(((2 * u - 1) * width, side * (.001 + .027 * puff + fold), z))
    stride = (nx + 1) * (nz + 1)
    for side in range(2):
        for row in range(nz):
            for col in range(nx):
                a = side * stride + row * (nx + 1) + col
                faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    boundary = list(range(nx + 1))
    boundary += [row * (nx + 1) + nx for row in range(1, nz + 1)]
    boundary += [nz * (nx + 1) + col for col in range(nx - 1, -1, -1)]
    boundary += [row * (nx + 1) for row in range(nz - 1, 0, -1)]
    for i, a in enumerate(boundary):
        b = boundary[(i + 1) % len(boundary)]
        faces.append((a, a + stride, b + stride, b))
    return mesh_object('BAG_PuffedBody', verts, faces, mat, parent, color, smooth=True)


def build(root):
    powder = material('Powder coat', roughness=.52)
    metal = material('Satin steel', metallic=.75, roughness=.30)
    film = material('Plain bag film', roughness=.34)
    box('BASE_FloorPlinth', (0, 0, .028), (.8, .4, .056), powder, root, GRAPHITE, .009)
    box('BASE_InsetTop', (0, 0, .061), (.768, .368, .012), powder, root, IVORY, .003)
    for x in (-.369, .369):
        box('FRAME_Upright', (x, .126, .916), (.032, .036, 1.768), powder, root, IVORY, .003)
        box('FRAME_FootCollar', (x, .126, .087), (.050, .054, .04), powder, root, GRAPHITE)
    box('FRAME_LowerCrossbar', (0, .126, .24), (.720, .026, .03), powder, root, GRAPHITE)
    # Rear stiffeners sit behind the merchandise; no solid backboard is needed.
    for x in (-.20, .20):
        box('FRAME_BackSpine', (x, .135, .94), (.014, .018, 1.40), powder, root, IVORY, .001)
    box('HEADER_Surround', (0, .111, 1.705), (.704, .052, .19), powder, root, GRAPHITE, .008)
    box('HEADER_BlankFace', (0, .081, 1.705), (.665, .009, .150), powder, root, IVORY, .002)
    for row in range(4):
        top = .59 + row * .32
        box(f'FRAME_HookRail_R{row + 1}', (0, .117, top - .011), (.71, .027, .024),
            powder, root, GRAPHITE)
        # Rolled front lip and a recessed blank price strip, with no printed prices.
        rail_z = top - .268
        box(f'PRICE_Rail_R{row + 1}', (0, -.102, rail_z), (.700, .018, .035), powder, root,
            GRAPHITE, .002)
        box(f'PRICE_BlankStrip_R{row + 1}', (0, -.112, rail_z), (.672, .002, .020),
            powder, root, IVORY, .0003)
        for x in (-.331, .331):
            box('PRICE_Support', (x, .006, rail_z - .008), (.009, .232, .012),
                metal, root, SILVER, .001)
        for col in range(5):
            x = (col - 2) * .14
            z = top - .0085
            tube(f'HOOK_R{row + 1}C{col + 1}',
                 [(x, .12, z), (x, -.070, z), (x, -.077, z + .003),
                  (x, -.080, z + .009), (x, -.080, z + .016)], .0017, metal, root)
            anchor = bpy.data.objects.new(f'PACK_R{row + 1}C{col + 1}', None)
            bpy.context.scene.collection.objects.link(anchor)
            anchor.parent = root
            anchor.location = (x, -.044, top)
            anchor['row'] = row + 1
            anchor['column'] = col + 1
            color = COLORS[(col + row) % len(COLORS)]
            pillow(anchor, film, color)
            top_seal(anchor, film, color)
            box('SEAL_Bottom', (0, 0, -.2205), (.128, .002, .013), film, anchor, color, 0)
            # Fine physical heat-crimp ribs on the front, leaving the hang hole clear.
            for rib in range(6):
                xx = (rib - 2.5) * .020
                for zz, height in [(-.011, .018), (-.2205, .010)]:
                    box('SEAL_Crimp', (xx, -.00135, zz), (.0011, .0007, height), film, anchor,
                        tuple(v * .94 for v in color), 0)


def aim(obj):
    obj.rotation_euler = (Vector(TARGET) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new('Neutral studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.22, .25, .29, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .6
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.001))
    floor = bpy.context.object
    floor.name = 'STUDIO_Floor'
    floor_mat = bpy.data.materials.new('Studio floor only')
    floor_mat.diffuse_color = (.30, .35, .38, 1)
    floor.data.materials.append(floor_mat)
    for name, loc, energy, size in [('Key', (-3, -4, 5), 900, 4),
                                     ('Fill', (4, -2, 3), 550, 3),
                                     ('Rim', (1, 3, 4), 1000, 3)]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        obj = bpy.context.object
        obj.name = 'STUDIO_' + name
        obj.data.energy = energy
        obj.data.size = size
        aim(obj)
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.name = 'STUDIO_Camera'
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = 2.16
    scene.camera.location = (2.5, -5, 2.25)
    aim(scene.camera)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.seed = 0
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'


def export(path):
    """Bake evaluated parts into material batches without changing editable sources."""
    root = bpy.data.objects[ROOT]
    root.name = 'SOURCE_InstantNoodlePackDisplay'
    export_root = bpy.data.objects.new(ROOT, None)
    bpy.context.scene.collection.objects.link(export_root)
    for key in root.keys():
        export_root[key] = root[key]
    try:
        bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        groups = {}
        for obj in sorted(root.children_recursive, key=lambda part: part.name):
            if obj.type != 'MESH':
                continue
            mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(graph), preserve_all_data_layers=True,
                                                  depsgraph=graph)
            mesh.transform(root.matrix_world.inverted() @ obj.matrix_world)
            copy = bpy.data.objects.new('EXPORT_' + obj.name, mesh)
            bpy.context.scene.collection.objects.link(copy)
            copy.parent = export_root
            groups.setdefault(obj.data.materials[0].name, []).append(copy)
        for name, parts in sorted(groups.items()):
            bpy.ops.object.select_all(action='DESELECT')
            for part in parts:
                part.select_set(True)
            bpy.context.view_layer.objects.active = parts[0]
            bpy.ops.object.join()
            parts[0].name = 'BATCH_' + name.replace(' ', '')
        bpy.ops.object.select_all(action='DESELECT')
        export_root.select_set(True)
        for obj in export_root.children_recursive:
            obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                                  export_apply=True, export_yup=True, export_animations=False,
                                  export_texcoords=False, export_extras=True,
                                  export_cameras=False, export_lights=False)
    finally:
        for obj in list(export_root.children_recursive):
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        bpy.data.objects.remove(export_root, do_unlink=True)
        root.name = ROOT


def render_views():
    scene = bpy.context.scene
    for name, loc in [('hero', (2.5, -5, 2.25)), ('front', (0, -6, .90)),
                      ('side', (6, 0, 1.20)), ('3q', (-3, -5, 2.15))]:
        scene.camera.location = loc
        aim(scene.camera)
        scene.render.image_settings.file_format = 'PNG'
        scene.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)
        scene.render.image_settings.file_format = 'WEBP'
        scene.render.image_settings.quality = 88
        bpy.data.images['Render Result'].save_render(str(HERE / 'previews' / (name + '.webp')), scene=scene)


def main():
    for folder in ['sources', 'exports', 'previews', 'reports', 'metadata']:
        (HERE / folder).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        scene = bpy.context.scene
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = 1
        root = bpy.data.objects.new(ROOT, None)
        scene.collection.objects.link(root)
        root['units'] = 'metres'
        root['front_axis'] = 'Blender -Y / glTF +Z'
        root['origin'] = 'Floor centre of base footprint'
        root['scope'] = 'Static unbranded hanging pillow-bag rack; S06 / P2'
        root['pack_count'] = 20
        root['row_count'] = 4
        build(root)
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    export(HERE / 'exports' / 'optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
