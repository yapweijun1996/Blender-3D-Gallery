"""Bake the Studio A-line dress against the local master and quaternion clips.

Run in Blender 5.1 with --python fit_dress_r2.py -- build check verify render.
"""

from contextlib import redirect_stdout
import hashlib
import io
import json
import math
from pathlib import Path
import runpy
import struct
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROUND_ONE = HERE.parent
PREVIOUS = runpy.run_path(str(ROUND_ONE / "fit_dress.py"))
MASTER, MOTION = PREVIOUS["MASTER"], PREVIOUS["MOTION"]
GLB = HERE / "dress_v2.glb"
BLEND = HERE / "dress_v2.blend"
CLIPS = PREVIOUS["CLIPS"]
MARGIN, FLOOR, CAP = .002, .0005, .03
TRIANGLE_LIMIT, ITERATIONS = 8000, 16

mesh_points = PREVIOUS["mesh_points"]
mesh_triangles = PREVIOUS["mesh_triangles"]
mesh_coords = PREVIOUS["mesh_coords"]
clearance = PREVIOUS["clearance"]
read_weights = PREVIOUS["read_weights"]
write_weights = PREVIOUS["write_weights"]
average = PREVIOUS["average"]
neighbors = PREVIOUS["neighbors"]
set_pose = PREVIOUS["set_pose"]
cache_samples = PREVIOUS["cache_samples"]
smoothstep = PREVIOUS["smoothstep"]
limit_weights = PREVIOUS["limit_weights"]
simplex = PREVIOUS["HOODIE"]["simplex"]
sha = PREVIOUS["sha"]


def scene_for_fit():
    scene, arm, body = PREVIOUS["open_master"]()
    with bpy.data.libraries.load(str(ROUND_ONE / "dress_v1.blend")) as (source, target):
        assert "Dress" in source.objects
        target.objects = ["Dress"]
    garment, = target.objects
    scene.collection.objects.link(garment)
    garment.parent = arm
    for modifier in garment.modifiers:
        if modifier.type == "ARMATURE":
            modifier.object = arm
    PREVIOUS["setup_motion"](scene, arm, body, garment)
    return scene, arm, body, garment


def skin_poses(points, weights, columns, transforms):
    skin = np.zeros((len(transforms), len(points), 3, 4), dtype=np.float32)
    for column, coefficient in zip(columns.T, weights.T):
        skin += transforms[:, column] * coefficient[None, :, None, None]
    posed = np.einsum("fvij,vj->fvi", skin[..., :3], points) + skin[..., 3]
    return posed, skin


def full_weights(weights, columns, count):
    result = np.zeros((len(weights), count), dtype=np.float32)
    np.put_along_axis(result, columns, weights, axis=1)
    return result


def directions(tree, points):
    """Use the nearest-surface ray and retain the checker sign convention."""
    d = np.empty(len(points), dtype=np.float32)
    n = np.empty_like(points)
    nearest = np.empty(len(points), dtype=np.int32)
    for i, p in enumerate(points.tolist()):
        loc, normal, face, _ = tree.find_nearest(p)
        x, y, z = p[0]-loc.x, p[1]-loc.y, p[2]-loc.z
        signed = x*normal.x + y*normal.y + z*normal.z
        distance = math.sqrt(x*x+y*y+z*z)
        direction = (1 if signed >= 0 else -1) / max(distance, 1e-9)
        n[i] = (x*direction,y*direction,z*direction) if distance > 1e-8 else normal
        d[i], nearest[i] = signed, face
    return d, n, nearest


def triangulation(garment):
    return np.asarray(mesh_triangles(garment.data), dtype=np.int32)


def inspect_motion(points, triangles, samples, posed, details=False):
    triangle_list = triangles.tolist()
    distances = np.empty(posed.shape[:2], dtype=np.float32)
    normals = np.empty_like(posed)
    contacts = []
    hits = np.zeros(len(triangles), dtype=np.int32)
    summary = {}
    body_zones = details if details else None
    zones = PREVIOUS["section"](points)
    for i, (clip, frame, tree, body_points, body_faces) in enumerate(samples):
        p = posed[i]
        signed, normal, nearest = directions(tree, p)
        distances[i], normals[i] = signed, normal
        surface = BVHTree.FromPolygons(p.tolist(), triangle_list, all_triangles=True)
        overlap = np.asarray(tree.overlap(surface), dtype=np.int32).reshape(-1, 2)
        v = int(signed.argmin())
        count = int((signed < 0).sum())
        note = summary.setdefault(clip, {"samples": 0, "inside": 0, "pairs": 0, "min_m": 1.,
                                         "total_pairs": 0, "failing_frames": 0})
        note["samples"] += 1
        note["inside"] = max(note["inside"], count)
        note["total_pairs"] += len(overlap)
        note["failing_frames"] += int(len(overlap)>0 or signed[v]<FLOOR)
        if "pair_frame" not in note or len(overlap)>note["pairs"]:
            note.update(pairs=len(overlap), pair_frame=frame)
        if signed[v]<note["min_m"]:
            note.update(min_m=float(signed[v]), min_frame=frame, min_zone=str(zones[v]),
                        min_rest_xyz=points[v].tolist())
            if body_zones:
                note["min_body_zone"] = body_zones[nearest[v]]
        if len(overlap):
            np.add.at(hits, overlap[:,1], 1)
            contacts.append((i, overlap))
    return distances, normals, hits, contacts, summary


def target_rank(distances, summary):
    """Combined dense severity, with the worst frame penalized across each clip."""
    deficit = np.maximum(MARGIN-distances, 0)*1000
    total_pairs = sum(note["total_pairs"] for note in summary.values())
    return (float(np.mean(deficit**2)*1500 + np.mean(deficit.max(axis=0)**2)*350
                  + total_pairs*.022 + deficit.max()**2*5),
            -float(distances.min()), total_pairs)


