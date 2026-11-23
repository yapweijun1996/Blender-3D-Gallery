"""Fit the supplied Tripo Studio spiky mesh to the GJH chibi master using bpy.

Run the guarded Blender with -b -noaudio --python-exit-code 1 --python fit_hair.py.
Optional stages after -- are build, sheet, vertex, tri and audit. The bob
fitting and QA helpers live at their original read-only repository paths.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import runpy
import sys
import subprocess
import tempfile

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
PARTS = HERE.parents[1]
SOURCE = HERE / "source_studio_retopo.glb"
BOB = PARTS / "hair-fit-astra"
NAME = "Hair_Spiky"
GLB = HERE / "hair_spiky_v1.glb"
BLEND = GLB.with_suffix(".blend")
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("bob_helpers", BOB / "fit_hair.py")
bob = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bob)
ROOT, MASTER, MOTION = bob.ROOT, bob.MASTER, bob.MOTION
bob.HERE, bob.GLB = HERE, GLB
smooth = bob.smooth
VIEW_SPAN = .60
VIEWS = ((0,-1,0), (.6,-1,.08), (-.6,-1,.08), (1,0,.03), (0,1,.06), (-1,0,.03))


def skin_radius(tree, ray, gap):
    hit, normal, _, _ = tree.ray_cast(ROOT + .55 * ray, -ray, .548)
    if hit is None:
        # The lowest rays pass through the open base of the isolated head.
        return .197 + gap
    return (hit-ROOT).dot(ray) + gap / max(.38, ray.dot(normal))


def resize_maps(obj):
    images = {}
    for node in obj.active_material.node_tree.nodes:
        if node.type != "TEX_IMAGE":
            continue
        im = node.image
        kind = "basecolor" if "basecolor" in im.name else "normal" if "normal" in im.name else "rm"
        im.scale(1024, 1024)
        with tempfile.TemporaryDirectory(dir=HERE/"work") as tmp:
            # PNG also preserves the channel values of the two data maps.
            path = Path(tmp) / ("Spiky_" + kind + (".jpg" if kind == "basecolor" else ".png"))
            im.filepath_raw = str(path)
            im.file_format = "JPEG" if kind == "basecolor" else "PNG"
            im.save(quality=95)
            data = path.read_bytes()
            im.pack(data=data, data_len=len(data))
        im.filepath_raw = "//" + path.name
        im.name = "Spiky_" + kind
        images[kind] = im
    return images["basecolor"]


def map_exterior(obj, tree, image):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1.e-6)
    # The source has one single-sided fin attached to an otherwise closed mesh.
    fins = [f for f in bm.faces if sum(e.is_boundary for e in f.edges) == 2]
    assert len(fins) == 1
    bmesh.ops.delete(bm, geom=fins, context="FACES")
    assert all(e.is_manifold for e in bm.edges)
    uv = bm.loops.layers.uv.active
    atlas = np.empty(1024*1024*4, np.float32)
    image.pixels.foreach_get(atlas)
    atlas = atlas.reshape(1024,1024,4)
    keep = {}
    for v in bm.verts:
        x, y, z = v.co
        colors = []
        for loop in v.link_loops:
            u, t = loop[uv].uv
            colors.append(atlas[int(t % 1 * 1024), int(u % 1 * 1024), :3])
        r, g, b = np.median(colors, axis=0)
        color_cut = max(.61-r, 4*(.054-g+b), z-.54)
        depth = math.hypot(x-.012, y+.012)
        neck_cut = depth - .242*(1-smooth(.145,.265,z))
        # Open the recess around the source ears. Both sides are part of
        # the same original surface and retain their own asymmetric locks.
        ear_cut = math.hypot((y+.030)/.077, (z-.213)/.095)-1
        if abs(x) < .20:
            ear_cut = 1
        keep[v] = min(color_cut, neck_cut, ear_cut*.12)
    bob.trim_field(bm,keep)
    parts = bob.connected_faces(bm)
    for faces in parts[1:]:
        bmesh.ops.delete(bm,geom=faces,context="FACES")
    # A scalar contour splits the textured polygons with interpolated UVs.
    # Tracking the cut contours identifies the main rim and small local cutouts.
    borders = [e for e in bm.edges if e.is_boundary]
    paths = []
    pending = set(borders)
    while pending:
        edge = min(pending,key=lambda e:e.index)
        p0 = edge.verts[0]
        v = p0
        verts = []
        while True:
            verts.append(v)
            pending.remove(edge)
            v = edge.other_vert(v)
            if v == p0:
                break
            edge, = [e for e in v.link_edges if e in pending]
        paths.append(verts)
    paths.sort(key=len,reverse=True)
    print("Hair contours", [len(row) for row in paths], "source kept",len(bm.faces))
    rim = paths[0]
    for row in paths[1:]:
        bmesh.ops.holes_fill(bm,edges=[bm.edges.get((row[i-1],v)) for i,v in enumerate(row)])
    # One pinned front and ear deformation field, shared by all layers.
    samples = []
    for v in bm.verts:
        x, y, z = v.co
        front = smooth(.015,.285,-y)
        low = 1-smooth(.35,.72,z)
        side = smooth(.13,.26,abs(x))
        ear = math.exp(-((y+.025)/.135)**2) * side
        forehead = .023 + .020*side
        behind_ear = .061*smooth(-.15,-.01,y)*(1-smooth(.11,.34,y))*side*(1-smooth(.20,.43,z))
        p = Vector((.001 + .500*(x-.012), .007 + .495*y + behind_ear,
                    .645 + .457*z + forehead*front*low + .009*ear*low
                    - .015*smooth(-.03,.20,y)*low))
        # Bring the textured Studio side curtain down to the natural ear arch.
        side_angle = abs(math.degrees(math.atan2(p.x-ROOT.x,-p.y)))
        p.z -= .028*math.exp(-((side_angle-88)/24)**4)*low
        delta = p-ROOT
        ray = delta.normalized()
        surface = skin_radius(tree,ray,0.)
        gap = delta.length-surface
        samples.append((v,ray,surface,gap,front,low,z))
    rays = np.array([tuple(row[1]) for row in samples])
    deficits = np.clip([.012-row[3] for row in samples],0,.075)
    for v,ray,surface,gap,front,low,z in samples:
        # Inflate a *neighborhood* of the old hair by its deepest root.
        # Nested forelocks then keep distinct dorsal and ventral surfaces.
        spread = np.exp((rays @ np.array(ray)-1)/.16**2)
        lift = float(np.max(deficits*spread))
        before = .0125 + .065*gap + .006*np.logaddexp(0,(gap-.0125)/.006)
        supported = gap + lift
        relief = .0105 + .60*(supported-.0105) + .40*.004*np.logaddexp(0,(supported-.0105)/.004)
        influence = (.23 + .77*front)*low
        relief = before*(1-influence) + relief*influence
        tuck = (1-front)*low*(1-smooth(.24,.50,z))
        relief *= 1-.23*tuck
        v.co = ROOT + ray*(surface+relief)
        # Ease the high opening under the part down over its fitted return.
        az = math.degrees(math.atan2(ray.x,-ray.y))
        el = math.degrees(math.asin(ray.z))
        v.co.z -= .008*math.exp(-((az+2)/24)**2-((el-6)/14)**2)
        v.co.z -= .016*math.exp(-((az-26)/20)**2-((el-27)/18)**2)
    add_lining(bm, rim, tree)
    bm.normal_update()
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        e.smooth = True
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    for f in obj.data.polygons:
        f.use_smooth = True
    bpy.context.view_layer.objects.active = obj
    if obj.data.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()


def add_lining(bm, rim, tree):
    # Map the ordered boundary to the scalp. Near overlapping locks the
    # angular outline briefly doubles back. Consume those small reversals
    # along the hidden return course, then join to regular scalp latitudes.
    def polar(v):
        d = (v.co-ROOT).normalized()
        return math.atan2(d.x,-d.y), math.asin(np.clip(d.z,-1,1))
    def unwrap(row):
        return np.unwrap([polar(v)[0] for v in row])
    angles = unwrap(rim)
    if angles[-1] < angles[0]:
        rim.reverse()
        angles = unwrap(rim)
    # Start the wrap in the middle of the quiet posterior arc.
    start = min(range(len(rim)),key=lambda i:abs(abs(polar(rim[i])[0])-math.pi))
    rim[:] = rim[start:]+rim[:start]
    angles = unwrap(rim)
    elevations = np.array([polar(v)[1] for v in rim])
    # Periodic isotonic regression keeps the correspondence ordered.
    angles = np.concatenate((angles-2*math.pi,angles,angles+2*math.pi))
    blocks = []
    for a in angles:
        blocks.append((a,1))
        while len(blocks)>1 and blocks[-2][0] > blocks[-1][0]:
            q,m = blocks.pop()
            p,n = blocks.pop()
            blocks.append(((p*n+q*m)/(n+m),n+m))
    ordered = np.concatenate([np.full(n,x) for x,n in blocks])[len(rim):2*len(rim)]
    arc = np.array([(rim[i].co-rim[i-1].co).length for i in range(len(rim))])
    walk = np.cumsum(arc)-arc[0]
    ordered = .97*ordered + .03*(ordered[0]+2*math.pi*walk/sum(arc))
    def scalp(a,e,gap=.0083):
        ray = Vector((math.sin(a)*math.cos(e),-math.cos(a)*math.cos(e),math.sin(e)))
        return ROOT+skin_radius(tree,ray,gap)*ray
    def face(verts):
        f = bm.faces.new(verts)
        f.material_index = 1
        f.smooth = True
    count, bands = 104, 16
    uniform = ordered[0]+np.arange(count)*2*math.pi/count
    seam = np.interp(uniform,ordered,elevations,period=2*math.pi)
    seam = (.5*seam + .25*np.roll(seam,1)+.25*np.roll(seam,-1))
    longitude = np.abs(np.rad2deg(np.angle(np.exp(1j*uniform))))
    limit = np.interp(longitude,[0,38,60,73,80,103,115,130,180],
                      [23,23,1,-10,-12,-12,-27,-36,-36])
    # A lightly scalloped hem follows the tips, arches over the ear, and
    # descends to the nape. The visible rim has its own hair-thickness roll.
    hem = np.minimum(seam+.012,np.deg2rad(limit-1.3+1.2*np.cos(13*uniform+.6)))
    rolled = [bm.verts.new(scalp(a,e,.0136+.0010*math.cos(13*a))) for a,e in zip(uniform,hem)]
    i = j = 0
    while i<len(rim) or j<count:
        a = ordered[(i+1)%len(rim)] if i+1<len(rim) else ordered[0]+2*math.pi
        b = uniform[(j+1)%count] if j+1<count else uniform[0]+2*math.pi
        if i<len(rim) and (j==count or a<=b):
            face([rim[i%len(rim)],rim[(i+1)%len(rim)],rolled[j%count]])
            i += 1
        else:
            face([rim[i%len(rim)],rolled[(j+1)%count],rolled[j%count]])
            j += 1
    row = [bm.verts.new(scalp(a,e+.011,.0083)) for a,e in zip(uniform,hem)]
    for i in range(count):
        face([rolled[i-1],rolled[i],row[i],row[i-1]])
    for band in range(1,bands):
        t = band/bands
        el = (hem+.011)*(1-t)+math.pi/2*t
        nxt = [bm.verts.new(scalp(a,e)) for a,e in zip(uniform,el)]
        for i in range(count):
            face([row[i-1],row[i],nxt[i],nxt[i-1]])
        row = nxt
    pole = bm.verts.new(scalp(0,math.pi/2))
    for i in range(len(row)):
        face([row[i-1],row[i],pole])
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))


def self_intersections(mesh):
    indices = [p.vertices[:] for p in mesh.polygons]
    tree = BVHTree.FromPolygons([v.co[:] for v in mesh.vertices],indices,all_triangles=True)
    vertices = [set(row) for row in indices]
    return sum(i<j and vertices[i].isdisjoint(vertices[j]) for i,j in tree.overlap(tree))


def remove_buried_faces(obj):
    """Keep only the boundary of the union of the fitted strands and return."""
    mesh = obj.data
    points = np.array([v.co[:] for v in mesh.vertices])
    triangles = points[np.array([f.vertices[:] for f in mesh.polygons])]
    # Blender's exact self-intersection operation cuts accurate shared edges.
    # At a crossing it also returns interior cells. A face is on the solid
    # boundary exactly when its two sides disagree about positive winding.
    cut = obj.modifiers.new("Split intersecting folds", "BOOLEAN")
    cut.operation,cut.solver,cut.operand_type = "UNION","EXACT","COLLECTION"
    cut.use_self = True
    bpy.ops.object.modifier_apply(modifier=cut.name)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
    bm.normal_update()
    def occupied(point):
        vectors = triangles-point
        a,b,c = vectors[:,0],vectors[:,1],vectors[:,2]
        la,lb,lc = np.linalg.norm(vectors,axis=2).T
        def dot(x,y):
            return np.einsum("ij,ij->i",x,y)
        numerator = dot(a,np.cross(b,c))
        denominator = la*lb*lc + dot(a,b)*lc + dot(b,c)*la + dot(c,a)*lb
        return np.arctan2(numerator,denominator).sum() > math.pi
    hidden = []
    for f in bm.faces:
        # Float64 centroids avoid landing on the wrong side of tiny cells.
        center = np.mean([v.co[:] for v in f.verts],axis=0)
        delta = .0000007*np.array(f.normal)
        outer,inner = occupied(center+delta),occupied(center-delta)
        if outer==inner:
            hidden.append(f)
        elif outer:
            f.normal_flip()
    bmesh.ops.delete(bm,geom=hidden,context="FACES")
    for part in bob.connected_faces(bm)[1:]:
        bmesh.ops.delete(bm,geom=part,context="FACES")
    # Single-precision output can leave a microscopic open cell when two
    # cut surfaces are tangent. Close only loops of sub-texel extent.
    boundary = [e for e in bm.edges if e.is_boundary]
    if boundary:
        print("Winding boundary edges",len(boundary),
              "total length",sum(e.calc_length() for e in boundary),flush=True)
        assert sum(e.calc_length() for e in boundary)<.003
        bmesh.ops.holes_fill(bm,edges=boundary)
        bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
    assert all(e.is_manifold for e in bm.edges)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    print("Removed buried triangle fragments",len(hidden),flush=True)
    if len(obj.data.polygons)>3000:
        dec = obj.modifiers.new("Simplify split boundary", "DECIMATE")
        dec.use_collapse_triangulate = True
        dec.ratio = 2972/len(obj.data.polygons)
        bpy.ops.object.modifier_apply(modifier=dec.name)
    assert self_intersections(obj.data)==0, "Residual crossing in the fitted solid"


def settle_forehead(mesh,tree):
    # Shift the edge of the natural forehead opening under the swept locks.
    # The inner and outer surfaces travel together, preserving the depth
    # of the return as it moves onto the differently curved forehead.
    outside = {i for f in mesh.polygons if f.material_index==0 for i in f.vertices}
    for v in mesh.vertices:
        dr = v.co-ROOT
        ray = dr.normalized()
        a,e = math.atan2(ray.x,-ray.y),math.asin(max(-1,min(1,ray.z)))
        amount = math.radians(15.5)*math.exp(-((math.degrees(a)-26)/18)**2-((math.degrees(e)-30)/24)**2)
        if amount<1.e-6:
            continue
        new_e = e-amount
        nr = Vector((math.sin(a)*math.cos(new_e),-math.cos(a)*math.cos(new_e),math.sin(new_e)))
        radius = dr.length + skin_radius(tree,nr,0)-skin_radius(tree,ray,0)
        if v.index in outside:
            weight = math.exp(-((math.degrees(a)-32)/16)**4-((math.degrees(new_e)-35)/22)**4)
            radius += .011*weight
        v.co = ROOT+radius*nr
    mesh.update()


def support_part(obj,tree):
    # Close the deep root groove beneath the swept part. The dorsal surface
    # samples original strand color and normals wherever it is exposed.
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    rows = []
    faces = []
    for gap in (.0074,.0185):
        layer = []
        for elevation in range(23,50,3):
            row = []
            for azimuth in range(25,42,2):
                a,e = math.radians(azimuth),math.radians(elevation)
                ray = Vector((math.sin(a)*math.cos(e),-math.cos(a)*math.cos(e),math.sin(e)))
                row.append(bm.verts.new(ROOT+ray*skin_radius(tree,ray,gap)))
            layer.append(row)
        rows.append(layer)
    def quad(corners,material):
        f = bm.faces.new(corners)
        f.material_index = material
        f.smooth = True
        faces.append(f)
    for k,layer in enumerate(rows):
        for j in range(1,len(layer)):
            for i in range(1,len(layer[0])):
                quad((layer[j-1][i-1],layer[j-1][i],layer[j][i],layer[j][i-1]),1-k)
    def perimeter(layer):
        return layer[0]+[r[-1] for r in layer[1:]]+layer[-1][-2::-1]+[r[0] for r in layer[-2:0:-1]]
    bottom,top = [perimeter(layer) for layer in rows]
    for i in range(len(top)):
        quad((bottom[i-1],bottom[i],top[i],top[i-1]),0)
    bmesh.ops.recalc_face_normals(bm,faces=faces)
    bmesh.ops.triangulate(bm,faces=faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def geometry(obj, tree, atlas):
    lining = bpy.data.materials.new("Chestnut underside")
    lining.diffuse_color = (.073,.027,.020,1)
    lining.use_nodes = True
    shader = lining.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = lining.diffuse_color
    shader.inputs["Roughness"].default_value = .64
    obj.data.materials.append(lining)
    map_exterior(obj, tree, atlas)
    bpy.context.view_layer.objects.active = obj
    high = obj.data.copy()
    dec = obj.modifiers.new("Spiky silhouette budget", "DECIMATE")
    dec.use_collapse_triangulate = True
    dec.ratio = min(1,2998/len(obj.data.polygons))
    bpy.ops.object.modifier_apply(modifier=dec.name)
    bob.correct_clearance(obj, tree)
    bob.support_faces(obj, tree)
    for v in obj.data.vertices:
        # The weighted low occiput compresses during the first run contact.
        extra = .0015*smooth(.040,.110,v.co.y)*(1-smooth(.715,.756,v.co.z))
        v.co += (v.co-ROOT).normalized()*extra
    obj.data.update()
    settle_forehead(obj.data,tree)
    settle_forehead(high,tree)
    support_part(obj,tree)
    remove_buried_faces(obj)
    b = bmesh.new()
    b.from_mesh(obj.data)
    print("Finish", len(b.faces),"boundary",sum(e.is_boundary for e in b.edges),
          "nonmanifold",sum(not e.is_manifold for e in b.edges),"material faces",
          {m.name:sum(f.material_index == i for f in b.faces) for i,m in enumerate(obj.data.materials)})
    b.free()
    transfer_atlas(obj,high)
    bpy.data.meshes.remove(high)


def normalized(v):
    return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1.e-12)


def transfer_atlas(obj, high):
    """Resample the Studio material on the final triangles without UV drift.

    Both meshes are in the same fitted coordinates. For every covered texel,
    find the nearest point on the un-decimated exterior and interpolate its
    original UV. Express the detailed high normal in the new tangent frame.
    """
    mesh = obj.data
    mat = mesh.materials[0]
    nodes = {n.image.name.split("_")[-1]:n for n in mat.node_tree.nodes if n.type=="TEX_IMAGE"}
    dim = 1024
    source = {}
    target = {}
    for kind, node in nodes.items():
        pixels = np.empty(dim*dim*4,np.float32)
        node.image.pixels.foreach_get(pixels)
        source[kind] = pixels.reshape(dim,dim,4)
        target[kind] = np.zeros((dim,dim,4),np.float32)
    # Atlas the exterior only. The return has a constant chestnut material.
    for f in mesh.polygons:
        f.select = f.material_index==0
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for f in mesh.polygons:
        f.select = f.material_index==0
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(62),island_margin=.005,
                             margin_method="FRACTION",area_weight=.2)
    bpy.ops.object.mode_set(mode="OBJECT")
    def arrays(m):
        m.calc_tangents(uvmap=m.uv_layers.active.name)
        faces = [f for f in m.polygons if f.material_index==0]
        idx = np.array([f.loop_indices[:] for f in faces])
        verts = np.array([v.co[:] for v in m.vertices])
        tri = np.array([f.vertices[:] for f in faces])
        uv = np.array([x.uv[:] for x in m.uv_layers.active.data])[idx]
        normals = np.array([v.normal[:] for v in m.vertices])[tri]
        tangents = np.array([l.tangent[:] for l in m.loops])[idx]
        sign = np.array([l.bitangent_sign for l in m.loops])[idx]
        return verts,tri,uv,normals,tangents,sign
    coords,indices,hi_uv,hi_n,hi_t,hi_s = arrays(high)
    high_tree = BVHTree.FromPolygons(coords.tolist(),indices.tolist(),all_triangles=True)
    hi_pos = coords[indices]
    low_pts,low_tri,low_uv,low_n,low_t,low_s = arrays(mesh)
    owner = np.full((dim,dim),-1,np.int32)
    weights = np.zeros((dim,dim,3),np.float32)
    for idx, uv in enumerate(low_uv):
        corners = uv*dim-.5
        lo = np.maximum(np.ceil(corners.min(0)).astype(int),0)
        hi = np.minimum(np.floor(corners.max(0)).astype(int),dim-1)
        if np.any(hi<lo):
            continue
        yy,xx = np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        dx,dy = xx-corners[0,0], yy-corners[0,1]
        a,b = corners[1:]-corners[0]
        det = a[0]*b[1]-a[1]*b[0]
        if abs(det)<1.e-10:
            continue
        v = (dx*b[1]-dy*b[0])/det
        w = (a[0]*dy-a[1]*dx)/det
        u = 1-v-w
        mask = (u>=0)&(v>=0)&(w>=0)
        owner[yy[mask],xx[mask]] = idx
        weights[yy[mask],xx[mask]] = np.stack((u[mask],v[mask],w[mask]),axis=-1)
    def interp(attr, tri, bary):
        return np.einsum("ij,ijk->ik",bary,attr[tri])
    def frame(normals,tangents,signs,tri,bary):
        n = normalized(interp(normals,tri,bary))
        t = interp(tangents,tri,bary)
        t = normalized(t-(n*t).sum(1)[:,None]*n)
        b = np.cross(n,t)*np.sign((signs[tri]*bary).sum(1))[:,None]
        return t,b,n
    ys,xs = np.nonzero(owner>=0)
    skin_pixels = np.zeros((dim,dim),bool)
    for start in range(0,len(ys),32768):
        y,x = ys[start:start+32768],xs[start:start+32768]
        lt = owner[y,x]
        lb = weights[y,x]
        xyz = interp(low_pts[low_tri],lt,lb)
        hit = [high_tree.find_nearest(p) for p in xyz]
        # In tight overlapping layers, the closest point can belong to the
        # back of the adjacent lock. Compare normals before sampling its UV.
        guides = normalized(interp(low_n,lt,lb))
        geometric = np.array([r[1][:] for r in hit])
        for k in np.flatnonzero(np.sum(geometric*guides,axis=1)<.55):
            radius = max(.006,hit[k][3]+.005)
            choices = high_tree.find_nearest_range(xyz[k],radius)
            g = Vector(guides[k])
            if choices:
                hit[k] = min(choices,key=lambda h:h[3]+.006*(1-h[1].dot(g)))
        ht = np.array([r[2] for r in hit])
        hp = np.array([r[0][:] for r in hit])
        p0,p1,p2 = np.swapaxes(hi_pos[ht],0,1)
        e1,e2,rel = p1-p0,p2-p0,hp-p0
        def dot(a,b):
            return np.einsum("ij,ij->i",a,b)
        aa,bb,ab = dot(e1,e1),dot(e2,e2),dot(e1,e2)
        det = np.maximum(aa*bb-ab*ab,1.e-18)
        v = (bb*dot(rel,e1)-ab*dot(rel,e2))/det
        w = (aa*dot(rel,e2)-ab*dot(rel,e1))/det
        hb = np.clip(np.stack((1-v-w,v,w),axis=1),0,1)
        hb /= np.maximum(hb.sum(1)[:,None],1.e-12)
        uv = (interp(hi_uv,ht,hb)%1)*dim-.5
        ixy = np.floor(uv).astype(int)
        frac = uv-ixy
        for kind,pixels in source.items():
            col = np.zeros((len(x),3))
            for j in (0,1):
                for i in (0,1):
                    weight = (frac[:,0] if i else 1-frac[:,0])*(frac[:,1] if j else 1-frac[:,1])
                    col += weight[:,None]*pixels[(ixy[:,1]+j)%dim,(ixy[:,0]+i)%dim,:3]
            if kind=="normal":
                st,sb,sn = frame(hi_n,hi_t,hi_s,ht,hb)
                dt,db,dn = frame(low_n,low_t,low_s,lt,lb)
                local = normalized(2*col-1)
                world = normalized(st*local[:,0:1]+sb*local[:,1:2]+sn*local[:,2:3])
                col = np.clip(.5+.5*np.stack((dot(world,dt),dot(world,db),dot(world,dn)),axis=1),0,1)
            if kind=="basecolor":
                r,g,b = col.T
                skin_pixels[y,x] = (r>.60)&(g-b>.055)&(hp[:,2]<.92)
            target[kind][y,x,:3] = col
    # Propagate the nearest hair color across the tiny antialiased skin trim
    # and atlas gutters. All exterior paint originates in the supplied atlas.
    for kind,pixels in target.items():
        mask = owner>=0
        if kind=="basecolor":
            mask &= ~skin_pixels
        for _ in range(16):
            expanded = mask.copy()
            for axis,step in ((0,1),(1,1),(0,-1),(1,-1)):
                add = ~expanded & np.roll(mask,step,axis)
                pixels[add] = np.roll(pixels,step,axis)[add]
                expanded |= add
            if np.array_equal(expanded,mask):
                break
            mask = expanded
        fallback = {"basecolor":(.28,.15,.13),"normal":(.5,.5,1),"rm":(1,.65,0)}[kind]
        pixels[~mask,:3] = fallback
        pixels[:,:,3] = 1
        node = nodes[kind]
        old = node.image
        im = bpy.data.images.new("Spiky fitted "+kind,dim,dim,alpha=False)
        im.colorspace_settings.name = old.colorspace_settings.name
        im.pixels.foreach_set(pixels.ravel())
        with tempfile.TemporaryDirectory(dir=HERE/"work") as tmp:
            path = Path(tmp)/("Spiky_"+kind+(".jpg" if kind=="basecolor" else ".png"))
            im.file_format = "JPEG" if kind=="basecolor" else "PNG"
            im.filepath_raw = str(path)
            im.save(quality=96)
            data = path.read_bytes()
            im.pack(data=data,data_len=len(data))
        im.filepath_raw = "//"+path.name
        node.image = im
        bpy.data.images.remove(old)
    print("Studio texture samples",len(ys),"skin fringe texels repaired",int(skin_pixels.sum()))


def build():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    arm, body = [bpy.data.objects[n] for n in ("Armature","Base_Body")]
    tree = bob.tree_for(body,True)
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    obj, = [o for o in set(bpy.context.scene.objects)-before if o.type == "MESH"]
    obj.data.transform(obj.matrix_world)
    obj.parent = None
    obj.matrix_world = Matrix.Identity(4)
    obj.name, obj.data.name = NAME, "Spiky strands and fitted underside"
    obj.active_material.name = "Spiky original chestnut"
    mix = next(n for n in obj.active_material.node_tree.nodes if n.type=="MIX")
    mix.inputs[7].default_value = (.52,.404,.353,1)
    atlas = resize_maps(obj)
    geometry(obj,tree,atlas)
    head = obj.vertex_groups.new(name=bob.HEAD)
    neck = obj.vertex_groups.new(name=bob.NECK)
    for v in obj.data.vertices:
        w = .105*smooth(-.008,.095,v.co.y)*(1-smooth(.652,.760,v.co.z))
        w = w if w > .0001 else 0
        head.add([v.index],1-w,"REPLACE")
        if w:
            neck.add([v.index],w,"REPLACE")
    md = obj.modifiers.new("Master skeleton","ARMATURE")
    md.object = arm
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=str(GLB),export_format="GLB",use_selection=True,
          export_animations=False,export_def_bones=False,export_all_influences=False,export_tangents=True)
    obj.parent = arm
    arm.hide_set(True)
    for area in (a for s in bpy.data.screens for a in s.areas if a.type=="VIEW_3D"):
        space = area.spaces.active
        space.overlay.show_overlays = False
        space.shading.color_type = "TEXTURE"
        view = space.region_3d
        view.view_rotation = Vector((0,1,0)).to_track_quat("-Z","Y")
        view.view_distance, view.view_location, view.view_perspective = .8, ROOT, "ORTHO"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND),compress=True)
    print("Export", GLB.stat().st_size, hashlib.sha256(GLB.read_bytes()).hexdigest())


def sheet():
    # Import the exact GLB into the original master, separate from authoring.
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    sc = bpy.context.scene
    bob.cpu_studio(sc)
    camera = bpy.data.cameras.new("Fit camera")
    co = bpy.data.objects.new("Fit camera", camera)
    sc.collection.objects.link(co)
    sc.camera = co
    camera.type = "ORTHO"
    camera.ortho_scale = VIEW_SPAN
    target = Vector((0, 0, .807))
    sc.render.resolution_x = sc.render.resolution_y = 520
    points = [v.co.copy() for v in sc.objects[NAME].data.vertices]
    pixels = np.empty((1040, 1560, 4), dtype=np.float32)
    with tempfile.TemporaryDirectory(dir=HERE/"work") as tmp:
        for i, direction in enumerate(VIEWS):
            co.location = target + Vector(direction).normalized() * 2
            co.rotation_euler = (target - co.location).to_track_quat("-Z", "Y").to_euler()
            rotation = co.rotation_euler.to_quaternion().inverted()
            assert all(max(abs((rotation @ (p-target))[k]) for k in (0,1)) < VIEW_SPAN*.49 for p in points)
            sc.render.filepath = str(Path(tmp) / f"view{i}.png")
            bpy.ops.render.render(write_still=True)
            im = bpy.data.images.load(sc.render.filepath)
            # Join the rendered PNG samples in display space, without applying
            # a second view transform when the sheet is written.
            im.colorspace_settings.name = "Non-Color"
            a = np.empty(520 * 520 * 4, dtype=np.float32)
            im.pixels.foreach_get(a)
            y, x = (1 - i // 3) * 520, (i % 3) * 520
            pixels[y:y+520, x:x+520] = a.reshape((520, 520, 4))
            bpy.data.images.remove(im)
    result = bpy.data.images.new("Spiky fit views", 1560, 1040, alpha=True)
    result.colorspace_settings.name = "Non-Color"
    result.pixels.foreach_set(pixels.ravel())
    result.filepath_raw = str(HERE / "fit_views.png")
    result.file_format = "PNG"
    result.save()


def checker(kind):
    @bpy.app.handlers.persistent
    def cpu(scene,*_):
        if scene.camera and scene.camera.name=="c" and scene.render.engine=="BLENDER_WORKBENCH":
            bob.cpu_studio(scene)
    source = HERE/"work"/("motion_check_tri.py" if kind=="tri" else "motion_check.py")
    old = sys.argv
    bpy.app.handlers.frame_change_pre.append(cpu)
    try:
        with tempfile.TemporaryDirectory(dir=HERE/"work") as tmp:
            sys.argv = [str(source),"--",str(MASTER),str(MOTION),str(GLB),tmp]
            runpy.run_path(str(source),run_name="__main__")
            path = Path(tmp)/"motion_check.json"
            rows = json.loads(path.read_text())
            path.replace(HERE/source.with_suffix(".json").name)
            if kind=="vertex":
                for name in ("walk","run","wave","jump"):
                    (Path(tmp)/(name+".png")).replace(HERE/(name+".png"))
                # The supplied fixed action camera trims the top of the
                # airborne crown. Reframe the delivered jump at exactly the
                # checker's pose, preserving its measurement and raw image.
                (HERE/"jump.png").replace(HERE/"work/checker_jump.png")
                scene = bpy.context.scene
                dg = bpy.context.evaluated_depsgraph_get()
                points = []
                for obj_name in ("Base_Body","garment"):
                    ge = scene.objects[obj_name].evaluated_get(dg)
                    points.extend((ge.matrix_world@v.co).z for v in ge.data.vertices)
                scene.camera.location.z = (min(points)+max(points))*.5
                scene.render.filepath = str(HERE/"jump.png")
                bpy.ops.render.render(write_still=True)
            assert list(rows) == ["rest","walk","run","wave","jump","idle","nod","dance"]
            assert all(n==0 and d>=.0005 for n,d in rows.values()), rows
    finally:
        sys.argv = old
        bpy.app.handlers.frame_change_pre.remove(cpu)


def skin_audit():
    doc, binary = bob.read_glb(GLB)
    base, reference = bob.read_glb(MASTER.with_name("base_body.glb"))
    skin, = doc["skins"]
    base_skin, = base["skins"]
    def hierarchy(d, sk):
        return [(d["nodes"][j]["name"],[d["nodes"][c]["name"] for c in d["nodes"][j].get("children",[])])
                for j in sk["joints"]]
    joints = hierarchy(doc,skin)
    assert joints==hierarchy(base,base_skin) and len(joints)==65
    assert np.allclose(bob.accessor(doc,binary,skin["inverseBindMatrices"]),
                       bob.accessor(base,reference,base_skin["inverseBindMatrices"]),atol=1.e-6,rtol=0)
    names = [name for name,_ in joints]
    node, = [n for n in doc["nodes"] if "mesh" in n]
    assert node["name"]==NAME and node["skin"]==0
    assert not any(k in node for k in ("translation","rotation","scale","matrix"))
    assert not doc.get("animations")
    mesh, = doc["meshes"]
    triangles = max_influences = 0
    max_neck = 0.
    for prim in mesh["primitives"]:
        attr = prim["attributes"]
        assert "JOINTS_1" not in attr
        joints = bob.accessor(doc,binary,attr["JOINTS_0"])
        weights = bob.accessor(doc,binary,attr["WEIGHTS_0"])
        act = weights>0.
        assert np.allclose(weights.sum(1),1.,atol=1.e-6,rtol=0) and np.all(weights>=0)
        assert {names[i] for i in np.unique(joints[act])} <= {bob.HEAD,bob.NECK}
        max_neck = max(max_neck,float(np.where(joints==names.index(bob.NECK),weights,0).sum(1).max()))
        max_influences = max(max_influences,int(act.sum(1).max()))
        triangles += doc["accessors"][prim["indices"]]["count"]//3
    assert 0<triangles<=3000 and 0<max_neck<1 and max_influences<=4
    return dict(triangles=triangles,bytes=GLB.stat().st_size,joints=65,influences=max_influences,
                max_neck=max_neck,sha256=hashlib.sha256(GLB.read_bytes()).hexdigest())


def eye_audit(body,scalp,hair):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1.e-5)
    bm.verts.index_update()
    eye_faces = []
    for part in bob.connected_faces(bm):
        heights = [v.co.z for f in part for v in f.verts]
        if .67 < min(heights) and max(heights) < .80:
            eye_faces.extend(part)
    assert len(eye_faces) == 268
    eyes = BVHTree.FromPolygons([v.co.copy() for v in bm.verts],
                                [[v.index for v in f.verts] for f in eye_faces])
    bm.free()
    counts = []
    for camera in VIEWS[:3]:
        ray = Vector(camera).normalized()
        rotation = (-ray).to_track_quat('-Z', 'Y')
        right = rotation @ Vector((1, 0, 0))
        up = rotation @ Vector((0, 1, 0))
        kept = [0, 0]
        hidden = [0, 0]
        for y in range(230, 405):
            for x in range(30, 491):
                origin = Vector((0, 0, .807)) + ray + right * ((x + .5 - 260)
                                                               * VIEW_SPAN / 520) + up * ((260 - y - .5) * VIEW_SPAN / 520)
                eye = eyes.ray_cast(origin, -ray, 2)[0]
                if eye is None:
                    continue
                body_hit = scalp.ray_cast(origin, -ray, 2)[0]
                if body_hit is not None and (body_hit - eye).dot(ray) > .00003:
                    continue
                side = int(eye.x > 0)
                kept[side] += 1
                hit = hair.ray_cast(origin, -ray, 2)[0]
                if hit is not None and (hit - eye).dot(ray) > .00001:
                    hidden[side] += 1
        print("Eye pixels:", camera, kept, "hair occluded:", hidden)
        counts.append([sum(kept),sum(hidden)])
        assert min(kept) > 0 and sum(hidden) == 0

    return counts


def audit():
    stats = skin_audit()
    # Use the repository's installed Khronos validator, with no downloads.
    js = """const fs=require('node:fs'), v=require('gltf-validator');
