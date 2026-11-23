"""Compare packed PBR images and mirror-to-surface distances on the real GLBs."""
import bpy,json,hashlib
import numpy as np
from mathutils.bvhtree import BVHTree
from pathlib import Path
p=Path(__file__).resolve().parent
def inspect(path,original):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    m=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    mesh=m.data;mesh.calc_loop_triangles()
    world=np.array([m.matrix_world@v.co for v in mesh.vertices])
    tri=[tuple(t.vertices) for t in mesh.loop_triangles]
    tree=BVHTree.FromPolygons(world.tolist(),tri,all_triangles=True)
    pts=np.unique(np.round(world,7),axis=0)
    mm=np.array([tree.find_nearest((-x,y,z))[3]*1000 for x,y,z in pts])
    mirrors={}
    for name,mask in [('whole',np.ones(len(pts),dtype=bool)),('hands',abs(pts[:,0])>.2862)]:
        v=mm[mask];mirrors[name]={'vertices':len(v),'mean_mm':float(v.mean()),'p95_mm':float(np.percentile(v,95)),'max_mm':float(v.max())}
    textures={};dims={}
    for im in bpy.data.images:
        if im.name in ['Render Result','Viewer Node']:continue
        n=im.name.lower();role='base_color' if 'basecolor' in n else 'normal' if 'normal' in n else 'roughness_metallic'
        dims[role]=list(im.size)
        if original:im.scale(1024,1024)
        a=np.empty(1024*1024*4,np.float32);im.pixels.foreach_get(a)
        textures[role]=a.reshape(1024,1024,4)[:,:,:3].copy()
    return textures,mirrors,dims
a,src,orig=inspect(p.parent/'studio_rigged.glb',True)
b,body,target=inspect(p/'body_female_v1.glb',False)
mask=np.ones((1024,1024),bool);mask[32:32+24,304:304+24]=False
textures={}
for role,im in a.items():
    delta=abs(b[role]-im)[mask];textures[role]={'source_px':orig[role],'body_px':target[role],'outside_hand_tile_pixels':int(mask.sum()),'mean_abs_rgb':delta.mean(0).tolist(),'max_abs_rgb':delta.max(0).tolist()}
result={'body_sha256':hashlib.sha256((p/'body_female_v1.glb').read_bytes()).hexdigest(),'channels':'Blender decoded RGB float values in the active colour space; compare with a Blender 1024-pixel resize. 24 x 24 unused tile excluded.','textures':textures,'mirror_definition':'Unique rest-space points reflected across world X=0, closest opposite point on any triangle. Sampling weights each unique point equally.','source_mirror':src,'body_mirror':body}
(p/'appearance_check.json').write_text(json.dumps(result,indent=2)+'\n')
print(result)
