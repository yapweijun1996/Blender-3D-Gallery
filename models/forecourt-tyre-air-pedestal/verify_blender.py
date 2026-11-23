"""Use with the native .blend and exact shipped GLB; no external runtime."""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector
ID='forecourt-tyre-air-pedestal'
HOSE='AIR_CONTINUOUS_COIL_AND_LEAD'
CHUCK='AIR_CHUCK_SMALL_STOWED_HANDLE'
CRADLE='NOZZLE_CRADLE_FORK'
NAMES=(HOSE,CHUCK,CRADLE,'Upper cabinet inlet sleeve','Chuck cable flex strain relief',
       'Open reel lower floor','Recess deep back wall','Smoked acrylic instrument face',
       'Fixed ivory pointer in decorative dial','FORCOURT_BILINGUAL_GEOMETRY')
def verts(n):
 o=bpy.data.objects[n]
 return [o.matrix_world@v.co for v in o.data.vertices]
def bounds(v):return [[min(p[i] for p in v),max(p[i] for p in v)] for i in range(3)]
def sample():
 bpy.context.view_layer.update()
 b={k:bounds(verts(k)) for k in NAMES}
 assert b[HOSE][0][0]<-.235 and b[HOSE][0][1]>.356
 assert b[HOSE][2][1]>1.02 and b[HOSE][2][0]<.45
 assert b[HOSE][1][0]<-.254 and b[HOSE][1][1]>-.060
 assert b[HOSE][1][1]<b[NAMES[6]][1][0]-.010,'the hose is in the open bay in front of its back wall'
 assert b[CHUCK][2][0]<1.0<b[CHUCK][2][1]
 for axis in range(3):
  assert max(b[CRADLE][axis][0],b[CHUCK][axis][0]) < min(b[CRADLE][axis][1],b[CHUCK][axis][1]),'The cradle and chuck bounds must meet'
 # The indicator is immediately in front of, not buried under, the dark instrument face.
 assert b[NAMES[8]][1][0]<b[NAMES[7]][1][1]
 assert b[NAMES[7]][2][0]<b[NAMES[8]][2][0]<b[NAMES[8]][2][1]<b[NAMES[7]][2][1]
 return b
native=sample()
H=bpy.data.objects[HOSE];rings=int(H['curve_rings']);sides=int(H['radial_vertices'])
V=verts(HOSE);assert len(V)==rings*sides
mid=[sum(V[k:k+sides],Vector())/sides for k in range(0,len(V),sides)]
radii=[(p-mid[i//sides]).length for i,p in enumerate(V)]
assert max(abs(x-.0122) for x in radii)<5e-6
for i,n in ((0,NAMES[3]),(-1,NAMES[4])):
 assert all(lo < mid[i][axis] < hi for axis,(lo,hi) in enumerate(native[n])),(i,mid[i],native[n])
phase=[math.atan2(p.z-.681,p.x+.038) for p in mid[12:105]]
wind=sum((b-a+math.pi)%math.tau-math.pi for a,b in zip(phase,phase[1:]))/math.tau
assert abs(wind-1.75)<.015 and float(H['wound_turns'])==1.75
pitch=min((mid[i]-mid[j]).length for i in range(12,105) for j in range(i+43,min(i+61,105)))
assert pitch>.0244,'Neighbouring turns must not penetrate'
bm=bmesh.new();bm.from_mesh(H.data)
assert all(e.is_manifold and e.is_contiguous for e in bm.edges)
assert all(f.calc_area()>1e-10 for f in bm.faces) and bm.calc_volume(signed=True)>0
todo=[next(iter(bm.verts))];seen=set()
while todo:
 v=todo.pop()
 if v in seen:continue
 seen.add(v)
 for e in v.link_edges:todo.append(e.other_vert(v))
assert len(seen)==len(bm.verts),'The hose must be one connected mesh'
bm.free()
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(Path(sys.argv[sys.argv.index('--')+1]).resolve()),merge_vertices=True)
assert all(o.type=='MESH' and not o.animation_data for o in bpy.context.scene.objects)
assert not any(n.startswith('Studio') for n in bpy.data.objects.keys())
export=sample()
delta=max(abs(x-y) for n in NAMES for a,b in zip(native[n],export[n]) for x,y in zip(a,b))
assert delta<2e-5,delta
print('AIR_PEDESTAL_EVIDENCE='+json.dumps({'hoseConnectedAndManifold':True,
 'centerlineRings':rings,'radialVertices':sides,'hoseTurns':wind,
 'minAdjacentTurnCenterlineSpacingM':pitch,
 'hoseRubberRadiusM':sum(radii)/len(radii),'endpointsInsidePhysicalCollars':True,'dockedCradleAndChuck':True,
 'maximumNativeExportBoundsDeltaM':delta,'native':native},sort_keys=True))
