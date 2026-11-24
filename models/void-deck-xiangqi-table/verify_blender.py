"""Verify actual 9x10 stone-board/stools/piece coordinates before and after exact GLB round trip."""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector
T=.800; s=.092
X=[(i-4)*s for i in range(9)]
Y=[(i-4.5)*s for i in range(10)]
GRID='XIANGQI_INTEGRAL_GRID_RIVER_PALACES'; PANEL='BOARD_FIXED_INTEGRAL_INSET'
P=['XIANGQI_RED_GENERAL','XIANGQI_RED_CHARIOT','XIANGQI_RED_HORSE','XIANGQI_RED_CANNON','XIANGQI_RED_SOLDIER',
   'XIANGQI_DARK_GENERAL','XIANGQI_DARK_CHARIOT','XIANGQI_DARK_HORSE','XIANGQI_DARK_CANNON','XIANGQI_DARK_SOLDIER']
loc=[(4,0),(8,2),(2,2),(7,4),(4,4),(4,9),(0,7),(6,7),(1,5),(6,6)]
seats=['STOOL_'+n+'_SOLID_CAST_SEAT' for n in ('FRONT','BACK','LEFT','RIGHT')]
def ob(n):return bpy.data.objects[n]
def points(n):
 o=ob(n)
 return [o.matrix_world@v.co for v in o.data.vertices]
def bounds(n):
 v=points(n)
 return [[min(x[i] for x in v),max(x[i] for x in v)] for i in range(3)]
def ray(n,x,y):
 dep=bpy.context.evaluated_depsgraph_get()
 o=ob(n).evaluated_get(dep);inv=o.matrix_world.inverted()
 h,hit,norm,poly=o.ray_cast(inv@Vector((x,y,2)), (inv.to_3x3()@Vector((0,0,-1))).normalized())
 if not h:return None
 material=o.data.materials[o.data.polygons[poly].material_index].name
 return (float((o.matrix_world@hit).z),material.removesuffix(".001"))
def sample():
 bpy.context.view_layer.update()
 grid='Dark muted khaki inset grid'; river='Soft jade river hint'
 hchecks=[]
 # Every horizontal stroke, sampling its inside span away from circular tokens.
 for j,y in enumerate(Y):
  t=ray(GRID,.132,y); assert t is not None and t[1]==grid,(j,t)
  hchecks.append(t[0])
 # Check all 81 file segments independently and each of the seven unpainted inner river breaks.
 vf=0;br=0
 for i,x in enumerate(X):
  for j in range(9):
   v=ray(GRID,x,(Y[j]+Y[j+1])/2)
   if j==4 and i not in (0,8):
    assert v is not None and v[1]==river,(i,j,v)
    br+=1
   else:
    assert v is not None and v[1]==grid,(i,j,v)
    vf+=1
 assert (vf,br)==(74,7)
 # Inspect both true diagonals per palace on off-axis gold-free samples.
 diag=0
 for bottom,top in ((0,2),(7,9)):
  for sx in (-1,1):
   for t in (.29,.71):
    x=sx*(t*2-1)*s
    y=Y[bottom]*(1-t)+Y[top]*t
    vv=ray(GRID,x,y); assert vv is not None and vv[1]==grid,(bottom,x,y,vv)
    diag+=1
 seat_h=[]
 for n in seats:
  b=bounds(n)
  assert abs(b[2][0]-.088)<3e-6 and abs(b[2][1]-.457)<3e-6
  assert .327<b[0][1]-b[0][0]<.329
  seat_h.append(b[2][1])
 assert abs(bounds('TABLE_ROUNDED_CAST_TERRAZZO_TOP')[2][1]-T)<3e-6
 assert len(set(loc))==10
 pieces=[]
 for n,(i,j) in zip(P,loc):
  bb=bounds(n); x=(bb[0][0]+bb[0][1])/2;y=(bb[1][0]+bb[1][1])/2
  assert abs(x-X[i])<2e-6 and abs(y-Y[j])<2e-6,(n,(x,y))
  ink=ray(GRID,x,y) or ray(PANEL,x,y)
  assert ink is not None and 0<=bb[2][0]-ink[0]<.0015
  assert bounds(n+'_ENGRAVING')[2][1]>bb[2][1]
  pieces.append((n,i,j,x,y))
 # Opposing generals remain in the two palace endpoints, separated by the staged central soldier.
 assert loc[0]==(4,0) and loc[5]==(4,9) and loc[4]==(4,4)
 return dict(horizontalRanks=len(hchecks),verticalStrokeSegments=vf,openInnerRiverFiles=br,palaceOffAxisProbes=diag,
   boardPlaneZ=ray(PANEL,0,0)[0],fourStoolTops=seat_h,pieceCenters=pieces)
before=sample()
for n in seats+P+['TABLE_SOLID_CAST_TAPER_AND_FOOT']:
 b=bmesh.new();b.from_mesh(ob(n).data)
 assert all(e.is_manifold and e.is_contiguous for e in b.edges),n
 assert b.calc_volume(signed=True)>0 and all(f.calc_area()>1e-10 for f in b.faces),n
 b.free()
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(Path(sys.argv[sys.argv.index('--')+1]).resolve()),merge_vertices=True)
assert all(o.type=='MESH' and not o.animation_data for o in bpy.context.scene.objects)
assert not any(n.startswith('Studio') for n in bpy.data.objects.keys())
after=sample()
assert before==after,(before,after)
print('XIANGQI_PHYSICAL_EVIDENCE='+json.dumps({**after,'closedCastStools':4,'closedCastPedestal':True,'closedPhysicalPieces':10,'roundTripExactlyEqual':True},sort_keys=True))
