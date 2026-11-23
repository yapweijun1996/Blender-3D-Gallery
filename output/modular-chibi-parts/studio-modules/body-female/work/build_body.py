"""Build the Studio female module in Blender world metres, preserving the proximal surface."""
import bpy
import math
from collections import defaultdict
from pathlib import Path
from mathutils import Matrix, Vector
import numpy as np

OUT = Path(__file__).resolve().parent
DIGITS = ('Index','Middle','Ring','Pinky','Thumb')
CUT = .2862
YC, ZC = -.017, .542
V = Vector
def smooth(a,b,x):
    u=min(1,max(0,(x-a)/(b-a)))
    return u*u*(3-2*u)
def skin(ws):
    ws=sorted(((n,w) for n,w in ws.items() if w>.00011),key=lambda i:-i[1])[:4]
    total=sum(w for _,w in ws)
    return {n:w/total for n,w in ws}
def mixweights(a,b,t):
    return {n:a.get(n,0)*(1-t)+b.get(n,0)*t for n in a.keys()|b.keys()}
def key(p):
    return tuple(round(c,7) for c in p)
def init():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0
    bpy.context.preferences.filepaths.file_preview_type='NONE'
    bpy.ops.import_scene.gltf(filepath=str(OUT.parent/'studio_rigged.glb'))
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    src=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    # Source mesh and armature carry the same change of basis. Bake it once.
    mw=rig.matrix_world.copy()
    positions=[src.matrix_world@v.co for v in src.data.vertices]
    normals=[(src.matrix_world.to_3x3()@n.vector).normalized() for n in src.data.corner_normals]
    rig.parent=None
    rig.matrix_world=Matrix.Identity(4)
    rig.data.transform(mw)
    return rig,src,positions,normals
