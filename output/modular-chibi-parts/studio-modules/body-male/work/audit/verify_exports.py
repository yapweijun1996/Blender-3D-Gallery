"""Independent world-space audit of the exported Studio male module and gesture library."""
from collections import Counter, deque
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
REFERENCE = WORK.parents[2]/'hand-gestures-astra'/'round2'
sys.dont_write_bytecode = True
sys.path.insert(0, str(REFERENCE))
from hand_surface import nearest as disjoint_distance
from mathutils.geometry import intersect_ray_tri

DIGITS = ('Index', 'Middle', 'Ring', 'Pinky', 'Thumb')
GESTURES = ('fist','open_relaxed','point','thumbs_up','peace','ok','grip_small','pinch','open_wide')
WRIST = .28245

def rounded(a, n=6):
    return np.round(np.asarray(a,dtype=float),n).tolist()

def unit(a):
    a=np.asarray(a,dtype=float)
    length=np.linalg.norm(a)
    return a/max(length,1e-15)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def parse(path):
    raw=path.read_bytes()
    glb, version, full, n, typ=struct.unpack_from('<4sIIII',raw)
    assert glb==b'glTF' and version==2 and len(raw)==full and typ==0x4E4F534A
    return json.loads(raw[20:20+n]),raw[28+n:]

def import_asset(path):
    ids=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path),bone_heuristic='BLENDER')
    return [o for o in bpy.data.objects if o not in ids]

def verts(body, evaluated=False):
    if evaluated:
        body=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    points=np.empty(len(body.data.vertices)*3,np.float32)
    body.data.vertices.foreach_get('co',points)
    m=np.asarray(body.matrix_world)
    return points.reshape(-1,3)@m[:3,:3].T + m[:3,3]

def geometry(body):
    points=verts(body)
    body.data.calc_loop_triangles()
    triangles=[tuple(f.vertices) for f in body.data.loop_triangles]
    keys=[tuple(round(float(c),6) for c in p) for p in points]
    signature=[frozenset(keys[i] for i in f) for f in triangles]
    return points,triangles,signature

def coplanar_overlaps(points,tris,keys):
    """Catch coincident triangular interiors that a transverse BVH crossing misses."""
    xyz=np.asarray(points,dtype=float)[np.asarray(tris)]
    lo=xyz.min(1);hi=xyz.max(1)
    low=np.floor(lo/.018).astype(int);high=np.floor(hi/.018).astype(int)
    cells={}
    for i,(a,b) in enumerate(zip(low,high)):
        for x in range(a[0],b[0]+1):
            for y in range(a[1],b[1]+1):
                for z in range(a[2],b[2]+1):cells.setdefault((x,y,z),[]).append(i)
    count=len(tris)
    pair_codes=[]
    idx_cache={}
    for cell in cells.values():
        k=len(cell)
        if k<2:continue
        if k not in idx_cache:idx_cache[k]=np.triu_indices(k,1)
        a,b=idx_cache[k];ids=np.asarray(cell,dtype=np.int32)
        pair_codes.append(ids[a]*count+ids[b])
    pair=np.unique(np.concatenate(pair_codes));aa=pair//count;bb=pair%count
    boxed=((lo[aa]-1e-10<=hi[bb])&(lo[bb]-1e-10<=hi[aa])).all(1)
    a,b=aa[boxed],bb[boxed]
    n=np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]);area=np.linalg.norm(n,axis=1)
    n/=np.maximum(area[:,None],1e-22)
    parallel=(np.abs((n[a]*n[b]).sum(1))>1-1e-12)&(area[a]>1e-12)&(area[b]>1e-12)
    a,b=a[parallel],b[parallel]
    dist=np.abs(((xyz[b]-xyz[a,0:1])*n[a,None]).sum(2)).max(1)
    dist2=np.abs(((xyz[a]-xyz[b,0:1])*n[b,None]).sum(2)).max(1)
    pairs=[(int(i),int(j)) for i,j in zip(a[(dist<2e-9)&(dist2<2e-9)],b[(dist<2e-9)&(dist2<2e-9)]) if keys[i].isdisjoint(keys[j])]
    if not pairs:return []
    a,b=np.asarray(pairs).T
    edges=np.concatenate([np.roll(xyz[a],-1,axis=1)-xyz[a],np.roll(xyz[b],-1,axis=1)-xyz[b]],axis=1)
    axes=np.cross(n[a,None],edges)
    axes/=np.maximum(np.linalg.norm(axes,axis=2,keepdims=True),1e-20)
    d1=np.einsum('pik,pjk->pij',xyz[a]-xyz[a,0:1],axes)
    d2=np.einsum('pik,pjk->pij',xyz[b]-xyz[a,0:1],axes)
    overlap=np.minimum(d1.max(1),d2.max(1))-np.maximum(d1.min(1),d2.min(1))
    return [q for q,ok in zip(pairs,overlap.min(1)>2e-9) if ok]

