"""Re-measure the male sockets from JSON and the original read-only assets."""
import argparse
import hashlib

from geometry import *


FILE = HERE/'sockets_male.json'
ATTACH_FRAME = 29
FPS = 24
DEPTH_LIMIT = .001
CONTACT_LIMIT_MM = 3.0


def moving_pose(cfg, clip, t, hand, repeat=False):
    key = 'jar' if clip == 'take_item' else clip
    if key != 'jar' or t >= cfg['shelf']['attachFrame']/FPS-1e-9:
        return hand @ bpy_pose(cfg['sockets'][key])
    shelf = cfg['shelf']
    pickup = bpy_pose(shelf['pickupStop'])
    if not repeat:
        return pickup
    release = bpy_pose(shelf['returnStop'])
    start, end = shelf['returnFrames']
    u = np.clip((t*FPS-start)/(end-start),0,1)
    weight = float(u*u*(3-2*u))
    a, qa, _ = release.decompose()
    b, qb, _ = pickup.decompose()
    return Matrix.LocRotScale(a.lerp(b, weight), qa.slerp(qb, weight), Vector((1,1,1)))


def asset_scene(replay, cfg, clip):
    prop, extra = replay.prop('sit_idle' if clip in CHAIR else clip)
    if clip in CHAIR:
        prop.obj.matrix_world = bpy_pose(cfg['chair'])
    for part in extra:
        part.obj.matrix_world = bpy_pose(cfg['shelf']['displayRail'])
    return prop, extra


def unsigned_gap(p, patch, q, prop_faces, prop_bvh):
    ids = np.unique(patch)
    witness = min(prop_bvh.find_nearest(p[i])[3] for i in ids)*1000
    if witness <= CONTACT_LIMIT_MM:
        return witness
    # A vertex witness already certifies a pass. Near the gate, include
    # prop-to-pad and edge-to-edge witnesses as well as crossing triangles.
    if tree(p, patch).overlap(prop_bvh):
        return 0.
    return nearest_witness_mm(p, patch, q, prop_faces)


def penetration_report(p, pf, bt, body_parts, q, qf, qt, prop_shells, certify=False):
    hits = bt.overlap(qt)
    bdep = inside_depth(p, prop_shells)
    qdep = inside_depth(q, body_parts)
    measured = max([0., *bdep.values(), *qdep.values()])
    certified = not (hits or bdep or qdep)
    if certify and not certified:
        # Refine triangles crossed by the opposing surface. Signed distance
        # is 1-Lipschitz per closed shell, so intervals bound unsampled depth.
        hit1 = {i for i, _ in hits}
        hit2 = {j for _, j in hits}
        for points, faces_, indices, parts, depths in (
                (p,pf,hit1,prop_shells,bdep),(q,qf,hit2,body_parts,qdep)):
            if depths:
                indices.update(i for i, f in enumerate(faces_) if any(j in depths for j in f))
            if indices:
                sub = np.array(faces_)[sorted(indices)]
                d, passed = certify_depth(points[sub], parts, DEPTH_LIMIT)
                measured = max(measured, d)
                if not passed:
                    break
        else:
            certified = measured <= DEPTH_LIMIT
    return dict(depth_mm=measured*1000, body_vertices_inside=len(bdep),
                prop_vertices_inside=len(qdep), triangle_pairs=len(hits), depth_gate_certified=certified)


def certify_depth(triangles, parts, limit):
    # Four-way subdivision reuses all dyadic sample points. Subdivision
    # stops at every triangle proven within the tolerance or a failing sample.
    peak = 0.
    for lo, hi, surface in parts:
        local = triangles[((triangles.max(1)>=lo)&(triangles.min(1)<=hi)).all(1)]
        cache = {}
        for _ in range(12):
            if not len(local):
                break
            corners = local.reshape(-1,3)
            key = [tuple(v) for v in corners]
            for v in set(key)-cache.keys():
                point = Vector(v)
                _, _, _, d = surface.find_nearest(point)
                cache[v] = d if d <= EPSILON_M or inside(point, surface) else -d
            depth = np.asarray([cache[k] for k in key]).reshape(-1,3)
            peak = max(peak, float(depth.max()))
            if peak > limit:
                return peak, False
            edge = np.linalg.norm(local-np.roll(local,1,axis=1),axis=2).max(1)
            # Each point is within at most 2/3 of the longest edge from
            # the nearest vertex. Use max + radius as a conservative bound.
            local = local[depth.max(1)+edge*(2/3)>limit]
            if len(local):
                a,b,c = local.transpose(1,0,2)
                x,y,z = (a+b)*.5,(b+c)*.5,(c+a)*.5
                local = np.concatenate([np.stack(q,axis=1) for q in ((a,x,z),(b,y,x),(c,z,y),(x,y,z))])
        else:
            return peak, False
    return peak, True


