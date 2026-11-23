"""Local clearance repair for the Round 2 Studio A-line dress in Blender 5.1."""
import json
import math
from pathlib import Path
import runpy
import sys

import bpy
import bmesh
import numpy as np
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
R2 = runpy.run_path(str(HERE.parent / "round2/fit_dress_r2.py"))
R1 = R2["PREVIOUS"]
MASTER = R2["MASTER"]
MOTION = MASTER.parent.parent / "body-fix/motion_fixed.glb"
SEED = HERE.parent / "round2/dress_v2.glb"
GLB = HERE / "dress_v3.glb"
BLEND = HERE / "dress_v3.blend"
MARGIN = .002
FLOOR = .0005
CAP = .03
CLIPS = R2["CLIPS"]
R1["setup_motion"].__globals__["MOTION"] = MOTION
mesh_points = R2["mesh_points"]
clearance = R2["clearance"]
triangulation = R2["triangulation"]
set_pose = R2["set_pose"]
cache_samples = R2["cache_samples"]
read_weights = R2["read_weights"]
section = R1["section"]


def baseline():
    scene, arm, body, garment = R1["read_export"](SEED)
    points = mesh_points(garment.data)
    triangles = triangulation(garment)
    names = tuple(bone.name for bone in arm.data.bones)
    samples, _, posed = cache_samples(scene, arm, body, names, garment=garment)
    reports, *_ = R1["scan"](points, triangles, samples, posed, report=True,
                             body_names=R1["zone_names"](body, names))
    R1["report_status"](reports)
    (HERE / ".baseline.json").write_text(json.dumps(reports, indent=2) + "\n")


SEED_BLEND = SEED.with_suffix(".blend")
ITERATIONS = 16


def fit_scene():
    scene, arm, body = R1["open_master"]()
    with bpy.data.libraries.load(str(SEED_BLEND)) as (source, target):
        assert "Dress" in source.objects
        target.objects = ["Dress"]
    garment, = target.objects
    scene.collection.objects.link(garment)
    garment.parent = arm
    for modifier in garment.modifiers:
        if modifier.type == "ARMATURE":
            modifier.object = arm
    R1["setup_motion"](scene, arm, body, garment)
    return scene, arm, body, garment


def constraints(points, weights, columns, triangles, samples, matrices, details=False):
    """Linearize the dense pose contacts in rest position and skin weights."""
    posed, skin = R2["skin_poses"](points, weights, columns, matrices)
    faces = triangles.tolist()
    regions = section(points)
    rows, gradients, deficits = [], [], []
    hits = np.zeros(len(triangles), dtype=np.int32)
    summary = {}
    worst = np.full(len(points), MARGIN, dtype=np.float32)
    worst_ray = np.zeros_like(points)
    scale = 10.
    for f, (clip, frame, tree, body, body_faces) in enumerate(samples):
        p = posed[f]
        signed, normal, nearest = clearance(tree, p)
        overlap = np.asarray(tree.overlap(BVHTree.FromPolygons(p.tolist(), faces, all_triangles=True)),
                             dtype=np.int32).reshape(-1, 2)
        v = int(signed.argmin())
        note = summary.setdefault(clip, {"samples": 0, "inside": 0, "pairs": 0,
                                         "min_m": 1., "total_pairs": 0})
        note["samples"] += 1
        note["inside"] = max(note["inside"], int((signed < 0).sum()))
        note["pairs"] = max(note["pairs"], len(overlap))
        note["total_pairs"] += len(overlap)
        if signed[v] < note["min_m"]:
            note.update(min_m=float(signed[v]), min_frame=frame, zone=str(regions[v]),
                        xyz=np.round(points[v]*1000,1).tolist())
        if len(overlap):
            np.add.at(hits, overlap[:, 1], 1)
        if details:
            # On each vertex retain its largest sampled deficit and the ray
            # to the closest body point, transported back through the skin.
            deeper = np.flatnonzero(signed < worst)
            for vertex in deeper:
                loc, n, _, _ = tree.find_nearest(p[vertex].tolist())
                ray = np.asarray(loc) - p[vertex]
                if signed[vertex] >= 0:
                    ray = -ray
                length = np.linalg.norm(ray)
                worst_ray[vertex] = (ray / length if length > 1e-8 else n) @ skin[f,vertex,:,:3]
            worst[deeper] = signed[deeper]
        target = .0008 if f == 0 else MARGIN
        active = np.flatnonzero(signed < target)
        ids = np.zeros((len(active), 3), dtype=np.int32)
        ids[:, 0] = active
        bary = np.zeros((len(active), 3), dtype=np.float32)
        bary[:, 0] = 1
        n = normal[active]
        gap = target - signed[active]
        if f == 0:
            high = np.flatnonzero(signed > CAP - .002)
            high_ids = np.zeros((len(high),3),dtype=np.int32)
            high_ids[:,0] = high
            high_bary = np.zeros((len(high),3),dtype=np.float32)
            high_bary[:,0] = 1
            ids = np.concatenate((ids, high_ids))
            bary = np.concatenate((bary, high_bary))
            n = np.concatenate((n, -normal[high]))
            gap = np.r_[gap, signed[high] - (CAP - .00015)]
        if len(overlap):
            tf, coeff = R1["pair_witnesses"](p, triangles, body, body_faces, overlap[:,::-1])
            corners = triangles[tf]
            locations = np.einsum("nk,nki->ni", coeff, p[corners])
            d, normals, _ = clearance(tree, locations)
            # Keep the three strongest contacts on a face to prevent dense
            # body triangulation from overweighting a single intersection.
            order = np.lexsort((d,tf))
            starts = np.flatnonzero(np.r_[True,np.diff(tf[order])!=0])
            keep = order[(np.arange(len(order))-np.repeat(starts,np.diff(np.r_[starts,len(order)])))<3]
            keep = keep[d[keep] < target]
            ids = np.vstack((ids,corners[keep]))
            bary = np.vstack((bary,coeff[keep]))
            n = np.vstack((n,normals[keep]))
            gap = np.r_[gap,target-d[keep]]
        if not len(gap):
            continue
        gx = np.einsum("ni,nkij->nkj",n,skin[f,ids,:,:3])
        mats = matrices[f,columns[ids]]
        moved = np.einsum("nkbic,nkc->nkbi",mats[...,:3],points[ids])+mats[...,3]
        gw = np.einsum("ni,nkbi->nkb",n,moved-p[ids][:,:,None,:])
        gw -= gw.mean(axis=-1,keepdims=True)
        grad = np.concatenate((gx,scale*gw),axis=2) * bary[...,None]
        rows.append(ids)
        gradients.append(grad)
        deficits.append(gap)
    return summary, hits, np.concatenate(rows), np.concatenate(gradients), np.concatenate(deficits), worst, worst_ray


