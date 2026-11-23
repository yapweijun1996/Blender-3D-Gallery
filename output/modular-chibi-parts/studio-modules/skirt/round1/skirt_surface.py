"""Pleated closed ring loft and body-weight transfer for the Studio skirt."""
import bpy
import math
import numpy as np
from mathutils import Vector
from fit_skirt import N, coords, faces, make_tree, nearest

SIDES = 64
CENTER = np.array((.0008, -.020), dtype=np.float32)
SOURCE_CENTER = np.array((.0008, -.016), dtype=np.float32)
CONTROLS = ("Hips", "LeftUpLeg", "RightUpLeg", "Spine", "Spine1")
PLEATS = 10


def smooth(value):
    value = np.clip(value, 0, 1)
    return value * value * (3 - 2 * value)


def barycentric(points, triangles):
    a, b, c = np.moveaxis(triangles, 1, 0)
    ab, ac, v = b-a, c-a, points-a
    ab2, ac2 = (ab*ab).sum(axis=1), (ac*ac).sum(axis=1)
    cross = (ab*ac).sum(axis=1)
    v_ab, v_ac = (v*ab).sum(axis=1), (v*ac).sum(axis=1)
    scale = np.maximum(ab2*ac2 - cross**2, 1e-21)
    u = (ac2*v_ab - cross*v_ac) / scale
    w = (ab2*v_ac - cross*v_ab) / scale
    result = np.clip(np.array((1-u-w, u, w)).T, 0, 1)
    return result / result.sum(axis=1, keepdims=True)


def body_weight_transfer(points, body, tree):
    _, surface, _, ids = nearest(tree, points)
    source_faces = faces(body)[ids]
    bary = barycentric(surface, coords(body)[source_faces])
    values = np.zeros((len(body.data.vertices), len(CONTROLS)), dtype=np.float32)
    groups = {group.index: CONTROLS.index(group.name.removeprefix(N))
              for group in body.vertex_groups if group.name.removeprefix(N) in CONTROLS}
    for vertex in body.data.vertices:
        for group in vertex.groups:
            if group.group in groups:
                values[vertex.index, groups[group.group]] = group.weight
    transferred = np.einsum("ij,ijk->ik", bary, values[source_faces])
    return transferred / np.maximum(1e-8, transferred.sum(axis=1, keepdims=True))


def limit_weights(weights):
    result = np.maximum(weights, 0)
    result[np.arange(len(result)), result.argmin(axis=1)] = 0
    result[result < .0001] = 0
    empty = result.sum(axis=1) < 1e-8
    result[empty, 0] = 1
    return result / result.sum(axis=1, keepdims=True)


def ring_faces(count):
    quads = []
    for row in range(count):
        next_row = (row + 1) % count
        for col in range(SIDES):
            next_col = (col + 1) % SIDES
            quads.append((row*SIDES+col, next_row*SIDES+col,
                          next_row*SIDES+next_col, row*SIDES+next_col))
    quads = np.array(quads, dtype=np.int32)
    triangles = np.empty((2*len(quads), 3), dtype=np.int32)
    triangles[::2] = quads[:, (0,1,2)]
    triangles[1::2] = quads[:, (0,2,3)]
    return triangles


def build_loft(body, tree, hem=.285, flare=1.0, leg=1.0, center_lift=.010):
    theta = np.arange(SIDES, dtype=np.float32) * (2*math.pi/SIDES)
    sin, cos = np.sin(theta), np.cos(theta)
    rays = np.column_stack((sin, -cos))
    depth = np.array((0., .025, .085, .115, .22, .35, .50, .66, .80, .92, 1.))
    waist = .426
    profile = .73*np.cos(PLEATS*theta+.25) + .27*np.cos(2*PLEATS*theta+.62)
    fore_center = np.exp(-((1-cos)/.14)**2) * center_lift
    back_center = np.exp(-((1+cos)/.14)**2) * center_lift*.8
    z = waist - (waist-hem)*depth[:, None] + depth[:, None]**3*(fore_center+back_center)
    z += .0025 * depth[:, None]**3 * np.cos(PLEATS*theta+.25)
    width = .103 + (.048*flare)*depth
    front = .096 + (.018*flare)*depth
    back = .085 + (.022*flare)*depth
    reach = np.where(cos[None, :] > 0, front[:, None], back[:, None])
    radial = ((sin/width[:, None])**2 + (cos/reach)**2)**(-.5)
    radial += (.001+.004*depth[:, None]) * depth[:, None] * profile
    # Strap top and bottom turn in slightly. Concentrate the raised buckle
    # at the source-facing centre of the front waistband.
    strap = np.array((-.0018, .0018, .0022, -.0012, 0, 0, 0, 0, 0, 0, 0))
    radial += strap[:, None]
    buckle = np.exp(-((1-cos)/.009)**2)
    radial += np.array((0,.0018,.0037,.0009,0,0,0,0,0,0,0))[:,None]*buckle

    def positions(r):
        return np.concatenate((CENTER + r[:, :, None]*rays, z[:, :, None]), axis=2)

    # Project the outer outline into the space between the body and the rest
    # clearance cap. Smooth the angular corrections before the final clamp.
    def constrain(r, low=.0055, high=.026):
        for _ in range(18):
            gaps, _, normals, _ = nearest(tree, positions(r).reshape(-1, 3))
            gaps = gaps.reshape(r.shape)
            directional = np.einsum("rsi,si->rs", normals.reshape(len(z), SIDES,3)[:,:,:2], rays)
            step = np.clip(np.maximum(low-gaps, 0) - np.maximum(gaps-high, 0), -.012, .012)
            r += step / np.maximum(directional, .50)
            if np.max(abs(step)) < .00008:
                break
        return r

    target = radial.copy()
    for _ in range(3):
        constrain(radial)
        correction = radial - target
        radial = target + .55*correction + .225*(np.roll(correction,1,1)+np.roll(correction,-1,1))
    outer = positions(constrain(radial))
    weights = body_weight_transfer(outer.reshape(-1, 3),body,tree).reshape(len(z),SIDES,-1)
    for _ in range(5):
        angular = .5*(np.roll(weights, 1, axis=1) + np.roll(weights, -1, axis=1))
        weights = .60*weights + .4*angular
    # Fade the thigh weights smoothly at the waistband and share the weight
    # between thighs around the front/back bridge as the cloth crosses centre.
    weights[:,:,1:3] *= (leg * smooth((depth-.17)/.54))[:,None,None]
    weights[:,:,0] = 1. - weights[:,:,1:].sum(axis=2)
    # At the cut edges the inner wall shares the outer wall's skin weights.
    # Matching cross sections keep the waistband and hem thickness stable.
    inside = np.array((10,9,8,7,6,5,4,3,2,1,0))
    separation = np.array((.0018,.0017,.0016,.00155,.0015,.0015,.0015,.0015,.0015,.0015,.0018))
    inner = outer[inside].copy()
    inner[:,:,:2] -= separation[:,None,None]*rays
    geometry = np.concatenate((outer,inner))
    duplicate_rows = len(outer) + np.arange(len(inside))
    paired = np.column_stack((inside[:,None]*SIDES+np.arange(SIDES),
                              duplicate_rows[:,None]*SIDES+np.arange(SIDES))).reshape(len(inside),2,SIDES)
    return (geometry.reshape(-1,3).astype(np.float32), ring_faces(len(geometry)),
            limit_weights(np.concatenate((weights,weights[inside])).reshape(-1,len(CONTROLS))),
            paired, depth, theta)


