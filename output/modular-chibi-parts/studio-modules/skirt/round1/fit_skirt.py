"""Build a closed, skinned A-line skirt from the local Studio segmentation."""
from pathlib import Path
import hashlib
import json
import math
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
PARTS = HERE.parents[2]
SOURCE = HERE.parent / "source_studio_segmented.glb"
MASTER = PARTS / "master/GJH_Chibi_Master_rigged.blend"
GLB = HERE / "skirt_v1.glb"
BLEND = HERE / "skirt_v1.blend"
WORK = HERE / ".work"
SEED = WORK / "studio_skirt.blend"
N = "mixamorig:"
BANKS = {
    "shared": (PARTS / "body-fix/motion_fixed.glb",
               ("walk", "run", "wave", "jump", "idle", "nod", "dance")),
    "sit_hold": (PARTS / "actions-fix/actions_fixed.glb",
                 ("sit_down", "sit_idle", "stand_up", "hold_item")),
    "carry": (PARTS / "actions-hold2/hold_actions.glb",
              ("hold_box", "hold_bag", "take_item")),
}
COLLISION_FLOOR, REST_CAP = .0005, .030


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    (HERE / path).write_text(json.dumps(value, indent=2) + "\n")


def coords(obj, evaluated=False):
    if evaluated:
        obj = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    buffer = np.empty(3 * len(obj.data.vertices), dtype=np.float32)
    obj.data.vertices.foreach_get("co", buffer)
    matrix = np.array(obj.matrix_world, dtype=np.float32)
    return buffer.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3]


def faces(obj):
    obj.data.calc_loop_triangles()
    return np.array([tuple(tri.vertices) for tri in obj.data.loop_triangles], dtype=np.int32)


def master_scene():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body = scene.objects["Armature"], scene.objects["Base_Body"]
    body.hide_set(False)
    arm.animation_data_create()
    arm.animation_data.use_nla = False
    set_pose(scene, arm, None, 1)
    assert len(arm.data.bones) == 65
    return scene, arm, body


def set_pose(scene, arm, action, frame):
    channel = arm.animation_data
    if action is None or channel.action != action:
        channel.action = None
        for bone in arm.pose.bones:
            bone.matrix_basis = Matrix.Identity(4)
        if action:
            channel.action = action
            channel.action_slot = action.slots[0]
    scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.context.view_layer.update()


def load_actions(scene):
    collected = {}
    for bank, (path, clips) in BANKS.items():
        if bank != "shared":
            scene.render.fps, scene.render.fps_base = 30, 1
        previous, existing = set(bpy.data.actions), set(scene.objects)
        bpy.ops.import_scene.gltf(filepath=str(path))
        imported = set(bpy.data.actions) - previous
        for clip in clips:
            collected[clip], = [a for a in imported if a.name.split(".")[0] == clip]
            assert collected[clip].slots
            collected[clip].use_fake_user = True
        for obj in set(scene.objects) - existing:
            bpy.data.objects.remove(obj, do_unlink=True)
    return collected


def half_frames(first, last):
    first, last = round(float(first), 5), round(float(last), 5)
    return sorted({first, last, *(step / 2 for step in range(math.ceil(first * 2), math.floor(last * 2) + 1))})


def object_stats(obj):
    points = coords(obj)
    return {"triangles": len(faces(obj)), "vertices": len(points),
            "min_m": points.min(axis=0).tolist(), "max_m": points.max(axis=0).tolist()}


def tidy_material(obj):
    material, = obj.data.materials
    nodes = material.node_tree.nodes
    shader = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    image = shader.inputs["Base Color"].links[0].from_node.image
    for slot in ("Normal", "Roughness", "Metallic"):
        for link in tuple(shader.inputs[slot].links):
            material.node_tree.links.remove(link)
    shader.inputs["Roughness"].default_value = .65 if obj.name == "Studio Fabric" else .48
    shader.inputs["Metallic"].default_value = 0.0
    for node in list(nodes):
        if node.type == "TEX_IMAGE" and node.image != image:
            nodes.remove(node)
    assert max(image.size) <= 1024, tuple(image.size)
    return image.name


