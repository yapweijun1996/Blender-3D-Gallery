"""Audit final GLB accessors, source skin correspondence, UV maps and geometric fit."""
import sys,struct,json,hashlib
from pathlib import Path
from collections import Counter
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from face import *
from regions import masks
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

class GLB:
    def __init__(self,path):
        raw=path.read_bytes()
        size=struct.unpack_from("<I",raw,12)[0]
        self.doc=json.loads(raw[20:20+size])
        self.binary=raw[28+size:]
        self.sha=hashlib.sha256(raw).hexdigest()
        self.prim=self.doc["meshes"][0]["primitives"][0]
    def accessor(self,index):
        a=self.doc["accessors"][index]
        dtypes={5121:"u1",5123:"<u2",5125:"<u4",5126:"<f4"}
        dt=np.dtype(dtypes[a["componentType"]])
        dim={"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4,"MAT4":16}[a["type"]]
        def read(ref,n,width,dtype):
            v=self.doc["bufferViews"][ref["bufferView"]]
            return np.ndarray((n,width),dtype,self.binary,v.get("byteOffset",0)+ref.get("byteOffset",0),
                       strides=(v.get("byteStride",width*dtype.itemsize),dtype.itemsize))
        result=(read(a,a["count"],dim,dt) if "bufferView" in a else np.zeros((a["count"],dim),dt))
        if "sparse" in a:
            sp=a["sparse"]
            indices=read(sp["indices"],sp["count"],1,np.dtype(dtypes[sp["indices"]["componentType"]]))
            result=result.copy()
            result[indices.ravel()]=read(sp["values"],sp["count"],dim,dt)
        return result
    def attr(self,k):
        return self.accessor(self.prim["attributes"][k])
    def joints(self):
        return [self.doc["nodes"][n]["name"] for n in self.doc["skins"][0]["joints"]]
    def triangles(self):
        return self.accessor(self.prim["indices"]).reshape(-1,3)
    def positions(self):
        return self.attr("POSITION")[:,[0,2,1]].astype(float)*[1,-1,1]
    def weights(self):
        labels=self.joints()
        return [{labels[i]:float(w) for i,w in zip(ids,ws) if w>0} for ids,ws in zip(self.attr("JOINTS_0"),self.attr("WEIGHTS_0"))]

def components(xyz,idx):
    unique,inv=np.unique(xyz.round(6),axis=0,return_inverse=True)
    adj=[set() for p in unique]
    for a,b,c in inv[idx]:
        adj[a].update((b,c));adj[b].update((c,a));adj[c].update((a,b))
    todo=set(range(len(unique)))
    out=[]
    while todo:
        seed=todo.pop()
        stack=[seed];verts=[seed]
        while stack:
            nxt=adj[stack.pop()]&todo
            todo-=nxt
            stack.extend(nxt);verts.extend(nxt)
        coords=unique[verts]
        out.append({"vertices":len(verts),"triangles":int(np.isin(inv[idx[:,0]],verts).sum()),
                    "min_xyz_m":coords.min(0).tolist(),"max_xyz_m":coords.max(0).tolist()})
    return sorted(out,key=lambda c:-c["vertices"])

def main():
    base=GLB(BASE)
    asset=GLB(ROOT/"body_expressions.glb")
    hair=GLB(HAIR)
    g=asset.doc
    mesh=g["meshes"][0]
    names=mesh["extras"]["targetNames"]
    assert len(g["meshes"])==len(g["skins"])==len(mesh["primitives"])==1
    assert names==["expr_"+s for s in NAMES[1:]]
    assert mesh["weights"]==[0,0,0]
    assert len(asset.joints())==65 and asset.joints()==base.joints()
    # The denser face atlas adds UV seam vertices. Match physical positions and
    # oriented faces independently of the exporter's buffer order or new splits.
    pa,pb=asset.positions(),base.positions()
    points,source_ids=np.unique(pb,axis=0,return_inverse=True)
    src_tree=KDTree(len(points))
    for i,point in enumerate(points):src_tree.insert(point,i)
    src_tree.balance()
    matched=np.array([src_tree.find(v)[1] for v in pa])
    position_error=float(np.linalg.norm(pa-points[matched],axis=1).max())
    assert position_error<1e-6,position_error
    def tri_keys(tris,ids):
        def rotate(f):
            t=tuple(ids[f])
            return min(t,t[1:]+t[:1],t[2:]+t[:2])
        return Counter(rotate(f) for f in tris)
    idx=asset.triangles()
    assert tri_keys(idx,matched)==tri_keys(base.triangles(),source_ids)
    wa,wb=asset.weights(),base.weights()
    options={}
    for v,weights in zip(source_ids,wb):options.setdefault(v,[]).append(weights)
    werr=0
    for ws,v in zip(wa,matched):
        candidates=[s for s in options[v] if ws.keys()==s.keys()]
        assert candidates
        werr=max(werr,min(max(abs(w-s[k]) for k,w in ws.items()) for s in candidates))
    ibm=lambda obj:obj.accessor(obj.doc["skins"][0]["inverseBindMatrices"])
    bind_err=float(np.abs(ibm(asset)-ibm(base)).max())
    assert werr<1e-5 and bind_err<1e-5
    p=asset.positions()
    h=hair.positions()
    htree=BVHTree.FromPolygons(h.tolist(),hair.triangles().tolist(),all_triangles=True)
    hairline=np.array([htree.find_nearest(v)[3] for v in p])<=.016
    zones=masks(p)
    def counts(mask,points=p):
        return {"glb_vertices":int(mask.sum()),"unique_positions":int(len(np.unique(points[mask].round(6),axis=0)))}
    def clearance(points):
        tree=BVHTree.FromPolygons(points.tolist(),idx.tolist(),all_triangles=True)
        signed=[]
        euclidean=[]
        for v in h:
            loc,n,_,distance=tree.find_nearest(v)
            signed.append((v-np.array(loc))@np.array(n))
            euclidean.append(distance)
        return {"hair_vertices_tested":len(h),"hair_vertices_inside":int(np.count_nonzero(np.array(signed)<0)),
                "triangle_overlap_pairs":len(tree.overlap(htree)),"min_signed_mm":round(min(signed)*1000,6),
                "min_euclidean_mm":round(min(euclidean)*1000,6)},np.array(euclidean)

    def guarded_surface_bound(delta):
        # Distance to a surface is 1-Lipschitz. A patch whose bounding ball
        # misses the 16 mm hair envelope cannot contribute to the hairline bound.
        def visit(tri,vec,level):
            maximum=np.linalg.norm(vec,axis=1).max()
            if maximum==0:return 0.
            center=tri.mean(0)
            radius=np.linalg.norm(tri-center,axis=1).max()
            if htree.find_nearest(center)[3]-radius>.016:return 0.
            if radius<.00035 or level>=9:return maximum
            m=(tri+np.roll(tri,-1,axis=0))/2
            v=(vec+np.roll(vec,-1,axis=0))/2
            bounds=[visit(m,v,level+1)]
            for k in range(3):
                bounds.append(visit(np.array([tri[k],m[k],m[k-1]]),np.array([vec[k],v[k],v[k-1]]),level+1))
            return max(bounds)
        active=(delta[idx]!=0).any(axis=(1,2))
        return 1000*max((visit(p[tri],delta[tri],0) for tri in idx[active]),default=0)
    neutral,rest_distances=clearance(p)
    results={}
    for name,t in zip(names,asset.prim["targets"]):
        d=asset.accessor(t["POSITION"])[:,[0,2,1]].astype(float)*[1,-1,1]
        dist=np.linalg.norm(d,axis=1)
        moved=dist>0
        assert np.all(d[~zones["face"]]==0) and np.all(d[hairline]==0)
        fit,fit_distances=clearance(p+d)
        fit["max_euclidean_change_from_neutral_mm"]=round(1000*np.max(np.abs(fit_distances-rest_distances)),6)
        bound=guarded_surface_bound(d)
        assert bound<=3.,(name,bound)
        results[name]={**counts(moved),"nonface_vertices_moved":int((moved&~zones["face"]).sum()),
            "max_nonface_mm":float(1000*dist[~zones["face"]].max()),"max_hairline_total_mm":float(1000*dist[hairline].max()),
            "hairline_surface_displacement_upper_bound_mm":bound,
            "max_total_mm":round(dist.max()*1000,6),"clearance":fit}
    assert all(r["clearance"]["hair_vertices_inside"]==r["clearance"]["triangle_overlap_pairs"]==0 for r in results.values())
    assert neutral["hair_vertices_inside"]==neutral["triangle_overlap_pairs"]==0
    sizes={}
    body_pixels={}
    for name in NAMES:
        im=bpy.data.images.load(str(ROOT/"textures"/(name+".png")))
        sizes[name]=im.size[:]
        assert sizes[name]==(1024,1024)
        block=pixels(im)[:557,:,:3]
        if name=="neutral":neutral_rows=block.copy()
        body_pixels[name]=int(np.count_nonzero((block!=neutral_rows).any(axis=2)))
        assert body_pixels[name]==0,(name,body_pixels[name])
    image_view=g["bufferViews"][g["images"][0]["bufferView"]]
    start=image_view.get("byteOffset",0)
    assert asset.binary[start:start+image_view["byteLength"]]==(ROOT/"textures/neutral.png").read_bytes()
    result={"body_sha256":asset.sha,"input_sha256":base.sha,"hair_sha256":hair.sha,
        "glb_meshes":1,"primitives":1,"skins":1,"joints":len(asset.joints()),"triangles":len(idx),"vertices":len(p),
        "max_bind_matrix_element_difference":bind_err,"max_skin_weight_difference":werr,
        "source_max_neutral_position_error_mm":position_error*1000,"oriented_triangles_match_source":True,
        "input_regions":{name:counts(mask,pb) for name,mask in masks(pb).items()},
        "source_connected_components_welded_1um":components(base.positions(),base.triangles()),
        "regions":{name:counts(mask) for name,mask in zones.items()},"nonface":counts(~zones["face"]),
        "hair_guard_16mm":counts(hairline),"neutral_static_fit":neutral,"targets":results,"texture_sizes":sizes,"body_tile_pixels_different_from_neutral":body_pixels,
        "embedded_neutral_identical_to_png":True}
    (ROOT/"checks/geometry.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(results,indent=2))
main()
