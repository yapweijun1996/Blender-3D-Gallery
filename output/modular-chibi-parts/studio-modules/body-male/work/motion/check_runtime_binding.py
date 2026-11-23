"""Replay the original GLB's absolute channels and bind-relative equivalents offline.

This is an independent numerical glTF check inside Blender. It samples one
representative frame per source clip and skins the actual exported positions
against the actual inverse bind matrices, in glTF coordinates. No asset is modified.
"""
from collections import Counter
import hashlib
import json
from math import degrees
from pathlib import Path
import struct
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector
import numpy as np

FRAMES = {'walk':25, 'run':8, 'wave':19, 'jump':9, 'idle':22, 'nod':17, 'dance':40}
DTYPES = {5121:'u1', 5123:'<u2', 5125:'<u4', 5126:'<f4'}
COMPONENTS = {'SCALAR':1, 'VEC2':2, 'VEC3':3, 'VEC4':4, 'MAT4':16}


class GLB:
    def __init__(self, path):
        self.path = Path(path)
        data = self.path.read_bytes()
        self.sha = hashlib.sha256(data).hexdigest()
        json_size = struct.unpack_from('<I', data, 12)[0]
        self.doc = json.loads(data[20:20+json_size])
        self.bin = memoryview(data)[28+json_size:]
        self.nodes = self.doc['nodes']
        self.ids = {n['name']:i for i,n in enumerate(self.nodes) if n.get('name','').startswith('mixamorig:')}
        self.parents = {child:i for i,node in enumerate(self.nodes) for child in node.get('children',())}
        self.rest = []
        for n in self.nodes:
            if 'matrix' in n:
                values=n['matrix']
                mat=Matrix([values[i:i+4] for i in range(0,16,4)]).transposed()
                loc,rot,scale=mat.decompose()
            else:
                x,y,z,w=n.get('rotation',(0,0,0,1))
                loc=Vector(n.get('translation',(0,0,0)))
                rot=Quaternion((w,x,y,z))
                scale=Vector(n.get('scale',(1,1,1)))
            self.rest.append((loc,rot,scale))
        self.rest_world=self.world(self.rest)
        self.encoded={}

    def accessor(self,i):
        if i in self.encoded:return self.encoded[i]
        a=self.doc['accessors'][i]
        view=self.doc['bufferViews'][a['bufferView']]
        dtype=np.dtype(DTYPES[a['componentType']]); width=COMPONENTS[a['type']]
        offset=view.get('byteOffset',0)+a.get('byteOffset',0)
        values=np.ndarray((a['count'],width), dtype, self.bin, offset,
                          strides=(view.get('byteStride',width*dtype.itemsize),dtype.itemsize))
        if a.get('normalized'): values=values.astype(float)/np.iinfo(dtype).max
        self.encoded[i]=values
        return values

    def world(self,trs):
        absolute={}
        def matrix(i):
            if i not in absolute:
                local=Matrix.LocRotScale(*trs[i])
                absolute[i]=matrix(self.parents[i]) @ local if i in self.parents else local
            return absolute[i]
        for i in range(len(self.nodes)): matrix(i)
        return absolute

    def sample(self,action,seconds):
        sample=[list(trs) for trs in self.rest]
        for channel in action['channels']:
            sampler=action['samplers'][channel['sampler']]
            times=self.accessor(sampler['input']).reshape(-1)
            values=self.accessor(sampler['output'])
            i1=min(len(times)-1, int(np.searchsorted(times,seconds)))
            i0=max(0,i1-1)
            mix=np.clip((seconds-times[i0])/(times[i1]-times[i0]),0,1) if i0 != i1 else 0.
            method=sampler.get('interpolation','LINEAR')
            assert method in ('LINEAR','STEP')
            if method=='STEP':
                mix=float(seconds>=times[i1])
            ii=channel['target']['node']; key=channel['target']['path']
            if key=='rotation':
                q0,q1=(Quaternion((v[3],v[0],v[1],v[2])).normalized() for v in (values[i0],values[i1]))
                sample[ii][1]=q0.slerp(q1,mix)
            else:
                sample[ii][0 if key=='translation' else 2]=Vector(values[i0]).lerp(Vector(values[i1]),mix)
        return sample

    def skin(self, world):
        skin,=self.doc['skins']
        inv=self.accessor(skin['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1)
        transform=np.stack([np.array(world[i]) for i in skin['joints']]) @ inv
        result=[]
        for prim in self.doc['meshes'][0]['primitives']:
            attrib=prim['attributes']
            pos=self.accessor(attrib['POSITION']); pos=np.column_stack((pos,np.ones(len(pos))))
            joints=self.accessor(attrib['JOINTS_0']); weights=self.accessor(attrib['WEIGHTS_0'])
            assert 'WEIGHTS_1' not in attrib
            output=np.zeros((len(pos),3))
            for j in range(4):
                output += np.einsum('nij,nj->ni',transform[joints[:,j],:3,:],pos) * weights[:,j,None]
            result.append(output)
        return np.vstack(result)


def transfer(source,target,pose):
    direct=list(target.rest); relative=list(target.rest)
    for name,si in source.ids.items():
        ti=target.ids[name]; s0, sq, ss=source.rest[si]; t0,tq,ts=target.rest[ti]
        loc,rot,scale=pose[si]
        direct[ti]=(loc,rot,scale)
        sr=source.rest_world[si].to_quaternion().normalized()
        tr=target.rest_world[ti].to_quaternion().normalized()
        convert=tr.inverted() @ sr
        sp=source.rest_world[source.parents[si]].to_3x3() if si in source.parents else Matrix.Identity(3)
        tp=target.rest_world[target.parents[ti]].to_3x3() if ti in target.parents else Matrix.Identity(3)
        relative[ti]=(t0+tp.inverted() @ sp @ (loc-s0), tq @ convert @ sq.inverted() @ rot @ convert.inverted(),
                      Vector([ts[j]*scale[j]/ss[j] for j in range(3)]))
    direct=target.world(direct); relative=target.world(relative)
    diff=1000*np.linalg.norm(target.skin(direct)-target.skin(relative),axis=1)
    joint_diff={name:1000*(direct[ti].translation-relative[ti].translation).length for name,ti in target.ids.items()}
    return {'skin_rms_delta_mm':float(np.sqrt(np.mean(diff**2))),'skin_max_delta_mm':float(diff.max()),
            'vertex_count_over_0p5mm_delta':int((diff>.5).sum()),'joint_max_delta_mm':max(joint_diff.values()),
            'joint_max_name':max(joint_diff,key=joint_diff.get)}


def main(body_path,motion_path,folder):
    body=GLB(body_path); source=GLB(motion_path)
    if set(body.ids)!=set(source.ids):raise ValueError('Joint names disagree')
    output={'body_sha256':body.sha,'motion_sha256':source.sha,'blender_version':bpy.app.version_string,
            'method':'Read-only glTF 2.0 sampler interpolation with original glTF node TRS, primitive positions, JOINTS_0, WEIGHTS_0 and inverse bind matrices. Compare blind same-name absolute TRS replacement with bind-relative transfer on this body. Results use metres converted to mm. Nonroot static translations in the source replace the target joint offsets if copied blindly.',
            'world_bind_frames':{},'clips':{},
            'source_neutral_rest_as_absolute_vs_target_rest':transfer(source,body,source.rest)}
    for name in sorted(source.ids):
        si=source.ids[name]; ti=body.ids[name]; sr=source.rest_world[si]; tr=body.rest_world[ti]
        q=tr.to_quaternion().normalized().inverted()@sr.to_quaternion().normalized()
        output['world_bind_frames'][name]={'axis_difference_deg':degrees(2*np.arctan2(np.linalg.norm(tuple(q)[1:]),abs(q.w))),
                                         'joint_head_difference_mm':1000*(tr.translation-sr.translation).length,
                                         'local_translation_difference_mm':1000*(body.rest[ti][0]-source.rest[si][0]).length}
    for clip in source.doc['animations']:
        name=clip['name']; frame=FRAMES[name]; pose=source.sample(clip,frame/24)
        counts=Counter(ch['target']['path'] for ch in clip['channels'])
        if counts != {'rotation':65,'translation':65,'scale':65}:
            raise ValueError(f'Unexpected channels on {name}')
        output['clips'][name]={'frame_24fps':frame,'seconds':frame/24,'counts':counts,**transfer(source,body,pose)}
    output_path=Path(folder)/'runtime_binding.json'; output_path.write_text(json.dumps(output,indent=2)+'\n')
    print('runtime report',output_path,output['source_neutral_rest_as_absolute_vs_target_rest'],flush=True)


if __name__=='__main__':
    main(*sys.argv[sys.argv.index('--')+1:])