def extract():
    if SEED.exists():
        print("Reusing", SEED, flush=True)
        return
    WORK.mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    parts = {obj.name: obj for obj in bpy.context.scene.objects if obj.type == "MESH"}
    source_report = {name: object_stats(obj) for name, obj in sorted(parts.items())}
    keep = {"tripo_part_1": ("Studio Fabric", 26000),
            "tripo_part_6": ("Studio Belt", 11000)}
    for key in keep:
        obj = parts[key]
        world = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world
    for obj in list(bpy.context.scene.objects):
        if obj not in [parts[k] for k in keep]:
            bpy.data.objects.remove(obj, do_unlink=True)
    reduced = {}
    for key, (label, triangles) in keep.items():
        obj = parts[key]
        obj.name = label
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        modifier = obj.modifiers.new("Studio working mesh reduction", "DECIMATE")
        modifier.ratio = triangles / len(faces(obj))
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        image = tidy_material(obj)
        reduced[key] = {**object_stats(obj), "label": label, "base_color": image}
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(SEED))
    write_json("source_parts.json", {"source_sha256": digest(SOURCE), "source_parts": source_report,
                                     "working_parts": reduced})


def probe():
    scene, arm, body = master_scene()
    print("BODY", object_stats(body), "fps", scene.render.fps)
    for key in ("Hips", "Spine", "Spine1", "Spine2", "LeftUpLeg", "RightUpLeg", "LeftLeg", "RightLeg"):
        bone = arm.data.bones[N + key]
        print("BONE", key, tuple(bone.head_local), tuple(bone.tail_local))
    tree = BVHTree.FromPolygons(coords(body).tolist(), faces(body).tolist(), all_triangles=True)
    for z in np.arange(.24, .571, .01):
        row = []
        for angle in np.arange(0, 360, 30):
            direction = Vector((math.sin(math.radians(angle)), -math.cos(math.radians(angle)), 0))
            point, _, _, _ = tree.ray_cast(Vector((0, 0, z)) + direction, -direction)
            row.append(round(point.xy.length, 4) if point and point.dot(direction) > 0 else None)
        print(f"BODY RADIUS {z:.3f}", row)



def make_tree(points, triangles):
    return BVHTree.FromPolygons(points.tolist(), triangles.tolist(), all_triangles=True)


def source_scene():
    with bpy.data.libraries.load(str(SEED)) as (_, target):
        target.objects = ["Studio Fabric", "Studio Belt"]
    return target.objects


def nearest(tree, points):
    surface = np.empty_like(points)
    normals = np.empty_like(points)
    indices = np.empty(len(points), dtype=np.int32)
    for row, point in enumerate(points):
        surface[row], normals[row], indices[row], _ = tree.find_nearest(point)
    return np.einsum("ij,ij->i", points - surface, normals), surface, normals, indices


def studio_probe():
    scene, arm, body = master_scene()
    for obj in source_scene():
        v, f = coords(obj), faces(obj)
        tree = make_tree(v, f)
        print(obj.name, [tuple(n.image.size) for m in obj.data.materials for n in m.node_tree.nodes
                         if n.type == "TEX_IMAGE"])
        for z in np.arange(v[:,2].min()+.002, v[:,2].max(), .008):
            values = []
            for angle in np.arange(0, 360, 15):
                d = Vector((math.sin(math.radians(angle)), -math.cos(math.radians(angle)), 0))
                p, _, _, _ = tree.ray_cast(Vector((0, -.032, z)) + d, -d)
                values.append(round((p - Vector((0, -.032, z))).dot(d), 4) if p else None)
            print(round(z,4), values)


