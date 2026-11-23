"""Refit the Round 3 A-line dress against both corrected animation banks."""
import json
import os
from pathlib import Path
import runpy
import sys

sys.dont_write_bytecode = True
sys.path.insert(0,str(Path(__file__).resolve().parent))

import numpy as np
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
WORK = HERE / ".work"
WORK.mkdir(exist_ok=True)
PREVIOUS = runpy.run_path(str(HERE.parent / "round4/fit_dress_r4.py"))
shared = PREVIOUS["import_scene"].__globals__
shared.update(HERE=HERE, BANK=PREVIOUS["MASTER"].parent.parent / "actions-fix/actions_fixed.glb",
              GLB=HERE/"dress_v5.glb", BLEND=HERE/"dress_v5.blend")
BAKE_POSES = shared["cache"]
R1, R2, R3 = (PREVIOUS[key] for key in ("R1", "R2", "R3"))
SEED = PREVIOUS["SEED"]
FLOOR, CAP = PREVIOUS["FLOOR"], PREVIOUS["CAP"]


def cache_poses(scene, arm, body, names, actions):
    """Keep sampled transforms and posed body vertices for local iterations."""
    key = "_".join(shared["sha"](shared[name])[:16] for name in ("MASTER","MOTION","BANK"))
    path = WORK/f"poses_{key}.npz"
    if path.is_file():
        with np.load(path,allow_pickle=False) as data:
            assert tuple(data["bones"]) == names
            clips, frames, shapes, faces, matrices = (
                data[item] for item in ("clips","frames","shapes","faces","matrices"))
        poly = faces.tolist()
        samples = [(str(clip),float(frame),
                    BVHTree.FromPolygons(xyz.tolist(),poly,all_triangles=True),xyz,faces)
                   for clip,frame,xyz in zip(clips,frames,shapes,strict=True)]
        return samples, matrices
    samples, matrices = BAKE_POSES(scene,arm,body,names,actions)
    stage = path.with_suffix(f".{os.getpid()}.npz")
    np.savez(stage,bones=names,clips=[s[0] for s in samples],frames=[s[1] for s in samples],
             shapes=np.asarray([s[3] for s in samples]),faces=samples[0][4],matrices=matrices)
    stage.replace(path)
    return samples, matrices


def load_fit(source):
    scene, arm, body, garment, actions = shared["import_scene"](source, weld=True)
    names = tuple(bone.name for bone in arm.data.bones)
    points = shared["mesh_points"](garment.data)
    weights = R3["read_weights"](garment, names)
    faces = shared["triangulation"](garment)
    samples, matrices = cache_poses(scene, arm, body, names, actions)
    return (scene, arm, body, garment, names), points, weights, faces, samples, matrices


def baseline():
    state, points, weights, faces, samples, matrices = load_fit(SEED)
    r3 = shared["scan"](points,weights,faces,samples,matrices)[0]
    garment = R1["import_mesh"](HERE.parent/"round4/dress_v4.glb")
    points = shared["mesh_points"](garment.data)
    weights = R3["read_weights"](garment,state[4])
    faces = shared["triangulation"](garment)
    r4 = shared["scan"](points,weights,faces,samples,matrices)[0]
    for title, report in (("ROUND 3",r3),("ROUND 4",r4)):
        R3["display"](title,report)
    (HERE/"seed_comparison.json").write_text(json.dumps({"round3":r3,"round4":r4},indent=2)+"\n")


def hybrid_cut(state, points, weights):
    """Reuse the earlier skirt loft on the original Round 3 topology and UVs."""
    scene, _, _, garment, names = state
    before = set(scene.objects)
    previous = R1["import_mesh"](HERE.parent/"round4/dress_v4.glb")
    by_uv = dict(zip(shared["uv_keys"](previous.data),range(len(previous.data.vertices)),strict=True))
    source_uv = shared["uv_keys"](garment.data)
    # A welded chart vertex may own several UV coordinates. Match the
    # smallest common chart set when the other GLB retains a seam split.
    by_corner = {uv:key for key in by_uv for uv in key}
    lookup = [by_uv[key if key in by_uv else by_corner[key[0]]] for key in source_uv]
    old_p = shared["mesh_points"](previous.data)[lookup]
    old_w = R3["read_weights"](previous,names)[lookup]
    taper = np.clip((.52-points[:,2])/.075,0,1)
    blend = (taper*taper*(3-2*taper))[:,None]
    for obj in set(scene.objects)-before:
        bpy.data.objects.remove(obj,do_unlink=True)
    return (points+(old_p-points)*blend,
            R2["limit_weights"](weights+(old_w-weights)*blend))


