"""Fit the local Studio twin tails to the master and check the exported module.

Run in background Blender with --python fit_hair.py [-- build sheet underside vertex tri audit].
Uses the project's read-only bob helpers for mesh cuts and Cycles lighting.
"""
import hashlib
import importlib.util
import heapq
import json
import math
from pathlib import Path
import runpy
import sys
import tempfile

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
PARTS = HERE.parents[1]
SOURCE = HERE / "source_studio_retopo.glb"
MASTER = PARTS / "master/GJH_Chibi_Master_rigged.blend"
MOTION = PARTS.parents[1] / "models/tripo-chibi-motion/motion.glb"
GLB = HERE / "hair_twintails_v1.glb"
BLEND = HERE / "hair_twintails_v1.blend"
REFERENCE = PARTS / "white-bg/hair-03-twin-tails.png"
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("bob_fit", PARTS / "hair-fit-astra/fit_hair.py")
bob = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bob)
ROOT, HEAD, NECK = bob.ROOT, bob.HEAD, bob.NECK
smooth = bob.smooth
FRAMING = .73
CAMERA_TARGET = Vector((.001, 0, .812))
VIEWS = [(0, -1, 0), (.6, -1, .08), (-.6, -1, .08), (1, 0, .03), (0, 1, .06), (-1, 0, .03)]
PIXELS = 570


def tail_membership(bm):
    # Geodesic labels distinguish the inward-turning ends from the nape,
    # which overlaps them in front projection but lies on another surface.
    bm.verts.index_update()
    verts = list(bm.verts)
    def distances(seeds):
        dist = np.full(len(verts), np.inf)
        todo = []
        for v in seeds:
            dist[v.index] = 0.
            heapq.heappush(todo, (0., v.index))
        while todo:
            d, i = heapq.heappop(todo)
            if d > dist[i]:
                continue
            v = verts[i]
            for edge in v.link_edges:
                j = edge.other_vert(v).index
                cand = d + edge.calc_length()
                if cand < dist[j]:
                    dist[j] = cand
                    heapq.heappush(todo, (cand,j))
        return dist
    tails, cap = [], []
    for v in verts:
        x,y,z = v.co
        if abs(x) > .339 or (z < .23 and y > .035 and abs(x)>.235):
            tails.append(v)
        elif (abs(x)<.19 or y<-.075 or
              (y>.28 and abs(x)<.237) or (abs(x)<.29 and y<.03 and z<.54)):
            cap.append(v)
    a,b = distances(cap), distances(tails)
    return {v:smooth(-.030,.045,a[v.index]-b[v.index]) for v in verts}


def rebuild_cheek_ends(bm, uv, image):
    # The Studio cheek locks are fused to the painted face. Below a section
    # under the broad bangs their remaining cross-section doubles back into
    # small, skin-textured folds. Keep each original root and sweep a clean
    # underside and tip along its own measured centerline.
    level = .345
    region = [v for v in bm.verts if abs(v.co.z-level)<.10 and v.co.y<-.025 and abs(v.co.x)>.10]
    edges = {e for v in region for e in v.link_edges}
    faces = {f for e in edges for f in e.link_faces}
    bmesh.ops.bisect_plane(bm, geom=[*region,*edges,*faces], dist=1e-7,
                           plane_co=(0,0,level), plane_no=(0,0,1))
    low = {f for f in bm.faces if max(v.co.z for v in f.verts) < level+1e-6}
    repair = []
    while low:
        stack = [low.pop()]
        group = []
        while stack:
            f = stack.pop()
            group.append(f)
            for e in f.edges:
                for other in e.link_faces:
                    if other in low:
                        low.remove(other)
                        stack.append(other)
        coords = np.array([v.co[:] for f in group for v in f.verts])
        if .08 < coords[:,2].min() < .12 and coords[:,1].max() < -.02:
            repair.append(group)
    assert len(repair) == 2
    profile = []
    for group in repair:
        slice_edges = {e for f in group for e in f.edges if min(v.co.z for v in e.verts)>level-1e-6}
        vertices = {v for e in slice_edges for v in e.verts}
        ends = [v for v in vertices if sum(e in slice_edges for e in v.link_edges)==1]
        assert len(ends)==2
        arc = [min(ends,key=lambda v:v.co.y)]
        while slice_edges:
            e, = [e for e in arc[-1].link_edges if e in slice_edges]
            slice_edges.remove(e)
            arc.append(e.other_vert(arc[-1]))
        sign = math.copysign(1,arc[0].co.x)
        for f in group:
            # Sample the undamaged outward-facing surface of the input lock.
            if f.normal.x*sign < .3 or f.normal.y > .45:
                continue
            pos = f.calc_center_median()
            st = sum((l[uv].uv for l in f.loops),Vector((0,0)))/len(f.loops)
            h,w,_ = image.shape
            color = image[int(st.y*h)%h,int(st.x*w)%w,:3]
            if color[0]+1.65*(color[1]-color[2]) < .84:
                profile.append((pos.z,color.copy()))
        bmesh.ops.delete(bm,geom=group,context='FACES')
        heights = [.09,.105,.13,.16,.20,.25,.295,.325,.345]
        centers = [.148,.159,.179,.192,.201,.208,.214,.216,.217]
        depth = [-.146,-.144,-.137,-.131,-.125,-.118,-.113,-.111,-.11]
        widths = [0,.011,.022,.030,.036,.041,.041,.041,.042]
        radial = [0,.005,.009,.012,.013,.013,.014,.014,.014]
        def point(z,theta):
            cx = np.interp(z,heights,centers) + (.028 if sign>0 else 0)
            cy = np.interp(z,heights,depth)
            width = np.interp(z,heights,widths)*math.cos(theta)
            thick = np.interp(z,heights,radial)*math.sin(theta)
            return Vector((sign*(cx+.44*width+.898*thick), cy+.898*width-.44*thick,z))
        lengths = np.array([(v.co-arc[(i+1)%len(arc)].co).length for i,v in enumerate(arc)])
        ts = np.r_[0.,np.cumsum(lengths)/lengths.sum()]
        def difference(config):
            phase,turn = config
            return sum((v.co-point(level,phase+turn*2*math.pi*t)).length_squared for v,t in zip(arc,ts))
        phase,turn=min(((p,d) for p in np.arange(0,2*math.pi,.10) for d in [-1,1]),key=difference)
        def face(verts, params):
            f=bm.faces.new(verts)
            f.smooth=True
            f.material_index=1
            for l,(t,z) in zip(f.loops,params):
                l[uv].uv=(t, (z-.09)/(level-.09))
        prev, previous_t, previous_z = arc,ts,level
        n=14
        for z in reversed(heights[1:-1]):
            row = [bm.verts.new(point(z,phase+turn*2*math.pi*i/n)) for i in range(n)]
            i=j=0
            while i<len(prev) or j<n:
                a, b = prev[i%len(prev)],row[j%n]
                if i<len(prev) and (j==n or previous_t[i+1] <= (j+1)/n):
                    face([a,prev[(i+1)%len(prev)],b],[(previous_t[i],previous_z),(previous_t[i+1],previous_z),(j/n,z)])
                    i+=1
                else:
                    face([a,row[(j+1)%n],b],[(previous_t[i],previous_z),((j+1)/n,z),(j/n,z)])
                    j+=1
            prev,previous_t,previous_z=row,np.linspace(0,1,n+1),z
        tip=bm.verts.new(point(.09,0))
        for i in range(n):
            face([prev[i],prev[(i+1)%n],tip],[(i/n,previous_z),((i+1)/n,previous_z),((i+.5)/n,.09)])
    # Smoothly interpolate three strand color quantiles measured on the donor.
    palette=[]
    for z in np.linspace(.09,level,18):
        samples=np.array([c for h,c in profile if abs(h-z)<.037])
        palette.append(np.quantile(samples,[.28,.57,.78],axis=0))
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts)>3])
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    return np.array(palette)