def cache_motion(scene, arm, body):
    keys = [N + name for name in ("Hips", "LeftUpLeg", "RightUpLeg", "Spine", "Spine1")]
    path = WORK / "motion.npz"
    inputs = [digest(MASTER), *(digest(f) for f, _ in BANKS.values())]
    if path.is_file():
        with np.load(path, allow_pickle=False) as data:
            if data["inputs"].tolist() == inputs:
                return tuple(data[key] for key in ("clips", "frames", "body", "triangles", "matrices"))
    actions = {"rest": None, **load_actions(scene)}
    bones = [arm.pose.bones[name] for name in keys]
    inverse = [bone.bone.matrix_local.inverted() for bone in bones]
    modes = [bone.rotation_mode for bone in arm.pose.bones]
    clips, frames, points, matrices = [], [], [], []
    triangles = faces(body)
    for name, action in actions.items():
        for frame in half_frames(*action.frame_range) if action else [1.]:
            set_pose(scene, arm, action, frame)
            clips.append(name)
            frames.append(frame)
            points.append(coords(body, evaluated=True))
            matrices.append(np.asarray([bone.matrix @ bind for bone, bind in zip(bones, inverse)],
                                       dtype=np.float32)[:, :3, :])
        print("Cached", name, len(frames), flush=True)
    assert modes == [bone.rotation_mode for bone in arm.pose.bones]
    set_pose(scene, arm, None, 1)
    data = tuple(map(np.asarray, (clips, frames, points, triangles, matrices)))
    np.savez(path, inputs=inputs, **dict(zip(("clips","frames","body","triangles","matrices"), data)))
    return data


def cache():
    cache_motion(*master_scene())



def sweep(points, triangles, weights, motion, selected=None, constraints=False):
    clips, frames, body, body_faces, matrices = motion
    if selected is None:
        selected = np.arange(len(clips))
    transforms = np.einsum("vk,fkij->fvij", weights, matrices[selected], optimize=True)
    posed = np.einsum("fvij,vj->fvi", transforms[:, :, :, :3], points) + transforms[:, :, :, 3]
    distances = np.empty(posed.shape[:2], dtype=np.float32)
    overlaps = np.zeros(len(selected), dtype=np.int32)
    directions, zones = [], []
    face_list = triangles.tolist()
    body_list = body_faces.tolist()
    for i, row in enumerate(selected):
        tree = BVHTree.FromPolygons(body[row].tolist(),body_list,all_triangles=True)
        gap, _, normals, _ = nearest(tree, posed[i])
        garment = BVHTree.FromPolygons(posed[i].tolist(),face_list,all_triangles=True)
        pairs = tree.overlap(garment)
        distances[i] = gap
        overlaps[i] = len(pairs)
        if constraints:
            directions.append(normals)
            zones.append(np.unique(np.array(pairs)[:,1]) if pairs else np.empty(0,dtype=np.int64))
    return distances, overlaps, transforms, posed, np.asarray(directions), zones


def short_result(result, motion, selected):
    d,p = result[:2]
    clips, frames = motion[:2]
    for name in dict.fromkeys(clips[selected]):
        ix = np.flatnonzero(clips[selected] == name)
        row,col = np.unravel_index(d[ix].argmin(),d[ix].shape)
        print(name, len(ix), "pair peak", int(p[ix].max()), "inside peak",
              int((d[ix]<0).sum(axis=1).max()), "min mm", round(1000*float(d[ix[row],col]),4),
              "frame", frames[selected[ix[row]]], "node", col, flush=True)
    print("REST MAX", float(d[0].max())*1000, "PAIRS", int(p.sum()),
          "GAPS", int((d<.0005).sum()), flush=True)


def baseline(hem=".285",flare="1.0",leg="1.0",lift=".010"):
    from skirt_surface import build_loft
    scene,arm,body = master_scene()
    motion = cache_motion(scene,arm,body)
    rest = make_tree(motion[2][0],motion[3])
    parameters = tuple(map(float,(hem,flare,leg,lift)))
    p,t,w,paired,depth,theta = build_loft(body,rest,*parameters)
    selected = np.unique(np.r_[np.arange(0,len(motion[0]),4),
                               np.flatnonzero(np.isin(motion[0], ["run", "sit_down", "sit_idle","stand_up"]))])
    result = sweep(p,t,w,motion,selected)
    print("Parameters",parameters,flush=True)
    short_result(result,motion,selected)
    np.savez(WORK/"baseline.npz",points=p,triangles=t,weights=w,paired=paired,depth=depth,theta=theta)


def solve(iterations="14",resume="no"):
    from skirt_contact import optimize
    scene,arm,body = master_scene()
    motion = cache_motion(scene,arm,body)
    optimize(motion,body,WORK/"baked.npz",int(iterations),resume=="yes")


