"""Read native scene first, then exact glTF; model units are illustrative only."""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector
S='RUBBER_ROLLER_SMOOTH_LOWER';R='RUBBER_ROLLER_RIBBED_UPPER';H='RUBBER_MOCK_SHEET_RIBBED_OUTFEED';T='OUTFEED_WORKTRAY_SLATS';I='INLET_WORKTRAY_SLATS'; C='RUBBER_FIXED_HAND_CRANK'
N=(S,R,H,T,I,C)
def obj(n):return bpy.data.objects[n]
def verts(n):
 o=obj(n)
 return [o.matrix_world @ v.co for v in o.data.vertices]
def ray(n,x,y,up):
 dep=bpy.context.evaluated_depsgraph_get()
 ob=obj(n).evaluated_get(dep); inv=ob.matrix_world.inverted()
 src=inv@Vector((x,y,-.4 if up else 2))
 d=inv.to_3x3()@Vector((0,0,1 if up else -1))
 ok,p,normal,_=ob.ray_cast(src,d.normalized())
 return (ob.matrix_world@p).z if ok else None
def tray(which):
 ds=[]
 for x in (-.21,-.10,0,.10,.21):
  for k in range(129):
   if which==T:y=-.149-k*.202/128
   else:y=.151+k*.240/128
   top=ray(which,x,y,False)
   if top is None:continue
   bottom=ray(H,x,y,True)
   assert bottom is not None
   ds.append(bottom-top)
 return min(ds),len(ds)
def sample():
 bpy.context.view_layer.update()
 vals={}
 for n,K in ((S,.691),(R,.865)):
  V=verts(n)
  span=max(v.x for v in V)-min(v.x for v in V)
  r=[math.hypot(v.y,v.z-K) for v in V]
  assert abs(span-.588)<2e-6
  expected=.083 if n==S else .0782
  assert abs(min(r)-expected)<2e-6 and abs(max(r)-.083)<2e-6
  vals[n]={'spanM':span,'rMinM':min(r),'rMaxM':max(r)}
 # Shared staged sheet appears behind the nip and extends into the outfeed with actual rib contour.
 for x in (-.14,0,.14):
  assert all(ray(H,x,y,False) is not None for y in (-.53,-.3,0,.356))
 curves=[]
 for k in range(150):
  y=-.14-k*.404/149
  top=ray(H,0,y,False); assert top is not None
  curves.append(top-(.7794-.171*((-y-.091)/.491)**1.20+.0041))
 assert max(curves)-min(curves)>.004
 clear,probes=tray(T)
 assert clear>.0007 and probes>400,(clear,probes)
 inclose,nin=tray(I)
 # The rear feed table closely supports this staged mock sheet without penetration.
 assert 0<=inclose<.0021 and nin>400,(inclose,nin)
 V=verts(C);val=max(v.z for v in V)-min(v.z for v in V);assert .13<val<.17
 return {'rollerProfiles':vals,'sheetResidualPeakToPeakM':max(curves)-min(curves),
          'minOutfeedSlatClearanceM':clear,'outfeedProbes':probes,'minInletSlatClearanceM':inclose,'inletProbes':nin,'crankSpanVertM':val}
before=sample()
for n in (S,R,H):
 bm=bmesh.new();bm.from_mesh(obj(n).data)
 assert all(e.is_manifold and e.is_contiguous for e in bm.edges),n
 assert bm.calc_volume(signed=True)>0 and all(f.calc_area()>1e-10 for f in bm.faces),n
 bm.free()
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(Path(sys.argv[sys.argv.index('--')+1]).resolve()),merge_vertices=True)
assert all(o.type=='MESH' and not o.animation_data for o in bpy.context.scene.objects)
assert not any(o.name.startswith('Studio') for o in bpy.context.scene.objects)
after=sample()
print('RUBBER_GEOMETRY_EVIDENCE='+json.dumps({'native':before,'reimport':after,'closedMockSheetMesh':True},sort_keys=True))