def log_sweep(label, distances, summary):
    print(label, round(target_rank(distances, summary)[0], 2),
          [(clip, r["inside"], r["pairs"], round(r["min_m"]*1000, 2))
           for clip, r in summary.items()], flush=True)


def project_rest(points, original, tree, rounds=4):
    p = points.copy()
    for _ in range(rounds):
        delta = p-original
        p = original + delta*np.minimum(1, (.03/np.linalg.norm(delta,axis=1).clip(1e-8)))[:,None]
        rest, normal, _ = clearance(tree, p)
        correction = np.clip(rest, .0012, CAP-.00015)-rest
        p += correction[:,None]*normal
    return p


def rest_guard(candidate, current, original, triangles, tree, orientation_reference=None):
    base = (original if orientation_reference is None else orientation_reference)[triangles]
    normals = np.cross(base[:,1]-base[:,0], base[:,2]-base[:,0])
    lengths = np.sum(normals**2,axis=1)
    faces = triangles.tolist()
    for _ in range(13):
        rests, _, _ = clearance(tree, candidate)
        t = candidate[triangles]
        cross = np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])
        turned = np.sum(cross*normals,axis=1) < lengths*.07
        overlap = np.asarray(tree.overlap(BVHTree.FromPolygons(candidate.tolist(),faces,all_triangles=True)),
                             dtype=np.int32).reshape(-1,2)
        bad = (rests < .00055) | (rests > CAP) | (np.linalg.norm(candidate-original,axis=1) > .030001)
        bad[triangles[turned].ravel()] = True
        bad[triangles[overlap[:,1]].ravel()] = True
        if not bad.any():
            return candidate
        candidate[bad] = current[bad] + (candidate[bad]-current[bad])*.46
    return current.copy()


