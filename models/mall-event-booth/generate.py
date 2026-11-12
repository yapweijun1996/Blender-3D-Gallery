"""Create the original jade/brass/walnut mall event booth.

Run with Blender 4.0.2: blender --background --python generate.py
PosterPanel and DisplayContent stay as separate source collections and GLB nodes.
"""
from pathlib import Path
import math
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent

def mat(name, rgb, rough=.55, metal=0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    s = m.node_tree.nodes.get('Principled BSDF')
    def lin(v): return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
    s.inputs['Base Color'].default_value = tuple(lin(v / 255) for v in rgb) + (1,)
    s.inputs['Roughness'].default_value = rough; s.inputs['Metallic'].default_value = metal
    m.diffuse_color = s.inputs['Base Color'].default_value
    return m

def finish(o, name, material, bevel=.015):
    o.name = name; o.data.materials.append(material)
    if bevel:
        b = o.modifiers.new('Soft manufactured edge', 'BEVEL'); b.width = bevel; b.segments = 2
        o.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return o

def box(name, xyz, size, material, bevel=.015):
    bpy.ops.mesh.primitive_cube_add(size=1, location=xyz); o = bpy.context.object
    o.dimensions = size; bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, name, material, bevel)

def text(body, xyz, size, material, name):
    c = bpy.data.curves.new(name, 'FONT'); c.body = body; c.align_x = 'CENTER'; c.size = size; c.extrude = .0004; c.resolution_u = 2
    o = bpy.data.objects.new(name, c); bpy.context.collection.objects.link(o); o.location = xyz; o.rotation_euler = (math.pi / 2, 0, math.pi); c.materials.append(material); return o

def cylinder(name, xyz, radius, depth, material):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=depth, location=xyz)
    return finish(bpy.context.object, name, material, .006)

def point_at(o, target): o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()

def palette():
    return {'jade': mat('Deep jade powder coat', (35, 78, 67), .46), 'brass': mat('Brushed champagne brass', (184, 157, 95), .3, .72),
            'walnut': mat('Warm walnut', (109, 72, 46), .48), 'ivory': mat('Warm ivory poster ink', (234, 226, 208), .62),
            'charcoal': mat('Charcoal recess', (25, 32, 31), .7), 'sage': mat('Soft sage accent', (142, 173, 145), .6),
            'coral': mat('Terracotta accent', (186, 99, 72), .6)}

def make_collections():
    root = bpy.data.collections.new('ASSET_MallEventBooth'); bpy.context.scene.collection.children.link(root)
    groups = {}
    for name in ('BoothStructure', 'PosterPanel', 'DisplayContent'):
        c = bpy.data.collections.new(name); root.children.link(c); groups[name] = c
    # Blender operators link to the active collection; move authored objects after creation.
    return root, groups

def move(o, collection):
    for c in list(o.users_collection): c.objects.unlink(o)
    collection.objects.link(o); return o