def extract(obj, image):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    bm.normal_update()
    assert len(bm.faces) == 9746 and len(bob.connected_faces(bm)) == 1
    # One short four-face edge pinches together two crown ridges in Studio.
    # Removing the collapsed contact restores the separate surface fans.
    pinch, = [e for e in bm.edges if len(e.link_faces) > 2]
    bmesh.ops.collapse(bm, edges=[pinch])
    label = bm.verts.layers.float.new("Gathered tail")
    uv = bm.loops.layers.uv.active
    size = image.size[0]
    colors = np.empty(size * size * 4, dtype=np.float32)
    image.pixels.foreach_get(colors)
    colors = colors.reshape(size, size, 4)
    values = {}
    for v in bm.verts:
        x, y, z = v.co
        # The blank face, ears and neck share topology with the fringe.
        # The purple ties and the free, curled tails are outside this region.
        if z > .56 or abs(x) > .299 or (abs(x) > .235 and y > .12):
            values[v] = 1.
            continue
        scores = []
        for loop in v.link_loops:
            center = sum((l[uv].uv for l in loop.face.loops), Vector((0, 0))) / 3
            coord = loop[uv].uv.lerp(center, .12)
            r, g, b = colors[int(coord.y * size) % size, int(coord.x * size) % size, :3]
            scores.append(.86 - r - 1.65 * (g - b))
        values[v] = float(np.median(scores))
    # Only the connected negative region containing the mannequin face is
    # removed. Isolated light highlights in the chestnut are still hair.
    negative = {v for v in bm.verts if values[v] < 0}
    islands = []
    while negative:
        stack = [negative.pop()]
        group = []
        while stack:
            v = stack.pop()
            group.append(v)
            for e in v.link_edges:
                w = e.other_vert(v)
                if w in negative:
                    negative.remove(w)
                    stack.append(w)
        islands.append(group)
    for group in sorted(islands, key=len, reverse=True)[1:]:
        for v in group:
            values[v] = .25
    tail_weights = tail_membership(bm)
    for v in bm.verts:
        v[label] = tail_weights[v]
        x, y, z = v.co
        # Trim the buried turn beneath the nape where the Studio color turns
        # brown in the shadow of the neck. The curls lie outside this cavity.
        if y > -.025 and z < .38:
            radius = math.hypot(x, y)
            floor = .185 * (1 - smooth(.26, .38, z)) * smooth(-.025, .055, y)
            values[v] = min(values[v], 6*(radius - floor))
        if y > -.14 and tail_weights[v] < .4 and z < .46:
            angle = abs(math.degrees(math.atan2(x, -y)))
            rim = np.interp(angle, [58,68,78,86,97,105,115,128,180],
                            [.04,.16,.305,.37,.359,.319,.234,.17,.125])
            values[v] = min(values[v], 5*(z-rim))
    bob.trim_field(bm, values)
    parts = bob.connected_faces(bm)
    for group in parts[1:]:
        if len(group) < 20:
            bmesh.ops.delete(bm, geom=group, context='FACES')
    # Cut just behind the color transition so antialiased flesh-colored
    # texels cannot form a light rim around the new hair opening.
    boundary = {v for e in bm.edges if e.is_boundary for v in e.verts}
    relaxed = {}
    for v in boundary:
        ends = [e.other_vert(v).co for e in v.link_edges if e.is_boundary]
        if len(ends) == 2:
            relaxed[v] = v.co.lerp((ends[0] + ends[1]) * .5, .55)
    for v, co in relaxed.items():
        v.co = co
    palette = rebuild_cheek_ends(bm, uv, colors)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    print("Extracted triangles", len(obj.data.polygons), flush=True)
    return palette