def collisions(points,tris,keys,regions,labels=None):
    bvh=BVHTree.FromPolygons(points.tolist(),tris,all_triangles=True)
    hits=sorted((a,b) for a,b in bvh.overlap(bvh) if a<b and not keys[a]&keys[b])
    coplanar=coplanar_overlaps(points,tris,keys)
    hits=sorted(set(hits)|set(coplanar))
    return hits,{'coplanar_interiors':len(coplanar),'whole_body':len(hits),'left_hand_or_wrist':sum(1 in (regions[a],regions[b]) for a,b in hits),
                 'right_hand_or_wrist':sum(-1 in (regions[a],regions[b]) for a,b in hits),
                 'nonhand_only':sum(not(regions[a] or regions[b]) for a,b in hits),
                 'regions':dict(Counter('/'.join(sorted([labels[a],labels[b]])) for a,b in hits)) if labels is not None else {},
                 'face_indices':hits}

def check_asset(path,gesture=False):
    d,buf=parse(path)
    summary={'sha256':digest(path),'bytes':path.stat().st_size,'meshes':len(d.get('meshes',[])),
             'skins':len(d.get('skins',[])),'joints_per_skin':[len(s['joints']) for s in d.get('skins',[])],
             'triangles':sum(d['accessors'][pr['indices']]['count']//3 for m in d.get('meshes',[]) for pr in m['primitives']),
             'animations':len(d.get('animations',[])),'materials':len(d.get('materials',[])),'textures':[]}
    for im in d.get('images',[]):
        vv=d['bufferViews'][im['bufferView']]; data=buf[vv.get('byteOffset',0):vv.get('byteOffset',0)+vv['byteLength']]
        # Use actual decoded Blender image datablocks for non-PNG formats in the main report.
        size=list(struct.unpack_from('>II',data,16)) if data[:8]==b'\x89PNG\r\n\x1a\n' else None
        summary['textures'].append({'name':im.get('name',''),'mime':im['mimeType'],'byte_count':len(data),'size':size})
    if not gesture:return summary
    summary['clips']={}
    for anim in d.get('animations',[]):
        n=anim['name']; side='Left' if n.endswith('_L') else 'Right'; pre='mixamorig:'+side+'Hand'
        channels=[];bad=[]
        for c in anim['channels']:
            node=d['nodes'][c['target']['node']]['name']
            typ=c['target']['path']; s=anim['samplers'][c['sampler']]
            time=d['accessors'][s['input']]; cnt=d['accessors'][s['output']]['count']
            ch=dict(bone=node,path=typ,input_count=time['count'],output_count=cnt,time_min=time['min'],time_max=time['max'])
            channels.append(ch)
            if node not in {pre+dig+str(k) for dig in DIGITS for k in range(1,5)} or typ not in ('rotation','scale') or time['count']!=1 or cnt!=1:bad.append(ch)
        summary['clips'][n]={'channels':len(channels),'paths':dict(Counter(ch['path'] for ch in channels)),'invalid':bad,
                             'sample_times':sorted({tuple(ch['time_min']+ch['time_max']) for ch in channels})}
    return summary

def nearest(points,aa,bb):
    """Use the complete disjoint-triangle routine and handle interior crossings explicitly."""
    points=np.asarray(points,dtype=float)
    pts=points.tolist()
    trees=[BVHTree.FromPolygons(pts,faces,all_triangles=True) for faces in (aa,bb)]
    overlap=trees[0].overlap(trees[1])
    result=disjoint_distance(points,aa,bb)
    if overlap:
        for i,j in overlap:
            if result['distance_mm']==0:break
            for f,g in ((aa[i],bb[j]),(bb[j],aa[i])):
                tri=[Vector(points[k]) for k in f]
                for h,k in zip(g,g[1:]+g[:1]):
                    a,b=Vector(points[h]),Vector(points[k]);d=b-a
                    q=intersect_ray_tri(*tri,d,a,True)
                    if q is not None and (q-a).dot(d)>=0 and (q-b).dot(d)<=1e-12:
                        result['distance_mm']=0
                        result['witness_world_mm']=[rounded(1000*np.asarray(q),5)]*2
                        break
    nn=[tree.find_nearest(np.asarray(q)/1000)[1] for tree,q in zip(trees,result['witness_world_mm'])]
    result['surface_normal_dot_at_witness']=round(float(nn[0].dot(nn[1])),5)
    result['crossing_patch_face_pairs']=len(overlap)
    return result

def joint_frames(path):
    d,_=parse(path)
    nodes=d['nodes'];parents={i:k for k,node in enumerate(nodes) for i in node.get('children',[])}
    cache={}
    def world(i):
        if i in cache:return cache[i]
        node=nodes[i]
        if 'matrix' in node:local=np.reshape(node['matrix'],(4,4)).T
        else:
            x,y,z,w=node.get('rotation',[0,0,0,1])
            local=np.array(Matrix.LocRotScale(Vector(node.get('translation',(0,0,0))),
                          Quaternion((w,x,y,z)),Vector(node.get('scale',(1,1,1)))))
        cache[i]=(world(parents[i])@local) if i in parents else local
        return cache[i]
    return {n['name']:(nodes[parents[i]].get('name','') if i in parents else '',world(i)) for i,n in enumerate(nodes) if n.get('name','').startswith('mixamorig:')}

def get_weights(body):
    return [{body.vertex_groups[g.group].name:float(g.weight) for g in v.groups if g.weight>0} for v in body.data.vertices]

def dweights(weights,pre):
    return np.array([[sum(w for name,w in ws.items() if name.startswith(pre+d)) for d in DIGITS] for ws in weights])

def classify(body,rig,sg,points,triangles,weights):
    side='Left' if sg==1 else 'Right';pre='mixamorig:'+side+'Hand'
    mat=np.array(rig.matrix_world);bones=rig.data.bones
    def bcoord(n):return np.asarray(rig.matrix_world@bones[n].head_local,dtype=float)
    scores=dweights(weights,pre)
    wrist=bcoord(pre);mcp=np.mean([bcoord(pre+d+'1') for d in DIGITS[:4]],0)
    center=(wrist+mcp)*.5
    tri=np.asarray(triangles)
    tx=sg*points[tri,0]
    inhand=tx.max(1)>WRIST+1e-6
    localinds=np.nonzero(inhand)[0];local=tri[localinds]
    xyz=points[local]
    avg=scores[local].mean(1)
    labels=np.array([DIGITS[j] if val>.48 else 'Palm' for j,val in zip(np.argmax(avg,1),avg.max(1))])
    raw_norm=np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0])
    normal=raw_norm/np.maximum(np.linalg.norm(raw_norm,axis=1,keepdims=True),1e-20)
    onpal=(labels=='Palm')&(tx[localinds].mean(1)>WRIST+.001)&(normal[:,2]<-.12)&(xyz.mean(1)[:,2]<mcp[2]+.001)
    palm=[tuple(t) for t in local[onpal].tolist()]
    st=BVHTree.FromPolygons(points.tolist(),[tuple(t) for t in local.tolist()],all_triangles=True)
    q,n,_,_=st.ray_cast((center[0],center[1],center[2]-.08),(0,0,1))
    if q is None: raise ValueError(f'No palmar surface under {center}')
    center=np.array(q)
    sets={'Palm':palm}; tips={};axes={};segments={};free={}; shaft_bleed={}
    for ix,dig in enumerate(DIGITS):
        heads=np.array([bcoord(pre+dig+str(i)) for i in range(1,5)])
        direction=unit(heads[-1]-heads[0])
        selected=(scores[:,ix]>.60)&(sg*points[:,0]>WRIST)
        ex=(points-heads[-1])@direction
        tipmax=ex[selected].max()
        tipi=np.nonzero(selected & (ex>=tipmax-.0018))[0]
        tip=points[tipi].mean(0)
        _,unique=np.unique(np.round(points[tipi],7),axis=0,return_index=True)
        tipi=tipi[unique]; tip=points[tipi].mean(0)
        tips[dig]=tipi
        volar=unit((sg*.82,.51,-.48) if dig=='Thumb' else (0,0,-1))
        volar=unit(volar-direction*np.dot(direction,volar)); padnorm=unit(direction+.65*volar)
        near=(labels==dig)&(np.linalg.norm(xyz-tip,axis=2).max(1)<.016)
        dots=(xyz-tip)@padnorm
        support=dots[near].max()
        pad=near&(dots.min(1)>support-.00265)&(normal@padnorm>.32)
        terminal=near&(((xyz-tip)@direction).min(1)>-.008)
        sets[dig]=[tuple(x) for x in local[pad].tolist()]
        sets[dig+'_tip']=[tuple(x) for x in local[terminal].tolist()]
        if not sets[dig] or not sets[dig+'_tip']: raise ValueError(f'Empty {side} {dig} pulp or tip patch: {len(sets[dig])}, {len(sets[dig+"_tip"])}')
        own_line=(heads[-1]-heads[0]); ahead=(points-heads[0])@direction
        # Independently identify free-shaft vertices by nearest rest centerline; no reliance on their own weights.
        free[dig]=(heads[0],direction,float(np.linalg.norm(own_line)))
        ax=[]
        for i in range(1,5):
            b=bones[pre+dig+str(i)]
            m=mat[:3,:3]@np.asarray(b.matrix_local)[:3,:3]
            # The +X/+Z labels describe the closest canonical local direction.
            flex=unit(np.cross(direction,volar))
            spreadtoward=np.array((0,1 if ix in (2,3) else -1,0),dtype=float)
            if dig=='Thumb':spreadtoward=np.array((0,0,-1),dtype=float)
            spread=unit(np.cross(direction,spreadtoward))
            def signed_axis(v):
                cc=np.linalg.solve(m,v);ind=int(np.argmax(np.abs(cc)))
                return ('+' if cc[ind]>=0 else '-')+'XYZ'[ind], rounded(unit(cc),5)
            ax.append({'joint':i,'curl_toward_pulp':signed_axis(flex),'spread':signed_axis(spread)})
        axes[dig]=ax
        segments[dig]={'bone_head_spacings_mm':rounded(1000*np.linalg.norm(np.diff(heads,axis=0),axis=1),4),
                       'root_to_skin_tip_unit':rounded(unit(tip-heads[0]),5),'pulp_triangles':int(sum(pad)),
                       'tip_triangles':int(sum(terminal)),'tip_vertices':len(tipi),'rest_tip_m':rounded(tip)}
    corrected_boundary=[{tuple(np.round(points[i],6)) for i in f} for f in local.tolist()]
    ring_counts=Counter()
    for f in corrected_boundary:
        xyzlist=list(f)
        for i in range(len(xyzlist)):
            for j in range(i):
                ring_counts[tuple(sorted([xyzlist[i],xyzlist[j]]))]+=1
    hand_open_edges=sum(v==1 and max(sg*q[0] for q in e)>WRIST+2e-6 for e,v in ring_counts.items())
    hand_overfull_edges=sum(v>2 for v in ring_counts.values())
    gaps={}
    for i in range(3):
        aa,bb=DIGITS[i:i+2]
        sets_free=[]
        for digit in (aa,bb):
            a,d,length=free[digit]
            mask=(labels==digit)&(((xyz-a)@d).min(1)>.32*length)
            sets_free.append([tuple(x) for x in local[mask].tolist()])
        gaps[aa+'_'+bb]=disjoint_distance(points,*sets_free)['distance_mm']
    # Intersect the fitted thumb with three transverse planes; report measured width
    # and thickness on the skin, plus the two visible thumb bone lengths above.
    a,d,length=free['Thumb']; up=unit(np.array([0,0,1])-np.dot(d,[0,0,1])*d); lat=unit(np.cross(d,up))
    xthumb=xyz[labels=='Thumb']
    cross_sections={}
    for t in (.36,.62,.84):
        offset=(xthumb-a)@d-length*t
        samples=[]
        for k in range(3):
            j=(k+1)%3;ok=offset[:,k]*offset[:,j]<0
            alpha=offset[ok,k]/(offset[ok,k]-offset[ok,j])
            samples.extend(xthumb[ok,k]+alpha[:,None]*(xthumb[ok,j]-xthumb[ok,k]))
        samples=np.array(samples)
        cross_sections[str(t)]={'width_mm':round(float(np.ptp(samples@lat)*1000),3),'thickness_mm':round(float(np.ptp(samples@up)*1000),3)}
    independently_owned=[]
    for p in points:
        best=None
        for dig,(a,v,length) in free.items():
            t=np.dot(p-a,v);dist=np.linalg.norm(p-a-np.clip(t,0,length)*v)
            item=(dist,dig,t,length)
            if best is None or dist<best[0]:best=item
        dist,dig,t,ll=best
        independently_owned.append(dig if sg*p[0]>WRIST and t>.32*ll and t<ll+.005 and dist<.014 else '')
    for ix,dig in enumerate(DIGITS):
        inds=np.nonzero(np.array(independently_owned)==dig)[0]
        foreign=np.delete(scores[inds],ix,axis=1).sum(1)
        shaft_bleed[dig]={'vertices':len(inds),'any_foreign_digit':int((foreign>0).sum()),'above_0_2':int((foreign>.2).sum()),
                          'maximum_foreign_weight':round(float(foreign.max(initial=0)),8)}
    return {'tris':local,'labels':labels,'global_ids':localinds,'tips':tips,'sets':sets,'palm':center,
            'summary':{'hand_triangles_any_vertex':len(local),'palm_triangles':len(palm),'palm_normal':rounded(n),
                       'palm_degrees_from_down':round(math.degrees(math.acos(np.clip(-n.z,-1,1))),4),'palmar_point_m':rounded(center),
                       'axes':axes,'digits':segments,'free_shaft_weights':shaft_bleed,'interdigital_free_shaft_gaps_mm':gaps,'thumb_section_widths':cross_sections,'open_edges_distal_to_wrist':hand_open_edges,'nonmanifold_edges_over_two_faces':hand_overfull_edges}}

