"""Bake a per-vertex worst-pose clearance field on each authored shell."""
import numpy as np

from body_audit import posed
from fit_module import nearest
from fitting_geometry import arrays, laplacian, tree, weld_graph
from garments import unit
from gate_module import poses
from skirt_envelope import SkirtEnvelope, edges

MARGIN = .0018
PROBES = np.array(((1/3,1/3,1/3),(.5,.5,0),(.5,0,.5),(0,.5,.5),
                   (.72,.14,.14),(.14,.72,.14),(.14,.14,.72)))


def transforms(arm, bind):
    return np.array([np.array(bone.matrix) for bone in arm.pose.bones]) @ bind


def pose_shell(p, matrices, ids, w):
    affine = (matrices[ids,:3,:] * w[:,:,None,None]).sum(axis=1)
    return np.einsum('vij,vj->vi',affine[:,:,:3],p) + affine[:,:,3],affine[:,:,:3]


def required_on_pose(surface, p, f, pairs):
    signed,n,ids = nearest(surface,p)
    need = np.maximum(0,MARGIN - signed)
    if pairs:
        touched = np.unique(np.asarray(pairs)[:,1])
        corners = f[touched]
        q = np.einsum('kc,tcd->tkd',PROBES,p[corners])
        depths, normals, _ = nearest(surface,q.reshape(-1,3))
        depths = depths.reshape(-1,len(PROBES))
        lowest = depths.argmin(axis=1)
        normals = normals.reshape(-1,len(PROBES),3)[np.arange(len(touched)),lowest]
        required = MARGIN + np.maximum(0,-depths.min(axis=1))
        for tri,axis,value in zip(corners,normals,required):
            pressure = tri[need[tri]<value]
            need[pressure], n[pressure] = value, axis
    return need,n,int(np.count_nonzero(signed<0)),float(signed.min())


def smooth_envelope(delta, graph, skirt=False):
    size = np.linalg.norm(delta,axis=1)
    heading = unit(delta)
    for _ in range(9 if skirt else 6):
        delta = .58*delta+.42*laplacian(delta,graph)
        # Spreading the highest requirement must not lower the displacement
        # already needed at its witness vertex.
        delta += heading*np.maximum(0,size-np.einsum('vi,vi->v',delta,heading))[:,None]
    return delta


def layer_pressure(item, layer, fit, faces, hits, directions):
    vertices = np.unique(faces[np.asarray(hits)[:,1]])
    distance,normal,_ = nearest(layer,fit[vertices])
    if item.startswith('top'):
        axis = directions[vertices].copy()
        axis[:,2] = np.maximum(axis[:,2],.7)
        axis = unit(axis)
    elif item=='bottom-skirt':
        axis = directions[vertices]
    else:
        axis = np.zeros_like(normal)
        axis[:,2] = -1
    need = np.clip(.0025+abs(distance)*.85,.0025,.017)
    return vertices,axis,need


