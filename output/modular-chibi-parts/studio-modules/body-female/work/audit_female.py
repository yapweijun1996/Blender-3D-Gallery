"""Read-only geometry, skin, glTF and animation audit. Run with run_blender.sh."""
import argparse
import hashlib
import json
import math
import re
import struct
import subprocess
import sys
from collections import Counter
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

WORK = Path(__file__).resolve().parent
SOURCE = WORK.parent / 'studio_rigged.glb'
OLD = WORK.parents[2] / 'hand-gestures-astra' / 'round2'
sys.dont_write_bytecode = True
sys.path.insert(0, str(OLD))
from hand_surface import nearest  # Round 2 includes vertex/triangle and edge/edge witnesses.

DIGITS = ('Index', 'Middle', 'Ring', 'Pinky', 'Thumb')
SIDES = {'L': ('Left', 1), 'R': ('Right', -1)}
GESTURES = ('fist', 'open_relaxed', 'point', 'thumbs_up', 'peace', 'ok', 'grip_small', 'pinch', 'open_wide')
TARGET = re.compile(r'^mixamorig:(Left|Right)Hand(Index|Middle|Ring|Pinky|Thumb)[1-4]$')


def read_glb(path):
    raw = path.read_bytes()
    magic, ver, total, size, kind = struct.unpack_from('<4sIIII', raw)
    assert (magic, ver, total, kind) == (b'glTF', 2, len(raw), 0x4e4f534a)
    return json.loads(raw[20:20+size]), raw[28+size:]


def rounded(value):
    return np.asarray(value, dtype=float).round(6).tolist()


def normalized(v):
    return v / max(1e-12, np.linalg.norm(v))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def world_points(obj, evaluated=False):
    if evaluated:
        obj = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    vertices = obj.data.vertices
    xyz = np.empty(len(vertices)*3, dtype=np.float32)
    vertices.foreach_get('co', xyz)
    transform = np.asarray(obj.matrix_world)
    return xyz.reshape((-1, 3)) @ transform[:3, :3].T + transform[:3, 3]