def display(label, report):
    print(label, [(name,r["inside"],r["pairs"],round(r["min_m"]*1000,3),r["min_frame"],r["zone"])
                  for name,r in report.items()], flush=True)


def score(report):
    return (sum(r["total_pairs"] for r in report.values())*.0005
            + sum(max(0.,FLOOR-r["min_m"])**2 * 1e6 for r in report.values())
            + sum(r["inside"] for r in report.values())*.08)


def optimize(ids, gradient, deficit, points, offset, weights, columns, links, ray, worst, iteration):
    """Fit the required world-space displacements with a regularized local solve."""
    active = np.unique(ids[abs(gradient).max(axis=2) > 1e-6])
    expanded = np.zeros(len(points),dtype=bool)
    expanded[active] = True
    source, dest, _ = links
    for _ in range(2):
        expanded[dest[expanded[source]]] = True
    bake = ray*np.clip(MARGIN-worst,0,CAP)[:,None]
    neighbor = R2["average"]
    for _ in range(3):
        mean = neighbor(bake,links)
        # Preserve the worst-frame normal component of each required offset.
        bake += .34*(mean-bake)
        unit = ray / np.linalg.norm(ray,axis=1,keepdims=True).clip(1e-8)
        correction = np.maximum(0,np.clip(MARGIN-worst,0,CAP)
                                -np.einsum("vi,vi->v",bake,unit))
        bake += correction[:,None]*unit
    flat_ids = ids.ravel()
    flat_grad = gradient.reshape(-1,7)
    # Absolute row sums give a bound for a Jacobi-preconditioned gradient step.
    sums = np.abs(gradient).sum(axis=(1,2))
    diagonal = np.stack([np.bincount(flat_ids,weights=np.abs(g)*np.repeat(sums,3),
                                    minlength=len(points)) for g in flat_grad.T],axis=1)
    regularity = np.array([.17,.17,.17,.13,.13,.13,.13])
    smoothing = np.array([.47,.47,.47,.26,.26,.26,.26])
    diagonal += 2*smoothing + regularity
    trial = np.zeros((len(points),7),dtype=np.float32)
    trial[:,:3] = bake*.24
    current = trial.copy()
    for k in range(72):
        remainder = deficit - np.einsum("nki,nki->n",gradient,trial[ids])
        factor = np.repeat(remainder.clip(0),3)
        pull = np.stack([np.bincount(flat_ids,weights=factor*g,minlength=len(points))
                         for g in flat_grad.T],axis=1)
        combined = trial.copy()
        combined[:,:3] += offset
        pull += smoothing*(neighbor(combined,links)-combined)
        pull -= regularity*trial
        proposal = trial + (pull/diagonal).astype(np.float32)
        proposal[~expanded] = 0
        step_cap = .010 if iteration < 5 else .006
        proposal[:,:3] = R2["bound_delta"](proposal[:,:3],step_cap)
        proposal[:,3:] = (R2["simplex"](weights+proposal[:,3:]*10.)-weights)/10.
        trial = proposal + (k/(k+3.))*(proposal-current)
        current = proposal
    return current[:,:3], current[:,3:]*10.


def fit():
    scene, arm, body, garment = fit_scene()
    names = tuple(bone.name for bone in arm.data.bones)
    points = mesh_points(garment.data)
    original = points.copy()
    weights = read_weights(garment, names)
    coefficients, columns = R2["sparse_weights"](weights)
    samples, matrices = cache_samples(scene, arm, body, names)
    R2["export"].__globals__.update(GLB=GLB, BLEND=BLEND)
    mesh = garment.data
    triangles = triangulation(garment)
    links = R2["neighbors"](mesh)
    rest = samples[0][2]
    history = []
    best_score = float("inf")
    for i in range(ITERATIONS+1):
        report, hits, ids, grad, gap, worst, ray = constraints(
            points, coefficients, columns, triangles, samples, matrices, details=True)
        display(f"SWEEP {i}",report)
        history.append(report)
        (HERE/".iterations.json").write_text(json.dumps(history,indent=2)+"\n")
        value = score(report)
        passed = all(r["inside"]==r["pairs"]==0 and r["min_m"]>=FLOOR for r in report.values())
        if value < best_score or passed:
            best_score = value
            R2["export"](scene,arm,body,garment,points,
                         R2["full_weights"](coefficients,columns,len(names)),names)
        if i == ITERATIONS or passed:
            break
        step, change = optimize(ids,grad,gap,points,points-original,coefficients,columns,links,ray,worst,i)
        print("STEP MM",round(float(np.linalg.norm(step,axis=1).max())*1000,3),
              "WEIGHT",round(float(np.abs(change).max()),3),flush=True)
        points = R2["rest_guard"](R2["project_rest"](points + step, original, rest),
                                  points, original, triangles, rest)
        coefficients = R2["simplex"](coefficients+change)


