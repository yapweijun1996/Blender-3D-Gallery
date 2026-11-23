"""Fit the Tripo dress in headless Blender 5.1.

Run with --python fit_dress.py. Optional modes after -- are checkers, verify
and renders. The build reads the original master, motion, and Tripo GLB.
"""

from contextlib import redirect_stdout
import hashlib
import io
import json
import math
from pathlib import Path
import runpy
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
MODULAR = HERE.parents[1]
MASTER = MODULAR / "master/GJH_Chibi_Master_rigged.blend"
MOTION = MODULAR.parents[1] / "models/tripo-chibi-motion/motion.glb"
SOURCE = HERE / "source_studio_retopo.glb"
OUTPUT = HERE
GLB = OUTPUT / "dress_v1.glb"
BLEND = OUTPUT / "dress_v1.blend"
CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
RENDER_FRAMES = {"walk": 31.5, "run": 15.5, "wave": 14.5, "jump": 7.0}
MARGIN = .00205
REST_CAP = .02995
TRIANGLE_LIMIT = 6000
ITERATIONS = 12

# Reuse the neighborhood, action-slot, skinning and contact-witness routines
# from the worked fit, with both reference scripts kept read-only.
HOODIE = runpy.run_path(str(MODULAR / "hoodie-fit-sol/round3/fit_hoodie_round3.py"))
PRIOR = HOODIE["PRIOR"]
posed_mesh = HOODIE["posed_mesh"]
pair_witnesses = HOODIE["pair_witnesses"]
def set_pose(scene, arm, name, frame):
    action = bpy.data.actions[name] if name != "rest" else None
    animation = arm.animation_data
    if animation.action != action:
        animation.action = action
        if action:
            animation.action_slot = action.slots[0]
    scene.frame_set(math.floor(frame), subframe=frame % 1)
frames = HOODIE["frames"]
read_weights = PRIOR["read_weights"]
write_weights = PRIOR["write_weights"]
mesh_points = PRIOR["mesh_points"]
mesh_triangles = PRIOR["mesh_triangles"]
skin_matrices = PRIOR["skin_matrices"]
limit_weights = PRIOR["limit_weights"]
stats = PRIOR["stats"]
barycentric = HOODIE["barycentric"]


def open_master():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    scene = bpy.context.scene
    arm, body = scene.objects["Armature"], scene.objects["Base_Body"]
    arm.animation_data_clear()
    arm.animation_data_create()
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    scene.frame_set(1)
    bpy.context.view_layer.update()
    return scene, arm, body


def import_mesh(path):
    scene = bpy.context.scene
    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported = sorted(set(scene.objects) - before, key=lambda obj: obj.name)
    garment = max((obj for obj in imported if obj.type == "MESH"),
                  key=lambda obj: len(obj.data.polygons))
    matrix = garment.matrix_world.copy()
    garment.parent = None
    for modifier in list(garment.modifiers):
        garment.modifiers.remove(modifier)
    garment.matrix_world.identity()
    garment.data.transform(matrix)
    for obj in imported:
        if obj != garment:
            bpy.data.objects.remove(obj, do_unlink=True)
    return garment


def smoothstep(a, b, x):
    t = np.clip((x-a)/(b-a), 0, 1)
    return t*t*(3-2*t)


