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

import numpy as np
ks=importlib.util.spec_from_file_location('candidatekin',P/'kinematics.py');kin=importlib.util.module_from_spec(ks);ks.loader.exec_module(kin)
pose,L,N,pitch,flat=kin.make_track(.75,-1)
# Geometry proposal only; all existing source/GLB bytes remain unchanged.
phases=np.array([(L*f/1200+i*pitch)%L for f in range(1201)for i in range(58)]);order=np.argsort(phases);phases=phases[order];poses=np.array(d['samples']).reshape(-1,7)[order]
wheel=next(m for m in d['meshes']if m['name']=='STEP_WHEELS_00');parts=components(wheel)
reports=[];out={}
for name,dy,dz in [('CHAIN',0,0),('GUIDE',-.32,.03)]:
 part=next(v for v in parts if v['x'][1]<0 and (abs(sum(v['x'])/2)<.63)==(name=='CHAIN'));local=np.array(part['poly']);c=np.cos(poses[:,3,None]);sn=np.sin(poses[:,3,None]);wy=poses[:,1,None]+c*local[:,0]-sn*local[:,1];wz=poses[:,2,None]+sn*local[:,0]+c*local[:,1];world=np.stack([wy,wz],axis=2)
 def center(s):
  y,z,a,_=pose(s);return np.array([y+math.cos(a)*dy-math.sin(a)*dz-poses[0,1]+poses[0,1],z+math.sin(a)*dy+math.cos(a)*dz-.2])
 # Derive CENTER from exact first step at phase zero, so world coordinates match GLB.
 center_offset=-d['samples'][0][0][1]
 def center(s):
  y,z,a,_=pose(s);return np.array([y+math.cos(a)*dy-math.sin(a)*dz-center_offset,z+math.sin(a)*dy+math.cos(a)*dz-.2])
 parameters=[0.];s=0
 while s<L:
  pm=center(s-.02);pc=center(s);pp=center(s+.02);u=pc-pm;v=pp-pc;cross=abs(u[0]*v[1]-u[1]*v[0])/(np.linalg.norm(u)*np.linalg.norm(v));da=abs(math.sin(pose(s+.02)[2]-pose(s-.02)[2]));step=.025 if cross>.001 or da>.001 else .20
  s=min(L,s+step)
  if s<L:parameters.append(s)
 normals=[];offsets=[]
 for i,s in enumerate(parameters):
  end=parameters[i+1]if i+1<len(parameters)else L;a=center(s);b=center(end);t=(b-a)/np.linalg.norm(b-a);n=np.array([t[1],-t[0]]);mid=(s+end)/2;delta=np.abs((phases-mid+L/2)%L-L/2);polys=world[delta<(end-s)/2+.12];tv=polys@t;nv=polys@n;lo=a@t-.003;hi=b@t+.003;values=list(nv[(tv>=lo)&(tv<=hi)])
  for boundary in [lo,hi]:
   tv2=np.roll(tv,-1,axis=1);nv2=np.roll(nv,-1,axis=1);mask=(tv-boundary)*(tv2-boundary)<0
   if mask.any():values.extend((nv[mask]+(boundary-tv[mask])/(tv2[mask]-tv[mask])*(nv2[mask]-nv[mask])).tolist())
  assert values
  normals.append(n);offsets.append(max(values)+.000002)
 points=[];outer=[]
 for i in range(len(parameters)):
  n1,n2=normals[i-1],normals[i];det=n1[0]*n2[1]-n1[1]*n2[0]
  if abs(det)<1e-7:
   v=center(parameters[i]);v=v+n2*(max(offsets[i-1],offsets[i])-v@n2);w=v+n2*.024
  else:
   A=np.array([n1,n2]);v=np.linalg.solve(A,[offsets[i-1],offsets[i]]);w=np.linalg.solve(A,[offsets[i-1]+.024,offsets[i]+.024])
  points.append(v.tolist());outer.append(w.tolist())
 quads=[hull([points[i],points[(i+1)%len(points)],outer[(i+1)%len(points)],outer[i]])for i in range(len(points))];bounds=[old.bounds(q)for q in quads];fail=[];maxdep=0;checks=0
 # Every exported pose and both wheel positions have identical YZ shapes across left/right.
 for f in range(0,len(world)):
  poly=world[f].tolist();bb=old.bounds(poly)
  for q,qb in zip(quads,bounds):
   if qb[2]<bb[0]or bb[2]<qb[0]or qb[3]<bb[1]or bb[3]<qb[1]:continue
   checks+=1;dep=old.fast_sat(poly,q,bb,qb)
   if dep is not None:
    maxdep=max(maxdep,dep)
    if len(fail)<12:fail.append({'phase':float(phases[f]),'depth_m':dep})
 out[name]={'inner':points,'outer':outer,'phase':parameters};reports.append({'track':name,'segments':len(points),'narrow_tests':checks,'maximum_overlap_m':maxdep,'failures':fail,'status':'FAIL'if fail else'PASS_ANALYTIC_NONINTERSECTION_ONLY'})
 print(json.dumps(reports[-1]),flush=True)
(P/'reports/faceted-envelope-proposal.json').write_text(json.dumps(out));(P/'reports/faceted-envelope-result.json').write_text(json.dumps(reports,indent=2))