def body(destination=OUT):
    destination.mkdir(parents=True,exist_ok=True)
    rig,src,points,source_normals=init()
    mesh=src.data
    mesh.calc_loop_triangles()
    uv=mesh.uv_layers.active.data
    material=mesh.materials[0]
    vpos=[]; weights=[]; lookup={}; faces=[]; uv_faces=[]; authored=[]; hand_side=[]
    boundaries={1:set(),-1:set()}
    wrist_colors=[]; wrist_normals=defaultdict(list)
    def vert(p,w):
        k=tuple(round(c,6) for c in p) if abs(abs(p.x)-CUT)<1e-7 else key(p)
        if k not in lookup:
            lookup[k]=len(vpos); vpos.append(V(p)); weights.append(skin(w))
        return lookup[k]
    def face(ids,coords=None,norms=None,side=0):
        if len(set(ids))<3:return
        faces.append(tuple(ids)); uv_faces.append(coords); authored.append(norms);hand_side.append(side)
    def source_weight(v):
        w={src.vertex_groups[g.group].name:g.weight for g in v.groups}
        # Fingers never own forearm skin. Retain the exact total wrist contribution.
        for n in list(w):
            if 'Hand' in n and n[-1].isdigit():
                root=n[:n.index('Hand')+4];w[root]=w.get(root,0)+w.pop(n)
        return w
    oldw=[source_weight(v) for v in mesh.vertices]
    for tri in mesh.loop_triangles:
        raw=[(points[i],uv[l].uv.copy(),source_normals[l],oldw[i]) for i,l in zip(tri.vertices,tri.loops)]
        if all(abs(q[0].x)>CUT and q[0].x*raw[0][0].x>0 for q in raw):continue
        sg=1 if sum(v[0].x for v in raw)>0 else -1
        clipped=[]
        for a,b in zip(raw,raw[1:]+raw[:1]):
            inside=sg*a[0].x<=CUT
            if inside:clipped.append(a)
            if inside != (sg*b[0].x<=CUT):
                t=(sg*CUT-a[0].x)/(b[0].x-a[0].x)
                q=a[0].lerp(b[0],t); q.x=sg*CUT
                clipped.append((q,a[1].lerp(b[1],t),a[2].lerp(b[2],t).normalized(),mixweights(a[3],b[3],t)))
        iv=[vert(q,w) for q,u,n,w in clipped]
        for i,(q,u,n,w) in zip(iv,clipped):
            if abs(abs(q.x)-CUT)<1e-7:
                boundaries[sg].add(i)
                wrist_colors.append((math.atan2(q.z-ZC,q.y-YC),tuple(u)))
                wrist_normals[i].append(n.copy())
        for j in range(1,len(iv)-1):
            order=(0,j,j+1);face([iv[i] for i in order],[clipped[i][1] for i in order],[clipped[i][2] for i in order])
    # Allocate a small free area of the retained body's atlas for the reconstructed hands.
    occupied=np.zeros((128,128),dtype=bool)
    for uvs in uv_faces:
        b=np.asarray(uvs); lo=np.maximum(0,np.floor(b.min(0)*128).astype(int)-1);hi=np.minimum(127,np.ceil(b.max(0)*128).astype(int)+1)
        occupied[lo[1]:hi[1]+1,lo[0]:hi[0]+1]=True
    tile=None
    for width in (8,6,4,3,2):
        for y in range(1,127-width):
            for x in range(1,127-width):
                if not occupied[y:y+width,x:x+width].any():
                    tile=(x*8,y*8,width*8);break
            if tile:break
        if tile:break
    assert tile
    for n in material.node_tree.nodes:
        if n.type!='TEX_IMAGE':continue
        im=n.image; im.scale(1024,1024)
        px=np.empty(1024*1024*4,np.float32); im.pixels.foreach_get(px); px=px.reshape(1024,1024,4)
        tx,ty,tw=tile
        if 'basecolor' in im.name:
            angles=np.array([a for a,u in wrist_colors])
            samples=np.array([px[int(u[1]*1024)%1024,int(u[0]*1024)%1024,:3] for a,u in wrist_colors])
            for j in range(tw):
                ang=2*math.pi*(j-2)/(tw-5)-math.pi
                kernel=np.exp(17*(np.cos(angles-ang)-1)); col=np.average(samples,axis=0,weights=kernel)
                for i in range(tw):
                    f=np.clip((i-2)/(tw-5),0,1);px[ty+j,tx+i,:3]=np.clip(col*(1-.74*f)+samples.mean(0)*.74*f+f*np.array([.009,-.004,-.006]),0,1)
            im.name='Female_BaseColor'
        elif 'normal' in im.name:
            px[ty:ty+tw,tx:tx+tw,:3]=(.5,.5,1);im.name='Female_Normal'
        else:
            px[ty:ty+tw,tx:tx+tw,:3]=(1,.50,.115);im.name='Female_RoughnessMetallic'
        im.pixels.foreach_set(px.reshape(-1));im.update();im.file_format='PNG';im.pack()
    # Use the source knuckle line to roll the wrist into the new palm frame.
    joints={}; hand_axes={}; wrist_adjustments={}
    for sg,side in [(1,'Left'),(-1,'Right')]:
        pre='mixamorig:'+side+'Hand'; base={pre:1}
        knuckle=rig.data.bones[pre+'Pinky1'].head_local-rig.data.bones[pre+'Index1'].head_local
        roll=-math.atan2(knuckle.z,knuckle.y)
        hand_axes[pre]=roll
        C=lambda x,y,z:V((sg*x,y,z))
        def genface(ids):
            face(ids if sg==1 else ids[::-1],side=sg)
        # Palm cross-sections. u spans the fingers, v the palmar/dorsal faces.
        # The thumb exits through an eight-edge window in the radial side.
        xs=[.291,.298,.307,.316,.325,.335,.348]
        widths=[.0242,.027,.0305,.034,.0365,.038,.038]
        thick=[.025,.023,.0196,.0168,.015,.013,.010]
        palm={}
        def pkey(row,j,k):
            ij=(row,j,k)
            if ij in palm:return palm[ij]
            u=(j-4)/4; v=k
            w=widths[row]; h=thick[row]
            y=YC+u*w*(1-.10*abs(v)**2*abs(u)**2)
            z=ZC+h*v*(1-.37*abs(u)**2) + .0009*(1-u*u)
            x=xs[row]-(.0045*abs(u)**2)*smooth(.311,.348,xs[row])
            if row<3:
                # Sample the original wrist section and progressively rotate it.
                angle=math.atan2(z-ZC,y-YC)
                old=sorted(boundaries[sg],key=lambda i:math.atan2(vpos[i].z-ZC,vpos[i].y-YC))
                correction=roll*smooth(CUT,.311,x)
                def angular(i):
                    p=vpos[i]; return abs(math.atan2(math.sin(math.atan2(p.z-ZC,p.y-YC)+correction-angle),math.cos(math.atan2(p.z-ZC,p.y-YC)+correction-angle)))
                ii=min(old,key=angular); q=vpos[ii]
                radius=math.hypot(q.y-YC,q.z-ZC)
                amount=.72*(1-smooth(CUT,.31,x))
                y=(1-amount)*y+amount*(YC+math.cos(angle)*radius)
                z=(1-amount)*z+amount*(ZC+math.sin(angle)*radius)
            w=base
            if row<=2:
                near=min(boundaries[sg],key=lambda i:(V((vpos[i].y,vpos[i].z))-V((y,z))).length_squared)
                w=mixweights(weights[near],base,smooth(CUT,.311,x))
            palm[ij]=vert(C(x,y,z),w)
            return palm[ij]
        # Perimeter counterclockwise as seen from distal +X.
        perimeter=[(j,-1) for j in range(9)]+[(8,0)]+[(j,1) for j in reversed(range(9))]+[(0,0)]
        rings=[[pkey(r,j,k) for j,k in perimeter] for r in range(7)]
        # Join disparate wrist tessellations by monotonically advancing polar angle.
        old=list(boundaries[sg]); new=rings[0]
        angle=lambda i: math.atan2(vpos[i].z-ZC,vpos[i].y-YC)%(2*math.pi)
        old.sort(key=angle);new=sorted(new,key=angle)
        oi=ni=0
        while oi<len(old) or ni<len(new):
            ii=oi%len(old);jj=ni%len(new)
            oa=angle(old[(oi+1)%len(old)])+(2*math.pi if oi+1>=len(old) else 0) if oi<len(old) else math.inf
            na=angle(new[(ni+1)%len(new)])+(2*math.pi if ni+1>=len(new) else 0) if ni<len(new) else math.inf
            if oa<na:
                genface([old[ii],old[(ii+1)%len(old)],new[jj]]); oi+=1
            else:
                genface([old[ii],new[(jj+1)%len(new)],new[jj]]); ni+=1
        for row in range(6):
            for e,(j,k) in enumerate(perimeter):
                nj,nk=perimeter[(e+1)%len(perimeter)]
                if row in (1,2) and j==nj==0:continue
                genface([rings[row][e],rings[row][(e+1)%20],rings[row+1][(e+1)%20],rings[row+1][e]])
        # Reconstruct the radial profile through the retained distal forearm.
        # A matched tangent at the cut prevents the radial heel from forming
        # an abrupt lip when the hand flattens into its palm-down section.
        angles=np.array([math.atan2(vpos[i].z-ZC,vpos[i].y-YC) for i in old])
        radii=np.array([math.hypot(vpos[i].z-ZC,vpos[i].y-YC) for i in old])
        order=np.argsort(angles)
        for row,mix in ((0,.93),(1,.49),(2,.14)):
            for col,i in enumerate(rings[row]):
                q=vpos[i]
                a=math.atan2(q.z-ZC,q.y-YC)
                newang=math.radians(-162+18*col)
                a+=mix*math.atan2(math.sin(newang-a),math.cos(newang-a))
                r=np.interp(a,angles[order],radii[order],period=2*math.pi)
                # Let the heel attain its distal maximum inside the repaired region.
                lower=max(0,-math.sin(a))
                r+=.0013*lower
                target=C(abs(q.x),YC+r*math.cos(a),ZC+r*math.sin(a))
                wrist_adjustments[i]=q.lerp(target,mix)
        def digit_weights(name,s,bounds):
            ns=[pre]+[pre+name+str(i) for i in range(1,5)]
            transitions=[smooth(p-width,p+width,s) for p,width in bounds]
            vals=[1-transitions[0]]+[a-b for a,b in zip(transitions,transitions[1:])]+[transitions[-1]]
            return {n:w for n,w in zip(ns,vals) if w>0}
        for d,name in enumerate(DIGITS):
            if d<4:
                j=2*d
                ring=[pkey(6,j,-1),pkey(6,j+1,-1),pkey(6,j+2,-1),pkey(6,j+2,0),pkey(6,j+2,1),pkey(6,j+1,1),pkey(6,j,1),pkey(6,j,0)]
                start=sum((vpos[i] for i in ring),V())/8
                yaw=math.radians((-9,-3,3,10)[d]);direction=C(math.cos(yaw),math.sin(yaw),-.025).normalized()
                shaft=(.063,.069,.065,.052)[d]; r=(.0077,.0080,.00765,.00665)[d]
                lateral=C(-math.sin(yaw),math.cos(yaw),0); up=direction.cross(lateral)*sg
                pivot=[.003,shaft*.40,shaft*.71,shaft*.95]
                bounds=list(zip(pivot,[.012,.0115,.010,.003]))
            else:
                # Looking down the projecting thumb, the aperture is traversed
                # in its outward winding around the thenar saddle.
                ring=[pkey(1,0,-1),pkey(2,0,-1),pkey(3,0,-1),pkey(3,0,0),pkey(3,0,1),pkey(2,0,1),pkey(1,0,1),pkey(1,0,0)]
                start=sum((vpos[i] for i in ring),V())/8
                start.y-=.0085
                direction=C(.42,-.906,-.060).normalized()
                lateral=C(.906,.42,0).normalized();up=direction.cross(lateral)*sg
                shaft=.050; r=.0097
                pivot=[-.005,.011,.029,.047]
                bounds=list(zip(pivot,[.015,.013,.011,.003]))
            # Joint 4 is a terminal helper. MCP/IP remain the visible thumb hinges.
            chain=[start+direction*s for s in pivot+[shaft+.005]]
            joints[pre+name]=chain
            prev=ring
            for t,rw,rh in [(.075,.97,1.03),(.19,1,1.00),(.31,.965,.94),(.405,.98,.95),(.49,.947,.90),(.625,.89,.85),(.705,.905,.86),(.805,.864,.81),(.88,.83,.77),(.94,.69,.64),(.978,.435,.40)]:
                v=start+direction*(shaft*t)
                # Soft rise at the proximal thumb outlines the two short phalanges.
                v+=up*((.00135 if d==4 else .00055)*math.sin(t*math.pi))
                cur=[]
                count=16 if d==4 and t>=.49 else 8
                for k in range(count):
                    ang=k*2*math.pi/count-3*math.pi/4
                    taper=1-.15*smooth(.18,.89,t) if d==4 else 1
                    q=v+(lateral*(math.cos(ang)*rw*r)+up*(math.sin(ang)*rh*r))*taper
                    if d==4:
                        radial=V((0,-1,0))
                        basepoint=vpos[ring[k*8//count]]+radial*(.0085+shaft*t)
                        q=basepoint.lerp(q,smooth(-.12,.39,t))
                    elif t<.15:
                        q=q.lerp(vpos[ring[k]]+direction*shaft*t,.26)
                    cur.append(vert(q,digit_weights(name,t*shaft,bounds)))
                for k in range(len(prev)):
                    a=k*len(cur)//len(prev);b=((k+1)*len(cur)//len(prev))%len(cur)
                    if len(cur)==len(prev):
                        genface([prev[k],prev[(k+1)%len(prev)],cur[b],cur[a]])
                    else:
                        mid=(a+1)%len(cur)
                        genface([prev[k],prev[(k+1)%len(prev)],cur[mid]])
                        genface([prev[k],cur[mid],cur[a]])
                        genface([prev[(k+1)%len(prev)],cur[b],cur[mid]])
                prev=cur
            tip=vert(start+direction*shaft,digit_weights(name,shaft,bounds))
            for k in range(len(prev)):genface([prev[k],prev[(k+1)%len(prev)],tip])
    for i,q in wrist_adjustments.items():vpos[i]=q
    # Preserve every distinct source vertex dominated by the forearm, including
    # the few dorsal wrist vertices lying distal to the nominal wrist plane.
    anchors={}
    for v,p in zip(mesh.vertices,points):
        if abs(p.x)<=CUT:continue
        strongest=max(v.groups,key=lambda g:g.weight)
        if 'Hand' not in src.vertex_groups[strongest.group].name:anchors[key(p)]=(p,oldw[v.index])
    pinned=set()
    for p,ws in anchors.values():
        best=min((i for i,q in enumerate(vpos) if i not in pinned and abs(q.x)>CUT+.0001),key=lambda i:(vpos[i]-p).length_squared)
        vpos[best]=p.copy();weights[best]=skin(ws);pinned.add(best)
    output=bpy.data.meshes.new('FemaleBody_Surface')
    output.from_pydata(vpos,[],faces);output.update()
    out=bpy.data.objects.new('Body_Female',output);bpy.context.collection.objects.link(out);output.materials.append(material)
    # Original chart and normals survive outside the wrist; the hands share one neutral atlas tile.
    layer=output.uv_layers.new(name='UVMap')
    tx,ty,tw=tile
    for poly,coords,sg in zip(output.polygons,uv_faces,hand_side):
        poly.use_smooth=True
        if coords is None:
            bodyco=[vpos[i] for i in poly.vertices]
            # Both hands reuse the padded skin swatch. Continuous coordinates
            # keep Blender's split-normal deformation continuous across joints.
            coords=[((tx+2+(tw-5)*(.09+5.60*(abs(q.x)-CUT)+1.4*(q.z-ZC)+.29*(q.y-YC)))/1024,
                     (ty+2+(tw-5)*(.52+11.3*(q.z-ZC)+1.18*(q.y-YC)+.31*(abs(q.x)-CUT)))/1024)
                    for q in bodyco]
            raw=[(math.atan2(q.z-ZC,q.y-YC)+math.pi)/(2*math.pi) for q in bodyco]
            if max(raw)-min(raw)>.5:raw=[a+1 if a<.5 else a for a in raw]
            mapped=[]
            for q,a,old_uv in zip(bodyco,raw,coords):
                t=smooth(.299,.326,abs(q.x))
                u=(tx+2+(tw-5)*min(1,max(0,(abs(q.x)-CUT)/.113)))/1024
                v=(ty+2+max(-1.4,min(tw-3.6,(tw-5)*a)))/1024
                mapped.append((u*(1-t)+old_uv[0]*t,v*(1-t)+old_uv[1]*t))
            coords=mapped
        for li,c in zip(poly.loop_indices,coords):layer.data[li].uv=c
    # Calculate offset normals only on the hand; avoid shading a wrist seam.
    normals=[n.vector.copy() for n in output.corner_normals]
    for poly,ns in zip(output.polygons,authored):
        if ns:
            for li,n in zip(poly.loop_indices,ns):normals[li]=n
    seam={i:sum(group,V()).normalized() for i,group in wrist_normals.items()}
    for poly,sg in zip(output.polygons,hand_side):
        if not sg:continue
        for li in poly.loop_indices:
            i=output.loops[li].vertex_index
            p=vpos[i]
            if abs(p.x)>=.301:continue
            distance=lambda j:(p.y-vpos[j].y)**2+(p.z-vpos[j].z)**2
            j=min(boundaries[sg],key=distance)
            original=seam[j]
            normals[li]=original.lerp(normals[li],smooth(CUT,.301,abs(p.x))).normalized()
    output.normals_split_custom_set(normals);output.update()
    for b in rig.data.bones:out.vertex_groups.new(name=b.name)
    for i,ws in enumerate(weights):
        for n,w in ws.items():out.vertex_groups[n].add([i],w,'REPLACE')
    out.parent=None
    mod=out.modifiers.new('Studio skin','ARMATURE');mod.object=rig
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for pre,roll in hand_axes.items():
        hand=rig.data.edit_bones[pre]; hand.use_connect=False
        head=hand.head.copy(); tail=hand.tail.copy();z=hand.z_axis.copy()
        rot=Matrix.Rotation(roll,3,'X')
        hand.tail=head+rot@(tail-head);hand.align_roll(rot@z)
    for pre,chain in joints.items():
        for i in range(4):
            b=rig.data.edit_bones[pre+str(i+1)];b.use_connect=False
            b.head=chain[i];b.tail=chain[i+1]
            b.align_roll(V((0,0,-1)))
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects.remove(src,do_unlink=True)
    for o in list(bpy.context.scene.objects):
        if o not in (out,rig):bpy.data.objects.remove(o,do_unlink=True)
    for ac in list(bpy.data.actions):bpy.data.actions.remove(ac)
    rig.animation_data_clear();rig.name='Female_Rig'
    # The node hierarchy and all non-hand bind transforms are preserved.
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);out.select_set(True);bpy.context.view_layer.objects.active=rig
    opts=dict(export_format='GLB',use_selection=True,export_leaf_bone=False,export_def_bones=False,export_rest_position_armature=True,export_skins=True,export_influence_nb=4,export_tangents=True)
    bpy.ops.export_scene.gltf(filepath=str(destination/'body_female_v1.glb'),export_animations=False,**opts)
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(destination/'body_female_v1.blend'))
    output.calc_loop_triangles()
    print('BODY',len(output.loop_triangles),len(output.vertices),'tile',tile,'roll',hand_axes)
if __name__=='__main__':body()
