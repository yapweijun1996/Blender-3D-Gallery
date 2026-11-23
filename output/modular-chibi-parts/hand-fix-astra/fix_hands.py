"""Repair the two hands of the supplied GJH master, in Blender's bind pose.

Run with Blender's --python fix_hands.py -- [source.blend]. Outputs are next
to this script. The working .blend is a byte copy before bpy opens it.
"""
import argparse
import heapq
import math
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import bpy
import bmesh
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

OUT = Path(__file__).resolve().parent
SOURCE = OUT.parent / "master" / "GJH_Chibi_Master_rigged.blend"
FINGERS = ("Index", "Middle", "Ring", "Pinky")
DIGITS = (*FINGERS, "Thumb")
YAW = dict(zip(DIGITS, (-9.75, -3.25, 3.25, 9.75, -58.0)))


def smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def sample_chain(point, joints):
    """Return distance and continuous arclength of closest finite segment."""
    candidates = []
    length = 0.0
    for a, b in zip(joints, joints[1:]):
        axis = b - a
        t = max(0.0, min(1.0, (point - a).dot(axis) / axis.length_squared))
        candidates.append(((point - a - t * axis).length, length + t * axis.length))
        length += axis.length
    return min(candidates)


def islands(points, graph):
    pending = set(points)
    while pending:
        seed = pending.pop()
        group = [seed]
        for p in group:
            for q in graph[p].intersection(pending):
                pending.remove(q)
                group.append(q)
        yield group