def bake(p, f, w, directions, item, scene, arm, body, body_faces, actions, layers, fresh, round_no):
    faces = f.tolist()
    graph = weld_graph(p,f)
    names = [b.name for b in arm.data.bones]
    assert names == [b.name for b in arm.pose.bones]
    bind = np.array([np.asarray(arm.data.bones[n].matrix_local.inverted()) for n in names])
    ids = np.argpartition(w,-4,axis=1)[:,-4:]
    w = w[np.arange(len(ids))[:,None],ids]
    skirt = SkirtEnvelope(p,body_faces,arrays(body)[0],arm) if item=='bottom-skirt' and fresh else None
    shirt_obj, shirt_edge = None, None
    if skirt is not None:
        shirt_obj = layers['male-top-tshirt.glb'][0]
        shirt_vertices, shirt_tri = arrays(shirt_obj)
        waist_faces = shirt_tri[shirt_vertices[shirt_tri,2].max(axis=1)<.460]
        shirt_edge = edges(waist_faces)
    body_faces = body_faces.tolist()
    last_clip = None
    worst = np.zeros(len(p))
    layer_worst = np.zeros(len(p))
    correction = np.zeros_like(p)
    layer_correction = np.zeros_like(p)
    stats = {}
    for clip,frame in poses(scene,arm,actions):
        if last_clip!=clip:
            print('BAKE',item,clip,flush=True)
            last_clip = clip
        matrices = transforms(arm,bind)
        body_points = posed(body)
        if skirt is not None:
            skirt.sample(body_points,matrices,posed(shirt_obj),shirt_edge)
        fit,basis = pose_shell(p,matrices,ids,w)
        target = tree(fit,faces)
        body_surface = tree(body_points,body_faces)
        pairs = body_surface.overlap(target)
        need,axis,inside,minimum = required_on_pose(body_surface,fit,f,pairs)
        peak = stats.setdefault(clip,dict(inside=0,pairs=0,minimum_m=1.,layers={},witness_frames={}))
        if len(pairs)>peak['pairs']:
            peak['witness_frames']['pairs'] = frame
        if inside>peak['inside']:
            peak['witness_frames']['inside'] = frame
        if minimum<peak['minimum_m'] and minimum<.001:
            peak['witness_frames']['signed'] = frame
        peak['inside'] = max(peak['inside'],inside)
        peak['pairs'] = max(peak['pairs'],len(pairs))
        peak['minimum_m'] = min(peak['minimum_m'],minimum)
        active = np.flatnonzero(need)
        gradient = np.einsum('vji,vj->vi',basis[active],axis[active])
        guide = directions[active]
        along = np.einsum('vi,vi->v',gradient,guide)
        # Favor the shell's outward direction where it actually clears the
        # witness. Use posed-normal relief around crossing limbs and joints.
        direct = along > .52
        if item=='bottom-skirt':
            direct = along > .24
        distance = need[active]/np.where(direct,along,np.maximum(np.linalg.norm(gradient,axis=1),.35))
        direction = np.where(direct[:,None],guide,unit(gradient))
        replace = distance>worst[active]
        selected = active[replace]
        worst[selected] = distance[replace]
        correction[selected] = direction[replace]*distance[replace,None]

        for name,(obj,tri) in layers.items():
            obstacle = posed(obj)
            if (obstacle.max(axis=0)<fit.min(axis=0)).any() or (fit.max(axis=0)<obstacle.min(axis=0)).any():
                continue
            layer = tree(obstacle,tri)
            hits = layer.overlap(target)
            if len(hits)>peak['layers'].get(name,0):
                peak['witness_frames'][name] = frame
            peak['layers'][name] = max(peak['layers'].get(name,0),len(hits))
            if not hits:
                continue
            vertices,axis,need = layer_pressure(item,layer,fit,f,hits,directions)
            replace = need > layer_worst[vertices]
            selected = vertices[replace]
            layer_worst[selected] = need[replace]
            layer_correction[selected] = axis[replace]*need[replace,None]

    raw = correction+layer_correction
    delta = smooth_envelope(raw,graph,item=='bottom-skirt')
    if item=='bottom-skirt':
        cap = .095
    else:
        cap = .034
    delta *= np.minimum(1,cap/np.maximum(1.e-12,np.linalg.norm(delta,axis=1)))[:,None]
    result = dict(margin_m=MARGIN, max_raw_body_relief_m=float(worst.max()),
                  max_raw_layer_relief_m=float(layer_worst.max()),
                  max_baked_offset_m=float(np.linalg.norm(delta,axis=1).max()), clips=stats)
    if skirt is not None:
        clamped = skirt.clamp(p.copy(),slim=round_no==3)
        result['skirt_sweep_peak_m'] = float(np.linalg.norm(clamped-p,axis=1).max())
        result['skirt_sweep_includes_shipped_shirt_hem'] = True
        # The leg envelope already covers radial contact; retain the larger
        # of the independently measured local correction and radial sweep.
        swept = np.maximum(0,np.einsum('vi,vi->v',clamped-p,directions))
        baked = np.einsum('vi,vi->v',delta,directions)
        delta += directions * np.maximum(0,swept-baked)[:,None]
    return p+delta,result