def source_surface(garment):
    mesh = garment.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    bm.normal_update()
    bm.verts.index_update()
    verts = [v.co.copy() for v in bm.verts]
    faces = list(bm.faces)
    tree = BVHTree.FromPolygons(verts, [tuple(v.index for v in f.verts) for f in faces])
    keep = set()
    for face in faces:
        c = face.calc_center_median()
        x, y, z = c
        arm = abs(x) > .203 and z > .482
        if arm:
            axial = Vector((0, y+.024, z-.608))
            if abs(x) > .409:
                continue
        else:
            axial = Vector((x, y-.015, max(0, z-.714)*.4))
        if axial.length < .03:
            continue
        axial.normalize()
        if face.normal.dot(axial) < -.10:
            continue
        if z < .058:
            # Keep the outer rolled hem, discarding the attached false floor.
            radius = math.hypot(x/.355, (y+.003)/.289)
            if radius < .91:
                continue
        # A long radial ray down from a sleeve can hit the flared skirt.
        reach = .135 if arm else .65
        loc, _, _, distance = tree.ray_cast(c + axial*reach, -axial, reach+.05)
        if loc is not None and distance > reach-.007:
            keep.add(face)
    # Small isolated patches are liner faces that are visible through openings.
    todo = set(keep)
    islands = []
    while todo:
        stack = [min(todo, key=lambda f: f.index)]
        todo.remove(stack[0])
        island = set(stack)
        while stack:
            for edge in stack.pop().edges:
                for face in edge.link_faces:
                    if face in todo:
                        todo.remove(face)
                        island.add(face)
                        stack.append(face)
        islands.append(island)
    keep = max(islands, key=len)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in keep], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # A side-on ray can miss the original concave gusset at the armpit.
    # Close only those tiny interior boundaries, keeping all four real openings.
    gusset_edges = [e for e in bm.edges if e.is_boundary and all(
        .183 < abs(v.co.x) < .251 and .451 < v.co.z < .545 for v in e.verts)]
    uv = bm.loops.layers.uv.active
    corner_uvs = {v: next(loop[uv].uv.copy() for loop in v.link_loops)
                  for e in gusset_edges for v in e.verts}
    filled = bmesh.ops.holes_fill(bm, edges=gusset_edges, sides=12)["faces"]
    for face in filled:
        for loop in face.loops:
            loop[uv].uv = corner_uvs[loop.vert]
    bmesh.ops.triangulate(bm, faces=filled)
    # Flatten the sleeve opening along the arm axis and round its perimeter.
    # Face materials and per-corner UVs stay attached to the Tripo surface.
    cuffs = [v for v in bm.verts if v.is_boundary and abs(v.co.x) > .36]
    for _ in range(3):
        updates = []
        for v in cuffs:
            ring = [e.other_vert(v).co for e in v.link_edges if e.is_boundary]
            updates.append((v, v.co*.62 + sum(ring, Vector())*(.38/max(1,len(ring)))))
        for v, co in updates:
            co.x = math.copysign(.410, v.co.x)
            v.co = co
    bm.verts.index_update()
    bm.faces.index_update()
    bm.to_mesh(mesh)
    print("SOURCE EXTERIOR", len(mesh.vertices), len(mesh.polygons), "removed", 6330-len(mesh.polygons), flush=True)
    bm.free()
    mesh.update()
    if mesh.has_custom_normals:
        bpy.context.view_layer.objects.active = garment
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), dtype=bool))
    return mesh_points(mesh)


def clearance(tree, points):
    signed = np.empty(len(points), dtype=np.float32)
    normals = np.empty_like(points)
    indices = np.empty(len(points), dtype=np.int32)
    for i, p in enumerate(points.tolist()):
        loc, normal, index, _ = tree.find_nearest(p)
        signed[i] = (p[0]-loc.x)*normal.x + (p[1]-loc.y)*normal.y + (p[2]-loc.z)*normal.z
        normals[i] = normal
        indices[i] = index
    return signed, normals, indices


def neighbors(mesh):
    edges = np.empty(len(mesh.edges)*2, dtype=np.int32)
    mesh.edges.foreach_get("vertices", edges)
    edges = edges.reshape(-1, 2)
    ends = np.r_[edges[:, 0], edges[:, 1]]
    starts = np.r_[edges[:, 1], edges[:, 0]]
    degree = np.bincount(ends, minlength=len(mesh.vertices)).clip(1)
    return starts, ends, degree


def average(values, links):
    starts, ends, degree = links
    return np.stack([np.bincount(ends, weights=values[starts, i], minlength=len(values))/degree
                     for i in range(values.shape[1])], axis=1).astype(np.float32)


def fit_landmarks(source, tree, links):
    x, y, z = source.T
    width = np.interp(z, [0,.11,.24,.39,.49,.57,.68,.78],
                      [.452,.48,.555,.59,.49,.47,.44,.285])
    depth = np.interp(z, [0,.12,.27,.42,.53,.65,.73,.78],
                      [.296,.321,.385,.447,.418,.366,.360,.36])
    xx = x*width
    yy = -.017 + (y+.023)*depth
    zz = np.interp(z, [0,.053,.15,.27,.39,.49,.61,.71,.7793],
                   [.239,.256,.295,.358,.433,.493,.558,.595,.611])
    sleeve = smoothstep(.18,.385,abs(x))*smoothstep(.44,.51,z)
    sx = np.interp(abs(x), [.18,.25,.30,.41], [.091,.101,.108,.119])
    sy = -.008+(y+.028)*.48
    sz = .564+(z-.602)*.42
    result = np.column_stack((.001+xx*(1-sleeve)+np.sign(x)*sx*sleeve,
                              yy*(1-sleeve)+sy*sleeve, zz*(1-sleeve)+sz*sleeve)).astype(np.float32)
    # Preserve the source profile while projecting loose and tight patches
    # back inside the rest clearance band.
    start = result.copy()
    for _ in range(14):
        signed, normals, _ = clearance(tree, result)
        target = np.clip(signed, .005, .024)
        restored = result + (target-signed)[:,None]*normals
        local = restored-start
        result = start+.7*local+.3*average(local, links)
    return result


