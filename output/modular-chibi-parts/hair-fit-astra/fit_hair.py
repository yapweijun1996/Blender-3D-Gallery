"""Rebuild the Tripo bob as a detachable Blender/glTF skin and check the export.

Run in background Blender with --python fit_hair.py. Requires the original
project layout, the supplied motion_check.py and the master character files.
"""
import hashlib
import json
import math
import shutil
import struct
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MASTER = HERE.parent / "master/GJH_Chibi_Master_rigged.blend"
SOURCE = HERE.parent / "tripo-hair/tripo-out/modular-hair-bob-a20b7eff/model.glb"
MOTION = REPO / "models/tripo-chibi-motion/motion.glb"
NAME = "hair_bob_v1"
HEAD, NECK = "mixamorig:Head", "mixamorig:Neck"
ROOT = Vector((0.001, 0.0, 0.807))
GLB = HERE / (NAME + ".glb")
BLEND = HERE / (NAME + ".blend")


def smooth(a, b, x):
    t = max(0., min(1., (x - a) / (b - a)))
    return t * t * (3. - 2. * t)


def load_hair():
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    obj, = [o for o in set(bpy.context.scene.objects) - before if o.type == "MESH"]
    obj.data.transform(obj.matrix_world)
    obj.parent = None
    obj.matrix_world = Matrix.Identity(4)
    obj.name = "Hair_Bob"
    obj.data.name = "Bob_Strands"
    return obj


def connected_faces(bm):
    pending = set(bm.faces)
    components = []
    while pending:
        stack = [pending.pop()]
        result = []
        while stack:
            face = stack.pop()
            result.append(face)
            for edge in face.edges:
                for other in edge.link_faces:
                    if other in pending:
                        pending.remove(other)
                        stack.append(other)
        components.append(result)
    return sorted(components, key=len, reverse=True)


def trim_field(bm, values):
    new = set()
    for e in list(bm.edges):
        a, b = e.verts
        da, db = values[a], values[b]
        if (da < 0) != (db < 0):
            factor = max(.00001, min(.99999, da / (da - db)))
            _, v = bmesh.utils.edge_split(e, a, factor)
            new.add(v)
    for f in list(bm.faces):
        cuts = [v for v in f.verts if v in new]
        if len(cuts) == 2:
            bmesh.utils.face_split(f, *cuts)
    bmesh.ops.delete(bm, geom=[v for v, d in values.items() if d < 0], context="VERTS")
    bmesh.ops.triangulate(bm, faces=list(bm.faces))