def fit_point(p, skin, tail):
    x, y, z = p
    front = smooth(.07, .24, -y)
    low = 1 - smooth(.34, .70, z)
    raw = Vector((.001 + (.685 - .035*tail) * x, (.653 - .033*tail)*y,
                  .836 + .51 * (z - .42) + .037 * front * low))
    curl = tail * (1 - smooth(.19, .57, z))
    raw.x -= math.copysign(.015 * curl, x)
    raw.y -= .023 * curl
    raw.z -= .006 * curl
    tuck = tail * math.exp(-((z-.23)/.17)**2) * (1-.48*smooth(.36,.48,abs(x)))
    raw.x -= math.copysign(.029*tuck, x)
    raw.y -= .037*tuck
    raw.z += .016 * smooth(.09, .17, abs(x)) * smooth(.135, .20, -y) * (1-smooth(.35, .55, z))
    raw.z -= .006 * (1 - smooth(.085,.16,abs(x))) * front * low
    delta = raw - ROOT
    ray = delta.normalized()
    loc, normal, _, _ = skin.ray_cast(ROOT + .53 * ray, -ray, .526)
    if loc is None:
        return raw
    facing = max(.52, normal.dot(ray))
    gap = (raw - loc).dot(ray) * facing
    clearance = .010 + .009 * np.logaddexp(0., (gap - .005) / .009)
    roof = smooth(.65,.982,ray.z)*(1-tail)
    clearance += roof*(.0111+.00055*math.tanh((gap-.016)/.014)-clearance)
    return loc + ray * (clearance / facing)


def mesh_arrays(mesh):
    mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)
    def collect(items, attribute, n, dtype='f'):
        data = np.empty(len(items) * n, dtype=dtype)
        items.foreach_get(attribute, data)
        return data.reshape(-1, n)
    ids = np.asarray([f.vertices[:] for f in mesh.polygons])
    loops = np.asarray([f.loop_indices[:] for f in mesh.polygons])
    positions = collect(mesh.vertices, 'co', 3)[ids]
    normal = collect(mesh.corner_normals, 'vector', 3)[loops]
    tangent = collect(mesh.loops, 'tangent', 3)[loops]
    sign = collect(mesh.loops, 'bitangent_sign', 1)[loops]
    uv = collect(mesh.uv_layers.active.data, 'uv', 2)[loops]
    return positions, normal, tangent, sign, uv


def normalize(rows):
    return rows / np.maximum(1e-12, np.linalg.norm(rows, axis=-1, keepdims=True))