def new_body(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return (next(o for o in bpy.context.scene.objects if o.type=='MESH'),
            next(o for o in bpy.context.scene.objects if o.type=='ARMATURE'))


def topology(body):
    body.data.calc_loop_triangles()
    return [tuple(t.vertices) for t in body.data.loop_triangles]


def joint(rig, name):
    return np.array(rig.matrix_world @ rig.data.bones[name].head_local)


def weights(body):
    return [{body.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>0}
            for v in body.data.vertices]


class MeshCheck:
    def __init__(self, body, rig):
        self.rest = world_points(body)
        self.bind = world_points(body, evaluated=True)
        self.tris = topology(body)
        self.tri = np.asarray(self.tris)
        self.weights = weights(body)
        loops=np.empty(len(body.data.loop_triangles)*3,dtype=np.int32)
        body.data.loop_triangles.foreach_get('loops',loops)
        loops=loops.reshape((-1,3))
        uv=body.data.uv_layers.active
        coords=np.empty(len(body.data.loops)*2,dtype=np.float32)
        if uv:uv.data.foreach_get('uv',coords)
        self.tri_uv=coords.reshape((-1,2))[loops] if uv else None
        mat=np.asarray(body.matrix_world)[:3,:3]
        corner=np.empty(len(body.data.loops)*3, dtype=np.float32)
        body.data.corner_normals.foreach_get('vector',corner)
        self.tri_normals=corner.reshape((-1,3))[loops] @ np.linalg.inv(mat)
        self.tri_normals/=np.maximum(np.linalg.norm(self.tri_normals,axis=2)[:,:,None],1e-14)
        self.joints = {b.name:joint(rig, b.name) for b in rig.data.bones}
        self.parents = {b.name:b.parent.name if b.parent else None for b in rig.data.bones}
        # Multiple vertex and normal/UV splits refer to one topological point.
        self.keys = [tuple(int(v) for v in p) for p in np.rint(self.rest*1e6)]
        self.welds = [set(self.keys[i] for i in t) for t in self.tris]
        self.regions = np.zeros(len(self.tris), dtype=int)
        self.cutoffs = {}
        for tag, (side, sign) in SIDES.items():
            pre = 'mixamorig:'+side+'Hand'
            self.cutoffs[tag] = float(abs(self.joints[pre][0]))
            self.regions[(sign*self.rest[self.tri,0]).max(1)>self.cutoffs[tag]] = sign
        self.bind_pairs = self.crossings(self.bind)

    def crossings(self, points):
        tree = BVHTree.FromPolygons(points.tolist(), self.tris, all_triangles=True)
        return {(a,b) for a,b in tree.overlap(tree) if a<b and self.welds[a].isdisjoint(self.welds[b])}

    def crossing_result(self, pairs, face_labels=None):
        counts = Counter()
        for i,j in pairs:
            counts['Left'] += 1 in (self.regions[i], self.regions[j])
            counts['Right'] += -1 in (self.regions[i], self.regions[j])
            counts['outside_hands'] += not(self.regions[i] or self.regions[j])
        both = [p for p in pairs if self.regions[list(p)].any()]
        details = Counter(tuple(sorted((face_labels[i],face_labels[j]))) for i,j in both) if face_labels else {}
        return {'whole':len(pairs),'involving_either_hand':len(both),
                **{k:int(counts[k]) for k in ('Left','Right','outside_hands')},
                'new_vs_bind':len(pairs-self.bind_pairs), 'missing_vs_bind':len(self.bind_pairs-pairs),
                'hand_parts':{'/'.join(k):v for k,v in details.items()},
                'hand_examples':[list(p) for p in sorted(both)[:18]]}

    def description(self):
        bleed = np.array([[sum(v for n,v in ws.items() if ('Hand'+d) in n) for d in DIGITS]
                          for ws in self.weights])
        lengths = np.array([len(w) for w in self.weights])
        sum_error = max(abs(sum(w.values())-1) for w in self.weights)
        z = self.bind[:,2]
        edge_counts=Counter()
        hand_edge_counts=Counter()
        for t,side in zip(self.tris,self.regions):
            for a,b in zip(t,t[1:]+t[:1]):
                edge=tuple(sorted((self.keys[a],self.keys[b])))
                edge_counts[edge]+=1
                if side:hand_edge_counts[edge]+=1
        hand_bad=Counter(edge_counts[e] for e in hand_edge_counts if edge_counts[e]!=2)
        return dict(welded_nonmanifold_edges=dict(Counter(n for n in edge_counts.values() if n!=2)),
                    welded_hand_nonmanifold_edges=dict(hand_bad),
                    hand_nonmanifold_examples=[dict(edge_mm=rounded(np.asarray(edge)/1000),incident_faces=edge_counts[edge]) for edge in hand_edge_counts if edge_counts[edge]!=2][:15], vertices=len(self.rest), triangles=len(self.tris), height_m=float(z.max()-z.min()),
                    feet_z_m=float(z.min()), bounds_m=rounded([self.bind.min(0),self.bind.max(0)]),
                    wrist_plane_x_abs_m=self.cutoffs,
                    triangles_touching_wrist_distal={s:int((self.regions==sg).sum()) for s,(_,sg) in SIDES.items()},
                    hand_triangles_by_centroid={s:int(((sg*self.rest[self.tri,0]).mean(1)>self.cutoffs[s]).sum())
                                                for s,(_,sg) in SIDES.items()},
                    max_influences=int(lengths.max()), weight_sum_min=float(min(sum(w.values()) for w in self.weights)), weight_sum_max=float(max(sum(w.values()) for w in self.weights)), unweighted=int((lengths==0).sum()),
                    vertices_over_four=int((lengths>4).sum()), max_weight_sum_error=sum_error,
                    mixed_digit_any=int(((bleed>0).sum(1)>1).sum()),
                    mixed_digit_over_point_two=int(((bleed>.2).sum(1)>1).sum()),
                    worst_second_digit_weight=float(np.sort(bleed,axis=1)[:,-2].max()),
                    bind_rest_max_mm=float(np.max(np.linalg.norm(self.bind-self.rest,axis=1))*1000),
                    crossings=self.crossing_result(self.bind_pairs))


def drift(source, current):
    # Match by nearest rest position in both directions to support welding and UV duplication.
    def tree_for(points):
        tree = KDTree(len(points))
        for i,p in enumerate(points): tree.insert(p,i)
        tree.balance()
        return tree
    dst, src = tree_for(current.rest), tree_for(source.rest)
    def stats(old,new_tree):
        distances = np.array([new_tree.find(p)[2]*1000 for p in old.rest])
        before_wrist = ((old.rest[:,0]<=source.cutoffs['L']) & (old.rest[:,0]>=-source.cutoffs['R']))
        nonhand = np.array(['Hand' not in max(w,key=w.get) if w else True for w in old.weights])
        output = {}
        for name,mask in [('within_original_symmetric_cut',np.abs(old.rest[:,0]) <= .2862),('at_or_proximal_to_wrist',before_wrist),('dominant_joint_nonhand',nonhand)]:
            ids = np.flatnonzero(mask)
            i = int(ids[np.argmax(distances[ids])])
            output[name] = dict(vertices=len(ids),maximum_mm=float(distances[i]), over_0_5_mm=int((distances[ids]>.5).sum()),
                                witness_mm=rounded(old.rest[i]*1000))
        return output
    src_surface=BVHTree.FromPolygons(source.rest.tolist(),source.tris,all_triangles=True)
    within=np.abs(current.rest[:,0])<=.2862+1e-6
    surf_millimeters=[1000*src_surface.find_nearest(p)[3] for p in current.rest[within]]
    return dict(source_to_final=stats(source,dst), final_to_source=stats(current,src),
                final_at_or_inside_seam_to_original_triangles_max_mm=max(surf_millimeters),
                reverse_point_to_point_note='Clipping inserts new vertices along source edges at the seam. Their distances to the original triangle surfaces are measured separately.')


def untouched_faces(source,current):
    tree=KDTree(len(source.rest))
    for i,p in enumerate(source.rest):tree.insert(p,i)
    tree.balance()
    lookup=[]
    for p in current.rest:
        _,i,dist=tree.find(p)
        lookup.append(source.keys[i] if dist<1e-6 else None)
    signatures={}
    for tid,t in enumerate(current.tris):
        points=[lookup[i] for i in t]
        if None not in points:signatures[tuple(sorted(points))]=(tid,points)
    uv_diffs=[]; norm_diffs=[]; original=0
    for i,t in enumerate(source.tris):
        if np.abs(source.rest[list(t),0]).max()>.2862:continue
        original+=1
        points=[source.keys[v] for v in t]
        result=signatures.get(tuple(sorted(points)))
        if not result:continue
        tid,final_points=result
        order=[final_points.index(p) for p in points]
        uv_diffs.append(np.abs(source.tri_uv[i]-current.tri_uv[tid,order]).max())
        norm_diffs.extend(np.rad2deg(np.arccos(np.clip((source.tri_normals[i]*current.tri_normals[tid,order]).sum(1),-1,1))))
    return dict(source_wholly_inside_cut_triangles=original, corresponded_triangles=len(uv_diffs),
                max_uv_component_error=float(max(uv_diffs)) if uv_diffs else None,
                max_corner_normal_degrees=float(max(norm_diffs)) if norm_diffs else None,
                p99_corner_normal_degrees=float(np.percentile(norm_diffs,99)) if norm_diffs else None)


def source_delta(source, current):
    def signature(mesh,pairs):
        # Compare actual geometry by nearest original bind vertices.
        tree = KDTree(len(source.rest))
        for i,p in enumerate(source.rest): tree.insert(p,i)
        tree.balance()
        lookup = {}
        for t in {t for p in pairs for t in p}:
            hits=[tree.find(mesh.rest[i]) for i in mesh.tris[t]]
            if max(v[2] for v in hits)>1e-5:
                lookup[t]=('unmatched', t)
            else:
                lookup[t]=tuple(sorted(source.keys[v[1]] for v in hits))
        return {frozenset((lookup[i],lookup[j])) for i,j in pairs}
    original=signature(source,source.bind_pairs)
    new=signature(current,current.bind_pairs)
    return dict(original_unique_triangle_pair_signatures=len(original),final_unique_triangle_pair_signatures=len(new),
                common=len(original&new),new=len(new-original),removed=len(original-new))


def glb_summary(path):
    doc,blob = read_glb(path)
    results = dict(sha256=sha(path), bytes=path.stat().st_size,
                   meshes=len(doc.get('meshes',[])),skins=len(doc.get('skins',[])),
                   skin_joints=[len(s['joints']) for s in doc.get('skins',[])],
                   materials=len(doc.get('materials',[])),images=len(doc.get('images',[])),
                   animations=len(doc.get('animations',[])), nodes=len(doc['nodes']))
    result_clips={}
    for action in doc.get('animations',[]):
        bad=[]; channels=Counter(); data_times=[]
        side=action['name'].rsplit('_',1)[-1]
        for channel in action['channels']:
            target=channel['target']
            name=doc['nodes'][target['node']].get('name','')
            match=TARGET.fullmatch(name)
            if not match or match.group(1)!=SIDES.get(side,('',0))[0]:
                bad.append(name)
            channels[target['path']]+=1
            smp=action['samplers'][channel['sampler']]
            ac=doc['accessors'][smp['input']]
            bv=doc['bufferViews'][ac['bufferView']]
            offset=ac.get('byteOffset',0)+bv.get('byteOffset',0)
            step=bv.get('byteStride',4)
            data_times += [struct.unpack_from('<f',blob,offset+i*step)[0] for i in range(ac['count'])]
        result_clips[action['name']]=dict(channels=dict(channels), invalid_bones=bad,
                                          times_s=sorted(set(data_times)),
                                          max_samples=max(doc['accessors'][s['input']]['count'] for s in action['samplers']))
    results['clips']=result_clips
    return results


def rig_compatibility(body_path,clip_path):
    def hierarchy(doc):
        nodes=doc['nodes']
        parents={c:i for i,n in enumerate(nodes) for c in n.get('children',[])}
        locals_={};worlds={}
        for i,n in enumerate(nodes):
            if 'matrix' in n:locals_[i]=np.asarray(n['matrix']).reshape(4,4).T
            else:
                q=n.get('rotation',[0,0,0,1])
                mat=np.eye(4)
                mat[:3,:3]=np.asarray(Quaternion((q[3],*q[:3])).to_matrix())@np.diag(n.get('scale',[1,1,1]))
                mat[:3,3]=n.get('translation',[0,0,0])
                locals_[i]=mat
        def mat(i):
            if i not in worlds:worlds[i]=(mat(parents[i])@locals_[i]) if i in parents else locals_[i]
            return worlds[i]
        result={n['name']:(mat(i),locals_[i],nodes[parents[i]].get('name','') if i in parents else None)
                for i,n in enumerate(nodes) if n.get('name','').startswith('mixamorig:')}
        return result
    mesh_doc,buf=read_glb(body_path)
    body=hierarchy(mesh_doc)
    library=hierarchy(read_glb(clip_path)[0])
    names=set(body)&set(library)
    s=mesh_doc['skins'][0]
    ac=mesh_doc['accessors'][s['inverseBindMatrices']]
    bv=mesh_doc['bufferViews'][ac['bufferView']]
    off=bv.get('byteOffset',0)+ac.get('byteOffset',0)
    stride=bv.get('byteStride',64)
    residual=[]
    for i,node in enumerate(s['joints']):
        inv=np.frombuffer(buf,dtype='<f4',count=16,offset=off+i*stride).reshape(4,4).T
        name=mesh_doc['nodes'][node]['name']
        residual.append(float(np.max(np.abs(body[name][0]@inv-np.eye(4)))))
    return dict(joints_in_both=len(names),body_only=sorted(set(body)-names),library_only=sorted(set(library)-names),
                max_world_matrix_component_error=max(float(np.max(np.abs(body[n][0]-library[n][0]))) for n in names),
                max_local_matrix_component_error=max(float(np.max(np.abs(body[n][1]-library[n][1]))) for n in names),
                differing_joint_parents=[n for n in sorted(names) if body[n][2]!=library[n][2]],
                max_inverse_bind_identity_error=max(residual))


def validator(path, out):
    script = """const fs=require('fs');const v=require(process.argv[1]);v.validateBytes(new Uint8Array(fs.readFileSync(process.argv[2])),{uri:process.argv[2].split('/').pop(),maxIssues:10000}).then(r=>process.stdout.write(JSON.stringify(r,null,2))).catch(e=>{console.error(e);process.exit(1)});"""
    result=subprocess.run(['node','-e',script,str(WORK.parents[4]/'node_modules/gltf-validator'),str(path)],
                          check=True,capture_output=True,text=True)
    report=json.loads(result.stdout)
    out.write_text(json.dumps(report,indent=2)+'\n')
    return {name:report['issues'][name] for name in ['numErrors','numWarnings','numInfos','numHints']}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline',action='store_true')
    parser.add_argument('--diagnose-bind',action='store_true')
    parser.add_argument('--body',type=Path,default=WORK/'body_female_v1.glb')
    parser.add_argument('--library',type=Path,default=WORK/'hand_gestures_female.glb')
    parser.add_argument('--preview',action='store_true',help='Print without replacing final audit files')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    body,rig=new_body(SOURCE)
    source=MeshCheck(body,rig)
    print('SOURCE',json.dumps(source.description()),flush=True)
    if args.baseline: return
    body_hash=sha(args.body)
    body,rig=new_body(args.body)
    mesh=MeshCheck(body,rig)
    details=dict(source_sha256=sha(SOURCE),source=source.description(),body=mesh.description(),nonhand_drift=drift(source,mesh),
                 source_crossing_comparison=source_delta(source,mesh), nonhand_surface=untouched_faces(source,mesh),
                 parent_changes={n:[source.parents.get(n),mesh.parents.get(n)] for n in set(source.parents)|set(mesh.parents)
                                 if source.parents.get(n)!=mesh.parents.get(n)},
                 body_glb=glb_summary(args.body),
                 textures_px={im.name:list(im.size) for im in bpy.data.images if im.type=='IMAGE' and im.size[0]>0})
    print('BODY',json.dumps(details['body']),flush=True)
    if args.diagnose_bind:
        surfaces={tag:Surface(mesh,tag) for tag in SIDES}
        for i,j in sorted(mesh.bind_pairs):
            tag='L' if mesh.regions[i]+mesh.regions[j]>0 else 'R'
            pp=surfaces[tag]
            print('CROSS',i,j,pp.face_labels.get(i,'palm'),pp.face_labels.get(j,'palm'),
                  rounded(mesh.rest[mesh.tri[[i,j]]].mean(1)*1000),flush=True)
        for tag,hand in surfaces.items():print('SHAFT',tag,hand.foreign)
        return
    # Filled after importing the skeleton-only library, with its actual Blender 5 slots.
    if args.library.exists():
        library_hash=sha(args.library)
        details['library_glb']=glb_summary(args.library)
        details['rig_compatibility']=rig_compatibility(args.body,args.library)
        details['gesture_checks']=check_gestures(body,rig,mesh,args.library)
    if args.preview:
        print('DETAIL',json.dumps(details),flush=True)
        return
    details['khronos']={key:validator(p,WORK/('validator_'+key+'.json'))
                        for key,p in [('body',args.body),('library', args.library)] if p.exists()}
    if args.library.exists():
        assert sha(args.library)==library_hash, 'Clip export changed mid-audit; rerun against finished bytes.'
    assert sha(args.body)==body_hash, 'Body export changed mid-audit. Rerun against finished bytes.'
    details['gates']=gates(details)
    (WORK/'audit.json').write_text(json.dumps(details,indent=2)+'\n')
    (WORK/'check.log').write_text(report(details))




class Surface:
    """Define anatomical regions once on the neutral export, never refit them to a posed contact."""
    def __init__(self, mesh, tag):
        self.side,self.sign = SIDES[tag]
        self.pre='mixamorig:'+self.side+'Hand'
        self.tris=mesh.tris
        tri=mesh.tri
        pos=mesh.rest[tri]
        centers=pos.mean(1)
        normals=np.cross(pos[:,1]-pos[:,0],pos[:,2]-pos[:,0])
        normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-20)
        self.owned={}
        self.terminal={}
        self.pulp={}
        self.tips={}
        self.landmarks={}
        self.vertices = mesh.rest
        totals=np.array([[sum(v for n,v in ws.items() if n.startswith(self.pre+d)) for d in DIGITS]
                         for ws in mesh.weights])
        tri_totals=totals[tri].mean(1)
        digits=np.argmax(tri_totals,axis=1)
        proximal=tri_totals.max(1)<.45
        wrist=mesh.joints[self.pre]
        self.wrist=wrist
        knuckles=np.array([mesh.joints[self.pre+d+'1'] for d in DIGITS[:4]])
        across=knuckles[-1]-knuckles[0]
        along=knuckles.mean(0)-wrist
        volar=-self.sign*normalized(np.cross(along,across))
        self.rest_frame=dict(volar_unit=rounded(volar),
                             volar_angle_to_down_deg=math.degrees(math.acos(np.clip(-volar[2],-1,1))),
                             wrist_to_knuckles_mm=round(float(np.linalg.norm(along)*1000),5))
        palm_r=np.array([mesh.joints[self.pre+d+'1'] for d in DIGITS[:4]]).mean(0)
        palmar=(self.sign*centers[:,0]>abs(wrist[0])) & proximal & (normals[:,2]<-.2)
        self.palm=[mesh.tris[i] for i in np.flatnonzero(palmar)]
        self.all_palm=[mesh.tris[i] for i in np.flatnonzero(proximal & (self.sign*centers[:,0]>abs(wrist[0])-.015))]
        self.middle=(wrist+palm_r)/2
        self.face_labels={}
        self.geometry_owned={}
        self.foreign={}
        dists=[]
        for d in DIGITS:
            joints=np.array([mesh.joints[self.pre+d+str(i)] for i in range(1,5)])
            distances=[]
            for a,b in zip(joints[:-1],joints[1:]):
                delta=b-a
                u=np.clip((mesh.rest-a)@delta/max(np.dot(delta,delta),1e-12),0,1)
                distances.append(np.linalg.norm(mesh.rest-(a+u[:,None]*delta),axis=1))
            dists.append(np.min(distances,axis=0))
        dists=np.array(dists).T
        nearest_chain=np.argmin(dists,axis=1)
        sorted_dists=np.sort(dists,axis=1)
        for di,d in enumerate(DIGITS):
            joints=np.array([mesh.joints[self.pre+d+str(i)] for i in range(1,5)])
            distal=normalized(joints[3]-joints[2])
            if np.linalg.norm(distal)<.9: distal=normalized(joints[2]-joints[1])
            vmask=totals[:,di]>.56
            if not vmask.any(): raise ValueError(f'No distal weights for {tag} {d}')
            distal_proj=(mesh.rest-joints[2])@distal
            end=distal_proj[vmask].max()
            tip_vertices=np.flatnonzero(vmask & (distal_proj>end-.0018))
            self.tips[d]=list({mesh.keys[i]:int(i) for i in tip_vertices}.values())
            tip=mesh.rest[self.tips[d]].mean(0)
            owned=(digits==di) & ~proximal & (self.sign*centers[:,0]>abs(wrist[0])-.01)
            self.owned[d]=[mesh.tris[i] for i in np.flatnonzero(owned)]
            for i in np.flatnonzero(owned):self.face_labels[i]=d
            pad_dir=normalized(distal+.65*normalized(np.array([0.,0.,-1])-distal*(-distal[2])))
            region=owned & (np.linalg.norm(pos-tip,axis=2).max(1)<.017)
            if not region.any(): raise ValueError(f'No terminal triangles for {tag} {d}')
            support=((pos[region]-tip)@pad_dir).max()
            # The same 2.65 mm forward/volar support slab used in the earlier review.
            # Intersect with the slab geometrically instead of accepting the whole selected triangle.
            self.pulp[d]=[]
            for i in np.flatnonzero(region & (normals@pad_dir>.32)):
                face=mesh.tris[i]
                ds=(pos[i]-tip)@pad_dir-support+.00265
                if max(ds)<0:continue
                polygon=[]
                for k in range(3):
                    a,b=face[k],face[(k+1)%3]
                    v1,v2=ds[k],ds[(k+1)%3]
                    if v1>=0:polygon.append((a,a,0.))
                    if (v1>=0)!=(v2>=0):polygon.append((a,b,float(v1/(v1-v2))))
                for k in range(1,len(polygon)-1):
                    self.pulp[d].append((polygon[0],polygon[k],polygon[k+1]))
            if not self.pulp[d]:raise ValueError(f'Empty pad {tag} {d}')
            tip_cut=end-.008
            cap=region & (distal_proj[tri].mean(1)>tip_cut)
            self.terminal[d]=[mesh.tris[i] for i in np.flatnonzero(cap)]
            unique=np.unique(tri[owned])
            root=joints[0]
            axis=normalized(tip-root)
            proj=(mesh.rest-root)@axis
            length=np.dot(tip-root,axis)
            if length>1e-6:
                geometric=(nearest_chain==di)&((sorted_dists[:,1]-sorted_dists[:,0])>.002)&(sorted_dists[:,0]<.014)&(proj>.45*length)
                foreign=totals[:,[i for i in range(len(DIGITS)) if i!=di]].sum(1)
                self.foreign[d]=dict(samples=int(geometric.sum()), with_foreign=int(((foreign>0)&geometric).sum()),
                                     max_foreign=float(foreign[geometric].max()) if geometric.any() else None)
            self.landmarks[d]=dict(root_mm=rounded(root*1000), distal_tip_mm=rounded(tip*1000),
                                   axis_unit=rounded(axis), distal_axis_unit=rounded(distal),
                                   pad_support_unit=rounded(pad_dir),root_tip_length_mm=float(length*1000),
                                   pulp_triangles=len(self.pulp[d]),terminal_triangles=len(self.terminal[d]),
                                   center_tip_vertices=len(self.tips[d]))
        thumb=self.landmarks['Thumb']
        axis=np.asarray(thumb['axis_unit'])
        root=np.asarray(thumb['root_mm'])/1000
        tri=self.vertices[np.asarray(self.owned['Thumb'])]
        self.rest_frame['thumb_angle_to_forward_deg']=math.degrees(math.acos(np.clip(-axis[1],-1,1)))
        self.rest_frame['thumb_direction_unit']=thumb['axis_unit']
        self.rest_frame['thumb_root_to_tip_mm']=thumb['root_tip_length_mm']
        joint_mm=1000*np.array([mesh.joints[self.pre+'Thumb'+str(i)] for i in range(1,5)])
        self.rest_frame['thumb_joint_intervals_mm']=rounded(np.linalg.norm(np.diff(joint_mm,axis=0),axis=1))
        sections={}
        side_axis=normalized(np.cross(axis,[0,0,1]))
        up=normalized(np.cross(side_axis,axis))
        for frac in (.30,.50,.70,.85,.95):
            dd=(tri-root)@axis-thumb['root_tip_length_mm']*.001*frac
            coords=[]
            for k in range(3):
                j=(k+1)%3
                mask=(dd[:,k]>=0)!=(dd[:,j]>=0)
                interp=dd[mask,k]/(dd[mask,k]-dd[mask,j])
                v=tri[mask,k]+(tri[mask,j]-tri[mask,k])*interp[:,None]
                coords.extend(v)
            if coords:
                shell=np.asarray(coords)*1000
                sections[str(frac)]={'width_mm':round(float(np.ptp(shell@side_axis)),5),
                                     'depth_mm':round(float(np.ptp(shell@up)),5)}
        self.rest_frame['thumb_sections_frac_of_root_to_tip']=sections
        self.foreign['note']='Independent shaft sample uses proximity to a sole bone chain, next-chain distance margin >2 mm, centerline distance <14 mm, and distal shaft position beyond 45 percent.'
        kd=BVHTree.FromPolygons(mesh.rest.tolist(),self.palm,all_triangles=True)
        self.middle[2]=kd.find_nearest(self.middle)[0][2]

    def posed(self,points):
        # Clipped triangles carry barycentric coordinates on the original exported triangle.
        vertices=list(points)
        pads={}
        for d in DIGITS:
            indices={}
            faces=[]
            for face in self.pulp[d]:
                tri=[]
                for key in face:
                    a,b,t=key
                    if a==b:tri.append(a);continue
                    if key not in indices:
                        indices[key]=len(vertices)
                        vertices.append(points[a]*(1-t)+points[b]*t)
                    tri.append(indices[key])
                faces.append(tuple(tri))
            pads[d]=faces
        return np.array(vertices),pads

    def gauge(self,points,axis,center):
        """Nearest axis/triangle distance after orthogonal projection onto a transverse plane."""
        axis=normalized(np.asarray(axis,dtype=float))
        center=np.asarray(center,dtype=float)
        def radial(points):
            return points-np.sum(points*axis,axis=-1,keepdims=True)*axis
        by_part={}
        min_vectors={}
        contacts={}
        count=0
        for d,faces in {'Palm':self.all_palm,**self.owned}.items():
            tr=radial(points[np.asarray(faces)]-center)
            edges=np.roll(tr,-1,axis=1)-tr
            u=np.clip(-np.sum(tr*edges,axis=-1)/np.maximum(np.sum(edges*edges,axis=-1),1e-20),0,1)
            candidates=tr+u[:,:,None]*edges
            dist=np.linalg.norm(candidates,axis=2)
            nearest_edge=np.argmin(dist,axis=1)
            nearest_pts=candidates[np.arange(len(tr)),nearest_edge]
            clearance=np.linalg.norm(nearest_pts,axis=1)
            signs=np.cross(edges,-tr)@axis
            interior=(signs.min(1)>0)|(signs.max(1)<0)
            clearance[interior]=0
            best=int(np.argmin(clearance))
            by_part[d]=round(float(clearance[best]*1000),5)
            min_vectors[d]=rounded(nearest_pts[best]*1000)
            contacts[d]=int((clearance<.020).sum())
            count+=contacts[d]
        return dict(diameter_mm=40,axis=rounded(axis), center_mm=rounded(center*1000),
                    min_axis_to_skin_mm=by_part, nearest_radial_offset_mm=min_vectors,
                    penetration_triangle_counts=contacts,total_penetrations=count)

    def measures(self,points,gesture):
        vertices,pads=self.posed(points)
        tips={d:points[self.tips[d]].mean(0) for d in DIGITS}
        result=dict(tip_center_mm={d:rounded(p*1000) for d,p in tips.items()})
        if gesture in ('pinch','ok','grip_small'):
            result['pulp_to_pulp']=nearest(vertices,pads['Thumb'],pads['Index'])
            if gesture in ('pinch','ok'):
                contact=result['pulp_to_pulp']
                normals=[]
                near_area={}
                trees={d:BVHTree.FromPolygons(vertices.tolist(),pads[d],all_triangles=True)
                       for d in ('Thumb','Index')}
                for d,other,w in zip(('Thumb','Index'),('Index','Thumb'),contact['witness_world_mm']):
                    wr=np.asarray(w)*.001
                    normals.append(np.asarray(trees[d].find_nearest(wr)[1]))
                    triangles=vertices[np.asarray(pads[d])]
                    area=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)*500000
                    # Three-point barycentric quadrature quantifies near-contact footprint separately
                    # from the exact minimum and respects the curved finite pulp surface.
                    samples=(triangles.sum(1)[:,None,:]+triangles)/4
                    fractions=[np.mean([trees[other].find_nearest(p)[3]<.001 for p in ts]) for ts in samples]
                    near_area[d]=round(float(area@fractions),4)
                contact['witness_outward_normals_dot']=round(float(normals[0]@normals[1]),6)
                contact['estimated_area_within_1mm_sqmm']=near_area

            result['terminal_to_terminal']=nearest(vertices,self.terminal['Thumb'],self.terminal['Index'])
        if gesture in ('fist','grip_small','thumbs_up','point','peace'):
            digits={'fist':DIGITS,'grip_small':DIGITS,'thumbs_up':DIGITS[:4],'peace':DIGITS[2:4],'point':DIGITS[1:4]}[gesture]
            result['pulp_to_palm_mm']={d:nearest(vertices,pads[d],self.palm)['distance_mm'] for d in digits}
            result['terminal_to_palm_mm']={d:nearest(vertices,self.terminal[d],self.palm)['distance_mm'] for d in digits}
            tree=BVHTree.FromPolygons(vertices.tolist(),self.palm,all_triangles=True)
            result['tip_center_to_palm_mm']={d:round(tree.find_nearest(tips[d])[3]*1000,5) for d in digits}
        if gesture=='fist':
            result['thumb_pulp_to_folded_parts_mm']={
                d:nearest(vertices,pads['Thumb'],self.owned[d])['distance_mm'] for d in DIGITS[:4]}
        if gesture=='thumbs_up':
            result['thumb_above_highest_other_center_mm']=float((tips['Thumb'][2]-max(tips[d][2] for d in DIGITS[:4]))*1000)
            result['thumb_tip_surface_above_other_tip_surfaces_mm']=float(1000*(points[np.unique(self.terminal['Thumb']),2].max()-
                max(points[np.unique(self.terminal[d]),2].max() for d in DIGITS[:4])))
        return result


