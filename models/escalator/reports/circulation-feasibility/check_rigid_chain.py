"""Reject or admit a proposed rigid-step path before Blender generation.
This is a 2D extruded-step collision feasibility test, NOT GLB motion evidence.
All steps have identical1m X width; positive YZ polygon overlap therefore proves
3D intersection. Adjacent-pair test is sufficient to reject, not sufficient to
certify a passing mechanism. No hiding/scaling/fading of risers is permitted.
"""
import math,json,bisect
from pathlib import Path
P=Path(__file__).resolve().parent
THETA=math.pi/6;TRANSITION_R=.6;TURN_R=.275;SPEED=.5
TREAD_DEPTH=.398;TREAD_THICKNESS=.035;RISER_HEIGHT=.2;RISER_THICKNESS=.012
# Smooth slope-angle transitions: horizontal ->30deg ->horizontal; rise exactly3m.
arc_rise=2*TRANSITION_R*(1-math.cos(THETA));incline_length=(3-arc_rise)/math.sin(THETA)
upper=[]
for i in range(121):upper.append((i*.01,0.,0.,'lower_flat'))
y,z=upper[-1][:2]
for i in range(1,121):
 a=THETA*i/120;upper.append((y+TRANSITION_R*math.sin(a),z+TRANSITION_R*(1-math.cos(a)),0.,'lower_transition'))
y,z=upper[-1][:2]
for i in range(1,601):upper.append((y+incline_length*i/600*math.cos(THETA),z+incline_length*i/600*math.sin(THETA),0.,'incline'))
y,z=upper[-1][:2]
for i in range(1,121):
 a=THETA*(1-i/120);upper.append((y+TRANSITION_R*(math.sin(THETA)-math.sin(a)),z+TRANSITION_R*(math.cos(a)-math.cos(THETA)),0.,'upper_transition'))
y,z=upper[-1][:2]
for i in range(1,121):upper.append((y+i*.01,z,0.,'upper_flat'))
assert abs(upper[-1][1]-3)<1e-10
path=list(upper);y,z=upper[-1][:2]
for i in range(1,181):
 a=math.pi*i/180;path.append((y+TURN_R*math.sin(a),z-TURN_R+TURN_R*math.cos(a),-a,'upper_turn'))
for y,z,_,region in reversed(upper[:-1]):path.append((y,z-2*TURN_R,-math.pi,'return_'+region))
y,z=upper[0][:2]
for i in range(1,181):
 a=math.pi+math.pi*i/180;path.append((y+TURN_R*math.sin(a),z-TURN_R+TURN_R*math.cos(a),-a,'lower_turn'))
lengths=[0.]
for a,b in zip(path,path[1:]):lengths.append(lengths[-1]+math.hypot(b[0]-a[0],b[1]-a[1]))
L=lengths[-1];N=round(L/.4);pitch=L/N;period=L/SPEED
# Match the rigid riser height to the exact closed-chain pitch on30deg incline.
# This corrects the geometric input; the nonintersection threshold is unchanged.
RISER_HEIGHT=pitch*math.sin(THETA)

def pose(s):
 s%=L;i=min(len(path)-2,bisect.bisect_right(lengths,s)-1);t=(s-lengths[i])/(lengths[i+1]-lengths[i]);a,b=path[i:i+2]
 return (a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]),a[2]+t*(b[2]-a[2]),a[3])
def rect(y0,y1,z0,z1):return [(y0,z0),(y1,z0),(y1,z1),(y0,z1)]
local=[rect(-TREAD_DEPTH/2,TREAD_DEPTH/2,-TREAD_THICKNESS,0),rect(-TREAD_DEPTH/2,-TREAD_DEPTH/2+RISER_THICKNESS,-RISER_HEIGHT,-TREAD_THICKNESS)]
def polygons(p):
 y,z,a,_=p;c,s=math.cos(a),math.sin(a)
 return [[(y+c*x-s*v,z+s*x+c*v) for x,v in poly] for poly in local]
def overlap(a,b):
 minimum=1e9
 for poly in [a,b]:
  for p,q in zip(poly,poly[1:]+poly[:1]):
   dx,dz=q[0]-p[0],q[1]-p[1];norm=math.hypot(dx,dz);axis=(-dz/norm,dx/norm)
   va=[v[0]*axis[0]+v[1]*axis[1] for v in a];vb=[v[0]*axis[0]+v[1]*axis[1] for v in b]
   d=min(max(va),max(vb))-max(min(va),min(vb))
   if d<=1e-6:return None
   minimum=min(minimum,d)
 return minimum
failures=[];counts={};examples={};maxpenetration=0.
for frame in range(241):
 distance=L*frame/240
 for i in range(N):
  a=pose(distance+i*pitch);b=pose(distance+(i+1)*pitch)
  for ai,pa in enumerate(polygons(a)):
   for bi,pb in enumerate(polygons(b)):
    depth=overlap(pa,pb)
    if depth is not None:
     key=a[3]+' / '+b[3];counts[key]=counts.get(key,0)+1;maxpenetration=max(maxpenetration,depth)
     row={'frame':frame,'step':i,'next_step':(i+1)%N,'region':key,'part_pair':[ai,bi],'positive_SAT_overlap_m':depth,'polygons':[pa,pb]}
     if len(failures)<20:failures.append(row)
     if key not in examples:examples[key]=row
closure=max(math.hypot(pose(i*pitch)[0]-pose(L+i*pitch)[0],pose(i*pitch)[1]-pose(L+i*pitch)[1]) for i in range(N))
# Independent loop periods are necessary for equal belt linear speed. This is a
# scheduling calculation only, not a simulated handrail/step-contact proof.
handrail_length=L+1.2;handrail_period=handrail_length/SPEED
report={'result':'FAIL' if counts else 'NEEDS REVIEW','asset_status':'NEEDS REVIEW','reason':'Rigid rectangular riser/tread pairs intersect through flattening and turnarounds; no mechanism exported','static_base_commit':'b4d71d712881fcf43200f61070475155c1b4e118','fixed_asset_budget':{'triangles':70000,'bytes':6000000,'mesh_primitives':220},'design':{'rise_m':3,'main_angle_deg':30,'upper_transition_radius_m':TRANSITION_R,'turn_radius_m':TURN_R,'tread_depth_m':TREAD_DEPTH,'tread_thickness_m':TREAD_THICKNESS,'riser_height_m':RISER_HEIGHT,'nominal_pitch_m':.4,'actual_closed_chain_pitch_m':pitch,'steps':N,'path_length_m':L,'speed_m_s':SPEED,'period_s':period},'sample_frames_including_endpoints':241,'adjacent_pair_checks':241*N*4,'collision_counts_by_region':counts,'max_positive_overlap_m':maxpenetration,'first_failures':failures,'closure_position_error_m':closure,'handrail_speed_scheduling_only':{'illustrative_distinct_length_m':handrail_length,'independent_period_s':handrail_period,'computed_speed_m_s':handrail_length/handrail_period,'not_a_verified_geometry_track':True},'unmet':['nonintersecting rigid-step flattening','nonintersecting rigid-step turnaround','actual comb/landing/guard swept clearance','final Blender/GLB raw motion tracks','matched handrail geometry and linear-speed validation','rendered extreme-pose and browser motion inspection'],'limitations':'Reject-only simplified rigid L-profile candidate. Does not prove no valid curved-riser dual-track mechanism exists. No engineering/safety certification.'}
(P/'result.json').write_text(json.dumps(report,indent=2)+'\n');(P/'collision-examples.json').write_text(json.dumps(examples,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['first_failures']},indent=2));raise SystemExit(1 if counts else 0)
