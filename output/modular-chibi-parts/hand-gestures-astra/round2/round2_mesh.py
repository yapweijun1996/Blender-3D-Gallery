"""Smooth the dorsal knuckle transitions while preserving the volar grip envelope."""
from collections import defaultdict
from mathutils import Vector
from hand_common import smooth


def refine_dorsum(body):
    mesh = body.data
    pos = [v.co.copy() for v in mesh.vertices]
    keys = [tuple(round(v, 7) for v in p) for p in pos]
    groups, graph = defaultdict(list), defaultdict(set)
    for i, key in enumerate(keys):
        groups[key].append(i)
    for e in mesh.edges:
        a, b = (keys[i] for i in e.vertices)
        if a != b:
            graph[a].add(b)
            graph[b].add(a)
    original_normals = [n.vector.copy() for n in mesh.corner_normals]
    encoded = [tuple(n.value) for n in mesh.attributes['custom_normal'].data]
    coords = {k: pos[ids[0]].copy() for k, ids in groups.items()}
    mask = {k: smooth(.29, .32, abs(k[0]))*(1-smooth(.348,.375,abs(k[0])))*
               smooth(.557,.567,k[2]) for k in coords}
    for _ in range(5):
        new = dict(coords)
        for key, t in mask.items():
            if not t or not graph[key]:
                continue
            mean = sum((coords[k] for k in graph[key]), Vector())/len(graph[key])
            new[key] = coords[key].lerp(mean,.40*t)
        coords = new
    for k, ids in groups.items():
        if mask[k]:
            for i in ids:
                mesh.vertices[i].co = coords[k]
    mesh.update()
    sums = defaultdict(Vector)
    for f in mesh.polygons:
        for i in f.vertices:
            if mask[keys[i]]:
                sums[keys[i]] += f.area*f.normal
    for li,loop in enumerate(mesh.loops):
        k = keys[loop.vertex_index]
        if mask[k]:
            original_normals[li] = original_normals[li].lerp(sums[k].normalized(),mask[k]).normalized()
    mesh.normals_split_custom_set(original_normals)
    custom=mesh.attributes['custom_normal'].data
    for loop in mesh.loops:
        if not mask[keys[loop.vertex_index]]:custom[loop.index].value=encoded[loop.index]
    mesh.update()


def pad_axis(rig, side, digit):
    from hand_common import prefix
    bone = rig.data.bones[prefix(side)+digit+'3']
    return (bone.matrix_local.col[1].xyz + .65*bone.matrix_local.col[2].xyz).normalized()


def soften_pads(body, rig):
    from hand_common import prefix, SIDES, vertex_weights
    mesh = body.data
    for _, side, sg in SIDES:
        for digit in ('Thumb','Index'):
            name = prefix(side)+digit
            axis = pad_axis(rig,side,digit)
            tip = rig.data.bones[name+'4'].head_local
            verts = [v for v in mesh.vertices if (v.co-tip).length < .020
                     and any(k.startswith(name) for k in vertex_weights(body,v))]
            level = max((v.co-tip).dot(axis) for v in verts) - .00165
            for v in verts:
                h = (v.co-tip).dot(axis)-level
                if h > -.0005:
                    # Soften the shoulder into a broad oval pulp surface.
                    t = min(1, max(0, (h+.0005)/.001))
                    removal = .25*.001*t*t if h<=.0005 else h-.00025
                    v.co -= .96*removal*axis
    mesh.update()


def distribute_proximal_flex(body, rig):
    """Reuse joint 4 as the DIP and give the long first phalanx a bend support.

    When joint 2 is neutral its skin transform equals joint 1 exactly. Moving
    the old PIP and DIP curves to joints 3 and 4 preserves an existing pose.
    """
    import bpy
    from hand_common import DIGITS, SIDES, prefix, vertex_weights
    chains={}
    for _,side,sg in SIDES:
        for digit in DIGITS[:4]:
            key=prefix(side)+digit
            bones=[rig.data.bones[key+str(i)] for i in (1,2,3,4)]
            chains[key]=[(b.head_local.copy(),b.tail_local.copy(),b.matrix_local.col[2].xyz.copy()) for b in bones]
    for v in body.data.vertices:
        weights=vertex_weights(body,v)
        names=[k for k in weights if k[:-1] in chains]
        if not names:continue
        key=names[0][:-1]
        chain=chains[key]
        a,b,_=chain[0]
        u=(v.co-a).dot(b-a)/(b-a).length_squared
        mix=smooth(.22,.78,u)
        first=weights.get(key+'1',0)
        new=[first*(1-mix),first*mix,weights.get(key+'2',0),weights.get(key+'3',0)+weights.get(key+'4',0)]
        # A few vertices at the root carry a palm/wrist slot as well.
        if sum(q>0 for q in new)+len(weights)-len(names)>4:
            if mix<.5:new[0],new[1]=first,0
            else:new[0],new[1]=0,first
        if 0 < new[0] < .00011:
            new[1]+=new[0];new[0]=0
        if 0 < new[1] < .00011:
            new[0]+=new[1];new[1]=0
        for n in names:body.vertex_groups[n].remove([v.index])
        for j,value in enumerate(new,1):
            if value:body.vertex_groups[key+str(j)].add([v.index],value,'REPLACE')
    bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT')
    for key,chain in chains.items():
        bones=[rig.data.edit_bones[key+str(i)] for i in (1,2,3,4)]
        connected=[b.use_connect for b in bones]
        for b in bones:b.use_connect=False
        start,end,up=chain[0]
        middle=start.lerp(end,.48)
        new=[(start,middle,up),(middle,end,up),chain[1],chain[2]]
        for b,(head,tail,guide) in zip(bones,new):
            b.head,b.tail=head,tail
            b.align_roll(guide)
        for b,was in zip(bones,connected):
            if was and (b.head-b.parent.tail).length<.000001:b.use_connect=True
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()
