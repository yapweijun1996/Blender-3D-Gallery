"""Rebuild the fitted bob in Blender. Run with the supplied guarded Blender.

Uses the read-only v1 blend and its camera, fitting and skin-audit helpers.
The default entry point builds, checks and renders the reimported GLB.
"""
import importlib.util
import hashlib
import json
import math
from pathlib import Path
import runpy
import sys
import tempfile

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
# The read-only source is part of the rebuild contract. Avoid .pyc beside it.
sys.dont_write_bytecode = True
source = importlib.util.spec_from_file_location("bob_v1", HERE.parent / "fit_hair.py")
base = importlib.util.module_from_spec(source)
source.loader.exec_module(base)

GLB = HERE / "hair_bob_v2.glb"
BLEND = HERE / "hair_bob_v2.blend"
MASTER, MOTION, ROOT = base.MASTER, base.MOTION, base.ROOT
OLD = base.BLEND
TAU = 2 * math.pi
sstep = base.smooth
rad = math.radians
degrees = math.degrees
HEAD, NECK = base.HEAD, base.NECK


def polar(p):
    d = (p - ROOT).normalized()
    return math.atan2(d.x, -d.y), math.asin(max(-1, min(1, d.z)))


def direction(a, e):
    return Vector((math.cos(e) * math.sin(a), -math.cos(e) * math.cos(a), math.sin(e)))


def blend(a, b, fraction):
    return a + (b - a) * fraction


def hem(a):
    # The open frontal hairline sits underneath the parted bangs.
    # The narrowing tip at the sideburn shares vertices with the curtain.
    knots = [(0, 22), (12, 22), (24, 30), (32, 27), (44, 11), (55, 3),
             (62, -6), (65, -12), (70, -43), (75, -32), (80, -12.5),
             (87, -10.4), (94, -10), (101, -12), (105, -19), (111, -44),
             (118, -58), (128, -55), (140, -63), (150, -57), (161, -65),
             (171, -60), (180, -64)]
    return rad(float(np.interp(abs(degrees(a)), *zip(*knots))))


def field(a, e):
    # Comb lines curve around the ear. Phase is periodic at the nape.
    return 14 * a - 1.45 * math.sin(a) * math.cos(e + .20) + .52 * math.sin(3 * a) + .16 * math.sin(5 * a + e)


def surface(skin, a, e, inset=0):
    ray = direction(a, e)
    loc, n, _, _ = skin.ray_cast(ROOT + ray * .51, -ray, .505)
    if loc is None:
        raise ValueError(("Missing scalp", degrees(a), degrees(e)))
    strength = sstep(38, 84, abs(degrees(a)))
    groove = (.5 + .5 * math.cos(field(a, e))) ** 2
    amount = .0067 + strength * (.001 + .0031 * groove) * max(0, math.cos(e)) - inset
    # Running compresses the skinning gap at the low occiput. Ease the
    # fitted lining outward locally while preserving the neck weights.
    amount += .00115 * sstep(120, 157, abs(degrees(a))) * (1 - sstep(.714, .754, loc.z))
    r = (loc - ROOT).dot(ray) + amount / max(.38, n.dot(ray))
    return ROOT + r * ray


def scalp_offset(skin, a, e, distance):
    ray = direction(a, e)
    hit, n, _, _ = skin.ray_cast(ROOT + ray * .52, -ray, .515)
    return hit + ray * (distance / max(.4, n.dot(ray)))


def bezier(points, t):
    p, q, r, s = points
    u = 1 - t
    return u**3 * p + 3 * u * u * t * q + 3 * u * t * t * r + t**3 * s