def write_mesh(points, triangles, weights, source_objects, depth, theta, arm, finish_cloth=False):
    from skirt_surface import CONTROLS
    from skirt_uv import assign_uv
    scene = bpy.context.scene
    mesh = bpy.data.meshes.new("Pleated Skirt")
    mesh.from_pydata(points.tolist(),[],triangles.tolist())
    garment = bpy.data.objects.new(mesh.name,mesh)
    scene.collection.objects.link(garment)
    for source,label in zip(source_objects,("Studio Green Fabric","Studio Brass Belt"),strict=True):
        material = source.data.materials[0]
        material.name = label
        garment.data.materials.append(material)
    uv_report = assign_uv(garment,source_objects,triangles,depth,theta)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    mesh.update()
    if finish_cloth:
        from skirt_surface import finish_fabric
        finish_fabric(mesh,depth,theta)
    for i,key in enumerate(CONTROLS):
        group = garment.vertex_groups.new(name=N+key)
        for vertex in np.flatnonzero(weights[:,i]):
            group.add([int(vertex)],float(weights[vertex,i]),"REPLACE")
    garment.modifiers.new("Master Skin","ARMATURE").object = arm
    garment.parent = arm
    garment["source_parts"] = "tripo_part_1 and tripo_part_6"
    garment["pleat_count"] = 10
    return garment,uv_report


def export_glb(arm, garment, path):
    bpy.ops.object.select_all(action="DESELECT")
    garment.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = garment
    garment.parent = None
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True,
                             export_animations=False, export_all_influences=False,
                             export_keep_originals=False, export_tangents=False)
    garment.parent = arm


def finish(checkpoint="baked.npz", draft="no"):
    scene,arm,body = master_scene()
    sources = source_scene()
    path = HERE / checkpoint
    if not path.is_file():
        path = WORK / checkpoint
    with np.load(path) as data:
        points,triangles,weights,depth,theta,parameters = (
            data[key] for key in ("points","triangles","weights","depth","theta","parameters"))
        offset = data["buckle_offset"] if "buckle_offset" in data else (0.,0.,0.)
        scale = float(data["buckle_scale"]) if "buckle_scale" in data else 1.
        finish_cloth = bool(data.get("finish_cloth",False))
    from skirt_surface import add_buckle
    if scale > 0:
        points,triangles,weights = add_buckle(points,triangles,weights,offset,scale)
    assert len(triangles) <= 3500
    garment, uv_report = write_mesh(points,triangles,weights,sources,depth,theta,arm,finish_cloth)
    topology = bmesh.new()
    topology.from_mesh(garment.data)
    edges = list(topology.edges)
    volumes = topology.calc_volume(signed=True)
    assert all(edge.is_manifold and edge.is_contiguous for edge in edges) and volumes > 0
    topology.free()
    rest_tree = make_tree(coords(body,evaluated=True),faces(body))
    xyz = points[triangles]
    probes = np.concatenate((xyz.mean(axis=1),.5*(xyz+np.roll(xyz,1,axis=1)).reshape(-1,3)))
    gaps,surface,_,_ = nearest(rest_tree,points)
    sample_gaps,sample_surface,_,_ = nearest(rest_tree,probes)
    target = (WORK/"draft.glb") if draft=="yes" else GLB
    export_glb(arm,garment,target)
    if draft=="yes":
        return
    arm.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    for obj in list(scene.objects):
        if obj not in (arm,body,garment):
            bpy.data.objects.remove(obj,do_unlink=True)
    body.hide_render = False
    body.hide_set(False)
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.file.pack_all()
    prefs = bpy.context.preferences.filepaths
    prefs.save_version = 0
    if hasattr(prefs,"use_save_preview_images"):
        prefs.use_save_preview_images = False
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    write_json("build_metrics.json", {
        "glb_sha256":digest(GLB),"blend_sha256":digest(BLEND),
        "source_sha256":digest(SOURCE),"master_sha256":digest(MASTER),
        "triangles":len(triangles),"editable_vertices":len(points),"manifold_edges":len(edges),
        "nonmanifold_edges":0,"signed_volume_m3":volumes,"pleats":garment["pleat_count"],
        "maximum_influences":int((weights>0).sum(axis=1).max()),
        "master_fit_landmarks_m":{"waist":.426,
            "hip_joint":float(arm.data.bones[N+"LeftUpLeg"].head_local.z),
            "knee_joint":float(arm.data.bones[N+"LeftLeg"].head_local.z)},
        "buckle_offset_m":np.asarray(offset).tolist(),"buckle_scale":scale,
        "geometry_min_m":points.min(axis=0).tolist(),"geometry_max_m":points.max(axis=0).tolist(),
        "seed_hem_flare_leg_weight_center_lift":parameters.tolist(),
        "rest_min_signed_m":float(gaps.min()),"rest_max_signed_m":float(gaps.max()),
        "rest_max_euclidean_m":float(np.linalg.norm(points-surface,axis=1).max()),
        "rest_surface_probe_count":len(probes),"rest_surface_min_signed_m":float(sample_gaps.min()),
        "rest_surface_max_signed_m":float(sample_gaps.max()),
        "rest_surface_max_euclidean_m":float(np.linalg.norm(probes-sample_surface,axis=1).max()),
        **uv_report})