def transfer_weights(points, body, tree, names, links):
    coords = mesh_points(body.data)
    tris = np.asarray(mesh_triangles(body.data), dtype=np.int32)
    vertices = read_weights(body, names, validate=False)
    hits = [tree.find_nearest(p) for p in points.tolist()]
    nearest = np.asarray([tuple(hit[0]) for hit in hits])
    face = tris[[hit[2] for hit in hits]]
    bary = barycentric(coords[face], nearest).clip(0, 1)
    weights = np.einsum("nv,nvb->nb", bary, vertices[face])
    index = {name.split(":")[-1]: i for i, name in enumerate(names)}
    x, y, z = points.T
    # Both legs influence the skirt bridge. A bilateral blend avoids a hard
    # nearest-thigh seam down its middle. The bodice retains transferred weights.
    pelvis = smoothstep(.43, .30, z)
    left = smoothstep(-.076,.082,x)
    upper_leg = smoothstep(.395,.251,z)*.92
    skirt = np.zeros_like(weights)
    skirt[:,index["Hips"]] = 1-upper_leg
    for side, factor in (("Left", left), ("Right", 1-left)):
        knee = .13*smoothstep(.30,.24,z)
        skirt[:,index[side+"UpLeg"]] = factor*upper_leg*(1-knee)
        skirt[:,index[side+"Leg"]] = factor*upper_leg*knee
    weights = weights*(1-pelvis[:,None]) + skirt*pelvis[:,None]
    for _ in range(4):
        weights = .73*weights + .27*average(weights, links)
    return limit_weights(weights)


def bind(garment, arm):
    garment.parent = arm
    modifier = garment.modifiers.new("Master skin", "ARMATURE")
    modifier.object = arm


def setup_motion(scene, arm, body, garment):
    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(MOTION))
    for obj in scene.objects:
        if obj not in (body, arm, garment) and obj.type in {"MESH","ARMATURE"}:
            obj.hide_viewport = obj.hide_render = True
    for obj in list(scene.objects):
        if obj not in before and obj.type in {"MESH","ARMATURE"}:
            bpy.data.objects.remove(obj, do_unlink=True)
    for name in CLIPS:
        assert bpy.data.actions.get(name), name


def cache_samples(scene, arm, body, names, garment=None):
    bones = [arm.pose.bones[name] for name in names]
    modes = tuple(bone.rotation_mode for bone in bones)
    inv = [bone.bone.matrix_local.inverted() for bone in bones]
    samples, matrices, actual = [], [], []
    faces = None
    for clip, frame in frames():
        set_pose(scene, arm, clip, frame)
        graph = bpy.context.evaluated_depsgraph_get()
        coords, polygons = posed_mesh(body, graph)
        if faces is None:
            faces = np.asarray(polygons, dtype=np.int32)
        tree = BVHTree.FromPolygons(coords, polygons, all_triangles=True)
        if len(samples) % 200 == 0:
            print("CACHING POSE", len(samples), clip, frame, flush=True)
        samples.append((clip, frame, tree, np.asarray(coords, dtype=np.float32), faces))
        matrices.append(np.asarray([bone.matrix @ bind for bone, bind in zip(bones, inv)])[:, :3, :])
        if garment is not None:
            evaluated = garment.evaluated_get(graph)
            mesh = evaluated.to_mesh()
            try:
                actual.append(mesh_points(mesh))
            finally:
                evaluated.to_mesh_clear()
    assert modes == tuple(bone.rotation_mode for bone in bones)
    print("POSES", len(samples), flush=True)
    transforms = np.asarray(matrices, dtype=np.float32)
    if garment is not None:
        return samples, transforms, np.asarray(actual, dtype=np.float32)
    return samples, transforms


def mesh_coords(garment, points):
    garment.data.vertices.foreach_set("co", np.ascontiguousarray(points, dtype=np.float32).ravel())
    garment.data.update()


def export(garment, arm, body, points, names, weights):
    set_pose(bpy.context.scene, arm, "rest", 1)
    arm.animation_data_clear()
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()
    mesh_coords(garment, points)
    write_weights(garment, names, weights)
    garment.name = garment.data.name = "Dress"
    assert len(mesh_triangles(garment.data)) <= TRIANGLE_LIMIT and len(names) == 65
    bpy.ops.object.select_all(action="DESELECT")
    garment.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = garment
    garment.parent = None
    bpy.ops.export_scene.gltf(filepath=str(GLB), use_selection=True,
                             export_animations=False, export_def_bones=False, export_all_influences=False,
                             export_tangents=True)
    garment.parent = arm
    body.hide_render = False
    body.hide_set(False)
    # Retain the unchanged body in the editable scene as a fitting reference.
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))