def add_bangs(obj, skin):
    # Each path is a broad forelock combed from the same part. The section
    # rolls under at the edges and the point has a single shared vertex.
    # Coordinates describe longitude and elevation on the fitted scalp.
    specs = [
        ([(5, 55), (-20, 53), (-28, 22), (-44, 5)], 13.0, .0090, 0),
        ([(8, 55), (31, 50), (33, 20), (51, 4)], 11.5, .0090, 1),
        ([(6, 55), (-41, 59), (-70, 12), (-38, 1.7)], 11.8, .0120, 2),
        ([(8, 55), (57, 54), (72, 10), (40, 2.1)], 11.4, .0120, 3),
        ([(8, 55), (23, 40), (24, 13), (10, -.4)], 8.5, .0097, 4),
        ([(6, 55), (-3, 41), (17, 15), (-9, -1.9)], 12.8, .0132, 5),
    ]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uv = bm.loops.layers.uv.active
    lock_faces = []
    sections = 12
    # The flattened underside requires fewer samples than the lit face.
    angles = [0, 34, 70, 106, 145, 180, 270]
    for path, width, bulge, slot in specs:
        points = np.deg2rad(np.array(path, dtype=float))
        rows = []
        for j in range(sections + 1):
            t = j / sections
            center = bezier(points, t)
            tangent = bezier(points, min(1, t + .002)) - bezier(points, max(0, t - .002))
            tangent[0] *= max(.45, math.cos(center[1]))
            tangent /= np.linalg.norm(tangent)
            across = np.array((-tangent[1] / max(.45, math.cos(center[1])), tangent[0]))
            envelope = math.sin(math.pi * t)**.77 * (1.05 - .13 * t)
            radius = rad(width) * envelope
            if j in (0, sections):
                p = scalp_offset(skin, *center, .0073 if j == 0 else .0090)
                rows.append([bm.verts.new(p)])
                continue
            row = []
            for ang in angles:
                c, sn = math.cos(rad(ang)), math.sin(rad(ang))
                a, e = center + across * radius * c
                depth = .0075 + .0015 * t + envelope * (bulge * max(0, sn) - .0017 * max(0, -sn))
                row.append(bm.verts.new(scalp_offset(skin, a, e, depth)))
            rows.append(row)
        for j in range(sections):
            for k in range(len(angles)):
                k1 = (k + 1) % len(angles)
                # Same UV on the dorsal/ventral edge. The painted band
                # tapers with the actual geometry, including its pointed tip.
                a0, a1 = angles[k], angles[k1]

                def corner(row, idx, theta):
                    v = rows[row][0 if len(rows[row]) == 1 else idx]
                    u = (1 + math.cos(rad(theta))) * .5
                    return v, ((slot * 160 + 7 + 146 * u) / 1024, (14 + 720 * row / sections) / 1024)
                poly = [corner(j, k, a0), corner(j + 1, k, a0), corner(j + 1, k1, a1), corner(j, k1, a1)]
                if j == 0:
                    poly.pop(3)
                if j + 1 == sections:
                    poly.pop(2)
                f = bm.faces.new([c[0] for c in poly])
                f.smooth = True
                lock_faces.append(f)
                for l, c in zip(f.loops, poly):
                    l[uv].uv = c[1]
    bmesh.ops.recalc_face_normals(bm, faces=lock_faces)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def add_curtain(obj, skin, columns, rings):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uv = bm.loops.layers.uv.active
    # Shift the top pole toward the part while keeping the bottom opening
    # and all ear/rim coordinates fixed.

    def coordinates(i, t, inset=0, turn=0):
        a = (i / columns - .5) * TAU
        e = blend(math.pi / 2, hem(a), t) + turn
        vec = direction(a, e)
        vec.y -= .20 * (1 - t)**2
        vec.normalize()
        aa, ee = math.atan2(vec.x, -vec.y), math.asin(vec.z)
        return surface(skin, aa, ee, inset), (i / columns, t)

    def face(vs, uvs):
        f = bm.faces.new(vs)
        f.smooth = True
        for loop, (u, t) in zip(f.loops, uvs):
            # Explicit duplicate UV at the nape avoids interpolation across
            # the atlas. The two endpoint texels sample the same comb line.
            loop[uv].uv = ((1 + 1021 * u) / 1024, (1022 - 250 * t) / 1024)

    pole = bm.verts.new(coordinates(0, 0)[0])
    rows = []
    steps = [(j / rings, 0., 0.) for j in range(1, rings + 1)]
    steps.append((1., .0018, rad(.6)))
    for t, inset, turn in steps:
        rows.append([bm.verts.new(coordinates(i, t, inset, turn)[0]) for i in range(columns)])
    # Behind the pinna a bob has a rolled hem. The fitted cavity continues
    # down the skull; the combed outside turns around and joins it, providing
    # actual hair thickness instead of a free-floating strand beside the ear.
    start = 4
    outside = {}

    def edge_profile(x, pts):
        return float(np.interp(x, *zip(*pts)))

    def horizontal_floor(a, z):
        axis = Vector((math.sin(a), -math.cos(a), 0))
        center = Vector((ROOT.x, ROOT.y, z))
        hit, n, _, _ = skin.ray_cast(center + .40 * axis, -axis, .395)
        if hit is None:
            return 0.
        return (hit - center).dot(axis) + .0074 / max(.48, n.dot(axis))
    for i in range(columns):
        a = TAU * (i / columns - .5)
        ad = abs(degrees(a))
        gain = sstep(80, 105, ad)
        if gain < .00001:
            continue
        axis = Vector((math.sin(a), -math.cos(a), 0))
        r0 = math.hypot(rows[start][i].co.x - ROOT.x, rows[start][i].co.y - ROOT.y)
        prev = math.hypot(rows[start - 1][i].co.x - ROOT.x, rows[start - 1][i].co.y - ROOT.y)
        end = rows[rings - 1][i].co
        endz = edge_profile(ad, [(80, .759), (90, .756), (95, .748), (100, .735),
                                 (105, .699), (110, .658), (115, .641), (120, .640),
                                 (130, .654), (140, .642), (150, .650), (165, .643), (180, .650)])
        endr = edge_profile(ad, [(80, .178), (95, .188), (100, .193), (105, .187),
                                 (110, .177), (115, .162), (125, .158), (140, .150),
                                 (160, .141), (180, .137)])
        for k in range(start + 1, rings):
            t = (k - start) / (rings - 1 - start)
            u = 1 - t
            inner = rows[k][i].co
            aa, _ = polar(inner)
            axis = Vector((math.sin(aa), -math.cos(aa), 0))
            z = inner.z + gain * (endz - end.z) * t**1.2
            shaped = u**3 * r0 + 3 * u * u * t * (r0 + 1.7 * (r0 - prev)) + \
                3 * u * t * t * (endr + .053) + t**3 * endr
            # A broad swept ridge and a narrower groove run to the hem.
            comb = 14 * (a - .28 * math.sin(a) * ((k + 1) / rings)**1.45) + .52 * math.sin(3 * a)
            shaped += .0038 * math.sin(t * math.pi * .82) * math.cos(comb)
            drape = blend((inner - ROOT).dot(axis), shaped, gain)
            r = max(drape, (inner - ROOT).dot(axis) + .0026 * gain * math.sin(t * math.pi / 2))
            # Account for the back edge of the ear, including its rounded
            # top where one horizontal scan can miss the nearby overhang.
            r = max(r, horizontal_floor(aa, z), horizontal_floor(aa, z + .006) - .003)
            outside[k, i] = bm.verts.new(Vector((ROOT.x, ROOT.y, z)) + r * axis)
        # A single return course folds beneath the lower hem. It is checked
        # against the ear at its interpolated height before joining the cavity.
        inn = rows[-1][i].co
        out = outside[rings - 1, i].co
        q = out.lerp(inn, .39)
        q.z -= .0055 * gain
        q += axis * max(0, horizontal_floor(a, q.z) - (q - ROOT).dot(axis))
        outside[rings, i] = bm.verts.new(q)

    lining = {}
    for i in range(columns):
        j = (i + 1) % columns
        u, v = i / columns, (i + 1) / columns
        face([pole, rows[0][i], rows[0][j]], [((u + v) / 2, 0), (u, steps[0][0]), (v, steps[0][0])])
        for k in range(1, len(rows)):
            t0, t1 = steps[k - 1][0], steps[k][0]
            corners = [(u, t0), (u, t1), (v, t1), (v, t0)]
            indices = [(k - 1, i), (k, i), (k, j), (k - 1, j)]
            original = [rows[row][col] for row, col in indices]
            outer = [outside.get(idx, pt) for idx, pt in zip(indices, original)]
            if outer != original:
                face(outer, corners)
                if k > start:
                    liner = []
                    for idx, pt in zip(indices, original):
                        if idx not in lining:
                            if idx[0] == rings:
                                lining[idx] = pt
                            else:
                                lining[idx] = bm.verts.new(pt.co.copy())
                        liner.append(lining[idx])
                    face(liner[::-1], corners[::-1])
            else:
                face(original, corners)
        verts = [outside.get((rings, i), rows[-1][i]), rows[-1][i],
                 rows[-1][j], outside.get((rings, j), rows[-1][j])]
        rim = []
        for vtx, st in zip(verts, [(u, .985), (u, 1.), (v, 1.), (v, .985)]):
            if all(vtx != pt for pt, _ in rim):
                rim.append((vtx, st))
        if len(rim) >= 3:
            face([p for p, _ in rim], [st for _, st in rim])
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def make_atlas(obj):
    # One locally painted atlas, with continuous color across the ear and
    # nape and dedicated, padded strips for the forward section of each lock.
    atlas = np.zeros((1024, 1024, 4), 'f')
    atlas[:, :, 3] = 1.
    xs = (np.arange(1024) + .5)[None, :]
    ys = (np.arange(768) + .5)[:, None]
    for slot in range(6):
        u = np.clip((xs - slot * 160 - 7) / 146, 0, 1)
        t = np.clip((ys - 14) / 720, 0, 1)
        root = 1 - t
        depth = .92 + .10 * root - .24 * (2 * u - 1)**6
        edge = .014 * np.sin(29 * u + 1.1 * t) + .006 * np.cos(85 * u - .5 * t)
        strand = depth + edge + .078 * np.exp(-((u - .40) / .21)**2) * np.sin(math.pi * t)
        for k, (bottom, upper) in enumerate(((.43, .65), (.222, .421), (.170, .428))):
            color = (bottom + (upper - bottom) * root) * strand
            atlas[:768, slot * 160:(slot + 1) * 160, k] = color[:, slot * 160:(slot + 1) * 160]
    a = TAU * ((np.clip(xs - 1, 0, 1021) / 1021) - .5)
    t = np.clip((1022 - (np.arange(768, 1024) + .5)[:, None]) / 250, 0, 1)
    phase = 14 * (a - .28 * np.sin(a) * t**1.45) + .52 * np.sin(3 * a) + .18 * np.sin(5 * a + t)
    tone = (.5 + .5 * np.cos(phase))**.8
    strand = .875 + .17 * tone + .029 * np.cos(2 * phase + .38) + .008 * np.sin(8 * phase)
    for k, (bottom, upper) in enumerate(((.43, .65), (.222, .421), (.170, .428))):
        atlas[768:, :, k] = (bottom + (upper - bottom) * (1 - t)**.73) * strand
    tex = bpy.data.images.new("Bob chestnut atlas", 1024, 1024, alpha=False)
    tex.colorspace_settings.name = "sRGB"
    tex.pixels.foreach_set(atlas.ravel())
    node = next(n for n in obj.active_material.node_tree.nodes if n.type == 'TEX_IMAGE')
    shader = next(n for n in obj.active_material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    shader.inputs['Roughness'].default_value = .60
    old = node.image
    node.image = tex
    with tempfile.TemporaryDirectory(dir=HERE) as tmp:
        tex.filepath_raw = str(Path(tmp) / "Bob_Chestnut.jpg")
        tex.file_format = "JPEG"
        tex.save(quality=96)
        data = Path(tex.filepath_raw).read_bytes()
        tex.pack(data=data, data_len=len(data))
    tex.filepath_raw = "//Bob_Chestnut.jpg"
    bpy.data.images.remove(old)


def build():
    bpy.ops.wm.open_mainfile(filepath=str(OLD))
    scene = bpy.context.scene
    arm, obj, body = [scene.objects[n] for n in ("Armature", "Hair_Bob", "Base_Body")]
    arm.hide_set(False)
    obj.parent = None
    for m in list(obj.modifiers):
        obj.modifiers.remove(m)
    obj.vertex_groups.clear()
    skin = base.tree_for(body, head_only=True)
    mat = obj.active_material
    old_mesh = obj.data
    obj.data = bpy.data.meshes.new("Bob combed scalp and forelocks")
    obj.data.materials.append(mat)
    obj.data.uv_layers.new(name="Bob atlas")
    bpy.data.meshes.remove(old_mesh)
    add_curtain(obj, skin, 72, 10)
    add_bangs(obj, skin)
    base.correct_clearance(obj, skin)
    base.support_faces(obj, skin)
    make_atlas(obj)
    h = obj.vertex_groups.new(name=HEAD)
    n = obj.vertex_groups.new(name=NECK)
    for v in obj.data.vertices:
        x, y, z = v.co
        w = .105 * sstep(-.008, .095, y) * (1 - sstep(.652, .760, z))
        if w < .0001:
            w = 0.
        h.add([v.index], 1 - w, "REPLACE")
        if w:
            n.add([v.index], w, "REPLACE")
    for f in obj.data.polygons:
        f.use_smooth = True
    mod = obj.modifiers.new("Master skeleton", "ARMATURE")
    mod.object = arm
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=str(GLB), export_format="GLB", use_selection=True,
                              export_animations=False, export_def_bones=False, export_all_influences=False)
    obj.parent = arm
    arm.hide_set(True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("EXPORTED", GLB.stat().st_size, hashlib.sha256(GLB.read_bytes()).hexdigest(), flush=True)


def check(kind):
    # Both original checkers use the same JSON and PNG names. Isolate the
    # second run, then preserve its JSON separately. Their pose math and
    # sample sets are left intact. Only the render engine changes.
    @bpy.app.handlers.persistent
    def cpu(scene, *_):
        if scene.camera and scene.camera.name == "c" and scene.render.engine == "BLENDER_WORKBENCH":
            base.cpu_studio(scene)

    source = HERE / ("motion_check_tri.py" if kind == "tri" else "motion_check.py")
    bpy.app.handlers.frame_change_pre.append(cpu)
    old = sys.argv.copy()
    try:
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            sys.argv = [str(source), "--", str(MASTER), str(MOTION), str(GLB), tmp]
            runpy.run_path(str(source), run_name="__main__")
            result = Path(tmp) / "motion_check.json"
            data = json.loads(result.read_text())
            result.replace(source.with_suffix(".json"))
            if kind == "vertex":
                for name in ("walk", "run", "wave", "jump"):
                    (Path(tmp) / (name + ".png")).replace(HERE / (name + ".png"))
            assert list(data) == ["rest", "walk", "run", "wave", "jump", "idle", "nod", "dance"]
            assert all(count == 0 and dist >= .0005 for count, dist in data.values()), data
    finally:
        sys.argv = old
        bpy.app.handlers.frame_change_pre.remove(cpu)


def render_sheet():
    # The v1 function fixes every camera, light, view transform and pixel.
    # Redirect only its output directory to avoid changing the original.
    with tempfile.TemporaryDirectory(dir=HERE) as tmp:
        base.HERE = Path(tmp)
        try:
            base.sheet()
            (base.HERE / "fit_views.png").replace(HERE / "fit_views_v2.png")
        finally:
            base.HERE = HERE


def audit_fit():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    body = bpy.context.scene.objects['Base_Body']
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    bob = bpy.context.scene.objects['Hair_Bob']
    hair = base.tree_for(bob)
    scalp = base.tree_for(body, True)
    clearance = []
    for ad in range(-180, 180, 2):
        if abs(ad) < 75:
            continue
        a = rad(ad)
        for ed in range(-65, 26, 2):
            if ed < degrees(hem(a)) + 2:
                continue
            ray = direction(a, rad(ed))
            skin = scalp.ray_cast(ROOT + .60 * ray, -ray, .59)[0]
            assert skin is not None, (ad, ed)
            first = hair.ray_cast(skin + .00001 * ray, ray, .14)[0]
            assert first is not None, (ad, ed)
            clearance.append(scalp.find_nearest(first)[3])
    print("Side and nape fit:", len(clearance), min(clearance), max(clearance))
    assert .004 <= min(clearance) <= max(clearance) <= .012

    # Select the two connected eye meshes on the master. Compare only eye
    # pixels that the body itself exposes from each orthographic camera.
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1.e-5)
    bm.verts.index_update()
    eye_faces = []
    for part in base.connected_faces(bm):
        heights = [v.co.z for f in part for v in f.verts]
        if .67 < min(heights) and max(heights) < .80:
            eye_faces.extend(part)
    assert len(eye_faces) == 268
    eyes = BVHTree.FromPolygons([v.co.copy() for v in bm.verts],
                                [[v.index for v in f.verts] for f in eye_faces])
    bm.free()
    for camera in ((0, -1, 0), (.6, -1, .08), (-.6, -1, .08)):
        ray = Vector(camera).normalized()
        rotation = (-ray).to_track_quat('-Z', 'Y')
        right = rotation @ Vector((1, 0, 0))
        up = rotation @ Vector((0, 1, 0))
        kept = [0, 0]
        hidden = [0, 0]
        for y in range(230, 405):
            for x in range(30, 491):
                origin = Vector((0, 0, .807)) + ray + right * ((x + .5 - 260)
                                                               * .55 / 520) + up * ((260 - y - .5) * .55 / 520)
                eye = eyes.ray_cast(origin, -ray, 2)[0]
                if eye is None:
                    continue
                body_hit = scalp.ray_cast(origin, -ray, 2)[0]
                if body_hit is not None and (body_hit - eye).dot(ray) > .00003:
                    continue
                side = int(eye.x > 0)
                kept[side] += 1
                hit = hair.ray_cast(origin, -ray, 2)[0]
                if hit is not None and (hit - eye).dot(ray) > .00001:
                    hidden[side] += 1
        print("Eye pixels:", camera, kept, "hair occluded:", hidden)
        assert min(kept) > 0 and sum(hidden) == 0


def audit():
    print("Skin (triangles, active influences, maximum Neck):", base.audit_skin())
    validation = base.validator()
    print(validation)
    assert "0 errors and 0 warnings" in validation
    audit_fit()
    frames, crown, cap = base.all_frames()
    print("Crown:", crown, "upper cap:", cap)
    assert .004 <= crown <= .012 and .004 <= cap[1] <= cap[2] <= .012
    assert all(inside == 0 and pairs == 0 and d >= .0005 for _, inside, d, pairs in frames.values())


if __name__ == "__main__":
    base.GLB, base.BLEND, base.HERE = GLB, BLEND, HERE
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args or "build" in args:
        build()
    if not args or "vertex" in args:
        check("vertex")
    if not args or "tri" in args:
        check("tri")
    if not args or "sheet" in args:
        render_sheet()
    if not args or "audit" in args:
        audit()
