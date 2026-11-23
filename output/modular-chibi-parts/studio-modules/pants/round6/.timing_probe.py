import runpy
from pathlib import Path
from time import perf_counter
import numpy as np
fit = runpy.run_path(str(Path(__file__).with_name('fit_pants_r6.py')))
fit['cache'].__globals__['frames'] = lambda actions: [('rest',1.),('run',9.),('walk',28.),('sit_idle',11.),('hold_item',15.)]
scene, arm, body, garment, actions = fit['setup'](fit['HERE']/'.prepared.glb')
names = tuple(arm.pose.bones.keys())
faces = fit['faces_of'](body.data)
samples, transforms = fit['cache'](scene, arm, body, actions, faces)
p = fit['coords'](garment.data)
w = fit['read_weights'](garment, names)
f = fit['faces_of'](garment.data)
api=fit['BASE']
for title, func in [
    ('dense', lambda: api['skin_matrices'](w, np.tile(transforms,(90,1,1,1)))),
    ('sparse', lambda: np.sum(np.tile(transforms,(90,1,1,1))[:,np.argsort(-w,axis=1)[:,:4]]*np.sort(w,axis=1)[:,::-1][:,:4][None,:,:,None,None],axis=2)),
    ('measure', lambda: fit['scan'](p,w,f,samples,transforms,faces)),
]:
    start=perf_counter()
    value=func()
    print('TIME',title,perf_counter()-start,flush=True)
    if title=='measure':
        for i,row in enumerate(samples):
            d,c=value[:2]; idx=np.argmin(d[i]); print('TIGHT',row[:2],d[i,idx],c[i],p[idx],w[idx,np.flatnonzero(w[idx])], [names[j] for j in np.flatnonzero(w[idx])],flush=True)