def chair_row(replay, prop, points, pp, parts, pt):
    body_tree = tree(points, replay.body_faces)
    depth = inside_depth(points, parts)
    row = {
        'vertices_inside': len(depth),
        'deepest_mm': max(depth.values(),default=0)*1000,
        'triangle_pairs': len(pt.overlap(body_tree)),
        'floor_min_mm': points[:,2].min()*1000,
    }
    # The seat is the horizontal patch at the author's 252 mm cushion top.
    top_face = [tri for tri in prop.faces if np.all(abs(prop.points[list(tri),2]-.252)<.00001)]
    seat = tree(pp, top_face)
    for side in SIDES:
        feet = replay.feet[side]
        for region, indices in feet.items():
            row[f'{side}_{region}_mm'] = points[indices,2].min()*1000
        row[f'{side}_foot_mm'] = min(row[f'{side}_{region}_mm'] for region in feet)
        support = points[replay.seat_mask(side, points)]
        row[f'{side}_seat_gap_mm'] = min(seat.find_nearest(p)[3] for p in support)*1000
    return row


def peak(rows, key):
    return max(rows, key=lambda row: row[key])[key]


def audit_chair(r, cfg, clip, prop, quick):
    unplaced = prop.obj.matrix_world.copy()
    all_rows = {}
    for label, matrix in [('origin', Matrix.Identity(4)), ('fitted', unplaced)]:
        prop.obj.matrix_world = matrix
        pp = bounds(prop, matrix)
        pt = tree(pp, prop.faces)
        parts = prop_parts(pp, closed_components(prop.points,prop.faces))
        r.select(clip)
        rows = []
        for t in r.times():
            if quick and not any(abs(t*n-round(t*n))<1e-6 for n in [2*SOURCE_FPS[clip],48]):
                if t != r.end_time:
                    continue
            p,_ = r.time(t)
            rows.append(dict(time_s=t, **chair_row(r, prop, p, pp, parts, pt)))
        seated = rows if clip == 'sit_idle' else rows[-1:] if clip == 'sit_down' else rows[:1]
        summary = {
            'samples': len(rows),
            'peak_vertices_inside': peak(rows,'vertices_inside'),
            'peak_triangle_pairs': peak(rows,'triangle_pairs'),
            'deepest_mm': peak(rows,'deepest_mm'),
            'min_body_floor_mm': min(row['floor_min_mm'] for row in rows),
            'max_seated_gap_mm': {side: peak(seated,f'{side}_seat_gap_mm') for side in SIDES},
            'max_foot_floor_error_mm': {side: max(abs(row[f'{side}_foot_mm']) for row in rows) for side in SIDES},
            'max_heel_floor_error_mm': {side: max(abs(row[f'{side}_heel_mm']) for row in rows) for side in SIDES},
        }
        summary['passes'] = (summary['peak_vertices_inside']==0 and summary['peak_triangle_pairs']==0
                              and summary['min_body_floor_mm']>=-1
                              and max(summary['max_seated_gap_mm'].values())<=2
                              and max(summary['max_foot_floor_error_mm'].values())<=1)
        all_rows[label] = dict(summary=summary, frames=rows)
    return all_rows