def check_gestures(body,rig,mesh,library):
    hand={tag:Surface(mesh,tag) for tag in SIDES}
    face_labels=[]
    for i,region in enumerate(mesh.regions):
        if region:
            selected=hand['L' if region==1 else 'R']
            face_labels.append(selected.side+selected.face_labels.get(i,'Palm'))
        else:
            face_labels.append('Body')
    bpy.ops.import_scene.gltf(filepath=str(library))
    result={}
    pose_samples={}
    for tag in SIDES:
        sel=hand[tag]
        for gesture in GESTURES:
            name='hand_'+gesture+'_'+tag
            action=bpy.data.actions.get(name)
            if not action:
                result[name]={'error':'Action missing after glTF import'}
                continue
            ad=rig.animation_data_create()
            ad.action=None
            for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
            ad.action=action
            ad.action_slot=action.slots[0]
            bpy.context.scene.frame_set(int(action.frame_range[0]))
            bpy.context.view_layer.update()
            points=world_points(body,evaluated=True)
            r=dict(action_slot=ad.action_slot.identifier,frame=float(action.frame_range[0]),
                   crossings=mesh.crossing_result(mesh.crossings(points),face_labels),
                   nonhand_pose_drift_mm=float(np.linalg.norm(points-mesh.bind,axis=1)[np.abs(mesh.rest[:,0])<=.2862].max()*1000),
                   max_vertex_motion_mm=float(np.linalg.norm(points-mesh.bind,axis=1).max()*1000))
            r.update(sel.measures(points,gesture))
            pose_samples[name]=points.astype(np.float32)
            if gesture=='grip_small':
                source=WORK/'hand_gestures_female.json'
                data=json.loads(source.read_text()) if source.is_file() else {}
                gauge=data.get('grip_gauges',{}).get(tag)
                if gauge:
                    r['cylinder']=sel.gauge(points,gauge['axis'],np.array(gauge['center_mm'])/1000)
            result[name]=r
            print('POSE', name, 'intersections',r['crossings']['whole'], 'pulp',r.get('pulp_to_pulp',{}).get('distance_mm'),
                  'tip to palm',r.get('pulp_to_palm_mm'), 'thumb Z',r.get('thumb_above_highest_other_center_mm'),flush=True)
    json_check={}
    if library.resolve()==(WORK/'hand_gestures_female.glb').resolve() and (WORK/'hand_gestures_female.json').is_file():
        json_check=check_json_replay(mesh.rest,pose_samples)
    return dict(clips=result,json_replay=json_check,rest_frame={tag:h.rest_frame for tag,h in hand.items()},
                bind_landmarks={tag:h.landmarks for tag,h in hand.items()},
                shaft_ownership={tag:h.foreign for tag,h in hand.items()},
                palm_triangles={tag:len(h.palm) for tag,h in hand.items()})


