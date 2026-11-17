"""Combine animations from two compatible Tripo GLBs without duplicating the mesh."""
import copy, json, struct, sys
from pathlib import Path

def read_glb(path):
    data=Path(path).read_bytes()
    magic,version,length=struct.unpack_from('<4sII',data,0)
    if (magic,version,length)!=(b'glTF',2,len(data)): raise ValueError('Invalid GLB header')
    n,kind=struct.unpack_from('<I4s',data,12)
    if kind!=b'JSON': raise ValueError('Missing JSON chunk')
    doc=json.loads(data[20:20+n]); offset=20+n
    size,kind=struct.unpack_from('<I4s',data,offset)
    if kind!=b'BIN\0': raise ValueError('Missing BIN chunk')
    return doc, bytearray(data[offset+8:offset+8+size])

def main(base_path,extra_path,out_path):
    base,binary=read_glb(base_path); extra,other=read_glb(extra_path)
    for key in ('nodes','skins','meshes','materials','images','textures','scenes'):
        if base.get(key)!=extra.get(key): raise ValueError('Incompatible '+key)
    if len(base['buffers'])!=1 or len(extra['buffers'])!=1: raise ValueError('Expected a single buffer')
    names={x.get('name') for x in base['animations']}; remap={}
    def import_accessor(index):
        if index in remap:return remap[index]
        acc=copy.deepcopy(extra['accessors'][index])
        if 'sparse' in acc or 'bufferView' not in acc: raise ValueError('Unsupported accessor')
        view=copy.deepcopy(extra['bufferViews'][acc['bufferView']])
        if view.get('buffer',0)!=0:raise ValueError('Unsupported buffer')
        start=view.get('byteOffset',0); size=view['byteLength']; binary.extend(b'\0'*((-len(binary))%4))
        view['byteOffset']=len(binary);binary.extend(other[start:start+size]);view['buffer']=0
        acc['bufferView']=len(base['bufferViews']);base['bufferViews'].append(view)
        remap[index]=len(base['accessors']);base['accessors'].append(acc);return remap[index]
    for animation in extra['animations']:
        animation=copy.deepcopy(animation)
        if animation.get('name') in names: raise ValueError('Duplicate clip name')
        for sampler in animation['samplers']:
            sampler['input']=import_accessor(sampler['input']);sampler['output']=import_accessor(sampler['output'])
        base['animations'].append(animation)
    base['buffers'][0]['byteLength']=len(binary)
    blob=json.dumps(base,separators=(',',':')).encode();blob+=b' '*((-len(blob))%4);binary.extend(b'\0'*((-len(binary))%4))
    total=12+8+len(blob)+8+len(binary)
    Path(out_path).write_bytes(struct.pack('<4sII',b'glTF',2,total)+struct.pack('<I4s',len(blob),b'JSON')+blob+struct.pack('<I4s',len(binary),b'BIN\0')+binary)
    print('Combined clips:',', '.join(a['name'] for a in base['animations']))
if __name__=='__main__':
    if len(sys.argv)!=4: raise SystemExit('usage: merge_clips.py BASIC.glb GESTURES.glb OUTPUT.glb')
    main(*sys.argv[1:])
