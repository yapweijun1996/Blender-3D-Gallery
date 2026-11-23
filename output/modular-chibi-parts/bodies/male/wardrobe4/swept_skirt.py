"""Build a pleated pelvis-bound skirt from the swept thigh cross sections."""
import numpy as np

from bake import transforms
from body_audit import posed
from gate_module import poses
from tailoring import CENTER, Panels, grid

N = 96


def edges(faces):
    edges = np.vstack((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]))
    return np.unique(np.sort(edges,axis=1),axis=0)


def swept_radii(levels, scene, arm, body, points, faces, actions, names, ring_weights, guard_arms=False):
    # Clipping model triangles to a slice yields convex polygons whose radial
    # extrema are on the original vertices or the cut edges.
    z = points[faces,2]
    lower = faces[(z.min(axis=1)<.411)&(z.max(axis=1)>.190)]
    e = edges(lower)
    vertices = np.unique(lower)
    compact_edges = np.searchsorted(vertices,e)
    origin = np.array((CENTER,-.024828))
    bind = np.array([np.asarray(arm.data.bones[name].matrix_local.inverted()) for name in names])
    used = np.flatnonzero(ring_weights.any(axis=0))
    planes = np.sort(np.r_[levels,(levels[1:]+levels[:-1])*.5])[::-1]
    blend = np.column_stack([np.interp(planes,levels[::-1],w[::-1]) for w in ring_weights[:,used].T])
    constant = np.array_equal(blend,np.broadcast_to(blend[0],blend.shape))
    span = np.r_[abs(np.diff(planes)),abs(planes[-2]-planes[-1])]
    radius = np.zeros((len(planes),N))
    upper = np.full_like(radius,np.inf)
    if guard_arms:
        arm_faces = faces[(z.min(1)>.458)&(z.max(1)<.600)&(abs(points[faces,0]-CENTER).min(1)>.145)]
        arms = edges(arm_faces)
        arm_verts = np.unique(arms)
        arms = np.searchsorted(arm_verts,arms)
    last = None

    def collect(rows, points, obstacle=False):
        xy = points[:,:2]-origin
        angle = np.arctan2(xy[:,1],xy[:,0])
        columns = np.floor(angle*(N/(2*np.pi))).astype(int)
        length = np.linalg.norm(xy,axis=1)
        if obstacle:
            for delta in (0,1):
                np.minimum.at(upper,(rows,(columns+delta)%N),length)
        else:
            for delta in (-1,0,1,2):
                np.maximum.at(radius,(rows,(columns+delta)%N),length)

    for clip,_ in poses(scene,arm,actions):
        if clip!=last:
            print('THIGH SWEEP',clip,flush=True)
            last=clip
        matrices = transforms(arm,bind)[used]
        inv = np.linalg.inv(np.einsum('lb,bij->lij',blend[:1] if constant else blend,matrices))
        evaluated = posed(body)
        world = evaluated[vertices]
        if constant:
            p = world @ inv[0,:3,:3].T + inv[0,:3,3]
            a,b = p[compact_edges[:,0]],p[compact_edges[:,1]]
            lo,hi = np.minimum(a[:,2],b[:,2]),np.maximum(a[:,2],b[:,2])
            rows, ids = np.nonzero((planes[:,None]>=lo)&(planes[:,None]<hi))
            fraction = (planes[rows]-a[ids,2])/(b[ids,2]-a[ids,2])
            collect(rows,a[ids]+fraction[:,None]*(b[ids]-a[ids]))
            valid = (p[:,2]<=planes[0])&(p[:,2]>=planes[-1])
            end = p[valid]
            rows = np.searchsorted(-planes,-end[:,2])
            collect(rows,end)
            collect(np.maximum(0,rows-1),end)
        else:
            p = np.einsum('lij,vj->lvi',inv[:,:3,:3],world) + inv[:,None,:3,3]
            a,b = p[:,compact_edges[:,0]],p[:,compact_edges[:,1]]
            lo,hi = np.minimum(a[:,:,2],b[:,:,2]),np.maximum(a[:,:,2],b[:,:,2])
            rows,ids = np.nonzero((planes[:,None]>=lo)&(planes[:,None]<hi))
            row_a,row_b = a[rows,ids],b[rows,ids]
            fraction = (planes[rows]-row_a[:,2])/(row_b[:,2]-row_a[:,2])
            collect(rows,row_a+fraction[:,None]*(row_b-row_a))
            rows,ids = np.nonzero(abs(p[:,:,2]-planes[:,None])<=span[:,None])
            collect(rows,p[rows,ids])
        if guard_arms:
            wrist = np.einsum('lij,vj->lvi',inv[:,:3,:3],evaluated[arm_verts]) + inv[:,None,:3,3]
            a,b = wrist[:,arms[:,0]],wrist[:,arms[:,1]]
            lo,hi = np.minimum(a[:,:,2],b[:,:,2]),np.maximum(a[:,:,2],b[:,:,2])
            rows,ids = np.nonzero((planes[:,None]>=lo)&(planes[:,None]<hi))
            row_a,row_b = a[rows,ids],b[rows,ids]
            fraction = (planes[rows]-row_a[:,2])/(row_b[:,2]-row_a[:,2])
            collect(rows,row_a+fraction[:,None]*(row_b-row_a),True)
    bound = radius[::2].copy()
    np.maximum(bound[:-1],radius[1::2],out=bound[:-1])
    np.maximum(bound[1:],radius[1::2],out=bound[1:])
    arm_limit = upper[::2].copy()
    np.minimum(arm_limit[:-1],upper[1::2],out=arm_limit[:-1])
    np.minimum(arm_limit[1:],upper[1::2],out=arm_limit[1:])
    return origin,bound,arm_limit


