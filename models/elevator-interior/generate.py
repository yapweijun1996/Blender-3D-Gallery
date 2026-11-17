"""Original metric elevator interior, Blender 5.2.3. No external assets.

Source/export/studio layout follows self-checkout-machine. No random inputs.
Blender +Z up / -Y front exports to glTF +Y up / +Z front.
"""
from pathlib import Path
import bpy
import math
import sys
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'elevator-interior'
ROOT = 'ASSET_ElevatorInterior'
IVORY = (.82, .81, .77)
GRAPHITE = (.105, .125, .14)
STONE = (.32, .35, .36)
BUTTON = (.72, .75, .75)


def linear(rgb):
    return tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb)+(1,)


def materials():
    matte = bpy.data.materials.new('Neutral panels and stone')
    matte.use_nodes = True
    shader = matte.node_tree.nodes['Principled BSDF']
    shader.inputs['Roughness'].default_value = .48
    color = matte.node_tree.nodes.new('ShaderNodeVertexColor')
    color.layer_name = 'SurfaceColor'
    matte.node_tree.links.new(color.outputs['Color'], shader.inputs['Base Color'])
    steel = bpy.data.materials.new('Polished stainless and mirror')
    steel.use_nodes = True
    shader = steel.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = linear((.83, .86, .87))
    shader.inputs['Metallic'].default_value = 1
    shader.inputs['Roughness'].default_value = .095
    light = bpy.data.materials.new('Warm white ceiling diffuser')
    light.use_nodes = True
    shader = light.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = linear((1, .96, .84))
    shader.inputs['Emission Color'].default_value = linear((1, .96, .84))
    shader.inputs['Emission Strength'].default_value = 2.2
    shader.inputs['Roughness'].default_value = .55
    for material in [matte, steel, light]:
        material.use_backface_culling = True
    return matte, steel, light


def finish(o, name, material, batch, bevel=0, rgb=None):
    o.name = name
    o.parent = bpy.data.objects[ROOT]
    o.data.materials.append(material)
    o['delivery_mesh'] = batch
    if rgb is not None:
        attr = o.data.color_attributes.new(name='SurfaceColor', type='FLOAT_COLOR', domain='CORNER')
        for item in attr.data:
            item.color = linear(rgb)
    if bevel:
        edge = o.modifiers.new('Manufactured edge', 'BEVEL')
        edge.width = bevel
        edge.segments = 2
        o.modifiers.new('Corner normals', 'WEIGHTED_NORMAL')
    return o


def box(name, loc, dims, material, batch, bevel=.002, rgb=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, name, material, batch, bevel, rgb)


def rod(name, a, b, radius, material, batch, bevel=.001, rgb=None):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=radius, depth=(b-a).length, location=(a+b)/2)
    o = bpy.context.object
    o.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    finish(o, name, material, batch, bevel, rgb)
    for face in o.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    return o


