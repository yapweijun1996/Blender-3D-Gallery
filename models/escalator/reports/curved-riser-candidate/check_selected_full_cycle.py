import math,json
from pathlib import Path
from kinematics import make_track,profile,transform,bounds,fast_sat,sat,rect
P=Path(__file__).resolve().parent
# Independent SAT rotation/translation controls plus convexity prerequisite.
a=rect(-.2,.2,-.1,.1);rot=transform(a,(0,0,.3,''));assert sat(a,rot)>0;assert sat(a,transform(a,(2,2,.3,''))) is None

def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def intersect(a,b,c,d):return cross(a,b,c)*cross(a,b,d)<-1e-14 and cross(c,d,a)*cross(c,d,b)<-1e-14
reports=[]
for R in [.275,.5,.75]:
 pose,L,N,pitch,flat=make_track(R,-1);pivot=(.36,-.2);poly=[(y-pivot[0],z-pivot[1]) for y,z in profile(pitch)];assert all(cross(poly[i],poly[(i+1)%len(poly)],poly[(i+2)%len(poly)])<0 for i in range(len(poly)))
 collisions=[];pairchecks=0;maxd=0
 for frame in range(1201):
  ps=[pose(L*frame/1200+i*pitch) for i in range(N)];polys=[transform(poly,p) for p in ps];bs=[bounds(p) for p in polys]
  for i in range(N):
   for j in range(i+1,N):
    pairchecks+=1;d=fast_sat(polys[i],polys[j],bs[i],bs[j])
    if d is not None:
     maxd=max(maxd,d)
     if len(collisions)<10:collisions.append({'frame':frame,'pair':[i,j],'depth':d,'regions':[ps[i][3],ps[j][3]]})
 tracks=[]
 for name,offset in [('chain',(0,0)),('rear_guide',(-.32,.03))]:
  points=[transform([offset],pose(i*L/1200))[0] for i in range(1200)];smallest_radius=1e9;min_speed=1e9
  for i in range(len(points)):
   a,b,c=points[(i-1)%len(points)],points[i],points[(i+1)%len(points)];ab=math.dist(a,b);bc=math.dist(b,c);ac=math.dist(a,c);area=abs(cross(a,b,c))/2
   if area>1e-12:smallest_radius=min(smallest_radius,ab*bc*ac/(4*area))
   min_speed=min(min_speed,bc/(L/1200))
  crossings=[]
  for i in range(len(points)):
   for j in range(i+2,len(points)):
    if i==0 and j==len(points)-1:continue
    if intersect(points[i],points[(i+1)%len(points)],points[j],points[(j+1)%len(points)]):crossings.append([i,j])
  tracks.append({'name':name,'self_crossings':crossings[:10],'count_self_crossings':len(crossings),'minimum_sampled_curvature_radius_m':smallest_radius,'min_motion_speed_ratio':min_speed,'roller_radius_m':.035,'sample_points':points})
 report={'turn_radius_m':R,'chain_pivot_local':pivot,'result':'FAIL' if collisions or any(t['count_self_crossings'] or t['minimum_sampled_curvature_radius_m']<.035 for t in tracks) else 'PASS_ANALYTIC_ONLY','samples':1201,'all_step_pairs_checked':pairchecks,'max_overlap_m':maxd,'collisions':collisions,'tracks':tracks,'period_s':L/.5,'step_count':N,'arc_pitch_m':pitch,'landing_length_m':flat,'path_length_m':L,'fixed_asset_budget':{'triangles':70000,'bytes':6000000,'mesh_primitives':220},'remaining':'fixed guards/comb/landings,source/GLB interpolation and actual rendering/browser'}
 reports.append(report);print(json.dumps({**report,'tracks':[{k:v for k,v in t.items() if k!='sample_points'} for t in tracks]}),flush=True)
(P/'selected-full-cycle-results.json').write_text(json.dumps(reports,indent=2)+'\n')
