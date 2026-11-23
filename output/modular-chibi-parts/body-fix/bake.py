"""Bake evaluated Blender poses into selected channels of the original shared GLB."""
import json
import struct
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bodycheck import CLIPS, OUT, SOURCE, Checker, bind, load, posed
from clearance import arms, feet, hand_targets, legs, relax_elbows
from polish import apply as apply_fold_corrections
from tune import set_time
from mathutils import Matrix, Vector
import numpy as np
from io_scene_gltf2.blender.imp.animation_node import BlenderNodeAnim


class MotionFile:
    def __init__(self, path):
        data = path.read_bytes()
        size, = struct.unpack_from('<I',data,12)
        self.doc = json.loads(data[20:20+size])
        self.buffer = bytearray(data[28+size:])
        self.times = {}

    def append(self, values, form):
        data = np.asarray(values,dtype='<f4')
        views,access = self.doc['bufferViews'],self.doc['accessors']
        views.append({'buffer':0,'byteOffset':len(self.buffer),'byteLength':data.nbytes})
        self.buffer.extend(data.tobytes())
        a = {'bufferView':len(views)-1,'componentType':5126,'count':len(data),'type':form}
        if form=='SCALAR':
            a.update(min=[float(data.min())],max=[float(data.max())])
        access.append(a)
        return len(access)-1

    def replace(self, anim, node, path, frames, values):
        channel, = [c for c in anim['channels'] if c['target']=={'node':node,'path':path}]
        # Source samplers can be shared across joints. Replace this binding only.
        times = tuple(frames)
        if times not in self.times:
            self.times[times] = self.append(np.asarray(times)/24,'SCALAR')
        sampler = {'input':self.times[times],
                   'output':self.append(values,'VEC4' if path=='rotation' else 'VEC3'),
                   'interpolation':'LINEAR'}
        assert sum(c['sampler']==channel['sampler'] for c in anim['channels']) == 1
        anim['samplers'][channel['sampler']] = sampler

    def write(self, path):
        self.doc['buffers'][0]['byteLength'] = len(self.buffer)
        js=json.dumps(self.doc,separators=(',',':')).encode()
        js+=b' '*(-len(js)%4)
        chunks=struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(self.buffer),b'BIN\0')+self.buffer
        path.write_bytes(struct.pack('<4sII',b'glTF',2,12+len(chunks))+chunks)


def source_basis():
    # Capture the edit and axis bases used by this Blender version's importer.
    # Inverting the same mappings avoids exporting new joint rest frames.
    frames = {}
    original = BlenderNodeAnim.anim
    def capture(gltf, anim_idx, node_idx):
        node = gltf.vnodes[node_idx]
        if node.type == node.Bone and node_idx not in frames:
            frames[node_idx] = (node.blender_bone_name,node.editbone_trans.copy(),node.editbone_rot.copy(),
                                node.rotation_after.copy(),node.rotation_before.copy(),
                                gltf.loc_gltf_to_blender((1,0,0)).length,
                                Matrix([node.base_scales_to_final_scales([gltf.scale_gltf_to_blender(axis)])[0]
                                        for axis in np.eye(3)]).transposed().inverted())
        return original(gltf,anim_idx,node_idx)
    with patch.object(BlenderNodeAnim,'anim',staticmethod(capture)):
        scene,arm,body,_ = load()
    assert len(frames)==65
    return scene,arm,body,frames


def bake():
    scene,arm,body,bases = source_basis()
    checker=Checker(body)
    source = MotionFile(SOURCE)
    preset = json.loads((OUT/'clearance_keys.json').read_text())
    fold=json.loads((OUT/'fold_keys.json').read_text())
    filepath = OUT/'motion_fixed.glb'
    anims = {a['name']:a for a in source.doc['animations']}
    expected = {}
    channels = {}
    for clip in CLIPS:
        frames = bind(arm,clip)
        cfg = preset[clip]
        assert frames[0]==cfg['frames'][0] and frames[-1]==cfg['frames'][-1]
        frames=cfg['frames']
        values = {}
        changed = set()
        expected[clip] = []
        for f,upper,lower,relax,hips,elbows in zip(frames,cfg['arm_strength'],cfg['knee_glide_mm'],
                                                 cfg['elbow_return'],fold[clip]['hip_mm'],fold[clip]['elbow_deg'],strict=True):
            set_time(scene,f)
            targets=hand_targets(arm)
            ref=posed(body)
            original = {pb.name:(pb.location.copy(),pb.rotation_quaternion.copy(),pb.scale.copy()) for pb in arm.pose.bones}
            legs(arm,lower)
            arms(arm,upper)
            relax_elbows(arm,targets,relax)
            apply_fold_corrections(arm,hips,elbows)
            feet(arm,body,checker,ref)
            expected[clip].append(posed(body).astype(np.float32))
            for idx,(name,et,er,ra,rb,units,scale_inv) in bases.items():
                pb = arm.pose.bones[name]
                t0,q0,s0 = original[name]
                if (pb.scale-s0).length>2.e-6: changed.add((idx,'scale'))
                values.setdefault((idx,'scale'),[]).append(tuple(scale_inv @ pb.scale))
                if (pb.location-t0).length > 1.e-9: changed.add((idx,'translation'))
                if (np.max(np.abs(np.asarray(pb.rotation_quaternion)-np.asarray(q0)))>1.e-7):
                    changed.add((idx,'rotation'))
                t = (ra.inverted() @ (er @ pb.location + et))/units
                q = (ra.inverted() @ er @ pb.rotation_quaternion @ rb.inverted()).normalized()
                values.setdefault((idx,'translation'),[]).append((t.x,t.z,-t.y))
                rots = values.setdefault((idx,'rotation'),[])
                row=np.array((q.x,q.z,-q.y,q.w))
                if rots and np.dot(row,rots[-1])<0: row=-row
                rots.append(row)
        channels[clip]=[]
        for idx,path in sorted(changed):
            assert 'Hand' not in bases[idx][0]
            source.replace(anims[clip],idx,path,frames,values[(idx,path)])
            channels[clip].append([bases[idx][0],path])
        print('BAKE',clip,len(changed),flush=True)
    source.write(filepath)
    scene,arm,body,_=load(filepath)
    errors={}
    for clip in CLIPS:
        fs=bind(arm,clip)
        assert fs[0]==preset[clip]['frames'][0] and fs[-1]==preset[clip]['frames'][-1]
        fs=preset[clip]['frames']
        worst=0
        for i,f in enumerate(fs):
            set_time(scene,f)
            worst=max(worst,float(np.linalg.norm(posed(body)-expected[clip][i],axis=1).max()*1000))
        errors[clip]=worst
        print('ROUNDTRIP',clip,worst,'mm',flush=True)
    assert max(errors.values())<.05, errors
    (OUT/'bake_verification.json').write_text(json.dumps({'changed_channels':channels,'max_vertex_roundtrip_error_mm':errors},indent=2)+'\n')


if __name__=='__main__':
    bake()
