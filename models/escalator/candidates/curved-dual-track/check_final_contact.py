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
tracks=json.loads((P/'reports/track-source-geometry.json').read_text());spec=json.loads((P/'rail-profiles.json').read_text());poses=np.array(d['samples']).reshape(-1,7);L=23.199983939521772;phases=np.array([(L*f/1200+i*L/58)%L for f in range(1201)for i in range(58)])
parts=components(next(m for m in d['meshes']if m['name']=='STEP_WHEELS_00'));reports=[]
def distances(v,a,b):
 e=b-a;w=v-a;t=np.clip((w*e).sum(axis=-1)/(e*e).sum(axis=-1),0,1);return np.sqrt(((w-t[...,None]*e)**2).sum(axis=-1))
for name in ['CHAIN','GUIDE']:
 part=next(v for v in parts if v['x'][1]<0 and (abs(sum(v['x'])/2)<.63)==(name=='CHAIN'));local=np.array(part['poly']);c=np.cos(poses[:,3,None]);sn=np.sin(poses[:,3,None]);world=np.stack([poses[:,1,None]+c*local[:,0]-sn*local[:,1],poses[:,2,None]+sn*local[:,0]+c*local[:,1]],axis=2)
 # Source rings are position-equivalent to the actual GLB as checked by wheel-rail SAT.
 vs=tracks['TRACK_'+name+'_L']['vertices'];ip=np.array([[v[1],v[2]]for v in vs[::4]]);jp=np.roll(ip,-1,axis=0);phasearr=np.array(spec[name]['phase']);gaps=[]
 for start in range(0,len(world),500):
  ww=world[start:start+500];ii=np.searchsorted(phasearr,phases[start:start+500],side='right')-1;ix=(ii[:,None]+np.arange(-6,7)[None,:])%len(ip);aa=ip[ix];bb=jp[ix]
  ds=distances(ww[:,:,None,:],aa[:,None,:,:],bb[:,None,:,:]).min(axis=(1,2));ds2=distances(aa[:,:,None,:],ww[:,None,:,:],np.roll(ww,-1,axis=1)[:,None,:,:]).min(axis=(1,2));gaps.extend(np.minimum(ds,ds2).tolist())
 reports.append({'track':name,'frames':1201,'positions':len(gaps),'min_gap_m':min(gaps),'max_gap_m':max(gaps),'max_phase_m':float(phases[int(np.argmax(gaps))]),'acceptance':'NEEDS REVIEW: no new contact-gap allowance silently introduced.'})
r={'sha256':d['sha256'],'status':'NEEDS REVIEW','method':'Actual GLB wheel polygon-to-export-equivalent inner contact polyline distance in both vertex/edge directions. Not an engineering contact or force simulation.','tracks':reports};(P/'reports/final-contact-06.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
