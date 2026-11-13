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
TEX_W, TEX_H_MAX = 1280, 640

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


def sample(px, x, y):
    """Bilinear sample of a top-down image at float pixel coordinates."""
    h, w, _ = px.shape
    x = np.clip(x, 0, w - 1.001)
    y = np.clip(y, 0, h - 1.001)
    x0, y0 = x.astype(int), y.astype(int)
    fx, fy = (x - x0)[..., None], (y - y0)[..., None]
    return (px[y0, x0] * (1 - fx) * (1 - fy) + px[y0, x0 + 1] * fx * (1 - fy) +
            px[y0 + 1, x0] * (1 - fx) * fy + px[y0 + 1, x0 + 1] * fx * fy)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def unroll_label(front_px, back_px, fb, bb, tex_h):
    """Unroll front/back packshots into one label strip. u=0.5 is the front centre, u=0/1 the back centre."""
    u = (np.arange(TEX_W) + 0.5) / TEX_W
    phi = (u - 0.5) * 2 * np.pi
    v = (np.arange(tex_h) + 0.5) / tex_h  # 0 bottom .. 1 top
    rim = 0.052  # seam fraction of can height, measured from the packshots
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
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.38
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


def lathe_bm(profile, segments=SEGMENTS, uv=None, cap_top=True):
    """Radial profile [(radius, z)] revolved around Z; phi=0 faces -Y. A zero radius becomes a single pole vertex."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r == 0:
            rings.append(bm.verts.new((0.0, 0.0, z)))
        else:
            rings.append([bm.verts.new((r * math.sin(i * math.tau / segments - math.pi),
                                        -r * math.cos(i * math.tau / segments - math.pi), z)) for i in range(segments)])
    layer = bm.loops.layers.uv.new("UVMap") if uv else None
    for j in range(len(profile) - 1):
        for i in range(segments):
            k = (i + 1) % segments
            a, b = rings[j], rings[j + 1]
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


def build_can(spec, label_img, height, tinplate, lid_metal, steel):
    r = DIAMETER / 2
    root = empty(spec["root"])
    seam = 0.0045
    body_top = height - seam
    # Body shell under the label (never visible except at the seams).
    mesh_object("CanBody", root, steel, lathe_bm([(0.0, seam * 0.5), (r, seam * 0.5), (r, body_top)]))
    # Double-seam rings at both ends, slightly proud of the body.
    for name, z0, z1 in (("BottomSeam", 0.0, seam * 1.9), ("TopSeam", height - seam * 1.9, height)):
        profile = [(0.0, z0), (r + 0.0012, z0), (r + 0.0016, (z0 + z1) / 2), (r + 0.0012, z1), (r - 0.0006, z1)]
        mesh_object(name, root, tinplate, lathe_bm(profile, cap_top=False))
    # Recessed lid with stepped panel and a ring-pull.
    lid_top = height - 0.0014
    mesh_object("Lid", root, lid_metal, lathe_bm([(0.0, lid_top - 0.0016), (r * 0.82, lid_top - 0.0016),
                                                  (r * 0.88, lid_top), (r - 0.0008, lid_top), (r - 0.0008, lid_top - 0.0004),
                                                  (0.0, lid_top - 0.0004)]))
    mesh_object("PullTabPlate", root, lid_metal, box_bm((0.022, 0.012, 0.0012), (0.0, 0.016, lid_top + 0.0006), 0.0003))
    ring = lathe_bm([(0.0, 0.0), (0.0090, 0.0), (0.0090, 0.0012), (0.0, 0.0012)], segments=32)
    ring_obj = mesh_object("PullTabRing", root, lid_metal, ring)
    ring_obj.location = (0.0, -0.010, lid_top + 0.0013)
    ring_obj.scale = (1.0, 1.35, 1.0)
    # Label shell: rises from the bottom seam to the top seam, mapped to the unrolled packshot texture.
    z0, z1 = seam * 1.9 - 0.0004, height - seam * 1.9 + 0.0004
    profile = [(r - 0.0002, z0), (r + 0.0006, z0), (r + 0.0006, z1), (r - 0.0002, z1)]
    mesh_object("Label", root, label_material(f"Label {spec['name']}", label_img),
                lathe_bm(profile, uv=[0.0, 0.0, 1.0, 1.0], cap_top=False))
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


def main():
    opts = args()
    packshots = Path(opts.packshots)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    # Partly metallic: fully metallic surfaces render black in viewers that have no environment map.
    tinplate = solid_material("Tinplate gold seam", (222, 196, 128), metallic=0.3, roughness=0.42)
    lid_metal = solid_material("Lid satin tinplate", (218, 212, 196), metallic=0.25, roughness=0.4)
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
        width = fb[1] - fb[0]
        height = DIAMETER * (fb[3] - fb[2]) / width
        label_h = height * (1 - 2 * 0.052)
        tex_h = int(min(TEX_W * label_h / (math.pi * DIAMETER), TEX_H_MAX)) // 2 * 2
        strip = unroll_label(fpx, bpx, fb, bb, tex_h)
        rgba = np.concatenate([strip, np.ones((tex_h, TEX_W, 1), np.float32)], axis=2)
        img = bpy.data.images.new(f"{spec['slug']}-label", TEX_W, tex_h)
        img.pixels = rgba.ravel()
        img.filepath_raw = str(tex_dir / f"{spec['slug']}-label.jpg")
        img.file_format = "JPEG"
        scene.render.image_settings.quality = 88
        img.save()
        img = bpy.data.images.load(str(tex_dir / f"{spec['slug']}-label.jpg"))
        img.name = f"{spec['slug']}-label"
        img.pack()
        root = build_can(spec, img, height, tinplate, lid_metal, steel)
        export_glb(root, HERE / "exports" / f"{spec['slug']}.glb")
        # Free the plain part names for the next variant; the exported GLB already keeps them unsuffixed.
        for node in root.children_recursive:
            node.name += f"_{spec['key']}"
            node.data.name += f"_{spec['key']}"
        reports["cans"][spec["slug"]] = dict(height_m=round(height, 5), diameter_m=DIAMETER, texture=[TEX_W, tex_h],
                                              front_bounds=fb, back_bounds=bb)
        cans.append((spec, root, height))

    # Source scene: all four cans in a row with a studio rig that is never exported.
    for i, (spec, root, height) in enumerate(cans):
        root.location = ((i - 1.5) * 0.12, 0, 0)
    studio = empty("STUDIO")
    floor_mat = solid_material("Studio floor", (226, 228, 230), roughness=0.85)
    fm = bmesh.new()
    bmesh.ops.create_cube(fm, size=1.0)
    for v in fm.verts:
        v.co = (v.co.x * 3, v.co.y * 3, v.co.z * 0.02 - 0.01)
    mesh_object("Floor", studio, floor_mat, fm, smooth=False)
    world = bpy.data.worlds.new("Studio")
    world.use_nodes = True
    next(n for n in world.node_tree.nodes if n.type == "BACKGROUND").inputs["Color"].default_value = (0.5, 0.51, 0.53, 1)
    scene.world = world
    for name, loc, energy in (("Key", (0.5, -0.7, 0.7), 12), ("Fill", (-0.6, -0.5, 0.4), 5), ("Rim", (0.0, 0.6, 0.5), 6)):
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.size = 0.5
        light.parent = studio
        light.rotation_euler = (Vector((0, 0, 0.06)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.parent = studio
    cam.data.lens = 85
    scene.camera = cam
    scene.render.resolution_x = scene.render.resolution_y = 800
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
        cam.location = (0.11, -0.42, height * 0.66)
        cam.rotation_euler = (Vector((0, 0, height * 0.5)) - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(HERE / "previews" / f"{spec['slug']}.png")
        bpy.ops.render.render(write_still=True)
        root.location = saved
    reports["engine"] = scene.render.engine
    reports["blender"] = bpy.app.version_string
    (HERE / "reports").mkdir(exist_ok=True)
    (HERE / "reports/build.json").write_text(json.dumps(reports, indent=2) + "\n")
    print("done", scene.render.engine, bpy.app.version_string)


main()