def shrink_textures(garment):
    images = {node.image for mat in garment.data.materials for node in mat.node_tree.nodes
              if node.type == "TEX_IMAGE" and node.image}
    for image in sorted(images, key=lambda img: img.name):
        width, height = image.size
        factor = min(1, 1024/max(width, height))
        image.scale(round(width*factor), round(height*factor))
        image.pack()


def make_source():
    scene, arm, body = open_master()
    garment = import_mesh(SOURCE)
    source = source_surface(garment)
    shrink_textures(garment)
    links = neighbors(garment.data)
    coords, polygons = posed_mesh(body, bpy.context.evaluated_depsgraph_get())
    tree = BVHTree.FromPolygons(coords, polygons, all_triangles=True)
    points = fit_landmarks(source, tree, links)
    names = tuple(bone.name for bone in arm.data.bones)
    weights = transfer_weights(points, body, tree, names, links)
    bind(garment, arm)
    return scene, arm, body, garment, points, names, weights, links


def build():
    scene, arm, body, garment, points, names, weights, links = make_source()
    setup_motion(scene, arm, body, garment)
    fit_and_export(scene, arm, body, garment, points, names, weights, links)


def section(points):
    x, _, z = points.T
    return np.select([z < .270, z < .413, (abs(x) > .104) & (z >= .519), z > .588,
                      (abs(x) > .084) & (z >= .478)],
                     ["hem", "skirt", "sleeve", "neck", "shoulder and armpit"], default="bodice")


def scan(points, triangles, samples, poses, constraints=False, report=False, body_names=None):
    faces = triangles.tolist()
    regions = section(points)
    face_regions = section(points[triangles].mean(axis=1))
    reports, planes = {}, []
    hits = np.zeros(len(triangles), dtype=np.int32)
    scores, rest = [], None
    field = np.empty(poses.shape[:2],dtype=np.float32)
    clean_cut = np.zeros(len(triangles),dtype=np.int32)
    for i, (clip, frame, tree, body, body_faces) in enumerate(samples):
        positions = poses[i]
        signed, normal, nearest_faces = clearance(tree, positions)
        garment = BVHTree.FromPolygons(positions.tolist(), faces, all_triangles=True)
        pairs = np.asarray(sorted(tree.overlap(garment)), dtype=np.int32).reshape(-1, 2)
        field[i] = signed
        if i == 0:
            rest = signed
        inside = int((signed < 0).sum())
        k = int(signed.argmin())
        n = len(pairs)
        values = reports.setdefault(clip, {"samples": 0, "inside": 0, "pairs": 0, "min_m": 1.0,
                                          "total_pairs": 0, "failing_frames": 0, "contact_zones": {}})
        values["samples"] += 1
        values["inside"] = max(values["inside"], inside)
        values["total_pairs"] += n
        values["failing_frames"] += int(n > 0 or signed[k] < .0005)
        if "pair_frame" not in values or n > values["pairs"]:
            values.update(pairs=n, pair_frame=frame)
        if signed[k] < values["min_m"]:
            values.update(min_m=float(signed[k]), min_frame=frame, min_zone=str(regions[k]),
                          min_vertex=k, min_body_zone=body_names[nearest_faces[k]] if body_names else None,
                          min_rest_xyz=points[k].tolist())
        deficient = np.maximum(MARGIN-signed, 0)
        scores.append(float(np.square(deficient).sum()))
        if constraints:
            failing = np.nonzero(deficient)[0]
            v = np.repeat(failing[:,None], 3, axis=1)
            bary = np.zeros(v.shape, dtype=np.float32)
            bary[:,0] = 1
            nrm = normal[failing]
            d = signed[failing]
        if len(pairs):
            np.add.at(hits, pairs[:,1], 1)
            crossed = pairs[:,1]
            clean = signed[triangles[crossed]].min(axis=1) >= .0005
            np.add.at(clean_cut, crossed[clean], 1)
            if constraints or report:
                f, b = pair_witnesses(positions, triangles, body, body_faces, pairs[:,::-1], dense=False)
                b = b.astype(np.float32)
                corners = triangles[f]
                contacts = np.einsum("nc,nci->ni", b, positions[corners])
                depths, normals, nearest = clearance(tree, contacts)
                if constraints:
                    order = np.lexsort((depths, f))
                    selected = order[np.r_[True, np.diff(f[order]) != 0]]
                    v = np.concatenate((v,corners[selected]))
                    bary = np.concatenate((bary,b[selected]))
                    nrm = np.concatenate((nrm,normals[selected]))
                    d = np.r_[d,depths[selected]]
                if report:
                    for j in np.flatnonzero(depths < 0):
                        gz = str(face_regions[f[j]])
                        bz = body_names[nearest[j]] if body_names else ""
                        key = f"{gz} / {bz}"
                        previous = values["contact_zones"].get(key, {"depth_m": 0})
                        if depths[j] < previous["depth_m"]:
                            values["contact_zones"][key] = {"depth_m": float(depths[j]), "frame": frame}
        if constraints and len(v):
            planes.append((i, v, bary, nrm, d))
    score = sum(scores) + sum(v["total_pairs"] for v in reports.values())*.000015
    return reports, rest, score, clean_cut if constraints else hits, planes, field


