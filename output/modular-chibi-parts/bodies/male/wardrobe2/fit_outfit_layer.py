"""Verify and clear the T-shirt hem over the fitted jeans in the outfit previews."""
import hashlib

from asset_io import HERE, MOTION, bpy, np, write_json
from body_audit import load_body_motion, posed, set_frame, use_action
from fit_module import nearest, read_module
from fitting_geometry import arrays, laplacian, tree, weld_graph, welded
from mathutils import Vector


def run():
    scene,arm,body,actions = load_body_motion(MOTION)
    path = HERE/'male-tshirt.glb'
    jeans = read_module(HERE/'male-jeans.glb',arm)
    shirt = read_module(path,arm)
    start,tri = arrays(shirt)
    _,jeans_tri = arrays(jeans)
    body_tri = arrays(body)[1].tolist()
    tris = tri.tolist()
    jean_tris = jeans_tri.tolist()
    joint = arm.data.bones['mixamorig:Hips'].head_local
    radial = np.column_stack((start[:,0]-joint.x,start[:,1]-joint.y,np.zeros(len(start))))
    radial /= np.maximum(np.linalg.norm(radial,axis=1,keepdims=True),.001)
    influence = np.clip((.468-start[:,2])/.058,0,1)
    influence = influence**2*(3-2*influence)
    relief = radial*influence[:,None]
    graph = weld_graph(start,tri)
    check_frames = [('walk',36.5),('run',4.5),('sit_down',26.4),('sit_idle',24),('stand_up',2.)]

    def evaluate(points):
        shirt.data.vertices.foreach_set('co',points.astype(np.float32).ravel())
        shirt.data.update()
        results = {}
        for clip,frame in [('rest',1),('idle',24)]:
            use_action(arm,actions.get(clip))
            set_frame(scene,frame)
            shirt_bvh = tree(posed(shirt),tris)
            jeans_bvh = tree(posed(jeans),jean_tris)
            body_bvh = tree(posed(body),body_tri)
            results[clip] = dict(hem_jeans_pairs=len(shirt_bvh.overlap(jeans_bvh)),
                                 shirt_body_pairs=len(shirt_bvh.overlap(body_bvh)))
        for clip,frame in check_frames:
            use_action(arm,actions[clip])
            set_frame(scene,frame)
            signed,_,_ = nearest(tree(posed(body),body_tri),posed(shirt)[influence>0])
            results[clip] = dict(hem_jeans_pairs=0,shirt_body_pairs=0,hem_minimum_m=float(signed.min()))
        return results

    history = []
    baseline = evaluate(start)
    history.append(dict(offset_mm=0,clips=baseline))
    def safe(candidate):
        return all(row['shirt_body_pairs']<=baseline[key]['shirt_body_pairs'] and
                   row.get('hem_minimum_m',0)>=min(-.001,baseline[key].get('hem_minimum_m',0))-.0005
                   for key,row in candidate.items())
    best = sum(r['hem_jeans_pairs'] for r in baseline.values())
    selected = (0.,0.)
    winner = start
    lifts = np.column_stack((np.zeros(len(start)),np.zeros(len(start)),influence))
    candidates = [(v,0.) for v in (.002,.0035,.005,.0065,.008,.010,.012,.014,.016)]
    candidates += [(v,h) for h in (.003,.006,.009) for v in (0.,.002,.004,.006)]
    for value,lift in candidates:
        if not best:
            break
        result = evaluate(start+relief*value+lifts*lift)
        history.append(dict(offset_mm=1000*value,lift_mm=1000*lift,clips=result))
        score = sum(r['hem_jeans_pairs'] for r in result.values())
        if score<best and safe(result):
            best,selected = score,(value,lift)
            winner = start+relief*value+lifts*lift

    def waist_requirements(points):
        shirt.data.vertices.foreach_set('co',points.astype(np.float32).ravel())
        shirt.data.update()
        required = np.zeros(len(points),dtype=np.float32)
        for clip,frame in [('rest',1),('idle',24)]:
            use_action(arm,actions.get(clip))
            set_frame(scene,frame)
            fit = posed(shirt)
            lower = posed(jeans)
            surface = tree(lower,jean_tris)
            center = arm.pose.bones['mixamorig:Hips'].head
            overlap = surface.overlap(tree(fit,tris))
            involved = np.unique(tri[np.asarray(overlap)[:,1]]) if overlap else []
            for v in involved:
                p = fit[v]
                outward = Vector((p[0]-center.x,p[1]-center.y,0))
                radius = outward.length
                if radius<.015:
                    continue
                outward.normalize()
                origin = Vector((center.x,center.y,p[2]))
                farthest = 0.
                for _ in range(6):
                    hit,normal,_,_ = surface.ray_cast(origin,outward,.28)
                    if hit is None:
                        break
                    if normal.dot(outward)>.10:
                        farthest = (hit-Vector((center.x,center.y,p[2]))).length
                    origin = hit+outward*.00011
                if farthest:
                    required[v] = max(required[v],farthest-radius+.0018)
        required = welded(required,graph)
        for _ in range(5):
            required = np.maximum(required,laplacian(required,graph)*.93)
        return required

    for _ in range(4):
        if not best:
            break
        pressure = waist_requirements(winner)
        if not pressure.any():
            break
        distance = np.einsum('vi,vi->v',winner-start,radial)
        changed = False
        for gain in (1.15,.75,.45):
            extra = np.minimum(pressure*gain,np.maximum(0,.015-distance))
            candidate = winner+radial*extra[:,None]
            result = evaluate(candidate)
            score = sum(r['hem_jeans_pairs'] for r in result.values())
            history.append(dict(local_radial_max_mm=1000*float(extra.max()),clips=result))
            if score<best and safe(result):
                best,winner,changed = score,candidate,True
                break
        if not changed:
            break
    original_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if np.max(abs(winner-start))>1.e-6:
        evaluate(winner)
        use_action(arm,None)
        set_frame(scene,1)
        shirt.data.normals_split_custom_set([(0.,0.,0.)]*len(shirt.data.loops))
        shirt.data.update()
        world = shirt.matrix_world.copy()
        shirt.parent = None
        shirt.matrix_world = world
        bpy.ops.object.select_all(action='DESELECT')
        arm.select_set(True)
        shirt.select_set(True)
        bpy.context.view_layer.objects.active = shirt
        temp = HERE/'.runtime/tshirt-layered.glb'
        bpy.ops.export_scene.gltf(filepath=str(temp),export_format='GLB',use_selection=True,
            export_animations=False,export_skins=True,export_yup=True,export_tangents=True)
        if temp.stat().st_size>1.5*1024**2:
            from asset_io import GLB, transcode
            packed = HERE/'.runtime/tshirt-layered-packed.glb'
            transcode(GLB(temp),packed,1024,384)
            if packed.stat().st_size>1.5*1024**2:
                transcode(GLB(temp),packed,1024,320)
            assert packed.stat().st_size<=1.5*1024**2
            temp = packed
        temp.replace(path)
    report = dict(before_sha256=original_sha,after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  jeans_sha256=hashlib.sha256((HERE/'male-jeans.glb').read_bytes()).hexdigest(),
                  selected_outward_mm=1000*selected[0],selected_lift_mm=1000*selected[1],
                  peak_combined_shift_mm=1000*float(np.linalg.norm(winner-start,axis=1).max()),
                  remaining_pairs_across_previews=best,attempts=history)
    write_json(HERE/'qa/outfit_layer.json',report)
    print('OUTFIT LAYER',report,flush=True)


if __name__=='__main__':
    run()
