import json,math,sys,importlib.util
from pathlib import Path
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('old',P.parents[1]/'reports/curved-riser-candidate/kinematics.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
d=json.loads((P/'reports/actual-glb-samples.json').read_text())
def hull(points):
 p=sorted(set(tuple(v) for v in points))
 def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
 lo=[];hi=[]
 for v in p:
  while len(lo)>1 and cross(lo[-2],lo[-1],v)<=1e-12:lo.pop()
  lo.append(v)
 for v in reversed(p):
  while len(hi)>1 and cross(hi[-2],hi[-1],v)<=1e-12:hi.pop()
  hi.append(v)
 return lo[:-1]+hi[:-1]
def transformed(poly,pose):
 x,y,z,a,*scale=pose;c=math.cos(a);s=math.sin(a)
 return [(y+c*u-s*v,z+s*u+c*v)for u,v in poly]
def components(mesh):
 vs=mesh['vertices'];idx=mesh['indices'];parents=list(range(len(vs)));same={}
 def root(i):
  while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
  return i
 def union(a,b):parents[root(a)]=root(b)
 for i,v in enumerate(vs):
  key=tuple(round(x,7)for x in v)
  if key in same:union(i,same[key])
  else:same[key]=i
 for i in range(0,len(idx),3):union(idx[i],idx[i+1]);union(idx[i],idx[i+2])
 groups={}
 for i,v in enumerate(vs):groups.setdefault(root(i),[]).append(v)
 return [{'poly':hull([(v[1],v[2])for v in group]),'x':(min(v[0]for v in group),max(v[0]for v in group))}for group in groups.values()]

polys=[hull([(v[1],v[2])for v in m['vertices']])for m in d['meshes']if m['name'].startswith('STEP_BODY')];center=-d['samples'][0][0][1];end=2*center
# Clip real exported full-profile hull to deck-covered half-plane, conservatively includes tread groove voids.
def clip(poly,bound,less):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ina=a[0]<=bound if less else a[0]>=bound;inb=b[0]<=bound if less else b[0]>=bound
  if ina:out.append(a)
  if ina!=inb:
   t=(bound-a[0])/(b[0]-a[0]);out.append((bound,a[1]+t*(b[1]-a[1])))
 return out
specs=[('lower',v-center,0)for v in [-.36,-.4,-.45,-.5,-.55,-.6]]+[('upper',end+v-center,3)for v in [0,.05,.1,.15,.2,.25,.3,.35]];rows=[]
for label,bound,floor in specs:
 maxz=-1e9;worst=None
 for f,poses in enumerate(d['samples']):
  for i,(poly,pose)in enumerate(zip(polys,poses)):
   q=clip(transformed(poly,pose),bound,label=='lower')
   if q and max(v[1]for v in q)-floor>maxz:maxz=max(v[1]for v in q)-floor;worst=[f,i]
 rows.append({'landing':label,'world_y_bound':bound,'bound_relative_end_m':bound+center if label=='lower'else bound+center-end,'max_step_top_relative_floor_m':maxz,'worst_frame_step':worst})
(P/'reports/flush-deck-feasibility.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
