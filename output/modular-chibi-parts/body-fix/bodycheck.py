"""Measure the master mesh against itself, using the shared action binding."""
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

OUT = Path(__file__).resolve().parent
MASTER = OUT.parent / 'master/GJH_Chibi_Master_rigged.blend'
SOURCE = OUT.parents[2] / 'models/tripo-chibi-motion/motion.glb'
CLIPS = ('walk', 'run', 'wave', 'jump', 'idle', 'nod', 'dance')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(motion=SOURCE):
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False)
    scene = bpy.context.scene
    arm = scene.objects['Armature']
    body = scene.objects['Base_Body']
    original = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(motion))
    incoming = set(scene.objects) - original
    source_arm, = [o for o in incoming if o.type == 'ARMATURE']
    assert set(source_arm.data.bones.keys()) == set(arm.data.bones.keys())
    for o in incoming:
        o.hide_viewport = o.hide_render = True
    arm.animation_data_create()
    return scene, arm, body, source_arm


def bind(arm, name):
    action = bpy.data.actions[name]
    arm.animation_data.action = action
    arm.animation_data.action_slot = action.slots[0]
    return range(round(action.frame_range[0]), round(action.frame_range[1]) + 1)


def posed(body):
    obj = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = obj.data
    points = np.empty(len(mesh.vertices)*3, dtype=np.float32)
    mesh.vertices.foreach_get('co', points)
    matrix = np.asarray(obj.matrix_world)
    return points.reshape(-1,3) @ matrix[:3,:3].T + matrix[:3,3]


def pair_depth(tri1, tri2):
    """Least separating translation in mm for each pair of zero-thickness triangles."""
    tri1=np.asarray(tri1,dtype=np.float64)
    tri2=np.asarray(tri2,dtype=np.float64)
    e1 = np.roll(tri1, -1, axis=1) - tri1
    e2 = np.roll(tri2, -1, axis=1) - tri2
    n1 = np.cross(e1[:,0], e1[:,1])
    n2 = np.cross(e2[:,0], e2[:,1])
    axes = np.concatenate([n1[:,None], n2[:,None],
                           np.cross(e1[:,:,None], e2[:,None,:]).reshape(-1,9,3)], axis=1)
    lengths = np.linalg.norm(axes, axis=2)
    valid = lengths > 1.e-16
    axes /= np.where(valid, lengths, 1)[:,:,None]
    local1 = tri1 - tri1[:,:1]
    local2 = tri2 - tri1[:,:1]
    p = np.einsum('ntc,nac->nat', local1, axes)
    q = np.einsum('ntc,nac->nat', local2, axes)
    separating = np.minimum(p.max(2) - q.min(2), q.max(2) - p.min(2))
    return np.maximum(np.min(np.where(valid, separating, np.inf),axis=1),0)*1000


