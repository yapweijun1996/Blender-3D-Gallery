"""Refine an exported offset bake using clearance and layer witnesses."""
import argparse
from collections import defaultdict
import sys
from pathlib import Path

import bmesh

from asset_io import GLB, HERE, MALE, MOTION, bpy, json, np, transcode, write_json
from body_audit import load_body_motion, set_frame, use_action
from fit_module import (FLOOR, envelope, influences, motion_samples, objective,
                        read_module, scan, skin, store_geometry)
from fitting_geometry import arrays, barycentric, laplacian, limit_weights, region, tree, weights, weld_graph
from gate_module import bounded_tree

PROBES = np.array([[1/3, 1/3, 1/3], [.5,.5,0], [.5,0,.5], [0,.5,.5]], dtype=np.float32)
SOLE_M = -.0065


def floor_profile(points):
    result = points.copy()
    for side in (1, -1):
        mask = np.sign(points[:,0]) == side
        low = points[mask,2].min()
        z = points[mask,2]
        # Compress the lowest sole rubber into a common floor without lifting
        # the toe box or the heel counter.
        gain = np.clip(1-(z-low)/.024,0,1)**2
        result[mask,2] = z+(SOLE_M-low)*gain
    return result


def export(garment, arm, scene, p, w, names, path):
    use_action(arm, None)
    set_frame(scene, 0)
    store_geometry(garment, p, w, names)
    world = garment.matrix_world.copy()
    garment.parent = None
    garment.matrix_world = world
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    garment.select_set(True)
    bpy.context.view_layer.objects.active = garment
    stage = HERE / '.runtime' / path.name
    bpy.ops.export_scene.gltf(filepath=str(stage), export_format='GLB', use_selection=True,
                              export_animations=False, export_skins=True, export_yup=True,
                              export_tangents=bool(garment.data.uv_layers))
    if stage.stat().st_size <= 1.5*1024**2:
        stage.replace(path)
    else:
        for cap in (512,384,320,256):
            transcode(GLB(stage),path,1024,cap)
            if path.stat().st_size <= 1.5*1024**2:
                break


class Layers:
    def __init__(self, arm, names, shoe, mode, p, faces, graph, samples):
        self.faces, self.graph, self.samples = faces, graph, samples
        self.polish = shoe and mode in ('polish','radial-polish','conform')
        self.separate_sides = shoe
        self.side = p[faces,0].mean(axis=1) > 0
        self.separation = np.zeros_like(p)
        self.separation[:,0] = np.sign(p[:,0])
        garment_keys = ['male-jeans.glb'] if shoe else ['male-tshirt.glb']
        self.references = []
        for key in garment_keys:
            obj = read_module(MALE/key,arm)
            fit, f = arrays(obj)
            self.references.append((fit,f,*influences(weights(obj,names))))
        # The cuff wraps the shipped jeans. The waistband sits under the top.
        x = np.where(p[:,0]>0,1,-1)
        ankles = [arm.data.bones['mixamorig:'+side+'Foot'].head_local
                  for side in ('Left','Right')]
        centers = np.where((x>0)[:,None], np.asarray(ankles[0]), np.asarray(ankles[1]))
        if not shoe:
            centers = np.broadcast_to(np.asarray(arm.data.bones['mixamorig:Hips'].head_local), p.shape)
        direction = (p-centers).copy()
        direction[:,2] = 0
        direction /= np.linalg.norm(direction,axis=1,keepdims=True).clip(.002,None)
        if mode in ('lower','polish'):
            direction[:] = [0,0,-1]
        elif not shoe and mode != 'outside':
            direction *= -1
        self.direction = direction
        self.faces_list = faces.tolist()
        # Precompute the unchanged layers once for this coarse pose bank.
        self.posed = [[(skin(s,ids,packed,fit)[0],f,fit[f,0].mean(axis=1)>0)
                       for fit,f,ids,packed in self.references]
                      for s in samples]

    def scan(self, p, w, collect=False):
        ids, packed = influences(w)
        need = np.zeros((2,len(p)),dtype=np.float32)
        hits = defaultdict(int)
        for sample, layers in zip(self.samples,self.posed):
            fit, basis = skin(sample,ids,packed,p)
            garment = tree(fit,self.faces_list)
            for layer, f, side in layers:
                surface, face_ids = bounded_tree(layer, f, fit, .050 if collect else 0)
                if surface is None:
                    continue
                pairs = surface.overlap(garment)
                if not pairs:
                    continue
                hits[sample.clip] += len(pairs)
                if not collect:
                    continue
                indices = np.asarray(pairs)
                separated = side[face_ids[indices[:,0]]] != self.side[indices[:,1]] if self.separate_sides else np.zeros(len(indices),dtype=bool)
                for k, (mask, direction) in enumerate(((~separated,self.direction),(separated,self.separation))):
                    if not mask.any():
                        continue
                    corners = self.faces[np.unique(indices[mask,1])]
                    points = (PROBES@fit[corners]).reshape(-1,3)
                    posed_axes = np.einsum('vij,vj->vi',basis,direction)[corners]
                    rays = (PROBES@posed_axes).reshape(-1,3)
                    rays /= np.linalg.norm(rays,axis=1,keepdims=True).clip(.25,None)
                    distances = self.layer_depth(surface,points,rays)
                    amount = distances.reshape(-1,len(PROBES)).max(axis=1)
                    np.maximum.at(need[k],corners.ravel(),np.repeat(amount,3))
        return dict(hits), need

    def layer_depth(self, surface, points, rays):
        distances = []
        for point, axis in zip(points,rays):
            # The first hit from the far side gives the full layer thickness
            # along the movement axis.
            for limit in (.028,.046):
                hit,_,_,dist = surface.ray_cast(point+axis*limit,-axis,limit+.003)
                if hit is not None:
                    distances.append(max(.0009,limit-dist+.0012))
                    break
            else:
                distances.append(.0014)
        return np.asarray(distances)

    def move(self, needs):
        inverse = self.graph[0]
        result = np.zeros_like(self.direction)
        for need,direction in zip(needs,(self.direction,self.separation)):
            if not need.any():
                continue
            shared = np.zeros(int(inverse.max())+1)
            np.maximum.at(shared,inverse,need)
            need = shared[inverse]
            for _ in range(2 if self.polish else 4):
                need = np.maximum(need,laplacian(need,self.graph)*(.67 if self.polish else .85))
            result += direction * np.minimum(need,.016)[:,None]
        return result


