"""Numerical glTF evaluation used during optimization, then checked in Blender."""
import math
from mathutils import Matrix, Quaternion
import numpy as np

GLTF_TO_BPY = np.array(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)),dtype=np.float32)


def normalized(a):
    n = np.linalg.norm(a,axis=-1,keepdims=True)
    return a / np.maximum(n,1.e-20)


def matrices(t,q,s):
    x,y,z,w = normalized(q).T
    out = np.zeros((len(t),4,4),dtype=np.float32)
    out[:,0,:3] = np.column_stack((1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)))
    out[:,1,:3] = np.column_stack((2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)))
    out[:,2,:3] = np.column_stack((2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)))
    out[:,:3,:3] *= s[:,None,:]
    out[:,:3,3] = t
    out[:,3,3] = 1
    return out


class Rig:
    def __init__(self, bind):
        skin, = bind.doc['skins']
        self.ids = skin['joints']
        self.names = [bind.nodes[i]['name'].split(':',1)[-1] for i in self.ids]
        self.index = {n:i for i,n in enumerate(self.names)}
        self.parent = [self.ids.index(bind.parents[i]) if bind.parents[i] in self.ids else -1
                       for i in self.ids]
        assert all(p<i for i,p in enumerate(self.parent))
        self.inv = bind.accessor(skin['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1)
        nodes = [bind.nodes[i] for i in self.ids]
        self.rest = tuple(np.asarray([n.get(p,d) for n in nodes],dtype=np.float32) for p,d in
                          [('translation',(0,0,0)),('rotation',(0,0,0,1)),('scale',(1,1,1))])

    def sample(self, library, anim, times):
        out = [np.tile(a[None,:,:],(len(times),1,1)) for a in self.rest]
        index = {library.ids['mixamorig:'+name]:i for i,name in enumerate(self.names)}
        for channel in anim['channels']:
            target = channel['target']
            if target['node'] not in index:
                continue
            j = index[target['node']]
            kind = ['translation','rotation','scale'].index(target['path'])
            s = anim['samplers'][channel['sampler']]
            ts = library.accessor(s['input']).ravel()
            raw = library.accessor(s['output'])
            idx = np.searchsorted(ts,times,side='right')
            a = np.clip(idx-1,0,len(ts)-1)
            b = np.clip(idx,0,len(ts)-1)
            mix = np.clip((times-ts[a])/np.maximum(ts[b]-ts[a],1.e-8),0,1)[:,None]
            if s.get('interpolation')=='STEP':
                mix[:] = 0
            if kind==1:
                first,second = raw[a],raw[b]
                sign = np.sum(first*second,axis=1)<0
                second = np.where(sign[:,None],-second,second)
                out[kind][:,j,:] = normalized((1-mix)*first+mix*second)
            else:
                out[kind][:,j,:] = raw[a]*(1-mix)+raw[b]*mix
        return out

    def world(self,state):
        world = matrices(*state)
        for i,p in enumerate(self.parent):
            if p>=0:
                world[i] = world[p] @ world[i]
        return world

    def world_batch(self,states):
        result = np.stack([matrices(*state) for state in zip(*states)])
        for i,p in enumerate(self.parent):
            if p>=0:
                result[:,i] = result[:,p] @ result[:,i]
        return result


def clock(library,anim,rates=(24,30)):
    values = [library.accessor(s['input']).ravel() for s in anim['samplers']]
    start,end = min(float(a[0]) for a in values), max(float(a[-1]) for a in values)
    # Keep the source time origin and both checkers' exact integer/half grids.
    grid = {round(start,8),round(end,8)}
    for fps in rates:
        grid.update(round(step/(2*fps),8) for step in
                    range(math.ceil(start*fps*2-1.e-5),math.floor(end*fps*2+1.e-5)+1))
    times = np.array(sorted(grid),dtype=np.float32)
    times[0],times[-1] = start,end
    return times[np.r_[True,np.diff(times)>1.e-6]]


class Skin:
    def __init__(self,asset,rig):
        p = asset.doc['meshes'][0]['primitives']
        self.parts = [len(asset.accessor(prim['attributes']['POSITION'])) for prim in p]
        points = np.concatenate([asset.accessor(prim['attributes']['POSITION']) for prim in p])
        self.points = np.column_stack((points,np.ones(len(points),dtype=np.float32)))
        self.w = np.concatenate([asset.accessor(prim['attributes']['WEIGHTS_0']) for prim in p])
        self.w = self.w.astype(np.float32)
        self.w /= self.w.sum(axis=1,keepdims=True)
        self.ids = np.concatenate([asset.accessor(prim['attributes']['JOINTS_0']) for prim in p])
        self.local = np.einsum('vkij,vj->vki',rig.inv[self.ids],self.points)*self.w[:,:,None]
        self.faces = np.vstack([asset.accessor(prim['indices']).reshape((-1,3))+start
                                for start,prim in zip(np.r_[0,np.cumsum(self.parts[:-1],dtype=np.int32)],p)])
        self.feet = {}
        self.shares = {}
        for side in ('Left','Right'):
            names = np.asarray(rig.names)[self.ids]
            limb = lambda parts: np.isin(names,[side+n for n in parts])
            feet = ('Foot','ToeBase','Toe_End')
            f = limb(feet)
            keep = f[np.arange(len(self.w)),self.w.argmax(axis=1)]
            self.feet[side] = np.flatnonzero(keep)
            self.shares[side] = ((.22*limb(('UpLeg','Leg',*feet))+
                                 .42*limb(('Leg',*feet))+.36*f)*self.w).sum(axis=1)[keep]

    def posed(self,world):
        return np.einsum('vkij,vkj->vi',world[self.ids,:3,:],self.local)
