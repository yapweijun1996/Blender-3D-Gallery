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

# Use seven unequal locks flowing out from a whorl. Unlike the original v4
# three-row shingles, each follows a continuous curve from crown towards nape.
# Locks cover the lower cap without extending beyond its bottom silhouette.
def rear_locks():
    locks=[]
    for k in range(-3,4):
        az=180+k*27
        side=abs(k)
        end={0:-54,1:-51,2:-45,3:-30}[side]
        drift=k*2.8
        width={0:.151,1:.147,2:.139,3:.124}[side]
        ctrl=[(180+k*14,78,.97),(az-k*4,51,.99),(az,23,1.0),
              (az+drift*.5,-7,1.0),(az+drift,end,1.0)]
        locks.append((ctrl,width,.195))
    return locks
h.hair_locks=rear_locks
# Keep the original cap and fringe/temples. Change only rear lock depth and
# tufts; the original raised tips and dark baked AO exaggerate intersections.
source=inspect.getsource(h.build_hair)
source=source.replace('ctrl = ctrl[:-1] + [(ctrl[-1][0], ctrl[-1][1], 1.06)]',
                      'ctrl = ctrl[:-1] + [(ctrl[-1][0], ctrl[-1][1], 1.005)]')
source=source.replace('thick=0.030, groove=0.0, root=0.9, taper=3.0',
                      'thick=0.017, groove=0.0, root=0.82, taper=2.1')
source=source.replace('(0.052, -0.004, 0.905), (0.046, -0.008, 0.940), (0.030, -0.011, 0.966), (0.008, -0.012, 0.984),\n          (-0.020, -0.012, 0.986)',
                      '(0.050, -0.004, 0.903), (0.043, -0.008, 0.917), (0.025, -0.011, 0.932), (-0.002, -0.012, 0.942),\n          (-0.035, -0.012, 0.941)')
source=source.replace('(0, 0, 1), 0.044, 0.024)', '(0, 0, 1), 0.064, 0.012)')
source=source.replace('bake_ao(part, HH, lin(HAIR_HEX))', 'bake_ao(part, HH, lin(HAIR_HEX), floor=0.58, power=1.0)')
if 'floor=0.58' not in source or 'thick=0.017' not in source or '0.064, 0.012' not in source:
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