def finger_check(points,h):
    tippos={d:points[ids].mean(0) for d,ids in h['tips'].items()}
    tree=BVHTree.FromPolygons(points.tolist(),h['sets']['Palm'],all_triangles=True)
    return {'tip_centroid_to_palm_skin_mm':{d:round(1000*tree.find_nearest(v)[3],5) for d,v in tippos.items()},
            'thumb_above_highest_other_mm':round(float((tippos['Thumb'][2]-max(tippos[d][2] for d in DIGITS[:4]))*1000),5),
            'thumb_index_centroid_mm':round(float(np.linalg.norm(tippos['Thumb']-tippos['Index'])*1000),5),
            'tip_centroids_world_mm':{d:rounded(v*1000,4) for d,v in tippos.items()}}

def pulp_near_area(points,first,second):
    """Area-weighted micropatches closer than 0.5/1 mm to opposed fingertip skin."""
    points=np.asarray(points,float);output=[]
    subdiv=12
    weights=[]
    for i in range(subdiv):
        for j in range(subdiv-i):
            for k in ((1/3,2/3) if i+j<subdiv-1 else (1/3,)):
                weights.append([1-(i+j+2*k)/subdiv,(i+k)/subdiv,(j+k)/subdiv])
    for aa,bb in ((first,second),(second,first)):
        tree=BVHTree.FromPolygons(points.tolist(),bb,all_triangles=True)
        totals=[0.,0.];sample_count=0
        for face in aa:
            xyz=points[list(face)];normal=np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0])
            length=np.linalg.norm(normal);normal/=length
            sample_area=.5e6*length/(subdiv*subdiv)
            for q in np.asarray(weights)@xyz:
                _,other,_,dis=tree.find_nearest(q)
                if normal@np.asarray(other)<0:
                    for k,t in enumerate([.0005,.001]):
                        if dis<t:totals[k]+=sample_area
                sample_count+=1
        output.append({'within_0_5_mm_area_mm2':round(totals[0],4),'within_1_mm_area_mm2':round(totals[1],4),'equal_area_samples':sample_count})
    return dict(thumb_pulp=output[0],index_pulp=output[1])

