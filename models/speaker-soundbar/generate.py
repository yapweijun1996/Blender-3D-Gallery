"""Original procedural audio display. Blender 5.2.3; no external assets."""
from pathlib import Path
import math
import sys
import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'speaker-soundbar'
ROOT = 'ASSET_SpeakerSoundbar'
TARGET = (0, 0, .40)
MODULES = ('SOUNDBAR', 'FLOOR_SPEAKER')


def material(name, rgb, metallic=0, roughness=.4):
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


def cloth_material():
    """Bake an original seamless plain weave; one 128 px embedded colour tile."""
    mat = material('Warm graphite grille cloth', (.29, .28, .265), roughness=.93)
    image = bpy.data.images.new('Original procedural plain weave', width=128, height=128, alpha=False)
    pixels, normals = [], []
    for y in range(128):
        for x in range(128):
            warp, weft = (x // 8) % 2, (y // 8) % 2
            strand = math.sin(math.pi * ((x if warp == weft else y) % 8 + .5) / 8)
            gap = min((x % 8), (y % 8)) == 0
            value = .22 + .075 * strand - .035 * gap
            pixels.extend((value * 1.04, value * 1.01, value * .97, 1))
            slope = math.cos(math.pi * ((x if warp == weft else y) % 8 + .5) / 8) * .28
            normal = Vector((-slope if warp == weft else 0, 0 if warp == weft else -slope, 1)).normalized()
            normals.extend(tuple(component * .5 + .5 for component in normal) + (1,))
    image.pixels.foreach_set(pixels)
    image.filepath_raw = str(HERE / 'sources/grille-weave.png')
    image.file_format = 'PNG'
    image.save()
    image.pack()
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.name = 'Original woven cloth tile'
    tex.image = image
    tex.extension = 'REPEAT'
    uv = mat.node_tree.nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'UVMap'
    mat.node_tree.links.new(uv.outputs['UV'], tex.inputs['Vector'])
    mat.node_tree.links.new(tex.outputs['Color'], mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    normal_image = bpy.data.images.new('Original procedural weave normal', width=128, height=128, alpha=False)
    normal_image.colorspace_settings.name = 'Non-Color'
    normal_image.pixels.foreach_set(normals)
    normal_image.filepath_raw = str(HERE / 'sources/grille-weave-normal.png')
    normal_image.file_format = 'PNG'
    normal_image.save()
    normal_image.pack()
    normal_tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    normal_tex.image = normal_image
    mat.node_tree.links.new(uv.outputs['UV'], normal_tex.inputs['Vector'])
    normal_map = mat.node_tree.nodes.new('ShaderNodeNormalMap')
    normal_map.uv_map = 'UVMap'
    normal_map.inputs['Strength'].default_value = .55
    mat.node_tree.links.new(normal_tex.outputs['Color'], normal_map.inputs['Color'])
    mat.node_tree.links.new(normal_map.outputs['Normal'], mat.node_tree.nodes['Principled BSDF'].inputs['Normal'])
    return mat


def empty(name, location=(0, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    return obj


def finish(obj, name, mat, parent, bevel=0):
    obj.name = name
    obj.data.materials.append(mat)
    obj.parent = parent
    if bevel:
        mod = obj.modifiers.new('Manufactured edge', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        obj.modifiers.new('Corner normals', 'WEIGHTED_NORMAL')
    return obj


def box(name, location, dimensions, mat, parent, bevel=.002):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, name, mat, parent, min(bevel, min(dimensions) * .3))


def cloth_panel(name, location, dimensions, mat, parent):
    obj = box(name, location, dimensions, mat, parent, 0)
    # A 48 mm tile with sixteen 3 mm threads; UVs stay in metric proportion.
    uv = obj.data.uv_layers.active
    for poly in obj.data.polygons:
        axes = (1, 2) if abs(poly.normal.x) > .5 else ((0, 2) if abs(poly.normal.y) > .5 else (0, 1))
        for index in poly.loop_indices:
            co = obj.data.vertices[obj.data.loops[index].vertex_index].co
            uv.data[index].uv = (co[axes[0]] / .048, co[axes[1]] / .048)
    return obj


def lathe(name, centre, profile, mat, parent, segments=48):
    """Closed solid of revolution about -Y; zero-radius endpoints use single poles."""
    vertices, rings, faces = [], [], []
    for radius, depth in profile:
        ring = []
        for index in range(1 if radius == 0 else segments):
            angle = 2 * math.pi * index / segments
            ring.append(len(vertices))
            vertices.append((centre[0] + radius * math.cos(angle), centre[1] + depth,
                             centre[2] + radius * math.sin(angle)))
        rings.append(ring)
    pairs = list(zip(rings, rings[1:]))
    if len(rings[0]) > 1 and len(rings[-1]) > 1:
        pairs.append((rings[-1], rings[0]))
    for first, second in pairs:
        for index in range(segments):
            nxt = (index + 1) % segments
            if len(first) == 1:
                faces.append((first[0], second[index], second[nxt]))
            elif len(second) == 1:
                faces.append((first[index], second[0], first[nxt]))
            else:
                faces.append((first[index], second[index], second[nxt], first[nxt]))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return finish(obj, name, mat, parent)


def driver(prefix, x, y, z, radius, graphite, alloy, parent, segments=48):
    def shape(label, profile, mat):
        return lathe(prefix + '_' + label, (x, y, z),
                     [(r * radius, d * radius) for r, d in profile], mat, parent, segments)
    shape('Trim', [(1.05, 0), (1.05, -.055), (.96, -.07), (.96, 0)], alloy)
    shape('Surround', [(.98, -.01), (.98, -.08), (.92, -.15), (.85, -.17),
                       (.79, -.12), (.77, -.06), (.77, 0), (.92, .015)], graphite)
    shape('Cone', [(.78, -.07), (.75, -.10), (.23, .065), (.23, .09), (.78, -.04)], alloy)
    shape('DustCap', [(0, -.015), (.11, -.005), (.19, .025), (.24, .067),
                      (.23, .085), (0, .085)], graphite)


def build(root):
    graphite = material('Graphite enclosure and rubber', (.145, .157, .17), .08, .39)
    alloy = material('Satin driver alloy', (.43, .45, .46), .62, .34)
    cloth = cloth_material()
    bar = empty('SOUNDBAR', (-.22, 0, 0), root)
    speaker = empty('FLOOR_SPEAKER', (.53, 0, 0), root)
    for module in (bar, speaker):
        module['units'] = 'metres'
        module['origin'] = 'Local floor centre of footprint'
        module['front_axis'] = 'Blender -Y / glTF +Z'
    box('BAR_Enclosure', (0, 0, .055), (.9, .15, .082), graphite, bar, .012)
    cloth_panel('BAR_WovenCentreGrille', (0, -.0765, .055), (.526, .005, .059), cloth, bar)
    for x in (-.35, .35):
        driver('BAR_Left' if x < 0 else 'BAR_Right', x, -.077, .055, .032,
               graphite, alloy, bar, 40)
    for x in (-.32, .32):
        for y in (-.045, .045):
            box('BAR_FloorPad', (x, y, .007), (.075, .045, .014), graphite, bar, .004)
    # Tactile buttons have no lettering, symbols, logo or screen content.
    for x in (-.035, 0, .035):
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=.007, depth=.0018,
                                          location=(x, 0, .0964))
        finish(bpy.context.object, 'BAR_TopButton', alloy, bar, .0004)
    box('BAR_RearConnectorPlate', (0, .075, .047), (.17, .002, .030), alloy, bar, .002)
    box('BAR_BlankSocket', (0, .0765, .047), (.04, .002, .012), graphite, bar, .001)

    box('SPEAKER_Plinth', (0, 0, .022), (.28, .32, .028), graphite, speaker, .009)
    for x in (-.095, .095):
        for y in (-.11, .11):
            box('SPEAKER_FloorPad', (x, y, .004), (.035, .045, .008), graphite, speaker, .002)
    box('SPEAKER_Enclosure', (0, 0, .468), (.236, .266, .864), graphite, speaker, .008)
    for x in (-.1183, .1183):
        cloth_panel('SPEAKER_WovenSideGrille', (x, 0, .468), (.002, .228, .80), cloth, speaker)
    driver('SPEAKER_Tweeter', 0, -.135, .782, .039, graphite, alloy, speaker, 40)
    for label, z in [('Midbass', .59), ('Woofer', .35)]:
        driver('SPEAKER_' + label, 0, -.135, z, .085, graphite, alloy, speaker)
    # A dark closed back and rolled lip suggest a recessed reflex port.
    lathe('SPEAKER_PortLip', (0, -.135, .14),
          [(.032, .001), (.032, -.004), (.027, -.010), (.024, -.007), (.024, .002)],
          alloy, speaker, 40)
    lathe('SPEAKER_PortInterior', (0, -.1336, .14),
          [(0, 0), (.0245, 0), (.0245, .0005), (0, .0005)], graphite, speaker, 40)
    box('SPEAKER_RearConnectorPlate', (0, .133, .15), (.092, .003, .085), alloy, speaker, .004)
    for x in (-.023, .023):
        lathe('SPEAKER_BindingPost', (x, .139, .15),
              [(0, -.003), (.008, -.003), (.008, .003), (0, .003)], graphite, speaker, 24)


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new('Neutral studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.22, .25, .29, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
    floor = material('Studio floor only', (.66, .68, .70), roughness=.8)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.001))
    bpy.context.object.name = 'STUDIO_Floor'
    bpy.context.object.data.materials.append(floor)
    for name, location, energy, size in [('Key', (-3, -4, 5), 550, 3),
                                        ('Fill', (4, -2, 3), 350, 3),
                                        ('Rim', (1, 3, 4), 650, 2)]:
        bpy.ops.object.light_add(type='AREA', location=location)
        obj = bpy.context.object
        obj.name = 'STUDIO_' + name
        obj.data.energy = energy
        obj.data.shape = 'DISK'
        obj.data.size = size
        aim(obj, TARGET)
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.name = 'STUDIO_Camera'
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = 1.65
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.seed = 0
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'


def export(path):
    """Export two independent nodes, baking saved source edits in temporary copies."""
    root = bpy.data.objects[ROOT]
    groups = [bpy.data.objects[name] for name in MODULES]
    root.name = 'SOURCE_' + ROOT
    for name, group in zip(MODULES, groups):
        group.name = 'SOURCE_' + name
    output = empty(ROOT)
    for key in root.keys():
        output[key] = root[key]
    try:
        bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        for name, group in zip(MODULES, groups):
            parts = []
            for obj in sorted(group.children_recursive, key=lambda part: part.name):
                if obj.type != 'MESH':
                    continue
                mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(graph))
                mesh.transform(group.matrix_world.inverted() @ obj.matrix_world)
                copy = bpy.data.objects.new('EXPORT_' + obj.name, mesh)
                bpy.context.scene.collection.objects.link(copy)
                copy.parent = output
                parts.append(copy)
            bpy.ops.object.select_all(action='DESELECT')
            for part in parts:
                part.select_set(True)
            bpy.context.view_layer.objects.active = parts[0]
            bpy.ops.object.join()
            combined = parts[0]
            combined.name = name
            combined.data.name = name + '_BatchedMesh'
            combined.data.uv_layers.active_index = 0
            combined.data.uv_layers[0].active_render = True
            # MikkTSpace needs triangulated bevel caps before tangent extraction.
            triangulate = combined.modifiers.new('Export triangulation', 'TRIANGULATE')
            bpy.ops.object.modifier_apply(modifier=triangulate.name)
            combined.matrix_world = group.matrix_world
            for key in group.keys():
                combined[key] = group[key]
        bpy.ops.object.select_all(action='DESELECT')
        output.select_set(True)
        for obj in output.children_recursive:
            obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                                  export_apply=True, export_yup=True, export_animations=False,
                                  export_texcoords=True, export_tangents=True, export_extras=True,
                                  export_cameras=False, export_lights=False)
    finally:
        for obj in list(output.children_recursive):
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        bpy.data.objects.remove(output, do_unlink=True)
        root.name = ROOT
        for name, group in zip(MODULES, groups):
            group.name = name


def render_views():
    scene = bpy.context.scene
    selected = next((set(arg.split('=', 1)[1].split(',')) for arg in sys.argv if arg.startswith('--views=')), None)
    views = [('hero', (1.5, -4, 1.65)), ('front', (0, -5, .40)),
             ('side', (5, 0, .40)), ('3q', (-2.1, -4.5, 1.8)), ('rear', (2, 4.5, 2))]
    if selected is not None:
        assert selected <= {name for name, _ in views}, 'Unknown preview view'
    for name, location in views:
        if selected is not None and name not in selected:
            continue
        scene.camera.location = location
        aim(scene.camera, TARGET)
        scene.render.image_settings.file_format = 'PNG'
        scene.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)
        scene.render.image_settings.file_format = 'WEBP'
        scene.render.image_settings.quality = 85
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
        root = empty(ROOT)
        root['units'] = 'metres'
        root['front_axis'] = 'Blender -Y / glTF +Z'
        root['origin'] = 'Floor centre of display footprint'
        root['scope'] = 'Static audio display; no acoustic or electrical operation'
        build(root)
        studio()
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
