"""Export every explicitly tagged character slot as a rig-compatible GLB.

Each module contains its own copy of the same rest skeleton and its own
meshes. Consumers bind the module skin to the matching named character bones;
a static parent-to-one-bone shortcut is insufficient for multi-bone garments.
"""
import bpy, re, json
from pathlib import Path
from mathutils import Matrix

sc=bpy.data.scenes['GJH Reference Visitor'];bpy.context.window.scene=sc
model=next(c for c in sc.collection.children if c.name.startswith('GJH Visitor Model'))
optional=bpy.data.collections.get('GJH Optional Wardrobe')
rig=next(o for o in model.objects if o.type=='ARMATURE')
bpy.context.view_layer.update()
if max(rig.matrix_world.to_scale())-min(rig.matrix_world.to_scale())>1e-5 or rig.matrix_world.determinant()<=0:
    raise RuntimeError('Uniform positive rig scale required')
objects=[o for c in (model,optional) if c for o in c.objects if o.type=='MESH' and o.get('partSlot')]
slots={}
for o in objects:slots.setdefault(o['partSlot'],[]).append(o)
if not slots:raise RuntimeError('No partSlot objects')
out=Path('/Users/yapweijun/Documents/GitHub/Blender-3D-Gallery/models/gjh-reference-visitor/exports/modules');out.mkdir(parents=True,exist_ok=True)
manifest={'coordinates':'glTF +Y up, +Z forward; character sole-midpoint origin','skeleton':'Visitor Humanoid','modules':{}}
for slot,items in sorted(slots.items()):
    slug=re.sub(r'[^A-Za-z0-9]+','-',slot).strip('-').lower();path=out/(slug+'.glb')
    temp=bpy.data.collections.new('Module export '+slot);sc.collection.children.link(temp);copies=[]
    try:
        r=rig.copy();r.data=rig.data.copy();temp.objects.link(r);copies.append(r)
        r.parent=None;r.matrix_world=Matrix.Identity(4);r.data.transform(rig.matrix_world)
        r.hide_viewport=False;r.hide_render=False;r.hide_set(False)
        if r.animation_data:r.animation_data_clear()
        for o in items:
            n=o.copy();n.data=o.data.copy();temp.objects.link(n);copies.append(n)
            n.parent=None;n.matrix_world=Matrix.Identity(4);n.data.transform(o.matrix_world,shape_keys=True)
            n.hide_viewport=False;n.hide_render=False;n.hide_set(False)
            for m in n.modifiers:
                if m.type=='ARMATURE' and m.object==rig:m.object=r
        bpy.context.view_layer.update()
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',collection=temp.name,export_yup=True,
                                  export_apply=True,export_vertex_color='MATERIAL',export_extras=True,export_animations=False)
        manifest['modules'][slot]={'file':path.name,'objects':[o.name for o in items],
           'bones':sorted({g.name for o in items for g in o.vertex_groups if g.name in rig.data.bones}),
           'optional':all(bool(o.get('optional')) for o in items)}
    finally:
        for n in copies:
            data=n.data;bpy.data.objects.remove(n,do_unlink=True)
            if data and data.users==0:
                if isinstance(data,bpy.types.Mesh):bpy.data.meshes.remove(data)
                elif isinstance(data,bpy.types.Armature):bpy.data.armatures.remove(data)
        bpy.data.collections.remove(temp)
manifest['variants']={'Jeans':{'hide':['Shorts','Leg.L','Leg.R','Sock.L','Sock.R']},'Hat':{'hide':[]}}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
result={'slots':len(slots),'directory':str(out),'modules':sorted(slots)}