def radial_openings(points,hand,sign):
    """Direct skin silhouette in the standard oblique thumb-side viewing direction."""
    view=unit((.26*sign,-1,-.16))
    up=np.array((sign,0.,0.));up=unit(up-view*np.dot(up,view));hor=unit(np.cross(up,view))
    xyz=np.asarray(points,dtype=float)[hand['tris']]*1000
    xy=np.stack([xyz@hor,xyz@up],axis=2)
    pitch=.25
    lo=xy.min((0,1))-pitch*3
    uv=(xy-lo)/pitch
    w,h=np.ceil(uv.max((0,1))+4).astype(int)
    mask=np.zeros((h,w),bool)
    for tri in uv:
        mn=np.maximum(0,np.floor(tri.min(0)).astype(int));mx=np.minimum([w-1,h-1],np.ceil(tri.max(0)).astype(int))
        if np.any(mx<mn):continue
        xx,yy=np.meshgrid(np.arange(mn[0],mx[0]+1)+.5,np.arange(mn[1],mx[1]+1)+.5)
        ee=np.roll(tri,-1,axis=0)-tri
        area=ee[:,0,None,None]*(yy-tri[:,1,None,None])-ee[:,1,None,None]*(xx-tri[:,0,None,None])
        mask[mn[1]:mx[1]+1,mn[0]:mx[0]+1]|=(area.min(0)>=0)|(area.max(0)<=0)
    holes=[]
    for y,x in np.argwhere(~mask):
        if mask[y,x]:continue
        q=deque([(int(y),int(x))]);mask[y,x]=True;count=0;edge=False
        while q:
            a,b=q.popleft();count+=1
            if a==0 or b==0 or a==h-1 or b==w-1:edge=True
            for j,k in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1)):
                ny=a+j;nx=b+k
                if 0<=ny<h and 0<=nx<w and not mask[ny,nx]:
                    q.append((ny,nx));mask[ny,nx]=True
        if not edge and count>=4:holes.append(count*pitch**2)
    holes.sort(reverse=True)
    return {'projection_dir':rounded(view),'pixel_pitch_mm':pitch,'hole_areas_mm2':holes,
                'max_equivalent_diameter_mm':round(float(2*math.sqrt(max(holes,default=0)/math.pi)),4)}