def transfer_atlas(obj, original, maps, palette):
    # Decimating across the Studio atlas's 767 UV islands would interpolate
    # unrelated texels. Resample all three original maps in fitted 3D
    # space. Change tangent bases before packing the new normal map.
    mesh = obj.data
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if mesh.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    for f in mesh.polygons:
        f.use_smooth = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(65), island_margin=.012,
                             area_weight=.35, correct_aspect=False, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    for d in mesh.uv_layers.active.data:
        d.uv.y = .04 + .96 * d.uv.y
    repaired = np.array([f.material_index == 1 for f in original.polygons])
    assert np.any(repaired)
    src = mesh_arrays(original)
    dst = mesh_arrays(mesh)
    source_tree = BVHTree.FromPolygons([v.co for v in original.vertices],
                                       [f.vertices[:] for f in original.polygons], all_triangles=True)
    size = 1024
    textures = {}
    atlases = {}
    for key, im in maps.items():
        w, h = im.size
        pix = np.empty(4 * w * h, 'f')
        im.pixels.foreach_get(pix)
        textures[key] = (pix.reshape(h, w, 4)[:, :, :3] * 255 + .5).astype('B')
        atlases[key] = np.zeros((size, size, 3), dtype='f')
        del pix
    filled = np.zeros((size, size), dtype=bool)
    for idx, (a, b, c) in enumerate(dst[4]):
        vertices = np.stack((a, b, c)) * size - .5
        u0, v0 = np.maximum(0, np.ceil(vertices.min(0))).astype(int)
        u1, v1 = np.minimum(size-1, np.floor(vertices.max(0))).astype(int)
        yy, xx = np.mgrid[v0:v1+1, u0:u1+1]
        basis = (vertices[1:] - vertices[0]).T
        if abs(np.linalg.det(basis)) < 1e-8:
            continue
        uvw = (np.stack((xx, yy), axis=-1) - vertices[0]) @ np.linalg.inv(basis).T
        bary = np.dstack((1 - uvw.sum(-1), uvw))
        mask = bary.min(-1) >= -1e-6
        if not mask.any():
            continue
        ys, xs, bary = yy[mask], xx[mask], bary[mask]
        pos = bary @ dst[0][idx]
        near = []
        for p, target_normal in zip(pos, normalize(bary @ dst[1][idx])):
            point, normal = Vector(p), Vector(target_normal)
            h = source_tree.find_nearest(point)
            if h[1].dot(normal) < .65:
                reach = min(.012, .002 + 2*h[3])
                candidates = source_tree.find_nearest_range(point, reach)
                if candidates:
                    h = min(candidates, key=lambda hit: hit[3] + .012*(1-max(-1.,hit[1].dot(normal)))**2)
            near.append(h)
        faces = np.array([h[2] for h in near])
        q = np.array([h[0][:] for h in near])
        tri = src[0][faces]
        e1, e2 = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
        cross = np.cross(e1, e2)
        area_sq = np.maximum(1e-24, (cross * cross).sum(1))
        delta = q - tri[:, 0]
        u = (np.cross(delta, e2) * cross).sum(1) / area_sq
        v = (np.cross(e1, delta) * cross).sum(1) / area_sq
        w = np.stack((1 - u - v, u, v), axis=1)
        texcoord = np.einsum('ij,ijk->ik', w, src[4][faces])
        for key, pixels in textures.items():
            wh = np.array(pixels.shape[1::-1])
            at = texcoord * wh - .5
            floor = np.floor(at).astype(int)
            frac = at - floor
            color = np.zeros((len(pos), 3))
            for ox, oy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                c = pixels[(floor[:, 1] + oy) % wh[1], (floor[:, 0] + ox) % wh[0]]
                weight = (frac[:, 0] if ox else 1 - frac[:, 0]) * (frac[:, 1] if oy else 1 - frac[:, 1])
                color += c * weight[:, None] / 255
            new = repaired[faces]
            if new.any():
                if key == 'basecolor':
                    t = np.clip(texcoord[new,1],0,1)*(len(palette)-1)
                    h = np.minimum(t.astype(int),len(palette)-2)
                    mix = (t-h)[:,None,None]
                    tones = palette[h]*(1-mix)+palette[h+1]*mix
                    along = .5 + .5*np.cos(2*math.pi*(texcoord[new,0]-.33))
                    m = along[:,None]
                    color[new] = (1-m)**2*tones[:,0]+2*m*(1-m)*tones[:,1]+m**2*tones[:,2]
                else:
                    color[new] = (.5,.5,1.) if key=='normal' else (1.,.61,0.)
            if key == 'normal':
                def frame(normal, tangent, sign):
                    n = normalize(normal)
                    t = normalize(tangent - (tangent * n).sum(1, keepdims=True) * n)
                    return t, np.cross(n, t) * np.sign(sign), n
                source = frame(*(np.einsum('ij,ijk->ik', w, data[faces]) for data in src[1:4]))
                destination = frame(*(bary @ data[idx] for data in dst[1:4]))
                vector = sum((2*color[:, k:k+1]-1) * source[k] for k in range(3))
                color = .5 + .5*normalize(np.stack([(vector * axis).sum(1) for axis in destination], axis=1))
            if key == 'basecolor':
                # Only antialiased skin texels at the new opening need hair
                # color. Preserve the original highlight and purple tie texels.
                edge = (pos[:, 2] < .865) & (abs(pos[:, 0]) < .207)
                skin = color[:, 0] + 1.65 * (color[:, 1] - color[:, 2]) > .86
                color[edge & skin] = (.38, .19, .135)
            atlases[key][ys, xs] = color
        filled[ys, xs] = True
    # Eight texels of edge padding also covers the first mip levels.
    for _ in range(10):
        remaining = ~filled
        grew = np.zeros_like(filled)
        for direction in ((1,0),(-1,0),(0,1),(0,-1)):
            mask = remaining & np.roll(filled, direction, axis=(0,1))
            if mask.any():
                for img in atlases.values():
                    img[mask] = np.roll(img, direction, axis=(0,1))[mask]
                remaining[mask] = False
                grew |= mask
        filled |= grew
    for key, values in atlases.items():
        swatch = {'basecolor': (.32, .155, .11), 'normal': (.5, .5, 1.), 'rm': (1., .61, 0.)}[key]
        values[~filled] = swatch
        values[:27, :, :] = swatch
        im = bpy.data.images.new('Twintails_' + key, size, size, alpha=False)
        im.colorspace_settings.name = 'sRGB' if key == 'basecolor' else 'Non-Color'
        rgba = np.ones((size, size, 4), 'f')
        rgba[:, :, :3] = np.clip(values, 0, 1)
        im.pixels.foreach_set(rgba.ravel())
        filename = 'Twintails_' + key + ('.jpg' if key == 'basecolor' else '.png')
        with tempfile.TemporaryDirectory(dir=WORK) as tmp:
            im.filepath_raw = str(Path(tmp) / filename)
            im.file_format = 'JPEG' if key == 'basecolor' else 'PNG'
            im.save(quality=96)
            data = Path(im.filepath_raw).read_bytes()
            im.pack(data=data, data_len=len(data))
        im.filepath_raw = '//' + filename
        node = next(n for n in obj.active_material.node_tree.nodes if n.type=='TEX_IMAGE' and n.image==maps[key])
        node.image = im
        bpy.data.images.remove(maps[key])
    print('Source texture transfer complete', flush=True)


def boundary_cycles(bm):
    edges = {e for e in bm.edges if e.is_boundary}
    loops = []
    while edges:
        start = min(edges, key=lambda e: e.index)
        v = start.verts[0]
        ring = [v]
        e = start
        while e in edges:
            edges.remove(e)
            v = e.other_vert(v)
            if v == ring[0]:
                break
            ring.append(v)
            remaining = [k for k in v.link_edges if k in edges]
            if not remaining:
                raise ValueError('Open chain at the hairline')
            e = min(remaining, key=lambda k:k.index)
        loops.append(ring)
    return sorted(loops, key=len, reverse=True)


