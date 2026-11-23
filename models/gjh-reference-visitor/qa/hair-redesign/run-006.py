"""Build a revised hairstyle from the original v4 cap and fringe.

Run inside the connected Blender on the editable visitor scene. The existing
hair object, its head rig and all other model parts retain their identity.
"""
import bpy
import importlib.util
import inspect
import math
from pathlib import Path

base = Path('/Users/yapweijun/Documents/GitHub/Blender-3D-Gallery')
spec = importlib.util.spec_from_file_location('visitor_v4_hair_helpers', base / 'models/chibi-visitor-v4/generate.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
scene = bpy.data.scenes['GJH Reference Visitor']
h.SCENE = scene.name
model = next(c for c in scene.collection.children if c.name.startswith('GJH Visitor Model'))
old = next(o for o in model.objects if o.type == 'MESH' and o.name.startswith('Hair'))
material = old.data.materials[0]

# Keep the original nape, upper-back and crown layers that enclose the
# head. Retain two middle locks to bridge the visible cap between rows.
original_rear_locks = h.hair_locks
def rear_locks():
    locks = original_rear_locks()
    return locks[:5] + [locks[7], locks[8]] + locks[11:]
h.hair_locks=rear_locks
# Keep the original cap, fringe, temples and rear lock depth. Soften baked
# crevice shading and shorten the outer spikes and tuft.
source=inspect.getsource(h.build_hair)
# Keep original lock thickness and nape fitting; soften the outer hair
# spikes without modifying the forehead locks or covering the eyes.
source=source.replace('(-102, -6, 1.30)', '(-102, -6, 1.15)')
source=source.replace('(-104, 9, 1.31)', '(-104, 9, 1.15)')
source=source.replace('(102, -4, 1.29)', '(102, -4, 1.15)')
source=source.replace('(104, 14, 1.30)', '(104, 14, 1.15)')
source=source.replace('(0.052, -0.004, 0.905), (0.046, -0.008, 0.940), (0.030, -0.011, 0.966), (0.008, -0.012, 0.984),\n          (-0.020, -0.012, 0.986)',
                      '(0.050, -0.004, 0.903), (0.043, -0.008, 0.917), (0.025, -0.011, 0.932), (-0.002, -0.012, 0.942),\n          (-0.035, -0.012, 0.941)')
source=source.replace('(0, 0, 1), 0.044, 0.024)', '(0, 0, 1), 0.064, 0.012)')
source=source.replace('bake_ao(part, HH, lin(HAIR_HEX))', 'bake_ao(part, HH, lin(HAIR_HEX), floor=0.58, power=1.0)')
if 'floor=0.58' not in source or '(-102, -6, 1.15)' not in source or '0.064, 0.012' not in source:
    raise RuntimeError('Original hair helper has changed; review the replacement patterns')
exec(compile(source,'visitor_reference_hair','exec'),h.__dict__)
part=h.build_hair({'hair':material})
new=part.build(model,old.parent)
old_mesh=old.data
old.data=new.data
bpy.data.objects.remove(new,do_unlink=True)
for group in list(old.vertex_groups):old.vertex_groups.remove(group)
head=old.vertex_groups.new(name='Head')
head.add(list(range(len(old.data.vertices))),1.0,'REPLACE')
for mod in list(old.modifiers):
    if mod.type=='DECIMATE':old.modifiers.remove(mod)
bpy.context.view_layer.update()
result={'hair':old.name,'vertices':len(old.data.vertices),'faces':len(old.data.polygons),
        'old_mesh_preserved':old_mesh.name,'head_weight':True}