def solve(source, iterations, split=False, hybrid=False, exact=False):
    from contact_fit import fit_sweep

    state, points, weights, faces, samples, matrices = load_fit(source)
    scene, arm, body, garment, names = state
    shared["setup_material"](garment)
    origin = points.copy()
    if hybrid:
        points,weights = hybrid_cut(state,points,weights)
    links = R2["neighbors"](garment.data)
    shared["anatomy"] = shared["body_weight_targets"](points,body,names,samples[0])
    best = float("inf")
    history = []
    destination = ("exact.glb" if exact else
                   "hybrid.glb" if hybrid else "split.glb" if split else "solve.glb")
    for step in range(iterations+1):
        report,hits,proposal,weight_proposal = fit_sweep(
            points,weights,origin,faces,links,samples,matrices,(R1,R2,R3,shared),step+(11 if exact else 0))
        history.append(report)
        (WORK/(destination+".json")).write_text(json.dumps(history,indent=2)+"\n")
        objective = shared["fit_score"](report)
        if objective < best or step==0:
            shared["export"](*state,points,weights,draft=True,draft_name=destination)
            best = objective
        if objective==0 or step==iterations:
            break
        if split and step in (0,5) and hits.any():
            budget = min(650, 8000-len(faces))
            R2["subdivide"](garment, points, weights, names, faces, hits, .0045 if exact else .006, budget, loft=True)
            new = shared["mesh_points"](garment.data)
            origin = R2["transfer_split_reference"](points,faces,origin,new)
            points = new
            weights = R3["read_weights"](garment,names,validate=False)
            weights = R2["limit_weights"](weights)
            faces = shared["triangulation"](garment)
            links = R2["neighbors"](garment.data)
            shared["anatomy"] = shared["body_weight_targets"](points,body,names,samples[0])
        else:
            points,weights = proposal,weight_proposal


def polish(source, passes):
    from polish_contacts import move_patch

    state, points, weights, faces, samples, matrices = load_fit(source)
    _,_,body,garment,names = state
    shared["setup_material"](garment)
    anatomy = shared["body_weight_targets"](points,body,names,samples[0])
    for step in range(passes+1):
        report,posed,skin,signed,_,contacts,hits = shared["scan"](
            points,weights,faces,samples,matrices)
        R3["display"](f"POLISH {step}",report)
        shared["export"](*state,points,weights,draft=True,draft_name="polish.glb")
        heat = np.maximum(.00056-signed,0).max(axis=0)
        np.add.at(heat,faces[hits>0].ravel(),.00012*np.log1p(hits[hits>0]).repeat(3))
        if step==passes or not heat.any():
            break
        used = np.zeros(len(points),bool)
        for pivot in np.argsort(-heat,kind="stable"):
            if heat[pivot] <= 0:
                break
            if used[pivot]:
                continue
            for radius in (.011,.0065,.018):
                result = move_patch(pivot,radius,points,weights,faces,posed,skin,signed,
                                    contacts,samples,matrices,anatomy,(R1,R2,shared))
                if result is not None:
                    ids,new_p,new_w,loss,gain = result
                    points[ids],weights[ids] = new_p,new_w
                    posed[:,ids],skin[:,ids] = R2["skin_poses"](
                        new_p,*R2["sparse_weights"](new_w),matrices)
                    shared["export"](*state,points,weights,draft=True,draft_name="polish.glb")
                    print("LOCAL",pivot,points[pivot].tolist(),loss,gain,flush=True)
                    break
            used |= np.linalg.norm(points-points[pivot],axis=1)<.016


