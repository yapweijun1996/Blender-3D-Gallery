"""Replace only authored quaternion sample bytes, using the Blender importer bases."""
import json
import struct
import sys
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from arms import apply_arm
from io_scene_gltf2.blender.imp.animation_node import BlenderNodeAnim

def bank():
    bases={}
    orig=BlenderNodeAnim.anim
    def capture(gltf,anim_index,node_index):
        n=gltf.vnodes[node_index]
        if n.type==n.Bone and node_index not in bases:
            bases[node_index]=(n.blender_bone_name,n.editbone_rot.copy(),n.rotation_after.copy(),n.rotation_before.copy())
        return orig(gltf,anim_index,node_index)
    with patch.object(BlenderNodeAnim,'anim',staticmethod(capture)):
        scene,arm,body,actions=load()
    assert len(bases)==65
    return scene,arm,body,actions,bases

def bake():
    scene,arm,body,actions,bases=bank()
    angles=json.loads((OUT/'arm_angles.json').read_text())
    src=SOURCE.read_bytes(); data=bytearray(src)
    json_size,=struct.unpack_from('<I',data,12)
    start=28+json_size
    doc,_=chibi.glb(SOURCE)
    aset={a['name']:a for a in doc['animations']}
    used={s['output'] for a in aset.values() for s in a['samplers']}
    assert len(used)==sum(len(a['samplers']) for a in aset.values())
    checks={}; expected={}
    for clip,last in CLIPS.items():
        chibi.bind(arm,actions[clip])
        channels={}
        for ch in aset[clip]['channels']:
            idx=ch['target']['node']
            if ch['target']['path']!='rotation':continue
            name,et,ra,rb=bases[idx]
            acc=doc['accessors'][aset[clip]['samplers'][ch['sampler']]['output']]
            view=doc['bufferViews'][acc['bufferView']]
            assert acc['type']=='VEC4' and acc['count']==last+1 and acc['componentType']==5126
            channels[name]=(np.ndarray((last+1,4),dtype='<f4',buffer=data,
                           offset=start+view.get('byteOffset',0)+acc.get('byteOffset',0),
                           strides=(view.get('byteStride',16),4)),et,ra,rb)
        edits=set()
        expected[clip]=[]
        for f in range(last+1):
            at(scene,f)
            original={pb.name:pb.rotation_quaternion.copy() for pb in arm.pose.bones}
            for s,d in zip(SIDES,angles[clip][f]):apply_arm(arm,s,d)
            expected[clip].append(posed(body).copy())
            for name,(rows,et,ra,rb) in channels.items():
                q=arm.pose.bones[name].rotation_quaternion
                if max(abs(a-b) for a,b in zip(q,original[name]))<1.e-7:continue
                rot=(ra.inverted()@et@q@rb.inverted()).normalized()
                value=np.array([rot.x,rot.z,-rot.y,rot.w])
                rows[f]=value if rows[f]@value>=0 else -value
                edits.add(name)
        checks[clip]={'changed_rotation_samplers':sorted(edits)}
    FIXED.write_bytes(data)
    scene,arm,body,actions=load(FIXED)
    for clip,last in CLIPS.items():
        chibi.bind(arm,actions[clip])
        worst=0
        for f in range(last+1):
            at(scene,f)
            worst=max(worst,float(np.linalg.norm(posed(body)-expected[clip][f],axis=1).max()*1000))
        checks[clip]['max_roundtrip_vertex_error_mm']=worst
        print('BAKE',clip,checks[clip],flush=True)
        assert worst<.01
    (OUT/'bake_verification.json').write_text(json.dumps(checks,indent=2)+'\n')

if __name__=='__main__':bake()
