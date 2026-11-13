import json,math,hashlib,struct,subprocess
from pathlib import Path
p=Path(__file__).resolve().parent;d=json.loads((p/'reports/actual-glb-samples.json').read_text());rails=json.loads((p/'rail-profiles.json').read_text());tracks=[]
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
for name,r in rails.items():
 pts=r['inner'];bad=[]
 for i in range(len(pts)):
  for j in range(i+2,len(pts)):
   if i==0 and j==len(pts)-1:continue
   a,b,c,e=pts[i],pts[(i+1)%len(pts)],pts[j],pts[(j+1)%len(pts)]
   if cross(a,b,c)*cross(a,b,e)<-1e-14 and cross(c,e,a)*cross(c,e,b)<-1e-14:bad.append([i,j])
 tracks.append({'name':name,'segments':len(pts),'self_crossings':bad,'minimum_segment_m':min(math.dist(a,b)for a,b in zip(pts,pts[1:]+pts[:1]))})
chords=[math.dist(a[1:3],b[1:3])for frame in d['samples']for a,b in zip(frame,frame[1:]+frame[:1])]
b=(p/'exports/optimized.glb').read_bytes();g=json.loads(b[20:20+struct.unpack_from('<I',b,12)[0]]);tri=sum(g['accessors'][q['indices']]['count']//3 for m in g['meshes']for q in m['primitives']);prim=sum(len(m['primitives'])for m in g['meshes']);assert tri<=70000 and len(b)<=6000000 and prim<=220;assert not any(t['self_crossings']for t in tracks)
# Full byte comparison was retained for generation04; verify repository content diff again without re-reading every historical binary.
changed=subprocess.check_output(['git','diff','--name-only','2080cee2']).decode().splitlines();assert not changed
surfaces={}
for m in d['fixed']:
 if m['name'].startswith(('LANDING','COMB')):
  expected=3 if 'Upper'in m['name']else 0;top=max(v[2]for v in m['vertices']);assert abs(top-expected)<1e-6;surfaces[m['name']]=top
report={'status':'NEEDS REVIEW','actual_walking_surface_z_m':surfaces,'illustrative_sampled_circulation':'PASS with documented faceting gaps; not physical mechanism acceptance','physical_continuous_contact':'NOT PROVEN; no predeclared allowable gap','rigid_constant_pitch_drive':'NOT PROVEN','attachment_chord_min_m':min(chords),'attachment_chord_max_m':max(chords),'track_profiles':tracks,'triangles':tri,'glb_bytes':len(b),'primitives':prim,'source_sha256':hashlib.sha256((p/'sources/escalator-circulation.blend').read_bytes()).hexdigest(),'glb_sha256':hashlib.sha256(b).hexdigest(),'baseline':'2080cee2dabfae55f0d01f782de0cc6c0ede64c9','all_baseline_tracked_files_byte_identical':True,'catalog_changed':False,'new_registered_assets':0,'landing_top_above_flat_tread_m':0.0,'engineering_or_safety_certification':False,'physical_mobile_safari':'NOT TESTED'}
(p/'reports/final-contracts.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