def check_json_replay(export_rest,export_poses):
    path=WORK/'hand_gestures_female.json'
    blend=WORK/'body_female_v1.blend'
    data=json.loads(path.read_text())
    bpy.ops.wm.open_mainfile(filepath=str(blend),load_ui=False,use_scripts=False)
    body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    if rig.animation_data:
        rig.animation_data.action=None
        for t in rig.animation_data.nla_tracks:t.mute=True
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
    native_rest=world_points(body)
    tree=KDTree(len(native_rest))
    for i,p in enumerate(native_rest):tree.insert(p,i)
    tree.balance()
    mapping=[tree.find(p) for p in export_rest]
    ids=np.array([i for _,i,_ in mapping])
    rest_err=max(v[2] for v in mapping)*1000
    per_clip={}
    for name,export_pts in export_poses.items():
        for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
        for bone,angles in data['gestures'][name].items():
            pb=rig.pose.bones[bone]
            assert pb.rotation_mode=='QUATERNION'
            pb.rotation_quaternion=Euler(tuple(math.radians(v) for v in angles),'XYZ').to_quaternion()
        for bone,scale in data.get('scales',{}).get(name,{}).items():rig.pose.bones[bone].scale=scale
        bpy.context.view_layer.update()
        coords=world_points(body,evaluated=True)[ids]
        per_clip[name]=round(float(np.linalg.norm(coords-export_pts,axis=1).max()*1000),6)
    return dict(blend_sha256=sha(blend),json_sha256=sha(path),rest_max_mm=rest_err,
                per_clip_vertex_max_mm=per_clip,max_over_all_mm=max(per_clip.values()) if per_clip else None)


