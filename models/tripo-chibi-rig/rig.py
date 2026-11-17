import numpy as np,json,struct,sys,pathlib
f=pathlib.Path(sys.argv[1]);raw=f.read_bytes();n=struct.unpack_from('<I',raw,12)[0];d=json.loads(raw[20:20+n]);b=bytearray(raw[28+n:]);a=d['accessors'][0];v=d['bufferViews'][a['bufferView']];P=np.frombuffer(bytes(b),'<f4',count=a['count']*3,offset=v['byteOffset']).reshape(-1,3);h=P[:,1].max();x,y,z=(P/h).T
names=[];C=[];parents=[]
def add(name,xyz,parent=None):
 names.append(name);C.append(np.array(xyz)*float(h));parents.append(names.index(parent) if parent else -1)
add('Hips',(0,.25,0));add('Spine',(0,.33,0),'Hips');add('Chest',(0,.42,0),'Spine');add('Neck',(0,.53,0),'Chest');add('Head',(0,.58,0),'Neck')
for side,s in [('Left',1),('Right',-1)]:
 for nm,pos,par in [('Shoulder',(.045,.50,0),'Chest'),('Arm',(.108,.484,0),side+'Shoulder'),('ForeArm',(.159,.400,.010),side+'Arm'),('Hand',(.187,.335,.027),side+'ForeArm'),('UpLeg',(.077,.259,.014),'Hips'),('Leg',(.081,.157,.025),side+'UpLeg'),('Foot',(.088,.078,.009),side+'Leg'),('ToeBase',(.092,.034,.088),side+'Foot')]:
  add(side+nm,(s*pos[0],pos[1],pos[2]),par)
W=np.zeros((len(P),len(C)),np.float32)
def smooth(a,b,v):
 t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)
def spread(m,knots,coords):
 vals=np.array([np.interp(coords,[i[0] for i in knots],[int(k==j) for k in range(len(knots))]) for j in range(len(knots))])
 for (coord,name),v in zip(knots,vals):W[:,names.index(name)]+=m*v
ax=abs(x);armedge=np.interp(y,[.265,.31,.36,.41,.47,.5,.54],[.164,.151,.146,.138,.115,.104,.12])
arm=smooth(armedge-.008,armedge+.012,ax)*smooth(.25,.277,y)*(1-smooth(.50,.542,y))*smooth(-.105,-.07,z)
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
idx=d['accessors'][3]; vv=d['bufferViews'][idx['bufferView']]; faces=np.frombuffer(bytes(b),'<u4',count=idx['count'],offset=vv['byteOffset']).reshape(-1,3)
unique,inv=np.unique(P,axis=0,return_inverse=True);inv=inv.ravel();ff=inv[faces];edge=np.sort(np.concatenate([ff[:,[0,1]],ff[:,[1,2]],ff[:,[0,2]]]),axis=1);edge=np.unique(edge,axis=0);i,j=edge.T
dist=np.linalg.norm(unique[i]-unique[j],axis=1)/h
graph=coo_matrix((dist,(i,j)),shape=(len(unique),len(unique))).tocsr()
def geod(mask):
 return dijkstra(graph,directed=False,indices=np.unique(inv[mask]),min_only=True)[inv]
armseed=((y>.253)&(y<.339)&(ax>.131))|((y>=.339)&(y<.43)&(ax>.168)&(z>-.07))
bodyseed=(y>.526)|(y<.249)|(ax<.082)|((y<.332)&(ax<.125))|((y>.335)&(z<-.106))
da=geod(armseed);db=geod(bodyseed)
delta=np.zeros_like(arm);reachable=np.isfinite(da)&np.isfinite(db);delta[reachable]=db[reachable]-da[reachable]
arm=np.where(reachable,smooth(-.033,.04,delta),np.where(np.isfinite(da),1,np.where(np.isfinite(db),0,arm)))

# Keep the independent shorts and waistband below the armpit anchored to the pelvis.
boundary=np.interp(y,[.255,.275,.300,.325,.34],[.150,.139,.132,.128,.128])
cutoff=smooth(boundary-.0015,boundary+.0015,ax)
arm*=1-(1-cutoff)*(1-smooth(.333,.365,y))
arm*=smooth(.250,.260,y)
leg=(1-smooth(.222,.277,y))*(1-arm)
torso=1-arm-leg
spread(torso,[(.24,'Hips'),(.341,'Spine'),(.465,'Chest'),(.54,'Neck'),(.58,'Head')],y)
for side,sm in [('Left',x>=0),('Right',x<0)]:
 spread(arm*sm,[(.323,side+'Hand'),(.355,side+'ForeArm'),(.395,side+'ForeArm'),(.426,side+'Arm'),(.477,side+'Arm'),(.514,side+'Shoulder')],y)
 foot=1-smooth(.082,.113,y);toe=foot*smooth(.063,.116,z)
 W[:,names.index(side+'ToeBase')]+=leg*sm*toe;W[:,names.index(side+'Foot')]+=leg*sm*(foot-toe)
 spread(leg*sm*(1-foot),[(.12,side+'Leg'),(.141,side+'Leg'),(.177,side+'UpLeg'),(.275,side+'UpLeg')],y)
J=np.argsort(W,axis=1)[:,-4:][:,::-1].copy();V=np.take_along_axis(W,J,axis=1);V/=V.sum(axis=1)[:,None];assert np.isfinite(V).all()
def accessor(arr,comp,kind,target=None):
 view={'buffer':0,'byteOffset':len(b),'byteLength':arr.nbytes};d['bufferViews'].append(view)
 if target:view['target']=target
 b.extend(arr.tobytes());b.extend(b'\0'*(-len(b)%4))
 d['accessors'].append(dict(bufferView=len(d['bufferViews'])-1,componentType=comp,type=kind,count=len(arr)));return len(d['accessors'])-1
at=d['meshes'][0]['primitives'][0]['attributes'];at['JOINTS_0']=accessor(np.where(V>0,J,0).astype('u1'),5121,'VEC4',34962);at['WEIGHTS_0']=accessor(V.astype('<f4'),5126,'VEC4',34962)
M=np.tile(np.eye(4,dtype='<f4'),(len(C),1,1));M[:,3,:3]=-np.array(C);ibm=accessor(M,5126,'MAT4')
nodes=d['nodes'];nodes[0].update(name='Chibi Visitor',skin=0);first=len(nodes)
for i,(name,c,parent) in enumerate(zip(names,C,parents)):
 node=dict(name=name,translation=(c-(C[parent] if parent>=0 else 0)).tolist());nodes.append(node)
 if parent>=0:nodes[first+parent].setdefault('children',[]).append(first+i)
d['scenes'][0]['nodes'].append(first);d['skins']=[dict(name='Chibi humanoid',joints=list(range(first,len(nodes))),skeleton=first,inverseBindMatrices=ibm)]
d['buffers'][0]['byteLength']=len(b);j=json.dumps(d,separators=(',',':')).encode();j+=b' '*(-len(j)%4);f.with_name('rigged-character.glb').write_bytes(struct.pack('<4sIIII',b'glTF',2,len(j)+len(b)+28,len(j),0x4E4F534A)+j+struct.pack('<II',len(b),0x004E4942)+b);print('bones',len(C),'weighted vertices',len(J))