def check():
    """Run each supplied checker on both frame phases and both endpoints."""
    from contextlib import redirect_stdout
    from io import StringIO

    schedule = '''    for fr in clip_frames(a):
        sc.frame_set(math.floor(fr), subframe=fr % 1)
        i,m=measure()
        worst=max(worst,i)
        mn=min(mn,m)
        frames[name].append([float(fr),i,m])
    res[name]=(worst,mn)
'''
    initialization = "    worst=0;mn=9\n    frames[name]=[]\n"
    for stem in ("motion_check", "motion_check_tri"):
        path = HERE.parent / "round2" / f"{stem}.py"
        source = path.read_text().split("sc.render.engine=",1)[0]
        start = source.index("    f0,f1=a.frame_range")
        stop = source.index("for k,v in res.items():")
        source = source[:start] + initialization + schedule + source[stop:]
        source = source.replace("sc.frame_set(1);arm.animation_data.action=None;bpy.context.view_layer.update()",
                                "arm.animation_data.action=None\nfor bone in arm.pose.bones: bone.matrix_basis.identity()\n"
                                "sc.frame_set(1);bpy.context.view_layer.update()")
        source = source.replace("res['rest']=measure()","res['rest']=measure()\nframes['rest']=[[1.,*res['rest']]]")
        source = source.replace("if not a:continue","assert a is not None, name")
        namespace = {"__name__":"__main__", "clip_frames": clip_frames, "frames": {}}
        old_argv = sys.argv
        sys.argv = [str(path),"--",str(MASTER),str(MOTION),str(GLB),str(HERE)]
        output = StringIO()
        try:
            with redirect_stdout(output):
                exec(compile(source,str(path),"exec"),namespace)
        finally:
            sys.argv = old_argv
        result = "\n".join(line for line in output.getvalue().splitlines()
                           if line.startswith("RESULT "))
        (HERE/f"{stem}.txt").write_text(result+"\n")
        report = {
            "glb_sha256": R2["sha"](GLB), "master_sha256": R2["sha"](MASTER),
            "motion_sha256": R2["sha"](MOTION), "blender": bpy.app.version_string,
            "frame_columns": ["frame", "triangle_pairs" if stem.endswith("_tri")
                              else "vertices_inside", "minimum_signed_m"],
            "results": namespace["res"], "frames": namespace["frames"],
        }
        (HERE/f"{stem}.json").write_text(json.dumps(report,indent=2)+"\n")
        print(result,flush=True)


def clip_frames(action):
    first, last = map(lambda value: round(value, 5), action.frame_range)
    return sorted({first, last, *(step/2 for step in range(math.ceil(first*2),math.floor(last*2)+1))})


def compare_body_baseline():
    path = MOTION.parent / "body_selfcheck_after.json"
    reference = json.loads(path.read_text())
    assert reference["master_sha256"] == R2["sha"](MASTER)
    assert reference["motion_sha256"] == R2["sha"](MOTION)
    scene, arm, body, garment = R1["read_export"](GLB)
    audit = runpy.run_path(str(MOTION.parent/"bodycheck.py"))
    body_checker = audit["Checker"](body)
    garment_faces = triangulation(garment)
    garment_face_list = garment_faces.tolist()
    garment_regions = section(mesh_points(garment.data)[garment_faces].mean(axis=1))
    results = {}
    garment_results = {}
    for clip in ("rest", *CLIPS):
        frames = [1.] if clip == "rest" else clip_frames(bpy.data.actions[clip])
        counts = []
        reference_rows = ([reference["source_rest_pose"]] if clip == "rest"
                          else reference["clips"][clip]["samples"])
        baseline_pairs = {
            (1. if clip=="rest" else row["frame"]): {
                (a,b) for region in row["region_pairs"].values()
                for a,b,_ in region["triangles_and_depth_mm"]
            } for row in reference_rows
        }
        matches = True
        garment_regions_found = {}
        for frame in frames:
            set_pose(scene,arm,clip,frame)
            body_points = audit["posed"](body)
            body_pairs, _ = body_checker.overlap(body_points)
            counts.append([frame,len(body_pairs)])
            if frame in baseline_pairs:
                matches &= set(body_pairs) == baseline_pairs[frame]
            body_tree = BVHTree.FromPolygons(body_points.tolist(),body_checker.faces,all_triangles=True)
            garment_points = audit["posed"](garment)
            dress_tree = BVHTree.FromPolygons(garment_points.tolist(),garment_face_list,all_triangles=True)
            intersections = body_tree.overlap(dress_tree)
            if intersections:
                b,g = np.asarray(intersections).T
                depths = audit["pair_depth"](body_points[body_checker.indices[b]],
                                             garment_points[garment_faces[g]])
                for body_face,garment_face,depth in zip(b,g,depths):
                    zone = f"{garment_regions[garment_face]} / {body_checker.regions[body_face]}"
                    detail = garment_regions_found.setdefault(zone, {"occurrences":0, "max_separation_mm":-1})
                    detail["occurrences"] += 1
                    if depth > detail["max_separation_mm"]:
                        detail.update(max_separation_mm=float(depth),frame=frame)
        actual = [amount for frame, amount in counts if float(frame).is_integer()]
        expected = ([reference["source_rest_pose"]["pairs"]] if clip == "rest" else
                    [row["pairs"] for row in reference["clips"][clip]["samples"]])
        results[clip] = {"integer_occurrences":sum(actual),
                         "half_frame_occurrences":sum(amount for frame,amount in counts
                                                      if not float(frame).is_integer()),
                         "baseline_integer_occurrences":sum(expected),
                         "matches_every_baseline_integer_frame":actual==expected,
                         "matches_baseline_triangle_ids":matches,
                         "frames":counts}
        garment_results[clip] = garment_regions_found
    return results, garment_results


