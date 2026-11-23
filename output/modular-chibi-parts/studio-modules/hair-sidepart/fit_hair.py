"""Fit the Studio side-part to the GJH master. Run inside Blender 5.

Without an argument, build the editable scene, export the module, render the
six views, run the two supplied checkers and audit the exported geometry.
Optional stages after -- are build, sheet, vertex, tri, audit and dense.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import runpy
import sys
import tempfile

import bmesh
import bpy
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
PARTS = HERE.parents[1]
REPO = PARTS.parents[1]
MASTER = PARTS / "master/GJH_Chibi_Master_rigged.blend"
MOTION = REPO / "models/tripo-chibi-motion/motion.glb"
SOURCE = HERE / "source_studio_retopo.glb"
GLB = HERE / "hair_sidepart_v1.glb"
BLEND = GLB.with_suffix(".blend")
ROOT = Vector((.001, 0., .807))
HEAD, NECK = "mixamorig:Head", "mixamorig:Neck"

# Reuse the bob's mesh-field cutter, camera rig and glTF accessor reader.
spec = importlib.util.spec_from_file_location("bob_fit", PARTS / "hair-fit-astra/fit_hair.py")
bob = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bob)
bob.HERE, bob.GLB, bob.REPO, bob.MASTER = HERE, GLB, REPO, MASTER
smooth = bob.smooth


def active(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def rim_loops(bm):
    boundary = {edge for edge in bm.edges if edge.is_boundary}
    loops = []
    while boundary:
        e = boundary.pop()
        first, v = e.verts
        loop = [first, v]
        while True:
            adjacent = [e for e in v.link_edges if e in boundary]
            assert len(adjacent) == 1, (v.co[:], len(adjacent))
            e = adjacent[0]
            boundary.remove(e)
            v = e.other_vert(v)
            if v == first:
                break
            loop.append(v)
        loops.append(loop)
    return sorted(loops, key=len, reverse=True)


def extract(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1.e-6)
    # Two redundant fins in the Studio retopology share two edges with
    # the exterior. Removing just their free triangles restores manifoldness.
    fins = [f for f in bm.faces if any(e.is_boundary for e in f.edges)
            and sum(len(e.link_faces) > 2 for e in f.edges) == 2]
    bmesh.ops.delete(bm, geom=fins, context="FACES")
    assert all(e.is_manifold for e in bm.edges)
    bm.normal_update()
    def cavity_cut(p):
        a = abs(math.degrees(math.atan2(p.x, -p.y)))
        r = .204 + .125*smooth(12, 83, a) + .027*smooth(100, 163, a)
        return max(math.hypot(p.x,p.y)-r, 3*(p.z-.464))
    field = {v: cavity_cut(v.co) for v in bm.verts}
    seed = min(bm.verts, key=lambda v: (v.co - Vector((0, 0, .454))).length)
    inside = {seed}
    queue = [seed]
    while queue:
        v = queue.pop()
        for e in v.link_edges:
            w = e.other_vert(v)
            if w not in inside and field[w] < 0:
                inside.add(w)
                queue.append(w)
    # Isolate the central underside by connectivity. The same volume can
    # also contain the folded backs of the lowest exterior strands.
    values = {v: field[v] if v in inside else max(.001, abs(field[v])) for v in bm.verts}
    print("Fused shell extraction:", len(inside), "interior vertices;", len(fins), "fins")
    bob.trim_field(bm, values)
    parts = bob.connected_faces(bm)
    for tiny in parts[1:]:
        bmesh.ops.delete(bm, geom=tiny, context="FACES")
    loops = rim_loops(bm)
    print("Source hem loops:", [len(loop) for loop in loops], flush=True)
    # Small uncut bubbles on a concave source fold are enclosed by the
    # main cut. Fill any subsidiary openings; only the main hem is relined.
    for loop in loops[1:]:
        verts = set(loop)
        res = bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary and set(e.verts) <= verts])
        bmesh.ops.triangulate(bm, faces=res["faces"])
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def get_surface(tree, ray, distance):
    hit, n, _, _ = tree.ray_cast(ROOT + .62 * ray, -ray, .61)
    assert hit is not None, tuple(ray)
    point = hit + ray * (distance / max(.28, ray.dot(n)))
    # A nearest-surface check also covers the curvature around the ear.
    for _ in range(6):
        q, normal, _, _ = tree.find_nearest(point)
        delta = (point-q).dot(normal)
        if delta >= distance - .00003:
            break
        point += ray * ((distance-delta) / max(.3, ray.dot(normal)))
    return point


def pre_fit(p):
    x, y, h = p
    az = math.atan2(x, -y)
    deg = abs(math.degrees(az))
    # Bring the original pointed sideburn just forward of the ear. Drop the
    # high Studio rear hem to the occiput and keep the ear opening rounded.
    steer = smooth(40, 83, deg) * (1-smooth(110, 162, deg)) * (1-smooth(.16, .57, h))
    a = az - math.copysign(math.radians(19) * steer, az)
    shift = float(np.interp(deg, [0, 76, 91, 99, 109, 120, 130, 150, 180],
                            [0, 0, 0, .019, .023, -.012, -.060, -.104, -.119]))
    radius = math.hypot(x, y)
    z = .705 + .407 * h + shift * (1-smooth(.30, .70, h)) * smooth(.05, .27, radius)
    nominal = Vector((ROOT.x + .438 * radius * math.sin(a),
                      -.003 - .455 * radius * math.cos(a), z))
    return nominal


class SourceCavity:
    """Smooth angular field of the Studio underside in the pre-fitted mesh."""

    def __init__(self, original):
        xyz = [pre_fit(v.co) for v in original.vertices]
        tree = BVHTree.FromPolygons(xyz,[f.vertices[:] for f in original.polygons])
        # Missing rays below the natural source hem inherit the radius at
        # that azimuth's nearest covered elevation. The field is periodic.
        self.radii = np.zeros((180,81))
        for i in range(180):
            a=math.radians(2*i)
            valid=[]
            for j in range(81):
                el=math.radians(2*j-70)
                ray=Vector((math.sin(a)*math.cos(el),-math.cos(a)*math.cos(el),math.sin(el)))
                p=tree.ray_cast(ROOT,ray,.6)[0]
                if p is not None:
                    valid.append(j)
                    self.radii[i,j]=(p-ROOT).length
            self.radii[i]=np.interp(np.arange(81),valid,self.radii[i,valid])
        for _ in range(4):
            r=self.radii
            self.radii=(4*r+np.roll(r,1,0)+np.roll(r,-1,0)+
                        np.column_stack((r[:,0],r[:,:-1]))+np.column_stack((r[:,1:],r[:,-1])))/8

    def radius(self,ray):
        a=(math.degrees(math.atan2(ray.x,-ray.y))%360)/2
        el=np.clip((math.degrees(math.asin(min(1,max(-1,ray.z))))+70)/2,0,79.99999)
        i,j=int(a),int(el)
        t,u=a-i,el-j
        r=self.radii
        return ((1-t)*((1-u)*r[i,j]+u*r[i,j+1])+
                t*((1-u)*r[(i+1)%180,j]+u*r[(i+1)%180,j+1]))


def map_hair(p, skin, cavity):
    nominal=pre_fit(p)
    delta=nominal-ROOT
    ray=delta.normalized()
    wall=get_surface(skin,ray,.0080)
    # Map the source wall and its outer relief together. A positive
    # derivative throughout prevents folded strand roots from being
    # flattened onto a common sphere at the temples.
    depth=delta.length-cavity.radius(ray)
    if depth<0:
        depth=.008*math.expm1(depth/.008)
    front=smooth(-.27,.68,-ray.y)
    slope=.275+.18*front*(1-.70*smooth(.4,.95,ray.z))
    quiff=smooth(.44,.65,p.z)*(1-smooth(.09,.22,p.x))*smooth(-.30,-.03,-p.y)
    return wall+ray*(depth*(slope+.061*quiff))


def support_interior(obj,skin):
    # Long liner triangles can approach a curved skull between their
    # vertices. Check the first surface from inside at a one-degree pitch.
    directions=[]
    for a in np.radians(np.arange(-180,180,2)):
        for e in np.radians(np.arange(-56,91)):
            d=Vector((math.sin(a)*math.cos(e),-math.cos(a)*math.cos(e),math.sin(e)))
            p=skin.ray_cast(ROOT+.60*d,-d,.60)[0]
            if p is not None:
                directions.append((p,d))
    for _ in range(8):
        offsets=np.zeros(len(obj.data.vertices))
        tree=bob.tree_for(obj)
        for p,ray in directions:
            q,_,i,_=tree.ray_cast(p+.00002*ray,ray,.16)
            if q is None:
                continue
            _,normal,_,distance=skin.find_nearest(q)
            if distance<.00465:
                dz=(.00485-distance)/max(.35,normal.dot(ray))
                for v in obj.data.polygons[i].vertices:
                    offsets[v]=max(offsets[v],dz)
        if max(abs(offsets))<.00001:
            break
        for i in np.flatnonzero(offsets):
            v=obj.data.vertices[int(i)]
            v.co+=(v.co-ROOT).normalized()*offsets[i]
        obj.data.update()


def refine_wall(obj, skin):
    # Long pre-fit triangles at the rolled margin can bridge a curved
    # region of the skull. Add supports only on the loose first-hit faces.
    tree=bob.tree_for(obj)
    flagged=set()
    for a in np.radians(np.arange(-180,180,1)):
        for e in np.radians(np.arange(-42,48,1)):
            ray=Vector((math.sin(a)*math.cos(e),-math.cos(a)*math.cos(e),math.sin(e)))
            p=skin.ray_cast(ROOT+.60*ray,-ray,.60)[0]
            if p is None: continue
            q,_,i,_=tree.ray_cast(p+.00002*ray,ray,.16)
            if q is not None and skin.find_nearest(q)[3]>.01165:
                flagged.add(i)
    if not flagged:
        return False
    bm=bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    faces=[bm.faces[i] for i in sorted(flagged)]
    verts={v for f in faces for v in f.verts}
    edges={e for f in faces for e in f.edges if e.calc_length()>.031}
    budget=(3000-len(bm.faces))//2
    edges=sorted(edges,key=lambda e:(-e.calc_length(),e.index))[:budget]
    if edges:
        geometry=bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
        verts.update(v for v in geometry["geom_inner"] if isinstance(v,bmesh.types.BMVert))
        bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
    for v in verts:
        if not v.is_valid: continue
        ray=(v.co-ROOT).normalized()
        d=skin.find_nearest(v.co)[3]
        if d>.01065 or d<.0068:
            v.co=get_surface(skin,ray,.00865)
    print("Refined wall:",len(flagged),"faces;",len(edges),"edge supports;",len(bm.faces),"triangles")
    assert len(bm.faces)<=3000
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return True


def decimate(obj, budget):
    active(obj)
    obj.data.calc_loop_triangles()
    mod = obj.modifiers.new("Preserve quiff contour", "DECIMATE")
    mod.ratio = min(1., budget/len(obj.data.loop_triangles))
    mod.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=mod.name)


def liner(obj, skin):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    boundary, = rim_loops(bm)
    # Follow the existing edge winding so the liner normals face the head.
    e = bm.edges.get((boundary[0], boundary[1]))
    if e.link_loops[0].vert == boundary[0]:
        boundary.reverse()
    uv = bm.loops.layers.uv.active
    def face(points):
        f = bm.faces.new(points)
        # The underside uses a small chestnut swatch of the original atlas.
        for l in f.loops:
            p = l.vert.co
            l[uv].uv = (.5 + .02*p.x, .013 + .012*p.y)
        return f

    def polar(v):
        d = v.co - ROOT
        return math.atan2(d.x, -d.y), math.atan2(d.z, math.hypot(d.x,d.y))
    def on_head(a, el, gap=.0082):
        ray = Vector((math.sin(a)*math.cos(el), -math.cos(a)*math.cos(el), math.sin(el)))
        return get_surface(skin, ray, gap)

    # Connect the irregular source hem to evenly spaced rings. A periodic
    # height envelope follows both ear notches and the asymmetric hairline.
    angles = np.unwrap([polar(v)[0] for v in boundary] + [polar(boundary[0])[0]])
    winding = 1 if angles[-1] > angles[0] else -1
    start = angles[0]
    phases = winding*(angles-start)
    heights = np.array([polar(v)[1] for v in boundary])
    rows = []
    count = 56
    hem=[]
    for j in range(count):
        phase=2*math.pi*j/count
        gap=np.abs((phases[:-1]-phase+math.pi)%(2*math.pi)-math.pi)
        near=np.argsort(gap)[:3]
        w=1/(.012+gap[near])**2
        hem.append(float(np.average(heights[near],weights=w))+.022)
    # Turn the inner cut into a thin fitted brow only across the front.
    # Its outer and inner courses share the brow edge. Behind the ears
    # the original rolled hair margin already forms this return.
    top_edge = hem.copy()
    expanded=[]
    for j in range(count):
        a=start+winding*2*math.pi*j/count
        deg=math.degrees(math.atan2(math.sin(a),math.cos(a)))
        gain=1-smooth(57,70,abs(deg))
        brow=float(np.interp(deg,[-70,-61,-55,-45,-30,-18,-11,-5,2,12,27,40,48,55,61,70],
                             [-31,-22,-3,3,2,3,5,10,20,22,22,17,9,-2,-21,-31]))
        hem[j]=top_edge[j]+gain*(min(top_edge[j],math.radians(brow))-top_edge[j])
        expanded.append(hem[j]<top_edge[j]-.004)
    for progress in (0., .14, .30, .47, .64, .81, .94):
        row = []
        for j in range(count):
            phase = 2*math.pi*j/count
            a = start + winding * phase
            el = hem[j]
            el += progress*(math.pi/2-el)
            gap=.0082-.0013*(1-smooth(0,.45,progress))*expanded[j]
            row.append(bm.verts.new(on_head(a, el, gap)))
        rows.append(row)
    shoulder=[]
    rolled=[]
    for j,edge in enumerate(rows[0]):
        a=start+winding*2*math.pi*j/count
        if expanded[j]:
            shoulder.append(bm.verts.new(on_head(a,top_edge[j],.0077)))
            rolled.append(bm.verts.new(on_head(a,hem[j]+.032,.0095)))
        else:
            shoulder.append(edge)
            rolled.append(edge)
    for upper, lower in ((shoulder,rolled),(rolled,rows[0])):
        for j in range(count):
            k=(j+1)%count
            corners=list(dict.fromkeys((upper[j],upper[k],lower[k],lower[j])))
            if len(corners)>=3:
                face(corners)
    # The zipper consumes every original edge, including the little
    # azimuth reversals at curled tips; it never splits the visible surface.
    i=j=0
    while i<len(boundary) or j<count:
        b = boundary[i%len(boundary)]
        r = shoulder[j%count]
        if i<len(boundary) and (j==count or phases[i+1] <= 2*math.pi*(j+1)/count):
            face([b,boundary[(i+1)%len(boundary)],r])
            i+=1
        else:
            face([b,shoulder[(j+1)%count],r])
            j+=1
    for outer, inner in zip(rows,rows[1:]):
        for j in range(count):
            k=(j+1)%count
            face([outer[j],outer[k],inner[k],inner[j]])
    top=bm.verts.new(on_head(0, math.pi/2))
    for j in range(count):
        face([rows[-1][j],rows[-1][(j+1)%count],top])
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts)>3])
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    assert all(e.is_manifold for e in bm.edges)
    print("Relined:",len(boundary),"hem vertices;",len(bm.faces),"triangles",flush=True)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()



def normalized(vectors):
    return vectors / np.maximum(1.e-12, np.linalg.norm(vectors, axis=-1, keepdims=True))


def atlas_transfer(obj, original):
    """Resample source maps on the reduced surface before nonuniform fitting.

    A closest-point lookup in undeformed source space avoids crossing the
    narrow overlapping locks after fitting. Interpolate both tangent frames
    to carry the original normal map to the new padded UV charts.
    """
    mesh = obj.data
    while mesh.uv_layers:
        mesh.uv_layers.remove(mesh.uv_layers[0])
    mesh.uv_layers.new(name="Sidepart atlas")
    active(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(58),island_margin=.0055,
                             area_weight=.2,scale_to_bounds=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    for uv in mesh.uv_layers.active.data:
        uv.uv.y = .035 + .965*uv.uv.y
    for f in mesh.polygons:
        f.use_smooth = True

    size = 1024
    def surface(m):
        m.calc_loop_triangles()
        m.calc_tangents()
        loops = np.array([t.loops[:] for t in m.loop_triangles])
        return dict(
            xyz=np.array([v.co[:] for v in m.vertices], dtype="f")[
                np.array([t.vertices[:] for t in m.loop_triangles])],
            uv=np.array([u.uv[:] for u in m.uv_layers.active.data], dtype="f")[loops],
            n=np.array([n.vector[:] for n in m.corner_normals], dtype="f")[loops],
            t=np.array([l.tangent[:] for l in m.loops], dtype="f")[loops],
            sign=np.array([l.bitangent_sign for l in m.loops], dtype="f")[loops])

    low = surface(mesh)
    high = surface(original)
    tree = BVHTree.FromPolygons([v.co for v in original.vertices],
                                [t.vertices[:] for t in original.loop_triangles], all_triangles=True)
    def bary2(points, tri):
        a,b,c=tri
        u,v=b-a,c-a
        den=u[0]*v[1]-u[1]*v[0]
        if abs(den)<1.e-10:
            return None
        d=points-a
        t=(d[...,0]*v[1]-d[...,1]*v[0])/den
        s=(u[0]*d[...,1]-u[1]*d[...,0])/den
        return np.stack((1-t-s,t,s),axis=-1)

    dest_face=np.full((size,size),-1,np.int32)
    dest_weights=np.zeros((size,size,3),"f")
    for index,tri in enumerate(low["uv"]*size-.5):
        mn=np.maximum(0,np.ceil(tri.min(axis=0)).astype(int))
        mx=np.minimum(size-1,np.floor(tri.max(axis=0)).astype(int))
        if np.any(mx<mn):
            continue
        yy,xx=np.mgrid[mn[1]:mx[1]+1,mn[0]:mx[0]+1]
        w=bary2(np.stack((xx,yy),axis=-1),tri)
        if w is None:
            continue
        ok = w.min(axis=-1)>=-1.e-6
        dest_face[yy[ok],xx[ok]]=index
        dest_weights[yy[ok],xx[ok]]=w[ok]
    mask=dest_face>=0
    yy,xx=np.where(mask)
    fi=dest_face[mask]
    w=dest_weights[mask]
    def interp(verts, faces, weights):
        return np.einsum("ijk,ij->ik",verts[faces],weights)

    positions=interp(low["xyz"],fi,w)
    source_face=np.empty(len(fi),np.int32)
    nearest=np.empty_like(positions)
    target_normals=normalized(interp(low["n"],fi,w))
    for k,p in enumerate(positions):
        loc,n,idx,d=tree.find_nearest(p)
        facing=n.dot(target_normals[k])
        # The nearest wall at a tapered strand end may be its dark reverse.
        # Prefer a nearby source triangle on the same side of that fold.
        if facing<.58:
            score=d+.010*(1-facing)**2
            for q,nn,j,dd in tree.find_nearest_range(p,d+.012):
                candidate=dd+.010*(1-nn.dot(target_normals[k]))**2
                if candidate<score:
                    loc,idx,score=q,j,candidate
        source_face[k]=idx
        nearest[k]=loc
    tri=high["xyz"][source_face]
    a,b,c=np.moveaxis(tri,1,0)
    u,v,p=b-a,c-a,nearest-a
    def dot(x,y):
        return np.einsum('ij,ij->i',x,y)
    uu,vv,uv,up,vp=dot(u,u),dot(v,v),dot(u,v),dot(u,p),dot(v,p)
    den=np.maximum(uu*vv-uv*uv,1.e-18)
    t,s=(vv*up-uv*vp)/den,(uu*vp-uv*up)/den
    sw=np.stack((1-t-s,t,s),axis=1)
    suv=interp(high["uv"],source_face,sw)
    def frame(surf,face,weights):
        n=normalized(interp(surf["n"],face,weights))
        t=interp(surf["t"],face,weights)
        t=normalized(t-n*dot(n,t)[:,None])
        sign=np.sign(np.einsum("ij,ij->i",surf["sign"][face],weights))
        return t,np.cross(n,t)*sign[:,None],n
    src_frame=frame(high,source_face,sw)
    dst_frame=frame(low,fi,w)
    def gutter(arr):
        filled=mask.copy()
        for _ in range(10):
            next_mask=filled.copy()
            for axis,step in ((0,1),(1,1),(0,-1),(1,-1)):
                available=np.roll(filled,step,axis=axis)&~next_mask
                arr[available]=np.roll(arr,step,axis=axis)[available]
                next_mask|=available
            filled=next_mask

    mat=obj.active_material
    for node in [n for n in mat.node_tree.nodes if n.type=="TEX_IMAGE"]:
        im=node.image
        channel=im.name.rsplit("_",1)[-1].split(".")[0]
        iw,ih=im.size
        raw=np.empty(iw*ih*4,"f");im.pixels.foreach_get(raw)
        raw=raw.reshape(ih,iw,4)
        coords=suv*np.array((iw,ih))-.5
        ij=np.floor(coords).astype(np.int32)
        frac=(coords-ij).astype("f")
        pixel=np.zeros((len(fi),3),"f")
        for dx,dy in ((0,0),(1,0),(0,1),(1,1)):
            mix=(frac[:,0] if dx else 1-frac[:,0])*(frac[:,1] if dy else 1-frac[:,1])
            pixel+=mix[:,None]*raw[(ij[:,1]+dy)%ih,(ij[:,0]+dx)%iw,:3]
        del raw
        if channel=="normal":
            local=2*pixel-1
            world=normalized(sum(axis*local[:,i,None] for i,axis in enumerate(src_frame)))
            pixel=.5+.5*normalized(np.stack([dot(world,axis) for axis in dst_frame],axis=1))
            # The smooth occipital surface has no individual carved locks.
            # Fade its source-space normal correction, which the curved
            # fitted topology would otherwise turn into UV-chart bands.
            rear=np.clip((positions[:,1]-.04)/.22,0,1)
            low_back=np.clip((.67-positions[:,2])/.13,0,1)
            strength=(1-rear*low_back)[:,None]
            pixel=.5+.5*normalized((2*pixel-1)*strength+np.array([0.,0.,1.])*(1-strength))
            under=(.5,.5,1.)
        elif channel=="basecolor":
            # Sample the shadow-side strand color for the inset hair return.
            under=np.percentile(pixel,12,axis=0)
        else:
            under=np.median(pixel,axis=0)
        atlas=np.zeros((size,size,4),"f")
        atlas[:,:,:3]=under
        atlas[:,:,3]=1
        atlas[yy,xx,:3]=np.clip(pixel,0,1)
        gutter(atlas)
        atlas[:25,:,:3]=under
        suffix=".jpg" if channel=="basecolor" else ".png"
        name="Sidepart_"+channel+suffix
        output=bpy.data.images.new(name,size,size,alpha=False)
        output.colorspace_settings.name="sRGB" if channel=="basecolor" else "Non-Color"
        output.pixels.foreach_set(atlas.ravel())
        with tempfile.TemporaryDirectory(dir=HERE/"work") as tmp:
            output.filepath_raw=str(Path(tmp)/name)
            output.file_format="JPEG" if suffix==".jpg" else "PNG"
            output.save(quality=96)
            data=Path(output.filepath_raw).read_bytes()
            output.pack(data=data,data_len=len(data))
        output.filepath_raw="//"+name
        node.image=output
        bpy.data.images.remove(im)
    print("Transferred material at",len(fi),"atlas samples",flush=True)


def build():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    sc=bpy.context.scene
    arm, body = sc.objects["Armature"], sc.objects["Base_Body"]
    skin = bob.tree_for(body, head_only=True)
    before=set(sc.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    obj, = [o for o in set(sc.objects)-before if o.type=="MESH"]
    obj.data.transform(obj.matrix_world)
    obj.parent = None
    obj.matrix_world=Matrix.Identity(4)
    obj.name="Hair_Sidepart"
    obj.data.name="Sidepart quiff and fitted hem"
    active(obj)
    original=obj.data.copy()
    if obj.data.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    extract(obj)
    decimate(obj,2040)
    atlas_transfer(obj,original)
    cavity=SourceCavity(original)
    bpy.data.meshes.remove(original)
    for v in obj.data.vertices:
        v.co=map_hair(v.co,skin,cavity)
    obj.data.update()
    liner(obj,skin)
    if len(obj.data.polygons)>2998:
        decimate(obj,2998)
    bob.correct_clearance(obj,skin)
    bob.support_faces(obj,skin)
    support_interior(obj,skin)
    # A support edge can expose a previously unmeasured neighboring face.
    # Re-evaluate the fitted surface after editing its topology.
    for _ in range(4):
        if not refine_wall(obj,skin):
            break
        support_interior(obj,skin)
    for f in obj.data.polygons:
        f.use_smooth=True
    mat=obj.active_material
    mat.name="Sidepart Chestnut"
    mat.diffuse_color=(.26,.085,.045,1)
    normal=next(n for n in mat.node_tree.nodes if n.type=="NORMAL_MAP")
    normal.uv_map=obj.data.uv_layers.active.name
    normal.inputs["Strength"].default_value=.28
    h,n=(obj.vertex_groups.new(name=name) for name in (HEAD,NECK))
    for v in obj.data.vertices:
        x,y,z = v.co
        w = .033*smooth(.002,.09,y)*(1-smooth(.695,.795,z))
        w = w if w>=.0001 else 0.
        h.add([v.index],1-w,"REPLACE")
        if w:
            n.add([v.index],w,"REPLACE")
    mod=obj.modifiers.new("Master skeleton","ARMATURE")
    mod.object=arm
    active(obj)
    arm.hide_set(False)
    arm.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(GLB),export_format="GLB",use_selection=True,
                              export_animations=False,export_def_bones=False,export_tangents=True,
                              export_all_influences=False)
    obj.parent=arm
    arm.hide_set(True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=="VIEW_3D":
                sp=area.spaces.active
                sp.overlay.show_overlays=False
                sp.shading.color_type="TEXTURE"
                sp.region_3d.view_rotation=Vector((0,1,0)).to_track_quat("-Z","Y")
                sp.region_3d.view_distance=.77
                sp.region_3d.view_location=(0,0,.80)
                sp.region_3d.view_perspective="ORTHO"
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND),compress=True)
    print("EXPORTED", GLB.stat().st_size, hashlib.sha256(GLB.read_bytes()).hexdigest(), flush=True)


def check(kind):
    @bpy.app.handlers.persistent
    def use_cpu(scene,*_):
        if scene.camera and scene.camera.name=="c" and scene.render.engine=="BLENDER_WORKBENCH":
            bob.cpu_studio(scene)
    bpy.app.handlers.frame_change_pre.append(use_cpu)
    source=HERE/"work"/("motion_check_tri.py" if kind=="tri" else "motion_check.py")
    old=sys.argv
    try:
        with tempfile.TemporaryDirectory(dir=HERE/"work") as tmp:
            sys.argv=[str(source),"--",str(MASTER),str(MOTION),str(GLB),tmp]
            runpy.run_path(str(source),run_name="__main__")
            report=Path(tmp)/"motion_check.json"
            data=json.loads(report.read_text())
            report.replace(HERE/source.with_suffix(".json").name)
            if kind=="vertex":
                # The checker's last frame is airborne. Keep its pose and
                # projection, and shift only the published jump portrait
                # enough to show the crown with a 10 cm top margin.
                scene=bpy.context.scene
                assert scene.objects["Armature"].animation_data.action.name=="jump"
                dg=bpy.context.evaluated_depsgraph_get()
                hair=scene.objects["garment"].evaluated_get(dg)
                crown=max((hair.matrix_world@v.co).z for v in hair.data.vertices)
                camera=scene.camera
                camera.location.z=max(camera.location.z,crown+.10-camera.data.ortho_scale*.5)
                scene.render.filepath=str(Path(tmp)/"jump.png")
                bpy.ops.render.render(write_still=True)
                print("Jump portrait:",scene.frame_current,"camera Z",camera.location.z,flush=True)
                for name in ("walk","run","wave","jump"):
                    (Path(tmp)/(name+".png")).replace(HERE/(name+".png"))
            assert set(data)==set("rest walk run wave jump idle nod dance".split())
            assert all(count==0 and dist>=.0005 for count,dist in data.values()),data
    finally:
        sys.argv=old
        bpy.app.handlers.frame_change_pre.remove(use_cpu)



def full_frames():
    """Repeat the body collision measurements at every integer action frame."""
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    sc=bpy.context.scene
    arm,body=sc.objects["Armature"],sc.objects["Base_Body"]
    before=set(sc.objects)
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    new=set(sc.objects)-before
    hair=sc.objects["Hair_Sidepart"]
    hair.parent=None
    for o in new:
        if o.type=="ARMATURE":
            bpy.data.objects.remove(o,do_unlink=True)
    hair.modifiers.clear()
    hair.parent=arm
    hair.modifiers.new("master","ARMATURE").object=arm
    bpy.ops.import_scene.gltf(filepath=str(MOTION))
    for o in sc.objects:
        if o not in (body,arm,hair):
            o.hide_viewport=True
    arm.animation_data_create()
    for name in ("rest","walk","run","wave","jump","idle","nod","dance"):
        a=None if name=="rest" else bpy.data.actions[name]
        arm.animation_data.action=a
        frames=[1]
        if a:
            arm.animation_data.action_slot=a.slots[0]
            frames=range(int(a.frame_range[0]),int(a.frame_range[1])+1)
        lowest=10.
        max_inside=max_pairs=0
        where=None
        pair_locations=[]
        for fr in frames:
            sc.frame_set(fr)
            dg=bpy.context.evaluated_depsgraph_get()
            b,g=body.evaluated_get(dg),hair.evaluated_get(dg)
            bvh=bob.tree_for(b)
            ht=bob.tree_for(g)
            pairs=bvh.overlap(ht)
            if len(pairs)>max_pairs:
                max_pairs=len(pairs)
                pair_locations=[(fr,tuple(round(x,4) for x in hair.data.polygons[hf].center)) for _,hf in pairs[:8]]
            inside=0
            for v in g.data.vertices:
                p=g.matrix_world@v.co
                q,n,_,_=bvh.find_nearest(p)
                dist=(p-q).dot(n)
                inside+=dist<0
                if dist<lowest:
                    lowest=dist
                    where=fr,tuple(round(x,5) for x in hair.data.vertices[v.index].co)
            max_inside=max(inside,max_inside)
        print("ALL FRAMES",name,len(frames),max_inside,max_pairs,lowest,where,pair_locations,flush=True)
        assert max_inside==max_pairs==0 and lowest>=.0005


def audit():
    doc, buf = bob.read_glb(GLB)
    ref, refbuf = bob.read_glb(MASTER.with_name("base_body.glb"))
    skin, = doc["skins"]
    def joints(g):
        return [(g["nodes"][i]["name"],[g["nodes"][c]["name"] for c in g["nodes"][i].get("children",[])])
                for i in g["skins"][0]["joints"]]
    assert joints(doc)==joints(ref) and len(skin["joints"])==65
    bind = bob.accessor(doc,buf,skin["inverseBindMatrices"])
    refbind = bob.accessor(ref,refbuf,ref["skins"][0]["inverseBindMatrices"])
    assert np.allclose(bind,refbind,atol=1.e-6,rtol=0)
    mesh, = doc["meshes"]
    prim, = mesh["primitives"]
    node, = [n for n in doc["nodes"] if "mesh" in n]
    assert node["name"]=="Hair_Sidepart" and node["skin"]==0
    assert not any(k in node for k in ("matrix","translation","rotation","scale"))
    assert "animations" not in doc and "cameras" not in doc
    attrs=prim["attributes"]
    weights=bob.accessor(doc,buf,attrs["WEIGHTS_0"])
    ids=bob.accessor(doc,buf,attrs["JOINTS_0"])
    names=[name for name,_ in joints(doc)]
    used=weights>0
    assert {names[i] for i in np.unique(ids[used])} == {HEAD,NECK}
    assert "JOINTS_1" not in attrs and np.allclose(weights.sum(axis=1),1.,atol=1.e-6)
    triangles=doc["accessors"][prim["indices"]]["count"]//3
    assert triangles<=3000 and int(used.sum(1).max())<=4
    print("GLB skin:",triangles,"triangles;",len(names),"joints;",
          used.sum(1).max(),"influences; peak Neck",np.where(ids==names.index(NECK),weights,0).sum(1).max())
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    obj=bpy.data.objects["Hair_Sidepart"]
    body=bpy.data.objects["Base_Body"]
    atlas=[n.image for n in obj.active_material.node_tree.nodes if n.type=="TEX_IMAGE"]
    assert len(atlas)==3 and all(im.packed_file and tuple(im.size)==(1024,1024) for im in atlas)
    bm=bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1.e-7)
    assert len(bob.connected_faces(bm))==1
    print("Round-trip manifold:",sum(not e.is_manifold for e in bm.edges),
          "non-manifold edges; minimum face area",min(f.calc_area() for f in bm.faces))
    assert all(e.is_manifold for e in bm.edges)
    bm.free()
    scalp, hair=bob.tree_for(body,True),bob.tree_for(obj)
    angles=np.radians(np.arange(-180,180,.5))
    all_hits=[]
    upper=[]
    for a in angles:
        covered=False
        for degree in np.arange(-60.,90.5,.5):
            el=math.radians(degree)
            ray=Vector((math.sin(a)*math.cos(el),-math.cos(a)*math.cos(el),math.sin(el)))
            p=scalp.ray_cast(ROOT+.60*ray,-ray,.60)[0]
            if p is None:
                assert degree<0
                continue
            q=hair.ray_cast(p+.00002*ray,ray,.16)[0]
            if q is None:
                assert not covered and degree<25,(a,degree,"gap")
                continue
            covered=True
            d=scalp.find_nearest(q)[3]
            all_hits.append((d,math.degrees(a),degree))
            if degree>=25:
                upper.append(d)
    print("First hair surface (all covered directions):",len(all_hits),min(all_hits),max(all_hits),flush=True)
    print("Continuous upper cap:",len(upper),min(upper),max(upper),flush=True)
    # Match the bob reviewer's independent eye visibility test. Build the
    # two eye components, then count pixels visible on the bare master that
    # would be occluded by the exported hair.
    eyes_bm=bmesh.new()
    eyes_bm.from_mesh(body.data)
    bmesh.ops.remove_doubles(eyes_bm,verts=list(eyes_bm.verts),dist=1.e-5)
    eyes_bm.verts.index_update()
    faces=[]
    for part in bob.connected_faces(eyes_bm):
        zs=[v.co.z for f in part for v in f.verts]
        if .67<min(zs) and max(zs)<.80:
            faces.extend(part)
    assert len(faces)==268
    eyes=BVHTree.FromPolygons([v.co.copy() for v in eyes_bm.verts],
                              [[v.index for v in f.verts] for f in faces])
    eyes_bm.free()
    for view in ((0,-1,0),(.6,-1,.08),(-.6,-1,.08)):
        ray=Vector(view).normalized()
        rotation=(-ray).to_track_quat("-Z","Y")
        right=rotation@Vector((1,0,0))
        up=rotation@Vector((0,1,0))
        exposed=hidden=0
        for y in range(230,405):
            row=ROOT-Vector((.001,0,0))+ray+up*((260-y-.5)*.55/520)
            for x in range(30,491):
                origin=row+right*((x+.5-260)*.55/520)
                iris=eyes.ray_cast(origin,-ray,2)[0]
                if iris is None: continue
                skin_hit=scalp.ray_cast(origin,-ray,2)[0]
                if skin_hit is not None and (skin_hit-iris).dot(ray)>.00003: continue
                exposed+=1
                lock=hair.ray_cast(origin,-ray,2)[0]
                hidden+=int(lock is not None and (lock-iris).dot(ray)>.00001)
        print("Eye pixels",view,exposed,"occluded",hidden,flush=True)
        assert exposed>0 and hidden==0
    validation=bob.validator()
    print(validation,flush=True)
    assert "0 errors and 0 warnings" in validation
    assert .004<=min(all_hits)[0] and max(all_hits)[0]<=.012


if __name__=="__main__":
    stages=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else ["build","sheet","vertex","tri","audit"]
    for stage in stages:
        if stage=="build": build()
        elif stage=="sheet": bob.sheet()
        elif stage in ("vertex","tri"): check(stage)
        elif stage=="audit": audit()
        elif stage=="dense": full_frames()
        else: raise ValueError(stage)
