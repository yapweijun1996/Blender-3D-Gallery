"""Rebuild the male module from its Studio GLB; coordinates below are in metres."""
import bpy, math, json, sys
import numpy as np
from mathutils import Matrix, Vector
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[1]
DIGITS = ('Index','Middle','Ring','Pinky','Thumb')
W = .28245
V = Vector
def smooth(a,b,t):
    t=max(0.,min(1.,(t-a)/(b-a)))
    return t*t*(3-2*t)
def normalized(weights):
    top=sorted(((k,v) for k,v in weights.items() if v>.00010), key=lambda kv:-kv[1])[:4]
    total=sum(v for _,v in top)
    return {k:v/total for k,v in top}
def clean_weights(weights):
    scores=defaultdict(float)
    for n,v in weights.items():
        if 'Hand' in n and n[-1].isdigit():scores[n[:-1]]+=v
    if len(scores)>1:
        winner=max(scores,key=scores.get)
        for n in list(weights):
            if n[:-1] in scores and n[:-1]!=winner:
                palm=n.split('Hand')[0]+'Hand'
                weights[palm]=weights.get(palm,0)+weights.pop(n)
    return normalized(weights)
def lerp(a,b,t):return a*(1-t)+b*t
def cyclic_bridge(a,b):
    """Connect ordered sections with different vertex counts without hanging vertices."""
    pairs=[];i=j=0
    while i<len(a) or j<len(b):
        ai=a[i%len(a)];bj=b[j%len(b)]
        ai1=a[(i+1)%len(a)];bj1=b[(j+1)%len(b)]
        left=(i+1)*len(b);right=(j+1)*len(a)
        if left==right:
            pairs.append((ai,ai1,bj1,bj));i+=1;j+=1
        elif left<right:
            pairs.append((ai,ai1,bj));i+=1
        else:
            pairs.append((ai,bj1,bj));j+=1
    return pairs