class Hand:
    def __init__(self, side, arm, graph):
        self.prefix = 'mixamorig:' + side + 'Hand'
        self.sign = 1 if side == 'Left' else -1
        bones = arm.data.bones
        self.wrist = bones[self.prefix].head_local.copy()
        self.joints = {}
        for digit in DIGITS:
            chain = [bones[self.prefix + digit + str(i)] for i in range(1, 5)]
            self.joints[digit] = [b.head_local.copy() for b in chain] + [chain[-1].tail_local.copy()]

        # The knuckle line measures the actual inclination of this particular
        # hand. Using either palm-facing normal alone would leave roll ambiguous.
        across = self.joints['Pinky'][0] - self.joints['Index'][0]
        self.roll = -math.atan2(across.z, across.y)
        self.rotation = {}
        self.front = {}
        self.offset = {}
        for digit, joints in self.joints.items():
            root = self.base(joints[0])
            end = self.base(joints[3])
            flat = (end - root).normalized()
            yaw = math.radians(YAW[digit])
            pitch = math.radians(-4 if digit == 'Thumb' else -2)
            target = Vector((self.sign * math.cos(yaw)*math.cos(pitch),
                             math.sin(yaw)*math.cos(pitch), math.sin(pitch)))
            self.rotation[digit] = flat.rotation_difference(target)
            self.front[digit] = target
            self.offset[digit] = Vector((0, 0 if digit == 'Thumb' else
                                         (FINGERS.index(digit)-1.5)*0.0009, 0))

        self.label = {}
        unbranched_palm = set()
        self.free_shafts = set()
        keys = [key for key in graph if self.sign*key[0] > 0.27]
        # Texture and normal seams use duplicate Blender vertices. Connectivity
        # on coincident positions keeps both copies on exactly the same digit.
        for threshold, digits in [(0.323, ('Thumb',)), (0.348, ('Index',)),
                                  (0.352, ('Pinky',)), (0.356, FINGERS)]:
            pieces = sorted(islands([p for p in keys if self.sign*p[0] > threshold], graph),
                            key=lambda g: sum(p[1] for p in g)/len(g))
            if digits == ('Thumb',):
                assert len(pieces)==2
                unbranched_palm.update(pieces[1])
            elif digits == ('Pinky',):
                pieces = pieces[-1:]
            elif digits == FINGERS:
                assert len(pieces)==4
            for digit, group in zip(digits, pieces):
                self.free_shafts.update(group)
                for p in group:
                    self.label[p] = digit
        for p in keys:
            if p not in self.label:
                candidates = FINGERS if p in unbranched_palm else DIGITS
                self.label[p] = min(candidates, key=lambda d: sample_chain(Vector(p), self.joints[d])[0])

        self.new_joints = {d: [self.digit_map(p, d) for p in joints]
                           for d, joints in self.joints.items()}

    def fit_knuckles(self, positions):
        # Compressing the webs and recovering finger length stretches the
        # distal phalanges. Redistribute the pivots along the mapped finger
        # axis, using the actual fingertip and the new web line as landmarks.
        for digit,root_x in zip(FINGERS,(0.324,0.328,0.329,0.325)):
            axis=self.front[digit]
            points=[positions[p] for p,d in self.label.items() if d==digit and abs(p[0])>0.36]
            end=max(p.dot(axis) for p in points)
            cap=[p for p in points if p.dot(axis)>end-0.0035]
            tip=sum(cap,Vector())/len(cap)
            length=(tip.x-self.sign*root_x)/axis.x
            root=tip-axis*length
            # Keep the MCP hinge inside the palmar half of the knuckle,
            # below the dorsal cap that carries most of the bent silhouette.
            pad = [positions[p].z for p,d in self.label.items()
                   if d==digit and abs(positions[p].x-root.x)<0.009
                   and abs(positions[p].y-root.y)<0.012]
            root.z = min(pad)+0.30*(max(pad)-min(pad))
            last_length=(self.new_joints[digit][-1]-self.new_joints[digit][-2]).length
            self.new_joints[digit]=[root.lerp(tip,t) for t in (0,0.46,0.75,1)]
            self.new_joints[digit].append(tip+axis*last_length)

    def measure_free_shafts(self, graph, positions):
        # Surface distance to the first independent finger loops avoids
        # capturing skin on the opposite wall of the thumb/index web.
        distances = dict.fromkeys(self.label,math.inf)
        queue = []
        for p in self.free_shafts:
            distances[p] = 0
            if any(q not in self.free_shafts for q in graph[p]):
                queue.append((0,p))
        heapq.heapify(queue)
        while queue:
            d,p=heapq.heappop(queue)
            if d!=distances[p] or d>=0.026:
                continue
            for q in graph[p]:
                if self.label.get(q)!=self.label[p]:
                    continue
                distance=d+(positions[q]-positions[p]).length
                if distance<distances[q]:
                    distances[q]=distance
                    heapq.heappush(queue,(distance,q))
        self.shaft_distance=distances

    def measure_thumb_web(self, graph, positions):
        # The thumb and index share a broad saddle. Both sides of its ownership
        # boundary need to approach Hand smoothly. A 3D nearest-bone distance
        # alone can jump across the folded surface here.
        distances = {p:math.inf for p in self.label}
        for p,digit in self.label.items():
            for q in graph[p]:
                if q in self.label and (self.label[q]=='Thumb') != (digit=='Thumb'):
                    distances[p] = min(distances[p], (positions[p]-positions[q]).length/2)
        queue = [(d,p) for p,d in distances.items() if math.isfinite(d)]
        heapq.heapify(queue)
        while queue:
            d,p = heapq.heappop(queue)
            if d!=distances[p] or d>=0.026:
                continue
            for q in graph[p]:
                if q not in distances:
                    continue
                candidate = d+(positions[p]-positions[q]).length
                if candidate<distances[q]:
                    distances[q] = candidate
                    heapq.heappush(queue,(candidate,q))
        self.thumb_web = distances

    def base(self, p):
        x = self.sign * p.x
        # The first ring that belongs to the forearm gets a sub-millimetre
        # rotation. The larger rotation is distributed through the wrist.
        fade = 0.008*smooth(0.251, 0.27, x) + 0.992*smooth(0.27, 0.309, x)
        twisted = self.wrist + Matrix.Rotation(self.roll*fade, 3, 'X') @ (p-self.wrist)
        # Pull the saddle of each web proximally, then recover length out
        # along the phalanges. A continuous field leaves all triangles attached.
        shift = 0.022*smooth(0.277, 0.344, x)*(1.0-smooth(0.36, 0.414, x))
        twisted.x -= self.sign*shift
        return twisted

    def digit_map(self, p, digit):
        root = self.base(self.joints[digit][0])
        return root + self.offset[digit] + self.rotation[digit] @ (self.base(p)-root)

    def geometry(self, p, digit):
        base = self.base(p)
        # Blend the local rotations into the common palm on the proximal side
        # of the web. Distal vertices follow one chain's transform completely.
        axis = (self.joints[digit][1]-self.joints[digit][0]).normalized()
        along = (p-self.joints[digit][0]).dot(axis)
        fade = smooth(-0.012, 0.014, along)
        if digit=='Thumb':
            fade *= smooth(0,0.023,self.thumb_web[tuple(p)])
        mapped = self.digit_map(p, digit)
        # Taper only the cross-finger dimension, about the nearest centerline.
        # The web and the dorsal/palmar thickness are retained.
        if digit != 'Thumb':
            joints = self.new_joints[digit]
            direction = self.front[digit]
            lateral = Vector((-direction.y, direction.x, 0)).normalized()
            nearest = min((a + (b-a)*max(0.0, min(1.0, (mapped-a).dot(b-a)/(b-a).length_squared))
                           for a,b in zip(joints, joints[1:])), key=lambda q: (mapped-q).length_squared)
            mapped -= lateral * (mapped-nearest).dot(lateral) * 0.055
        result = base.lerp(mapped, fade)
        # The source palm pad slopes sharply up to the MCPs. Ease its
        # underside toward the MCP pad height, retaining a rounded heel.
        pad = smooth(0.272,0.293,abs(p.x)) * (1-smooth(0.334,0.354,abs(p.x)))
        proximity = 1-smooth(0.037,0.055,abs(base.y-self.wrist.y))
        underside = 1-smooth(0.549,0.560,result.z)
        pad_height = 0.548-0.0015*smooth(0.298,0.332,abs(p.x))
        result.z += (pad_height-result.z)*0.96*pad*proximity*underside
        return result

    def weights(self, original, point, digit):
        chain = self.new_joints[digit]
        _, arc = sample_chain(point, chain)
        axis = (chain[1] - chain[0]).normalized()
        projection = (point - chain[0]).dot(axis)
        # Opposing web vertices must meet at a stable palm attachment before
        # bending toward their separate chains.
        own, _ = sample_chain(original, self.joints[digit])
        other = min(sample_chain(original, self.joints[d])[0] for d in DIGITS if d != digit)
        isolated = smooth(0.0, 0.012, other-own)
        branch = smooth(0.0, 0.021, projection)
        support = smooth(-0.023, 0.024, projection)
        if digit=='Thumb':
            support *= (isolated+(1-isolated)*branch)*(1-smooth(0.017,0.032,own))
        width = 0.026 if digit=='Thumb' else 0.012
        support *= smooth(0,width,self.thumb_web[tuple(original)])
        # Once the surface branches from the palm, release the palm bone
        # completely. Let support reach this endpoint from inside the web.
        shaft = self.shaft_distance[tuple(original)]
        web = self.thumb_web[tuple(original)]
        release = 1-smooth(0,0.026,shaft)
        if math.isfinite(web) and release:
            release *= smooth(0,1,web/(web+shaft))
        support += (1-support)*release
        widths = [(b-a).length for a,b in zip(chain,chain[1:])]
        weights = {self.prefix: 1-support}
        segment_weights = [1.0, 0.0, 0.0, 0.0]
        boundary = 0
        for i in range(3):
            boundary += widths[i]
            # A soft hinge spans both sides of the joint. The overlapping
            # intervals distribute a deep bend across several mesh rings.
            radius = 0.42*(widths[i]+widths[i+1])
            mix = smooth(boundary-radius, boundary+radius, arc)
            segment_weights[i] -= mix
            segment_weights[i+1] += mix
        for i,w in enumerate(segment_weights,1):
            weights[self.prefix+digit+str(i)] = support*w
        return {n:w for n,w in weights.items() if w>1e-8}


