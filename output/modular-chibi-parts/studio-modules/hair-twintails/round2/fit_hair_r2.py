"""Repair the fitted twin tails and test the exact GLB in background Blender.

Stages: build (includes both supplied motion gates), baseline, views, compare,
audit. The default runs every stage. All output and temporary files stay here.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
WORK = HERE / '.work'
WORK.mkdir(exist_ok=True)
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('twintails_v1', HERE.parent / 'fit_hair.py')
v1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v1)
bob = v1.bob
GLB = HERE / 'hair_twintails_v2.glb'
BLEND = HERE / 'hair_twintails_v2.blend'
VIEWS = ['front', 'three_quarter_left', 'three_quarter_right', 'left', 'back', 'right']
# Coordinates in the original 570 px panels, from the top left.
REGIONS = {
    'fringe': (1, (173, 130, 350, 254)),
    'tail_three_quarter': (1, (428, 157, 540, 312)),
    'tail_profile': (3, (263, 164, 401, 304)),
    'crown_to_nape': (4, (165, 119, 398, 412)),
    'temple': (5, (320, 201, 477, 395)),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def pixels(path):
    im = bpy.data.images.load(str(path), check_existing=False)
    im.colorspace_settings.name = 'Non-Color'
    w, h = im.size
    arr = np.empty(w*h*4, np.float32)
    im.pixels.foreach_get(arr)
    bpy.data.images.remove(im)
    return arr.reshape(h, w, 4)


def write_png(path, data):
    h, w = data.shape[:2]
    im = bpy.data.images.new(path.stem, w, h, alpha=data.shape[-1] == 4)
    im.colorspace_settings.name = 'Non-Color'
    if data.shape[-1] == 3:
        data = np.dstack((data, np.ones((h,w), 'f')))
    im.pixels.foreach_set(np.ascontiguousarray(data, dtype=np.float32).ravel())
    im.filepath_raw = str(path)
    im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)


def hair_mask(axis, tree, body, size):
    # Pixel-center visibility against the identical, opaque, unaltered master.
    rot = (-axis).to_track_quat('-Z', 'Y')
    across = rot @ Vector((1, 0, 0))
    up = rot @ Vector((0, 1, 0))
    pitch = v1.FRAMING / size
    first = v1.CAMERA_TARGET + axis * 2 - (across+up)*(.5*(size-1)*pitch)
    across *= pitch
    up *= pitch
    mask = np.zeros((size, size), bool)
    for row in range(size):
        origin = first + up*row
        for col in range(size):
            p = origin + across*col
            hit = tree.ray_cast(p, -axis, 3)
            if hit[0] is not None:
                block = body.ray_cast(p, -axis, hit[3])
                mask[row, col] = block[0] is None
    return mask


def capture(asset, tag):
    bpy.ops.wm.open_mainfile(filepath=str(v1.MASTER))
    bpy.ops.import_scene.gltf(filepath=str(asset))
    sc = bpy.context.scene
    bob.cpu_studio(sc)
    data = bpy.data.cameras.new('Orthographic fit')
    cam = bpy.data.objects.new(data.name, data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    data.type, data.ortho_scale = 'ORTHO', v1.FRAMING
    tree = bob.tree_for(sc.objects['Hair_Twintails'])
    body = bob.tree_for(sc.objects['Base_Body'])
    frames = []
    count_rows = []
    size = v1.PIXELS
    orig = pixels(v1.HERE / 'fit_views.png') if tag == 'v1' else None
    for i, direction in enumerate(v1.VIEWS):
        axis = Vector(direction).normalized()
        cam.location = v1.CAMERA_TARGET + 2*axis
        cam.rotation_euler = (v1.CAMERA_TARGET-cam.location).to_track_quat('-Z','Y').to_euler()
        sc.render.resolution_x = sc.render.resolution_y = size
        sc.render.use_border = False
        frame_path = WORK / f'{tag}_panel.png'
        sc.render.filepath = str(frame_path)
        bpy.ops.render.render(write_still=True)
        frame = pixels(frame_path)
        frames.append(frame)
        mask = hair_mask(axis, tree, body, size)
        rgb = frame[mask, :3].astype(np.float64)
        weights = np.array([.2126, .7152, .0722])
        linear = np.where(rgb <= .04045, rgb/12.92, ((rgb+.055)/1.055)**2.4)
        row = dict(view=VIEWS[i], hair_pixels=int(mask.sum()),
                   near_black_srgb=int((rgb @ weights < .12).sum()),
                   relative_luminance_lt_12pct=int((linear @ weights < .12).sum()))
        if orig is not None:
            y, x = (1-i//3)*size, (i%3)*size
            given = orig[y:y+size, x:x+size, :3][mask]
            row['supplied_sheet_near_black_srgb'] = int((given @ weights < .12).sum())
            row['supplied_sheet_relative_luminance_lt_12pct'] = int((np.where(
                given <= .04045, given/12.92, ((given+.055)/1.055)**2.4) @ weights < .12).sum())
            row['supplied_sheet_max_rgb_byte_delta'] = int(np.rint(255*np.abs(given-rgb).max()))
        count_rows.append(row)
        for name, (view, (left, top, right, bottom)) in REGIONS.items():
            if view != i:
                continue
            sc.render.resolution_x = sc.render.resolution_y = 3*size
            sc.render.use_border = sc.render.use_crop_to_border = True
            sc.render.border_min_x, sc.render.border_max_x = left/size, right/size
            sc.render.border_min_y, sc.render.border_max_y = 1-bottom/size, 1-top/size
            sc.render.filepath = str(WORK / f'{tag}_{name}.png')
            bpy.ops.render.render(write_still=True)
    sheet = np.vstack((np.hstack(frames[3:]), np.hstack(frames[:3])))
    if tag == 'v2':
        write_png(HERE / 'fit_views_v2.png', sheet)
    write_json(WORK / f'{tag}_counts.json', dict(asset=asset.name, sha256=digest(asset), views=count_rows))


def compare():
    close = HERE / 'closeups'
    close.mkdir(exist_ok=True)
    for name in REGIONS:
        before, after = [pixels(WORK / f'{tag}_{name}.png') for tag in ('v1','v2')]
        divider = np.full((len(after), 5, 4), .6, 'f')
        divider[:,:,3] = 1
        write_png(close / f'{name}.png', np.hstack((before, divider, after)))
    results = {tag: json.loads((WORK / f'{tag}_counts.json').read_text()) for tag in ('v1','v2')}
    assert results['v2']['sha256'] == digest(GLB)
    for tag in results:
        results[tag]['total'] = {key: sum(row[key] for row in results[tag]['views'])
                                 for key in ('hair_pixels', 'near_black_srgb', 'relative_luminance_lt_12pct')}
    results['image_sha256'] = {p.name:digest(p) for p in [HERE/'fit_views_v2.png', *sorted(close.glob('*.png'))]}
    for metric in ('near_black_srgb','relative_luminance_lt_12pct'):
        assert results['v2']['total'][metric] < results['v1']['total'][metric]
    write_json(HERE / 'visual_check.json', results)
    print('COUNTS', results['v1']['total'], results['v2']['total'], flush=True)



def step(lo, hi, t):
    s = np.clip((t-lo)/(hi-lo), 0, 1)
    return s*s*(3-2*s)


def unit(rows):
    return rows / np.maximum(1e-10, np.linalg.norm(rows, axis=-1, keepdims=True))


def lerp(a, b, t):
    return a + (b-a)*t[..., None]


def bilinear(field, a, b):
    a = np.clip(a, 0, field.shape[0]-1.001)
    b = np.clip(b, 0, field.shape[1]-1.001)
    i, j = a.astype(int), b.astype(int)
    return lerp(lerp(field[i,j], field[i+1,j], a-i),
                lerp(field[i,j+1], field[i+1,j+1], a-i), b-j)


class BackPatch:
    """Paired strips from the intact cap, indexed by angle around the skull."""
    center = .009
    tilt_min = -.84
    tilt_step = .004
    span_step = .003
    z0 = .807

    def __init__(self, obj, arrays, images):
        pos, normals, tangents, signs, uv = arrays
        ids = np.flatnonzero(uv[:,:,1].min(axis=1) > .03)
        tree = BVHTree.FromPolygons([v.co for v in obj.data.vertices],
                                   [obj.data.polygons[int(i)].vertices[:] for i in ids], all_triangles=True)
        self.fields = []
        for side in (-1, 1):
            # Radius, sRGB, world-space mapped normal, roughness and metallic.
            field = np.full((620, 23, 10), np.nan, 'f')
            for k in range(len(field)):
                a = self.tilt_min + k*self.tilt_step
                ray = Vector((0, math.cos(a), math.sin(a)))
                for j in range(field.shape[1]):
                    x = self.center + side*(.022 + j*self.span_step)
                    axis = Vector((x,0,self.z0))
                    pt, _, face, _ = tree.ray_cast(axis+ray*.50, -ray, .42)
                    if pt is None:
                        continue
                    f = ids[face]
                    edges = pos[f,1:] - pos[f,0]
                    cross = np.cross(edges[0], edges[1])
                    d = np.asarray(pt)-pos[f,0]
                    b = np.dot(np.cross(d, edges[1]), cross)/np.dot(cross,cross)
                    c = np.dot(np.cross(edges[0], d), cross)/np.dot(cross,cross)
                    w = np.array([1-b-c,b,c])
                    st = (w @ uv[f])*1024-.5
                    def tex(key):
                        return bilinear(images[key], st[1], st[0])
                    n = unit(w @ normals[f])
                    t = w @ tangents[f]
                    t = unit(t-np.dot(t,n)*n)
                    bt = np.cross(n,t)*np.sign((w @ signs[f])[0])
                    nm = tex('normal')*2-1
                    field[k,j] = np.r_[(pt-axis).dot(ray), tex('basecolor'),
                                         unit(t*nm[0]+bt*nm[1]+n*nm[2]), tex('rm')]
            for j in range(field.shape[1]):
                good = np.where(np.isfinite(field[:,j,0]))[0]
                for k in range(field.shape[2]):
                    field[:,j,k] = np.interp(np.arange(len(field)), good, field[good,j,k])
            self.fields.append(field)

    def weight(self, pos):
        x, y, z = np.moveaxis(pos,-1,0)
        return (1-step(.015,.057,abs(x-self.center))) * step(-.022,.027,y) * step(.668,.690,z)

    def donor(self, pos):
        x, y, z = np.moveaxis(pos,-1,0)
        dx = x-self.center
        span = np.sqrt(dx*dx + .031**2)
        tilt = np.arctan2(z-self.z0,y)
        # Extend the bands across the part in their original direction.
        tilt += .25*(span-abs(dx))
        a = (tilt-self.tilt_min)/self.tilt_step
        b = (span-.022)/self.span_step
        left, right = [bilinear(field,a,b) for field in self.fields]
        return lerp(left,right,step(-.026,.026,dx))


def triangle_texels(st):
    tri = st*1024-.5
    lo = np.maximum(0, np.ceil(tri.min(0))).astype(int)
    hi = np.minimum(1023, np.floor(tri.max(0))).astype(int)
    yy,xx = np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
    basis = (tri[1:]-tri[0]).T
    if abs(np.linalg.det(basis)) < 1e-9:
        return yy[:0].ravel(), xx[:0].ravel(), np.empty((0,3))
    ab = (np.stack((xx,yy),axis=-1)-tri[0]) @ np.linalg.inv(basis).T
    w = np.dstack((1-ab.sum(-1),ab))
    inside = w.min(-1) >= -1e-7
    return yy[inside], xx[inside], w[inside]


def split_charts(obj, arrays):
    # Flatten folded and severely compressed charts into empty atlas space.
    # Keeping a separate source UV correspondence lets the rebake transform
    # each face from its original tangent frame to its new one.
    occupied = np.zeros((1024,1024), bool)
    owner = np.full((1024,1024), -1, int)
    bad = set()
    overlap = 0
    for i, st in enumerate(arrays[4]):
        if st[:,1].min() < .03:
            continue
        yy,xx,w = triangle_texels(st)
        inside = w.min(-1) > 1.e-6
        y,x = yy[inside],xx[inside]
        hits = owner[y,x]
        clash = hits >= 0
        if clash.any():
            bad.add(i)
            bad.update(hits[clash].tolist())
            overlap += int(clash.sum())
        owner[y,x] = i
        occupied[yy,xx] = True
        verts = arrays[0][i]
        cx,cy,cz = verts.mean(axis=0)
        if abs(cx)>.225 and .80<cz<.95 and -.012<cy<.14:
            area = np.linalg.norm(np.cross(verts[1]-verts[0],verts[2]-verts[0]))*.5
            if len(yy) < .30*900**2*area:
                bad.add(i)
    occupied[:42] = True
    specs = []
    for i in sorted(bad):
        a,b,c = arrays[0][i]
        u = unit(b-a)
        n = unit(np.cross(u,c-a))
        v = np.cross(n,u)
        local = (arrays[0][i]-a) @ np.stack((u,v)).T * 920
        local -= local.min(axis=0)
        dims = np.ceil(local.max(axis=0)).astype(int)+1
        specs.append((i,local,dims))
    for i, local, dims in sorted(specs,key=lambda spec:-np.prod(spec[2])):
        integral = np.pad(occupied,((1,0),(1,0))).cumsum(0,dtype='i4').cumsum(1,dtype='i4')
        slot = None
        for scale in (1.,.85,.70,.56,.45,.35):
            pad=7
            for rotated in (False,True):
                chart = (local[:,::-1] if rotated else local)*scale
                w,h=np.ceil(chart.max(0)).astype(int)+1+2*pad
                free=(integral[h:,w:]-integral[:-h,w:]-integral[h:,:-w]+integral[:-h,:-w])==0
                spots=np.flatnonzero(free)
                if len(spots):
                    y,x=np.unravel_index(spots[0],free.shape)
                    slot=(y,x,w,h,chart)
                    break
            if slot is not None:
                break
        if slot is None:
            raise ValueError(f'No padded chart slot for triangle {i}')
        y,x,w,h,local=slot
        occupied[y:y+h,x:x+w] = True
        loops = obj.data.polygons[i].loop_indices
        for k, st in zip(loops,(local+[x+pad+.5,y+pad+.5])/1024):
            obj.data.uv_layers.active.data[k].uv = st
    return dict(overlapping_exterior_texels_before=overlap,relocated_triangles=len(specs))


def atlas_surface(arrays):
    pos, _, _, _, uv = arrays
    face = np.full((1024,1024), -1, int)
    bary = np.zeros((1024,1024,3),'f')
    for i, st in enumerate(uv):
        if st[:,1].min() < .03:
            continue
        y,x,w = triangle_texels(st)
        assert not np.any((face[y,x]>=0) & (w.min(axis=1)>1.e-5) &
                          (bary[y,x].min(axis=1)>1.e-5)), 'overlapping exterior chart interiors'
        face[y,x], bary[y,x] = i, w
    used = face >= 0
    faces, w = face[used], bary[used]
    def interp(data):
        return np.einsum('ij,ijk->ik', w, data[faces])
    n = unit(interp(arrays[1]))
    t = interp(arrays[2])
    t = unit(t - n*(t*n).sum(axis=1,keepdims=True))
    bt = np.cross(n,t)*np.sign(interp(arrays[3]))
    return used, interp(pos), n, t, bt, interp


def local_color(pos, color, pitch=.0038):
    # Estimate a continuous local strand colour across chart boundaries. Reject
    # dark occlusion samples when recovering the albedo of an exposed face.
    grid = (pos-pos.min(0))/pitch+2
    cells = np.floor(grid).astype(int)
    shape = cells.max(0)+4
    weight = step(.18,.49,color[:,0])**2 + .002
    vol = np.zeros((*shape,4),'f')
    np.add.at(vol, tuple(cells.T), np.column_stack((color*weight[:,None], weight)))
    for _ in range(3):
        for axis in range(3):
            vol = .25*(np.roll(vol,1,axis)+np.roll(vol,-1,axis))+.5*vol
    estimate = np.zeros((len(pos),4),'f')
    grid -= .5
    cells = np.floor(grid).astype(int)
    frac = grid-cells
    for offset in np.ndindex(2,2,2):
        at = cells+offset
        w = np.prod(np.where(np.array(offset),frac,1-frac),axis=1)
        estimate += w[:,None] * vol[tuple(at.T)]
    return estimate[:,:3]/np.maximum(1e-10,estimate[:,3:])


def clean_maps(obj, arrays, original_arrays, images, patch):
    used, pos, n, t, bt, interp = atlas_surface(arrays)
    st = interp(original_arrays[4])*1024-.5
    source_t = interp(original_arrays[2])
    source_t = unit(source_t-n*(source_t*n).sum(1,keepdims=True))
    source_bt = np.cross(n,source_t)*np.sign(interp(original_arrays[3]))
    original = bilinear(images['basecolor'],st[:,1],st[:,0])
    color = original.copy()
    rm = bilinear(images['rm'],st[:,1],st[:,0])
    tangent = bilinear(images['normal'],st[:,1],st[:,0])*2-1
    normal = unit(source_t*tangent[:,0:1]+source_bt*tangent[:,1:2]+n*tangent[:,2:3])
    x,y,z = pos.T
    # The defects follow the outside of the tail lobes and the exposed fringe.
    # Average clean neighbours in object space. Use the disparity to avoid
    # smearing the intact painted gloss streaks.
    halo = local_color(pos, color)
    tail = step(.205,.251,abs(x))*(1-step(.135,.17,abs(y-.069)))
    fringe = step(.050,.084,abs(x))*(1-step(.162,.195,abs(x))) * step(.105,.145,-y)*step(.845,.895,z)
    disparity = halo[:,0]-color[:,0]
    correction = np.maximum(tail,fringe)*step(.035,.135,disparity)
    color = lerp(color, halo, correction)
    normal = unit(lerp(normal,n,correction*.84))
    rm[:,1] += correction*(.63-rm[:,1])
    rm[:,2] *= 1-correction
    # On the two genuinely pinched lobes the old bake describes opposite
    # walls of a crease. Replace the high-frequency signal over its whole
    # width, including originally light pixels between the dark flecks.
    wide = local_color(pos,original,pitch=.010)
    tail_patch = (step(.225,.256,abs(x))*(1-step(.023,.053,abs(y-.074))) *
                  step(.79,.843,z)*(1-step(.905,.961,z)))
    fringe_patch = ((1-step(.021,.044,abs(abs(x)-.137))) * (1-step(.018,.042,abs(z-.933))) *
                    step(.115,.152,-y))
    nape = step(.035,.093,y)*(1-step(.134,.175,abs(x)))*(1-step(.709,.746,z))
    temple = (step(.085,.127,abs(x))*(1-step(.205,.225,abs(x))) * step(.055,.085,-y) *
              (1-step(.80,.841,z)))
    # A continuous, shallow channel follows the flow of the outer lobe.
    # Its broad flanks carry the highlight across the repaired wall.
    cross = (y - (.074-.16*(z-.875)))/.013
    groove = np.exp(-.5*cross**2)
    flank = .095*np.exp(-.5*((cross+1.55)/.85)**2)+.045*np.exp(-.5*((cross-1.65)/1.0)**2)
    wide *= (1+tail_patch*(flank-.205*groove))[:,None]
    repaint = np.maximum.reduce([tail_patch,fringe_patch,nape,temple])
    color = lerp(color,wide,repaint)
    flow_normal = n.copy()
    flow_normal[:,1] -= .33*tail_patch*cross*groove
    flow_normal[:,2] -= .0528*tail_patch*cross*groove
    normal = unit(lerp(normal,unit(flow_normal),repaint))
    rm[:,1] += repaint*(.64-rm[:,1])
    rm[:,2] *= 1-repaint
    # Recover the diffuse brown beneath baked occlusion. Outer gloss and
    # the violet bands retain their authored colours.
    brown = 1-step(.015,.10,color[:,2]-color[:,1])
    shadows = (1-step(.19,.56,color[:,0]))*brown
    color += shadows[:,None]*np.array([.132,.096,.078])
    # Preserve flowing bands on both sides of the posterior centerline.
    w = patch.weight(pos)
    sel = w > 0
    donor = patch.donor(pos[sel])
    donor_col = donor[:,1:4].copy()
    donor_col += (1-step(.19,.56,donor_col[:,0]))[:,None]*np.array([.132,.096,.078])
    color[sel] = lerp(color[sel],donor_col,w[sel])
    normal[sel] = unit(lerp(normal[sel],donor[:,4:7],w[sel]))
    rm[sel] = lerp(rm[sel],donor[:,7:],w[sel])
    # The lowest course turns underneath the head, outside the donor strips.
    # Let the refaired surface normal carry the diffuse roll at the hem.
    normal = unit(lerp(normal,n,nape))
    # Hair is dielectric. Reduce the source's metallic contamination except
    # on the intentional violet ties, where the authored response is kept.
    rm[:,2] *= 1-.9*brown
    local = np.column_stack(((normal*t).sum(1),(normal*bt).sum(1),(normal*n).sum(1)))
    local[:,2] = np.maximum(.25,local[:,2])
    maps = {'basecolor':color,'normal':.5+.5*unit(local),'rm':rm}
    # Pad freshly repaired chart boundaries with the nearest growing front.
    # Preserve the dedicated lining strip. No roll-around across atlas edges.
    for key, repaired in maps.items():
        images[key][used] = repaired
    filled = used.copy()
    for _ in range(24):
        original_mask = filled.copy()
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
            src = (slice(max(0,-dy),min(1024,1024-dy)),slice(max(0,-dx),min(1024,1024-dx)))
            dst = (slice(max(0,dy),min(1024,1024+dy)),slice(max(0,dx),min(1024,1024+dx)))
            extend = original_mask[src] & ~filled[dst]
            for atlas in images.values():
                atlas[dst][extend] = atlas[src][extend]
            filled[dst] |= extend
    for key, atlas in images.items():
        swatch = {'basecolor':(.35,.18,.132), 'rm':(1,.62,0), 'normal':(.5,.5,1)}[key]
        atlas[~filled] = swatch
        atlas[:27] = swatch
        path = WORK / f'Twintails_R2_{key}.png'
        write_png(path, np.clip(atlas,0,1))
        im = bpy.data.images.load(str(path),check_existing=False)
        im.colorspace_settings.name = 'sRGB' if key=='basecolor' else 'Non-Color'
        im.pack()
        im.filepath = '//'+path.name
        node = next(node for node in obj.active_material.node_tree.nodes if node.type=='TEX_IMAGE' and
                    node.image.name == 'Twintails_'+key)
        old = node.image
        node.image = im
        bpy.data.images.remove(old)
    return int((correction>.5).sum())


def repair_shape(obj, patch):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uv = bm.loops.layers.uv.active
    def exterior(f):
        return min(l[uv].uv.y for l in f.loops)>.03
    def rim_edges():
        return [e for e in bm.edges if any(exterior(f) for f in e.link_faces)
                and not all(exterior(f) for f in e.link_faces)]
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    assert len(bob.connected_faces(bm)) == 1 and all(e.is_manifold for e in bm.edges)
    ext = {v for f in bm.faces if exterior(f) for v in f.verts}
    for v in ext:
        p = np.array(v.co)
        w = patch.weight(p)
        if w:
            target = patch.donor(p)[0]
            radius = np.linalg.norm(p[1:]-[0,patch.z0])
            # Neighbour strips are off axis. Restore the slight vault of
            # the cap and smoothly bridge the original recessed fold.
            change = np.clip(target+.0025-radius, -.008, .014)
            v.co.y += p[1]/radius*w*change
            v.co.z += (p[2]-patch.z0)/radius*w*change
    original_tree = bob.tree_for(obj)
    # Open out a pinched crease in the outward surface of each tail. Move
    # the connected walls together toward the envelope of adjacent lobes.
    for _ in range(12):
        move = {}
        for v in ext:
            x,y,z = v.co
            w = step(.239,.267,abs(x))*(1-step(.021,.048,abs(y-.074))) * step(.800,.843,z)*(1-step(.905,.952,z))
            if w:
                near = [e.other_vert(v).co for e in v.link_edges]
                target = sum(near,Vector())/len(near)
                move[v] = v.co.lerp(target,float(.49*w))
        for v,p in move.items():
            v.co = p
    # Restore the convex outside of each lobe after redistributing its
    # pinched vertices. Sample the intact flanks on either side of the groove.
    for v in ext:
        x,y,z=v.co
        side=math.copysign(1,x)
        center=.074-.16*(z-.875)
        w=step(.237,.266,abs(x))*(1-step(.020,.048,abs(y-center)))*step(.802,.846,z)*(1-step(.904,.947,z))
        if w:
            reach=[]
            for dy in (-.021,-.016,-.010,.010,.016,.021):
                for dz in (-.006,0,.006):
                    origin=Vector((side*.41,y+dy,z+dz))
                    h=original_tree.ray_cast(origin,Vector((-side,0,0)),.20)[0]
                    if h is not None:
                        reach.append(abs(h.x))
            if reach:
                v.co.x+=side*float(w)*(np.percentile(reach,72)-abs(x))
    # Subdivide only exterior-to-lining rim edges. Roll this course into a
    # smooth lower arc, preserving the thin cheek-lock ends and ear clearance.
    eligible = [e for e in rim_edges() if sum(v.co.y for v in e.verts)>-2*.066
                and sum(v.co.z for v in e.verts)<2*.835 and e.calc_length()>.008]
    eligible.sort(key=lambda e:e.calc_length(),reverse=True)
    edges = eligible[:38]
    bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=False)
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
    border = rim_edges()
    paths = {}
    for e in border:
        a,b=e.verts
        paths.setdefault(a,[]).append(b)
        paths.setdefault(b,[]).append(a)
    for _ in range(9):
        move = {}
        for v,adj in paths.items():
            if len(adj)!=2:
                continue
            x,y,z = v.co
            w = step(-.081,-.035,y)*(1-step(.808,.854,z))
            if not w:
                continue
            a,b = (other.co for other in adj)
            t = (v.co-a).length / max(1e-9,(v.co-a).length+(b-v.co).length)
            delta = a.lerp(b,t)-v.co
            move[v] = v.co + Vector((delta.x*.28,delta.y*.37,delta.z*.82))*float(w)
        for v,p in move.items():
            v.co = p
    for v in paths:
        x,y,z=v.co
        if y>.068 and abs(x)<.162:
            w = float((1-step(.10,.162,abs(x)))*step(.068,.10,y))
            # A gentle nape dip continues through center instead of rising
            # into the V-shaped notch from the mirrored extraction.
            target = .685 + .003*(x/.1)**2
            v.co.z += w*(target-z)
    # The inherited lining pokes out through the compressed center of the
    # posterior hem. Re-form the external course over the head at fixed
    # height, leaving room for the complete return to the concave lining.
    skin = bob.tree_for(bpy.context.scene.objects['Base_Body'],True)
    ext = {v for f in bm.faces if exterior(f) for v in f.verts}
    for v in ext:
        x,y,z=v.co
        w=step(.042,.085,y)*(1-step(.134,.170,abs(x)))*(1-step(.720,.764,z))
        if w:
            hit=skin.ray_cast(Vector((x,.40,z)),Vector((0,-1,0)),.45)[0]
            if hit is not None:
                outer_y=hit.y+.035
                v.co.y+=float(w)*max(0.,outer_y-y)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for f in bm.faces:
        f.smooth = True
    assert all(e.is_manifold and e.is_contiguous for e in bm.edges)
    assert bm.calc_volume(signed=True)>0 and len(bm.faces)<=3000
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return len(edges)


def support_rim(obj):
    # A triangulated return can approach the curved ear between its vertices.
    # Move only triangles whose sampled physical clearance was reduced.
    skin = bob.tree_for(bpy.context.scene.objects['Base_Body'],True)
    mesh = obj.data
    for _ in range(5):
        offsets = {}
        for face in mesh.polygons:
            a,b,c=[mesh.vertices[i].co for i in face.vertices]
            for j in range(17):
                for k in range(17-j):
                    p=a+(b-a)*(j/16)+(c-a)*(k/16)
                    pt,n,_,d=skin.find_nearest(p)
                    if d<.00408:
                        amount=.00452-d
                        for idx in face.vertices:
                            if idx not in offsets or amount>offsets[idx][0]:
                                offsets[idx]=amount,(p-pt).normalized() if (p-pt).dot(n)>0 else n
        if not offsets:
            break
        for idx,(amount,direction) in offsets.items():
            mesh.vertices[idx].co+=amount*direction
    mesh.update()


def separate_temple_walls(obj):
    # At the cap-to-cheek turn, an inside-facing wall can cross the outside
    # by a fraction of a millimetre. Recover positive thickness on the
    # outer wall while preserving vertices shared by the returning edge.
    bm=bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    count=0
    for _ in range(6):
        tree=BVHTree.FromBMesh(bm)
        shifts={}
        for side in (-1,1):
            ray=Vector((-side,0,0))
            pairs=[]
            for z in np.arange(.766,.836,.0018):
                for y in np.arange(-.095,-.046,.0018):
                    hit,n,back,_=tree.ray_cast(Vector((side*.32,y,z)),ray,.19)
                    if hit is None or side*n.x>-.30:
                        continue
                    h,front_n,front,_=tree.ray_cast(hit+ray*.000003,ray,.011)
                    if h is not None and side*front_n.x>.55:
                        pairs.append((bm.faces[back],bm.faces[front],abs(hit.x-h.x)))
            shared={v for back,_,_ in pairs for v in back.verts}
            for _,front,gap in pairs:
                for v in front.verts:
                    if v not in shared:
                        amount=min(.004,max(.0018,2*(gap+.001)))
                        if v not in shifts or amount>abs(shifts[v]):
                            shifts[v]=side*amount
        if not shifts:
            break
        for v,delta in shifts.items():
            v.co.x+=delta
        count+=len(shifts)
        bm.normal_update()
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return count


def checker(kind):
    @bpy.app.handlers.persistent
    def cpu(scene,*_):
        if scene.camera and scene.camera.name=='c' and scene.render.engine=='BLENDER_WORKBENCH':
            bob.cpu_studio(scene)
    script = HERE / ('motion_check.py' if kind=='vertex' else 'motion_check_tri.py')
    out = HERE / 'checks' / kind
    out.mkdir(parents=True,exist_ok=True)
    args = sys.argv
    bpy.app.handlers.frame_change_pre.append(cpu)
    try:
        sys.argv = [str(script),'--',str(v1.MASTER),str(v1.MOTION),str(GLB),str(out)]
        runpy.run_path(str(script),run_name='__main__')
    finally:
        sys.argv = args
        bpy.app.handlers.frame_change_pre.remove(cpu)
    data = json.loads((out/'motion_check.json').read_text())
    assert set(data)=={'rest','walk','run','wave','jump','idle','nod','dance'}
    assert all(count==0 and dist>=.0005 for count,dist in data.values()),data


def build():
    bpy.ops.wm.open_mainfile(filepath=str(v1.BLEND))
    sc=bpy.context.scene
    obj,arm=sc.objects['Hair_Twintails'],sc.objects['Armature']
    arrays = v1.mesh_arrays(obj.data)
    images = {}
    for node in obj.active_material.node_tree.nodes:
        if node.type!='TEX_IMAGE':
            continue
        im = node.image
        key = im.name.split('_')[-1]
        im.colorspace_settings.name='Non-Color'
        arr=np.empty(1024*1024*4,'f')
        im.pixels.foreach_get(arr)
        images[key]=arr.reshape(1024,1024,4)[:,:,:3].copy()
    patch=BackPatch(obj,arrays,images)
    extra=repair_shape(obj,patch)
    support_rim(obj)
    temple_shifts=separate_temple_walls(obj)
    src_frames=v1.mesh_arrays(obj.data)
    chart_stats=split_charts(obj,src_frames)
    treated=clean_maps(obj,v1.mesh_arrays(obj.data),src_frames,images,patch)
    print('UV REPAIR',chart_stats,flush=True)
    # The analytic weight field also covers every inserted rim vertex.
    heads,necks=obj.vertex_groups[bob.HEAD],obj.vertex_groups[bob.NECK]
    for v in obj.data.vertices:
        x,y,z=v.co
        w=.105*bob.smooth(-.008,.095,y)*(1-bob.smooth(.652,.760,z))
        if w<.0001:
            w=0.
        heads.add([v.index],1-w,'REPLACE')
        necks.add([v.index],w,'REPLACE')
    bpy.ops.object.select_all(action='DESELECT')
    arm.hide_set(False)
    for ob in (obj,arm):
        ob.select_set(True)
    bpy.context.view_layer.objects.active=obj
    # glTF skins are world-space nodes. Retain the armature modifier during
    # export and restore the editable scene hierarchy afterwards.
    obj.parent=None
    bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,
                              export_tangents=True,export_animations=False,export_all_influences=False,
                              export_def_bones=False)
    obj.parent=arm
    arm.hide_set(True)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print('REPAIR',treated,'recovered exterior texels;',extra,'new rim points;',len(obj.data.polygons),'triangles',flush=True)
    checker('vertex')
    checker('triangle')
    write_json(HERE/'checks'/'build.json',dict(sha256=digest(GLB), **chart_stats,
               overlapping_exterior_texels_after=0, new_rim_vertices=extra, temple_wall_vertex_adjustments=temple_shifts,
               checker_sha256={name:digest(HERE/name) for name in ('motion_check.py','motion_check_tri.py')}))


def audit():
    # Reuse the original exact-export skeleton, topology, fit, eye visibility
    # and all-frame motion audit, changing only input/output paths.
    v1.WORK=WORK
    v1.GLB=GLB
    v1.audit()
    out=HERE/'checks'
    (WORK/'asset_audit.json').replace(out/'asset_audit.json')
    js = """const fs = require('fs'), v = require('gltf-validator');
    v.validateBytes(new Uint8Array(fs.readFileSync(process.argv[1]))).then(
      report => console.log(JSON.stringify({version:v.version(), ...report})),
      err => {console.error(err); process.exitCode=1;});"""
    report=json.loads(subprocess.check_output(['node','-e',js,str(GLB)],cwd=bob.REPO,text=True))
    report['sha256']=digest(GLB)
    assert report['issues']['numErrors']==report['issues']['numWarnings']==0
    write_json(out/'gltf_validator.json',report)
    # Body collision and hair-layer self-contact are separate measurements.
    # Keep a matched topology comparison for the inherited interleaved locks.
    contact={}
    for path in (v1.HERE/'hair_twintails_v1.glb',GLB):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(path))
        mesh=next(o.data for o in bpy.context.scene.objects if o.type=='MESH')
        bm=bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
        bm.faces.ensure_lookup_table()
        tree=BVHTree.FromBMesh(bm)
        pairs=sum(i<j and not set(bm.faces[i].verts).intersection(bm.faces[j].verts)
                  for i,j in tree.overlap(tree))
        contact[path.name]=dict(sha256=digest(path), nonadjacent_hair_triangle_pairs=pairs,
                  boundary_edges=sum(e.is_boundary for e in bm.edges),
                  inconsistent_winding_edges=sum(not e.is_contiguous for e in bm.edges))
        bm.free()
    write_json(out/'hair_shell.json',contact)


if __name__ == '__main__':
    for stage in (sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else
                  ['build', 'baseline', 'views', 'compare', 'audit']):
        if stage == 'baseline':
            capture(v1.GLB, 'v1')
        elif stage == 'views':
            capture(GLB, 'v2')
        else:
            globals()[stage]()