def named_surfaces(points,h,g):
    sets=h['sets']
    if g in ('pinch','ok'):return {'pulp_to_pulp':nearest(points,sets['Thumb'],sets['Index']),'opposing_pulp_near_area':pulp_near_area(points,sets['Thumb'],sets['Index'])}
    if g=='fist':
        folded=[tuple(x) for x in h['tris'][np.isin(h['labels'],DIGITS[:4])].tolist()]
        tree=BVHTree.FromPolygons(points.tolist(),folded,all_triangles=True)
        visible=[]
        for f in folded:
            xyz=np.asarray(points)[list(f)];c=xyz.mean(0)
            norm=unit(np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0]))
            if norm[2]>-.35:continue
            q,_,_,_=tree.ray_cast(c+[0,0,-.12],(0,0,1),.24)
            if q is not None and np.linalg.norm(np.asarray(q)-c)<.00001:visible.append(f)
        return {'thumb_terminal_to_palmar_exterior':nearest(points,sets['Thumb_tip'],visible),
                'thumb_pulp_to_palmar_exterior':nearest(points,sets['Thumb'],visible),
                'long_finger_pulp_to_palm':{d:nearest(points,sets[d],sets['Palm']) for d in DIGITS[:4]},
                'terminal_to_palm':{d:nearest(points,sets[d+'_tip'],sets['Palm']) for d in DIGITS},
                'thumb_terminal_to_folded':nearest(points,sets['Thumb_tip'],folded)}
    return {}