def refine_hand_surface(mesh):
    """Add one triangle split only in the hands for the 70-degree curl."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    source_face = bm.faces.layers.int.new('source_triangle')
    for index,face in enumerate(bm.faces):
        face[source_face] = index
    edges = [e for e in bm.edges if all(abs(v.co.x)>0.279 for v in e.verts)]
    bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
    bm.to_mesh(mesh)
    bm.free()
    # The same edge can occur twice at a UV seam with opposite traversal.
    # Canonicalize its floating point midpoint, without welding the UVs.
    tree = KDTree(len(mesh.vertices))
    for v in mesh.vertices:
        tree.insert(v.co,v.index)
    tree.balance()
    for v in mesh.vertices:
        if abs(v.co.x)>0.279:
            hits = tree.find_range(v.co,1e-7)
            v.co = min(hits,key=lambda hit:hit[1])[0]
    mesh.update()


def repair(body, arm):
    mesh = body.data
    assert body.matrix_world == arm.matrix_world == Matrix.Identity(4)
    encoded = mesh.attributes['custom_normal'].data
    source_normals = {(f.index,mesh.loops[i].vertex_index):tuple(encoded[i].value)
                      for f in mesh.polygons for i in f.loop_indices
                      if abs(mesh.vertices[mesh.loops[i].vertex_index].co.x)<=0.251}
    refine_hand_surface(mesh)
    original = [v.co.copy() for v in mesh.vertices]
    graph = defaultdict(set)
    for e in mesh.edges:
        a,b = [tuple(original[i]) for i in e.vertices]
        graph[a].add(b)
        graph[b].add(a)
    hands = [Hand(side, arm, graph) for side in ('Left','Right')]
    rest_positions = {tuple(p):p for p in original}
    for hand in hands:
        hand.measure_thumb_web(graph,rest_positions)
    # Preserve authored corner normals on the untouched mesh. On the repaired
    # patch use smooth surface normals across coincident UV-seam vertices.
    old_normals = [n.vector.copy() for n in mesh.corner_normals]
    for v,p in zip(mesh.vertices,original):
        if abs(p.x) <= 0.251:
            continue
        hand = hands[int(p.x < 0)]
        if abs(p.x) <= 0.27:
            v.co = hand.base(p)
            continue
        digit = hand.label[tuple(p)]
        v.co = hand.geometry(p, digit)
    # Relax the subdivided surface across UV splits before computing skin
    # weights. This rounds facet corners and the thin interdigit saddles.
    positions = {tuple(p):v.co.copy() for p,v in zip(original,mesh.vertices)}
    for strength in (0.68,0.57,0.45):
        relaxed = {}
        for key,point in positions.items():
            if abs(key[0])<=0.279:
                continue
            neighbors = graph[key]
            center = sum((positions[q] for q in neighbors),Vector())/len(neighbors)
            relaxed[key] = point.lerp(center,strength*smooth(0.279,0.313,abs(key[0])))
        positions.update(relaxed)
    for hand in hands:
        hand.fit_knuckles(positions)
        hand.measure_thumb_web(graph,positions)
        hand.measure_free_shafts(graph,positions)
    for v,p in zip(mesh.vertices,original):
        if abs(p.x)<=0.27:
            # Some master forearm vertices carry thumb weights, even near
            # the elbow. Preserve their neutral positions and transfer only
            # that stray influence to the forearm it actually belongs to.
            stray = [(g.group,g.weight) for g in v.groups
                     if 'Hand' in body.vertex_groups[g.group].name
                     and body.vertex_groups[g.group].name[-1].isdigit()]
            if stray:
                side = 'Left' if p.x>0 else 'Right'
                for group_id,_ in stray:
                    body.vertex_groups[group_id].remove([v.index])
                body.vertex_groups['mixamorig:'+side+'ForeArm'].add(
                    [v.index],sum(w for _,w in stray),'ADD')
            continue
        v.co = positions[tuple(p)]
        hand = hands[int(p.x < 0)]
        digit = hand.label[tuple(p)]
        weights = hand.weights(p, v.co, digit)
        # Preserve the original wrist transition into the forearm. Finger
        # groups begin inside the hand; wrist weights only mix Hand/ForeArm.
        forearm = hand.prefix.replace('Hand','ForeArm')
        forearm_weight = next((g.weight for g in v.groups if body.vertex_groups[g.group].name==forearm), 0)
        forearm_weight *= 1-smooth(0.27,0.294,abs(p.x))
        old_group_ids = [g.group for g in v.groups]
        for group_id in old_group_ids:
            body.vertex_groups[group_id].remove([v.index])
        weights = {n:w*(1-forearm_weight) for n,w in weights.items()}
        weights[forearm] = forearm_weight
        # Match Blender's glTF minimum influence so both assets keep the
        # same effective weights even at the very end of a blend interval.
        weights = {n:w for n,w in weights.items() if w>0.0001}
        total = sum(weights.values())
        for name,w in weights.items():
            if w>0:
                body.vertex_groups[name].add([v.index],w/total,'REPLACE')

    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    for hand in hands:
        for b in arm.data.edit_bones:
            if not b.name.startswith(hand.prefix):
                continue
            digit = b.name[len(hand.prefix):-1]
            h,t,z = b.head.copy(),b.tail.copy(),b.z_axis.copy()
            if b.name == hand.prefix:
                b.head,b.tail = hand.base(h),hand.base(t)
                roll_axis = hand.base(t+z*0.001)-hand.base(t)
            else:
                i=int(b.name[-1])-1
                b.head,b.tail = hand.new_joints[digit][i:i+2]
                roll_axis = hand.digit_map(t+z*0.001,digit)-hand.digit_map(t,digit)
            b.align_roll(roll_axis)
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh.update()
    normals = defaultdict(lambda: Vector((0,0,0)))
    for poly in mesh.polygons:
        for i in poly.vertices:
            if abs(original[i].x)>0.251:
                normals[tuple(original[i])] += poly.area * poly.normal
    for loop in mesh.loops:
        i = loop.vertex_index
        if abs(original[i].x)>0.251:
            blend = smooth(0.251,0.286,abs(original[i].x))
            old = old_normals[loop.index]
            old_normals[loop.index] = old.lerp(normals[tuple(original[i])].normalized(),blend).normalized()
    mesh.normals_split_custom_set(old_normals)
    encoded = mesh.attributes['custom_normal'].data
    parent_face = mesh.attributes['source_triangle'].data
    for f in mesh.polygons:
        for i in f.loop_indices:
            key = (parent_face[f.index].value,mesh.loops[i].vertex_index)
            if key in source_normals:
                encoded[i].value = source_normals[key]
    mesh.update()
    bpy.context.view_layer.update()


def build(source, output, glb):
    shutil.copyfile(source,output)
    bpy.ops.wm.open_mainfile(filepath=str(output),load_ui=False,use_scripts=False)
    body = bpy.data.objects['Base_Body']
    arm = bpy.data.objects['Armature']
    repair(body,arm)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.preferences.filepaths.file_preview_type = 'NONE'
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',
                              use_selection=True,export_skins=True,export_animations=False,
                              export_def_bones=False,export_influence_nb=4,
                              export_leaf_bone=False,export_rest_position_armature=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path, default=SOURCE, nargs='?')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    source = args.source.resolve()
    output = OUT/'hands_fixed.blend'
    glb = OUT/'base_body_handfix.glb'
    if source == output.resolve() or not source.is_file():
        raise ValueError('Provide the original, separate master blend')
    with tempfile.TemporaryDirectory(prefix='.hand-build-',dir=OUT) as staging:
        new_blend = Path(staging)/output.name
        new_glb = Path(staging)/glb.name
        build(source,new_blend,new_glb)
        if not new_glb.is_file() or not new_glb.stat().st_size:
            raise RuntimeError('Blender did not produce the skinned GLB')
        new_blend.replace(output)
        new_glb.replace(glb)


if __name__ == '__main__':
    main()