class Checker:
    def __init__(self, body):
        self.body = body
        mesh = body.data
        mesh.calc_loop_triangles()
        self.faces = [t.vertices[:] for t in mesh.loop_triangles]
        self.indices = np.asarray(self.faces)
        self.index_sets = list(map(frozenset, self.faces))
        # The source duplicates vertices at chart boundaries. Weld exact rest
        # positions for adjacency testing only. The actual posed geometry is measured.
        vertex_ids = {}
        welded = [vertex_ids.setdefault(tuple(v.co), v.index) for v in mesh.vertices]
        self.surface_sets = [frozenset(welded[v] for v in tri) for tri in self.faces]
        weights = []
        for v in mesh.vertices:
            weights.append({body.vertex_groups[g.group].name.split(':')[-1]:g.weight
                            for g in v.groups if g.weight > 0})
        assert all(weights[i]==weights[j] for i,j in enumerate(welded)), "Split vertices have distinct weights"
        self.regions = []
        for face in self.faces:
            total = Counter()
            for i in face:
                total.update(weights[i])
            self.regions.append(total.most_common(1)[0][0])
        self.feet = {side: np.array([i for i,w in enumerate(weights)
                                     if max(w,key=w.get) in {side+'Foot',side+'ToeBase',side+'Toe_End'}])
                     for side in ('Left','Right')}
        self.foot_weights = {s:np.asarray([sum(v for k,v in weights[i].items()
                                                  if k in {s+'Foot',s+'ToeBase',s+'Toe_End'}) / sum(weights[i].values())
                                            for i in ids]) for s,ids in self.feet.items()}
        self.stats = {'vertices':len(mesh.vertices), 'unique_rest_positions':len(vertex_ids),
                      'triangles':len(self.faces), 'foot_vertex_counts':{k:len(v) for k,v in self.feet.items()}}

    def overlap(self, points, seam_ids=False):
        bvh = BVHTree.FromPolygons(points, self.faces, all_triangles=True, epsilon=0)
        overlap = bvh.overlap(bvh)
        raw = {(a,b) for a,b in overlap if a<b and self.index_sets[a].isdisjoint(self.index_sets[b])}
        surface = sorted((a,b) for a,b in raw if self.surface_sets[a].isdisjoint(self.surface_sets[b]))
        return surface, sorted(raw-set(surface)) if seam_ids else len(raw)-len(surface)

    def pair_records(self,points,pairs):
        region_pairs = defaultdict(list)
        if pairs:
            a,b = np.asarray(pairs).T
            depths = pair_depth(points[self.indices[a]], points[self.indices[b]])
            for (t,u), d in zip(pairs,depths):
                key = ' / '.join(sorted((self.regions[t],self.regions[u])))
                region_pairs[key].append([t,u,round(float(d),6)])
        return {key:{'count':len(vals),'max_depth_mm':max(v[2] for v in vals),
                     'triangles_and_depth_mm':vals} for key,vals in sorted(region_pairs.items())}

    def frame(self, frame):
        points=posed(self.body)
        pairs,seam=self.overlap(points,seam_ids=True)
        return {'frame':frame,'pairs':len(pairs),'seam_incident_pairs':len(seam),
                'index_only_pairs':len(pairs)+len(seam),
                'foot_min_z_mm':{s:float(points[ids,2].min()*1000) for s,ids in self.feet.items()},
                'region_pairs':self.pair_records(points,pairs),
                'seam_incident_region_pairs':self.pair_records(points,seam)}



def audit(motion, suffix):
    scene,arm,body,_ = load(motion)
    checker = Checker(body)
    report = {'master_sha256':sha(MASTER),'motion_sha256':sha(motion),
              'blender':bpy.app.version_string, 'fps':scene.render.fps, 'joints':sorted(arm.data.bones.keys()),
              **checker.stats, 'method':'Evaluated world triangles, epsilon-zero BVH, unique unordered pairs. Exclude triangles incident on the same exact rest position (including UV-split copies). seam_incident_pairs additionally counts non-index-adjacent pairs removed by that rule. Region = highest summed bone weight on the three corners. Depth = pair minimum separating translation via triangle SAT, mm, zero for tangency/coplanarity. IDs index master mesh loop_triangles. Feet = minimum world Z per side over foot/toe-dominant vertices.',
              'source_rest_pose':checker.frame('rest'), 'clips':{}}
    for clip in CLIPS:
        frames = []
        for fr in bind(arm,clip):
            scene.frame_set(fr)
            frames.append(checker.frame(fr))
        stats = {'frames':len(frames),'sum_pairs':sum(f['pairs'] for f in frames),
                 'peak_pairs':max(f['pairs'] for f in frames),
                 'overlapping_frames':sum(f['pairs']>0 for f in frames),
                 'max_depth_mm':max((r['max_depth_mm'] for f in frames for r in f['region_pairs'].values()),default=0)}
        print('AUDIT',clip,stats,flush=True)
        report['clips'][clip] = {**stats,'samples':frames}
    path = OUT / f'body_selfcheck_{suffix}.json'
    path.write_text(json.dumps(report,separators=(',',':'))+'\n')


if __name__ == '__main__':
    suffix = sys.argv[sys.argv.index('--')+1]
    audit(SOURCE if suffix=='before' else OUT/'motion_fixed.glb', suffix)