def cylinder_fit(points,h,sg):
    # Minimise the opposing standoff to a finite-radius infinite axis. A valid fit
    # needs contacts to surround the axis; a solution outside the grip is rejected.
    pp=np.asarray(points)*1000; tri=pp[h['tris']];labs=h['labels']
    groups=[np.nonzero(labs==d)[0] for d in ('Palm',*DIGITS)]
    origin=h['palm']*1000
    def distances(params, detail=False, explicit=None):
        if explicit is None:
            x,z,slope,vertical=params
            axis=unit((slope*sg,1,vertical)); center=origin+np.array((sg*x,0,z))
        else:
            center=np.asarray(explicit['point_world_mm']);axis=unit(explicit['axis_world'])
        d=tri-center; proj=d-(d@axis)[:,:,None]*axis
        edge=np.roll(proj,-1,axis=1)-proj
        t=np.clip(-(proj*edge).sum(2)/np.maximum((edge*edge).sum(2),1e-20),0,1)
        c=proj+t[:,:,None]*edge
        sq=(c*c).sum(2);i=np.argmin(sq,1); indr=np.arange(len(d))
        q=c[indr,i];dd=np.sqrt(sq[indr,i])
        crosses=np.cross(edge,-proj)@axis
        inside=(crosses.min(1)>0)|(crosses.max(1)<0)
        dd[inside]=0
        near=[gg[np.argmin(dd[gg])] for gg in groups]
        ds=dd[near];basis=unit(np.cross(axis,[0,0,1]));up=np.cross(axis,basis)
        ang=np.sort(np.arctan2(q[near]@up,q[near]@basis))
        maxangle=np.diff(np.r_[ang,ang[0]+2*np.pi]).max()
        # The diameter must clear all faces, including the palmar heel and webs.
        short=np.minimum(ds-20.004,0)
        score=600*np.dot(short,short)+np.sum((ds-20.004)**2)+3000*max(0,maxangle-np.pi)**2
        if detail:
            boundary=proj.reshape(-1,3)
            all_angles=np.sort(np.arctan2(boundary@up,boundary@basis))
            hull_gap=np.diff(np.r_[all_angles,all_angles[0]+2*np.pi]).max()
            return dict(point_world_mm=rounded(center,4),axis_world=rounded(axis),diameter_mm=40,
                       minimum_axis_distance_mm=round(float(dd.min()),5), penetrating_triangles=int((dd<20).sum()),
                       nearest_axis_mm={d:round(float(v),5) for d,v in zip(('Palm',*DIGITS),ds)},
                       max_angular_contact_gap_deg=round(math.degrees(maxangle),3),
                       max_angular_gap_all_skin_vertices_deg=round(math.degrees(hull_gap),3),encloses_axis=bool(hull_gap<np.pi))
        return float(score)
    # Use the production mandrel if its transform is available. Preserve the
    # exact authored transform in the report so a future audit can repeat it.
    tag='Left' if sg>0 else 'Right'
    declaration=HERE/'grip_gauges.json'
    if declaration.is_file():
        recorded=json.loads(declaration.read_text())
        if recorded['body_sha256']==digest(WORK/'body_male_v1.glb') and recorded['library_sha256']==digest(WORK/'hand_gestures_male.glb'):
            checked=distances(None,True,recorded[tag])
            checked['placement']='recorded authored cylinder'
            return checked
    for folder in (WORK/'.build',HERE):
        filepath=folder/('gauge_'+tag+'.json')
        if filepath.is_file():
            spec=json.loads(filepath.read_text())
            checked=distances(None,True,spec)
            checked['placement']='authored cylinder'
            return checked
    if tag=='Right' and (WORK/'.build/gauge_Left.json').exists():
        left=json.loads((WORK/'.build/gauge_Left.json').read_text())
        lm=json.loads((WORK/'.build/landmarks.json').read_text())
        delta=(np.asarray(lm['mixamorig:RightHandMiddle']['root'])-np.asarray(lm['mixamorig:LeftHandMiddle']['root'])*[-1,1,1])*1000
        pp=np.asarray(left['point_world_mm'])*[-1,1,1]+delta
        aa=np.asarray(left['axis_world'])*[-1,1,1]
        checked=distances(None,True,{'point_world_mm':pp,'axis_world':aa})
        checked['placement']='reflected authored cylinder plus right-hand bind offset'
        return checked
    seeds=[np.array([x,-22.,s,0.]) for x in (5.,14.,24.) for s in (-.45,0,.45)]
    best=min(seeds,key=distances)
    for step in ((8.,8.,.26,.18),(4.,4.,.13,.09),(2.,2.,.065,.045),(1.,1.,.032,.022),(.45,.45,.016,.011),(.20,.20,.008,.005),(.08,.08,.003,.002),(.025,.025,.001,.001)):
        f=distances(best)
        for _ in range(12):
            opts=[(distances(z),z) for k in range(4) for sig in (-1,1) if (-50<(z:=best+sig*np.eye(4)[k]*step[k])[0]<65 and -65<z[1]<0 and abs(z[2])<1 and abs(z[3])<.5)]
            value,p=min(opts,key=lambda t:t[0])
            if value>=f:break
            best=p;f=value
    return distances(best,True)

def compare_positions(source,final):
    tree=KDTree(len(final))
    for i,q in enumerate(final):tree.insert(q,i)
    tree.balance()
    ds=[tree.find(q)[2] for q in source if abs(q[0])<=WRIST]
    return {'source_vertex_copies_compared':len(ds),'maximum_source_to_export_mm':round(1000*max(ds),6),
            'over_0_5_mm':sum(d>.0005 for d in ds),'method':'Every original non-hand vertex to its closest reimported bind vertex; wrist abs(X) <= 0.28245 m.'}

def reset(rig):
    ad=rig.animation_data_create()
    ad.action=None
    for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()

def compare_editable(imported_rest,imported_poses,results):
    blend=WORK/'body_male_v1.blend'; posefile=WORK/'hand_gestures_male.json'
    if not blend.is_file() or not posefile.is_file():return None
    contents=json.loads(posefile.read_text())
    bpy.ops.wm.open_mainfile(filepath=str(blend),load_ui=False,use_scripts=False)
    arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    body=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.find_armature()==arm)
    reset(arm); bpy.context.scene.frame_set(1)
    rest=verts(body); tree=KDTree(len(rest))
    for i,p in enumerate(rest):tree.insert(p,i)
    tree.balance()
    mapping=np.asarray([tree.find(p)[1] for p in imported_rest])
    cmp={'blend_sha256':digest(blend),'json_sha256':digest(posefile),'native_vertices':len(rest),'reimport_vertices':len(imported_rest),
         'maximum_rest_vertex_mm':round(float(np.max(np.linalg.norm(imported_rest-rest[mapping],axis=1))*1000),7),
         'missing_clips_in_json':sorted(set(imported_poses)-set(contents['gestures'])),
         'only_in_json':sorted(set(contents['gestures'])-set(imported_poses))}
    for name,posed in imported_poses.items():
        reset(arm);act=bpy.data.actions[name];ad=arm.animation_data_create();ad.action=act;ad.action_slot=act.slots[0]
        bpy.context.scene.frame_set(round(act.frame_range[0]));bpy.context.view_layer.update()
        native=verts(body,True)
        results[name]['reimport_max_vertex_mm']=round(float(np.linalg.norm(posed-native[mapping],axis=1).max()*1000),7)
        errors=[]
        for n,angles in contents['gestures'][name].items():
            q=Euler(np.deg2rad(angles),'XYZ').to_quaternion()
            aq=np.array(arm.pose.bones[n].rotation_quaternion,float);bq=np.array(q,float)
            error=min(np.linalg.norm(aq-bq),np.linalg.norm(aq+bq))
            errors.append(np.rad2deg(4*np.arcsin(np.clip(.5*error,0,1))))
        results[name]['json_to_blend_max_angle_deg']=round(float(max(errors,default=0)),8)
    return cmp

