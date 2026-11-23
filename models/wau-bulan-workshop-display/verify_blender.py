"""Use: blender -b wau-bulan-workshop-display.blend --python-exit-code 31 --python verify_blender.py -- exports/wau-bulan-workshop-display.glb"""
import bpy,bmesh,json,sys
from mathutils import Vector
from pathlib import Path
ID='wau-bulan-workshop-display'
S='WAU_BOWED_PAPER_SAIL'; T='WAU_CRESCENT_PAPER_TAIL'
SP='WAU_LONGITUDINAL_BAMBOO_SPINE'; CS='WAU_CONTINUOUS_BOWED_CROSS_SPAR'; TS='WAU_CRESCENT_BOW_SPAR'
NAMES=(S,T,SP,CS,TS,'WAU_BRIDLE_UPPER','WAU_BRIDLE_LOWER','WORKSHOP_BAMBOO_STAND','WORKSHOP_COTTON_REEL')
def verts(n):
 o=bpy.data.objects[n]
 return [o.matrix_world @ v.co for v in o.data.vertices]
def bounds(p):
 return [[min(v[i] for v in p),max(v[i] for v in p)] for i in range(3)]
def cast(n,x,z,facing):
 o=bpy.data.objects[n]
 hit,p,normal,_=o.ray_cast(Vector((x,-facing*2,z)), Vector((0,facing,0)))
 if not hit:return None
 assert facing*normal.y<-.50,(n,x,z,facing,tuple(normal))
 return p.y
def sample():
 bpy.context.view_layer.update()
 D={n:bounds(verts(n)) for n in NAMES}
 checks=[(S,0,1.515),(S,0,1.770),(S,.48,1.600),(S,-.48,1.600),
         (T,0,.979),(T,.28,1.08),(T,-.28,1.08)]
 rays=[]
 for n,x,z in checks:
  f=cast(n,x,z,1);b=cast(n,x,z,-1)
  assert f is not None and b is not None and abs(b-f-.003)<2e-5,(n,x,z,f,b)
  rays.append([f,b])
 assert cast(S,0,1.15,1) is None and cast(T,0,1.15,1) is None,'Independent crescent gap must be open'
 assert 1.749<D[S][0][1]-D[S][0][0]<1.751
 assert .821<D[T][0][1]-D[T][0][0]<.834,D[T]
 assert abs(rays[2][0]-rays[3][0])<.00015 and abs(rays[5][0]-rays[6][0])<.00015,rays
 assert rays[2][0]-rays[0][0]>.012,'Paper must be materially bowed, not a flat card'
 assert .075<D[CS][1][1]-D[CS][1][0]<.22
 assert D[SP][2][0]<.899 and D[SP][2][1]>1.886
 assert D[TS][0][1]>.405 and D[TS][0][0]<-.405
 bridge=min((u-v).length for u in verts(NAMES[5]) for v in verts(NAMES[6]))
 assert bridge<.007,'Upper and lower bridle need one common knot'
 dmin=min((u-v).length for u in verts(SP) for v in verts(CS))
 assert dmin<.022,'Cross spar intersects or meets actual spine'
 assert abs(D[NAMES[7]][2][0])<.002 and D[NAMES[7]][2][1]>.980
 return {'bounds':D,'faceBackRays':rays,'paperPanelBowBetweenSamplesM':rays[2][0]-rays[0][0],
    'wingCrossSparBowM':D[CS][1][1]-D[CS][1][0],'bridleCommonKnotGapM':bridge,'spineCrossSparClosestVertexM':dmin}
init=sample()
for n in (S,T):
 bm=bmesh.new();bm.from_mesh(bpy.data.objects[n].data)
 assert all(e.is_manifold and e.is_contiguous for e in bm.edges),n+' should be an oriented manifold paper laminate'
 assert all(f.calc_area()>1e-10 for f in bm.faces),n+' has degenerate faces'
 assert bm.calc_volume(signed=True)>0,n+' outward normals'
 init.setdefault('panelClosedVolumesM3',{})[n]=bm.calc_volume(signed=True)
 bm.free()
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(Path(sys.argv[sys.argv.index('--')+1]).resolve()),merge_vertices=True)
assert all(o.type=='MESH' and not o.animation_data for o in bpy.context.scene.objects)
assert not any(n.startswith('Studio') for n in bpy.data.objects.keys())
post=sample()
def leaves(v):
 if isinstance(v,dict):return [y for x in v.values() for y in leaves(x)]
 if isinstance(v,list):return [y for x in v for y in leaves(x)]
 return [v]
delta=max(abs(x-y) for x,y in zip(leaves(post),leaves({k:init[k] for k in post})))
assert delta<2e-5,delta
print('WAU_PHYSICAL_EVIDENCE='+json.dumps({'original':init,'reimport':post,'maxEvidenceDifferenceM':delta},sort_keys=True))