def verify():
    for key in ("verify", "render", "glb_structure"):
        R2[key].__globals__.update(HERE=HERE, GLB=GLB, BLEND=BLEND)
    R2["verify"]()
    path = HERE/"dense_check.json"
    report = json.loads(path.read_text())
    doc, binary = R2["glb_metadata"](GLB)
    old, old_binary = R2["glb_metadata"](SEED)
    body_only, garment_contacts = compare_body_baseline()
    report.update({
        "master_sha256":R2["sha"](MASTER), "motion_sha256":R2["sha"](MOTION),
        "round2_glb_sha256":R2["sha"](SEED), "round2_blend_sha256":R2["sha"](SEED_BLEND),
        "round2_material_identical":doc["materials"]==old["materials"],
        "round2_texture_bytes_identical":R2["embedded_textures"](doc,binary)==
                                         R2["embedded_textures"](old,old_binary),
        "body_only":body_only, "garment_triangle_contacts_by_zone":garment_contacts,
        "round2_uv_corners_preserved":uv_audit(doc,binary,old,old_binary),
    })
    baseline_path = HERE/".baseline.json"
    if baseline_path.exists():
        report["round2_results_with_corrected_motion"] = json.loads(baseline_path.read_text())
    history_path = HERE/".iterations.json"
    if history_path.exists():
        report["fit_iterations"] = json.loads(history_path.read_text())
    history_path = HERE/".loft_iterations.json"
    if history_path.exists():
        report["local_loft_iterations"] = json.loads(history_path.read_text())
    path.write_text(json.dumps(report,indent=2)+"\n")


def uv_audit(document, binary, original, original_binary):
    def chart(doc, data):
        attribute = doc["meshes"][0]["primitives"][0]["attributes"]["TEXCOORD_0"]
        accessor = doc["accessors"][attribute]
        view = doc["bufferViews"][accessor["bufferView"]]
        assert accessor["componentType"] == 5126 and accessor["type"] == "VEC2"
        start = view.get("byteOffset",0) + accessor.get("byteOffset",0)
        values = np.ndarray((accessor["count"],2),dtype="<f4",buffer=data,offset=start,
                            strides=(view.get("byteStride",8),4))
        return set(map(tuple,np.round(values.astype(np.float64),7)))
    before, after = chart(original,original_binary), chart(document,binary)
    return {"round2_unique":len(before),"retained":len(before & after),
            "added":len(after-before)}


def render():
    # Use the raised-hand point of wave. The other plates use their
    # minimum-clearance timestamps for close inspection.
    configs = R2["render"].__globals__
    configs.update(HERE=HERE, GLB=GLB)
    original = configs["set_pose"]
    wave_frame = 19.
    def capture_pose(scene,arm,clip,frame):
        original(scene,arm,clip,wave_frame if clip=="wave" else frame)
    configs["set_pose"] = capture_pose
    try:
        R2["render"]()
    finally:
        configs["set_pose"] = original
    path = HERE/"dense_check.json"
    report = json.loads(path.read_text())
    report["render"]["frames"]["wave"] = wave_frame
    path.write_text(json.dumps(report,indent=2)+"\n")


def contact_field(points, triangles, samples, posed):
    """Measure the collision field used to place the local loft controls."""
    faces = triangles.tolist()
    deficits = np.zeros((len(samples),len(points)),dtype=np.float32)
    severity = np.zeros_like(deficits)
    hits = np.zeros(len(triangles),dtype=np.int32)
    clip_hits = {}
    for f,(clip,frame,tree,*_) in enumerate(samples):
        signed = clearance(tree,posed[f])[0]
        deficits[f] = np.maximum(.00155-signed,0)
        severity[f] = np.maximum(.00085-signed,0)
        pairs = np.asarray(tree.overlap(BVHTree.FromPolygons(posed[f].tolist(),faces,all_triangles=True)),
                           dtype=np.int32).reshape(-1,2)
        if len(pairs):
            np.add.at(hits,pairs[:,1],1)
            np.add.at(severity[f],triangles[np.unique(pairs[:,1])].ravel(),.001)
            by_face = clip_hits.setdefault(clip,{})
            for face in pairs[:,1]:
                by_face[int(face)] = by_face.get(int(face),0)+1
    return deficits,severity,hits,clip_hits


def checkpoint_fit(recover=False):
    """Open the checkpoint directly so the next save owns its data."""
    source_file = bpy.data.libraries.load(str(SEED_BLEND))
    with source_file as (source,target):
        target.objects = ["Dress"]
    original, = target.objects
    source_points = mesh_points(original.data)
    source_triangles = triangulation(original)
    if recover:
        scene,arm,body = R1["open_master"]()
        garment = R1["import_mesh"](GLB)
        R1["bind"](garment,arm)
        mesh = bmesh.new()
        mesh.from_mesh(garment.data)
        bmesh.ops.remove_doubles(mesh,verts=list(mesh.verts),dist=1e-7)
        mesh.to_mesh(garment.data)
        mesh.free()
    else:
        bpy.ops.wm.open_mainfile(filepath=str(BLEND))
        scene = bpy.context.scene
        arm,body,garment = (scene.objects[name] for name in ("Armature","Base_Body","Dress"))
        for action in list(bpy.data.actions):
            bpy.data.actions.remove(action)
    # Restore the original authored material datablock after any GLB recovery.
    with bpy.data.libraries.load(str(SEED_BLEND)) as (source,target):
        target.objects = ["Dress"]
    material_source, = target.objects
    material = material_source.data.materials[0]
    old_material = garment.data.materials[0]
    original_material_name = R2["glb_metadata"](SEED)[0]["materials"][0]["name"]
    garment.data.materials[0] = material
    bpy.data.objects.remove(material_source,do_unlink=True)
    if old_material != material and not old_material.users:
        bpy.data.materials.remove(old_material)
    duplicate = bpy.data.materials.get(original_material_name)
    if duplicate is not None and duplicate != material and not duplicate.users:
        bpy.data.materials.remove(duplicate)
    material.name = original_material_name
    arm.animation_data_create()
    R1["setup_motion"](scene,arm,body,garment)
    names = tuple(bone.name for bone in arm.data.bones)
    points = mesh_points(garment.data)
    weights = read_weights(garment,names)
    samples,matrices = cache_samples(scene,arm,body,names)
    if len(points) != len(source_points) or recover:
        source_points = R2["transfer_split_reference"](
            source_points,source_triangles,source_points,points)
    return scene,arm,body,garment,names,points,weights,samples,matrices,source_points