def prepare_strands(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1.e-6)
    bm.normal_update()
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    crown, skin, side_lock, sliver = connected_faces(bm)
    assert [len(c) for c in (crown, skin, side_lock, sliver)] == [3860, 1299, 92, 2], "Unexpected Tripo source topology"
    # The source contains one free-standing, clean temple lock. Its opposite
    # is fused to the unwanted face-side lining. Retain the complete original
    # lock and use a mirrored copy to rebuild that damaged counterpart.
    uv = bm.loops.layers.uv.active
    saved_verts = sorted({v for f in side_lock for v in f.verts}, key=lambda v: v.index)
    local = {v: i for i, v in enumerate(saved_verts)}
    coords = [v.co.copy() for v in saved_verts]
    loops = [[(local[l.vert], l[uv].uv.copy()) for l in f.loops]
             for f in sorted(side_lock, key=lambda f: f.index)]
    # Offset the original head's convex hull inward. This defines a smooth
    # cavity in source space, so the cut cannot turn into a jagged sequence
    # of individual triangle deletions or project the hidden face back out.
    hull = bm.copy()
    faces = bmesh.ops.convex_hull(hull, input=list(hull.verts))["geom"]
    triangles = [f for f in faces if isinstance(f, bmesh.types.BMFace)]
    hv = list(hull.verts)
    ids = {v: i for i, v in enumerate(hv)}
    envelope = BVHTree.FromPolygons([v.co.copy() for v in hv],
                                    [[ids[v] for v in f.verts] for f in triangles])
    hull.free()
    bmesh.ops.delete(bm, geom=skin + sliver, context="FACES")
    values = {}
    for v in bm.verts:
        p = v.co
        # The thinner temple cavity follows the underside of the swept locks.
        temple = smooth(.13, .29, abs(p.y)) * (1 - smooth(.20, .34, p.x)) * (1 - smooth(-.02, .16, p.z))
        tolerance = .069 - .031 * temple
        values[v] = tolerance - envelope.find_nearest(p)[3]
    before = len(bm.faces)
    trim_field(bm, values)
    for part in connected_faces(bm):
        points = [v.co for f in part for v in f.verts]
        loose_cheek = min(p.x for p in points) > .115 and max(p.z for p in points) < -.15
        if loose_cheek or len(part) <= 9:
            bmesh.ops.delete(bm, geom=part, context="FACES")
    label = bm.verts.layers.int.new("temple_lock")
    for mirror in (1, -1):
        verts = [bm.verts.new((p.x, mirror*p.y, p.z)) for p in coords]
        for v in verts:
            v[label] = 1
        for face_loops in loops:
            row = face_loops if mirror == 1 else face_loops[::-1]
            f = bm.faces.new([verts[i] for i, _ in row])
            for l, (_, texcoord) in zip(f.loops, row):
                l[uv].uv = texcoord
    print("Source cavity triangles:", before, "->", len(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def tree_for(obj, head_only=False):
    mesh = obj.data
    vertices = [obj.matrix_world @ v.co for v in mesh.vertices]
    faces = [p.vertices[:] for p in mesh.polygons]
    if head_only:
        faces = [f for f in faces if all(vertices[i].z > .603 for i in f)]
    return BVHTree.FromPolygons(vertices, faces)


def map_point(source, tree, lock):
    # At +X the source presents its unpainted face. Rotating -90 degrees
    # places its front at -Y and its original +Y on the character's left.
    s, t, h = source
    if lock:
        heights = [-.35, -.29, -.22, -.12, -.055, .04, .095]
        def at(values):
            return float(np.interp(h, heights, values))
        guide_x = at([.144, .151, .157, .155, .150, .143, .142])
        guide_y = at([-.096, -.094, -.095, -.106, -.116, -.128, -.135])
        guide_z = at([.674, .691, .711, .733, .749, .766, .779])
        width = abs(t) - at([.20, .234, .256, .270, .274, .277, .268])
        depth = s - at([.28, .238, .213, .207, .219, .221, .25])
        return Vector((.001 + math.copysign(guide_x + .26 * width, t),
                       guide_y - .24 * depth, guide_z))
    forelock = smooth(.18, .34, s) * (1 - smooth(.23, .39, abs(t)))
    low = 1 - smooth(-.29, .04, h)
    behind = 1 - smooth(.00, .26, s)
    z = .821 + .415 * h - .009 * smooth(.18, .45, h) + .022 * forelock * (1 - smooth(-.04, .29, h))
    reach = max(abs(t), -s)
    z -= low * behind * (.022 * smooth(.07, .28, reach) + .023 * smooth(.22, .38, reach))
    # Leave space in front of the ears by sweeping the lower side panels
    # back toward the nape. The short temple locks retain their front sweep.
    tuck = smooth(.19, .37, abs(t)) * (1 - smooth(.06, .26, s))
    y_shift = .057 * tuck * (1 - smooth(-.25, .25, h))
    point = Vector((.001 + (.428 + .013 * low * behind) * t, -.005 - .447 * s + y_shift, z))
    # Use a smooth monotonic lower bound in radial depth so overlapping
    # outer locks retain their order above the newly fitted inner surface.
    delta = point - ROOT
    ray = delta.normalized()
    loc, normal, _, _ = tree.ray_cast(ROOT + .65 * ray, -ray, .64)
    if loc is not None:
        radius = (loc - ROOT).dot(ray)
        facing = max(.35, normal.dot(ray))
        minimum = radius + .0072 / facing
        depth = delta.length - minimum
        blend = .010
        # Linear continuation below the surface preserves the relative depth
        # of closely nested hair surfaces in the compressed scalp cavity.
        if depth < .045:
            soft = blend * math.log1p(math.exp(depth / blend))
            point = ROOT + ray * (minimum + soft + .026 * min(0, depth))
    return point


def correct_clearance(obj, tree):
    # Decimation can move a vertex toward the head. Correct remaining local
    # deficits without flattening the outside of the crown.
    for v in obj.data.vertices:
        for _ in range(5):
            loc, n, _, _ = tree.find_nearest(v.co)
            signed = (v.co - loc).dot(n)
            if signed >= .0058:
                break
            v.co += n * (.0062 - signed)
    obj.data.update()


def open_ears(obj):
    # The base's ears protrude through the original wig cavity. Shape a
    # rounded clearance opening between the temple and rear curtains.
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    def edge_field(p):
        if abs(p.x) < .12:
            return 1.
        return math.hypot((p.y - .014) / .055, (p.z - .716) / .059) - 1
    for _ in range(2):
        edges = [e for e in bm.edges if e.calc_length() > .014
                 and abs(e.verts[0].co.x) > .12 and abs(e.verts[0].co.y-.014) < .11
                 and e.verts[0].co.z < .815]
        if edges:
            bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True)
            bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts)>3])
    trim_field(bm, {v: edge_field(v.co) for v in bm.verts})
    for part in connected_faces(bm):
        coords = np.array([v.co for f in part for v in f.verts])
        if coords[:, 2].max() < .68 and np.linalg.norm(np.ptp(coords, axis=0)) < .034:
            bmesh.ops.delete(bm, geom=part, context="FACES")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def remove_lining(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    tree = BVHTree.FromBMesh(bm)
    rays = []
    for i in range(120):
        z = 1 - 2*(i+.5)/120
        a = math.pi*(3-math.sqrt(5))*i
        r = math.sqrt(1-z*z)
        rays.append(Vector((r*math.cos(a), r*math.sin(a), z)))
    lining = []
    for f in bm.faces:
        p = f.calc_center_median()
        ray = (p - ROOT).normalized()
        if p.z < .812 or f.normal.dot(ray) > -.12:
            continue
        probes = [p] + [p.lerp(v.co, .75) for v in f.verts]
        visible = any(tree.ray_cast(q + .000005*d, d, .8)[0] is None
                      for d in rays if d.dot(ray) > .22 for q in probes)
        if not visible or (f.normal.dot(ray) < -.60 and max(e.calc_length() for e in f.edges) > .042):
            lining.append(f)
    print("Occluded inner crown triangles removed:", len(lining))
    bmesh.ops.delete(bm, geom=lining, context="FACES")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def nest_crown(obj, skin):
    # A broad angular deformation field moves overlapping surfaces together.
    # Fade the fit out below the cap so the fringe and nape can hang freely.
    shell = tree_for(obj)
    directions, excess = [], []
    for elevation in range(8, 90, 3):
        el = math.radians(elevation)
        for angle in range(0, 360, 4):
            az = math.radians(angle)
            ray = Vector((math.cos(az)*math.cos(el), math.sin(az)*math.cos(el), math.sin(el)))
            scalp = skin.ray_cast(ROOT + .6*ray, -ray, .6)[0]
            inner = shell.ray_cast(scalp + .00005*ray, ray, .14)[0]
            if inner is not None:
                directions.append(tuple(ray))
                excess.append(min(.037, max(0., skin.find_nearest(inner)[3] - .0081)))
    directions = np.array(directions)
    excess = np.array(excess)
    for v in obj.data.vertices:
        p = v.co.copy()
        ray = (p - ROOT).normalized()
        influence = smooth(-.06, .40, ray.z)
        if not influence:
            continue
        spread = np.exp(-2 * (1. - directions @ np.array(ray)) / .33**2)
        shift = influence * float(np.max(excess * spread))
        q, n, _, _ = skin.find_nearest(p)
        gap = (p - q).dot(n)
        floor = .0059 + .13 * max(0., gap-.0059)
        # The smooth positive part protects thin roots and retains layering.
        target = floor + .0016 * np.logaddexp(0., (gap-shift-floor)/.0016)
        correction = max(0., gap-target) / max(.55, n.dot(ray))
        v.co -= ray * correction
    obj.data.update()


def support_faces(obj, tree):
    # Long, low-poly triangles can cross a convex skull between otherwise
    # valid vertices. Offset only surfaces whose interiors approach the head.
    mesh = obj.data
    for _ in range(10):
        offsets = np.zeros(len(mesh.vertices))
        for face in mesh.polygons:
            corners = [mesh.vertices[i].co for i in face.vertices]
            a, b, c = corners
            probes = [(a + b + c) / 3]
            for u, v in ((a,b), (b,c), (c,a)):
                probes.extend(u.lerp(v, f) for f in (.25, .5, .75))
            delta = 0.
            for p in probes:
                loc, normal, _, _ = tree.find_nearest(p)
                dist = (p - loc).dot(normal)
                if dist < .0039:
                    ray = (p - ROOT).normalized()
                    delta = max(delta, (.0042 - dist) / max(.45, ray.dot(normal)))
            for i in face.vertices:
                offsets[i] = max(offsets[i], delta)
        if max(offsets) == 0:
            break
        for i in np.flatnonzero(offsets):
            v = mesh.vertices[int(i)]
            v.co += (v.co - ROOT).normalized() * min(.008, offsets[i])
    mesh.update()


def fit_mesh(obj, body):
    tree = tree_for(body, head_only=True)
    locks = obj.data.attributes["temple_lock"]
    for v in obj.data.vertices:
        v.co = map_point(v.co.copy(), tree, locks.data[v.index].value)
    obj.data.attributes.remove(locks)
    open_ears(obj)
    correct_clearance(obj, tree)
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("Silhouette-preserving collapse", "DECIMATE")
    mod.ratio = min(1.0, 2998 / len(obj.data.polygons))
    mod.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    correct_clearance(obj, tree)
    remove_lining(obj)
    nest_crown(obj, tree)
    correct_clearance(obj, tree)
    support_faces(obj, tree)
    # Discard source custom normals after nonuniform deformation.
    if obj.data.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    for face in obj.data.polygons:
        face.use_smooth = True
    obj.data.calc_loop_triangles()
    print("Fitted triangles:", len(obj.data.loop_triangles))
    assert len(obj.data.loop_triangles) <= 3000


def dress(obj, arm):
    mat = obj.data.materials[0]
    mat.name = "Chestnut Bob"
    mat.diffuse_color = (.265, .112, .078, 1)
    tex = next(n.image for n in mat.node_tree.nodes if n.type == "TEX_IMAGE")
    tex.name = "Bob_BaseColor"
    tex.scale(1024, 1024)
    # The importer retains the original packed JPEG. Replace its bytes with
    # the resized image before persistence and export.
    with tempfile.TemporaryDirectory(dir=HERE) as tmp:
        tex.filepath_raw = str(Path(tmp) / "Bob_BaseColor.jpg")
        tex.file_format = "JPEG"
        tex.save(quality=94)
        data = Path(tex.filepath_raw).read_bytes()
        tex.pack(data=data, data_len=len(data))
    tex.filepath_raw = "//Bob_BaseColor.jpg"
    # A material tint keeps the original strands and highlights in the atlas.
    tree = mat.node_tree
    color = next(n for n in tree.nodes if n.type == "TEX_IMAGE")
    bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
    tint = tree.nodes.new("ShaderNodeMix")
    tint.data_type = "RGBA"
    tint.blend_type = "MULTIPLY"
    tint.inputs[0].default_value = 1
    tint.inputs[7].default_value = (.56, .47, .45, 1)
    tree.links.new(color.outputs["Color"], tint.inputs[6])
    tree.links.new(tint.outputs[2], bsdf.inputs["Base Color"])
    head = obj.vertex_groups.new(name=HEAD)
    neck = obj.vertex_groups.new(name=NECK)
    weights = []
    for v in obj.data.vertices:
        x, y, z = v.co
        w = .105 * smooth(-.008, .095, y) * (1 - smooth(.652, .760, z))
        if w < .0001:
            w = 0.
        head.add([v.index], 1 - w, "REPLACE")
        if w:
            neck.add([v.index], w, "REPLACE")
            weights.append(w)
    print("Neck blend:", len(weights), "vertices; max", max(weights))
    mod = obj.modifiers.new("Master skeleton", "ARMATURE")
    mod.object = arm
    return tex


def build():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    sc = bpy.context.scene
    arm, body = sc.objects["Armature"], sc.objects["Base_Body"]
    obj = load_hair()
    prepare_strands(obj)
    fit_mesh(obj, body)
    dress(obj, arm)
    bpy.ops.object.select_all(action="DESELECT")
    for o in (obj, arm):
        o.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=str(GLB), export_format="GLB", use_selection=True,
                              export_animations=False, export_yup=True, export_def_bones=False,
                              export_all_influences=False)
    obj.parent = arm
    # The fitting reference is available when reopening the editable scene.
    arm.hide_set(True)
    obj.select_set(True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                space = area.spaces.active
                space.overlay.show_overlays = False
                space.shading.color_type = "TEXTURE"
                space.region_3d.view_rotation = Vector((0, 1, 0)).to_track_quat("-Z", "Y")
                space.region_3d.view_distance = .75
                space.region_3d.view_location = (0, 0, .79)
                space.region_3d.view_perspective = "ORTHO"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("GLB SHA256", hashlib.sha256(GLB.read_bytes()).hexdigest(), flush=True)


def checker_command():
    return [bpy.app.binary_path, "-b", "-noaudio", "--python-exit-code", "1",
            "--python", str(HERE / "motion_check.py"), "--", str(MASTER), str(MOTION),
            str(GLB), str(HERE)]


def cpu_studio(sc):
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 12
    sc.cycles.use_denoising = True
    sc.render.resolution_percentage = 100
    sc.render.use_compositing = False
    sc.render.use_sequencer = False
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    sc.world = bpy.data.worlds.new("QA studio")
    sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (.74, .77, .82, 1)
    sc.world.node_tree.nodes["Background"].inputs[1].default_value = .5
    for name, pos, power, size in (
            ("Key", (-1.2, -1.8, 2.5), 95, 1.9),
            ("Fill", (1.4, -1, 1.5), 46, 1.7),
            ("Rim", (.4, 1.5, 2.0), 90, 1.2)):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size = power, "DISK", size
        obj = bpy.data.objects.new(name, data)
        sc.collection.objects.link(obj)
        obj.location = pos
        obj.rotation_euler = (Vector((0, 0, .77)) - obj.location).to_track_quat("-Z", "Y").to_euler()


def cpu_check():
    # Keep the checker file, action selection, pose math, sign convention,
    # frame selection, camera and outputs intact. Headless Metal aborts at
    # the first Workbench render on this machine.
    @bpy.app.handlers.persistent
    def use_cpu(scene, *_):
        if scene.camera and scene.camera.name == "c" and scene.render.engine == "BLENDER_WORKBENCH":
            cpu_studio(scene)

    bpy.app.handlers.frame_change_pre.append(use_cpu)
    old = sys.argv
    try:
        sys.argv = checker_command()[5:]
        runpy.run_path(str(HERE / "motion_check.py"), run_name="__main__")
    finally:
        sys.argv = old
        bpy.app.handlers.frame_change_pre.remove(use_cpu)


def sheet():
    # Import the exact GLB into the original master, separate from authoring.
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    sc = bpy.context.scene
    cpu_studio(sc)
    camera = bpy.data.cameras.new("Fit camera")
    co = bpy.data.objects.new("Fit camera", camera)
    sc.collection.objects.link(co)
    sc.camera = co
    camera.type = "ORTHO"
    camera.ortho_scale = .55
    target = Vector((0, 0, .807))
    sc.render.resolution_x = sc.render.resolution_y = 520
    views = [(0, -1, 0), (.6, -1, .08), (-.6, -1, .08), (1, 0, .03), (0, 1, .06), (-1, 0, .03)]
    pixels = np.empty((1040, 1560, 4), dtype=np.float32)
    with tempfile.TemporaryDirectory(dir=HERE) as tmp:
        for i, direction in enumerate(views):
            co.location = target + Vector(direction).normalized() * 2
            co.rotation_euler = (target - co.location).to_track_quat("-Z", "Y").to_euler()
            sc.render.filepath = str(Path(tmp) / f"view{i}.png")
            bpy.ops.render.render(write_still=True)
            im = bpy.data.images.load(sc.render.filepath)
            # Join the rendered PNG samples in display space, without applying
            # a second view transform when the sheet is written.
            im.colorspace_settings.name = "Non-Color"
            a = np.empty(520 * 520 * 4, dtype=np.float32)
            im.pixels.foreach_get(a)
            y, x = (1 - i // 3) * 520, (i % 3) * 520
            pixels[y:y+520, x:x+520] = a.reshape((520, 520, 4))
            bpy.data.images.remove(im)
    result = bpy.data.images.new("Bob fit views", 1560, 1040, alpha=True)
    result.colorspace_settings.name = "Non-Color"
    result.pixels.foreach_set(pixels.ravel())
    result.filepath_raw = str(HERE / "fit_views.png")
    result.file_format = "PNG"
    result.save()


def read_glb(path):
    data = path.read_bytes()
    size = struct.unpack_from("<I", data, 12)[0]
    return json.loads(data[20:20+size]), memoryview(data)[28+size:]


def accessor(doc, binary, index):
    spec = doc["accessors"][index]
    view = doc["bufferViews"][spec["bufferView"]]
    fields = {"SCALAR": 1, "VEC3": 3, "VEC4": 4, "MAT4": 16}[spec["type"]]
    dtype = {5121: "u1", 5123: "<u2", 5125: "<u4", 5126: "<f4"}[spec["componentType"]]
    offset = view.get("byteOffset", 0) + spec.get("byteOffset", 0)
    assert "byteStride" not in view
    return np.frombuffer(binary, dtype=dtype, offset=offset,
                         count=spec["count"] * fields).reshape(-1, fields)


def audit_skin():
    doc, binary = read_glb(GLB)
    base, base_binary = read_glb(MASTER.with_name("base_body.glb"))
    mesh, = doc["meshes"]
    prim, = mesh["primitives"]
    hair_node, = [n for n in doc["nodes"] if "mesh" in n]
    assert hair_node["name"] == "Hair_Bob" and not any(k in hair_node for k in ("matrix", "rotation", "scale", "translation"))
    assert not any(doc.get(k) for k in ("animations", "cameras"))
    assert set(prim["attributes"]) == {"POSITION", "NORMAL", "TEXCOORD_0", "JOINTS_0", "WEIGHTS_0"}

    def skeleton(g):
        sk, = g["skins"]
        return [g["nodes"][i]["name"] for i in sk["joints"]], sk["inverseBindMatrices"]
    names, bind = skeleton(doc)
    reference, base_bind = skeleton(base)
    assert names == reference and len(set(names)) == 65
    def bone_children(g):
        nodes = g["nodes"]
        return {nodes[i]["name"]: sorted(nodes[c]["name"] for c in nodes[i].get("children", []))
                for i in g["skins"][0]["joints"]}
    assert bone_children(doc) == bone_children(base)
    assert np.allclose(accessor(doc, binary, bind), accessor(base, base_binary, base_bind), atol=1e-6, rtol=0)
    assert all(name.startswith("mixamorig:") for name in names)
    weights = accessor(doc, binary, prim["attributes"]["WEIGHTS_0"])
    joints = accessor(doc, binary, prim["attributes"]["JOINTS_0"])
    active = weights > 0.
    assert np.allclose(weights.sum(1), 1., atol=1e-6)
    assert {names[i] for i in np.unique(joints[active])} == {HEAD, NECK}
    neck = np.sum(np.where(joints == names.index(NECK), weights, 0.), axis=1)
    tris = len(accessor(doc, binary, prim["indices"])) // 3
    assert tris <= 3000 and np.max(active.sum(1)) <= 4
    return tris, int(np.max(active.sum(1))), float(neck.max())


def crown_distances(skin, hair):
    # Above the highest forehead opening, every direction should encounter
    # hair. Measure the first hair surface rather than the outer ridge.
    distances = []
    for elevation in list(range(25, 90, 2)) + [90]:
        el = math.radians(elevation)
        angles = [0] if elevation == 90 else range(0, 360, 2)
        for angle in angles:
            az = math.radians(angle)
            ray = Vector((math.cos(az)*math.cos(el), math.sin(az)*math.cos(el), math.sin(el)))
            p = skin.ray_cast(ROOT + .60*ray, -ray, .60)[0]
            q = hair.ray_cast(p + .00005*ray, ray, .14)[0]
            assert q is not None, (elevation, angle, "gap in upper cap")
            distances.append(skin.find_nearest(q)[3])
    return len(distances), min(distances), max(distances)


def all_frames():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    sc = bpy.context.scene
    body, arm = sc.objects["Base_Body"], sc.objects["Armature"]
    assert "Hair_Bob" not in sc.objects
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    hair = sc.objects["Hair_Bob"]
    assert hair.matrix_world == Matrix.Identity(4)
    for md in hair.modifiers:
        if md.type == "ARMATURE":
            md.object = arm
    hair.parent = arm
    atlas, = [n.image for n in hair.data.materials[0].node_tree.nodes if n.type == "TEX_IMAGE"]
    assert tuple(atlas.size) == (1024, 1024) and atlas.packed_file
    bpy.ops.import_scene.gltf(filepath=str(MOTION))
    arm.animation_data_create()
    rows = {}
    crown, cap = None, None
    for name in ("rest", "walk", "run", "wave", "jump", "idle", "nod", "dance"):
        action = None if name == "rest" else bpy.data.actions[name]
        arm.animation_data.action = action
        frames = [1]
        if action:
            arm.animation_data.action_slot = action.slots[0]
            frames = range(int(action.frame_range[0]), int(action.frame_range[1]) + 1)
        pairs, inside, distance = 0, 0, float("inf")
        for frame in frames:
            sc.frame_set(frame)
            dg = bpy.context.evaluated_depsgraph_get()
            be, he = body.evaluated_get(dg), hair.evaluated_get(dg)
            body_tree, hair_tree = tree_for(be), tree_for(he)
            pairs = max(pairs, len(body_tree.overlap(hair_tree)))
            signs = []
            for v in he.data.vertices:
                p = he.matrix_world @ v.co
                q, normal, _, _ = body_tree.find_nearest(p)
                signs.append((p-q).dot(normal))
            inside = max(inside, sum(s < 0 for s in signs))
            distance = min(distance, min(signs))
            if name == "rest":
                origin = Vector((.001, 0., 1.22))
                axis = Vector((0., 0., -1.))
                crown = hair_tree.ray_cast(origin, axis)[0].z - body_tree.ray_cast(origin, axis)[0].z
                cap = crown_distances(body_tree, hair_tree)
        rows[name] = (len(frames), inside, distance, pairs)
        print("FRAME AUDIT", name, rows[name], flush=True)
    return rows, crown, cap


def validator():
    node = shutil.which("node")
    if not node:
        return "Skipped because Node.js was unavailable."
    code = """const fs = require('fs');
const validator = require('gltf-validator');
validator.validateBytes(new Uint8Array(fs.readFileSync(process.argv[1]))).then(report => {
  console.log(JSON.stringify([validator.version(), report.issues]));
}).catch(e => { console.error(e); process.exitCode = 1; });"""
    output = subprocess.check_output([node, "-e", code, str(GLB)], cwd=REPO, text=True)
    version, result = json.loads(output)
    assert result["numErrors"] == result["numWarnings"] == 0, result
    return f"Khronos glTF Validator {version} reported 0 errors and 0 warnings."


def write_notes(renderer):
    tris, influences, neck = audit_skin()
    full, crown, cap = all_frames()
    sampled = json.loads((HERE / "motion_check.json").read_text())
    validation = validator()
    rows = []
    for name, (frames, inside, distance, pairs) in full.items():
        counted, sd = sampled[name]
        rows.append(f"| {name} | {counted} | {sd:.6f} | {frames} | {inside} | {distance:.6f} | {pairs} |")
    capture = "\n".join(rows)
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    files = [BLEND, GLB, HERE / "fit_views.png"] + [HERE / f"{n}.png" for n in ("walk", "run", "wave", "jump")]
    manifest = "\n".join(f"| {path.name} | {path.stat().st_size:,} | `{digest(path)}` |" for path in files)
    text = f"""# Chibi chestnut bob

The GLB contains one textured mesh and one skin with {tris:,} triangles. The editable Blender file includes the master body as a fitting reference. The root-level GLB mesh uses the master origin, glTF +Y up and +Z front. All 65 joint names match the base in order and have identical child-bone hierarchies. Inverse bind matrices match to 0.000001 absolute tolerance. The mesh uses at most {influences} normalized influences. Head carries the bob, with up to {100*neck:.2f}% Neck weight at the lower rear. The GLB has no clips or body geometry.

## Extraction and fit

The original Tripo mesh faces Blender +X. Its front-facing skin shell contains 1,299 of the 5,253 triangles. UV-seam welding separates that shell, the 3,860-triangle main hair mass, a 92-triangle temple lock and a two-triangle internal sliver. The build removes the face and sliver, cuts the deep lining out of the original strands and opens the lower curtains around the master ears. A mirrored copy of the intact Tripo temple lock replaces the fused opposite lock. The imported UVs and base-color image supply the strand detail. The embedded 2,048-pixel atlas is reduced to 1,024 × 1,024 and tinted chestnut in the material.

The vertical gap above the scalp at Blender (x=0.001, y=0) in the rest pose measures {crown:.6f} m. Across {cap[0]:,} radial samples of the continuous upper cap, first-layer clearance was {cap[1]:.6f} to {cap[2]:.6f} m. The audit covers every two degrees of azimuth and elevation from 25° above horizontal through the pole, and all rays hit hair. Sculpted outer locks and free ends have greater standoff. The lower and face openings let the module fit over the head. The reference is a single front image with a blank face. Eye clearance is judged on the actual master, and the rear shape follows the supplied 3D source.

The rebuilt side locks frame the outer eye corners. Both iris centers and both ears are visible from the front. The original rear cap is smoother than the separated front locks. Small highlight and shading variations remain near the temples. One pinpoint on the upper left profile falls inside a continuous hair triangle and corresponds to a darker region of the base-color atlas. The lower rim is intentionally open, with narrow gaps between separate locks.

## Export checks

{validation} Blender {bpy.app.version_string} reimported the saved GLB. The supplied checker ran on the original master and motion GLB. {renderer} Each standard clip RESULT uses its 12 requested sample frames. The supplemental pass checks every integer frame, including both endpoints, for signed vertex clearance and triangle-to-triangle intersections against the evaluated body. All distances are in metres. Fractional times between integer frames are outside this audit.

| Clip | RESULT max inside | RESULT min distance | Full frames | Full max inside | Full min distance | Full max intersecting triangle pairs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{capture}

## Files and reproduction

Run the supplied guarded Blender executable in background mode with `--python fit_hair.py`. Keep the repository input layout, the supplied `motion_check.py` beside the build script and the installed validator available. The script builds the blend and GLB, checks the exported file, renders all five PNGs and writes this report. `motion_check.json` is the unmodified checker's output. The 3×2 fit sheet shows the reimported GLB on the master. Top row is front, left and right three-quarter. Bottom row is left profile, rear and right profile. The orthographic camera is fixed (0.55 m, 520 pixels per view, Cycles CPU).

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
{manifest}

Source GLB `{digest(SOURCE)}`  
Master blend `{digest(MASTER)}`  
Motion GLB `{digest(MOTION)}`  
Reference PNG `{digest(HERE.parent / "white-bg/hair-01-bob.png")}`
"""
    (HERE / "NOTES.md").write_text(text, encoding="utf-8")
    assert all(n == 0 and d >= .0005 for n, d in sampled.values()), sampled
    assert all(i == 0 and d >= .0005 and p == 0 for _, i, d, p in full.values()), full
    assert .004 <= crown <= .012, crown
    assert .004 <= cap[1] <= cap[2] <= .012, cap


if __name__ == "__main__":
    renderer = "The original Workbench renderer completed."
    if "--qa-only" not in sys.argv:
        build()
        # Always attempt the user's exact checker before its CPU fallback.
        result = subprocess.run(checker_command(), cwd=HERE)
        if result.returncode:
            print("Native checker exit:", result.returncode, "retrying with CPU rendering", flush=True)
            cpu_check()
            renderer = "Native Workbench aborted headlessly on macOS. The unchanged checker completed using a frame handler that switches only rendering to Cycles CPU."
    else:
        cpu_check()
        renderer = "The unchanged checker completed using Cycles CPU for headless renders."
    sheet()
    write_notes(renderer)
