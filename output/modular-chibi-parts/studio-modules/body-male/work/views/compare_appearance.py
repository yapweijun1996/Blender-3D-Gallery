"""Compare protected regions of matched Cycles rest captures in display-referred RGB."""
import json
from pathlib import Path
import bpy
import numpy as np
p=Path(__file__).resolve().parent
a,b=[json.loads((p/d/'manifest.json').read_text()) for d in ('baseline','rest')]
frames=[next(f for f in doc['frames'] if f['image']=='rest_front.png') for doc in (a,b)]
assert a['samples']==b['samples'] and a['blender']==b['blender']
fa,fb=frames
assert fa['pixels']==fb['pixels']
assert max(abs(x-y) for x,y in zip(fa['camera_direction'],fb['camera_direction']))<1e-7
imgs=[]
for d in ('baseline','rest'):
    im=bpy.data.images.load(str(p/d/'rest_front.png'))
    im.colorspace_settings.name='Non-Color'
    v=np.empty(len(im.pixels),dtype=np.float32)
    im.pixels.foreach_get(v)
    imgs.append(np.round(v.reshape(im.size[1],im.size[0],4)[::-1,:,:3]*255).astype(float))
x,y=np.meshgrid(np.arange(fa['pixels'][0]),np.arange(fa['pixels'][1]))
report={}
for region,selection in {
    'head':(y<258),
    'eyes':(y>=146)&(y<=217)&(x>=229)&(x<=411),
    'torso_shorts_legs_feet':(y>=258)&(x>=236)&(x<=402),
}.items():
    bg=np.median(imgs[0][:20,:,:],axis=(0,1))
    mask=selection & (np.linalg.norm(imgs[0]-bg,axis=2)>48)
    d=np.abs(imgs[0][mask]-imgs[1][mask])
    report[region]={'pixels':int(mask.sum()),'mean_absolute_8bit_channel_error':float(d.mean()),
                    'p95_absolute_8bit_channel_error':float(np.quantile(d,.95)),
                    'max_absolute_8bit_channel_error':float(d.max())}
print(json.dumps(report))
(p/'appearance_comparison.json').write_text(json.dumps({
    'source_sha256':a['body'][1],'candidate_sha256':b['body'][1],
    'source_capture_sha256':frames[0]['sha256'],'candidate_capture_sha256':frames[1]['sha256'],
    'orthographic_width_m':[f['ortho_width_m'] for f in frames],
    'target_shift_world_m':[float(x-y) for x,y in zip(fb['target_m'],fa['target_m'])],
    'renderer':a['renderer'],'samples':a['samples'],'measure':'Absolute display-referred RGB channel difference on source foreground in the indicated frontal crops. Includes denoiser and rasterization differences.','regions':report},indent=2))