def steer_patch(points, weights, origin, triangles, links, samples, transforms, posed, skin,
                pivot, severity, radius, names, directions, body_weights=None, hard_floor=False, anchor=False):
    """Score candidate lofts against the exact swept local triangles."""
    distance = np.linalg.norm(points-points[pivot],axis=1)
    ids = np.flatnonzero(distance < radius)
    t = 1-distance[ids]/radius
    falloff = t*t*(3-2*t)
    fine = body_weights is not None
    if fine:
        frame_order = np.argsort(-severity[:,pivot],kind="stable")[:12]
        rays = []
        for frame in frame_order:
            loc, normal, _, _ = samples[frame][2].find_nearest(posed[frame,pivot].tolist())
            slope = np.asarray(normal) @ skin[frame,pivot,:,:3]
            length = np.linalg.norm(slope)
            if length > 1e-8 and all(slope @ ray < length*.97 for ray in rays):
                rays.append(slope/length)
        if rays:
            directions = np.vstack((rays,directions))
    changed = np.isin(triangles,ids).any(axis=1)
    nearby, face_ids = np.unique(triangles[changed].ravel(),return_inverse=True)
    local_faces = face_ids.reshape(-1,3).tolist()
    local_ids = np.searchsorted(nearby,ids)
    topology = triangles[changed]
    base_tri = points[topology]
    base_normal = np.cross(base_tri[:,1]-base_tri[:,0],base_tri[:,2]-base_tri[:,0])
    normal_size = np.sum(base_normal**2,axis=1)
    source, dest, _ = links

    # Rank quick trials on the most severe separated times in each clip.
    # Validate the finalists on the entire schedule before accepting one.
    heat = severity[:,nearby].sum(axis=1) + severity[:,nearby].max(axis=1)
    nearby_poses = {0,*range(0,len(samples),37)}
    for clip in CLIPS:
        clip_ids = np.array([i for i,row in enumerate(samples) if row[0]==clip])
        selected = []
        for row in clip_ids[np.argsort(-heat[clip_ids],kind="stable")]:
            if heat[row] <= 1e-7:
                break
            if all(abs(row-prev)>3 for prev in selected):
                selected.append(row)
            if len(selected)>=6:
                break
        nearby_poses.update(selected)
    nearby_poses = np.array(sorted(nearby_poses),dtype=np.int32)
    old_local = posed[:,nearby]
    base = points[ids].copy()
    wt = weights[ids].copy()
    local_rest = samples[0][2]
    resting = old_local[0].copy()
    rest_reference = origin[ids]
    tri_barys = R2["REST_BARYCENTRICS"]
    best = (float("inf"), None, None)

    def trial(delta, altered, frame_ids):
        """Return a continuous clearance cost augmented by exact pair counts."""
        rest_points = base + delta
        if np.linalg.norm(rest_points-rest_reference,axis=1).max() > CAP+1e-7:
            return float("inf")
        rest_coordinates = resting.copy()
        rest_coordinates[local_ids] = rest_points
        face = rest_coordinates[face_ids].reshape(-1,3,3)
        normals = np.cross(face[:,1]-face[:,0],face[:,2]-face[:,0])
        if np.any(np.sum(normals*base_normal,axis=1) < normal_size*.085):
            return float("inf")
        if np.any(delta):
            probes = np.einsum("bk,fki->fbi",tri_barys,face).reshape(-1,3)
            rest_distance = clearance(local_rest,np.vstack((rest_points,probes)))[0]
            if rest_distance.min() < .00053 or rest_distance.max() > CAP-.00002:
                return float("inf")

        skins = skin[frame_ids[:,None],ids]
        if altered is not None:
            coefficients, columns = R2["sparse_weights"](altered)
            _,skins = R2["skin_poses"](rest_points,coefficients,columns,transforms[frame_ids])
        moved = np.einsum("fvij,vj->fvi",skins[...,:3],rest_points)+skins[...,3]
        posed_local = old_local[frame_ids].copy()
        posed_local[:,local_ids] = moved
        total_depth = floor_depth = 0.
        inside = pair_count = 0
        maximum_deficit = max_floor_deficit = 0.
        for j,row in enumerate(frame_ids):
            tree = samples[row][2]
            loc = posed_local[j]
            signed = clearance(tree,loc)[0]
            pair_count += len(tree.overlap(BVHTree.FromPolygons(loc.tolist(),local_faces,
                                                                all_triangles=True)))
            inside += int(np.count_nonzero(signed<0))
            guard = .00078 if fine else .00125
            gap = np.maximum(guard-signed,0)*1000
            maximum_deficit = max(maximum_deficit,float(gap.max()))
            total_depth += float(gap@gap)
            if hard_floor:
                below_floor = np.maximum(.000555-signed,0)*1000
                floor_depth += float(below_floor@below_floor)
                max_floor_deficit = max(max_floor_deficit,float(below_floor.max()))
        if hard_floor:
            return (pair_count*450 + inside*500 + max_floor_deficit**2*800
                    + floor_depth*22 + total_depth*.008 + 7000*np.square(delta).sum())
        return (pair_count*(3 if fine else 1) + inside*11. + total_depth*.62
                + maximum_deficit**2 * 15. + 7000*np.square(delta).sum())

    zero = np.zeros((len(ids),3),dtype=np.float32)
    seed_cost = trial(zero,None,nearby_poses)
    if not np.isfinite(seed_cost):
        return None
    ranked = [(seed_cost,zero,None)]
    if radius >= .024:
        sizes = (.003,.006,.010,.014)
    elif hard_floor:
        sizes = (.00035,.00065,.0011,.0018,.003,.005)
    else:
        sizes = (.0007,.00155,.0032,.006) if fine else (.002,.0045,.008)
    for strength in sizes:
        for direction in directions:
            delta = falloff[:,None]*direction*strength
            cost = trial(delta,None,nearby_poses)
            if cost < seed_cost - .0001:
                ranked.append((cost,delta,None))
    if hard_floor:
        q = int(np.searchsorted(ids,pivot))
        slot = np.argsort(-wt[q],kind="stable")[:4]
        values = wt[q,slot]
        test_frames = np.flatnonzero(severity[:,pivot]>0)
        frame_ids = np.unique(np.r_[test_frames,nearby_poses])
        normals, signed = [], []
        for row in frame_ids:
            point = posed[row,pivot]
            loc,n,_,_ = samples[row][2].find_nearest(point.tolist())
            normals.append(tuple(n))
            signed.append((point-np.asarray(loc))@np.asarray(n))
        normals = np.asarray(normals)
        signed = np.asarray(signed)
        mats = transforms[frame_ids[:,None],slot]
        moved = np.einsum("fkij,j->fki",mats[...,:3],base[q])+mats[...,3]
        g_xyz = np.einsum("fi,fij->fj",normals,skin[frame_ids,pivot,:,:3])
        g_weights = np.einsum("fi,fki->fk",normals,moved)*9
        g_weights -= g_weights.mean(axis=1,keepdims=True)
        jacobian = np.column_stack((g_xyz,g_weights))
        lengths = (jacobian**2).sum(axis=1).clip(1e-6)
        for goal in (.00060,.00085,.0012):
            x = np.zeros(7,dtype=np.float32)
            for _ in range(180):
                short = goal-signed-jacobian@x
                i = int(np.argmax(short))
                if short[i] <= 1e-8:
                    break
                x += (short[i]/lengths[i]*jacobian[i]).astype(np.float32)
                length = np.linalg.norm(x[:3])
                if length > .004:
                    x[:3] *= .004/length
                qv = R2["simplex"]((values+9*x[3:])[None])[0]
                x[3:] = (qv-values)/9
            for fraction in (.4,.75,1.):
                delta = np.zeros_like(zero)
                delta[q] = x[:3]*fraction
                changed_wt = wt.copy()
                changed_wt[q,slot] += 9*x[3:]*fraction
                cost = trial(delta,changed_wt,nearby_poses)
                if cost < seed_cost - .0001:
                    ranked.append((cost,delta,changed_wt))
    if anchor:
        # Explore coupled changes where the arm and torso define competing
        # nearest planes. Evaluate the exact swept triangles for finalists.
        rng = np.random.default_rng(pivot)
        count = 1800
        offsets = rng.normal(size=(count,3)).astype(np.float32)
        offsets *= rng.choice(np.array((.00065,.0014,.0028,.0045),dtype=np.float32), count)[:,None]
        offsets = R2["bound_delta"](offsets,.007)
        baseline_weights = wt[q,slot]
        perturbation = rng.normal(size=(count,4)).astype(np.float32)
        perturbation *= rng.choice(np.array((.014,.042,.09,.17),dtype=np.float32),count)[:,None]
        candidate_weights = R2["simplex"](baseline_weights + perturbation)
        subset = np.asarray(frame_ids,dtype=np.int32)
        # Include a small set of safe poses so this search cannot optimize
        # only the worst collision side of the armpit.
        mats = transforms[subset[:,None],slot]
        skin_trials = np.einsum("fkij,ck->fcij",mats,candidate_weights)
        vertex_trials = (np.einsum("fcij,cj->fci",skin_trials[...,:3],base[q]+offsets)
                         + skin_trials[...,3])
        cost = np.zeros(count,dtype=np.float32)
        peak = cost.copy()
        for frame,positions in zip(subset,vertex_trials):
            distances = clearance(samples[frame][2],positions)[0]
            gap = np.maximum(.0006-distances,0)*1000
            cost += gap**2
            peak = np.maximum(peak,gap)
        costs = cost + 13*peak**2 + np.square(offsets*1000).sum(axis=1)*.006
        kept = 0
        for i in np.argsort(costs,kind="stable")[:180]:
            delta = np.zeros_like(zero)
            delta[q] = offsets[i]
            altered = wt.copy()
            altered[q,slot] = candidate_weights[i]
            trial_cost = trial(delta,altered,nearby_poses)
            if trial_cost < seed_cost-.0001:
                kept += 1
                ranked.append((trial_cost,delta,altered))
                if kept >= 24:
                    break
    ranked.sort(key=lambda item: item[0])

    # Contact nodes may need to follow an adjacent joint, especially at
    # the bottom cuff and across opposite thigh transitions.
    _,offset,_ = ranked[0]
    smooth = R2["average"](weights,links)[ids]
    all_names = {name.split(":")[-1]:index for index,name in enumerate(names)}
    side = "Left" if points[pivot,0]>0 else "Right"
    if points[pivot,2] < .40:
        bone_names = ("Hips",side+"UpLeg",side+"Leg")
    elif points[pivot,2] > .47:
        bone_names = ("Spine1","Spine2",side+"Shoulder",side+"Arm")
    else:
        bone_names = ("Hips","Spine","Spine1","Spine2")
    bases = [smooth]
    if fine:
        tree = samples[0][2]
        body,faces = samples[0][3:]
        data = [tree.find_nearest(point.tolist()) for point in points[ids]]
        face = faces[[row[2] for row in data]]
        nearest = np.array([tuple(row[0]) for row in data])
        mix = R1["barycentric"](body[face],nearest).clip(0,1)
        target = np.einsum("nk,nkj->nj",mix,body_weights[face])
        bases.append(target/target.sum(axis=1,keepdims=True))
    for name in bone_names:
        typical = np.zeros_like(wt)
        typical[:,all_names[name]] = 1.
        bases.append(typical)
    strengths = (.14,.32,.56,.84) if fine else (.10,.26)
    for strength in strengths:
        blend = falloff[:,None]*strength
        for typical in bases:
            altered = R2["limit_weights"]((1-blend)*wt + blend*typical)
            for delta in (zero,offset):
                cost = trial(delta,altered,nearby_poses)
                if cost < seed_cost - .0001:
                    ranked.append((cost,delta,altered))
    if len(ranked) == 1:
        return None
    ranked.sort(key=lambda item:item[0])
    full_schedule = np.arange(len(samples))
    control = trial(zero,None,full_schedule)
    for _,delta,altered in ranked[:(10 if anchor else 5)]:
        cost = trial(delta,altered,full_schedule)
        if cost < control - .0001:
            control = cost
            best = (cost,delta,altered)
    return (ids,*best[1:]) if best[1] is not None else None


