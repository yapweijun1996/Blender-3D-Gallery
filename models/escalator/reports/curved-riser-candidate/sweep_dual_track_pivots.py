import math,json,bisect,ast
from pathlib import Path
P=Path(__file__).resolve().parent
# Import only pure SAT helper definitions, not the old failed simulation.
old=ast.parse((P.parent/'circulation-feasibility/check_rigid_chain.py').read_text());ns={'math':math};exec(compile(ast.Module(body=[n for n in old.body if isinstance(n,ast.FunctionDef) and n.name in ['rect','overlap']],type_ignores=[]),'SAT','exec'),ns);sat=ns['overlap'];rect=ns['rect']
assert sat(rect(0,1,0,1),rect(1,2,0,1)) is None
assert abs(sat(rect(0,1,0,1),rect(.5,1.5,.5,1.5))-.5)<1e-12
ANGLE=math.pi/6;TRANS_R=1.5;H=.2;GAP=.004;DEPTH=.396

def make_track(turn_r,rotation_sign):
 rise=3.;straight=(rise-2*TRANS_R*(1-math.cos(ANGLE)))/math.sin(ANGLE);flat=1.2
 # Force exact400mm arc pitch through a small explicit landing-length adjustment.
 estimated=2*(2*flat+2*TRANS_R*ANGLE+straight)+2*math.pi*turn_r
 count=math.ceil(estimated/.4);flat+=(count*.4-estimated)/4
 upper=[]
 for i in range(121):upper.append((flat*i/120,0.,0.,'lower_flat'))
 y,z=upper[-1][:2]
 for i in range(1,181):
  a=ANGLE*i/180;upper.append((y+TRANS_R*math.sin(a),z+TRANS_R*(1-math.cos(a)),0.,'lower_transition'))
 y,z=upper[-1][:2]
 for i in range(1,601):upper.append((y+straight*i/600*math.cos(ANGLE),z+straight*i/600*math.sin(ANGLE),0.,'incline'))
 y,z=upper[-1][:2]
 for i in range(1,181):
  a=ANGLE*(1-i/180);upper.append((y+TRANS_R*(math.sin(ANGLE)-math.sin(a)),z+TRANS_R*(math.cos(a)-math.cos(ANGLE)),0.,'upper_transition'))
 y,z=upper[-1][:2]
 for i in range(1,121):upper.append((y+flat*i/120,z,0.,'upper_flat'))
 path=list(upper);y,z=upper[-1][:2]
 for i in range(1,361):
  a=math.pi*i/360;path.append((y+turn_r*math.sin(a),z-turn_r+turn_r*math.cos(a),rotation_sign*a,'upper_turn'))
 for y,z,_,reg in reversed(upper[:-1]):path.append((y,z-2*turn_r,rotation_sign*math.pi,'return_'+reg))
 y,z=upper[0][:2]
 for i in range(1,361):
  a=math.pi+math.pi*i/360;path.append((y+turn_r*math.sin(a),z-turn_r+turn_r*math.cos(a),rotation_sign*a,'lower_turn'))
 lens=[0.]
 for a,b in zip(path,path[1:]):lens.append(lens[-1]+math.hypot(b[0]-a[0],b[1]-a[1]))
 L=lens[-1];pitch=L/count
 def pose(s):
  s%=L;i=min(len(path)-2,bisect.bisect_right(lens,s)-1);t=(s-lens[i])/(lens[i+1]-lens[i]);a,b=path[i:i+2]
  return (a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]),a[2]+t*(b[2]-a[2]),a[3])
 return pose,L,count,pitch,flat

def profile(pitch):
 # Finite solid curved wedge: full tread, concave riser and integral rigid support.
 # Curve derived mathematically, not copied from a manufacturer's geometry.
 arc=[]
 for i in range(17):
  z=-H+H*i/16;arc.append((pitch-math.sqrt(pitch*pitch-z*z)+GAP,z))
 return [(GAP,0),(DEPTH,0),(DEPTH,-H)]+arc[:-1]

def transform(poly,p):
 y,z,a,_=p;c,s=math.cos(a),math.sin(a);return [(y+c*x-s*v,z+s*x+c*v) for x,v in poly]
def bounds(a):return (min(v[0] for v in a),max(v[0] for v in a),min(v[1] for v in a),max(v[1] for v in a))
def fast_sat(a,b,aa,bb):
 if min(aa[1],bb[1])-max(aa[0],bb[0])<=1e-6 or min(aa[3],bb[3])-max(aa[2],bb[2])<=1e-6:return None
 return sat(a,b)
reports=[]
for radius in [.275,.5,.75]:
 for pivot_y in [.30,.36,.396]:
  for pivot_z in [-.15,-.20,-.25]:
   pose,L,N,pitch,flat=make_track(radius,-1);poly=[(y-pivot_y,z-pivot_z) for y,z in profile(pitch)];counts={};examples={};maxd=0;tested=0
   for frame in range(121):
    ps=[pose(L*frame/120+i*pitch) for i in range(N)];polys=[transform(poly,p) for p in ps];bs=[bounds(p) for p in polys]
    for i in range(N):
     for k in [1,2,3]:
      j=(i+k)%N;tested+=1;d=fast_sat(polys[i],polys[j],bs[i],bs[j])
      if d is not None:
       key=ps[i][3]+' / '+ps[j][3];counts[key]=counts.get(key,0)+1;maxd=max(maxd,d)
       if key not in examples:examples[key]={'frame':frame,'steps':[i,j],'overlap_m':d,'polygons':[polys[i],polys[j]]}
   report={'result':'FAIL' if counts else 'NEEDS REVIEW','turn_radius_m':radius,'chain_pivot_local':[pivot_y,pivot_z],'turn_orientation_sign':-1,'transition_radius_m':TRANS_R,'profile':'complete finite rigid curved wedge with underside chain pivot','steps':N,'arc_pitch_m':pitch,'path_length_m':L,'samples':121,'pair_checks':tested,'collision_counts':counts,'max_SAT_overlap_m':maxd,'examples':examples,'unchecked':'full wheel tracks, all nonadjacent pairs, comb/guard sweeps and GLB'}
   reports.append(report);print(json.dumps({k:v for k,v in report.items() if k!='examples'}),flush=True)
(P/'dual-track-pivot-results.json').write_text(json.dumps(reports,indent=2)+'\n')
