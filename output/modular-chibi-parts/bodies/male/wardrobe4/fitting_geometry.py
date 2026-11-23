"""Region-aware transfer of neutral rest-space geometry to the male bind surface."""
from collections import defaultdict
import math

from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
import numpy as np


def arrays(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    points = np.empty(len(mesh.vertices)*3, dtype=np.float32)
    faces = np.empty(len(mesh.loop_triangles)*3, dtype=np.int32)
    mesh.vertices.foreach_get('co', points)
    mesh.loop_triangles.foreach_get('vertices', faces)
    return points.reshape(-1,3), faces.reshape(-1,3)


def weights(obj, names):
    ids = {name:i for i,name in enumerate(names)}
    groups = [ids.get(g.name) for g in obj.vertex_groups]
    out = np.zeros((len(obj.data.vertices),len(names)),dtype=np.float32)
    for vert in obj.data.vertices:
        for item in vert.groups:
            i = groups[item.group]
            if i is not None:
                out[vert.index,i] = item.weight
    assert (out.sum(axis=1)>0).all(), obj.name
    return out / out.sum(axis=1,keepdims=True)


def limit_weights(w):
    idx = np.argpartition(w, -4,axis=1)[:,-4:]
    values = w[np.arange(len(w))[:,None],idx]
    values /= values.sum(axis=1,keepdims=True)
    w = np.zeros_like(w)
    w[np.arange(len(w))[:,None],idx] = values
    return w


def tree(points, faces):
    return BVHTree.FromPolygons(points.tolist(),faces,all_triangles=True,epsilon=0)


def region(name):
    joint = name.split(':')[-1]
    if joint in ('Head','HeadTop_End'):
        return 'head'
    for side in ('Left','Right'):
        if not joint.startswith(side):
            continue
        part = joint[len(side):]
        if part in ('Foot','ToeBase','Toe_End'):
            return side+' foot'
        if part in ('Leg','UpLeg'):
            return side+' leg'
        if part.startswith(('Arm','ForeArm','Hand')):
            return side+' arm'
    return 'torso'


def region_mesh(points, faces, w, names):
    labels = [region(name) for name in names]
    categories = sorted(set(labels))
    grouped = np.stack([w[:,np.array(labels)==group].sum(axis=1) for group in categories],axis=1)
    triangle_w = grouped[faces].mean(axis=1)
    ids = {}
    for j,group in enumerate(categories):
        ids[group] = np.flatnonzero(triangle_w[:,j] >= .24)
    return ids, grouped, categories


def weld_graph(points, faces, links=()):
    # UV/material seams share the displacement without changing the input
    # topology, UV loops or texture islands.
    _, inverse = np.unique(np.round(points,6),axis=0,return_inverse=True)
    inverse = inverse.reshape(-1)
    if links:
        parent = np.arange(int(inverse.max())+1)
        def root(i):
            while parent[i]!=i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        for left,right in links:
            parent[root(inverse[left])] = root(inverse[right])
        _,inverse = np.unique([root(i) for i in inverse],return_inverse=True)
    edges = inverse[faces]
    edges = np.vstack((edges[:,[0,1]],edges[:,[0,2]],edges[:,[1,2]]))
    edges = np.unique(np.vstack((edges,edges[:,::-1])),axis=0)
    p,q = edges.T
    size = int(inverse.max())+1
    degree = np.maximum(1,np.bincount(p,minlength=size))
    copies = np.bincount(inverse,minlength=size)
    return inverse,p,q,degree,copies


def welded(values, graph):
    inverse,_,_,_,copies = graph
    def mean(v):
        return (np.bincount(inverse,weights=v,minlength=len(copies))/copies)[inverse]
    return mean(values) if values.ndim==1 else np.stack([mean(v) for v in values.T],axis=1)


def laplacian(values,graph):
    inverse,p,q,degree,copies = graph
    def average(v):
        v = np.bincount(inverse,weights=v,minlength=len(copies))/copies
        return (np.bincount(p,weights=v[q],minlength=len(copies))/degree)[inverse]
    return average(values) if values.ndim==1 else np.stack([average(v) for v in values.T],axis=1)


def barycentric(p, tri):
    a,b,c = np.asarray(tri,dtype=np.float64)
    ab,ac,ap = b-a,c-a,np.asarray(p)-a
    u,v,w = np.dot(ab,ab),np.dot(ab,ac),np.dot(ac,ac)
    denom = u*w-v*v
    if denom < 1e-18:
        return np.array([1.,0.,0.])
    av,cv = np.dot(ap,ab),np.dot(ap,ac)
    q,r = (w*av-v*cv)/denom,(u*cv-v*av)/denom
    ratio = np.maximum(0,[1-q-r,q,r])
    return ratio/ratio.sum()


def vertex_cloud(points, ids):
    kd = KDTree(len(ids))
    for i in ids:
        kd.insert(points[i],int(i))
    kd.balance()
    return kd


class SurfaceField:
    def __init__(self, neutral, male, neutral_rig, male_rig, names):
        src,vf = arrays(neutral)
        dst,mf = arrays(male)
        nw,mw = weights(neutral,names),weights(male,names)
        rg,blend,regions = region_mesh(src,vf,nw,names)
        male_regions,_,_ = region_mesh(dst,mf,mw,names)
        heads = np.array([male_rig.data.bones[n].head_local-neutral_rig.data.bones[n].head_local
                          for n in names])
        prior = nw @ heads
        src_norm = np.array([v.normal for v in neutral.data.vertices])
        self.fields = {}
        self.target = {}
        self.male_faces = mf
        self.male = dst
        self.weights = mw
        self.neutral = src
        self.blend = blend
        self.regions = regions
        for group in regions:
            source_ids = np.unique(vf[rg[group]])
            target_faces = mf[male_regions[group]]
            target_tree = tree(dst,target_faces.tolist())
            self.target[group] = target_tree,target_faces
            field = np.zeros_like(src)
            for i in source_ids:
                hint = src[i] + prior[i]
                origin = Vector(hint)
                normal = Vector(src_norm[i])
                hit,nt,_,dist = target_tree.find_nearest(origin)
                # Prefer a same-facing projection to avoid swapping the top and
                # bottom of the scalp, soles, fingers, and narrow folds.
                if normal.length > .5:
                    for direction in (normal,-normal):
                        cand,cn,_,cd = target_tree.ray_cast(origin,direction,.045)
                        if cand is not None and cn.dot(normal) > .45 and (cd < dist*2+.006 or nt.dot(normal)<.3):
                            hit,nt,dist = cand,cn,cd
                field[i] = np.asarray(hit)-src[i]
            self.fields[group] = vertex_cloud(src,source_ids),field
        self.surface_cloud = vertex_cloud(src,np.arange(len(src)))

    def apply(self, points, faces, w, names, slot, links=()):
        offsets = np.zeros_like(points)
        transferred = w.copy()
        assignment = []
        graph = weld_graph(points,faces,links)
        for i,p in enumerate(points):
            if slot=='hair':
                group_w = {'head':1.}
            elif slot=='shoes':
                group_w = {('Left' if p[0]>0 else 'Right')+' foot':1.}
            else:
                parts = defaultdict(float)
                for j in np.flatnonzero(w[i]):
                    parts[region(names[j])] += w[i,j]
                if slot in ('top','dress') and p[2]<.46:
                    # The hem inherits broad hip motion; a skirt must retain
                    # its bridging silhouette between the two legs.
                    mix = .66 if slot=='dress' else .30
                    parts = {k:(1-mix)*v for k,v in parts.items()}
                    parts['torso'] = parts.get('torso',0)+mix
                group_w = parts
            dominant = max(group_w,key=group_w.get)
            assignment.append(dominant)
            for group, amount in group_w.items():
                kd,displacement = self.fields[group]
                neighbors = kd.find_n(p,18)
                ids = [j for _,j,_ in neighbors]
                distance = np.array([d for _,_,d in neighbors])
                radius = .027 if slot in ('dress','bottom') else .019
                influence = np.exp(-(distance**2-distance.min()**2)/(2*radius**2))
                offsets[i] += amount * np.average(displacement[ids],axis=0,weights=influence)
            target,tf = self.target[dominant]
            q,_,hit,dist = target.find_nearest(p+offsets[i])
            if slot in ('top','bottom') and np.linalg.norm(offsets[i])>.008 and dist < .025:
                tri = tf[hit]
                inherited = barycentric(q,self.male[tri]) @ self.weights[tri]
                mix = min(.28, 8*np.linalg.norm(offsets[i]))
                transferred[i] = (1-mix)*w[i] + mix*inherited
        # Smooth only the displacement, retaining seams and garment detail.
        offsets = welded(offsets,graph)
        if slot=='dress':
            lower = points[:,2] < .39
            coords = np.column_stack((points,np.ones(len(points))))
            if lower.sum()>8:
                affine = np.linalg.lstsq(coords[lower],offsets[lower],rcond=None)[0]
                strength = .76*np.clip((.42-points[:,2])/.10,0,1)
                offsets = (1-strength[:,None])*offsets + strength[:,None]*(coords@affine)
        for _ in range(9 if slot in ('dress','bottom') else 4):
            offsets = .60*offsets + .40*laplacian(offsets,graph)
        return points+offsets,limit_weights(welded(transferred,graph)),assignment,graph


def shoe_layer_links(shoe, points, w):
    """Keep authored liner and paired sole columns on the same displacement."""
    groups = defaultdict(set)
    for poly in shoe.data.polygons:
        material = shoe.data.materials[poly.material_index].name
        for prefix,kind in (('Purple lining','liner'),('Purple collar piping','collar'),
                            ('Deep purple tread','tread'),('Purple upper','shell'),
                            ('Ivory midsole','midsole'),('Ivory rubber','shell')):
            if material.startswith(prefix):
                groups[kind].update(poly.vertices[:])
                break
    shell = groups['shell'] | groups['midsole'] | groups['tread'] | groups['collar']
    if not groups['liner'] or not shell:
        return []
    outside = vertex_cloud(points,sorted(shell))
    flattened = points.copy()
    flattened[:,2] = 0
    sole_map = vertex_cloud(flattened,sorted(groups['tread']))
    links = []
    for inner in sorted(groups['liner']):
        if inner in shell:
            continue
        for _,outer,distance in outside.find_n(points[inner],min(12,len(shell))):
            if distance>.0030:
                break
            if np.max(abs(w[inner]-w[outer]))<.001:
                links.append((inner,outer))
                break
        # Footbed and outsole have a common planar triangulation. Keep the
        # central paired columns together even where the tread is thicker.
        if points[inner,2]<.024:
            for _,outer,distance in sole_map.find_n(flattened[inner],min(9,len(groups['tread']))):
                if distance>.0006:
                    break
                thickness = points[inner,2]-points[outer,2]
                if .0008<thickness<.012 and np.max(abs(w[inner]-w[outer]))<.001:
                    links.append((inner,outer))
                    break
    # The toe's sidewall and tread perimeter are concentric bevel rings.
    # Couple their displacement even when the vertical layer spacing is
    # wider than the liner thickness.
    toe_mid = sorted(i for i in groups['midsole'] if points[i,1]<-.064)
    if toe_mid:
        mids = vertex_cloud(flattened,toe_mid)
        for outer in sorted(groups['tread']):
            if points[outer,1]>=-.064:
                continue
            for _,i,dist in mids.find_n(flattened[outer],min(10,len(toe_mid))):
                if dist>.0045:
                    break
                dz = points[i,2]-points[outer,2]
                if .002<dz<.019:
                    links.append((outer,i))
                    break
    return links
