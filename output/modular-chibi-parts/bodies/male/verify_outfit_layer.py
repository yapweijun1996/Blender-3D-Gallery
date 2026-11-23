from asset_io import HERE,MOTION,bpy,write_json
from body_audit import load_body_motion,posed,set_frame,use_action
from fitting_geometry import arrays,tree
from fit_module import read_module
from hashlib import sha256

sc,arm,body,actions=load_body_motion(MOTION)
objs=[read_module(HERE/f'male-{k}.glb',arm) for k in ('tshirt','jeans')]
tris=[arrays(o)[1].tolist() for o in objs]
records={}
for clip,frame in (('rest',1),('idle',24)):
    use_action(arm,actions.get(clip))
    set_frame(sc,frame)
    a,b=[tree(posed(o),f) for o,f in zip(objs,tris)]
    records[clip]={'frame':frame,'triangle_pairs':len(a.overlap(b))}
out={'clips':records,
     'assets':{k:sha256((HERE/f'male-{k}.glb').read_bytes()).hexdigest() for k in ('tshirt','jeans')}}
write_json(HERE/'qa/outfit_layer_reimport.json',out)
print(out,flush=True)
