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
body=[m for m in d['meshes']if m['name'].startswith('STEP_BODY')];assert len(body)==58
polys=[hull([(v[1],v[2])for v in m['vertices']])for m in body]
parts=[components(m)for m in body];assert all(len(x)==26 for x in parts),[len(x)for x in parts]
fixed=[]
for m in d['fixed']:
 # Non-convex side and bottom panels are decomposed into their actual triangles.
 if m['name'].startswith(('TRUSS','GUARD','SKIRT')):
  vs=m['vertices'];idx=m['indices']
  for i in range(0,len(idx),3):
   tri=[vs[j]for j in idx[i:i+3]];poly=hull([(v[1],v[2])for v in tri])
   if len(poly)>=3:fixed.append({'name':m['name'],'poly':poly,'x':(min(v[0]for v in tri),max(v[0]for v in tri))})
 else:
  for c in components(m):fixed.append({'name':m['name'],**c})
for f in fixed:f['bounds']=old.bounds(f['poly'])
# SAT must detect collision and distinguish a separating translation.
r=[(0,0),(1,0),(1,1),(0,1)];assert old.sat(r,[(x+.5,y)for x,y in r]) is not None;assert old.sat(r,[(x+2,y)for x,y in r]) is None
fail=[];pair_count=0;fixed_count=0;maxoverlap=0
for frame,poses in enumerate(d['samples']):
 worlds=[transformed(p,pose)for p,pose in zip(polys,poses)];bb=[old.bounds(p)for p in worlds]
 for i in range(58):
  assert max(abs(v-1)for v in poses[i][4:])<1e-5,'scale animation forbidden'
  for j in range(i+1,58):
   pair_count+=1;dep=old.fast_sat(worlds[i],worlds[j],bb[i],bb[j])
   if dep is not None:
    maxoverlap=max(maxoverlap,dep)
    if len(fail)<40:fail.append({'frame':frame,'a':body[i]['name'],'b':body[j]['name'],'depth_m':dep})
  for f in fixed:
   if f['x'][0]>=.5-1e-6 or f['x'][1]<=-.5+1e-6:continue
   if old.fast_sat(worlds[i],f['poly'],bb[i],f['bounds']) is None:continue
   for part in parts[i]:
    if min(part['x'][1],f['x'][1])-max(part['x'][0],f['x'][0])<=1e-6:continue
    w=transformed(part['poly'],poses[i]);fixed_count+=1;dep=old.fast_sat(w,f['poly'],old.bounds(w),f['bounds'])
    if dep is not None:
     maxoverlap=max(maxoverlap,dep)
     if len(fail)<40:fail.append({'frame':frame,'a':body[i]['name'],'b':f['name'],'depth_m':dep})
 if frame%200==0:print('frame',frame,'fail',len(fail),'max',maxoverlap,flush=True)
report={'status':'FAIL'if fail else'PASS_SAMPLED_BODY_CLEARANCE_ONLY','sha256':d['sha256'],'frames':len(d['samples']),'step_pairs':pair_count,'narrow_fixed_component_tests':fixed_count,'maximum_overlap_m':maxoverlap,'failures':fail,'tolerance_m':1e-6,'remaining':'wheel/track contact, rail seam speed, raw closure, browser and source proof'}
(P/'reports/actual-mesh-clearance-02.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));sys.exit(bool(fail))