def clearance_floor(source, passes):
    from polish_contacts import lift_vertex

    state, points, weights, faces, samples, matrices = load_fit(source)
    _,_,body,garment,names = state
    shared["setup_material"](garment)
    anatomy = shared["body_weight_targets"](points,body,names,samples[0])
    report,posed,skin,signed,_,contacts,_ = shared["scan"](points,weights,faces,samples,matrices)
    R3["display"]("FLOOR INPUT",report)
    assert not contacts, "Eliminate triangle intersections before polishing clearance."
    rng = np.random.default_rng(4882026)
    for _ in range(passes):
        minimum = signed.min(axis=0)
        active = np.flatnonzero(minimum<.000515)
        for vertex in active[np.argsort(minimum[active],kind="stable")]:
            result = lift_vertex(vertex,points,weights,faces,posed,skin,signed,samples,matrices,
                                 anatomy,(R2,shared),rng)
            if result is not None:
                points[vertex],weights[vertex],posed[:,vertex],skin[:,vertex],signed[:,vertex] = result
                print("CLEARANCE",int(vertex),float(minimum[vertex])*1000,
                      float(signed[:,vertex].min())*1000,flush=True)
        remaining = np.flatnonzero(signed.min(axis=0)<.0005)
        for vertex in remaining:
            at = int(signed[:,vertex].argmin())
            print("FLOOR REMAINING",int(vertex),samples[at][:2],float(signed[at,vertex])*1000,
                  points[vertex].tolist(),flush=True)
        shared["export"](*state,points,weights,draft=True,draft_name="floor.glb")
        if signed.min()>=.000502:
            break
    R3["display"]("FLOOR FINAL",shared["scan"](points,weights,faces,samples,matrices)[0])


def body_only():
    """Record the published master-body checks with their matching input hashes."""
    sha = shared["sha"]
    master_sha = sha(shared["MASTER"])
    motion_sha = sha(shared["MOTION"])
    actions_sha = sha(shared["BANK"])
    legacy_path = SEED.parent/"dense_check.json"
    added_path = shared["BANK"].with_name("body_selfcheck_after.json")
    legacy = json.loads(legacy_path.read_text())
    added = json.loads(added_path.read_text())
    assert legacy["master_sha256"] == added["master_sha256"] == master_sha
    assert legacy["motion_sha256"] == motion_sha and added["action_sha256"] == actions_sha
    result = {}
    for name, body in legacy["body_only"].items():
        result[name] = dict(samples=len(body["frames"]),
                            peak_body_only_pairs=max(c for _,c in body["frames"]),
                            total_body_only_pairs=body["integer_occurrences"]+body["half_frame_occurrences"])
    for name, clip in added["clips"].items():
        rows, summary = clip["samples"], clip["summary"]
        result[name] = dict(samples=len(rows),
                            peak_body_only_pairs=max(row["all_pairs"] for row in rows),
                            total_body_only_pairs=summary["all_integer"]+summary["all_half"],
                            peak_knee_pairs=max(row["target_pairs"] for row in rows),
                            total_knee_pairs=summary["target_total"],
                            knee_zones=summary["target_by_region"],
                            deepest_knee=summary["deepest_target"])
    (HERE/"body_only.json").write_text(json.dumps(
        {"master_sha256":master_sha,"motion_sha256":motion_sha,"actions_sha256":actions_sha,
         "legacy_audit_sha256":sha(legacy_path),"added_audit_sha256":sha(added_path),
         "source":"Prior Blender self-checks of the exact master and animation banks",
         "results":result},indent=2)+"\n")


def build():
    """Rebuild the local fitting stages from the shipped dress."""
    solve(SEED, 2, hybrid=True)
    solve(WORK/"hybrid.glb", 5, split=True, exact=True)
    polish(WORK/"exact.glb", 4)
    clearance_floor(WORK/"polish.glb", 3)
    restart = WORK/"floor_restart.glb"
    restart.write_bytes((WORK/"floor.glb").read_bytes())
    clearance_floor(restart, 1)
    shared["finalize"](WORK/"floor.glb")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--")+1:]
    stage = args[0] if args else "build"
    if stage == "build":
        build()
    elif stage == "body-only":
        body_only()
    elif stage == "baseline":
        baseline()
    elif stage in ("solve", "hybrid", "exact-split"):
        source = Path(args[2]).resolve() if len(args)>2 else SEED
        solve(source, int(args[1]), split=stage=="exact-split", hybrid=stage=="hybrid",
              exact=stage=="exact-split")
    elif stage == "polish":
        polish(Path(args[2]).resolve(), int(args[1]))
    elif stage == "floor":
        clearance_floor(Path(args[2]).resolve(), int(args[1]))
    elif stage == "cap":
        shared["cache"] = cache_poses
        shared["close_rest_cap"](Path(args[1]).resolve())
    elif stage == "finish":
        shared["finalize"](Path(args[1]).resolve())
    else:
        def verify_motion(variants=(False, True)):
            shared["check"](HERE/"dress_v5.glb", HERE, variants=variants)

        checks = {"check": verify_motion,
                  "vertex": lambda: verify_motion((False,)),
                  "triangles": lambda: verify_motion((True,)),
                  "zones": shared["failure_zones"]}
        for stage in args:
            (checks[stage] if stage in checks else shared[stage])()