def add_buckle(points, triangles, weights, offset=(0.,0.,0.), scale=1.):
    """Form a chamfered brass frame whose skin follows the front waistband."""
    center = .5*(points[SIDES]+points[2*SIDES])
    center[1] = min(points[SIDES,1],points[2*SIDES,1]) - .0011
    center[2] -= .00025
    center += np.asarray(offset,dtype=np.float32)
    width,height,stroke = .0090,.0048,.0015
    layers = []
    for wider,toward in ((True,True),(False,True),(False,False),(True,False)):
        w,h = (width,height) if wider else (width-stroke,height-stroke)
        c = .00135 if wider else .00075
        outline = np.array([(-w+c,-h),(w-c,-h),(w,-h+c),(w,h-c),
                            (w-c,h),(-w+c,h),(-w,h-c),(-w,-h+c)])
        axial = -.00165 if toward else .0011
        layers.append(center+np.column_stack((outline[:,0],np.full(8,axial),outline[:,1])))
    base = len(points)
    quads = []
    for layer in range(4):
        nxt = (layer+1)%4
        for j in range(8):
            k = (j+1)%8
            quads.append((base+layer*8+j,base+layer*8+k,base+nxt*8+k,base+nxt*8+j))
    quads = np.array(quads,dtype=np.int32)
    tris = np.stack((quads[:,(0,1,2)],quads[:,(0,2,3)]),axis=1).reshape(-1,3)
    verts = np.concatenate(layers).astype(np.float32)
    verts[:, (0,2)] = center[(0,2),] + scale*(verts[:, (0,2)]-center[(0,2),])
    coords_for_volume = verts[tris-base]
    signed = np.sum(np.einsum("ij,ij->i",coords_for_volume[:,0],
                              np.cross(coords_for_volume[:,1], coords_for_volume[:,2])))
    if signed < 0:
        tris = tris[:,::-1]
    influences = limit_weights(.5*(weights[SIDES]+weights[2*SIDES])[None])
    return (np.concatenate((points,verts)),np.concatenate((triangles,tris)),
            np.concatenate((weights,np.repeat(influences,len(verts),axis=0))))


def finish_fabric(mesh, depth, theta):
    """Soften baked shading dents and keep the modeled pleat cadence visible."""
    material = mesh.materials[0]
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
    color = shader.inputs["Base Color"]
    source = color.links[0].from_socket
    tint = nodes.new("ShaderNodeMix")
    tint.label = "Forest green fabric tint"
    tint.data_type = "RGBA"
    tint.blend_type = "MULTIPLY"
    tint.inputs[0].default_value = 1.
    tint.inputs[7].default_value = (.61,.73,.64,1.)
    links.new(source,tint.inputs[6])
    links.new(tint.outputs[2],color)
    shader.inputs["Roughness"].default_value = .82

    normals = np.array([vertex.normal[:] for vertex in mesh.vertices],dtype=np.float32)
    count = SIDES*len(depth)
    outside = normals[:count].reshape(len(depth),SIDES,3)
    rays = np.column_stack((.79*np.sin(theta),-1.18*np.cos(theta),np.zeros(len(theta))))
    rays /= np.linalg.norm(rays,axis=1,keepdims=True)
    tangent = np.column_stack((-rays[:,1],rays[:,0],np.zeros(len(theta))))
    folds = -.21*np.sin(PLEATS*theta+.25)[None,:]*(depth[:,None]**.55)
    unified = rays[None]+folds[:,:,None]*tangent
    unified[:,:,2] = .12 + .25*outside[:,:,2]
    influence = .72*smooth((depth-.17)/.32)[:,None,None]
    outside[:] = (1-influence)*outside+influence*unified
    normals /= np.maximum(1e-8,np.linalg.norm(normals,axis=1,keepdims=True))
    mesh.normals_split_custom_set_from_vertices(normals.tolist())