def zone_names(body, names):
    weights = read_weights(body, names, validate=False)
    tris = np.asarray(mesh_triangles(body.data), dtype=np.int32)
    return [names[i].split(":")[-1] for i in weights[tris].sum(axis=1).argmax(axis=1)]


def report_status(reports):
    for clip, r in reports.items():
        print("DENSE", clip, r["inside"], r["pairs"], round(r["min_m"]*1000,3),
              r["min_frame"], r["min_zone"], r["min_body_zone"], r["min_rest_xyz"], flush=True)


def read_export(path=None):
    path = GLB if path is None else path
    scene, arm, body = open_master()
    garment = import_mesh(path)
    bind(garment, arm)
    setup_motion(scene, arm, body, garment)
    return scene, arm, body, garment


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    scene, arm, body, garment = read_export()
    points = mesh_points(garment.data)
    tris = np.asarray(mesh_triangles(garment.data), dtype=np.int32)
    names = tuple(bone.name for bone in arm.data.bones)
    rest_weights = read_weights(garment, names)
    samples, _, poses = cache_samples(scene, arm, body, names, garment=garment)
    reports, rest, score, hits, _, _ = scan(points, tris, samples, poses,
                                        report=True, body_names=zone_names(body, names))
    result = {"glb_sha256": sha(GLB), "triangles": len(tris), "vertices": len(points),
              "max_influences": int((rest_weights > 0).sum(axis=1).max()), "poses": len(poses),
              "score": score, "results": reports, "rest": {"all": stats(rest)},
              "rest_over_30mm": int((rest > .03).sum()), "overlap_faces": int((hits > 0).sum())}
    sections = section(points)
    for zone in np.unique(sections):
        result["rest"][str(zone)] = stats(rest[sections == zone])
    (OUTPUT/"dense_check.json").write_text(json.dumps(result, indent=2)+"\n")
    report_status(reports)


def run_checkers():
    # Preserve each supplied script and its measurement/sampling code. Both
    # scripts write the same JSON name, so use separate temporary directories.
    for stem in ("motion_check", "motion_check_tri"):
        folder = OUTPUT/("." + stem)
        folder.mkdir(exist_ok=True)
        path = HERE/"work"/f"{stem}.py"
        source = path.read_text()
        # The supplied Workbench renderer crashes on this headless build.
        # Rendering is handled once by the textured Cycles QA stage.
        first, rest = source.split("sc.render.engine=", 1)
        persist = rest[rest.index("json.dump("):]
        old = sys.argv
        sys.argv = [str(path), "--", str(MASTER), str(MOTION), str(GLB), str(folder)]
        output = io.StringIO()
        try:
            with redirect_stdout(output):
                exec(compile(first+persist, str(path), "exec"), {"__name__": "__main__"})
        finally:
            sys.argv = old
        result = "\n".join(row for row in output.getvalue().splitlines() if row.startswith("RESULT "))
        report = folder/"motion_check.json"
        destination = OUTPUT/f"{stem}.json"
        report.replace(destination)
        folder.rmdir()
        (OUTPUT/f"{stem}.txt").write_text(result+"\n")
        print(result, flush=True)


def light(scene, name, location, power, size, target):
    data = bpy.data.lights.new(name,"AREA")
    data.energy, data.shape, data.size = power,"DISK",size
    obj = bpy.data.objects.new(name,data)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()


