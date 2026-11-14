import math,json
from pathlib import Path
from kinematics import make_track,profile,transform
P=Path(__file__).resolve().parent

def clip(poly,y0,ge):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ia=a[0]>=y0 if ge else a[0]<=y0;ib=b[0]>=y0 if ge else b[0]<=y0
  if ia:out.append(a)
  if ia!=ib:
   t=(y0-a[0])/(b[0]-a[0]);out.append((y0,a[1]+t*(b[1]-a[1])))
 return out
results=[]
for radius in [.275,.5,.75]:
 pose,L,N,pitch,flat=make_track(radius,-1);pivot=(.36,-.2);poly=[(y-pivot[0],z-pivot[1]) for y,z in profile(pitch)];topend=max(pose(i*L/6000)[0] for i in range(6000) if pose(i*L/6000)[3]=='upper_flat');metrics={'lower':-1e9,'upper':-1e9};examples={}
 for frame in range(1201):
  for i in range(N):
   p=pose(frame*L/1200+i*pitch);a=transform(poly,p);a=[(y,z-.2) for y,z in a]
   for name,limit,ge,height in [('lower',.6,False,0),('upper',topend-.6,True,3)]:
    c=clip(a,limit,ge)
    if c:
     over=max(v[1] for v in c)-height
     if over>metrics[name]:metrics[name]=over;examples[name]={'frame':frame,'step':i,'region':p[3],'clipped_polygon':c}
 result={'turn_radius_m':radius,'platform_top_levels_m':[0,3],'plate_underside_clearance_m':.005,'max_step_above_landing_m':metrics,'result':'PASS_ENVELOPE_ONLY' if max(metrics.values())<.005 else 'FAIL','examples':examples,'width_clearance_m':.04,'comb_proposal':{'rib_pitch_m':.04,'rib_width_m':.023,'tooth_width_m':.011,'side_clearance_m':(.04-.023-.011)/2,'body_top_m':-.02,'tooth_bottom_m':-.012,'vertical_body_clearance_m':.008},'unverified':'actual mesh teeth/rib bevels, full GLB tracks; no motion asset pass'};results.append(result);print(json.dumps({k:v for k,v in result.items() if k!='examples'}))
(P/'landing-envelope-results.json').write_text(json.dumps(results,indent=2)+'\n')