def build():
    root = bpy.data.objects.new(ROOT, None)
    bpy.context.scene.collection.objects.link(root)
    root['units'] = 'metres'
    root['origin'] = 'floor centre'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['scope'] = 'Static open car; four telescoping door leaves, no operating logic'
    matte, steel, light = materials()
    # Outer envelope 1.6 x 1.5 x 2.4 m. Finished floor top is 0.06 m.
    box('FLOOR_Base', (0, 0, .026), (1.6, 1.5, .052), matte, 'FLOOR_Stone', .003, GRAPHITE)
    box('FLOOR_Finish', (0, .023, .056), (1.472, 1.334, .008), matte, 'FLOOR_Stone', .001, STONE)
    # Dark backing exposes deliberate narrow reveals between neutral wall panels.
    box('WALL_RearBacking', (0, .727, 1.218), (1.6, .046, 2.328), matte, 'CABIN_Panels', .002, GRAPHITE)
    for side in [-1, 1]:
        box('WALL_SideBacking', (side*.777, 0, 1.218), (.046, 1.41, 2.328), matte, 'CABIN_Panels', .002, GRAPHITE)
        for y in [-.47, -.02, .43]:
            box('WALL_SidePanel', (side*.747, y, 1.245), (.014, .442, 2.19), matte, 'CABIN_Panels', .003, IVORY)
        box('SKIRT_Side', (side*.735, 0, .112), (.014, 1.37, .104), steel, 'FRAME_TrimAndHandrail')
        box('CORNICE_Side', (side*.73, 0, 2.327), (.02, 1.37, .045), steel, 'FRAME_TrimAndHandrail')
    for x in [-.494, 0, .494]:
        box('WALL_RearPanel', (x, .697, 1.245), (.486, .014, 2.19), matte, 'CABIN_Panels', .003, IVORY)
    box('SKIRT_Rear', (0, .682, .112), (1.47, .014, .104), steel, 'FRAME_TrimAndHandrail')
    # Rear mirror above a supported rail; mirror uses environment-reflective PBR.
    box('MIRROR_DarkReveal', (0, .681, 1.68), (1.236, .02, .89), matte, 'CABIN_Panels', .006, GRAPHITE)
    box('MIRROR_RearPanel', (0, .667, 1.68), (1.202, .01, .856), steel, 'MIRROR_Rear', .003)
    for x in [-.611, .611]:
        box('MIRROR_FrameUpright', (x, .661, 1.68), (.015, .016, .89), steel, 'FRAME_TrimAndHandrail')
    for z in [1.242, 2.118]:
        box('MIRROR_FrameHorizontal', (0, .661, z), (1.236, .016, .014), steel, 'FRAME_TrimAndHandrail')
    rod('HANDRAIL_Rear', (-.645, .585, 1.04), (.645, .585, 1.04), .022, steel, 'FRAME_TrimAndHandrail')
    for x in [-.56, .56]:
        rod('HANDRAIL_RearReturn', (x, .585, 1.04), (x, .683, 1.04), .014, steel, 'FRAME_TrimAndHandrail')
    rod('HANDRAIL_Left', (-.66, -.48, 1.04), (-.66, .50, 1.04), .022, steel, 'FRAME_TrimAndHandrail')
    for y in [-.40, .42]:
        rod('HANDRAIL_LeftReturn', (-.66, y, 1.04), (-.733, y, 1.04), .014, steel, 'FRAME_TrimAndHandrail')
    # Eight unlabelled concave-looking disks on the inner right wall.
    box('CONTROL_Backplate', (.725, -.096, 1.205), (.026, .222, .606), steel, 'FRAME_TrimAndHandrail', .009)
    box('CONTROL_Inset', (.708, -.096, 1.205), (.012, .188, .558), matte, 'CONTROL_UnlabelledButtons', .003, GRAPHITE)
    for row in range(4):
        for column in range(2):
            y = -.148+column*.104
            z = 1.40-row*.13
            rod(f'BUTTON_Bezel_{row}_{column}', (.696, y, z), (.705, y, z), .028, steel, 'FRAME_TrimAndHandrail')
            rod(f'BUTTON_Unlabelled_{row}_{column}', (.690, y, z), (.699, y, z), .020, matte, 'CONTROL_UnlabelledButtons', .001, BUTTON)
    # Real ceiling slab and recessed rectangular luminous panel (no exported light).
    box('CEILING_Slab', (0, 0, 2.375), (1.6, 1.5, .05), matte, 'CABIN_Panels', .002, IVORY)
    box('LIGHT_Recess', (0, .04, 2.345), (1.20, .98, .02), matte, 'CABIN_Panels', .006, GRAPHITE)
    box('LIGHT_CeilingPanel', (0, .04, 2.331), (1.14, .92, .012), light, 'LIGHT_Ceiling', .005)
    # Four telescopic leaves are stowed inside the envelope. Two tracks per side
    # permit a believable 0.9 m opening without leaves protruding past the car.
    for side, word in [(-1, 'Left'), (1, 'Right')]:
        box('FRAME_OuterPost_'+word, (side*.774, -.707, 1.13), (.052, .086, 2.14), steel, 'FRAME_TrimAndHandrail', .004)
        box('FRAME_InnerJamb_'+word, (side*.473, -.647, 1.16), (.046, .046, 2.20), steel, 'FRAME_TrimAndHandrail', .003)
        for layer, x, y in [('Inner', .579, -.690), ('Outer', .642, -.728)]:
            name = 'DOOR_'+word+layer
            o = box(name, (side*x, y, 1.14), (.242, .024, 2.148), steel, name, .003)
            o['door_state'] = 'open; static telescoping leaf'
    box('FRAME_Header', (0, -.700, 2.275), (1.6, .10, .15), steel, 'FRAME_TrimAndHandrail', .004)
    box('FRAME_UpperReveal', (0, -.755+ .012, 2.283), (1.44, .006, .012), matte, 'CABIN_Panels', .001, GRAPHITE)
    # Sill has two visible track channels, with no long dark strip in the path.
    box('SILL_Threshold', (0, -.697, .047), (1.51, .106, .026), steel, 'FRAME_TrimAndHandrail', .002)
    for y in [-.681, -.718]:
        box('SILL_Track', (0, y, .0605), (1.43, .006, .003), matte, 'FLOOR_Stone', .0005, GRAPHITE)