def local_refine(recover=False, fine=False, close=False):
    scene,arm,body,garment,names,points,weights,samples,matrices,origin = checkpoint_fit(recover)
    body_weights = read_weights(body,names,validate=False) if fine else None
    R2["export"].__globals__.update(GLB=GLB,BLEND=BLEND)
    triangles = triangulation(garment)
    coeff,columns = R2["sparse_weights"](weights)
    posed,skin = R2["skin_poses"](points,coeff,columns,matrices)
    gap,severity,hits,clips = contact_field(points,triangles,samples,posed)
    lengths = np.linalg.norm(points[triangles]-np.roll(points[triangles],1,axis=1),axis=2).max(axis=1)
    long = np.count_nonzero((hits>0)&(lengths>.012))
    print("LOCAL LOFT",len(points),len(triangles),"crossing faces",int((hits>0).sum()),"long",long,flush=True)
    for clip,faces in clips.items():
        print("LOCAL CONTACTS",clip,[(n,tuple(np.round(points[triangles[t]].mean(axis=0)*1000,1)))
                                        for t,n in sorted(faces.items(),key=lambda item:-item[1])[:8]],
              flush=True)
    if long and not (recover or close):
        old_points, old_triangles = points.copy(), triangles.copy()
        R2["subdivide"](garment,points,weights,names,triangles,hits,.012,8000-len(triangles),loft=True)
        points, triangles = mesh_points(garment.data),triangulation(garment)
        origin = R2["transfer_split_reference"](old_points,old_triangles,origin,points)
        weights = R2["limit_weights"](read_weights(garment,names,validate=False))
    links = R2["neighbors"](garment.data)
    history_path = HERE/".loft_iterations.json"
    history = json.loads(history_path.read_text()) if (recover or fine) and history_path.exists() else []
    start = len(history)
    stages = 2 if close else (3 if fine else 4-start)
    if recover:
        R2["export"](scene,arm,body,garment,points,weights,names)
    offset_grid = np.asarray([(a,b,c) for a in (-1,0,1) for b in (-1,0,1) for c in (-1,0,1)
                              if a or b or c],dtype=np.float32)
    offset_grid /= np.linalg.norm(offset_grid,axis=1,keepdims=True)
    for index in range(stages):
        k = start+index
        coeff,columns = R2["sparse_weights"](weights)
        posed,skin = R2["skin_poses"](points,coeff,columns,matrices)
        gap,severity,hits,clips = contact_field(points,triangles,samples,posed)
        heat = severity.sum(axis=0) + severity.max(axis=0)*65
        used = np.zeros(len(points),dtype=bool)
        chosen = 0
        controls = (8,12)[index] if close else (16 if k>0 else 22)
        for cursor in range(controls):
            pivot = int(np.argmax(np.where(used,-1,heat)))
            if heat[pivot]<1e-6:
                break
            if close:
                radius = (.027,.013)[index]
            else:
                radius = (.016,.013,.011)[index] if fine else (.019,.018,.015,.013)[k]
            distance = np.linalg.norm(points-points[pivot],axis=1)
            used |= distance < radius*.62
            result = steer_patch(points,weights,origin,triangles,links,samples,matrices,
                                 posed,skin,pivot,severity,radius,names,offset_grid,body_weights)
            if result is None:
                print("LOCAL NO CHANGE",k,pivot,np.round(points[pivot]*1000,1),flush=True)
                continue
            ids, delta, altered = result
            print("LOCAL MOVE",k,pivot,np.round(points[pivot]*1000,1),"mm",
                  round(float(np.linalg.norm(delta,axis=1).max()*1000),2),
                  "weighted",altered is not None,flush=True)
            points[ids] += delta
            if altered is not None:
                weights[ids] = altered
            q,b = R2["sparse_weights"](weights[ids])
            posed[:,ids],skin[:,ids] = R2["skin_poses"](points[ids],q,b,matrices)
            chosen += 1
        coeff,columns = R2["sparse_weights"](weights)
        report,*_ = constraints(points,coeff,columns,triangles,samples,matrices)
        display(f"LOCAL VERIFICATION {k}",report)
        history.append(report)
        history_path.write_text(json.dumps(history,indent=2)+"\n")
        R2["export"](scene,arm,body,garment,points,weights,names)
        if not chosen or all(r["inside"]==r["pairs"]==0 and r["min_m"]>=FLOOR for r in report.values()):
            break


