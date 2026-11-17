import json,struct,pathlib,numpy as np
import sys
from pathlib import Path
p=Path(sys.argv[1])
directory=Path(sys.argv[2]);directory.mkdir(exist_ok=True)
raw=p.read_bytes();n=struct.unpack_from('<I',raw,12)[0];d=json.loads(raw[20:20+n]);b=raw[28+n:];vs=d['bufferViews']
def view(i):
 v=vs[i];return b[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]
def acc(i):
 a=d['accessors'][i];return np.frombuffer(view(a['bufferView']),dtype={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']],offset=a.get('byteOffset',0)).reshape(a['count'],-1)
P=acc(0);x=np.sort(P[:,0]);g=np.diff(x);gaps=sorted(np.flatnonzero(g>.012),key=lambda k:-g[k])[:2];print([(x[i],x[i+1]) for i in gaps]);assert len(gaps)==2
cut=min(float(x[i]+g[i]/2) for i in gaps);I=acc(3).reshape(-1,3);mask=P[:,0]<cut;assert not np.any(mask[I].any(axis=1)!=mask[I].all(axis=1));idx=I[mask[I[:,0]]];remap=np.cumsum(mask)-1
pieces={};shift=(P[mask].min(axis=0)+P[mask].max(axis=0))/2;shift[1]=0
for i in range(4):
 a=d['accessors'][i];vals=(remap[idx].astype('<u4').reshape(-1,1) if i==3 else acc(i)[mask].copy())
 if i==0: vals-=shift
 if i==3:a['componentType']=5125
 a['count']=len(vals);a['min']=vals.min(axis=0).tolist();a['max']=vals.max(axis=0).tolist();pieces[a['bufferView']]=vals.tobytes()
out=bytearray()
for i,v in enumerate(vs):
 data=pieces.get(i,view(i));v.update(byteOffset=len(out),byteLength=len(data));out.extend(data);out.extend(b'\0'*(-len(out)%4))
d['buffers'][0]['byteLength']=len(out);j=json.dumps(d,separators=(',',':')).encode();j+=b' '*(-len(j)%4);path=directory/'front-character.glb';path.write_bytes(struct.pack('<4sIIII',b'glTF',2,len(j)+len(out)+28,len(j),0x4E4F534A)+j+struct.pack('<II',len(out),0x004E4942)+out);print(path,len(idx))
