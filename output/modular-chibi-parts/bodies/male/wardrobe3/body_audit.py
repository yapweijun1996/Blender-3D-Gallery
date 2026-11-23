"""Run the neutral bodycheck kernel against all male motion samples."""
import math
from collections import defaultdict
import sys

from asset_io import *
sys.path.insert(0,str(PARTS/'body-fix'))
from bodycheck import Checker, bind, posed, pair_depth
from mathutils import Matrix


def load_body_motion(path):
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False)
    scene = bpy.context.scene
    arm, body = scene.objects['Armature'], scene.objects['Base_Body']
    incoming = import_objects(path)
    source, = [o for o in incoming if o.type=='ARMATURE']
    assert {b.name:b.parent.name if b.parent else None for b in source.data.bones} == {
        b.name:b.parent.name if b.parent else None for b in arm.data.bones}
    actions = {a.name:a for a in bpy.data.actions}
    for o in incoming:
        bpy.data.objects.remove(o,do_unlink=True)
    arm.animation_data_create().use_nla = False
    return scene,arm,body,actions


def use_action(arm,action):
    arm.animation_data.action = None
    for bone in arm.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    if action:
        arm.animation_data.action = action
        arm.animation_data.action_slot = action.slots[0]


def set_frame(scene,frame):
    scene.frame_set(math.floor(frame),subframe=frame%1)


def frame_grid(action, fps=24, extra_fps=(30,)):
    first,last = action.frame_range
    grid = {float(first),float(last)}
    for rate in (fps,*extra_fps):
        max_step = math.floor((last-first)/fps*rate*2+1e-5)
        grid.update(min(last,first+n*fps/(rate*2)) for n in range(max_step+1))
    return sorted(grid)


def audit(path, outfile):
    sc,arm,body,actions = load_body_motion(path)
    checker = Checker(body)
    out = {'motion':str(path.name),'fps':sc.render.fps,'rest':checker.frame('rest'),'clips':{}}
    for clip in CLIPS:
        action = actions[clip]
        use_action(arm,action)
        regions = {}
        total = positive = worst_count = 0
        foot_min = {s:float('inf') for s in checker.feet}
        foot_max = {s:-float('inf') for s in checker.feet}
        contacts = []
        max_frame = None
        for frame in frame_grid(action):
            set_frame(sc,frame)
            pts = posed(body)
            height = {s:float(1000*pts[ids,2].min()) for s,ids in checker.feet.items()}
            for side,height_mm in height.items():
                foot_min[side] = min(foot_min[side],height_mm)
                foot_max[side] = max(foot_max[side],height_mm)
            contacts.append([round(frame,5),*[round(x,5) for x in height.values()]])
            pairs,_ = checker.overlap(pts)
            if not pairs: continue
            positive += 1
            total += len(pairs)
            if len(pairs)>worst_count:
                worst_count,max_frame = len(pairs),frame
            for zone,record in checker.pair_records(pts,pairs).items():
                result = regions.setdefault(zone,dict(pairs=0,frames=0,max_depth_mm=-1))
                result['pairs'] += record['count']
                result['frames'] += 1
                if record['max_depth_mm'] > result['max_depth_mm']:
                    result.update(max_depth_mm=record['max_depth_mm'],frame=round(frame,5))
        row = dict(samples=len(contacts),total_pairs=total,overlap_frames=positive,peak_pairs=worst_count,
                   peak_frame=max_frame,foot_min_mm=foot_min,foot_max_mm=foot_max,regions=regions,
                   foot_samples=contacts)
        out['clips'][clip] = row
        print('BODY',clip,total,positive,worst_count,max_frame,foot_min,regions,flush=True)
        write_json(outfile,out)


if __name__=='__main__':
    args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    audit(Path(args[0]) if args else MOTION, Path(args[1]) if len(args)>1 else HERE/'qa/body_selfcheck.json')