def clearance_finish(anchor=False):
    """Set the last submillimetre gaps with exact local pose comparisons."""
    scene,arm,body,garment,names,points,weights,samples,matrices,origin = checkpoint_fit()
    body_weights = read_weights(body,names,validate=False)
    triangles = triangulation(garment)
    links = R2["neighbors"](garment.data)
    coeff,columns = R2["sparse_weights"](weights)
    posed,skin = R2["skin_poses"](points,coeff,columns,matrices)
    gap,severity,hits,_ = contact_field(points,triangles,samples,posed)
    if hits.any():
        print("CLEARANCE ADJUSTMENT REQUIRES ZERO OVERLAPS",flush=True)
        return
    # Prioritize the vertices below the gate and keep the complete overlap
    # neighborhood in each trial even when repositioning only one control.
    need = np.maximum(gap-(.00155-.00056),0)
    active = np.flatnonzero(need.max(axis=0)>0)
    axes = np.asarray([(a,b,c) for a in (-1,0,1) for b in (-1,0,1) for c in (-1,0,1)
                       if a or b or c],dtype=np.float32)
    axes /= np.linalg.norm(axes,axis=1,keepdims=True)
    print("FINAL CLEARANCE CONTROLS",len(active),flush=True)
    order = active[np.argsort(-need[:,active].max(axis=0),kind="stable")]
    for vertex in order[:22]:
        severity = need
        other = np.linalg.norm(points-points[vertex],axis=1)
        radius = min(.012, max(.0035, float(np.min(other[other>1e-6]))*.97))
        result = steer_patch(points,weights,origin,triangles,links,samples,matrices,
                             posed,skin,vertex,severity,radius,names,axes,body_weights,
                             hard_floor=True,anchor=anchor)
        if result is None:
            continue
        ids,delta,changed_weights = result
        points[ids] += delta
        if changed_weights is not None:
            weights[ids] = changed_weights
        q,b = R2["sparse_weights"](weights[ids])
        posed[:,ids],skin[:,ids] = R2["skin_poses"](points[ids],q,b,matrices)
        print("FINAL CLEARANCE CONTROL",int(vertex),np.round(points[vertex]*1000,2),flush=True)
    coeff,columns = R2["sparse_weights"](weights)
    report,*_ = constraints(points,coeff,columns,triangles,samples,matrices)
    display("FINAL CLEARANCE",report)
    history_path = HERE/".loft_iterations.json"
    history = json.loads(history_path.read_text()) if history_path.exists() else []
    history_path.write_text(json.dumps([*history,report],indent=2)+"\n")
    if all(r["pairs"]==r["inside"]==0 for r in report.values()):
        R2["export"].__globals__.update(GLB=GLB,BLEND=BLEND)
        R2["export"](scene,arm,body,garment,points,weights,names)


