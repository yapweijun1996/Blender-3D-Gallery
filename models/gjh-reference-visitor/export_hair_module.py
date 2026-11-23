"""Export the modular hair at rest using the same modifier order as the character."""
import bpy
from pathlib import Path
from mathutils import Matrix
sc=bpy.data.scenes['GJH Reference Visitor'];bpy.context.window.scene=sc
model=next(c for c in sc.collection.children if c.name.startswith('GJH Visitor Model'))
hair=next(o for o in model.objects if o.type=='MESH' and o.get('partSlot')=='Hair')
out=Path('/Users/yapweijun/Documents/GitHub/Blender-3D-Gallery/models/gjh-reference-visitor/exports/gjh-visitor-hair.glb')
bpy.context.view_layer.update();temp=bpy.data.collections.new('Visitor Hair Export Temporary');sc.collection.children.link(temp)
obj=hair.copy();obj.data=hair.data.copy();temp.objects.link(obj)
try:
    # Match export_rigged.py: bake world scale BEFORE applying Decimate.
    obj.parent=None;obj.matrix_world=Matrix.Identity(4);obj.data.transform(hair.matrix_world,shape_keys=True)
    for mod in list(obj.modifiers):
        if mod.type=='ARMATURE':obj.modifiers.remove(mod)
    obj.hide_viewport=False;obj.hide_render=False;obj.hide_set(False)
    bpy.context.view_layer.update()
    bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',collection=temp.name,
        export_yup=True,export_apply=True,export_vertex_color='MATERIAL',export_extras=True,export_animations=False)
finally:
    data=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
    if data.users==0:bpy.data.meshes.remove(data)
    bpy.data.collections.remove(temp)
result={'export':str(out),'slot':'Hair','node':'one mesh; name may have a Blender suffix','origin':'character sole midpoint','coordinates':'glTF +Y up, +Z forward','rest_pose_baked':True}
