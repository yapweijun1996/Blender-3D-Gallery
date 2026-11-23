"""Resolve remaining contacts on recorded witnesses before exporting a round."""
import numpy as np

from bake import layer_pressure, pose_shell, required_on_pose, smooth_envelope, transforms
from body_audit import posed, set_frame, use_action
from fitting_geometry import tree, weld_graph
from garments import unit


def witness_frames(evidence, previous):
    frames = {('rest',0.)}
    for clip, row in evidence['clips'].items():
        frames.update((clip,frame) for frame in row.get('witness_frames',{}).values())
    if previous:
        for clip,row in previous['clips'].items():
            samples = row['frames']
            stride = max(1,len(samples)//5)
            for start in range(0,len(samples),stride):
                area = samples[start:start+stride]
                worst = min(area,key=lambda entry:(-entry['pairs']-entry['inside'],entry['min_signed_m']))
                if worst['pairs'] or worst['min_signed_m']<.0005:
                    frames.add((clip,worst['frame']))
            for name in previous['layers_sha256']:
                worst = max(row['frames'],key=lambda entry:entry['layer_pairs'][name])
                if worst['layer_pairs'][name]:
                    frames.add((clip,worst['frame']))
            for key in ('inside','pairs','min_signed_m'):
                if key=='min_signed_m':
                    worst = min(row['frames'],key=lambda entry:entry[key])
                    take = worst[key]<.0005
                else:
                    worst = max(row['frames'],key=lambda entry:entry[key])
                    take = worst[key]>0
                if take:
                    frames.add((clip,worst['frame']))
    return sorted(frames)


def refine(p, f, w, directions, item, scene, arm, body, bf, actions, layers, evidence, previous):
    graph = weld_graph(p,f)
    faces = f.tolist()
    body_faces = bf.tolist()
    bind = np.array([np.asarray(arm.data.bones[b.name].matrix_local.inverted()) for b in arm.pose.bones])
    ids = np.argpartition(w,-4,axis=1)[:,-4:]
    packets = w[np.arange(len(ids))[:,None],ids]
    cache = {}
    for clip,frame in witness_frames(evidence,previous):
        cache_key = (clip,frame)
        use_action(arm,actions.get(clip))
        set_frame(scene,frame)
        matrices = transforms(arm,bind)
        candidate,_ = pose_shell(p,matrices,ids,packets)
        nearby = []
        for obj,faces_layer in layers.values():
            layer = posed(obj)
            close = (layer.max(axis=0)>=candidate.min(axis=0)-.025).all() and (
                candidate.max(axis=0)>=layer.min(axis=0)-.025).all()
            if close:
                nearby.append(tree(layer,faces_layer))
        cache[cache_key] = matrices,tree(posed(body),body_faces),nearby
    best, best_score = p.copy(), None
    current = p.copy()
    journal = []
    for iteration in range(12):
        distances = np.zeros(len(p))
        delta = np.zeros_like(p)
        inside, overlaps, layer_overlaps, minimum = 0,0,0,1.
        for matrices,surface,nearby in cache.values():
            fit,basis = pose_shell(current,matrices,ids,packets)
            candidate = tree(fit,faces)
            pairs = surface.overlap(candidate)
            need,normal,count,worst = required_on_pose(surface,fit,f,pairs)
            inside += count
            overlaps += len(pairs)
            minimum = min(minimum,worst)
            active = np.flatnonzero(need > .0003)
            gradient = np.einsum('vji,vj->vi',basis[active],normal[active])
            magnitude = np.linalg.norm(gradient,axis=1)
            guide = directions[active]
            agree = np.einsum('vi,vi->v',gradient,guide)
            correction = np.where((agree>.70)[:,None],unit(guide*.80+unit(gradient)*.20),unit(gradient))
            need = need[active]/np.maximum(.40,np.einsum('vi,vi->v',gradient,correction))
            higher = need>distances[active]
            pos = active[higher]
            distances[pos] = need[higher]
            delta[pos] = correction[higher]*need[higher,None]
            for layer in nearby:
                hits = layer.overlap(candidate)
                layer_overlaps += len(hits)
                if not hits:
                    continue
                vertices,axis,pressure = layer_pressure(item,layer,fit,f,hits,directions,basis)
                add = pressure>distances[vertices]
                selected = vertices[add]
                distances[selected] = pressure[add]
                delta[selected] = axis[add]*pressure[add,None]
        score = (inside+overlaps+layer_overlaps, max(0.,.0009-minimum))
        journal.append(dict(inside_sum=inside,pairs_sum=overlaps,layer_pairs_sum=layer_overlaps,minimum_m=minimum))
        if best_score is None or score < best_score:
            best, best_score = current.copy(), score
        if score==(0,0.) or not distances.any():
            break
        delta = smooth_envelope(delta,graph)
        cap = .005 if iteration<4 else .0028
        delta *= np.minimum(1.,cap/np.maximum(1.e-12,np.linalg.norm(delta,axis=1)))[:,None]
        if iteration in (4,8):
            current = best.copy()
        current += delta * (0.8 if iteration<5 else .50)
    evidence['witness_refinement'] = dict(samples=len(cache), passes=journal)
    return best


def restore_rest_clearance(points, faces, body, body_faces):
    """Remove fold corrections that created penetration in the bind pose."""
    surface = tree(body,body_faces.tolist())
    graph = weld_graph(points,faces)
    face_list = faces.tolist()
    best, key = points.copy(),None
    journal = []
    for _ in range(9):
        pairs = surface.overlap(tree(points,face_list))
        depth,heading,inside,minimum = required_on_pose(surface,points,faces,pairs)
        score = (len(pairs),inside,max(0.,.0012-minimum))
        if key is None or score<key:
            best,key = points.copy(),score
        journal.append({'pairs':len(pairs),'inside':inside,'minimum_m':minimum})
        if score==(0,0,0.):
            break
        delta = heading * np.minimum(.005,depth[:,None])
        points = points + .68*smooth_envelope(delta,graph)
    return best,journal