def audit_prop(r, cfg, clip, prop, extra, quick):
    r.select(clip)
    shell_indices = list(closed_components(prop.points, prop.faces))
    body_indices = list(closed_components(r.rest,r.body_faces))
    rail = []
    for static in extra:
        q = bounds(static, static.obj.matrix_world)
        rail.append((q, static.faces, tree(q, static.faces),
                    prop_parts(q, closed_components(static.points, static.faces))))
        deck_faces = [face for face in static.faces if np.all(abs(static.points[list(face),2]-.442)<.000002)]
        deck = tree(q, deck_faces)
        deck_up = np.asarray(static.obj.matrix_world.to_3x3().col[2].normalized())
    hands = SIDES if clip == 'hold_box' else SIDES[:1]
    points = []
    head = [face for face in r.body_faces if any(r.labels[i]=='Head' for i in face)] if clip=='hold_box' else []
    timings = r.times()
    if quick:
        timings = [t for t in timings if any(abs(t*n-round(t*n))<1e-6 for n in [2*SOURCE_FPS[clip],48])]
    for t in timings:
        p, hand = r.time(t)
        imported_hand = r.arm.matrix_world @ r.arm.pose.bones[N+'RightHand'].head
        bt = tree(p, r.body_faces)
        body_parts = [(p.min(0),p.max(0),bt)] if len(body_indices)==1 else prop_parts(p,body_indices)
        row = dict(time_s=t, source_frame=t*SOURCE_FPS[clip],
                   joint_head_replay_difference_mm=(hand.translation-imported_hand).length*1000)
        jar = clip == 'take_item'
        attached = not jar or t >= cfg['shelf']['attachFrame']/FPS-1e-9
        variants = ['first','repeat'] if not attached else ['attached']
        for mode in variants:
            q = bounds(prop, moving_pose(cfg,clip,t,hand,mode=='repeat'))
            qt = tree(q,prop.faces)
            parts = prop_parts(q, shell_indices)
            row[mode] = penetration_report(p,r.body_faces,bt,body_parts,q,prop.faces,qt,parts,certify=not quick)
            if jar and not attached:
                low = q[int(np.argmin(q @ deck_up))]
                hit, _, _, distance = deck.find_nearest(low)
                row[mode]['jar_to_deck_gap_mm'] = distance*1000
                row[mode]['jar_deck_signed_height_mm'] = (low-np.array(hit))@deck_up*1000
            if attached:
                row['gaps_mm'] = {side+'_'+digit:unsigned_gap(p,r.pads[side,digit],q,prop.faces,qt)
                                  for side in hands for digit in DIGITS}
            if clip == 'hold_box':
                z = q[:,2].max()
                chin = [face for face in head if min(p[i,2] for i in face)<=z+.075]
                if chin:
                    row['chin_gap_mm'] = 0. if tree(p,chin).overlap(qt) else min(
                        75., nearest_witness_mm(p,chin,q,prop.faces))
                else:
                    row['chin_gap_mm'] = 75.
        for q, qf, qt, parts in rail:
            row['display_rail'] = penetration_report(p,r.body_faces,bt,body_parts,q,qf,qt,parts,certify=not quick)
        points.append(row)
    collisions = [row[k] for row in points for k in ('attached','first','repeat','display_rail') if k in row]
    grip = [row['gaps_mm'] for row in points if 'gaps_mm' in row]
    summary = dict(samples=len(points), grip_samples=len(grip),
                   max_pad_gap_mm={key:peak(grip,key) for key in grip[0]},
                   max_penetration_mm=peak(collisions,'depth_mm'),
                   peak_triangle_pairs=peak(collisions,'triangle_pairs'),
                   peak_body_vertices_inside=peak(collisions,'body_vertices_inside'),
                   peak_prop_vertices_inside=peak(collisions,'prop_vertices_inside'),
                   penetration_certified=all(row['depth_gate_certified'] for row in collisions),
                   joint_head_replay_difference_mm=peak(points,'joint_head_replay_difference_mm'))
    summary['passes'] = (max(summary['max_pad_gap_mm'].values())<=CONTACT_LIMIT_MM
                         and summary['max_penetration_mm']<=DEPTH_LIMIT*1000
                         and summary['penetration_certified'])
    if clip == 'hold_box':
        summary['min_chin_gap_mm'] = min(row['chin_gap_mm'] for row in points)
        summary['passes'] &= summary['min_chin_gap_mm']>=10
    if clip == 'take_item':
        shelf = cfg['shelf']
        p, hand = r.time(shelf['attachFrame']/FPS)
        q = bounds(prop,bpy_pose(shelf['pickupStop']))
        qp = bounds(prop,moving_pose(cfg,clip,shelf['attachFrame']/FPS,hand))
        qt = tree(q,prop.faces)
        summary['pickup_pad_gap_mm'] = {d:unsigned_gap(p,r.pads['Right',d],q,prop.faces,qt) for d in DIGITS}
        summary['pickup_handoff_vertex_snap_mm'] = np.linalg.norm(q-qp,axis=1).max()*1000
        thumb,index = [p[np.unique(r.pads['Right',d]),:2] for d in DIGITS]
        axis = index.mean(0)-thumb.mean(0)
        axis /= np.linalg.norm(axis)
        separation = (index@axis).min()-(thumb@axis).max()
        width = 2*np.linalg.norm(prop.points[:,:2],axis=1).max()
        summary['upright_jar_pad_separation_lower_bound_mm'] = separation*1000
        summary['upright_jar_width_upper_bound_mm'] = width*1000
        _, hand_end = r.time(r.end_time)
        endpoint = bounds(prop,moving_pose(cfg,clip,r.end_time,hand_end))
        freed = bounds(prop,bpy_pose(shelf['returnStop']))
        summary['release_frame'] = shelf['releaseFrame']
        summary['release_vertex_snap_mm'] = np.linalg.norm(endpoint-freed,axis=1).max()*1000
        free = [row[k] for row in points for k in ('first','repeat')
                if k in row and 'jar_to_deck_gap_mm' in row[k]]
        summary['max_jar_to_deck_gap_mm'] = peak(free, 'jar_to_deck_gap_mm')
        summary['max_jar_below_deck_mm'] = max(0., -min(row['jar_deck_signed_height_mm'] for row in free))
        summary['max_attached_penetration_mm'] = max(row['attached']['depth_mm'] for row in points if 'attached' in row)
        jar_rows = [row[k] for row in points for k in ('first','repeat','attached') if k in row]
        summary['max_jar_body_penetration_mm'] = peak(jar_rows, 'depth_mm')
        summary['jar_body_penetration_certified'] = all(row['depth_gate_certified'] for row in jar_rows)
        summary['max_rail_body_penetration_mm'] = max(row['display_rail']['depth_mm'] for row in points)
        summary['passes'] &= (max(summary['pickup_pad_gap_mm'].values())<=CONTACT_LIMIT_MM
                              and summary['pickup_handoff_vertex_snap_mm']<=CONTACT_LIMIT_MM
                              and summary['release_vertex_snap_mm']<=CONTACT_LIMIT_MM
                              and summary['max_jar_to_deck_gap_mm']<=2
                              and summary['max_jar_below_deck_mm']<=1
                              and shelf['attachFrame']==ATTACH_FRAME and shelf['releaseFrame']==0)
    return dict(summary=summary, frames=points)


