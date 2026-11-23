"""Export an animation-ready copy with skinned meshes at the scene root.

Run in the connected Blender after rig.py. The editable model is untouched;
world transforms are baked into temporary copies, including the armature's rest
bones. The current rig uses rotation-only bone animation and uniform scale.
"""
import bpy
from mathutils import Matrix
from pathlib import Path

scene = bpy.data.scenes['GJH Reference Visitor']
bpy.context.window.scene = scene
source = next(c for c in scene.collection.children if c.name.startswith('GJH Visitor Model'))
rigs = [o for o in source.objects if o.type == 'ARMATURE']
if len(rigs) != 1:
    raise RuntimeError('Expected one armature in the model collection')
rig = rigs[0]
# Baking rotations and rest bones is safe for the rig's uniform positive scale;
# non-uniform or negative scale would change the interpretation of rotations.
scale = rig.matrix_world.to_scale()
if min(scale) <= 0 or max(scale) - min(scale) > 1e-5 or rig.matrix_world.determinant() <= 0:
    raise RuntimeError('Rig must have positive uniform world scale for rotation-only action export')
bpy.context.view_layer.update()
out = Path('/Users/yapweijun/Documents/GitHub/Blender-3D-Gallery/models/gjh-reference-visitor/exports/gjh-reference-visitor-rigged.glb')
temp = bpy.data.collections.new('GJH Export Temporary')
scene.collection.children.link(temp)
copies = []
try:
    new_rig = rig.copy()
    new_rig.data = rig.data.copy()
    copies.append(new_rig)
    temp.objects.link(new_rig)
    new_rig.parent = None
    new_rig.matrix_world = Matrix.Identity(4)
    new_rig.data.transform(rig.matrix_world)
    for obj in list(source.objects):
        if obj.type != 'MESH':
            continue
        new = obj.copy()
        new.data = obj.data.copy()
        copies.append(new)
        temp.objects.link(new)
        new.parent = None
        new.matrix_world = Matrix.Identity(4)
        new.data.transform(obj.matrix_world, shape_keys=True)
        for mod in new.modifiers:
            if mod.type == 'ARMATURE' and mod.object == rig:
                mod.object = new_rig
    bpy.context.view_layer.update()
    bpy.ops.export_scene.gltf(filepath=str(out), export_format='GLB',
        collection=temp.name, export_yup=True, export_apply=True,
        export_vertex_color='MATERIAL', export_extras=True, export_animations=True,
        export_animation_mode='NLA_TRACKS')
finally:
    # Remove only the copies made above, including their private datablocks.
    for obj in copies:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data and data.users == 0:
            if isinstance(data, bpy.types.Mesh): bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Armature): bpy.data.armatures.remove(data)
    bpy.data.collections.remove(temp)
result = {'export': str(out), 'source_untouched': True}
