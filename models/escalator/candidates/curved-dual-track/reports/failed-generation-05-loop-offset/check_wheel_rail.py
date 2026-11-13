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

tracks=json.loads((P/'reports/track-source-geometry.json').read_text());rails={}
for name,t in tracks.items():
 vs=t['vertices'];quads=[]
 actual=next(m for m in d['rails']if m['name']==name)['vertices']
 # Both directions: no omitted or displaced exported track positions.
 source_set={tuple(round(c,5)for c in v)for v in vs};actual_set={tuple(round(c,5)for c in v)for v in actual};assert source_set==actual_set,name
 for k in range(len(vs)//4):
  a=k*4;b=((k+1)%(len(vs)//4))*4;poly=hull([(vs[i][1],vs[i][2])for i in [a,a+2,b,b+2]])
  if len(poly)>=3:quads.append((poly,old.bounds(poly)))
 rails[name]=quads
wheels=[m for m in d['meshes']if m['name'].startswith('STEP_WHEELS')];parts=[components(m)for m in wheels];assert all(len(x)==4 for x in parts)
fail=[];maxdep=0;count=0
for frame,poses in enumerate(d['samples']):
 for i in range(58):
  for part in parts[i]:
   x=sum(part['x'])/2;name='TRACK_'+('CHAIN_'if abs(x)<.63 else'GUIDE_')+('L'if x<0 else'R');poly=transformed(part['poly'],poses[i]);bb=old.bounds(poly)
   for q,qb in rails[name]:
    count+=1;dep=old.fast_sat(poly,q,bb,qb)
    if dep is not None:
     maxdep=max(maxdep,dep)
     if len(fail)<30:fail.append({'frame':frame,'step':i,'track':name,'depth_m':dep})
 if frame%200==0:print(frame,maxdep,len(fail),flush=True)
r={'status':'FAIL'if fail else'PASS_CENTER_PLANE_NONINTERSECTION_ONLY','sha256':d['sha256'],'samples':1201,'tests':count,'max_overlap_m':maxdep,'failures':fail,'tolerance_m':1e-6,'method':'Actual GLB rigid wheel polygon versus source track center-plane quads; source/GLB rail vertex sets verified both directions to 1e-5 m.'};(P/'reports/wheel-rail-sat-05.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