def import_exported(path):
    scene,arm,body = master_scene()
    previous = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = set(scene.objects)-previous
    garment, = [obj for obj in new if obj.type=="MESH" and len(obj.vertex_groups)]
    matrix = garment.matrix_world.copy()
    garment.parent = arm
    garment.matrix_world = matrix
    garment.modifiers.clear()
    garment.modifiers.new("Master Skin","ARMATURE").object = arm
    for obj in new-{garment}:
        bpy.data.objects.remove(obj,do_unlink=True)
    for obj in scene.objects:
        if obj not in (arm,body,garment):
            obj.hide_render = True
    return scene,arm,body,garment


def diagnose(checkpoint="baked.npz"):
    from skirt_contact import ContactFit
    scene,arm,body = master_scene()
    motion = cache_motion(scene,arm,body)
    with np.load(WORK/checkpoint) as data:
        p,t,w,paired = (data[key] for key in ("points","triangles","weights","paired"))
    selected = np.arange(len(motion[0]))
    fit = ContactFit(motion,t,paired,selected)
    result = fit.scan(p,w)
    short_result(result,motion,selected)
    d,n,skin,posed,contact = result
    body_triangles = motion[3]
    rest_body = motion[2][0]
    major = [max(v.groups,key=lambda g:g.weight).group for v in body.data.vertices]
    groups = [g.name for g in body.vertex_groups]
    for name in dict.fromkeys(motion[0]):
        rows = np.flatnonzero(motion[0]==name)
        row,v = np.unravel_index(d[rows].argmin(),d[rows].shape)
        if d[rows[row],v] < .0007 or n[rows].sum():
            r = rows[row]
            gap, center, normal, idx = nearest(fit.body(r), posed[r,[v]])
            tri = body_triangles[idx[0]]
            print("ISSUE", name, motion[1][r], v, "rest",p[v], "weights",w[v],
                  "body rest",rest_body[tri].mean(axis=0),[groups[major[k]] for k in tri],
                  "normal", normal[0], "sum", n[rows].sum(),flush=True)
    np.savez(WORK/"dense_state.npz",distances=d,overlaps=n)


def fine(iterations="12",checkpoint="baked.npz"):
    from skirt_contact import fine_optimize
    scene,arm,body = master_scene()
    motion = cache_motion(scene,arm,body)
    fine_optimize(motion,WORK/checkpoint,int(iterations))


def polish(iterations="5",checkpoint="baked.npz",max_patches="12"):
    from skirt_polish import polish_motion
    scene,arm,body = master_scene()
    motion = cache_motion(scene,arm,body)
    polish_motion(motion,WORK/checkpoint,int(iterations),int(max_patches))


def anchors(iterations="5",checkpoint="baked.npz"):
    from skirt_polish import polish_anchors
    scene,arm,body = master_scene()
    motion = cache_motion(scene,arm,body)
    polish_anchors(motion,WORK/checkpoint,int(iterations))


def band(checkpoint="baked.npz"):
    from skirt_polish import lower_rear_band
    scene,arm,body = master_scene()
    lower_rear_band(cache_motion(scene,arm,body), WORK/checkpoint)