def renders():
    scene, arm, body, garment = read_export()
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.world = bpy.data.worlds.new("Dress QA studio")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (.31,.35,.43,1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = .5
    for obj in list(scene.objects):
        if obj.type == "LIGHT":
            bpy.data.objects.remove(obj, do_unlink=True)
    light(scene,"Key",(-1,-2,2.4),200,1.25,(0,0,.5))
    light(scene,"Fill",(1.1,-1.5,.6),85,1.3,(0,0,.5))
    light(scene,"Rim",(.4,1.2,1.5),140,1.1,(0,0,.5))
    camera = bpy.data.cameras.new("Dress QA")
    camera.type = "ORTHO"
    obj = bpy.data.objects.new("Dress QA",camera)
    scene.collection.objects.link(obj)
    scene.camera = obj
    out = OUTPUT/"renders"
    out.mkdir(exist_ok=True)

    def capture(label, direction, target, scale):
        obj.location = Vector(target) + Vector(direction).normalized()*2.8
        obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()
        camera.ortho_scale = scale
        scene.render.filepath = str(out/f"{label}.png")
        bpy.ops.render.render(write_still=True)

    set_pose(scene,arm,"rest",1)
    for label, view in (("front",(0,-1,0)),("back",(0,1,0)),("left",(1,0,0)),
                        ("right",(-1,0,0)),("three_quarter",(.63,-1,.14)),("dress_only",(.36,-1,.29))):
        body.hide_render = label == "dress_only"
        full = label == "three_quarter"
        capture(f"rest_{label}", view, (0,-.012,.49 if full else .43), 1.12 if full else .59)
    body.hide_render = False
    rendered = {}
    for clip, frame in RENDER_FRAMES.items():
        set_pose(scene,arm,clip,frame)
        coords, _ = posed_mesh(body,bpy.context.evaluated_depsgraph_get())
        points = np.asarray(coords)
        center = (points.min(axis=0)+points.max(axis=0))*.5
        capture(clip,(.71,-1,.1), center, .92)
        rendered[clip] = frame
    manifest = {"glb_sha256": sha(GLB), "blender": bpy.app.version_string, "samples": scene.cycles.samples,
                "motion_frames": rendered, "images": {p.name: sha(p) for p in sorted(out.glob("*.png"))}}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")


def smooth_floor(step, links):
    filtered = step.copy()
    for _ in range(3):
        filtered = .66*filtered + .34*average(filtered, links)
    size = np.linalg.norm(step, axis=1)
    direction = step / size.clip(1e-9)[:,None]
    deficit = np.maximum(0, size-np.einsum("vi,vi->v", filtered, direction))
    return filtered+direction*deficit[:,None]


def split_contacts(garment, points, weights, names, triangles, hits):
    mesh_coords(garment, points)
    write_weights(garment, names, weights)
    bm = bmesh.new()
    bm.from_mesh(garment.data)
    edges = {}
    for t, count in zip(triangles, hits):
        if count:
            for a, b in zip(t, np.roll(t,1)):
                key = tuple(sorted((a,b)))
                edges[key] = edges.get(key,0)+int(count)
    candidates = []
    for edge in bm.edges:
        key = tuple(sorted(v.index for v in edge.verts))
        length = edge.calc_length()
        hits = edges.get(key,0)
        if hits >= 2 and length > .012:
            score = length**1.8*math.log1p(hits)
            candidates.append((-score, key, edge))
    budget = min(520, TRIANGLE_LIMIT-len(triangles))
    selection = []
    for _, _, edge in sorted(candidates, key=lambda row: row[:2]):
        cost = len(edge.link_faces)
        if budget >= cost:
            budget -= cost
            selection.append(edge)
    if selection:
        bmesh.ops.subdivide_edges(bm, edges=selection, cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts)>3])
        bm.to_mesh(garment.data)
        garment.data.update()
    bm.free()
    print("SUBDIVIDED", len(selection), flush=True)
    return mesh_points(garment.data), limit_weights(read_weights(garment,names,validate=False))


def prepare_update(points, weights, matrices, skin, planes, outward):
    columns = np.argsort(-weights, axis=1, kind="stable")[:,:4]
    coeff = np.take_along_axis(weights, columns, axis=1)
    allowed = coeff > .0001
    # Reserve the existing support so a wrist or a far-away joint can never
    # enter the shortlist just because its lever arm clears a constraint.
    vertex_ids, normals, depth = [], [], []
    for f, v, b, n, d in planes:
        grad = np.einsum("ni,ncji->ncj", n, np.swapaxes(skin[f,v,:,:3],-1,-2))
        joints = matrices[f,columns[v]]
        joint_pos = np.einsum("ncqij,ncj->ncqi", joints[...,:3], points[v]) + joints[...,3]
        wgrad = np.einsum("ni,ncqi->ncq", n, joint_pos)
        mask = allowed[v]
        wgrad -= (wgrad*mask).sum(axis=-1,keepdims=True)/mask.sum(axis=-1,keepdims=True)
        wgrad *= mask*2.8
        vertex_ids.append(v)
        normals.append(np.concatenate((grad,wgrad),axis=2)*b[...,None])
        depth.append(d)
    v, n, d = (np.concatenate(q) for q in (vertex_ids,normals,depth))
    geom = n[:,:,:3]
    vertex_grad = np.einsum("nci,nci->nc", geom, outward[v])
    forward = vertex_grad.clip(0).sum(axis=1)
    required = np.where((vertex_grad > .12) & (forward[:,None] > .30),
                        (MARGIN-d)[:,None]/forward[:,None].clip(.30), 0)
    radial = np.zeros(len(points), dtype=np.float32)
    np.maximum.at(radial, v.ravel(), required.ravel())
    update = HOODIE["worst_directional_step"](v, n, d, len(points)).astype(np.float32)
    return update, radial, columns, coeff, allowed