def main(body_path,gesture_path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    source=WORK.parent/'studio_rigged.glb'
    sobjs=import_asset(source); orig=next(o for o in sobjs if o.type=='MESH' and o.vertex_groups)
    sr=next(o for o in sobjs if o.type=='ARMATURE')
    original_bones={b.name:b.parent.name if b.parent else None for b in sr.data.bones}
    sp,sf,sk=geometry(orig)
    sx=np.array(sf); region=np.where(sp[sx,0].max(1)>WRIST,1,np.where(sp[sx,0].min(1)<-WRIST,-1,0))
    oldhits,oldcol=collisions(sp,sf,sk,region)
    oldcol['intersecting_pair_world_m']=[[rounded(sp[list(sf[k])],7) for k in ab] for ab in oldhits]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs=import_asset(body_path)
    rig=next(o for o in objs if o.type=='ARMATURE')
    body=next(o for o in objs if o.type=='MESH' and o.vertex_groups)
    reset(rig)
    rest,tris,keys=geometry(body)
    weights=get_weights(body)
    rr=check_asset(body_path)
    rr['decoded_images']={im.name:list(im.size) for im in bpy.data.images if im.packed_file}
    bones={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
    rr['missing_bones']=sorted(set(original_bones)-set(bones));rr['additional_bones']=sorted(set(bones)-set(original_bones))
    rr['changed_parents']={n:[p,bones[n]] for n,p in original_bones.items() if n in bones and p!=bones[n]}
    rr['height_m']=round(float(np.ptp(rest[:,2])),8); rr['feet_z_m']=round(float(rest[:,2].min()),8)
    rr['skin']={'max_influences':max(map(len,weights)),'over_four':sum(len(x)>4 for x in weights),
                'unweighted':sum(not x for x in weights),'max_sum_error':max(abs(sum(x.values())-1) for x in weights),
                'vertices':len(weights)}
    totals=np.vstack([dweights(weights,'mixamorig:'+s+'Hand').T for s in ('Left','Right')]).T
    rr['skin']['multiple_finger_chains']=int(((totals>0).sum(1)>1).sum())
    rr['skin']['multiple_finger_chains_above_0_2']=int(((totals>.2).sum(1)>1).sum())
    rr['original_rest_displacement']=compare_positions(sp,rest)
    hands={k:classify(body,rig,sg,rest,tris,weights) for k,sg in [('L',1),('R',-1)]}
    regions=np.zeros(len(tris),int);labels=np.full(len(tris),'Body',dtype='U15')
    for tag,sg in [('L',1),('R',-1)]:
        h=hands[tag];regions[h['global_ids']]=sg;labels[h['global_ids']]=[tag+'_'+v for v in h['labels']]
    _,col=collisions(rest,tris,keys,regions,labels)
    r={'blender':bpy.app.version_string,'source_sha256':digest(source),'source_rest_intersections':oldcol,'static':rr,
       'hands':{tag:h['summary'] for tag,h in hands.items()},'bind_intersections':col,'poses':{}}
    mirror=KDTree(len(rest))
    for i,q in enumerate(rest):mirror.insert(q,i)
    mirror.balance()
    mir=np.array([mirror.find((-q[0],q[1],q[2]))[2]*1000 for q in rest])
    rr['mirror_nearest_vertex_mm']={'rms':round(float(np.sqrt(np.mean(mir**2))),5),'max':round(float(max(mir)),5),'mean':round(float(mir.mean()),5)}
    def mirror_surface(points,faces):
        bvh=BVHTree.FromPolygons(points.tolist(),faces,all_triangles=True)
        ds=np.array([bvh.find_nearest((-p[0],p[1],p[2]))[3]*1000 for p in points])
        return {'mean':round(float(ds.mean()),5),'rms':round(float(np.sqrt(np.mean(ds*ds))),5),
                'p95':round(float(np.percentile(ds,95)),5),'max':round(float(ds.max()),5)}
    rr['mirror_reflected_vertex_to_surface_mm']={'original':mirror_surface(sp,sf),'export':mirror_surface(rest,tris)}
    if not gesture_path:
        (HERE/'static_preview.json').write_text(json.dumps(r,indent=2,default=lambda v:v.item() if isinstance(v,np.generic) else list(v)));return
    r['library']=check_asset(gesture_path,True)
    bodyframes,libframes=joint_frames(body_path),joint_frames(gesture_path)
    common=sorted(bodyframes.keys()&libframes.keys())
    r['library']['joint_frame_comparison']={'shared_joint_names':len(common),'missing_in_library':sorted(bodyframes.keys()-libframes.keys()),
                    'only_in_library':sorted(libframes.keys()-bodyframes.keys()),'changed_joint_parents':[n for n in common if (bodyframes[n][0] if bodyframes[n][0] in bodyframes else None)!=(libframes[n][0] if libframes[n][0] in libframes else None)],
                    'maximum_world_bind_matrix_difference':max(float(np.max(np.abs(bodyframes[n][1]-libframes[n][1]))) for n in common)}
    import_asset(gesture_path)
    imported_poses={}
    for side in ('L','R'):
        h=hands[side];sg=1 if side=='L' else -1
        for g in GESTURES:
            name='hand_'+g+'_'+side
            reset(rig);act=bpy.data.actions[name];ad=rig.animation_data_create()
            ad.action=act;ad.action_slot=act.slots[0]
            bpy.context.scene.frame_set(round(act.frame_range[0]));bpy.context.view_layer.update()
            pts=verts(body,True);imported_poses[name]=pts
            hits,col=collisions(pts,tris,keys,regions,labels)
            res=finger_check(pts,h); res['surfaces']=named_surfaces(pts,h,g);res['intersections']=col
            res['slot']=act.slots[0].identifier
            res['nonhand_pose_displacement_mm']=round(float(np.linalg.norm((pts-rest)[np.abs(rest[:,0])<=WRIST],axis=1).max()*1000),6)
            if g in ('fist','thumbs_up'):res['thumb_side_silhouette']=radial_openings(pts,h,sg)
            if g=='grip_small':res['cylinder_fit']=cylinder_fit(pts,h,sg)
            r['poses'][name]=res
            print(name,'crosses',len(hits),'surfaces',res['surfaces'],'grip',res.get('cylinder_fit'),flush=True)
    verify={'static_structure':rr['meshes']==rr['skins']==1 and rr['joints_per_skin']==[65] and rr['animations']==0,
            'one_material_max1024':rr['materials']==1 and all(max(v)<=1024 for v in rr['decoded_images'].values()),
            'names_and_parents':not(rr['missing_bones'] or rr['additional_bones'] or rr['changed_parents']),
            'triangles':rr['triangles']<=10000 and all(h['summary']['hand_triangles_any_vertex']<=3000 for h in hands.values()),
            'weights':rr['skin']['max_influences']<=4 and rr['skin']['unweighted']==0 and rr['skin']['multiple_finger_chains']==0 and all(all(x['any_foreign_digit']==0 for x in h['summary']['free_shaft_weights'].values()) for h in hands.values()),
            'nonhand_rest_position':rr['original_rest_displacement']['over_0_5_mm']==0,
            'clip_structure':r['library']['meshes']==0 and set(r['library']['clips'])==set(r['poses']) and not any(c['invalid'] for c in r['library']['clips'].values()),
            'all_whole_body_intersections_zero':all(p['intersections']['whole_body']==0 for p in r['poses'].values())}
    libcomp=r['library']['joint_frame_comparison']
    verify['gesture_rest_matches_body']=libcomp['shared_joint_names']==65 and not libcomp['changed_joint_parents'] and libcomp['maximum_world_bind_matrix_difference']<1e-5
    for tag in ('L','R'):
        for g in ('ok','pinch'):verify[g+'_'+tag]=r['poses'][f'hand_{g}_{tag}']['surfaces']['pulp_to_pulp']['distance_mm']<1
        fist=r['poses'][f'hand_fist_{tag}']['surfaces']
        verify['fist_contact_'+tag]=all(v['distance_mm']<=1 for v in fist['long_finger_pulp_to_palm'].values()) and fist['thumb_terminal_to_folded']['distance_mm']<=1 and fist['thumb_pulp_to_palmar_exterior']['distance_mm']<=1
        verify['thumbs_up_'+tag]=r['poses'][f'hand_thumbs_up_{tag}']['thumb_above_highest_other_mm']>0
        grip=r['poses'][f'hand_grip_small_{tag}']
        verify['grip_gaps_'+tag]=all(15<=x<=30 for x in grip['tip_centroid_to_palm_skin_mm'].values())
        verify['cylinder_'+tag]=not grip['cylinder_fit']['penetrating_triangles'] and grip['cylinder_fit']['encloses_axis']
    r['native_roundtrip']=compare_editable(rest,imported_poses,r['poses'])
    if r['native_roundtrip']:
        verify['editable_json_and_reimport_consistency']=(
            not r['native_roundtrip']['missing_clips_in_json'] and not r['native_roundtrip']['only_in_json']
            and r['native_roundtrip']['maximum_rest_vertex_mm']<.01
            and max(x['reimport_max_vertex_mm'] for x in r['poses'].values())<.01
            and max(x['json_to_blend_max_angle_deg'] for x in r['poses'].values())<.001)
    r['checks']=verify
    (HERE/'export_checks.json').write_text(json.dumps(r,indent=2,default=lambda v:v.item() if isinstance(v,np.generic) else list(v)))
    print('Final checks',verify,flush=True)

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:]
    main(Path(args[0]).resolve() if args else WORK/'body_male_v1.glb',None if args and len(args)==1 else (Path(args[1]).resolve() if args else WORK/'hand_gestures_male.glb'))