def add_lining(obj, skin):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    contours = boundary_cycles(bm)
    uv = bm.loops.layers.uv.active
    def face(verts, contact=False):
        f = bm.faces.new(verts)
        f.smooth = True
        for l in f.loops:
            l[uv].uv = (.5 + 1.3*l.vert.co.x, (.008 if contact else .020) + .010*(l.vert.co.z-.8))
        return f
    for loop in contours[1:]:
        face(loop)
    rim = contours[0]
    def polar(pt):
        d = (pt - ROOT).normalized()
        return math.atan2(d.x, -d.y), math.asin(d.z)
    angles = np.unwrap([polar(v.co)[0] for v in rim + [rim[0]]])
    if angles[-1] < angles[0]:
        rim.reverse()
    start = min(range(len(rim)), key=lambda j: abs(abs(polar(rim[j].co)[0]) - math.pi))
    rim = rim[start:] + rim[:start]
    angles = np.unwrap([polar(v.co)[0] for v in rim + [rim[0]]])
    elevations = np.array([polar(v.co)[1] for v in rim])
    # A fitted underside runs from the actual cut boundary up to the crown.
    # This is the exposed inside of the detachable wig, including the root
    # sockets. All original closed mannequin and trapped lining faces go.
    cols = 40
    rings = 7
    def point(a, e):
        ray = Vector((math.cos(e)*math.sin(a), -math.cos(e)*math.cos(a), math.sin(e)))
        loc, n, _, _ = skin.ray_cast(ROOT + ray * .53, -ray, .528)
        target = .0096 - .0022*smooth(.58,.92,ray.z)
        lo, hi = 0., .045
        for _ in range(16):
            mid = (lo+hi)/2
            if skin.find_nearest(loc+ray*mid)[3] < target:
                lo = mid
            else:
                hi = mid
        return loc + ray * hi
    band = []
    for i in range(cols):
        a = angles[0] + 2 * math.pi * i / cols
        dist = np.angle(np.exp(1j * (angles[:-1] - a)))
        weights = np.exp(-.5*(dist/.115)**2)
        edge = np.average(elevations, weights=weights) + .045
        # The liner sits just above the wispy tips. Between the bangs the
        # actual scalp opening can turn back on itself in angular space.
        if math.cos(a) > .55:
            edge = min(edge, math.radians(21))
        az = abs(math.degrees(math.atan2(math.sin(a),math.cos(a))))
        pinna = np.interp(az,[0,65,78,86,101,109,119,140,180],
                          [-90,-55,-15,-5,-5,-10,-27,-70,-75])
        band.append(max(edge,math.radians(pinna)))
    pole = bm.verts.new(point(0, math.pi/2))
    rows = []
    for j in range(1, rings+1):
        row = []
        for i, edge in enumerate(band):
            a = angles[0] + 2 * math.pi*i/cols
            row.append(bm.verts.new(point(a, math.pi/2 + (edge-math.pi/2)*j/rings)))
        rows.append(row)
        prev = rows[-2] if j > 1 else None
        for i in range(cols):
            k = (i+1)%cols
            face([row[i], row[k], prev[k], prev[i]] if prev else [row[i], row[k], pole], contact=True)
    # Match the irregular traced border to the regular inner rim in order.
    t = np.maximum.accumulate(angles-angles[0])/(2*math.pi)
    t = np.clip(t, 0, 1)
    cycle = rows[-1]
    i = j = 0
    while i<len(rim) or j<cols:
        v, w = rim[i%len(rim)], cycle[j%cols]
        if i<len(rim) and (j==cols or t[i+1] <= (j+1)/cols):
            face([v,rim[(i+1)%len(rim)],w])
            i+=1
        else:
            face([v,cycle[(j+1)%cols],w])
            j+=1
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    print('Closed lining, triangles', len(bm.faces),'border vertices',len(rim),
          'remaining boundary edges',sum(e.is_boundary for e in bm.edges),flush=True)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def tune_contact(obj, skin):
    # The outer hem crosses a convex ear. Support its full triangles, then
    # return the inner rim to the scalp without dragging those faces back
    # through the pinna.
    bob.support_faces(obj,skin)
    mesh=obj.data
    contact = {k for f in mesh.polygons
               if max(mesh.uv_layers.active.data[i].uv.y for i in f.loop_indices)<.013
               for k in f.vertices}
    for k in contact:
        v=mesh.vertices[k]
        hit,_,_,d=skin.find_nearest(v.co)
        if d>.0107:
            v.co=hit+(v.co-hit).normalized()*.0095
    for _ in range(8):
        offsets={}
        for face in mesh.polygons:
            a,b,c=[mesh.vertices[k].co for k in face.vertices]
            for j in range(9):
                for k in range(9-j):
                    p=a+(b-a)*(j/8)+(c-a)*(k/8)
                    hit,n,_,_=skin.find_nearest(p)
                    signed=(p-hit).dot(n)
                    if signed<.0045:
                        amount=.0049-signed
                        for idx in face.vertices:
                            if idx not in offsets or amount>offsets[idx][0]:
                                offsets[idx]=(amount,n.copy())
        if not offsets:
            break
        for k,(d,n) in offsets.items():
            mesh.vertices[k].co+=min(.003,d)*n
    mesh.update()
    bm=bmesh.new()
    bm.from_mesh(mesh)
    uv=bm.loops.layers.uv.active
    inside={f for f in bm.faces if max(l[uv].uv.y for l in f.loops)<.013}
    verts={v for f in inside for v in f.verts}
    edges={e for f in inside for e in f.edges if any(g not in inside for g in e.link_faces)}
    border={v for e in edges for v in e.verts}
    roll={}
    for v in verts:
        hit,_,_,d=skin.find_nearest(v.co)
        if d<=.0107:
            continue
        point=hit+(v.co-hit).normalized()*.0094
        if v in border:
            roll[v]=bm.verts.new(point)
        else:
            v.co=point
    # Preserve the supported exterior. Only the short turn at a distant
    # liner corner gets a new course. Inside and outside share every edge.
    patch={f for v in roll for f in v.link_faces if f in inside}
    new_faces=[]
    for f in patch:
        data=[(roll.get(l.vert,l.vert),l[uv].uv.copy()) for l in f.loops]
        new_faces.append(data)
    # Remember the border edges before replacing incident faces.
    joins=[e.verts[:] for e in edges if any(v in roll for v in e.verts)]
    bmesh.ops.delete(bm,geom=list(patch),context='FACES_ONLY')
    for data in new_faces:
        f=bm.faces.new([v for v,_ in data])
        f.smooth=True
        for l,(_,st) in zip(f.loops,data):
            l[uv].uv=st
    for a,b in joins:
        vs=list(dict.fromkeys([a,b,roll.get(b,b),roll.get(a,a)]))
        f=bm.faces.new(vs)
        f.smooth=True
        for l in f.loops:
            l[uv].uv=(.5+l.vert.co.x,.020+.01*(l.vert.co.z-.8))
    bmesh.ops.delete(bm,geom=[e for e in bm.edges if not e.link_faces],context='EDGES')
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def build():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    scene = bpy.context.scene
    body, arm = scene.objects['Base_Body'], scene.objects['Armature']
    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    added = set(scene.objects) - before
    obj, = [o for o in added if o.type == 'MESH']
    obj.data.transform(obj.matrix_world)
    obj.parent = None
    obj.matrix_world = Matrix.Identity(4)
    for other in added - {obj}:
        bpy.data.objects.remove(other, do_unlink=True)
    obj.name = 'Hair_Twintails'
    obj.data.name = 'Studio twin tails'
    mat = obj.active_material
    mat.name = 'Chestnut hair and violet ties'
    maps = {n.image.name.rsplit('_', 1)[-1].split('.')[0]: n.image for n in mat.node_tree.nodes
            if n.type == 'TEX_IMAGE'}
    obj.data.materials.append(mat)
    palette = extract(obj, maps['basecolor'])
    skin = bob.tree_for(body, True)
    label = obj.data.attributes['Gathered tail']
    for v in obj.data.vertices:
        v.co = fit_point(v.co.copy(), skin, label.data[v.index].value)
    obj.data.attributes.remove(label)
    bpy.context.view_layer.objects.active = obj
    if obj.data.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    for f in obj.data.polygons:
        f.use_smooth = True
    obj.data.update()
    original = obj.data.copy()
    mod = obj.modifiers.new('Silhouette reduction', 'DECIMATE')
    mod.ratio = min(1., 2250 / len(obj.data.polygons))
    mod.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    transfer_atlas(obj, original, maps, palette)
    for f in obj.data.polygons:
        f.material_index = 0
    obj.data.materials.pop(index=1)
    bpy.data.meshes.remove(original)
    add_lining(obj, skin)
    bob.correct_clearance(obj, skin)
    tune_contact(obj, skin)
    if obj.data.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    for f in obj.data.polygons:
        f.use_smooth = True
    factor = next(n for n in mat.node_tree.nodes if n.type == 'MIX')
    factor.inputs[7].default_value = (.60, .54, .52, 1.)
    h = obj.vertex_groups.new(name=HEAD)
    n = obj.vertex_groups.new(name=NECK)
    for v in obj.data.vertices:
        x, y, z = v.co
        w = .105 * smooth(-.008, .095, y) * (1 - smooth(.652, .760, z))
        if w < .0001:
            w = 0.
        h.add([v.index], 1 - w, 'REPLACE')
        if w:
            n.add([v.index], w, 'REPLACE')
    obj.modifiers.new('Master skeleton', 'ARMATURE').object = arm
    bpy.ops.object.select_all(action='DESELECT')
    for o in (arm, obj):
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(GLB), export_format='GLB', use_selection=True,
                              export_tangents=True, export_animations=False, export_all_influences=False, export_def_bones=False)
    obj.parent = arm
    arm.hide_set(True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                space.overlay.show_overlays = False
                space.shading.color_type = 'TEXTURE'
                space.region_3d.view_rotation = Vector((0, 1, 0)).to_track_quat('-Z', 'Y')
                space.region_3d.view_distance = .92
                space.region_3d.view_location = CAMERA_TARGET
                space.region_3d.view_perspective = 'ORTHO'
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print('Export', len(obj.data.polygons), GLB.stat().st_size, hashlib.sha256(GLB.read_bytes()).hexdigest())


def sheet(hair_only=False):
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    scene = bpy.context.scene
    bob.cpu_studio(scene)
    if hair_only:
        scene.objects['Base_Body'].hide_render = True
    views = [(0,-1,0), (.30,-.56,-1)] if hair_only else VIEWS
    cols, rows = (2,1) if hair_only else (3,2)
    cam = bpy.data.cameras.new('Orthographic fit')
    co = bpy.data.objects.new(cam.name, cam)
    scene.collection.objects.link(co)
    scene.camera = co
    cam.type = 'ORTHO'
    cam.ortho_scale = FRAMING
    size = PIXELS
    scene.render.resolution_x = scene.render.resolution_y = size
    pixels = np.empty((rows * size, cols * size, 4), 'f')
    with tempfile.TemporaryDirectory(dir=WORK) as tmp:
        for i, view in enumerate(views):
            co.location = CAMERA_TARGET + 2 * Vector(view).normalized()
            co.rotation_euler = (CAMERA_TARGET - co.location).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = str(Path(tmp) / f'{i}.png')
            bpy.ops.render.render(write_still=True)
            im = bpy.data.images.load(scene.render.filepath)
            im.colorspace_settings.name = 'Non-Color'
            a = np.empty(size * size * 4, 'f')
            im.pixels.foreach_get(a)
            y, x = (rows - 1 - i // cols) * size, i % cols * size
            pixels[y:y+size, x:x+size] = a.reshape(size, size, 4)
            bpy.data.images.remove(im)
    out = bpy.data.images.new('Twin tails fit views', cols * size, rows * size, alpha=True)
    out.colorspace_settings.name = 'Non-Color'
    out.pixels.foreach_set(pixels.ravel())
    out.filepath_raw = str(WORK / 'hair_underside.png' if hair_only else HERE / 'fit_views.png')
    out.file_format = 'PNG'
    out.save()


def check(kind):
    @bpy.app.handlers.persistent
    def cpu(scene, *_):
        if scene.camera and scene.camera.name == 'c' and scene.render.engine == 'BLENDER_WORKBENCH':
            bob.cpu_studio(scene)

    script = WORK / ('motion_check_tri.py' if kind == 'tri' else 'motion_check.py')
    old = sys.argv.copy()
    bpy.app.handlers.frame_change_pre.append(cpu)
    try:
        with tempfile.TemporaryDirectory(dir=WORK) as tmp:
            sys.argv = [str(script), '--', str(MASTER), str(MOTION), str(GLB), tmp]
            runpy.run_path(str(script), run_name='__main__')
            result = Path(tmp) / 'motion_check.json'
            data = json.loads(result.read_text())
            result.replace(HERE / script.with_suffix('.json').name)
            if kind == 'vertex':
                for name in ('walk', 'run', 'wave', 'jump'):
                    (Path(tmp) / (name + '.png')).replace(HERE / (name + '.png'))
                # The supplied static camera clips the crown at the height
                # of this jump. Retain the raw frame and render the same
                # evaluated pose with vertical headroom for the fit preview.
                scene=bpy.context.scene
                assert scene.objects['Armature'].animation_data.action.name=='jump'
                coords=[]
                dg=bpy.context.evaluated_depsgraph_get()
                for key in ('Base_Body','garment'):
                    o=scene.objects[key].evaluated_get(dg)
                    coords.extend((o.matrix_world@v.co).z for v in o.data.vertices)
                (HERE/'jump.png').replace(WORK/'jump_checker.png')
                scene.camera.location.z=(min(coords)+max(coords))/2
                scene.render.filepath=str(HERE/'jump.png')
                bpy.ops.render.render(write_still=True)
            assert list(data) == ['rest', 'walk', 'run', 'wave', 'jump', 'idle', 'nod', 'dance']
            assert all(n == 0 and d >= .0005 for n, d in data.values()), data
    finally:
        sys.argv = old
        bpy.app.handlers.frame_change_pre.remove(cpu)


def audit():
    bob.GLB = GLB
    validation = bob.validator()
    assert '0 errors and 0 warnings' in validation, validation
    doc, blob = bob.read_glb(GLB)
    ref, ref_blob = bob.read_glb(MASTER.with_name('base_body.glb'))
    mesh, = doc['meshes']
    prim, = mesh['primitives']
    node, = [n for n in doc['nodes'] if 'mesh' in n]
    assert node['name'] == 'Hair_Twintails' and not doc.get('animations')
    assert not any(k in node for k in ('matrix', 'scale', 'translation', 'rotation'))
    def skeleton(g):
        skin, = g['skins']
        nodes = g['nodes']
        return [(nodes[i]['name'], [nodes[j]['name'] for j in nodes[i].get('children', [])])
                for i in skin['joints']]
    joints = skeleton(doc)
    assert joints == skeleton(ref) and len(joints) == 65
    assert np.allclose(bob.accessor(doc, blob, doc['skins'][0]['inverseBindMatrices']),
                       bob.accessor(ref, ref_blob, ref['skins'][0]['inverseBindMatrices']), atol=1e-6, rtol=0)
    weights = bob.accessor(doc, blob, prim['attributes']['WEIGHTS_0'])
    indices = bob.accessor(doc, blob, prim['attributes']['JOINTS_0'])
    active = weights > 0
    assert set(prim['attributes']) == {'POSITION','NORMAL','TANGENT','TEXCOORD_0','WEIGHTS_0','JOINTS_0'}
    assert np.allclose(weights.sum(1), 1, atol=1e-6)
    assert {joints[k][0] for k in np.unique(indices[active])} == {HEAD, NECK}
    neck = np.where(indices == [x[0] for x in joints].index(NECK), weights, 0).sum(1)
    tri = doc['accessors'][prim['indices']]['count'] // 3
    assert tri <= 3000 and int(active.sum(1).max()) <= 4
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    sc = bpy.context.scene
    body, arm = sc.objects['Base_Body'], sc.objects['Armature']
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    obj = sc.objects['Hair_Twintails']
    images = {n.image.name:tuple(n.image.size) for n in obj.active_material.node_tree.nodes if n.type=='TEX_IMAGE'}
    assert len(images) == 3 and all(max(size) <= 1024 for size in images.values())
    assert all('bufferView' in im for im in doc['images'])
    skin, hair = bob.tree_for(body, True), bob.tree_for(obj)
    cap = bob.crown_distances(skin,hair)
    axis = Vector((0,0,-1))
    above = Vector((ROOT.x, ROOT.y, 1.3))
    crown = hair.ray_cast(above,axis)[0].z - skin.ray_cast(above,axis)[0].z
    # Measure the surface facing the skull, including points between its
    # vertices. The inward turn at the cut joins this sheet to the exterior.
    contact = []
    whole_min = math.inf
    euclidean_min = math.inf
    for f in obj.data.polygons:
        uv = [obj.data.uv_layers.active.data[i].uv.y for i in f.loop_indices]
        is_contact = max(uv) < .013
        a,b,c = [obj.data.vertices[i].co for i in f.vertices]
        for j in range(17):
            for k in range(17-j):
                p = a + (b-a)*(j/16) + (c-a)*(k/16)
                q,n,_,d = skin.find_nearest(p)
                whole_min = min(whole_min,(p-q).dot(n))
                euclidean_min = min(euclidean_min,d)
                if is_contact:
                    contact.append(d)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
    boundary = sum(e.is_boundary for e in bm.edges)
    nonmanifold = sum(not e.is_manifold for e in bm.edges)
    components = len(bob.connected_faces(bm))
    bm.free()
    # Use the same eye islands and perspective-independent BVH method as the
    # reviewed bob, scanning the entire frame at the delivered resolution.
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
    bm.verts.index_update()
    eye_faces = []
    for g in bob.connected_faces(bm):
        z = [v.co.z for f in g for v in f.verts]
        if .67 < min(z) and max(z) < .80:
            eye_faces.extend(g)
    assert len(eye_faces) == 268
    eyes = BVHTree.FromPolygons([v.co.copy() for v in bm.verts], [[v.index for v in f.verts] for f in eye_faces])
    bm.free()
    eye_pixels = []
    for view in VIEWS[:3]:
        axis = Vector(view).normalized()
        q = (-axis).to_track_quat('-Z','Y')
        across, up = q @ Vector((1,0,0)), q @ Vector((0,1,0))
        kept = hidden = 0
        for y in range(PIXELS):
            row = CAMERA_TARGET + axis + up*((y+.5-PIXELS/2)*FRAMING/PIXELS)
            for x in range(PIXELS):
                p = row + across*((x+.5-PIXELS/2)*FRAMING/PIXELS)
                eye = eyes.ray_cast(p,-axis,2)[0]
                if eye is None or (skin.ray_cast(p,-axis,2)[0]-eye).dot(axis) > .00003:
                    continue
                kept += 1
                h = hair.ray_cast(p,-axis,2)[0]
                hidden += h is not None and (h-eye).dot(axis) > .00001
        eye_pixels.append([kept,hidden])
    data = dict(validator=validation, triangles=tri, bytes=GLB.stat().st_size, joints=len(joints),
                influences=int(active.sum(1).max()), max_neck=float(neck.max()), images=images,
                shell_components=components, boundary_edges=boundary, nonmanifold_edges=nonmanifold,
                crown=crown, upper_cap=cap, inner_surface=[len(contact),min(contact),max(contact)], full_surface_signed_min=whole_min, full_surface_clearance_min=euclidean_min,
                eye_pixels=eye_pixels, sha256=hashlib.sha256(GLB.read_bytes()).hexdigest())
    print('EXPORTED ASSET AUDIT',json.dumps(data),flush=True)
    assert boundary == 0 and nonmanifold == 0 and components == 1
    assert all(seen > 0 and hidden == 0 for seen,hidden in eye_pixels)
    assert .004 <= crown <= .012 and .004 <= cap[1] <= cap[2] <= .012
    assert .004 <= min(contact) <= max(contact) <= .012 and euclidean_min >= .004 and whole_min >= .0005
    # Check all integer frames as a supplement to the supplied sample sets.
    for m in obj.modifiers:
        if m.type == 'ARMATURE':
            m.object = arm
    obj.parent = arm
    bpy.ops.import_scene.gltf(filepath=str(MOTION))
    arm.animation_data_create()
    all_frames = {}
    for clip in ('rest','walk','run','wave','jump','idle','nod','dance'):
        a = None if clip=='rest' else bpy.data.actions[clip]
        arm.animation_data.action = a
        frames = [1]
        if a:
            arm.animation_data.action_slot = a.slots[0]
            frames = range(int(a.frame_range[0]), int(a.frame_range[1])+1)
        inside = pairs = 0
        minimum = math.inf
        for frame in frames:
            sc.frame_set(frame)
            dg = bpy.context.evaluated_depsgraph_get()
            be, he = body.evaluated_get(dg), obj.evaluated_get(dg)
            st, ht = bob.tree_for(be), bob.tree_for(he)
            pairs = max(pairs, len(st.overlap(ht)))
            count = 0
            for v in he.data.vertices:
                p = he.matrix_world @ v.co
                hit,n,_,_ = st.find_nearest(p)
                signed = (p-hit).dot(n)
                count += signed < 0
                minimum = min(minimum,signed)
            inside = max(inside,count)
        all_frames[clip] = [len(frames),inside,pairs,minimum]
        print('ALL FRAMES',clip,all_frames[clip], flush=True)
    data['all_frames'] = all_frames
    assert all(v==p==0 and d >= .0005 for _,v,p,d in all_frames.values())
    (WORK/'asset_audit.json').write_text(json.dumps(data,indent=2)+'\n')


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['build', 'sheet', 'underside', 'vertex', 'tri', 'audit']
    for stage in args:
        if stage in ('vertex', 'tri'):
            check(stage)
        else:
            {'build': build, 'sheet': sheet, 'underside': lambda: sheet(True), 'audit': audit}[stage]()