def main():
    (ROOT/'.build').mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT.parent/'studio_rigged.glb'))
    arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    obj=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.find_armature())
    sys.path.insert(0,str(ROOT / "audit"))
    from repair_source_crossings import repair
    repair(obj)
    mesh=obj.data
    A=arm.matrix_world.copy();M=obj.matrix_world.copy()
    P=[M@v.co for v in mesh.vertices]
    weights=[{obj.vertex_groups[g.group].name:g.weight for g in v.groups} for v in mesh.vertices]
    uv=mesh.uv_layers.active.data
    N=M.to_3x3().inverted().transposed()
    normals=[(N@n.vector).normalized() for n in mesh.corner_normals]
    tris=[(tuple(f.vertices),[V(uv[l].uv) for l in f.loop_indices],[normals[l] for l in f.loop_indices]) for f in mesh.polygons]
    mat=mesh.materials[0]
    arm.parent=None;arm.matrix_world=Matrix.Identity(4)
    arm.data.transform(A)
    obj.parent=arm;obj.matrix_parent_inverse=Matrix.Identity(4);obj.matrix_basis=Matrix.Identity(4)
    for pb in arm.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    for ob in list(bpy.context.scene.objects):
        if ob not in (obj,arm):bpy.data.objects.remove(ob,do_unlink=True)
    for ob in (arm,obj):ob.hide_set(False)
    arm.name='Armature';obj.name='Body_Male';arm.data.name='Male_Mixamo'
    B=arm.data.bones
    wrist={s:B['mixamorig:'+side+'Hand'].head_local.copy() for s,side in [(1,'Left'),(-1,'Right')]}
    skinUV=[sum(uvs,V((0,0)))/3 for ids,uvs,_ in tris if all(abs(P[i].x)>W+.005 for i in ids)]
    wrist_samples=[]
    for ids,uvs,_ in tris:
        for j in range(3):
            q,r=P[ids[j]],P[ids[(j+1)%3]]
            if (abs(q.x)-W)*(abs(r.x)-W)>=0:continue
            amount=(W-abs(q.x))/(abs(r.x)-abs(q.x))
            v=q.lerp(r,amount); c=wrist[1 if q.x>0 else -1]
            angle=(math.atan2(v.z-c.z,v.y-c.y)/(2*math.pi))%1.
            u=uvs[j].lerp(uvs[(j+1)%3],amount)
            wrist_samples.append((angle,list(u)))
    # A narrow guttered strip fits two continuously sampled skin tones in each shared PBR atlas.
    for im in list(bpy.data.images):
        if not im.packed_file:continue
        name=im.name.lower()
        im.scale(1000,1024)
        src=np.empty(1000*1024*4,np.float32);im.pixels.foreach_get(src);src=src.reshape(1024,1000,4)
        uv_xy=np.array(skinUV)
        samples=src[(uv_xy[:,1]*1024).astype(int)%1024,(uv_xy[:,0]*1000).astype(int)%1000,:3]
        color=np.median(samples,axis=0)
        if 'normal' in name:
            name='Body_Male_Normal';color=np.array([.5,.5,1.])
        elif 'basecolor' in name:name='Body_Male_BaseColor'
        else:name='Body_Male_MetallicRoughness'
        target=np.empty((1024,1024,4),np.float32);target[:,:1000]=src
        target[:,1000:1004]=src[:,-1:, :]
        target[:,1004:,:3]=color
        target[:,1004:,3]=1
        if 'Normal' not in name:
            theta=np.array([k for k,u in wrist_samples])
            coords=np.array([u for k,u in wrist_samples])
            samples=src[(coords[:,1]*1024).astype(int)%1024,(coords[:,0]*1000).astype(int)%1000,:3]
            diff=np.abs(np.arange(1024)[:,None]/1024-theta)
            kernel=np.exp(-(np.minimum(diff,1-diff)/.038)**2)
            wrist_colour=(kernel@samples)/kernel.sum(1)[:,None]
            for col in range(1003,1024):
                t=smooth(1005,1019,col)
                target[:,col,:3]=wrist_colour*(1-t)+color*t
        if 'Normal' in name:
            tangent=target[:,:,:3]*2-1
            target[:,:,:3]=.5+.5*tangent/np.maximum(np.linalg.norm(tangent,axis=2,keepdims=True),1.e-6)
        im.scale(1024,1024);im.pixels.foreach_set(target.ravel());im.update()
        im.name=name;im.filepath_raw='//'+name+'.png';im.file_format='PNG';im.pack()
    pos=[];ws=[];faces=[];fuv=[];fnorm=[];table={}
    def vertex(q,w):
        key=tuple(round(k,6) for k in q)
        if key not in table:
            table[key]=len(pos);pos.append(V(q));ws.append(clean_weights(w.copy()))
        return table[key]
    def face(ids,uvs=None,norm=None):
        if len(set(ids))<3:return
        faces.append(tuple(ids));fuv.append(uvs);fnorm.append(norm)
    def clip(poly,sign):
        out=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            da,db=sign*a[0].x-W,sign*b[0].x-W
            if da<=0:out.append(a)
            if (da<0 and db>0) or (da>0 and db<0):
                t=da/(da-db);q=a[0].lerp(b[0],t);q.x=sign*W
                w={n:lerp(a[1].get(n,0),b[1].get(n,0),t) for n in a[1].keys()|b[1].keys()}
                out.append((q,w,a[2].lerp(b[2],t),a[3].lerp(b[3],t).normalized()))
        return out
    for ids,uvs,ns in tris:
        poly=[(P[i],weights[i],V((u.x*1000/1024,u.y)),n) for i,u,n in zip(ids,uvs,ns)]
        for s in (1,-1):
            if poly and max(s*p[0].x for p in poly)>W:poly=clip(poly,s)
        for j in range(1,len(poly)-1):
            sub=[poly[i] for i in (0,j,j+1)]
            face([vertex(q,w) for q,w,u,n in sub],[u for q,w,u,n in sub],[n for q,w,u,n in sub])
    # Remove sub-epsilon stray digit weights from the unmodified forearm, with a continuous wrist binding.
    for i,q in enumerate(pos):
        for n in list(ws[i]):
            if 'Hand' in n and n[-1].isdigit():
                palm=n.split('Hand')[0]+'Hand'
                ws[i][palm]=ws[i].get(palm,0)+ws[i].pop(n)
        ws[i]=normalized(ws[i])
    plans={};manifest={}
    for sg,side in ((1,'Left'),(-1,'Right')):
        pre='mixamorig:'+side+'Hand';wrist_q=wrist[sg]
        cy=wrist_q.y;cz=wrist_q.z
        def point(x,y,z):return V((sg*x,cy+y,cz+z))
        def add(x,y,z,w=None):return vertex(point(x,y,z),w or {pre:1})
        # The actual wrist section is retained. Its distal copy rolls the Studio section
        # into the new palm frame. Interpolate its order around the perimeter to avoid a
        # spiral at the arm attachment. Source wrist vertices remain numerically identical.
        rim=[i for i,q in enumerate(pos) if abs(q.x-sg*W)<8e-8]
        def angle(i):return math.atan2((pos[i].z-cz)/.029,(pos[i].y-cy)/.032)%(2*math.pi)
        rim.sort(key=angle)
        def generated(ids):
            # Face winding is normalized by bmesh after assembling the two mirrored hands.
            face(ids)
        # The original section is nearly circular. Follow the -90° material rotation
        # through geometric section correspondence, then round it into the palmar section.
        # Intermediate section uses corresponding radial samples, avoiding helical quads.
        r0=[]
        for i in rim:
            v=pos[i];u=angle(i)
            # Sample the source cross-section after rotation about X.
            src=min(rim,key=lambda j:abs(math.atan2(math.sin(angle(j)-u-math.pi/2),math.cos(angle(j)-u-math.pi/2))))
            v0=pos[src]-wrist_q
            rotated=V((v0.z,-v0.y))
            y=(v.y-cy)*.88+rotated.x*.12;z=(v.z-cz)*.88+rotated.y*.12
            r0.append(add(W+.0045,y*.997,z*.987))
        for f in cyclic_bridge(rim,r0):generated(f)
        X=[.294,.306,.318,.330,.345]
        wide=[.0325,.0345,.036,.037,.0355]
        thick=[.0262,.0221,.0189,.015,.0107]
        base={}
        def grid(i,j,k):
            key=(i,j,k)
            if key in base:return base[key]
            u=(j-4)/4
            across=wide[i]*u
            x=X[i]-(.0035*u*u if i>=3 else 0)
            z0=-.0008*(1-u*u)
            height=thick[i]*(1-(.69 if i==0 else .58 if i==1 else .46)*abs(u)**2)
            if i==4:
                # A shallow scallop separates adjacent metacarpal heads.
                height*=1.0 if j%2 else .79
            if k>0:z=z0+height
            elif k<0:z=z0-height*(1.11 if i<4 else 1.0)
            else:z=z0
            base[key]=add(x,across,z)
            return base[key]
        for i in range(4):
            for j in range(8):
                for k in (-1,1):generated([grid(i,j,k),grid(i+1,j,k),grid(i+1,j+1,k),grid(i,j+1,k)])
            for j in (0,8):
                if j==0 and i in (0,1):continue
                for k in (-1,0):generated([grid(i,j,k),grid(i+1,j,k),grid(i+1,j,k+1),grid(i,j,k+1)])
        rear=[grid(0,j,k) for k in (-1,1) for j in range(9)]+[grid(0,0,0),grid(0,8,0)]
        # Zipper by actual polar angle; the triangulated wrist section is not uniformly sampled.
        def zip_angle(a,b):
            def theta(ids):
                yy=np.array([[pos[i].y,pos[i].z] for i in ids]);mid=(yy.max(0)+yy.min(0))/2
                yy=(yy-mid)/(yy.max(0)-mid)
                return sorted((math.atan2(z,y)%(2*math.pi),i) for i,(y,z) in zip(ids,yy))
            a=theta(a);b=theta(b);i=j=0
            while i<len(a) or j<len(b):
                n=(a[(i+1)%len(a)][0]+(2*math.pi if i+1>=len(a) else 0)) if i<len(a) else 99
                m=(b[(j+1)%len(b)][0]+(2*math.pi if j+1>=len(b) else 0)) if j<len(b) else 99
                aa=a[i%len(a)][1];bb=b[j%len(b)][1]
                if n<m:generated([aa,a[(i+1)%len(a)][1],bb]);i+=1
                else:generated([aa,b[(j+1)%len(b)][1],bb]);j+=1
        zip_angle(r0,rear)
        for di,d in enumerate(DIGITS):
            thumb=d=='Thumb'
            if thumb:
                # The radial saddle spans two rows so opposing the thumb doesn't pull the index web.
                rootring=[grid(0,0,0),grid(0,0,1),grid(1,0,1),grid(2,0,1),grid(2,0,0),grid(2,0,-1),grid(1,0,-1),grid(0,0,-1)]
                root=point(.305,-.040,-.001)
                aim=V((sg*.52,-.845,-.12)).normalized()
                length=.0585;radius=.0098;dv=.0100
                stations=[.025,.33,.68,1.0,1.08]
                radii=[.94,1.04,1.0,.94,.94,.88,.80,.65,.40]
                fractions=[.12,.22,.36,.49,.57,.68,.80,.90,.97]
                count=12
            else:
                j=di*2
                rootring=[grid(4,j+2,0),grid(4,j+2,1),grid(4,j+1,1),grid(4,j,1),grid(4,j,0),grid(4,j,-1),grid(4,j+1,-1),grid(4,j+2,-1)]
                root=(pos[grid(4,j+1,1)]+pos[grid(4,j+1,-1)])/2
                yaw=(-.21,-.067,.067,.20)[di]
                aim=V((sg*math.cos(yaw),math.sin(yaw),-.027)).normalized()
                length=(.067,.073,.069,.056)[di]
                radius=(.0078,.0081,.0078,.0069)[di];dv=radius*1.04
                stations=[.035,.42,.72,1.0,1.08]
                radii=[1.04,.98,.97,.94,.90,.86,.79,.64,.40]
                fractions=[.08,.22,.34,.43,.56,.68,.76,.89,.97]
                count=10 if di<2 else 8
            lateral=V((-aim.y*sg,aim.x*sg,0)).normalized()
            if thumb:lateral=-lateral
            up=V((0,0,1));up=(up-aim*aim.dot(up)).normalized()
            # Starting phase is given by the socket's first point in the local cross-section.
            def phi(i):
                q=pos[i]-root
                return math.atan2(q.dot(up)/dv,q.dot(lateral)/radius)%(2*math.pi)
            phase=phi(rootring[0]);rootring=sorted(rootring,key=lambda i:(phi(i)-phase+1e-7)%(2*math.pi))
            chain=[root+aim*(length*u) for u in stations]
            for pivot in chain[:3]:
                if not thumb:pivot.z-=.0053
            if thumb:
                for i in rootring:ws[i]={pre:.83,pre+d+'1':.17}
            plans[pre+d]=(chain,thumb,sg)
            prev=rootring
            for ring_no,(t,rad) in enumerate(zip(fractions,radii)):
                if ring_no==4 or (di in (2,3) and ring_no==1):continue
                # Triangles at each hinge interpolate two neighbouring phalanges.
                if thumb:
                    gates=[(.16,.52),(.48,.86)]
                else:gates=[(.20,.62),(.53,.92)]
                g1,g2=(smooth(a,b,t) for a,b in gates)
                flex= smooth(-.09,.21,t) if not thumb else smooth(-.14,.16,t)
                if thumb:
                    # First bone spans the basal metacarpal, second and third the visible segments.
                    weights_ring={pre:1-flex,(pre+d+'1'):flex*(1-g1),(pre+d+'2'):flex*(g1-g2),(pre+d+'3'):flex*g2}
                else:weights_ring={pre:1-flex,pre+d+'1':flex*(1-g1),pre+d+'2':flex*(g1-g2),pre+d+'3':flex*g2}
                ring=[]
                for k in range(count):
                    a=phase+2*math.pi*k/count
                    q=root+aim*(length*t)+lateral*(radius*rad*math.cos(a))+up*(dv*rad*math.sin(a))
                    ring.append(vertex(q,weights_ring))
                for f in cyclic_bridge(prev,ring):generated(f)
                prev=ring
            end=vertex(root+aim*length,{pre+d+'3':1.0})
            for i in range(len(prev)):generated([prev[i],prev[(i+1)%len(prev)],end])
            manifest[pre+d]={'root':list(root),'tip':list(root+aim*length),'shaft':list(aim),'radius_m':radius,'joints':[list(p) for p in chain]}
        # Indicate actual palmar roll with the wrist bone as well as the repaired surface.
    # Carry the actual skin blend from each forearm section across the carpus.
    # Otherwise the first generated loop stretches into a narrow cuff during a wave/run.
    for sg,side in ((1,'Left'),(-1,'Right')):
        pre='mixamorig:'+side+'Hand'
        fore='mixamorig:'+side+'ForeArm'
        ring=[j for j,q in enumerate(pos) if abs(sg*q.x-W)<.000001]
        cy,cz=wrist[sg].y,wrist[sg].z
        angles=[math.atan2(pos[j].z-cz,pos[j].y-cy) for j in ring]
        for i,q in enumerate(pos):
            offset=sg*q.x-W
            if offset<.000001 or offset>=.035:continue
            theta=math.atan2(q.z-cz,q.y-cy)
            nearest=min(range(len(ring)),key=lambda k:abs(math.atan2(math.sin(theta-angles[k]),math.cos(theta-angles[k]))))
            w=ws[ring[nearest]].get(fore,0)*(1-smooth(0,.035,offset))
            w*=ws[i].get(pre,0)
            if w>.0001:
                ws[i][pre]-=w;ws[i][fore]=w;ws[i]=normalized(ws[i])
    rebuilt=bpy.data.meshes.new('Body_Male_Surface');rebuilt.from_pydata(pos,[],faces);rebuilt.update()
    obj.data=rebuilt;rebuilt.materials.append(mat);mat.name='Male_Body_PBR'
    tex=rebuilt.uv_layers.new(name='UVMap')
    oldnormal={}
    for f,uvs,ns in zip(rebuilt.polygons,fuv,fnorm):
        f.use_smooth=True
        for k,li in enumerate(f.loop_indices):
            if ns:tex.data[li].uv=uvs[k]
            else:
                q=pos[f.vertices[k]];c=wrist[1 if q.x>0 else -1]
                # The whole distal hand shares a flat skin texel to preserve continuous
                # deformed normals at every finger socket in a default glTF import.
                u=1005+14*smooth(W,W+.022,abs(q.x))
                v=(math.atan2(q.z-c.z,q.y-c.y)/(2*math.pi))%1.
                tex.data[li].uv=(u/1024,.5+(v-.5)*(1-smooth(W,W+.012,abs(q.x))))
            if ns:oldnormal[li]=ns[k]
    for b in arm.data.bones:
        if b.name not in obj.vertex_groups:obj.vertex_groups.new(name=b.name)
    for i,w in enumerate(ws):
        for n,weight in w.items():obj.vertex_groups[n].add([i],weight,'REPLACE')
    import bmesh
    bm=bmesh.new();bm.from_mesh(rebuilt);bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:]);bm.to_mesh(rebuilt);bm.free()
    # Recover imported loop normals by face and position after generated faces were oriented.
    nlist=[n.vector.copy() for n in rebuilt.corner_normals]
    for f,ids,ns in zip(rebuilt.polygons,faces,fnorm):
        if ns:
            src=dict(zip(ids,ns))
            for li in f.loop_indices:nlist[li]=src[rebuilt.loops[li].vertex_index]
    source_rim=defaultdict(list)
    for f,ns in zip(rebuilt.polygons,fnorm):
        if ns:
            for li in f.loop_indices:
                i=rebuilt.loops[li].vertex_index
                if abs(abs(pos[i].x)-W)<.000001:source_rim[i].append(nlist[li])
    for f,ns in zip(rebuilt.polygons,fnorm):
        if not ns:
            for li in f.loop_indices:
                i=rebuilt.loops[li].vertex_index;q=pos[i]
                if abs(q.x)>W+.012:continue
                closest=min((j for j in source_rim if pos[j].x*q.x>0),key=lambda j:(pos[j]-q).length)
                nr=sum(source_rim[closest],V()).normalized()
                nlist[li]=nr.lerp(nlist[li],smooth(W,W+.012,abs(q.x))).normalized()
    rebuilt.normals_split_custom_set(nlist)
    bpy.context.view_layer.objects.active=arm;arm.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for pre,(chain,thumb,sg) in plans.items():
        guide=V((sg*.82,.51,-.48)) if thumb else V((0,0,-1))
        bs=[arm.data.edit_bones[pre+str(i)] for i in range(1,5)]
        for b in bs:b.use_connect=False
        for j,b in enumerate(bs):
            b.head=chain[j];b.tail=chain[j+1];b.align_roll(guide)
    for side in ('Left','Right'):
        b=arm.data.edit_bones['mixamorig:'+side+'Hand']
        b.align_roll(V((0,0,-1)))
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()
    sys.path.insert(0,str(ROOT/'motion'))
    from align_motion_rest import align_body_motion_rest
    align_body_motion_rest(arm,ROOT.parents[4]/'models/tripo-chibi-motion/motion.glb')
    bpy.context.preferences.filepaths.save_version=0;bpy.context.preferences.filepaths.file_preview_type='NONE'
    (ROOT/'.build'/'landmarks.json').write_text(json.dumps(manifest))
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'.build'/'body_raw.blend'))
    print('built',len(pos),'vertices',sum(len(f)-2 for f in faces),'triangles',flush=True)

if __name__=='__main__':main()
