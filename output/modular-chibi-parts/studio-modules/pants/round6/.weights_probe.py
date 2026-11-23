import bpy, runpy
from pathlib import Path
import numpy as np
fit = runpy.run_path(str(Path(__file__).with_name('fit_pants_r6.py')))
fit['cache'].__globals__['frames'] = lambda actions: [('rest',1.),('run',8.),('run',9.),('walk',28.),('sit_idle',11.),('sit_idle',22.)]
scene, arm, body, garment, actions = fit['setup']()
names = tuple(arm.pose.bones.keys())
body_faces = fit['faces_of'](body.data)
samples, transforms = fit['cache'](scene, arm, body, actions, body_faces)
p, w, _ = fit['prepare'](garment, samples[0][2], names, body, body_faces, samples[0][3])
f = fit['faces_of'](garment.data)
graph = fit['adjacency'](garment.data)
api = fit['BASE']
natural = api['transfer_weights'](p,samples[0][3],body_faces,fit['read_weights'](body,names),samples[0][2],graph,names)
before=set(scene.objects)
bpy.ops.import_scene.gltf(filepath=str(fit['PARTS']/'studio-modules/jeans/round5/jeans_v5.glb'),merge_vertices=True)
jeans, = [o for o in bpy.context.selected_objects if o.type=='MESH']
jpoints = fit['coords'](jeans.data)
jfaces = fit['faces_of'](jeans.data)
jweights = fit['read_weights'](jeans,names)
jean_tree = fit['tree_for'](jpoints,jfaces.tolist())
hits = [jean_tree.find_nearest(point) for point in p]
ids = np.array([h[2] for h in hits])
nearest = np.array([tuple(h[0]) for h in hits])
bary = api['barycentric'](jpoints[jfaces[ids]],nearest).clip(0,1)
denom = bary.sum(axis=1,keepdims=True).clip(1e-6)
jeans = np.einsum('ni,nij->nj',bary/denom,jweights[jfaces[ids]])
if (jeans.sum(axis=1)==0).any(): jeans[jeans.sum(axis=1)==0]=natural[jeans.sum(axis=1)==0]
for name, trial in [('prep',w),('natural',natural),('jeans',jeans),('blend',.33*w+.67*jeans),('medium',.5*w+.5*natural)]:
    result=fit['scan'](p,fit['trim_weights'](trial),f,samples,transforms,body_faces)
    print('TEST',name,fit['quality'](result),result[0].min(axis=1)*1000,result[1], 'restmax', result[0][0].max()*1000, flush=True)
    for i in (1,2,4):
       v=result[0][i].argmin()
       print('ZONE', samples[i][:2], api['zone'](p[v]),np.round(p[v]*1000,2).tolist(),float(result[0][i,v]),[(n,round(float(a),3)) for n,a in zip(names,trial[v]) if a>0.005],flush=True)
