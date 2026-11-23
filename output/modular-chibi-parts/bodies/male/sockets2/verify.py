"""Audit both pad contacts, bidirectional mesh penetration and chin clearance."""
import argparse
import hashlib

from parcel import *
from mesh_verification import penetration_report

PAD_LIMIT_MM = 2.
CHIN_LIMIT_MM = 10.


def close_faces(points, face_ids, opposing_points, radius):
    triangles = points[face_ids]
    lo, hi = opposing_points.min(0), opposing_points.max(0)
    outside = np.maximum(np.maximum(triangles.min(1)-hi, lo-triangles.max(1)),0.)
    return face_ids[(outside**2).sum(1)<=(radius+1e-8)**2]


def mesh_gap(p, patch, q, prop_faces, prop_tree, limit=None):
    patch = np.asarray(patch)
    prop_faces = np.asarray(prop_faces)
    coords = p[np.unique(patch)]
    if limit is None:
        head_tree = tree(p,patch)
        witness = min(head_tree.find_nearest(v)[3] for v in q)
        patch = close_faces(p, patch, q, witness)
        if not len(patch):
            return witness*1000
        coords = p[np.unique(patch)]
    else:
        witness = min(prop_tree.find_nearest(v)[3] for v in coords)
        if witness*1000 <= limit:
            return witness*1000
    if tree(p, patch).overlap(prop_tree):
        return 0.
    candidates = close_faces(q, prop_faces, coords, witness)
    if not len(candidates):
        return witness*1000
    return min(witness*1000, nearest_witness_mm(p,patch,q,candidates))


def audit(config, step, critical):
    replay = ParcelReplay(config)
    prop, _ = replay.prop(CLIP)
    local = bpy_pose(config['sockets'][CLIP])
    body_shells = list(closed_components(replay.rest,replay.body_faces))
    parcel_shells = list(closed_components(prop.points,prop.faces))
    chin = [face for face in replay.body_faces if any(replay.labels[i]=='Head' for i in face)]
    ticks = replay.times()
    timings = sorted(set(ticks[::step]) | {0.,replay.end_time} | set(critical))
    rows = []
    for i,t in enumerate(timings):
        p, right = replay.time(t)
        q = transform(prop.points,right@local)
        qt = tree(q,prop.faces)
        bt = tree(p,replay.body_faces)
        parts = [(p.min(0),p.max(0),bt)] if len(body_shells)==1 else prop_parts(p,body_shells)
        collision = penetration_report(p,replay.body_faces,bt,parts,q,prop.faces,qt,
                                       prop_parts(q,parcel_shells),certify=True)
        pad_gaps = {side+'_'+digit:mesh_gap(p,patch,q,prop.faces,qt,PAD_LIMIT_MM)
                    for (side,digit),patch in replay.pads.items()}
        # Every omitted triangle is at least 75 mm above the parcel.
        z = q[:,2].max()
        lower = [face for face in chin if min(p[v,2] for v in face)<=z+.075]
        gap = min(75.,mesh_gap(p,lower,q,prop.faces,qt)) if lower else 75.
        rows.append(dict(time_s=t,source_frame=t*24,pad_gap_upper_mm=pad_gaps,chin_clearance_mm=gap,
                         gltf_joint_replay_error_mm=replay.replay_error(t),
                         **collision))
        if i%25==0:
            print(i,t,round(max(pad_gaps.values()),4),round(collision['depth_mm'],4),
                  collision['depth_gate_certified'],round(gap,4),flush=True)
    gaps = {k:max(row['pad_gap_upper_mm'][k] for row in rows) for k in rows[0]['pad_gap_upper_mm']}
    max_depth = max(row['depth_mm'] for row in rows)
    chin_gap = min(row['chin_clearance_mm'] for row in rows)
    certified = all(row['depth_gate_certified'] for row in rows)
    summary = dict(samples=len(rows),max_pad_gap_upper_mm=gaps,
                   max_penetration_measured_mm=max_depth,
                   penetration_certified=certified,penetration_certified_upper_mm=1. if certified else None,
                   min_chin_clearance_mm=chin_gap,
                   max_gltf_joint_replay_error_mm=max(row['gltf_joint_replay_error_mm'] for row in rows),
                   passes=max(gaps.values())<=PAD_LIMIT_MM and max_depth<=1. and certified and chin_gap>=CHIN_LIMIT_MM)
    metadata = dict(body=BODY_NAME, clip=CLIP, source_fps=24, duration_s=replay.end_time,
                    sampled_full_grid=step==1, grid_hz=[48, 120 if BODY_NAME=='female' else 192, 480], limits_mm=dict(pad_gap_max=PAD_LIMIT_MM,
                    penetration_max=1.,chin_clearance_min=CHIN_LIMIT_MM),
                    inputs_sha256={path.name:hashlib.sha256(path.read_bytes()).hexdigest()
                                   for path in (SOCKET_FILE,BODY_FILE,BANK,PROPS[CLIP][0])})
    return dict(**metadata, summary=summary, frames=rows)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--step',type=int,default=1)
    parser.add_argument('--critical', type=float, nargs='+', default=[])
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    args = parser.parse_args(argv)
    result = audit(json.loads(SOCKET_FILE.read_text()),args.step,args.critical)
    path = HERE/('verification.json' if args.step==1 else 'verification-preview.json')
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(result['summary'],flush=True)
    if not result['summary']['passes']:
        raise SystemExit(2)