def select_samples(samples, report, polish=False):
    coarse = [samples[0]]
    for clip, row in report['clips'].items():
        if clip == 'rest':
            continue
        group = [s for s in samples if s.clip == clip]
        active_motion = clip in ('walk','run','dance','sit_down','sit_idle','stand_up','jump')
        stride = max(1,len(group)//(20 if active_motion else 4))
        selected = set(group[::stride]+[group[-1]])
        rows = row['frames']
        bad_body = [r for r in rows if r['inside'] or r['pairs'] or r['min_signed_m'] < FLOOR]
        bad_layers = [r for r in rows if any(r['layer_pairs'].values())]
        witnesses = []
        for candidates, key in (
                (bad_body, lambda r: -r['min_signed_m']),
                (bad_body, lambda r: r['pairs']),
                (bad_layers, lambda r: sum(r['layer_pairs'].values()))):
            picks = []
            for witness in sorted(candidates,key=key,reverse=True):
                f = witness['frame']
                if all(abs(f-n)>.9 for n in picks):
                    picks.append(f)
                if len(picks)>=6:
                    break
            witnesses.extend(picks)
        if len(bad_body)<=28:
            witnesses.extend(r['frame'] for r in bad_body)
        if len(bad_layers)<=28:
            witnesses.extend(r['frame'] for r in bad_layers)
        selected.update(min(group,key=lambda s:abs(s.frame-f)) for f in witnesses)
        if polish:
            if clip in ('walk','run','jump') and (bad_body or bad_layers):
                selected.update(group)
            else:
                selected.update(s for s in group if any(abs(s.frame-f)<.48 for f in witnesses))
        coarse.extend(s for s in group if s in selected)
    return coarse


def split_long_edges(obj, limit=6000):
    # Give long bridging faces enough corners for local clearance moves.
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    bmesh.ops.triangulate(mesh,faces=list(mesh.faces))
    spare = limit-len(mesh.faces)
    cuts = []
    for edge in sorted(mesh.edges,key=lambda e:e.calc_length(),reverse=True):
        if edge.calc_length()<.015 or spare<len(edge.link_faces):
            break
        cuts.append(edge)
        spare -= len(edge.link_faces)
    if cuts:
        bmesh.ops.subdivide_edges(mesh,edges=cuts,cuts=1,use_grid_fill=True)
        bmesh.ops.triangulate(mesh,faces=[f for f in mesh.faces if len(f.verts)>3])
        assert len(mesh.faces)<=limit
        mesh.to_mesh(obj.data)
        obj.data.update()
    mesh.free()
    print('SPLIT LONG EDGES',len(cuts),flush=True)


def conform_weights(guide,names,p,w,graph,shoe,shorts):
    reference, faces = arrays(guide)
    guide_weights = weights(guide,names)
    bvh = tree(reference,faces.tolist())
    result = np.empty_like(w)
    distances = np.empty(len(p),dtype=np.float32)
    for i, point in enumerate(p):
        loc,_,tri,dist = bvh.find_nearest(point)
        result[i] = barycentric(loc,reference[faces[tri]]) @ guide_weights[faces[tri]]
        distances[i] = dist
    if shoe:
        # Follow the shin/ankle blend on the jeans only around the opening.
        amount = .65*np.clip((p[:,2]-.065)/.065,0,1)
    elif shorts:
        # The shorts have separate legs. Move with the nearest corresponding
        # male surface around the thigh, seat and inseam.
        same_side = np.sum(result*w,axis=1)
        amount = .56*np.clip((.047-distances)/.032,0,1)*np.clip(same_side*3,0,1)
    else:
        # Keep waist motion on the pelvis while letting the lower panels
        # follow their original legs.
        hip = names.index('mixamorig:Hips')
        result[:] = 0
        result[:,hip] = 1
        amount = .62*np.clip((p[:,2]-.34)/.067,0,1)
    blended = w+(result-w)*amount[:,None]
    from fitting_geometry import welded
    return limit_weights(welded(blended,graph))


def refit(path, destination, gate_path, mode):
    scene, arm, body, _ = load_body_motion(MOTION)
    names = [bone.name for bone in arm.data.bones]
    shoe = path.name.startswith('shoes-')
    # Low collars and shorts can clear the adjoining hem with a vertical
    # recess while preserving their overall width.
    low_profile = ('bottom-shorts','shoes-sandals','shoes-slipons')
    if mode == 'radial' and path.stem.rsplit('-r',1)[0] in low_profile:
        mode = 'lower'
    garment = read_module(path,arm)
    report = json.loads(gate_path.read_text())
    rows = list(report['clips'].values())
    if mode == 'conform' and shoe:
        layer_peak = max(max(r['layer_peaks'].values()) for r in rows)
        if layer_peak <= 85 and max(r['peak_inside'] for r in rows) <= 10:
            mode = 'polish' if path.stem.rsplit('-r',1)[0] in low_profile else 'radial-polish'
    if mode == 'conform' and not shoe and any(r['peak_pairs'] for r in report['clips'].values()):
        split_long_edges(garment)
    start,faces = arrays(garment)
    original_w = weights(garment,names)
    w = original_w.copy()
    graph = weld_graph(start,faces)
    _, body_faces = arrays(body)
    face_groups = np.asarray(names)[weights(body,names)[body_faces].sum(axis=1).argmax(axis=1)]
    samples = list(motion_samples(body,names,GLB(MALE/'body_male.glb'),GLB(MOTION)))
    near_final = shoe and mode in ('conform','polish','radial-polish')
    coarse = select_samples(samples,report,near_final)
    # Body triangle IDs stay stable for normals and collision witnesses.
    # Full trees are cached only for a compact subset of representative poses.
    for sample in coarse:
        sample.cached_tree = tree(sample.body,sample.faces)
    zones = [region(names[group]) for group in w.argmax(axis=1)]
    layers = Layers(arm,names,shoe,mode,start,faces,graph,coarse)
    p = floor_profile(start) if shoe else start.copy()
    if mode == 'conform' and not shoe:
        mode = 'outside'
    if mode in ('conform','outside'):
        guide = read_module(MALE/'male-jeans.glb',arm) if shoe else body
        w = conform_weights(guide,names,start,w,graph,shoe,path.name.startswith('bottom-shorts'))
    origin = p.copy()
    history = []
    best = None
    best_iteration = 0
    for iteration in range(16 if near_final else 10):
        rows,req,axes,constraints = scan(p,w,faces,coarse,zones,body_faces,face_groups,True)
        overlaps,pressure = layers.scan(p,w,True)
        body_score = objective(rows)
        layer_count = sum(overlaps.values())
        score = (body_score[0]+layer_count,body_score[1],body_score[2])
        print('REFIT',iteration,score,'layers',overlaps,flush=True)
        history.append(dict(iteration=iteration, score=score, layers=overlaps, clips=rows))
        if best is None or score < best[0]:
            best = (score,p.copy(),w.copy())
            best_iteration = iteration
        if (not body_score[1] and not layer_count) or iteration-best_iteration>=(6 if near_final else 4):
            break
        if near_final and score[0]>4*max(best[0][0],20):
            # Backtrack when a local edit brings back broad cuff collisions.
            p = .5*(p+best[1])
            continue
        correction = envelope(p,origin,req,axes,constraints,graph,.82)-p if body_score[1] else np.zeros_like(p)
        if layer_count:
            layer_move = layers.move(pressure) * (.82 if iteration<5 else .55)
            if mode in ('conform','outside','polish','radial-polish'):
                adverse = np.minimum(0,np.einsum('ij,ij->i',axes,layer_move))
                layer_move -= axes*(adverse*(req>.001))[:,None]
            correction = correction + layer_move
        p = p + correction
        shifts = p-origin
        p = origin + shifts * np.minimum(1,.039/np.linalg.norm(shifts,axis=1,keepdims=True).clip(1.e-8,None))
        if shoe:
            p[:,2] = np.maximum(p[:,2],SOLE_M)
    _, winner, skin_weights = best
    export(garment,arm,scene,winner,skin_weights,names,destination)
    write_json(HERE/'qa'/f'{destination.stem}.refit.json',dict(mode=mode, history=history,
        max_shift_mm=float(np.linalg.norm(winner-start,axis=1).max()*1000)))


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('prior',type=Path)
    cli.add_argument('output',type=Path)
    cli.add_argument('gate',type=Path)
    cli.add_argument('--mode',choices=['radial','lower','conform','outside','polish','radial-polish'],default='radial')
    values = cli.parse_args(sys.argv[sys.argv.index('--')+1:])
    refit(values.prior,values.output,values.gate,values.mode)
