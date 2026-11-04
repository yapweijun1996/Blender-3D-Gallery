"""Render asset-root previews from the saved scene, without changing the .blend file."""
import bpy, math
from pathlib import Path
from mathutils import Vector

scene = bpy.context.scene
out = Path(bpy.data.filepath).parent / 'thumbnails'
out.mkdir(exist_ok=True)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.show_shadows = True
scene.display.shading.background_type = 'WORLD'
scene.world.color = (0.12, 0.15, 0.15)
scene.render.resolution_x = scene.render.resolution_y = 400
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
for mat in bpy.data.materials:
    if mat.use_nodes and mat.node_tree.nodes.get('Principled BSDF'):
        mat.diffuse_color = mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value
roots = sorted((o for o in scene.objects if o.name.startswith('ASSET_')), key=lambda o:o.name)
for root in roots:
    objects = [o for o in root.children_recursive if o.type == 'MESH']
    for ob in scene.objects:
        if ob.type == 'MESH': ob.hide_render = ob not in objects
    coords = [ob.matrix_world @ Vector(corner) for ob in objects for corner in ob.bound_box]
    minimum = Vector([min(v[i] for v in coords) for i in range(3)])
    maximum = Vector([max(v[i] for v in coords) for i in range(3)])
    center = (minimum + maximum) * 0.5
    size = maximum - minimum
    camera = scene.camera
    direction = Vector((3.3, -4.5, 4.8)).normalized()
    camera.location = center + direction * max(size.length, .01) * 3
    camera.rotation_euler = (center-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = max(size.length, .01) * 1.18
    name = root.name.removeprefix('ASSET_').lower()
    scene.render.filepath = str(out / (name + '.png'))
    bpy.ops.render.render(write_still=True)
    print('THUMBNAIL',name,flush=True)