def audit_rest():
    _,_,body,garment = import_exported(GLB)
    surface = make_tree(coords(body,evaluated=True),faces(body))
    vertices = coords(garment,evaluated=True)
    tri = faces(garment)
    xyz = vertices[tri]
    edge_points = (.5*(xyz+np.roll(xyz,1,axis=1))).reshape(-1,3)
    probes = np.concatenate((vertices,xyz.mean(axis=1),edge_points))
    signed,nearest_surface,_,_ = nearest(surface,probes)
    true = np.linalg.norm(probes-nearest_surface,axis=1)
    measure = {
        "glb_sha256":digest(GLB),"samples":len(probes),"vertices":len(vertices),
        "min_vertex_signed_m":float(signed[:len(vertices)].min()),
        "max_vertex_euclidean_m":float(true[:len(vertices)].max()),
        "min_surface_probe_signed_m":float(signed.min()),
        "max_surface_probe_signed_m":float(signed.max()),
        "max_surface_probe_euclidean_m":float(true.max()),
        "probes_below_clearance_floor":int((signed<COLLISION_FLOOR).sum()),
        "probes_above_rest_cap":int((true>REST_CAP).sum()),
    }
    write_json("rest_check.json",measure)
    print(measure,flush=True)


def replay():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND),load_ui=False,use_scripts=False)
    scene = bpy.context.scene
    mesh,arm = scene.objects["Pleated Skirt"],scene.objects["Armature"]
    check = WORK/"blend_replay.glb"
    export_glb(arm,mesh,check)
    left,right = digest(GLB),digest(check)
    write_json("blend_replay.json",{"blend_sha256":digest(BLEND),"glb_sha256":left,
                                    "reexport_sha256":right,"byte_identical":left==right})
    check.unlink()


def lengthen(checkpoint="baked.npz"):
    from skirt_polish import clear_triangle_contacts, lengthen_hem, try_diagonals
    scene,arm,body = master_scene()
    motion = cache_motion(scene,arm,body)
    try_diagonals(motion,WORK/checkpoint)
    clear_triangle_contacts(motion,WORK/checkpoint)
    lengthen_hem(motion,WORK/checkpoint)


def buckle(checkpoint="baked.npz"):
    from skirt_polish import fit_buckle
    scene,arm,body = master_scene()
    fit_buckle(cache_motion(scene,arm,body),WORK/checkpoint)


