"""GJH abalone cans: four origin variants built from the owner's source-verified packshots.

Metres; floor centre at the origin, Blender +Z up, can front faces -Y. Deterministic.
Label textures are unrolled from the official front/back packshots (no redrawn logos or text).

    blender --background --factory-startup --python models/gjh-abalone-cans/generate.py -- \
        --packshots /path/to/Webpage-Design-Gallery/assets/companies/gjh/official
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
DIAMETER = 0.0735  # nominal metres; height follows each packshot's measured aspect ratio
SEGMENTS = 72
TEX_W, TEX_H_MAX = 1280, 640  # about 1.15x the packshot's real detail; more would only enlarge blur
LOD1_SEGMENTS, LOD1_TEX_W = 36, 640
SEG = {"segments": SEGMENTS}
SEAM = 0.0050  # double-seam height in metres
RIM_CROP = 0.05  # packshot rim fraction cropped from each end of the label

VARIANTS = [
    dict(key="nz", slug="gjh-can-new-zealand-abalone", name="New Zealand Abalone", zh="新西兰鲍鱼罐头",
         origin="New Zealand", pack="425g", root="ASSET_GJHCanNewZealandAbalone",
         front="new-moon-nz-425g-front.jpg", back="new-moon-nz-425g-back.jpg"),
    dict(key="au", slug="gjh-can-australia-abalone", name="Australia Abalone", zh="澳洲鲍鱼罐头",
         origin="Australia", pack="425g", root="ASSET_GJHCanAustraliaAbalone",
         front="new-moon-au-425g-front.jpg", back="new-moon-au-425g-back.jpg"),
    dict(key="sa", slug="gjh-can-south-africa-abalone", name="South Africa Abalone", zh="南非鲍鱼罐头",
         origin="South Africa", pack="425g", root="ASSET_GJHCanSouthAfricaAbalone",
         front="new-moon-sa-425g-front.jpg", back="new-moon-sa-425g-back.jpg"),
    dict(key="mx", slug="gjh-can-mexico-abalone", name="Mexico Abalone", zh="墨西哥鲍鱼罐头",
         origin="Mexico", pack="454g", root="ASSET_GJHCanMexicoAbalone",
         front="new-moon-mx-454g-front.jpg", back="new-moon-mx-454g-back.jpg"),
]


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--packshots", default=str(HERE.parents[2] / "Webpage-Design-Gallery/assets/companies/gjh/official"))
    return p.parse_args(argv)


def load_pixels(path):
    img = bpy.data.images.load(str(path), check_existing=False)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[:, :, :3]
    bpy.data.images.remove(img)
    return px[::-1]  # top-down rows


def can_bounds(px):
    """Bounding box (x0, x1, y0, y1) of the can, ignoring the logo header and white background."""
    ink = px.min(axis=2) < 0.86
    ink[:262] = False
    ink[905:] = False
    rows = np.where(ink.sum(axis=1) > 40)[0]
    y0, y1 = int(rows.min()), int(rows.max())
    cols = np.where(ink[y0:y1].sum(axis=0) > 40)[0]
    return int(cols.min()), int(cols.max()), y0, y1


def cubic_weights(t):
    """Catmull-Rom weights for the four taps around a fractional position t."""
    return np.stack([-0.5 * t ** 3 + t ** 2 - 0.5 * t, 1.5 * t ** 3 - 2.5 * t ** 2 + 1,
                     -1.5 * t ** 3 + 2 * t ** 2 + 0.5 * t, 0.5 * t ** 3 - 0.5 * t ** 2])


def sample(px, x, y):
    """Bicubic (Catmull-Rom) sample of a top-down image at float pixel coordinates."""
    h, w, _ = px.shape
    x = np.clip(x, 1, w - 3.001)
    y = np.clip(y, 1, h - 3.001)
    x0, y0 = x.astype(int), y.astype(int)
    wx, wy = cubic_weights(x - x0), cubic_weights(y - y0)
    out = np.zeros(x.shape + (3,), dtype=np.float32)
    for j in range(4):
        for i in range(4):
            out += px[y0 + j - 1, x0 + i - 1] * (wx[i] * wy[j])[..., None]
    return np.clip(out, 0, 1)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def gaussian_1d(a, sigma, axis):
    radius = int(sigma * 3) + 1
    k = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    k /= k.sum()
    pad = [(0, 0)] * a.ndim
    pad[axis] = (radius, radius)
    a = np.pad(a, pad, mode="edge")
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), axis, a)


def delight(px, bounds):
    """Remove the vertical shading baked into a cylinder packshot (edge darkening and the long highlight streak).

    The shading of a lit cylinder is close to a function of the column only, so it is estimated as the per-column
    median of luminance relative to each row's mean, then divided out. The viewer lights the model again."""
    x0, x1, y0, y1 = bounds
    out = px.copy()
    top, bottom = int(y0 + RIM_CROP * (y1 - y0)), int(y1 - RIM_CROP * (y1 - y0))
    cols = slice(x0 + 2, x1 - 1)
    band = px[top:bottom, cols].mean(axis=2)
    row_mean = band[:, band.shape[1] // 4: 3 * band.shape[1] // 4].mean(axis=1, keepdims=True) + 1e-4
    column = np.median(band / row_mean, axis=0)
    column = gaussian_1d(column, 16.0, 0)  # wide smoothing: per-column noise would show as vertical banding
    centre = column[len(column) // 4: 3 * len(column) // 4].mean()
    gain = np.clip(centre / np.maximum(column, 1e-3), 0.8, 1.4)
    out[:, cols] = np.clip(px[:, cols] * gain[None, :, None], 0, 1)
    return out


def sharpen(img, amount=0.7, sigma=1.1):
    blur = gaussian_1d(gaussian_1d(img, sigma, 0), sigma, 1)
    return np.clip(img + amount * (img - blur), 0, 1)


def unroll_label(front_px, back_px, fb, bb, tex_h):
    """Unroll front/back packshots into one label strip. u=0.5 is the front centre, u=0/1 the back centre."""
    u = (np.arange(TEX_W) + 0.5) / TEX_W
    phi = (u - 0.5) * 2 * np.pi
    v = (np.arange(tex_h) + 0.5) / tex_h  # 0 bottom .. 1 top
    rim = RIM_CROP
    result = []
    for px, (x0, x1, y0, y1), ang in ((front_px, fb, phi), (back_px, bb, np.where(phi >= 0, phi - np.pi, phi + np.pi))):
        cx, r = (x0 + x1) / 2, (x1 - x0) / 2
        height = y1 - y0
        top, bottom = y0 + rim * height, y1 - rim * height
        xs = cx + r * 0.995 * np.sin(ang)
        ys = bottom - v * (bottom - top)
        X, Y = np.meshgrid(xs, ys)
        result.append(sample(px, X, Y))
    # front weight 1 within 80 degrees of front centre, 0 beyond 100 degrees
    w_front = 1 - smoothstep(np.radians(80), np.radians(100), np.abs(phi))
    out = result[0] * w_front[None, :, None] + result[1] * (1 - w_front)[None, :, None]
    return out  # row 0 is the label bottom, as Blender expects


def srgb_to_linear(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def solid_material(name, rgb, metallic=0.0, roughness=0.45):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    color = (*[srgb_to_linear(c / 255) for c in rgb], 1.0)
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    m.diffuse_color = color
    return m


def label_material(name, image):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Linear"
    tex.extension = "EXTEND"
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.62  # printed lacquer: soft, no hot streaks
    return m


def link(obj, parent):
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


def empty(name, parent=None):
    return link(bpy.data.objects.new(name, None), parent)


def mesh_object(name, parent, mat, bm, smooth=True):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = smooth
    me.materials.append(mat)
    return link(bpy.data.objects.new(name, me), parent)


def lathe_bm(profile, segments=None, uv=None, cap_top=True, closed=False):
    """Radial profile [(radius, z)] revolved around Z; phi=0 faces -Y. A zero radius becomes a single pole vertex."""
    segments = segments or SEG["segments"]
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r == 0:
            rings.append(bm.verts.new((0.0, 0.0, z)))
        else:
            rings.append([bm.verts.new((r * math.sin(i * math.tau / segments - math.pi),
                                        -r * math.cos(i * math.tau / segments - math.pi), z)) for i in range(segments)])
    layer = bm.loops.layers.uv.new("UVMap") if uv else None
    for j in range(len(profile) - (0 if closed else 1)):
        for i in range(segments):
            k = (i + 1) % segments
            a, b = rings[j], rings[(j + 1) % len(profile)]
            if isinstance(a, list) and isinstance(b, list):
                face = bm.faces.new((a[i], a[k], b[k], b[i]))
            elif isinstance(a, list):
                face = bm.faces.new((a[i], a[k], b))
            else:
                face = bm.faces.new((a, b[k], b[i]))
            if layer:
                us = [i / segments, (i + 1) / segments, (i + 1) / segments, i / segments]
                vs = [uv[j], uv[j], uv[j + 1], uv[j + 1]]
                for loop, uu, vv in zip(face.loops, us, vs):
                    loop[layer].uv = (uu, vv)
    if cap_top and isinstance(rings[-1], list):
        bm.faces.new(rings[-1])
    return bm


def box_bm(size, loc, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = (v.co.x * size[0] + loc[0], v.co.y * size[1] + loc[1], v.co.z * size[2] + loc[2])
    if bevel:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=2, affect="EDGES")
    return bm


def build_can(spec, label_img, height, tinplate, lid_metal, steel, lod=0):
    r = DIAMETER / 2
    root = empty(spec["root"])
    # Body shell under the label (visible only through the seams).
    if lod == 0:
        mesh_object("CanBody", root, steel, lathe_bm([(0.0, SEAM * 0.5), (r, SEAM * 0.5), (r, height - SEAM * 0.5)], cap_top=False))
    # Rolled double seams: a rounded bead that bulges slightly past the body, with a chamfered outer lip.
    bead = r + 0.0020
    bottom = [(r - 0.0030, 0.0), (r + 0.0006, 0.0), (r + 0.0016, SEAM * 0.22), (bead, SEAM * 0.55),
              (r + 0.0016, SEAM * 0.9), (r + 0.0004, SEAM)]
    mesh_object("BottomSeam", root, tinplate, lathe_bm(bottom, cap_top=False))
    top = [(r + 0.0004, height - SEAM), (r + 0.0016, height - SEAM * 0.9), (bead, height - SEAM * 0.55),
           (r + 0.0016, height - SEAM * 0.22), (r + 0.0006, height), (r - 0.0030, height)]
    mesh_object("TopSeam", root, tinplate, lathe_bm(top, cap_top=False))
    # Lid: raised rim, recessed panel, stacking bead and a gentle pressed ring.
    lid = height - 0.0004
    panel = lid - 0.0024
    mesh_object("Lid", root, lid_metal, lathe_bm([
        (0.0, panel), (r * 0.50, panel), (r * 0.54, panel + 0.0011), (r * 0.60, panel), (r * 0.78, panel),
        (r * 0.84, panel + 0.0015), (r - 0.0034, lid - 0.0006), (r - 0.0030, lid), (r - 0.0030, lid - 0.0008),
        (r - 0.0050, lid - 0.0008), (0.0, lid - 0.0008)]))
    mesh_object("PullTabPlate", root, lid_metal, box_bm((0.020, 0.013, 0.0010), (0.0, 0.014, panel + 0.0007), 0.0003))
    ring = lathe_bm([(0.0048, 0.0), (0.0092, 0.0), (0.0092, 0.0019), (0.0048, 0.0019)], segments=40, closed=True)
    ring_obj = mesh_object("PullTabRing", root, lid_metal, ring)
    ring_obj.location = (0.0, -0.0105, panel + 0.0022)
    ring_obj.scale = (1.0, 1.4, 1.0)
    # Label: printed tin that continues under both seams, so there is no sticker edge.
    z0, z1 = SEAM * 0.6, height - SEAM * 0.6
    span = height - 2 * SEAM
    v_lo, v_hi = (z0 - SEAM) / span, (z1 - SEAM) / span
    profile = [(r - 0.0004, z0), (r + 0.0003, z0), (r + 0.0003, z1), (r - 0.0004, z1)]
    # Texture rows span seam-to-seam; the short strips under each seam repeat the edge rows.
    mesh_object("Label", root, label_material(f"Label {spec['name']}" + (" LOD1" if lod else ""), label_img),
                lathe_bm(profile, uv=[v_lo, v_lo, v_hi, v_hi], cap_top=False))
    return root


def export_glb(root, path):
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    for child in root.children_recursive:
        child.select_set(True)
    bpy.context.view_layer.objects.active = root
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
        export_animations=False, export_extras=True, export_texcoords=True, export_image_format="JPEG",
        export_jpeg_quality=88, export_cameras=False, export_lights=False)


def join_by_material(root):
    """LOD1: merge parts that share a material, so the can is one draw call per material."""
    groups = {}
    for obj in list(root.children):
        groups.setdefault(obj.data.materials[0].name, []).append(obj)
    for name, objs in groups.items():
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objs:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1:
            bpy.ops.object.join()
        bpy.context.view_layer.objects.active.name = "LOD1_" + name.replace(" ", "_")


def discard(root):
    for obj in [*root.children_recursive, root]:
        data = obj.data
        bpy.data.objects.remove(obj)
        if data and data.users == 0:
            bpy.data.meshes.remove(data)


def save_jpeg(strip, path, name, scene):
    h, w, _ = strip.shape
    rgba = np.concatenate([strip, np.ones((h, w, 1), np.float32)], axis=2)
    img = bpy.data.images.new(name + "-raw", w, h)
    img.pixels = rgba.ravel()
    img.filepath_raw = str(path)
    img.file_format = "JPEG"
    scene.render.image_settings.quality = 88
    img.save()
    bpy.data.images.remove(img)
    packed = bpy.data.images.load(str(path))
    packed.name = name
    packed.pack()
    return packed


def main():
    opts = args()
    packshots = Path(opts.packshots)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    # Partly metallic: fully metallic surfaces render black in viewers that have no environment map.
    tinplate = solid_material("Gold lacquered seam", (190, 150, 68), metallic=0.45, roughness=0.34)
    lid_metal = solid_material("Lid satin tinplate", (196, 196, 192), metallic=0.4, roughness=0.36)
    steel = solid_material("Can steel", (176, 180, 186), metallic=0.3, roughness=0.5)

    tex_dir = HERE / "textures"
    tex_dir.mkdir(parents=True, exist_ok=True)
    reports = {"inputs": {}, "cans": {}}
    cans = []
    for spec in VARIANTS:
        for kind in ("front", "back"):
            data = (packshots / spec[kind]).read_bytes()
            reports["inputs"][spec[kind]] = hashlib.sha256(data).hexdigest()
        fpx, bpx = load_pixels(packshots / spec["front"]), load_pixels(packshots / spec["back"])
        fb, bb = can_bounds(fpx), can_bounds(bpx)
        fpx, bpx = delight(fpx, fb), delight(bpx, bb)
        width = fb[1] - fb[0]
        height = DIAMETER * (fb[3] - fb[2]) / width
        label_h = height - 2 * SEAM
        tex_h = int(min(TEX_W * label_h / (math.pi * DIAMETER), TEX_H_MAX)) // 2 * 2
        strip = sharpen(unroll_label(fpx, bpx, fb, bb, tex_h))
        # LOD1 (shelf display): half-resolution texture, coarse lathes, no hidden body, one mesh per material.
        small = strip.reshape(tex_h // 2, 2, TEX_W // 2, 2, 3).mean(axis=(1, 3))
        (tex_dir / "lod1").mkdir(exist_ok=True)
        lod1_img = save_jpeg(small, tex_dir / "lod1" / f"{spec['slug']}-label-lod1.jpg", f"{spec['slug']}-label-lod1", scene)
        SEG["segments"] = LOD1_SEGMENTS
        lod1 = build_can(spec, lod1_img, height, tinplate, lid_metal, steel, lod=1)
        join_by_material(lod1)
        export_glb(lod1, HERE / "exports" / "lod1" / f"{spec['slug']}-lod1.glb")
        discard(lod1)
        for mat in [m for m in bpy.data.materials if m.name.endswith("LOD1")]:
            bpy.data.materials.remove(mat)
        bpy.data.images.remove(lod1_img)
        SEG["segments"] = SEGMENTS
        img = save_jpeg(strip, tex_dir / f"{spec['slug']}-label.jpg", f"{spec['slug']}-label", scene)
        root = build_can(spec, img, height, tinplate, lid_metal, steel)
        export_glb(root, HERE / "exports" / f"{spec['slug']}.glb")
        # Free the plain part names for the next variant; the exported GLB already keeps them unsuffixed.
        for node in root.children_recursive:
            node.name += f"_{spec['key']}"
            node.data.name += f"_{spec['key']}"
        reports["cans"][spec["slug"]] = dict(height_m=round(height, 5), diameter_m=DIAMETER, texture=[TEX_W, tex_h],
                                              front_bounds=fb, back_bounds=bb,
                                              lod1=dict(texture=[TEX_W // 2, tex_h // 2], segments=LOD1_SEGMENTS))
        cans.append((spec, root, height))

    # Source scene: all four cans in a row with a studio rig that is never exported.
    for i, (spec, root, height) in enumerate(cans):
        root.location = ((i - 1.5) * 0.12, 0, 0)
    studio = empty("STUDIO")
    floor_mat = solid_material("Studio cyclorama", (222, 224, 226), roughness=0.92)

    def cyclorama(bm):
        # Floor that sweeps up into a back wall along a quarter-circle, extruded along X.
        profile = [(-0.9, 0.0), (0.18, 0.0)]
        for step in range(1, 13):
            t = step / 12 * math.pi / 2
            profile.append((0.18 + 0.30 * math.sin(t), 0.30 - 0.30 * math.cos(t)))
        profile.append((0.48, 1.4))
        rows = [[bm.verts.new((x, y, z)) for x in (-1.2, 1.2)] for y, z in profile]
        for a_, b_ in zip(rows, rows[1:]):
            bm.faces.new((a_[0], a_[1], b_[1], b_[0]))
    cyc_bm = bmesh.new()
    cyclorama(cyc_bm)
    mesh_object("Cyclorama", studio, floor_mat, cyc_bm)
    world = bpy.data.worlds.new("Studio")
    world.use_nodes = True
    next(n for n in world.node_tree.nodes if n.type == "BACKGROUND").inputs["Color"].default_value = (0.45, 0.46, 0.48, 1)
    scene.world = world
    # Large area lights give soft, contact-grounded shadows; the key sits high at the front left.
    for name, loc, energy, size in (("Key", (-0.45, -0.55, 0.55), 11, 0.7), ("Fill", (0.6, -0.45, 0.25), 5, 1.0),
                                    ("Rim", (0.0, 0.5, 0.45), 7, 0.5)):
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.size = size
        light.data.use_shadow = True
        light.parent = studio
        light.rotation_euler = (Vector((0, 0, 0.05)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.parent = studio
    cam.data.lens = 85
    scene.camera = cam
    scene.render.resolution_x = scene.render.resolution_y = 1000
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "CYCLES"):
        if engine in engines:
            scene.render.engine = engine
            break
    (HERE / "sources").mkdir(exist_ok=True)
    (HERE / "previews").mkdir(exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "sources/gjh-abalone-cans.blend"), compress=True)

    # One preview per can, rendered with that can alone at the origin.
    for spec, root, height in cans:
        for other, other_root, _ in cans:
            for node in (other_root, *other_root.children_recursive):
                node.hide_render = other_root is not root
        saved = root.location.copy()
        root.location = (0, 0, 0)
        # Gallery cards show a centre crop of the top ~79% of the square image, so keep the can in the upper middle.
        cam.location = (0.09, -0.60, height * 0.62)
        cam.rotation_euler = (Vector((0, 0, height * 0.20)) - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(HERE / "previews" / f"{spec['slug']}.png")
        bpy.ops.render.render(write_still=True)
        root.location = saved
    reports["engine"] = scene.render.engine
    reports["blender"] = bpy.app.version_string
    (HERE / "reports").mkdir(exist_ok=True)
    (HERE / "reports/build.json").write_text(json.dumps(reports, indent=2) + "\n")
    print("done", scene.render.engine, bpy.app.version_string)


main()
