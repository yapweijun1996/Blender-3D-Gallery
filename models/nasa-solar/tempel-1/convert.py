import bpy, mathutils
from pathlib import Path
p=Path(__file__).resolve().parent
if (p/'model.glb').exists(): raise FileExistsError('Refusing to overwrite model.glb; use an isolated copy')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=str(p/'original.obj'))
objs=[o for o in bpy.context.scene.objects if o.type=='MESH']
assert len(objs)==1
obj=objs[0]
for face in obj.data.polygons: face.use_smooth=True
pts=[obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
mins=[min(v[i] for v in pts) for i in range(3)];maxs=[max(v[i] for v in pts) for i in range(3)];scale=2/max(maxs[i]-mins[i] for i in range(3));obj.scale=(scale,)*3;obj.location=[-(maxs[i]+mins[i])*scale/2 for i in range(3)]
mat=bpy.data.materials.new('Illustrative neutral surface');mat.diffuse_color=(0.22,0.21,0.20,1);mat.use_nodes=True;bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(0.22,0.21,0.20,1);bsdf.inputs['Roughness'].default_value=1;obj.data.materials.append(mat)
bpy.ops.export_scene.gltf(filepath=str(p/'model.glb'),export_format='GLB',export_cameras=False,export_lights=False)