def source_contract(replay):
    """The motion and gesture banks must use the same male joints and bind TRS."""
    body = GLB(BODY)
    gestures = GLB(MALE/'hand_gestures_male.glb')
    joint_names = set(body.ids)
    assert len(joint_names)==65
    for asset in (replay.motion, gestures):
        assert joint_names == set(asset.ids)
        for name in joint_names:
            assert asset.nodes[asset.parents[asset.ids[name]]]['name'] == body.nodes[body.parents[body.ids[name]]]['name']
            assert all(asset.nodes[asset.ids[name]].get(key) == body.nodes[body.ids[name]].get(key)
                       for key in ('translation', 'rotation', 'scale'))
    with bpy.data.libraries.load(str(MALE/'master_male.blend'),link=False) as (source, target):
        assert 'Base_Body' in source.objects
        target.objects = ['Base_Body']
    master, = target.objects
    master_delta = float(np.abs(vertices(master)-replay.rest).max())
    bpy.data.objects.remove(master, do_unlink=True)
    assert master_delta<.000001
    return dict(joints=len(joint_names), master_bind_vertex_delta_mm=master_delta*1000,
                gesture_clips=len(gestures.doc['animations']), pose_source=MOTION.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quick', action='store_true', help='Only check author/demo half-frames, skip depth bounds')
    parser.add_argument('--clips', nargs='+', choices=(*CARRY,*CHAIR))
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    cfg = json.loads(FILE.read_text())
    assert cfg['bone']=='mixamorig:RightHand'
    for name in ('hold_item','hold_box','hold_bag','jar'):
        sock = cfg['sockets'][name]
        assert len(sock['translation'])==3 and len(sock['rotation'])==4
        assert np.isfinite([*sock['translation'],*sock['rotation']]).all()
        assert abs(np.linalg.norm(sock['rotation'])-1)<.00001
    result = dict(body_sha256=hashlib.sha256(BODY.read_bytes()).hexdigest(),
                  motion_sha256=hashlib.sha256(MOTION.read_bytes()).hexdigest(),
                  sockets_sha256=hashlib.sha256(FILE.read_bytes()).hexdigest(), clips={})
    r = Replay()
    result['source_contract'] = source_contract(r)
    selected = args.clips or (*CARRY,*CHAIR)
    for clip in selected:
        prop,extra = asset_scene(r,cfg,clip)
        if clip in CHAIR:
            row = audit_chair(r,cfg,clip,prop,args.quick)
        else:
            row = audit_prop(r,cfg,clip,prop,extra,args.quick)
        result['clips'][clip] = row
        print('VERIFY',clip,{k:v['summary'] for k,v in row.items()} if clip in CHAIR else row['summary'],flush=True)
        for item in [prop,*extra]:
            bpy.data.objects.remove(item.obj,do_unlink=True)
    result['passes'] = all((v['fitted'] if k in CHAIR else v)['summary']['passes']
                           for k,v in result['clips'].items())
    outfile = 'verification.json' if not (args.quick or args.clips) else 'verification_subset.json'
    (HERE/outfile).write_text(json.dumps(result,indent=2,default=lambda v:v.item())+'\n')
    if not result['passes']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