def build_skirt(scene, arm, body, points, faces, actions, names, style):
    waist = (.383,.384,.376)[style-1]
    levels = np.r_[waist,waist-.005,waist-.012,np.linspace(waist-.017,.283 if style<3 else .290,13)]
    thigh = (0.,.19,.06)[style-1] * np.clip((waist-.010-levels)/.059,0,1)
    spine = (0.,.32,.54)[style-1] * np.clip((levels-waist+.027)/.027,0,1)
    shape_weights = np.zeros((len(levels),len(names)))
    for bone,profile in (('Hips',1.-2*thigh-spine),('Spine',spine),
                         ('LeftUpLeg',thigh),('RightUpLeg',thigh)):
        shape_weights[:,names.index('mixamorig:'+bone)] = profile
    origin,sweep,arm_limit = swept_radii(levels,scene,arm,body,points,faces,actions,names,shape_weights,style==3)
    angles = np.arange(N)*2*np.pi/N
    depth = np.clip((levels[0]-levels)/(.383-levels[-1]),0,1)[:,None]
    minima = sweep + (.003,.0028,.0021)[style-1]
    natural = minima[0] + depth*((.019 if style==1 else .010)+.020*np.abs(np.sin(angles)))
    r = np.maximum(minima,natural)
    # A one-sided filter softens folds in the envelope while keeping every
    # measured sweep radius as a lower bound.
    for _ in range(8):
        angular = (.5*r+.25*(np.roll(r,1,axis=1)+np.roll(r,-1,axis=1)))
        angular[1:-1] = .65*angular[1:-1]+.175*(angular[:-2]+angular[2:])
        r = np.maximum(minima,angular)
    pleat = np.array((.0,.0016,.0031,.0047,.0052,.0012)) * (1.3 if style>1 else 1.)
    r += np.tile(pleat,N//6) * np.clip((depth-.12)/.24,0,1)
    feasible = arm_limit- .0015 >= minima
    squeeze = np.maximum(0,r-np.where(feasible,arm_limit-.0015,minima))
    squeeze[~np.isfinite(arm_limit)] = 0.
    for _ in range(3):
        squeeze = np.maximum(squeeze,.28*(np.roll(squeeze,1,axis=1)+np.roll(squeeze,-1,axis=1)))
    r = np.maximum(minima,r-squeeze)
    xy = origin + r[:,:,None]*np.column_stack((np.cos(angles),np.sin(angles)))
    p = np.concatenate((xy,np.broadcast_to(levels[:,None,None],(*r.shape,1))),axis=2).reshape(-1,3)
    f = grid(len(levels),N,True,True)
    panel = Panels()
    panel.add(p,f,np.repeat(shape_weights,N,axis=0),np.where(p[f,2].mean(1)>levels[2],1,0))
    print('SWEEP BOUNDS',np.round(r.min(1),4).tolist(),np.round(r.max(1),4).tolist(),flush=True)
    return panel.result(), dict(sweep='skin bind frame, thigh triangle edges and slab vertices',
                                radial_clearance_m=float((r-sweep).min()), pleats=N//6,
                                thigh_weight_per_side=thigh.tolist(), spine_weight=spine.tolist(), ring_heights_m=levels.tolist(),
                                minimum_radii_m=r.min(1).tolist(),maximum_radii_m=r.max(1).tolist(),
                                arm_clearance_clamps=int(np.count_nonzero(squeeze)))