def export(path):
    """Evaluate and batch copies; the saved source retains individual parts."""
    root = bpy.data.objects[ROOT]
    deps = bpy.context.evaluated_depsgraph_get()
    groups = {}
    for source in list(root.children_recursive):
        if source.type != 'MESH':
            continue
        data = bpy.data.meshes.new_from_object(source.evaluated_get(deps), depsgraph=deps)
        o = bpy.data.objects.new('DELIVERY_'+source.name, data)
        bpy.context.scene.collection.objects.link(o)
        o.matrix_world = source.matrix_world.copy()
        groups.setdefault(source['delivery_mesh'], []).append(o)
    # Temporarily free exact mesh names for stable runtime nodes.
    names = {o: o.name for o in root.children_recursive}
    for o in names:
        o.name += '_Source'
    root.name = ROOT+'_Source'
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
        o.name = name
        o.data.name = name
        o.parent = anchor
        bpy.context.scene.cursor.location = (0, 0, 0)
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        batches.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in [anchor]+batches:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
        export_apply=True, export_yup=True, export_animations=False, export_texcoords=False,
        export_extras=True, export_cameras=False, export_lights=False)
    for o in batches+[anchor]:
        bpy.data.objects.remove(o, do_unlink=True)
    for o, name in names.items():
        o.name = name
    root.name = ROOT


def aim(o, point):
    o.rotation_euler = (Vector(point)-o.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    s = bpy.context.scene
    s.world = bpy.data.worlds.new('Neutral studio')
    s.world.use_nodes = True
    s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.10, .13, .17, 1)
    s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .55
    for name, loc, power, size in [('Key', (-3,-5,6), 650, 4), ('Fill', (4,-3,4), 400, 3), ('Rim', (1,4,5), 750, 3)]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        o = bpy.context.object
        o.name = 'STUDIO_'+name
        o.data.energy = power
        o.data.size = size
        aim(o, (0,0,1.2))
    bpy.ops.object.light_add(type='AREA', location=(0,.04,2.31))
    o = bpy.context.object
    o.name = 'STUDIO_CeilingBounce'
    o.data.energy = 32
    o.data.shape = 'RECTANGLE'
    o.data.size = 1.1
    o.data.size_y = .9
    bpy.ops.object.camera_add()
    s.camera = bpy.context.object
    s.camera.name = 'STUDIO_Camera'
    s.camera.data.type = 'ORTHO'
    s.camera.data.ortho_scale = 2.95
    s.render.engine = 'CYCLES'
    s.cycles.samples = 48
    s.cycles.seed = 0
    s.cycles.use_denoising = True
    s.render.resolution_x = s.render.resolution_y = 900
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.view_settings.view_transform = 'AgX'


def render_views():
    s = bpy.context.scene
    for name, loc in [('hero',(-.40,-2.65,1.45)), ('front',(0,-2.65,1.35)),
                      ('side',(5,0,1.3)), ('3q',(-3.5,-5,3.0)), ('interior',(0,-.62,1.40))]:
        s.camera.data.type = 'ORTHO' if name in ['side','3q'] else 'PERSP'
        s.camera.data.lens = 15 if name == 'interior' else 25
        s.camera.location = loc
        aim(s.camera, (0,.45,1.35) if name == 'interior' else (0,0,1.20))
        s.render.filepath = str(HERE/'previews'/(name+'.png'))
        bpy.ops.render.render(write_still=True)


def main():
    for folder in ['sources','exports','previews','reports','metadata']:
        (HERE/folder).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        s = bpy.context.scene
        s.unit_settings.system = 'METRIC'
        s.unit_settings.scale_length = 1
        build()
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')), compress=True)
    export(HERE/'exports/optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