def subdivide(garment, points, weights, names, triangles, hits, threshold, budget, loft=False):
    mesh_coords(garment, points)
    write_weights(garment, names, weights)
    mesh = bmesh.new()
    mesh.from_mesh(garment.data)
    mesh.verts.index_update()
    frequency = {}
    for face in np.flatnonzero(hits):
        corners = triangles[face]
        for a,b in zip(corners,np.roll(corners,-1)):
            key = tuple(sorted((a,b)))
            frequency[key] = frequency.get(key,0)+int(hits[face])
    edges = []
    for edge in mesh.edges:
        key = tuple(sorted(v.index for v in edge.verts))
        length = edge.calc_length()
        x,y,z = tuple((edge.verts[0].co+edge.verts[1].co)*.5)
        junction = (.065<abs(x)<.133 and .459<z<.557) or (abs(x)<.055 and z<.386)
        count = frequency.get(key,0)
        if count and (length>threshold or (loft and junction and length>.007)):
            edges.append((-length*math.log1p(count), key, edge))
    picked = []
    for _, _, edge in sorted(edges):
        cost = len(edge.link_faces)
        if cost <= budget:
            picked.append(edge)
            budget -= cost
    if picked:
        bmesh.ops.subdivide_edges(mesh, edges=picked, cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(mesh, faces=[face for face in mesh.faces if len(face.verts)>3])
        mesh.to_mesh(garment.data)
        garment.data.update()
    mesh.free()
    print("CONTACT EDGE SPLITS", len(picked), "triangles", len(garment.data.polygons), flush=True)
    return len(picked)


def export(scene, arm, body, garment, points, weights, names):
    set_pose(scene, arm, "rest", 1)
    arm.animation_data_clear()
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()
    mesh_coords(garment, points)
    write_weights(garment, names, weights)
    garment.name = garment.data.name = "Dress"
    assert len(names) == 65 and len(triangulation(garment)) <= TRIANGLE_LIMIT
    bpy.ops.object.select_all(action="DESELECT")
    garment.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = garment
    garment.parent = None
    bpy.ops.export_scene.gltf(filepath=str(GLB), use_selection=True, export_animations=False,
                             export_def_bones=False, export_all_influences=False, export_tangents=True)
    garment.parent = arm
    body.hide_render = False
    body.hide_set(False)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    arm.animation_data_create()


def base_state():
    scene, arm, body, garment = scene_for_fit()
    names = tuple(bone.name for bone in arm.data.bones)
    points = mesh_points(garment.data)
    weights = read_weights(garment, names)
    samples, matrices = cache_samples(scene, arm, body, names)
    return scene, arm, body, garment, names, points, weights, samples, matrices


def gather_constraints(points, weights, columns, triangles, samples, matrices, posed, skin,
                       distances, normals, contacts):
    """Accumulate linearized contact planes for vertices and cut face interiors."""
    count = len(points)
    size = 7
    hessian = np.zeros((count, size, size), np.float32)
    rhs = np.zeros((count, size), np.float32)
    worst = np.zeros((count, size), np.float32)
    requirement = np.zeros(count, np.float32)
    influence_scale = 5.0
    pair_by_pose = dict(contacts)
    witness = PREVIOUS["pair_witnesses"]
    for f, (clip, _, tree, bp, bt) in enumerate(samples):
        active = np.flatnonzero(distances[f] < MARGIN)
        vids = active[:,None]
        bary = np.ones((len(active),1),np.float32)
        grad = normals[f,active]
        gap = MARGIN-distances[f,active]

        overlap = pair_by_pose.get(f)
        blocks = [(vids,bary,grad,gap)]
        if overlap is not None:
            faces, b = witness(posed[f], triangles, bp, bt, overlap[:,::-1])
            tri = triangles[faces]
            xyz = np.einsum("nc,nci->ni", b, posed[f,tri])
            d,n,_ = directions(tree, xyz)
            order = np.lexsort((d,faces))
            deepest = order[np.r_[True, np.diff(faces[order])!=0]]
            deepest = deepest[d[deepest]<MARGIN]
            blocks.append((tri[deepest], b[deepest].astype(np.float32), n[deepest],
                           MARGIN-d[deepest]))
        for ids,b,n,need in blocks:
            if not len(ids):
                continue
            xyz_grad = np.einsum("ni,ncij->ncj", n, skin[f,ids,:,:3])
            by_bone = matrices[f,columns[ids]]
            location = np.einsum("ncqij,ncj->ncqi", by_bone[...,:3], points[ids])+by_bone[...,3]
            w_grad = np.einsum("ni,ncqi->ncq", n, location)
            w_grad -= np.sum(w_grad*weights[ids],axis=2,keepdims=True)
            jac = np.concatenate((xyz_grad, influence_scale*w_grad), axis=2)
            projected = jac * (need/(np.sum(jac**2*b[...,None],axis=(1,2)).clip(.08)))[:,None,None]
            ids_flat = ids.ravel()
            step_strength = (need[:,None] * b).ravel()
            # Track a worst constraint in addition to the least-squares fit.
            order = np.lexsort((-step_strength, ids_flat))
            order = order[np.r_[True,np.diff(ids_flat[order])!=0]]
            ids_unique = ids_flat[order]
            use = step_strength[order]>requirement[ids_unique]
            requirement[ids_unique[use]] = step_strength[order[use]]
            worst[ids_unique[use]] = projected.reshape(-1,size)[order[use]]
            strength = (b*np.sqrt(need[:,None]/MARGIN).clip(.25,3)).ravel()
            g = jac.reshape(-1,size)
            np.add.at(rhs,ids_flat,g*(strength*np.broadcast_to(need[:,None],b.shape).ravel())[:,None])
            np.add.at(hessian,ids_flat,(g*strength[:,None])[:,:,None]*g[:,None,:])
    diagonal = np.trace(hessian,axis1=1,axis2=2)*.026+.22
    hessian += diagonal[:,None,None]*np.diag((1,1,1,.65,.65,.65,.65))
    least = np.linalg.solve(hessian,rhs[...,None])[...,0]
    return least, worst, requirement, influence_scale


def spread_required(step, links, passes=3):
    smooth = step.copy()
    for _ in range(passes):
        smooth = .58*smooth+.42*average(smooth,links)
    length = np.linalg.norm(step,axis=1)
    axis = step/length[:,None].clip(1e-9)
    short = np.maximum(0,length-(axis*smooth).sum(axis=1))
    return smooth+axis*short[:,None]


def bound_delta(step, limit):
    length = np.linalg.norm(step, axis=1)
    return step * np.minimum(1,limit/length.clip(1e-9))[:,None]


def reweight(weights, columns, count, links, factor):
    expanded = full_weights(weights,columns,count)
    mixed = np.take_along_axis(average(expanded,links), columns,axis=1)
    mixed /= mixed.sum(axis=1,keepdims=True).clip(1e-10)
    return simplex(weights+factor[:,None]*(mixed-weights))


def local_move(points, original, weights, columns, triangles, samples, matrices, posed, skin,
               distances, normals, contacts, links, iteration):
    rest_tree = samples[0][2]
    least, worst, requirement, influence_scale = gather_constraints(
        points,weights,columns,triangles,samples,matrices,posed,skin,distances,normals,contacts)
    active = np.flatnonzero(requirement>.00015)
    if not len(active):
        return points.copy(),weights.copy()
    # Include the most constrained several half-frames in each clip, retain
    # the worst surface-normal bake, and test joint blends against real BVHs.
    blocks = [np.asarray([i for i,sample in enumerate(samples) if sample[0]==clip])
              for clip in CLIPS]
    rows = np.concatenate([block[np.argpartition(distances[block], 4, axis=0)[:5]]
                           for block in blocks])
    rest, rest_normal, _ = clearance(rest_tree, points)
    p = points[active]
    w = weights[active]
    radius = .012 if iteration < 6 else (.008 if iteration < 12 else .0055)
    step = bound_delta(least[active,:3], radius)
    closest = bound_delta(worst[active,:3], .03)
    closest = bound_delta(closest, 1.5*radius)
    outward = rest_normal[active]*np.minimum(CAP-.0002-rest[active], radius*1.1)[:,None]
    axes = np.eye(3,dtype=np.float32)
    alternatives = [np.zeros_like(p), step, step*1.6, closest, .55*closest+.55*step,
                    outward, .5*outward]
    alternatives += [np.broadcast_to(sign*axis*radius*.77,p.shape)
                     for axis in axes for sign in (-1,1)]
    choices = [p+move for move in alternatives]
    nw = simplex(w+least[active,3:]*influence_scale)
    ww = simplex(w+worst[active,3:]*influence_scale)
    wp = simplex(w+least[active,3:]*influence_scale*1.7)
    coefficients = [w, nw, wp, ww, nw, nw, w] + [w]*6
    for change in (nw, ww, wp):
        choices.append(p)
        coefficients.append(change)
    for axis in np.eye(4,dtype=np.float32):
        choices += [p+step, p+.4*outward]
        coefficients += [.70*w+.30*axis,.44*w+.56*axis]
    for move in (step, closest):
        choices.append(p+move)
        coefficients.append(w)

    original_active = original[active]
    choices = np.stack(choices,axis=1)
    coefficients = np.stack(coefficients,axis=1)
    count = choices.shape[1]
    bounds = np.repeat(original_active,count,axis=0)
    choices = project_rest(choices.reshape(-1,3), bounds, rest_tree).reshape(-1,count,3)
    choices[:,0] = p
    chosen = np.zeros(len(active),dtype=np.int32)
    for i, vertex in enumerate(active):
        frames = np.unique(rows[:,vertex])
        mats = matrices[frames[:,None],columns[vertex,None]]
        mx = np.einsum("fqij,cq->fcij", mats, coefficients[i])
        xyz = np.einsum("fcij,cj->fci", mx[...,:3], choices[i])+mx[...,3]
        d = np.stack([clearance(samples[f][2],values)[0] for f,values in zip(frames,xyz)])
        gap = np.maximum(MARGIN-d,0)*1000
        shape = np.sum(((choices[i]-original[vertex])*1000)**2,axis=1)
        change = np.sum((coefficients[i]-w[i])**2,axis=1)
        mean = np.mean(gap**2,axis=0)
        cost = 1.0*gap.max(axis=0)**2 + 1.6*mean + .017*shape + 6*change
        chosen[i] = cost.argmin()
    step = np.zeros_like(points)
    step[active] = choices[np.arange(len(active)),chosen]-p
    # Neighboring vertices take part of a local loft. The smoothing retains
    # the chosen correction along each active vertex's displacement.
    step = spread_required(step,links)
    new_points = rest_guard(project_rest(points+step,original,rest_tree),
                            points,original,triangles,rest_tree)
    new_weights = weights.copy()
    new_weights[active] = coefficients[np.arange(len(active)),chosen]
    x,_,z = points.T
    transition = ((z>.47)&(abs(x)>.07)) | (z<.435)
    amount = np.where(transition,.19,.10)
    weights_out = reweight(new_weights,columns,matrices.shape[1],links,amount)
    return new_points, weights_out


def initial_fit():
    scene,arm,body,garment,names,original,prior_weights,samples,matrices = base_state()
    triangles = triangulation(garment)
    adj = neighbors(garment.data)
    points = original.copy()
    weights,columns = sparse_weights(prior_weights)
    best = None
    retries = 0
    for iteration in range(5):
        posed,skin = skin_poses(points,weights,columns,matrices)
        d,n,_,contacts,summary = inspect_motion(points,triangles,samples,posed)
        rank = target_rank(d,summary)
        log_sweep(f"ITERATION {iteration}",d,summary)
        pass_rest = ((d[0]>=FLOOR)&(d[0]<=CAP)).all() and summary["rest"]["pairs"]==0
        if pass_rest and (best is None or rank<best[0]):
            best = rank,iteration,points.copy(),weights.copy()
            export(scene,arm,body,garment,points,full_weights(weights,columns,len(names)),names)
            print("SAVED BEST",iteration,flush=True)
            retries = 0
        else:
            retries += 1
        if iteration==4 or (pass_rest and all(r["failing_frames"]==0 for r in summary.values())):
            break
        if retries >= 2 and best is not None:
            points,weights = (array.copy() for array in best[2:4])
            posed,skin = skin_poses(points,weights,columns,matrices)
            d,n,_,contacts,summary = inspect_motion(points,triangles,samples,posed)
            retries = 0
        points,weights = local_move(points,original,weights,columns,triangles,samples,matrices,
                                    posed,skin,d,n,contacts,adj,iteration)
    assert best is not None, "No rest-compliant result"
    return pass_rest and all(r["failing_frames"]==0 for r in summary.values())


def check():
    """Run each supplied checker with its original sample and measure code."""
    for stem in ("motion_check", "motion_check_tri"):
        path = HERE/f"{stem}.py"
        source = path.read_text().split("sc.render.engine=",1)[0]
        # Both original scripts write motion_check.json. Persist the same res
        # independently, and use the textured CPU render stage for the PNGs.
        source += f'json.dump(res, open({str(HERE/f"{stem}.json")!r}, "w"), indent=2)\n'
        old_argv = sys.argv
        sys.argv = [str(path),"--",str(MASTER),str(MOTION),str(GLB),str(HERE)]
        output = io.StringIO()
        try:
            with redirect_stdout(output):
                exec(compile(source,str(path),"exec"),{"__name__": "__main__"})
        finally:
            sys.argv = old_argv
        result = "\n".join(line for line in output.getvalue().splitlines()
                           if line.startswith("RESULT "))
        (HERE/f"{stem}.txt").write_text(result+"\n")
        print(result,flush=True)


def glb_metadata(path):
    blob = path.read_bytes()
    magic, version, size, json_size, tag = struct.unpack_from("<4sIII4s", blob)
    assert magic == b"glTF" and version == 2 and size == len(blob) and tag == b"JSON"
    return json.loads(blob[20:20+json_size]), memoryview(blob)[28+json_size:]


def embedded_textures(document, binary):
    textures = []
    for item in document["images"]:
        view = document["bufferViews"][item["bufferView"]]
        start = view.get("byteOffset", 0)
        raw = binary[start:start+view["byteLength"]]
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"
        textures.append({
            "size": list(struct.unpack_from(">II", raw, 16)),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
    return textures


def glb_structure(names):
    document, binary = glb_metadata(GLB)
    original, original_binary = glb_metadata(ROUND_ONE/"dress_v1.glb")
    textures = embedded_textures(document, binary)
    joints = [document["nodes"][index]["name"] for index in document["skins"][0]["joints"]]
    assert len(document["skins"]) == 1 and len(joints) == len(names) == 65
    assert set(joints) == set(names)
    assert len(document["meshes"]) == 1 and not document.get("animations")
    assert all(max(texture["size"]) <= 1024 for texture in textures)
    assert all("TEXCOORD_0" in primitive["attributes"]
               for primitive in document["meshes"][0]["primitives"])
    return {
        "bytes": GLB.stat().st_size,
        "blend_bytes": BLEND.stat().st_size,
        "joints": len(joints),
        "meshes": len(document["meshes"]),
        "animations": len(document.get("animations", [])),
        "textures": textures,
        "round_one_texture_bytes_identical": textures == embedded_textures(original, original_binary),
        "round_one_material_identical": document["materials"] == original["materials"],
    }


def boundary_loops(garment):
    mesh = bmesh.new()
    mesh.from_mesh(garment.data)
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=1e-6)
    boundary = {edge for edge in mesh.edges if edge.is_boundary}
    loops = []
    while boundary:
        stack = [boundary.pop()]
        points = set()
        while stack:
            edge = stack.pop()
            for vertex in edge.verts:
                if vertex in points:
                    continue
                points.add(vertex)
                adjacent = boundary.intersection(vertex.link_edges)
                stack.extend(adjacent)
                boundary.difference_update(adjacent)
        coords = np.asarray([tuple(v.co) for v in points])
        center = coords.mean(axis=0)
        name = ("hem" if center[2]<.35 else "neck" if abs(center[0])<.05 else
                "left cuff" if center[0]>0 else "right cuff")
        loops.append({"zone": name, "vertices": len(coords), "center_m": center.tolist(),
                      "min_m": coords.min(axis=0).tolist(), "max_m": coords.max(axis=0).tolist()})
    non_manifold = sum(len(edge.link_faces)>2 for edge in mesh.edges)
    mesh.free()
    return sorted(loops,key=lambda item:item["zone"]), non_manifold


def verify():
    scene, arm, body, garment = PREVIOUS["read_export"](GLB)
    points = mesh_points(garment.data)
    triangles = triangulation(garment)
    names = tuple(bone.name for bone in arm.data.bones)
    weights = read_weights(garment,names)
    samples, _, poses = cache_samples(scene,arm,body,names,garment=garment)
    result, rest, _, hits, _, _ = PREVIOUS["scan"](
        points,triangles,samples,poses,report=True,body_names=PREVIOUS["zone_names"](body,names))
    zones = PREVIOUS["section"](points)
    stats = PREVIOUS["stats"]
    loop_stats, non_manifold = boundary_loops(garment)
    knee_height = {name.split(":")[-1]: float((arm.matrix_world@arm.data.bones[name].head_local).z)
                   for name in names if name.split(":")[-1] in {"LeftLeg", "RightLeg"}}
    positions = rest_sample_positions(poses[0],triangles)
    surface_samples = clearance(samples[0][2],positions.reshape(-1,3))[0]
    dense = {"glb_sha256": sha(GLB), "blend_sha256": sha(BLEND),
             "blender": bpy.app.version_string, **glb_structure(names),
             "vertices": len(points), "triangles": len(triangles), "poses": len(samples),
             "influences_max": int((weights>0).sum(axis=1).max()),
             "max_weight_sum_error": float(np.abs(weights.sum(axis=1)-1).max()),
             "overlap_faces": int((hits>0).sum()), "rest_over_30mm": int((rest>CAP).sum()),
             "rest_clearance": {"all": stats(rest), **{zone: stats(rest[zones==zone])
                                                       for zone in np.unique(zones)}},
             "boundaries": loop_stats, "non_manifold_cross_edges": non_manifold,
             "knee_joint_z_m": knee_height, "rest_triangle_sample_clearance": stats(surface_samples),
             "rest_triangle_samples_under_0_5mm": int((surface_samples<FLOOR).sum()),
             "rest_triangle_samples_over_30mm": int((surface_samples>CAP).sum()),
             "results": result}
    assert len(triangles)<=TRIANGLE_LIMIT
    (HERE/"dense_check.json").write_text(json.dumps(dense,indent=2)+"\n")
    PREVIOUS["report_status"](result)


def render():
    scene,arm,body,garment = PREVIOUS["read_export"](GLB)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "AgX"
    scene.world = bpy.data.worlds.new("Dress QA studio")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (.31,.35,.43,1)
    background.inputs[1].default_value = .50
    for obj in list(scene.objects):
        if obj.type == "LIGHT":
            bpy.data.objects.remove(obj,do_unlink=True)
    light = PREVIOUS["light"]
    light(scene,"Key",(-1,-2,2.4),200,1.25,(0,0,.5))
    light(scene,"Fill",(1.1,-1.5,.6),85,1.3,(0,0,.5))
    light(scene,"Rim",(.4,1.2,1.5),140,1.1,(0,0,.5))
    camera = bpy.data.cameras.new("Dress QA")
    camera.type = "ORTHO"
    view = bpy.data.objects.new("Dress QA",camera)
    scene.collection.objects.link(view)
    scene.camera = view

    def capture(filename, direction, target, scale):
        view.location = Vector(target)+Vector(direction).normalized()*2.8
        view.rotation_euler = (Vector(target)-view.location).to_track_quat("-Z","Y").to_euler()
        camera.ortho_scale = scale
        scene.render.filepath = str(HERE/filename)
        bpy.ops.render.render(write_still=True)

    rest_views = (("front",(0,-1,0)),("back",(0,1,0)),("left",(1,0,0)),
                  ("right",(-1,0,0)),("three-quarter",(.65,-1,.16)),
                  ("dress only",(.37,-1,.30)))
    set_pose(scene,arm,"rest",1)
    tile = 500
    scene.render.resolution_x = scene.render.resolution_y = tile
    sheet = np.zeros((2*tile,3*tile,4),dtype=np.float32)
    temporary = HERE/".rest_tile.png"
    try:
        for index,(label,direction) in enumerate(rest_views):
            body.hide_render = label=="dress only"
            capture(temporary.name,direction,(0,-.011,.426),.59)
            img = bpy.data.images.load(str(temporary),check_existing=False)
            pixels = np.empty(tile*tile*4,dtype=np.float32)
            img.pixels.foreach_get(pixels)
            row,col = 1-index//3,index%3
            sheet[row*tile:(row+1)*tile,col*tile:(col+1)*tile] = pixels.reshape(tile,tile,4)
            bpy.data.images.remove(img)
            temporary.unlink()
    finally:
        temporary.unlink(missing_ok=True)
    sheet_img = bpy.data.images.new("Six dress views",width=3*tile,height=2*tile,alpha=True)
    sheet_img.pixels.foreach_set(sheet.ravel())
    sheet_img.filepath_raw = str(HERE/"six_view.png")
    sheet_img.file_format = "PNG"
    sheet_img.save()

    body.hide_render = False
    scene.render.resolution_x = scene.render.resolution_y = 720
    report_path = HERE/"dense_check.json"
    dense = json.loads(report_path.read_text())
    assert dense["glb_sha256"] == sha(GLB)
    results = dense["results"]
    render_frames = {}
    for clip in ("walk","run","wave","jump"):
        frame = results[clip]["min_frame"]
        set_pose(scene,arm,clip,frame)
        coords,_ = PREVIOUS["posed_mesh"](body,bpy.context.evaluated_depsgraph_get())
        coords = np.asarray(coords)
        side = math.copysign(1, results[clip]["min_rest_xyz"][0])
        direction = (side*.55,-1,.10)
        rotation = Vector(direction).to_track_quat("Z","Y")
        camera_axes = np.asarray(rotation.to_matrix())
        projected = coords@camera_axes
        low, high = projected.min(axis=0), projected.max(axis=0)
        center = camera_axes@((low+high)*.5)
        scale = max((high-low)[:2]) * 1.10
        capture(f"{clip}.png",direction,center,scale)
        render_frames[clip] = frame
    dense["render"] = {
        "engine": "Cycles CPU",
        "samples": scene.cycles.samples,
        "six_view_order": [label for label,_ in rest_views],
        "frames": render_frames,
        "sha256": {filename: sha(HERE/filename)
                   for filename in ("six_view.png","walk.png","run.png","wave.png","jump.png")},
    }
    report_path.write_text(json.dumps(dense,indent=2)+"\n")


def sparse_weights(weights):
    columns = np.argsort(-weights,axis=1,kind="stable")[:,:4]
    return np.take_along_axis(weights,columns,axis=1),columns


def ring_lists(mesh):
    links = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a,b = edge.vertices
        links[a].append(b)
        links[b].append(a)
    return links


def stable_update(points, original, weights, columns, triangles, samples, matrices,
                  posed, skin, distances, normals, contacts, adj, rings, iteration):
    """Test neighbor-aware local motion before smoothing the rest displacement."""
    least, _, required, weight_scale = gather_constraints(
        points,weights,columns,triangles,samples,matrices,posed,skin,distances,normals,contacts)
    active = np.flatnonzero(required>.00025)
    tree = samples[0][2]
    x,_,z = original.T
    lower = z<.413
    arms = (abs(x)>.072)&(z>.473)
    trust = .008 if iteration<11 else .005
    backup = points.copy()
    _, out, _ = clearance(tree,points)
    step = bound_delta(least[:,:3],trust)
    vertex = np.arange(len(points))
    frame = np.argmin(distances[1:],axis=0)+1
    max_gap = np.clip(MARGIN-distances[frame,vertex],0,.03)
    closest = np.einsum("vij,vi->vj",skin[frame,vertex,:,:3],normals[frame,vertex])
    closest /= np.linalg.norm(closest,axis=1,keepdims=True).clip(1e-8)
    bake = closest*max_gap[:,None]
    # Keep the 30 mm bound on the requested nearest-surface bake. Smaller
    # alternatives prevent foldovers where several clips disagree.
    axes = np.eye(3,dtype=np.float32)
    outward = out*trust
    offset_grid = np.stack([np.zeros_like(points), step, step*1.4, bake, .50*bake,
                            bound_delta(bake,trust), outward, .5*outward,
                            *[np.broadcast_to(sign*axis*trust*.78,points.shape)
                              for axis in axes for sign in (-1,1)]])
    risk = [np.flatnonzero([sample[0]==clip for sample in samples]) for clip in CLIPS]
    rows = np.concatenate([block[np.argpartition(distances[block],2,axis=0)[:3]]
                           for block in risk])
    delta_w = least[:,3:]*weight_scale
    change_cap = np.where(arms,.135,np.where(lower,.095,.10))
    change_norm = np.linalg.norm(delta_w,axis=1)
    delta_w *= np.minimum(1,change_cap/change_norm.clip(1e-8))[:,None]
    new_w = simplex(weights+delta_w)
    w_count = len(offset_grid)
    candidate_offsets = offset_grid[:,active].transpose(1,0,2)
    candidates = points[active,None,:]+candidate_offsets
    candidates = np.concatenate((candidates,points[active,None,:]+candidate_offsets[:,:8]),axis=1)
    count = candidates.shape[1]
    coefficients = np.concatenate((np.broadcast_to(weights[active,None,:],(len(active),w_count,4)),
                                   np.broadcast_to(new_w[active,None,:],(len(active),8,4))),axis=1)
    candidates = project_rest(candidates.reshape(-1,3),np.repeat(original[active],count,axis=0),tree)
    candidates = candidates.reshape(-1,count,3)
    candidates[:,0] = points[active]
    requested = np.zeros_like(points)
    updates = weights.copy()

    for i,v in enumerate(active):
        frames = np.unique(np.r_[rows[:,v],frame[v]])
        mats = matrices[frames[:,None],columns[v,None]]
        transform = np.einsum("fqij,cq->fcij",mats,coefficients[i])
        locations = np.einsum("fcij,cj->fci",transform[...,:3],candidates[i])+transform[...,3]
        ring = np.asarray(rings[v],dtype=np.int32)
        # Evaluate four evenly spaced neighbors, plus the worst current edge.
        proxy = ring[np.linspace(0,len(ring)-1,min(4,len(ring)),dtype=int)]
        neighbors_pose = posed[frames[:,None],proxy]
        lengths = np.linalg.norm(locations[:,:,None]-neighbors_pose[:,None],axis=-1)
        baseline_length = lengths[:,0]
        edge_allowance = baseline_length + .0025 + .28*np.linalg.norm(
            original[proxy]-original[v],axis=1)
        strain = np.maximum(lengths-edge_allowance[:,None],0)*1000
        gaps = []
        for f, positions, link in zip(frames,locations,neighbors_pose):
            edge_middle = .50*positions[:,None,:]+.50*link[None,:,:]
            check = np.vstack((positions,edge_middle.reshape(-1,3)))
            signed = clearance(samples[f][2],check)[0]
            gaps.append(np.column_stack((signed[:count],signed[count:].reshape(count,-1))))
        deficit = np.maximum(MARGIN-np.asarray(gaps),0)*1000
        cost = (deficit[:,:,0].max(axis=0)**2 + 1.4*np.mean(deficit[:,:,0]**2,axis=0)
                + .68*np.mean(deficit[:,:,1:].max(axis=2)**2,axis=0)
                + .40*deficit[:,:,1:].max(axis=(0,2))**2)
        cost += .70*strain.max(axis=(0,2))**2 + .5*np.mean(strain**2,axis=(0,2))
        displacement = (candidates[i]-original[v])*1000
        reference_mean = ((points[ring]-original[ring]).mean(axis=0))*1000
        cost += .035*np.sum(displacement**2,axis=1)
        cost += .33*np.sum((displacement-reference_mean)**2,axis=1)
        choice = int(cost.argmin())
        requested[v] = candidates[i,choice]-points[v]
        updates[v] = coefficients[i,choice]

    planned = spread_required(requested,adj,passes=4)
    # Bounded smoothing of the accumulated offset controls creasing in rest.
    # Every candidate is checked again after the rest and topology guards.
    offset = backup+planned-original
    for _ in range(2):
        offset = .70*offset+.30*average(offset,adj)
    candidate = project_rest(original+offset,original,tree)
    candidate = rest_guard(candidate,backup,original,triangles,tree)
    return candidate,reweight(updates,columns,matrices.shape[1],adj,np.where(arms,.24,.18))


def transfer_split_reference(points, triangles, reference, split_points):
    tree = BVHTree.FromPolygons(points.tolist(),triangles.tolist(),all_triangles=True)
    nearest = [tree.find_nearest(point) for point in split_points.tolist()]
    faces = triangles[[hit[2] for hit in nearest]]
    centers = np.asarray([tuple(hit[0]) for hit in nearest],dtype=np.float32)
    weights = PREVIOUS["barycentric"](points[faces],centers)
    return np.einsum("nc,nci->ni", weights, reference[faces])


def stable_fit(checkpoint, resume_at_six=False):
    bpy.ops.wm.open_mainfile(filepath=str(checkpoint))
    saved = bpy.context.scene.objects["Dress"]
    seed = mesh_points(saved.data)
    saved_names = tuple(bone.name for bone in bpy.context.scene.objects["Armature"].data.bones)
    seed_weights = read_weights(saved,saved_names)
    scene,arm,body,garment,names,original,initial,samples,matrices = base_state()
    assert names == saved_names
    assert len(seed)==len(original)
    triangles = triangulation(garment)
    adj = neighbors(garment.data)
    rings = ring_lists(garment.data)
    tree = samples[0][2]
    z = original[:,2]
    retention = .14+.76*smoothstep(.31,.455,z)
    offset = (seed-original)*retention[:,None]
    for _ in range(4):
        offset = .52*offset+.48*average(offset,adj)
    if resume_at_six:
        points, initial_seed = seed, seed_weights
    else:
        points = rest_guard(project_rest(original+offset,original,tree),original,original,triangles,tree)
        initial_seed = limit_weights(initial+(seed_weights-initial)*retention[:,None])
    weights,columns = sparse_weights(initial_seed)
    reference = original.copy()
    best = None
    for iteration in range(6 if resume_at_six else 5,ITERATIONS+1):
        posed,skin = skin_poses(points,weights,columns,matrices)
        d,n,hits,contacts,summary = inspect_motion(points,triangles,samples,posed)
        log_sweep(f"REFINE {iteration}",d,summary)
        rank = target_rank(d,summary)
        admissible = ((d[0]>=FLOOR)&(d[0]<=CAP)).all() and summary["rest"]["pairs"]==0
        solved = admissible and all(r["failing_frames"]==0 for r in summary.values())
        if admissible and (solved or best is None or rank<best[0]):
            best = rank,iteration,points.copy(),weights.copy(),columns.copy(),len(triangles)
            export(scene,arm,body,garment,points,full_weights(weights,columns,len(names)),names)
            print("REFINED BEST",iteration,flush=True)
        if iteration==ITERATIONS or solved:
            break
        if iteration in (6,10,13) and hits.any():
            expanded = full_weights(weights,columns,len(names))
            if iteration == 6:
                # Use the same influence ordering as an editable checkpoint.
                weights,columns = sparse_weights(expanded)
            previous_points = points
            split = subdivide(garment,points,expanded,names,triangles,hits,.012,
                              min(TRIANGLE_LIMIT-len(triangles),1250),loft=iteration>=10)
            if split:
                old_n = len(previous_points)
                points = mesh_points(garment.data)
                assert np.allclose(points[:old_n],previous_points,atol=1e-7)
                added = transfer_split_reference(previous_points,triangles,reference,points[old_n:])
                reference = np.vstack((reference,added))
                next_weights,next_columns = sparse_weights(limit_weights(read_weights(garment,names,validate=False)))
                next_columns[:old_n],next_weights[:old_n] = columns,weights
                triangles = triangulation(garment)
                adj = neighbors(garment.data)
                rings = ring_lists(garment.data)
                # Midpoints can fall below the rest margin on concave panels.
                # Clear those adjacent to the split using their own local loft.
                points = rest_guard(project_rest(points,reference,tree),points,reference,triangles,tree,
                                    orientation_reference=points)
                weights,columns = next_weights,next_columns
                continue
        if best is not None and best[5]==len(triangles) and rank[0]>best[0][0]*1.10:
            points,weights,columns = (item.copy() for item in best[2:5])
            posed,skin = skin_poses(points,weights,columns,matrices)
            d,n,hits,contacts,summary = inspect_motion(points,triangles,samples,posed)
        points,weights = stable_update(points,reference,weights,columns,triangles,samples,matrices,
                                       posed,skin,d,n,contacts,adj,rings,iteration)
    assert best is not None
    print("SELECTED REFINED ITERATION",best[1],best[5],best[0],flush=True)


REST_BARYCENTRICS = np.asarray(((1/3,1/3,1/3),(.5,.5,0),(0,.5,.5),(.5,0,.5)),dtype=np.float32)


def rest_sample_positions(points, triangles):
    return np.einsum("bc,tci->tbi",REST_BARYCENTRICS,points[triangles])


def adjust_rest():
    """Project excess rest clearance at triangle centers and edge midpoints."""
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    scene = bpy.context.scene
    arm,body,garment = (scene.objects[name] for name in ("Armature","Base_Body","Dress"))
    arm.animation_data_create()
    tree = BVHTree.FromPolygons(*PREVIOUS["posed_mesh"](body,bpy.context.evaluated_depsgraph_get()),
                                all_triangles=True)
    initial = mesh_points(garment.data)
    points = initial.copy()
    triangles = triangulation(garment)
    adj = neighbors(garment.data)
    for _ in range(18):
        check = rest_sample_positions(points,triangles)
        signed,normal,_ = clearance(tree,check.reshape(-1,3))
        print("REST SURFACE",float(signed.min()),float(signed.max()),flush=True)
        if signed.min()>=.00082 and signed.max()<=CAP-.0011:
            if not np.array_equal(initial,points):
                names = tuple(bone.name for bone in arm.data.bones)
                export(scene,arm,body,garment,points,read_weights(garment,names),names)
            return
        correction = np.clip(signed,.00098,CAP-.00165)-signed
        rows, = np.where(abs(correction)>.00005)
        corners = triangles[rows//len(REST_BARYCENTRICS)]
        factor = REST_BARYCENTRICS[rows%len(REST_BARYCENTRICS)]
        adjustment = correction[rows,None]*normal[rows]
        adjustment = adjustment[:,None,:]*(factor/np.sum(factor**2,axis=1,keepdims=True))[:,:,None]
        delta = np.zeros_like(points)
        degree = np.zeros(len(points),dtype=np.float32)
        np.add.at(delta,corners.ravel(),adjustment.reshape(-1,3))
        np.add.at(degree,corners.ravel(),(factor>0).ravel())
        delta /= degree.clip(1)[:,None]
        delta = .89*delta+.15*average(delta,adj)
        candidate = initial + bound_delta(points+delta-initial,.0065)
        points = rest_guard(candidate,points,initial,triangles,tree)
    print("REST SURFACE PATCH DID NOT PASS",flush=True)


def tighten_exported_rest():
    """Handle the last sub-millimeter discrepancies on the reimported GLB."""
    for _ in range(4):
        _,_,body,garment = PREVIOUS["read_export"](GLB)
        graph = bpy.context.evaluated_depsgraph_get()
        tree = BVHTree.FromPolygons(*PREVIOUS["posed_mesh"](body,graph),all_triangles=True)
        evaluated = garment.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            posed = mesh_points(mesh)
            triangles = np.asarray(mesh_triangles(mesh),dtype=np.int32)
        finally:
            evaluated.to_mesh_clear()
        exported = mesh_points(garment.data)
        signed,normal,_ = clearance(tree,rest_sample_positions(posed,triangles).reshape(-1,3))
        rows, = np.where((signed>CAP)|(signed<FLOOR))
        print("REIMPORTED REST SURFACE",float(signed.min()),float(signed.max()),len(rows),flush=True)
        if not len(rows):
            return

        bpy.ops.wm.open_mainfile(filepath=str(BLEND))
        scene = bpy.context.scene
        arm,body,garment = (scene.objects[name] for name in ("Armature","Base_Body","Dress"))
        arm.animation_data_create()
        points = mesh_points(garment.data)
        delta = np.zeros_like(points)
        votes = np.zeros(len(points),dtype=np.float32)
        for row in rows:
            face = triangles[row//len(REST_BARYCENTRICS)]
            factor = REST_BARYCENTRICS[row%len(REST_BARYCENTRICS)]
            correction = (CAP-.00046 if signed[row]>CAP else .00083)-signed[row]
            for vertex, share in zip(face,factor):
                if share == 0:
                    continue
                distance = np.linalg.norm(points-exported[vertex],axis=1)
                match = int(np.argmin(distance))
                assert distance[match]<.00001
                strength = share/(factor@factor)
                delta[match] += correction*normal[row]*strength
                votes[match] += 1
        delta /= votes.clip(1)[:,None]
        faces = triangulation(garment)
        candidate = rest_guard(points+delta,points,points,faces,tree)
        if np.array_equal(candidate,points):
            return
        names = tuple(bone.name for bone in arm.data.bones)
        export(scene,arm,body,garment,candidate,read_weights(garment,names),names)


def build():
    if not initial_fit():
        stable_fit(BLEND)
    adjust_rest()
    tighten_exported_rest()


if __name__ == "__main__":
    modes = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else ["build"]
    for mode in modes:
        {"build": build, "rest": tighten_exported_rest, "check": check, "verify": verify, "render": render}[mode]()
