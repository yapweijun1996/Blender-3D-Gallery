import json,math,numpy as np
from pathlib import Path
p=Path(__file__).resolve().parent;d=json.loads((p/'reports/actual-glb-samples.json').read_text());tracks=json.loads((p/'reports/track-source-geometry.json').read_text());poses=np.array(d['samples']).reshape(-1,7);reports=[]
for name,dy,dz in [('TRACK_CHAIN_L',0,0),('TRACK_GUIDE_L',-.32,.03)]:
 pts=np.array(tracks[name]['centers'])[:,1:];a=pts;b=np.roll(pts,-1,axis=0);v=b-a;vv=(v*v).sum(axis=1)
 centers=np.column_stack([poses[:,1]+np.cos(poses[:,3])*dy-np.sin(poses[:,3])*dz,poses[:,2]+np.sin(poses[:,3])*dy+np.cos(poses[:,3])*dz]);dist=[]
 for start in range(0,len(centers),500):
  w=centers[start:start+500,None,:]-a[None,:,:];t=np.clip((w*v).sum(axis=2)/vv,0,1);delta=w-t[:,:,None]*v;dist.extend(np.sqrt((delta*delta).sum(axis=2).min(axis=1)).tolist())
 reports.append({'track':name,'samples':len(dist),'min_centerline_distance_m':min(dist),'max_centerline_distance_m':max(dist),'nominal_radius_sum_m':.047,'min_envelope_gap_m':min(dist)-.047,'max_envelope_gap_m':max(dist)-.047,'scope':'Conservative circular roller and rail envelope diagnostic, not exact faceted triangle contact acceptance.'})
(p/'reports/contact-diagnostic-03.json').write_text(json.dumps(reports,indent=2));print(json.dumps(reports))