def inspect_pose(clip="sit_down",frame="26",repair="no"):
    from skirt_surface import add_buckle
    scene,arm,body,garment = import_exported(GLB)
    exported_rest = coords(garment,evaluated=True)
    with np.load(WORK/"baked.npz") as saved:
        fields = dict(saved)
    p,t,w = (fields[key] for key in ("points","triangles","weights"))
    scale = float(fields.get("buckle_scale",1.))
    if scale > 0:
        p,t,w = add_buckle(p,t,w,fields.get("buckle_offset",(0.,0.,0.)),scale)
    mapped = np.square(exported_rest[:,None]-p[None]).sum(axis=2).argmin(axis=1)
    motion = cache_motion(scene,arm,body)
    row, = np.flatnonzero((motion[0]==clip)&(motion[1]==float(frame)))
    controls = motion[4][row]
    skin = np.einsum("vk,kij->vij",w,controls)
    predicted = np.einsum("vij,vj->vi",skin[:,:,:3],p)+skin[:,:,3]
    actions = load_actions(scene)
    set_pose(scene,arm,actions[clip],float(frame))
    evaluated = coords(garment,evaluated=True)
    body_poses = coords(body,evaluated=True)
    print("PROBE differences",float(abs(predicted[mapped]-evaluated).max()),
          float(abs(body_poses-motion[2][row]).max()),flush=True)
    target = make_tree(body_poses,faces(body))
    actual,loc,n,tri = nearest(target,evaluated)
    baseline = nearest(make_tree(motion[2][row],motion[3]),predicted)[0]
    for vertex in np.argsort(actual)[:8]:
        print("PROBE vertex",int(vertex),"mapped",int(mapped[vertex]),
              "actual",float(actual[vertex]),"predicted",float(baseline[mapped[vertex]]),
              "rest",p[mapped[vertex]], "weights",w[mapped[vertex]],"normal",n[vertex],
              "body triangle",int(tri[vertex]), "world",evaluated[vertex],flush=True)
    hits = target.overlap(make_tree(evaluated,faces(garment)))
    print("PROBE tri pairs",len(hits),flush=True)
    if repair != "yes" or actual.min() >= .00061:
        return
    from skirt_contact import ContactFit
    from skirt_surface import CONTROLS
    affected_id = int(mapped[int(actual.argmin())])
    if affected_id >= len(fields["points"]):
        raise RuntimeError("The frame contact is on the buckle.")
    chosen = next(pair for ring in fields["paired"] for pair in ring.T if affected_id in pair)
    stored = fields["points"]
    matrices = motion[4]
    blend = np.einsum("vk,rkij->rvij",w[chosen],matrices,optimize=True)
    paired_pose = np.einsum("rvij,vj->rvi",blend[:,:,:,:3],p[chosen])+blend[:,:,:,3]
    selected = np.arange(len(motion[0]))
    fitter = ContactFit(motion,fields["triangles"],fields["paired"],selected)
    old = np.array([nearest(fitter.body(r), posed)[0] for r,posed in enumerate(paired_pose)])
    live = np.array([arm.pose.bones[N+key].matrix @ arm.data.bones[N+key].matrix_local.inverted()
                     for key in CONTROLS],dtype=np.float32)[:,:3,:3]
    frame_spin = np.einsum("vk,kij->vij",w[chosen],live)
    indices = np.flatnonzero(np.isin(mapped,chosen))
    weight_slots = (mapped[indices] == chosen[1]).astype(np.int32)
    local = evaluated[indices]
    forward = frame_spin[weight_slots]
    _,_,out,_ = nearest(target,local)
    closest = np.argsort(actual[indices])
    axes = [out[slot] @ forward[slot] for slot in closest[:4]] + list(np.eye(3,dtype=np.float32))
    radius = p[affected_id,:2] - (0.,-.02)
    radius /= max(1e-8,np.linalg.norm(radius))
    axes.append(np.array((*radius,0.0)))
    exact_faces = faces(garment)
    exact_faces = exact_faces[np.isin(exact_faces,indices).any(axis=1)]
    old_points = stored.copy()
    tests = []
    for axis in axes:
        axis /= max(1e-8,np.linalg.norm(axis))
        for amp in (.00045,.0007,.001,.0014,.0020,.003,-.0007,-.0014,-.0025):
            delta = (axis*amp).astype(np.float32)
            moved = local + forward @ delta
            near = nearest(target,moved)[0].min()
            if near < .00068:
                continue
            changed_shape = evaluated.copy()
            changed_shape[indices] = moved
            if target.overlap(make_tree(changed_shape,exact_faces)):
                continue
            trial = old_points[chosen]+delta
            gap, prox, _, _ = nearest(fitter.body(0),trial)
            if gap.min()<.0009 or np.linalg.norm(trial-prox,axis=1).max()>.0298:
                continue
            world = paired_pose+blend[:,:,:,:3]@delta
            sample = np.flatnonzero((old.min(axis=1)<.004) | (np.arange(len(old))%21==0))
            model_min = min(nearest(fitter.body(r),world[r])[0].min() for r in sample)
            if model_min >= .00064:
                tests.append((abs(amp),-float(near),delta))
    print("EXACT candidates",len(tests),flush=True)
    for _,clearance,delta in sorted(tests,key=lambda z:z[:2])[:10]:
        candidate = stored.copy()
        candidate[chosen] += delta
        result = fitter.scan(candidate,w[:len(candidate)],edges=False)
        if result[0].min()>=.00058 and not result[1].any():
            fields["points"] = candidate
            np.savez(WORK/"baked.npz",**fields)
            print("EXACT REPAIR",affected_id,chosen.tolist(),delta.tolist(),-clearance,
                  float(result[0].min()),flush=True)
            return
    raise RuntimeError("No exact export clearance repair was accepted.")


def match_walls(checkpoint="baked.npz"):
    from skirt_polish import match_wall_diagonals
    scene,arm,body = master_scene()
    match_wall_diagonals(cache_motion(scene,arm,body),WORK/checkpoint)

if __name__ == "__main__":
    stage, *args = sys.argv[sys.argv.index("--") + 1:]
    globals()[stage](*args)