def gates(data):
    body=data['body']
    bg=data['body_glb']
    outcome={
        'static_one_mesh_one_skin_65_joints_no_animation':(bg['meshes'],bg['skins'],bg['skin_joints'],bg['animations'])==(1,1,[65],0),
        'all_parents_preserved':not data['parent_changes'],
        'all_vertex_weights':body['max_influences']<=4 and body['unweighted']==0 and body['max_weight_sum_error']<1e-5,
        'zero_mixed_digit_weights':body['mixed_digit_any']==0,
        'triangles_within_budget':body['triangles']<=10000 and max(body['triangles_touching_wrist_distal'].values())<=3000,
        'preserved_vertex_positions':all(v['maximum_mm']<=.5 for v in data['nonhand_drift']['source_to_final'].values()),
        'every_texture_within_1024':bool(data['textures_px']) and all(max(v)<=1024 for v in data['textures_px'].values()),
        'khronos_body_zero_errors_warnings':not (data['khronos']['body']['numErrors'] or data['khronos']['body']['numWarnings'])
    }
    if 'gesture_checks' not in data:return outcome
    gc=data['gesture_checks']
    clips=gc['clips']
    exported=data['library_glb']
    all_names={'hand_'+g+'_'+s for g in GESTURES for s in SIDES}
    outcome.update({
        'clip_names_correct_one_sample_finger_tracks_only':set(exported['clips'])==all_names and all(v['max_samples']==1 and
            not v['invalid_bones'] and set(v['channels'])=={'rotation'} for v in exported['clips'].values()),
        'clip_library_skeleton_only':exported['meshes']==0 and data['rig_compatibility']['joints_in_both']==65,
        'free_shafts_zero_foreign_weights':all(side[d]['max_foreign']==0 for side in gc['shaft_ownership'].values() for d in DIGITS),
        'zero_whole_body_crossings_bind_and_all_18_poses':body['crossings']['whole']==0 and len(clips)==18 and
            all(v.get('crossings',{}).get('whole')==0 for v in clips.values()),
        'all_pinch_and_ok_pulp_gaps_under_1_mm':all(clips['hand_'+g+'_'+t]['pulp_to_pulp']['distance_mm']<1
            for t in SIDES for g in ('pinch','ok')),
        'fist_four_pulps_within_1_mm_of_palmar_skin':all(clips['hand_fist_'+t]['pulp_to_palm_mm'][d]<1 for t in SIDES for d in DIGITS[:4]),
        'fist_thumb_pulp_within_1_mm_of_a_folded_digit':all(min(clips['hand_fist_'+t]['thumb_pulp_to_folded_parts_mm'].values())<1 for t in SIDES),
        'thumbs_up_higher_than_other_tips':all(clips['hand_thumbs_up_'+t]['thumb_above_highest_other_center_mm']>0 for t in SIDES),
        'grip_skin_and_center_gaps_15_to_30_mm':all(15<=v<=30 for t in SIDES for key in ('pulp_to_palm_mm','tip_center_to_palm_mm')
            for v in clips['hand_grip_small_'+t][key].values()),
        'grips_clear_declared_40mm_gauges':all(clips['hand_grip_small_'+t].get('cylinder',{}).get('total_penetrations')==0 for t in SIDES),
        'khronos_library_zero_errors_warnings':not (data['khronos']['library']['numErrors'] or data['khronos']['library']['numWarnings'])
    })
    return outcome


def report(details):
    lines=['Female body and clip-library audit','Blender '+bpy.app.version_string, '', *[('PASS ' if passed else 'FAIL ')+name for name,passed in details['gates'].items()], '']
    for key in ('body_glb','library_glb','source','body','nonhand_drift','source_crossing_comparison','nonhand_surface','rig_compatibility','parent_changes','textures_px','khronos'):
        if key in details:
            data={k:v for k,v in details[key].items() if k!='clips'}
            lines.append(f'{key} {json.dumps(data,sort_keys=True)}')
    if 'gesture_checks' in details:
        gc=details['gesture_checks']
        lines.append('Anatomical rest frames '+json.dumps(gc['rest_frame']))
        lines.append('Hand shaft verification '+json.dumps(gc['shaft_ownership']))
        lines.append('JSON vs exported GLB skin playback '+json.dumps(gc['json_replay']))
        for n,r in gc['clips'].items():
            lines.append(n+' '+json.dumps({k:v for k,v in r.items() if k!='tip_center_mm'},sort_keys=True))
    return '\n'.join(lines)+'\n'


if __name__=='__main__':
    main()