def trim_rest():
    """Ease a local hem panel inward to satisfy the rest surface cap."""
    scene,arm,body,garment = R1["read_export"](GLB)
    set_pose(scene,arm,"rest",1)
    graph = bpy.context.evaluated_depsgraph_get()
    body_points,body_faces = R1["posed_mesh"](body,graph)
    dress_points,_ = R1["posed_mesh"](garment,graph)
    tree = BVHTree.FromPolygons(body_points,body_faces,all_triangles=True)
    probes = R2["rest_sample_positions"](np.asarray(dress_points),triangulation(garment)).reshape(-1,3)
    distance,normal,_ = clearance(tree,probes)
    excessive = np.flatnonzero(distance>CAP)
    if not len(excessive):
        return
    center = probes[excessive].mean(axis=0)
    print("REST CAP PROBES",len(excessive),center.tolist(),float(distance.max()),flush=True)
    scene,arm,body,garment,names,points,weights,samples,matrices,origin = checkpoint_fit()
    triangles = triangulation(garment)
    coefficients,columns = R2["sparse_weights"](weights)
    posed,skin = R2["skin_poses"](points,coefficients,columns,matrices)
    base_rest = posed[0]
    tree = samples[0][2]
    directions = np.asarray([(0,1,0),(.55,1,0),(-.55,1,0),(0,1,.3),*list(-normal[excessive])],
                            dtype=np.float32)
    directions /= np.linalg.norm(directions,axis=1,keepdims=True)
    for size in (.0024,.0034,.0044,.0055,.007):
        for direction in directions:
            radius = .025
            d = np.linalg.norm(base_rest-center,axis=1)
            selected = np.flatnonzero(d<radius)
            weight = np.clip(1-d[selected]/radius,0,1)
            off = direction[None,:]*size*(weight**2*(3-2*weight))[:,None]
            if np.max(np.linalg.norm(points[selected]+off-origin[selected],axis=1))>CAP:
                continue
            changed = np.isin(triangles,selected).any(axis=1)
            patch,faces = np.unique(triangles[changed].ravel(),return_inverse=True)
            faces = faces.reshape(-1,3)
            rest_trial = base_rest.copy()
            rest_trial[selected] += off
            probe = R2["rest_sample_positions"](rest_trial,triangles).reshape(-1,3)
            d = clearance(tree,np.vstack((rest_trial,probe)))[0]
            chosen_probes = np.linalg.norm(probe-center,axis=1)<.008
            if d.max()>CAP-.000035 or d.min()<FLOOR or d[len(rest_trial):][chosen_probes].max()>.0285:
                continue
            base_tri = base_rest[triangles[changed]]
            result_tri = rest_trial[triangles[changed]]
            n0 = np.cross(base_tri[:,1]-base_tri[:,0],base_tri[:,2]-base_tri[:,0])
            n1 = np.cross(result_tri[:,1]-result_tri[:,0],result_tri[:,2]-result_tri[:,0])
            if np.any((n0*n1).sum(axis=1)<(n0*n0).sum(axis=1)*.1):
                continue
            change = np.einsum("fvij,vj->fvi",skin[:,selected,:,:3],off)
            loc = posed[:,patch].copy()
            loc[:,np.searchsorted(patch,selected)] += change
            usable = True
            for f,(_,_,body_tree,*_) in enumerate(samples):
                mesh = BVHTree.FromPolygons(loc[f].tolist(),faces.tolist(),all_triangles=True)
                if body_tree.overlap(mesh) or clearance(body_tree,loc[f])[0].min()<FLOOR:
                    usable = False
                    break
            if not usable:
                continue
            points[selected] += off
            print("REST CAP TRIM",len(selected),size,direction.tolist(),float(d.max()),flush=True)
            R2["export"].__globals__.update(GLB=GLB,BLEND=BLEND)
            R2["export"](scene,arm,body,garment,points,weights,names)
            return
    print("REST CAP TRIM RETAINED CHECKPOINT",flush=True)


if __name__ == "__main__":
    for mode in sys.argv[sys.argv.index("--") + 1:]:
        {"baseline":baseline, "fit":fit, "loft":local_refine,
         "recover":lambda: local_refine(recover=True),
         "finish":lambda: local_refine(fine=True),
         "close":lambda: local_refine(fine=True,close=True),
         "clearance":clearance_finish,
         "anchor":lambda: clearance_finish(anchor=True),
         "trim-rest":trim_rest,
         "check":check, "verify":verify, "render":render}[mode]()
