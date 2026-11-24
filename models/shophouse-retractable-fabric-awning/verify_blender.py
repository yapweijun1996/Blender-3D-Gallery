"""Validate authored endpoints/rigidity and official GLB round-trip."""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector
B='AWNING_FRONT_BAR'; F='AWNING_FABRIC'; R='AWNING_ROLLER'
pairs=[('AWNING_L_PROXIMAL','AWNING_L_DISTAL'),('AWNING_R_PROXIMAL','AWNING_R_DISTAL')]
N=(B,F,R,*[x for pair in pairs for x in pair])
q=math.radians(8.5); co,si=math.cos(q),math.sin(q)
L=.437;x=.821;H=1.115;Y=-.254
W=1.825
D0=.777;D1=.102
def pos(o):return o.matrix_world.translation.copy()
def dot(o,v):return o.matrix_world@Vector(v)
def obj(n):return bpy.data.objects[n]
def P(x0,d=0,h=0):return Vector((x0,Y-d*co-h*si,H-d*si+h*co))
def width(o):
 v=[dot(o,u.co) for u in o.data.vertices]
 return max(u.x for u in v)-min(u.x for u in v)
def checks():
 states=[]; last=None;roll=0;max_link_error=0;old=10
 for f in range(73):
  bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
  b,cloth,roller=[obj(k) for k in N[:3]]
  d=(pos(b)-P(0,0,.020)).dot(Vector((0,-co,-si)))
  assert d<=old+1e-6,(d,old)
  old=d
  full_width=width(cloth)
  assert abs(full_width-W)<2e-5
  assert (pos(cloth)-P(0,0,.0445)).length<2e-5
  cloth_end=dot(cloth,(0,-D0,.006))
  assert (cloth_end-P(0,d,.0505)).length<2e-5,(f,d,list(cloth_end))
  assert all(abs(s-1)<2e-6 for p in pairs for n in p for s in obj(n).matrix_world.to_scale())
  assert (pos(roller)-P(0)).length<2e-6
  rot=roller.matrix_world.to_quaternion()
  if last is not None:roll+=2*math.acos(min(1,abs(last.dot(rot))))
  last=rot
  maxerr=0
  for side,(pname,dname) in zip((-1,1),pairs):
   p,distal=obj(pname),obj(dname);u=pos(p);v=dot(p,(0,L,0));v2=pos(distal)
   w=dot(distal,(0,L,0));w0=P(side*x,d,-.004)
   maxerr=max(maxerr,(u-P(side*x,0,-.004)).length,(v-v2).length,(w-w0).length)
   assert side*v.x<abs(u.x)-.15 and math.copysign(1,v.x)==side,(f,side,tuple(v))
   assert abs((v-u).length-L)<2e-6 and abs((w-v2).length-L)<2e-6
  max_link_error=max(max_link_error,maxerr)
  if f in (0,4,36,68,72):states.append({'frame':f,'projectionM':d,'clothWidthM':full_width,'clothScale':list(cloth.matrix_world.to_scale()),'maxLinkErrorM':maxerr})
 assert abs(states[0]['projectionM']-D0)<.00001 and abs(states[-1]['projectionM']-D1)<.00001
 assert abs(states[0]['projectionM']-states[1]['projectionM'])<.000002
 assert abs(states[3]['projectionM']-states[4]['projectionM'])<.000002
 assert abs(roll-(D0-D1)/.047)<.011,(roll,(D0-D1)/.047)
 assert max_link_error<.00004,max_link_error
 return {"states":states,"rollerRadians":roll,"maxLinkErrorM":max_link_error}
def flat(o):
 if isinstance(o,list):return [y for x in o for y in flat(x)]
 if isinstance(o,dict):return [y for x in o.values() for y in flat(x)]
 return [o]
cloth=obj(F)
b=bmesh.new();b.from_mesh(cloth.data)
assert all(e.is_manifold and e.is_contiguous for e in b.edges) and b.calc_volume(signed=True)>0
b.free()
initial=checks()
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(Path(sys.argv[sys.argv.index('--')+1]).resolve()))
assert not any(o.name.startswith('Studio') for o in bpy.context.scene.objects)
loaded=checks()
assert max(abs(x-y) for x,y in zip(flat(initial['states']),flat(loaded['states'])))<.000025
print('AWNING_PHYSICAL_EVIDENCE='+json.dumps({"native":initial,"glbRoundtrip":loaded,"span_fixed_m":W,"rigid_link_length_m":L},sort_keys=True))
