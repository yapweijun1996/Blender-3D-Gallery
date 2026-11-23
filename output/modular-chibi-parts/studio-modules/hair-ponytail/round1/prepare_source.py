"""One full Studio import. Cache the decimated hair and head in source coordinates."""
import bpy, numpy as np, bmesh, sys, json
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
PARTS=HERE.parents[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
bpy.context.preferences.filepaths.file_preview_type='NONE'
bpy.ops.import_scene.gltf(filepath=str(HERE.parent/'source_studio_segmented.glb'))
survivors=[]
summary={}
for o in list(bpy.context.scene.objects):
    if o.type!='MESH':continue
    mat=o.active_material
    tex=next(n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and 'basecolor' in n.image.name)
    pix=np.empty(tex.size[0]*tex.size[1]*4,'f')
    tex.pixels.foreach_get(pix)
    sample=pix.reshape(-1,4)[::101,:3]
    sample=sample[sample.max(1)>.03]
    p=np.array([list(o.matrix_world@Vector(v)) for v in o.bound_box])
    summary[o.name]=dict(bounds=[p.min(0).tolist(),p.max(0).tolist()],color=np.median(sample,axis=0).tolist(),tri=len(o.data.polygons))
    if o.name not in ('tripo_part_0','tripo_part_2'):
        bpy.data.objects.remove(o,do_unlink=True)
        continue
    survivors.append(o)
    world=o.matrix_world.copy()
    o.parent=None
    from mathutils import Matrix
    o.data.transform(world)
    o.matrix_world=Matrix.Identity(4)
    bpy.context.view_layer.objects.active=o
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000002)
    bm.to_mesh(o.data);bm.free()
    dec=o.modifiers.new('Studio working resolution','DECIMATE')
    dec.ratio=min(1, (42000 if o.name=='tripo_part_0' else 10000)/len(o.data.polygons))
    bpy.ops.object.modifier_apply(modifier=dec.name)
    for n in list(mat.node_tree.nodes):
        if n.type=='TEX_IMAGE' and n.image!=tex:mat.node_tree.nodes.remove(n)
    tex.pack()
for o in list(bpy.context.scene.objects):
    if o not in survivors:bpy.data.objects.remove(o,do_unlink=True)
bpy.data.orphans_purge(do_recursive=True)
(HERE/'source_parts.json').write_text(json.dumps(summary,indent=2))
print(summary,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'source_working.blend'),compress=True)