def skin_geometry(matrices, weights, points):
    skin = skin_matrices(matrices, weights)
    return np.einsum("fvij,vj->fvi", skin[...,:3], points)+skin[...,3], skin


def rest_guard(current, candidate, triangles, tree, references):
    """Backtrack over flips, cap breaches, and actual rest triangle cuts."""
    v = references[triangles]
    reference_normals = np.cross(v[:,1]-v[:,0], v[:,2]-v[:,0])
    reference_area = np.square(reference_normals).sum(axis=1)
    faces = triangles.tolist()
    for _ in range(9):
        signed, _, _ = clearance(tree, candidate)
        surface = BVHTree.FromPolygons(candidate.tolist(), faces, all_triangles=True)
        overlaps = np.asarray(tree.overlap(surface), dtype=np.int32).reshape(-1, 2)
        t = candidate[triangles]
        normals = np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])
        flip = np.einsum("fi,fi->f", normals, reference_normals) < reference_area*.12
        bad = (signed < .00055) | (signed > REST_CAP)
        bad[triangles[flip].ravel()] = True
        bad[triangles[overlaps[:,1]].ravel()] = True
        if not bad.any():
            return candidate
        candidate[bad] = (candidate[bad]+current[bad])*.5
    return current.copy()


def local_score(values):
    gap = np.maximum(MARGIN-values,0)*1000
    return gap.max(axis=0)**2 + 1.15*np.square(gap).mean(axis=0)


def trial_offsets(iteration, geom, normals, radial):
    n = len(geom)
    trust = .0065 if iteration < 6 else .0035
    steps = [np.zeros_like(geom), geom, geom*.5,
             normals*np.minimum(radial,trust)[:,None]]
    axes = np.eye(3,dtype=np.float32)
    for axis in axes:
        steps.extend((np.broadcast_to(axis*trust,(n,3)),np.broadcast_to(-axis*trust,(n,3))))
    for direction in (-1,1):
        steps.append(normals*trust*direction)
    return np.asarray(steps,dtype=np.float32)


def local_search(iteration, points, weights, origin, prior_weights, matrices, skin, samples,
                 field, planes, links):
    rest_tree = samples[0][2]
    _, outward, _ = clearance(rest_tree, points)
    update, required, columns, coeff, allowed = prepare_update(points,weights,matrices,skin,planes,outward)
    step = update[:,:3]
    length = np.linalg.norm(step,axis=1)
    step *= np.minimum(1, .009/length.clip(1e-9))[:,None]
    weight_step = np.where(allowed, update[:,3:]*1.3, 0)
    proposed = HOODIE["simplex"](np.where(allowed, coeff+weight_step, -10))
    region = (field.min(axis=0) < MARGIN) | (required > .0002) | (length > .0002)
    offsets = trial_offsets(iteration,step,outward,required)
    chunks = [np.array([i for i,s in enumerate(samples) if s[0]==c],dtype=int) for c in CLIPS]
    # Many very similar half-frames can share one vertex's contact. Keep up to
    # four worst witnesses in each clip and rescan every half-frame afterwards.
    per_clip = [block[np.argpartition(field[block],4,axis=0)[:5]] for block in chunks]
    row_ids = np.concatenate([np.zeros((1,len(points)),dtype=int),*per_clip])
    new_points, new_weights = points.copy(), weights.copy()
    for v in np.flatnonzero(region):
        rows = np.unique(row_ids[:,v])
        p = points[v]
        cs = np.vstack((p+offsets[:,v],p,p+step[v],p+(origin[v]-p)*.55))
        rest, _, _ = clearance(rest_tree,cs)
        feasible = (rest >= .0016) & (rest <= REST_CAP)
        feasible[0] = True
        wc = np.repeat(coeff[v:v+1],len(cs),axis=0)
        wc[-3:-1] = proposed[v]
        # In the skirt, selecting the same-side leg is a useful alternative
        # to pushing the center bridge through the moving thigh.
        existing = columns[v,allowed[v]]
        if p[2] < .39 and len(existing) > 1:
            support = np.zeros((len(existing),4),dtype=np.float32)
            ids = np.flatnonzero(allowed[v])
            support[np.arange(len(ids)),ids] = 1
            wc = np.vstack((wc,(coeff[v]+support)*.5))
            cs = np.vstack((cs,np.repeat(p[None],len(ids),axis=0)))
            feasible = np.r_[feasible,np.ones(len(ids),dtype=bool)]
        cs, wc = cs[feasible], wc[feasible]
        m = matrices[rows[:,None],columns[v,None]]
        candidate_skin = np.einsum("sqij,cq->scij",m,wc)
        xyz = np.einsum("scij,cj->sci",candidate_skin[...,:3],cs)+candidate_skin[...,3]
        signed = np.empty(xyz.shape[:2],dtype=np.float32)
        for row, (f, q) in enumerate(zip(rows,xyz.tolist())):
            for option, co in enumerate(q):
                nearest,n,_,_=samples[f][2].find_nearest(co)
                signed[row,option] = (co[0]-nearest.x)*n.x+(co[1]-nearest.y)*n.y+(co[2]-nearest.z)*n.z
        cost = local_score(signed)
        cost += np.square((cs-origin[v])*1000).sum(axis=1)*.022
        cost += np.square(wc-prior_weights[v,columns[v]]).sum(axis=1)*9
        choice = int(cost.argmin())
        new_points[v] = cs[choice]
        new_weights[v] = 0
        new_weights[v,columns[v]] = wc[choice]
    delta = new_points-points
    # Keep the selected requirement while spreading a fraction to neighbors.
    delta = .73*delta+.27*average(delta,links)
    new_weights = limit_weights(.87*new_weights+.13*average(new_weights,links))
    return points+delta,new_weights