v.validateBytes(fs.readFileSync(process.argv[1]), {uri:'hair_spiky_v1.glb'})
 .then(r=>process.stdout.write(JSON.stringify(r,null,2)))
 .catch(e=>{console.error(e);process.exitCode=1;});"""
    validation = subprocess.check_output(["node","-e",js,str(GLB)],cwd=bob.REPO,text=True)
    report = json.loads(validation)
    assert report["issues"]["numErrors"] == report["issues"]["numWarnings"] == 0,report["issues"]
    (HERE/"work/gltf_validator.json").write_text(validation+"\n")
    stats["validator"] = f'Khronos glTF Validator {report["validatorVersion"]} reported 0 errors and 0 warnings.'
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    body,arm = (bpy.data.objects[n] for n in ("Base_Body","Armature"))
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    hair = bpy.data.objects[NAME]
    maps = [n.image for n in hair.data.materials[0].node_tree.nodes if n.type=="TEX_IMAGE"]
    assert all(im.packed_file and max(im.size)<=1024 for im in maps)
    stats["textures"] = {im.name:list(im.size) for im in maps}
    bm = bmesh.new()
    bm.from_mesh(hair.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1.e-7)
    stats["topology"] = dict(components=len(bob.connected_faces(bm)),
                             boundary=sum(e.is_boundary for e in bm.edges),
                             nonmanifold=sum(not e.is_manifold for e in bm.edges))
    # UV charts and material primitives have duplicated glTF vertices.
    # Test non-adjacent triangles after rejoining those coincident seams.
    welded = bpy.data.meshes.new("Topology audit")
    bm.to_mesh(welded)
    stats["self_intersections"] = self_intersections(welded)
    bpy.data.meshes.remove(welded)
    assert stats["self_intersections"] == 0
    bm.free()
    assert stats["topology"] == {"components":1,"boundary":0,"nonmanifold":0}
    tree = bob.tree_for(body,True)
    ht = bob.tree_for(hair)
    stats["eyes"] = eye_audit(body,tree,ht)
    stats["upper_scalp"] = bob.crown_distances(tree,ht)
    cap_origin = Vector((ROOT.x,ROOT.y,1.22))
    axis = Vector((0.,0.,-1.))
    p = tree.ray_cast(cap_origin,axis)[0]
    stats["crown"] = ht.ray_cast(p-axis*.00001,-axis,.2)[0].z-p.z
    lower = []
    for az in range(-180,180,2):
        if abs(az)<75:
            continue
        # Stay above the pinna openings and inside the nape hem.
        floor = float(np.interp(abs(az), [75,105,125,180],[-2,-2,-23,-26]))
        for el in range(math.ceil(floor),25,2):
            a,e = math.radians(az),math.radians(el)
            ray = Vector((math.sin(a)*math.cos(e),-math.cos(a)*math.cos(e),math.sin(e)))
            p = tree.ray_cast(ROOT+.6*ray,-ray,.595)[0]
            q = ht.ray_cast(p+.00001*ray,ray,.16)[0]
            assert q is not None,(az,el)
            lower.append(tree.find_nearest(q)[3])
    stats["side_nape"] = [len(lower),min(lower),max(lower)]
    for _,minimum,maximum in (stats["upper_scalp"],stats["side_nape"]):
        assert .004<=minimum<=maximum<=.012,stats
    for md in hair.modifiers:
        if md.type=="ARMATURE":
            md.object=arm
    hair.parent = arm
    bpy.ops.import_scene.gltf(filepath=str(MOTION))
    arm.animation_data_create()
    stats["full_frames"] = {}
    for name in ("rest","walk","run","wave","jump","idle","nod","dance"):
        action = None if name=="rest" else bpy.data.actions[name]
        arm.animation_data.action=action
        frames = [1]
        if action:
            arm.animation_data.action_slot=action.slots[0]
            frames=range(int(action.frame_range[0]),int(action.frame_range[1])+1)
        min_dist = 1.
        inside = pairs = 0
        for frame in frames:
            bpy.context.scene.frame_set(frame)
            dg = bpy.context.evaluated_depsgraph_get()
            ge = hair.evaluated_get(dg)
            bt,gt = bob.tree_for(body.evaluated_get(dg)),bob.tree_for(ge)
            pairs = max(pairs,len(bt.overlap(gt)))
            signs = []
            for v in ge.data.vertices:
                pos = ge.matrix_world @ v.co
                hit,n,_,_ = bt.find_nearest(pos)
                signs.append((pos-hit).dot(n))
            inside = max(inside,sum(s<0 for s in signs))
            min_dist = min(min_dist,min(signs))
        stats["full_frames"][name] = [len(frames),inside,pairs,min_dist]
        print("FULL",name,stats["full_frames"][name],flush=True)
        assert inside==pairs==0 and min_dist>=.0005
    (HERE/"work/fit_audit.json").write_text(json.dumps(stats,indent=2)+"\n")
    print(json.dumps(stats,indent=2))


if __name__ == "__main__":
    stages = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else ["build","sheet","vertex","tri","audit"]
    for stage in stages:
        if stage=="build": build()
        elif stage=="sheet": sheet()
        elif stage in ("vertex","tri"): checker(stage)
        elif stage=="audit": audit()
        else: raise ValueError(stage)