def build():
    bpy.ops.wm.read_factory_settings(use_empty=True); scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'; scene.unit_settings.scale_length = 1
    root, groups = make_collections(); p = palette()
    def B(group, *args, **kwargs): return move(box(*args, **kwargs), groups[group])
    # Low, open walnut plinth and asymmetric jade/brass arch: a recognisable booth silhouette.
    B('BoothStructure', 'Floor plinth', (0, 0, .055), (2.72, 1.18, .11), p['charcoal'], .035)
    B('BoothStructure', 'Brass plinth reveal', (0, 0, .125), (2.58, 1.04, .035), p['brass'], .01)
    B('BoothStructure', 'Walnut counter body', (0, .28, .62), (2.18, .28, 1.00), p['walnut'], .035)
    B('BoothStructure', 'Jade left wing', (-1.08, .02, 1.08), (.18, .92, 2.0), p['jade'], .03)
    B('BoothStructure', 'Jade right wing', (1.08, .02, 1.08), (.18, .92, 2.0), p['jade'], .03)
    B('BoothStructure', 'Walnut counter top', (0, .04, 1.10), (2.36, 1.02, .10), p['walnut'], .045)
    B('BoothStructure', 'Brass counter edge', (0, .555, 1.08), (2.22, .025, .035), p['brass'], .006)
    for x in (-.79, -.55, -.31, -.07, .17, .41, .65, .89): B('BoothStructure', 'Walnut front slat', (x, .435, .60), (.07, .035, .66), p['walnut'], .008)
    # Independent poster assembly: replace PANEL ART / CAMPAIGN text in the source.
    # The camera and the gallery's default orbit approach from +Y.  Keep all
    # campaign-facing surfaces on +Y so the headline is readable in the
    # shipped preview and in the first viewport frame.
    B('PosterPanel', 'PosterPanel brass frame', (0, .09, 2.04), (1.58, .12, 1.38), p['brass'], .035)
    B('PosterPanel', 'PosterPanel ivory face', (0, .158, 2.04), (1.42, .025, 1.22), p['ivory'], .018)
    B('PosterPanel', 'PosterPanel jade sun', (-.25, .18, 2.26), (.30, .018, .30), p['jade'], .18)
    B('PosterPanel', 'PosterPanel sage block', (.30, .18, 1.83), (.46, .018, .34), p['sage'], .08)
    B('PosterPanel', 'PosterPanel coral stripe', (.23, .18, 2.08), (.58, .018, .07), p['coral'], .02)
    move(text('YOUR STORY', (0, .20, 2.49), .13, p['jade'], 'PosterPanel editable headline'), groups['PosterPanel'])
    move(text('MADE HERE', (0, .20, 1.95), .07, p['jade'], 'PosterPanel editable subhead'), groups['PosterPanel'])
    # Independent content vignette: hero product pedestal, cards and a brass tray.
    B('DisplayContent', 'DisplayContent pedestal', (0, .17, 1.35), (.66, .52, .34), p['jade'], .025)
    B('DisplayContent', 'DisplayContent tray', (0, .17, 1.56), (.82, .64, .045), p['brass'], .018)
    B('DisplayContent', 'DisplayContent card left', (-.62, .18, 1.34), (.27, .04, .34), p['ivory'], .012)
    B('DisplayContent', 'DisplayContent card right', (.62, .18, 1.34), (.27, .04, .34), p['ivory'], .012)
    cylinder('DisplayContent sample plinth', (0, .18, 1.72), .13, .20, p['coral']); move(bpy.context.object, groups['DisplayContent'])
    move(text('EDITABLE DISPLAY', (0, .21, 1.47), .052, p['charcoal'], 'DisplayContent editable label'), groups['DisplayContent'])
    # Root metadata, intentionally explicit for source inspection.
    root['units'] = 'metres'; root['origin'] = 'floor centre'; root['poster_replacement'] = 'Replace PosterPanel face geometry and editable headline/subhead text'; root['display_replacement'] = 'Replace DisplayContent collection objects'; root['source'] = 'Original Blender-3D-Gallery event booth'
    for child in root.children: child['editable_content'] = child.name in ('PosterPanel', 'DisplayContent')
    # Export one evaluated mesh per named collection, preserving named,
    # independently replaceable nodes.  Do not join across semantic groups.
    export_root = bpy.data.objects.new('ASSET_MallEventBooth', None); scene.collection.objects.link(export_root)
    export_parts = [export_root]
    for group_name in ('BoothStructure', 'PosterPanel', 'DisplayContent'):
        originals = [o for o in groups[group_name].objects]
        copies = []
        for original in originals:
            c = original.copy(); c.data = original.data.copy(); scene.collection.objects.link(c); c.select_set(True); copies.append(c)
        for c in copies:
            bpy.context.view_layer.objects.active = c; c.select_set(True)
            if c.type == 'FONT': bpy.ops.object.convert(target='MESH')
        bpy.ops.object.select_all(action='DESELECT')
        for c in copies: c.select_set(True)
        bpy.context.view_layer.objects.active = copies[0]; bpy.ops.object.join(); merged = bpy.context.object; merged.name = f'{group_name} Geometry'
        group_node = bpy.data.objects.new(group_name, None); scene.collection.objects.link(group_node); group_node.parent = export_root
        merged.parent = group_node; group_node['source_collection'] = group_name; export_parts.extend([group_node, merged])
    bpy.ops.object.select_all(action='DESELECT'); export_root.select_set(True)
    for part in export_parts: part.select_set(True)
    bpy.context.view_layer.objects.active = export_root
    (HERE / 'exports').mkdir(exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(HERE / 'exports/mall-event-booth.glb'), export_format='GLB', use_selection=True, export_apply=True, export_yup=True, export_animations=False, export_texcoords=False, export_extras=True, export_cameras=False, export_lights=False)
    for part in reversed(export_parts):
        if part != export_root: bpy.data.objects.remove(part, do_unlink=True)
    bpy.data.objects.remove(export_root, do_unlink=True)
    # Studio lighting and camera stay source-only.
    ground = mat('Studio backdrop', (205, 214, 204), .95); box('Studio floor (not exported)', (0, 0, -.07), (200, 200, .1), ground, 0)
    for name, pos, energy, size in [('Key', (3.5, 4, 5), 850, 4), ('Fill', (-4, 1, 3), 500, 4), ('Rim', (1, -4, 4), 700, 3)]:
        bpy.ops.object.light_add(type='AREA', location=pos); l = bpy.context.object; l.name = name; l.data.energy = energy; l.data.shape = 'DISK'; l.data.size = size; point_at(l, (0, 0, 1.15))
    bpy.ops.object.camera_add(location=(3.9, 5.8, 3.35)); scene.camera = bpy.context.object; scene.camera.data.type = 'ORTHO'; scene.camera.data.ortho_scale = 3.65; point_at(scene.camera, (0, 0, 1.25))
    world = bpy.data.worlds.new('Studio environment'); world.use_nodes = True; world.node_tree.nodes['Background'].inputs['Color'].default_value = (.25, .31, .28, 1); world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5; scene.world = world
    scene.render.engine = 'BLENDER_EEVEE'; scene.render.resolution_x = scene.render.resolution_y = 768; scene.render.resolution_percentage = 100; scene.render.image_settings.file_format = 'PNG'; scene.render.filepath = str(HERE / 'previews/mall-event-booth.png'); scene.view_settings.look = 'AgX - Medium High Contrast'
    (HERE / 'sources').mkdir(exist_ok=True); (HERE / 'previews').mkdir(exist_ok=True); bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources/mall-event-booth.blend'), compress=True); bpy.ops.render.render(write_still=True)

if __name__ == '__main__': build()