def fit_and_export(scene, arm, body, garment, points, names, weights, links):
    samples, matrices = cache_samples(scene, arm, body, names)
    tree = samples[0][2]
    body_regions = zone_names(body, names)
    triangles = np.asarray(mesh_triangles(garment.data), dtype=np.int32)
    origin, prior_weights = points.copy(),weights.copy()
    history, best, before_subdivision = [], None, None
    for iteration in range(ITERATIONS+1):
        poses, skin = skin_geometry(matrices, weights, points)
        result, rest, score, hits, planes, field = scan(points, triangles, samples, poses, constraints=True,
                                                       body_names=body_regions)
        pairs = sum(v["total_pairs"] for v in result.values())
        print("ITERATION",iteration,"cost",round(score,5),"total pairs",pairs,"rest max",
              round(float(rest.max()),6),"triangles",len(triangles),flush=True)
        report_status(result)
        pass_rest = result["rest"]["pairs"] == 0 and rest.min() >= .0005 and rest.max() <= .03
        motion_rank = score + .00018*pairs + .6*max(-r["min_m"]*1000 for r in result.values())
        rank = motion_rank + (0 if pass_rest else 1000)
        history.append({"iteration":iteration,"score":score,"rank":rank,"results":result,
                        "rest_pass":bool(pass_rest),"rest_max_m":float(rest.max())})
        path = OUTPUT/"fit_history.json"
        path.write_text(json.dumps(history,indent=2)+"\n")
        if best is None or rank < best[0]:
            best = (rank, points.copy(), weights.copy(), iteration)
            export(garment,arm,body,points,names,weights)
            arm.animation_data_create()
        if (all(v["pairs"] == 0 and v["min_m"] >= .0005 for v in result.values()) and pass_rest
                or iteration == ITERATIONS or not planes):
            break
        if iteration == 8:
            before_subdivision = (best[0], best[3], GLB.read_bytes(), BLEND.read_bytes())
            points, weights = split_contacts(garment, best[1], best[2], names, triangles, hits)
            if len(garment.data.vertices) != len(origin):
                triangles = np.asarray(mesh_triangles(garment.data),dtype=np.int32)
                origin, prior_weights = points.copy(),weights.copy()
                links = neighbors(garment.data)
                best = None
                continue
        if iteration == 0:
            # Baseline outward bake uses the maximum requirement on all poses.
            _, outward, _ = clearance(tree,points)
            _, required, _, _, _ = prepare_update(points,weights,matrices,skin,planes,outward)
            offset = outward*smooth_floor(np.minimum(required,.009)[:,None],links)
            candidate = points+offset
            next_weights = weights
        else:
            candidate,next_weights = local_search(iteration,points,weights,origin,prior_weights,
                                                  matrices,skin,samples,field,planes,links)
        points = rest_guard(points,candidate,triangles,tree,origin)
        if not np.allclose(next_weights.sum(axis=1),1,atol=1e-5):
            raise RuntimeError("Invalid skin weight update")
        weights = next_weights
        del field, poses, skin, planes
    if before_subdivision and before_subdivision[0] < best[0]:
        rank, iteration, glb, blend = before_subdivision
        GLB.write_bytes(glb)
        BLEND.write_bytes(blend)
    else:
        rank, iteration = best[0], best[3]
        export(garment,arm,body,best[1],names,best[2])
    print("SELECTED ITERATION",iteration,"rank",rank,flush=True)


if __name__ == "__main__":
    modes = {"build": build, "verify": verify, "checkers": run_checkers, "renders": renders}
    for mode in sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else ["build"]:
        modes[mode]()
