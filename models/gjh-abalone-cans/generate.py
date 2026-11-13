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
SEGMENTS = 64
TEX_W, TEX_H_MAX = 1280, 640  # about 1.15x the packshot's real detail; more would only enlarge blur
LOD1_SEGMENTS, LOD1_TEX_W = 36, 640
SEG = {"segments": SEGMENTS}
SEAM = 0.0050  # double-seam height in metres
# Label rows measured on all 11 official packshots (same framing): the printed label runs from the first row below the
# top seam to the last row above the bottom seam. Values are row boundaries in the 1000 px packshot.
LABEL_TOP_ROW, LABEL_BOTTOM_ROW = 313.0, 848.0
LABEL_RADIUS = DIAMETER / 2 + 0.0003  # outer radius of the label surface, metres (the packshot silhouette is the label)

VARIANTS = [
    dict(key="nz", slug="gjh-can-new-zealand-abalone", name="New Zealand Abalone", zh="新西兰鲍鱼罐头",
         origin="New Zealand", pack="425g", root="ASSET_GJHCanNewZealandAbalone",
         front="new-moon-nz-425g-front.jpg", back="new-moon-nz-425g-back.jpg",
         nutrition="new-moon-nz-425g-nutrition.jpg"),
    dict(key="au", slug="gjh-can-australia-abalone", name="Australia Abalone", zh="澳洲鲍鱼罐头",
         origin="Australia", pack="425g", root="ASSET_GJHCanAustraliaAbalone",
         front="new-moon-au-425g-front.jpg", back="new-moon-au-425g-back.jpg",
         nutrition="new-moon-au-425g-nutrition.jpg"),
    dict(key="sa", slug="gjh-can-south-africa-abalone", name="South Africa Abalone", zh="南非鲍鱼罐头",
         origin="South Africa", pack="425g", root="ASSET_GJHCanSouthAfricaAbalone",
         front="new-moon-sa-425g-front.jpg", back="new-moon-sa-425g-back.jpg",
         nutrition="new-moon-sa-425g-nutrition.jpg"),
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


def body_extent(px, bounds):
    """Left and right silhouette of the can body at mid-height (excludes the wider seam beads)."""
    x0, x1, y0, y1 = bounds
    height = y1 - y0
    lefts, rights = [], []
    for y in range(int(y0 + 0.3 * height), int(y0 + 0.7 * height), 6):
        ink = np.where(px[y, :].min(axis=1) < 0.86)[0]
        ink = ink[(ink > x0 - 5) & (ink < x1 + 5)]
        if len(ink) > 50:
            lefts.append(ink.min())
            rights.append(ink.max())
    return float(np.median(lefts)), float(np.median(rights))


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
    top, bottom = int(LABEL_TOP_ROW), int(LABEL_BOTTOM_ROW)
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


PANEL_LIMIT = 74.0       # degrees from a packshot's centre beyond which limb distortion and edge glare dominate
EDGE_RANGE = range(44, 73)  # candidate seam positions, degrees from a panel's centre
PROFILE_BINS = 32


# Circular badges that the packshot retouching pasted on flat (not foreshortened by the cylinder): (x0, x1, y0, y1) in packshot
# pixels, measured on the enlarged official photos. Unrolling treats every pixel as foreshortened, which would stretch these
# badges about 1.4 to 1.7 times too wide when viewed face-on. Printed logos (halal, ASME, the SA seal) measure 1.00 to 1.04 and
# need no fix. A fix only remaps columns inside the badge's rows; it never redraws anything.
OVERLAY_BADGES = {
    "au": {"front": (600.5, 667.0, 646.0, 719.0)},
    "nz": {"front": (584.4, 653.6, 657.0, 727.6)},
    "mx": {"front": (598.0, 670.0, 646.0, 720.0)},
}
BADGE_MARGIN_PX = 30.0   # source pixels on the left of the badge over which the freed angle is absorbed
BADGE_ROW_PAD, BADGE_ROW_RAMP = 4.0, 8.0


class Panel:
    """One packshot treated as a cylinder panel centred on its own axis angle."""

    def __init__(self, name, px, bounds, badge=None):
        self.name, self.px, self.bounds = name, px, bounds
        left, right = body_extent(px, bounds)
        self.cx, self.r = (left + right) / 2, (right - left) / 2
        self.top, self.bottom = LABEL_TOP_ROW, LABEL_BOTTOM_ROW
        self.badge, self.warp, self.right_limit = badge, None, 999.0
        if badge:
            bx0, bx1, by0, by1 = badge
            phi_c = math.degrees(math.asin(((bx0 + bx1) / 2 - self.cx) / self.r))
            delta = math.degrees((by1 - by0) / self.r)        # round badge: arc width equals its height
            phi_b0, phi_b1 = phi_c - delta / 2, phi_c + delta / 2
            wx0 = bx0 - BADGE_MARGIN_PX
            asin_deg = lambda x: math.degrees(math.asin(min((x - self.cx) / self.r, 0.999)))
            x_limit = self.cx + self.r * math.sin(math.radians(PANEL_LIMIT))
            room = x_limit - bx1                     # real background pixels to the right of the badge, before the limb
            wx1 = bx1 + min(BADGE_MARGIN_PX, room) if room >= 8.0 else bx1 + 3.0
            self.warp = dict(phi=[asin_deg(wx0), phi_b0, phi_b1, max(asin_deg(wx1), phi_b1 + 3.0)],
                             x=[wx0, bx0, bx1, wx1], rows=(by0, by1), phi_c=phi_c, delta=delta)
            # With no real background right of the badge the panel must end just after it; otherwise other artwork
            # (such as the Chinese origin box) may continue to the limb and the seam stays free.
            self.right_limit = phi_b1 + 1.5 if room < 8.0 else 999.0

    def x_of(self, deg):
        """Source column for a local angle, with the flat-badge remap where it applies (vectorised, degrees)."""
        deg = np.asarray(deg, dtype=np.float64)
        x = self.cx + self.r * np.sin(np.radians(deg))
        if self.warp:
            phi, xs = self.warp["phi"], self.warp["x"]
            inside = (deg >= phi[0]) & (deg <= phi[3])
            x = np.where(inside, np.interp(deg, phi, xs), x)
        return x

    def columns(self, deg):
        return float(self.x_of(deg))

    def profile(self, deg):
        """Mean colour of PROFILE_BINS row bands at a given local angle (5 px wide strip)."""
        x = int(round(self.columns(deg)))
        band = self.px[int(self.top):int(self.bottom), x - 2:x + 3].mean(axis=1)
        return np.array([b.mean(axis=0) for b in np.array_split(band, PROFILE_BINS)])

    def energy(self, deg):
        """How busy the artwork is at a local angle: low means plain colour, a safe place for a seam."""
        x = int(round(self.columns(deg)))
        a = self.px[int(self.top):int(self.bottom), x - 3]
        b = self.px[int(self.top):int(self.bottom), x + 3]
        return float(np.abs(a - b).mean())

    def sample_columns(self, local_deg, v):
        """Bicubic colours for local angles (columns) and label heights v in 0 bottom .. 1 top."""
        local = np.clip(local_deg, -PANEL_LIMIT, PANEL_LIMIT)
        xs = self.cx + self.r * np.sin(np.radians(local))
        ys = self.bottom - v * (self.bottom - self.top)
        X, Y = np.meshgrid(xs, ys)
        if self.warp:
            by0, by1 = self.warp["rows"]
            weight = (smoothstep(by0 - BADGE_ROW_PAD - BADGE_ROW_RAMP, by0 - BADGE_ROW_PAD, ys) *
                      (1 - smoothstep(by1 + BADGE_ROW_PAD, by1 + BADGE_ROW_PAD + BADGE_ROW_RAMP, ys)))
            X = X + weight[:, None] * (self.x_of(local)[None, :] - xs[None, :])
        return sample(self.px, X, Y)


def seam_cost(a, b, deg_a, deg_b):
    """Mismatch between panel a's right edge and panel b's left edge, plus how busy both artworks are there."""
    diff = float(((a.profile(deg_a) - b.profile(deg_b)) ** 2).mean())
    return 4.0 * diff + a.energy(deg_a) + b.energy(deg_b)


def junction_table(a, b):
    """Best (cost, R, L) for every integer spacing R - L between a's right edge and b's left edge."""
    table = {}
    for right in (d for d in EDGE_RANGE if d <= a.right_limit):
        for left in (-d for d in EDGE_RANGE):
            cost = seam_cost(a, b, right, left)
            spacing = right - left
            if spacing not in table or cost < table[spacing][0]:
                table[spacing] = (cost, right, left)
    return table


def order_costs(panels):
    """Best seam cost of each cyclic order of three panels (front, back, nutrition) -> {order names: cost}."""
    result = {}
    for order in ((0, 1, 2), (0, 2, 1)):
        tables = [junction_table(panels[order[k]], panels[order[(k + 1) % 3]]) for k in range(3)]
        costs = [t1[0] + t2[0] + tables[2][360 - s1 - s2][0] for s1, t1 in tables[0].items() for s2, t2 in tables[1].items()
                 if 360 - s1 - s2 in tables[2]]
        result[tuple(panels[i].name for i in order)] = min(costs)
    return result


def plan_layout(panels, forced_order=None, forced_side=None):
    """Arrange panels around the can. Returns {'order', 'centres', 'intervals', 'gap', 'cost'}.

    Three panels must close the circle exactly (spacings sum to 360 degrees); the order and seam positions are the
    ones with the smallest colour/artwork mismatch at the seams. With two panels the rest of the circle is a gap that
    is left unprinted (no official image exists for it)."""
    names = [p.name for p in panels]
    if len(panels) == 3:
        best = None
        for order in ((0, 1, 2), (0, 2, 1)):
            if forced_order and tuple(names[i] for i in order) != tuple(forced_order):
                continue
            tables = [junction_table(panels[order[k]], panels[order[(k + 1) % 3]]) for k in range(3)]
            for s1, t1 in tables[0].items():
                for s2, t2 in tables[1].items():
                    s3 = 360 - s1 - s2
                    if s3 in tables[2]:
                        cost = t1[0] + t2[0] + tables[2][s3][0]
                        if best is None or cost < best[0]:
                            best = (cost, order, (t1, t2, tables[2][s3]), (s1, s2, s3))
        cost, order, joins, spacings = best
        centres, intervals = {}, {}
        acc = 0.0
        for k, idx in enumerate(order):
            centres[idx] = acc
            acc += spacings[k]
            prev_left = joins[(k - 1) % 3][2]
            intervals[idx] = (prev_left, joins[k][1])
        return dict(order=[names[i] for i in order], centres={names[i]: centres[i] for i in centres},
                    intervals={names[i]: intervals[i] for i in intervals}, gap=None, cost=round(cost, 4),
                    spacings=list(spacings))
    front, other = panels
    best = None
    for side in ((+1, -1) if forced_side is None else (forced_side,)):
        a, b = (front, other) if side > 0 else (other, front)  # a's right edge meets b's left edge
        table = junction_table(a, b)
        for spacing, (cost, right, left) in table.items():
            outer_a = min(EDGE_RANGE, key=lambda d: a.energy(-d))      # a's free (left) edge
            outer_b = min(EDGE_RANGE, key=lambda d: b.energy(d))       # b's free (right) edge
            if best is None or cost < best[0]:
                best = (cost, side, spacing, right, left, outer_a, outer_b)
    cost, side, spacing, right, left, outer_a, outer_b = best
    if side > 0:  # front at 0, other to its right
        centre_other = float(spacing)
        intervals = {front.name: (-float(outer_a), float(right)), other.name: (float(left), float(outer_b))}
        centres = {front.name: 0.0, other.name: centre_other}
        gap = (centre_other + outer_b, 360.0 - outer_a)
    else:         # other to the left of front
        centre_other = -float(spacing)
        intervals = {other.name: (-float(outer_a), float(right)), front.name: (float(left), float(outer_b))}
        centres = {front.name: 0.0, other.name: centre_other}
        gap = (outer_b, 360.0 + centre_other - outer_a)
    free = {front.name: 'left' if side > 0 else 'right', other.name: 'right' if side > 0 else 'left'}
    return dict(order=[front.name, other.name], centres=centres, intervals=intervals, gap=gap, cost=round(cost, 4),
                spacings=[spacing], free_edges=free)


def field_colour(panel, degrees, v):
    """Per-row median colour over several columns: removes thin lines, text and badges, keeping the base colour."""
    return np.median(panel.sample_columns(np.array(degrees, dtype=np.float64), v), axis=1)


def unroll_panels(panels, layout, tex_h):
    """Unroll the packshots into one label strip. u=0.5 is the front centre (absolute angle 0 at the front)."""
    u = (np.arange(TEX_W) + 0.5) / TEX_W
    absolute = (u - 0.5) * 360.0
    v = (np.arange(tex_h) + 0.5) / tex_h  # 0 bottom .. 1 top
    free = layout.get("free_edges", {})
    total = np.zeros(TEX_W, dtype=np.float32)
    acc = np.zeros((tex_h, TEX_W, 3), dtype=np.float32)
    for panel in panels:
        centre, (left, right) = layout["centres"][panel.name], layout["intervals"][panel.name]
        local = (absolute - centre + 180.0) % 360.0 - 180.0
        f_left = 6.0 if free.get(panel.name) == "left" else 2.0
        f_right = 6.0 if free.get(panel.name) == "right" else 2.0
        weight = (smoothstep(left - f_left / 2, left + f_left / 2, local) *
                  (1 - smoothstep(right - f_right / 2, right + f_right / 2, local))).astype(np.float32)
        acc += panel.sample_columns(local, v) * weight[None, :, None]
        total += weight
    out = acc / np.maximum(total, 1e-6)[None, :, None]
    if layout["gap"] is not None:
        # No official image covers this part of the circle. It is left as an unprinted placeholder: two flat base colours
        # (upper field and lower band) taken from the front panel, with no artwork, text or marks invented.
        front = panels[0]
        med = gaussian_1d(field_colour(front, np.linspace(-60, 60, 60), v), 3.0, 0)
        change = np.abs(np.diff(med, axis=0)).sum(axis=1)
        lo, hi = int(0.2 * tex_h), int(0.75 * tex_h)
        boundary = lo + int(np.argmax(change[lo:hi]))
        lower = np.median(med[:max(boundary - 6, 1)], axis=0)
        upper = np.median(med[boundary + 6:], axis=0)
        step = smoothstep(boundary - 3.0, boundary + 3.0, np.arange(tex_h).astype(np.float64))[:, None]
        fill = (lower[None, :] * (1 - step) + upper[None, :] * step)[:, None, :]
        fill = np.broadcast_to(fill, (tex_h, TEX_W, 3))
        gap_mask = np.clip(1.0 - total, 0.0, 1.0)[None, :, None]
        out = out * (1 - gap_mask) + fill * gap_mask
    return out


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
    bsdf.inputs["Metallic"].default_value = 0.2  # lacquered print on tin: glossy, with a soft highlight band
    bsdf.inputs["Roughness"].default_value = 0.3  # printed lacquer: soft, no hot streaks
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


def build_can(spec, label_img, height, gold, silver, lod=0):
    """Reusable can geometry. Parts are separate objects (editable in the .blend); exports merge them per material."""
    r = DIAMETER / 2
    root = empty(spec["root"])
    # Body shell under the label (visible only through the seams).
    if lod == 0:
        mesh_object("CanBody", root, silver, lathe_bm([(0.0, SEAM * 0.5), (r, SEAM * 0.5), (r, height - SEAM * 0.5)], cap_top=False))
    # Rolled double seams: a rounded bead that bulges slightly past the body, with a chamfered outer lip.
    bead = r + 0.0020
    bottom = [(r - 0.0030, 0.0), (r + 0.0006, 0.0), (r + 0.0016, SEAM * 0.22), (bead, SEAM * 0.55),
              (r + 0.0016, SEAM * 0.9), (r + 0.0004, SEAM)]
    mesh_object("BottomSeam", root, gold, lathe_bm(bottom, cap_top=False))
    top = [(r + 0.0004, height - SEAM), (r + 0.0016, height - SEAM * 0.9), (bead, height - SEAM * 0.55),
           (r + 0.0016, height - SEAM * 0.22), (r + 0.0006, height), (r - 0.0030, height)]
    mesh_object("TopSeam", root, gold, lathe_bm(top, cap_top=False))
    # Lid: raised rim, recessed panel, two pressed rings.
    lid = height - 0.0004
    panel = lid - 0.0024
    mesh_object("Lid", root, silver, lathe_bm([
        (0.0, panel), (r * 0.50, panel), (r * 0.54, panel + 0.0011), (r * 0.60, panel), (r * 0.78, panel),
        (r * 0.84, panel + 0.0015), (r - 0.0034, lid - 0.0006), (r - 0.0030, lid), (r - 0.0030, lid - 0.0008),
        (r - 0.0050, lid - 0.0008), (0.0, lid - 0.0008)]))
    # Opening score: a thin raised oval contour on the panel.
    score = lathe_bm([(0.0140, 0.0), (0.0147, 0.0), (0.0147, 0.00045), (0.0140, 0.00045)], segments=40, closed=True)
    score_obj = mesh_object("OpeningScore", root, silver, score)
    score_obj.scale = (1.0, 0.72, 1.0)
    score_obj.location = (0.0, 0.002, panel)
    # Pull tab: ring, neck plate and rivet are independent parts.
    mesh_object("PullTabPlate", root, silver, box_bm((0.011, 0.020, 0.0009), (0.0, -0.0045, panel + 0.0009), 0.0003))
    rivet = lathe_bm([(0.0, 0.0), (0.0024, 0.0), (0.0024, 0.0016), (0.0017, 0.0019), (0.0, 0.0019)], segments=24)
    rivet_obj = mesh_object("PullTabRivet", root, silver, rivet)
    rivet_obj.location = (0.0, 0.004, panel + 0.0013)
    ring = lathe_bm([(0.0050, 0.0), (0.0090, 0.0), (0.0090, 0.0016), (0.0050, 0.0016)], segments=40, closed=True)
    ring_obj = mesh_object("PullTabRing", root, silver, ring)
    ring_obj.scale = (0.9, 1.25, 1.0)
    ring_obj.location = (0.0, -0.0235, panel + 0.0013)
    # Base: standing ring, recessed base and central panel, so the underside is not an open hole or a flat disc.
    mesh_object("Base", root, silver, lathe_bm([
        (r - 0.0030, 0.0), (r - 0.0042, 0.0), (r - 0.0050, 0.0004), (r - 0.0075, 0.0016), (r * 0.78, 0.0020),
        (r * 0.74, 0.0030), (r * 0.46, 0.0030), (r * 0.42, 0.0022), (0.0, 0.0022)]))
    # Label: printed tin that continues under both seams, so there is no sticker edge.
    z0, z1 = SEAM * 0.6, height - SEAM * 0.6
    span = height - 2 * SEAM
    v_lo, v_hi = (z0 - SEAM) / span, (z1 - SEAM) / span
    profile = [(r - 0.0004, z0), (r + 0.0003, z0), (r + 0.0003, z1), (r - 0.0004, z1)]
    mesh_object("Label", root, label_material(f"Label {spec['name']}" + (" LOD1" if lod else ""), label_img),
                lathe_bm(profile, uv=[v_lo, v_lo, v_hi, v_hi], cap_top=False))
    return root


NODE_NAMES = {"Gold lacquered rim": "GoldRim", "Silver tinplate": "SilverMetal"}


def merged_copy(root, name):
    """Copy a can with parts merged per material (one draw call per material) for export, leaving the source parts intact."""
    clone = empty(name)
    for obj in root.children:
        dup = obj.copy()
        dup.data = obj.data.copy()
        dup.parent = clone
        bpy.context.scene.collection.objects.link(dup)
    # Bake each part's own transform into its mesh so joining keeps positions.
    bpy.ops.object.select_all(action="DESELECT")
    for dup in clone.children:
        dup.select_set(True)
    bpy.context.view_layer.objects.active = clone.children[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    groups = {}
    for dup in list(clone.children):
        groups.setdefault(dup.data.materials[0].name, []).append(dup)
    for name, objs in groups.items():
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objs:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1:
            bpy.ops.object.join()
        bpy.context.view_layer.objects.active.name = NODE_NAMES.get(name, "Label")
    return clone


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

    # Three materials in total (label, gold rim, silver metal) keep the can at three draw calls.
    gold = solid_material("Gold lacquered rim", (214, 170, 84), metallic=0.9, roughness=0.28)
    silver = solid_material("Silver tinplate", (206, 206, 202), metallic=0.9, roughness=0.34)

    tex_dir = HERE / "textures"
    tex_dir.mkdir(parents=True, exist_ok=True)
    reports = {"inputs": {}, "cans": {}}
    cans = []
    # Pass 1: load every packshot and choose one panel order shared by all three-panel SKUs (they share one design).
    loaded = {}
    for spec in VARIANTS:
        panels = []
        for kind in ("front", "back", "nutrition"):
            if kind not in spec:
                continue
            reports["inputs"][spec[kind]] = hashlib.sha256((packshots / spec[kind]).read_bytes()).hexdigest()
            raw = load_pixels(packshots / spec[kind])
            bounds = can_bounds(raw)
            panels.append(Panel(kind, delight(raw, bounds), bounds, OVERLAY_BADGES.get(spec["key"], {}).get(kind)))
        loaded[spec["key"]] = panels
    totals = {}
    reports["order_costs"] = {}
    for spec in VARIANTS:
        if len(loaded[spec["key"]]) == 3:
            costs = order_costs(loaded[spec["key"]])
            reports["order_costs"][spec["key"]] = {"/".join(k): round(v, 4) for k, v in costs.items()}
            for order, cost in costs.items():
                totals[order] = totals.get(order, 0.0) + cost
    common = min(totals, key=totals.get)
    reports["common_order"] = list(common)
    side_of_nutrition = +1 if common.index("nutrition") == 1 else -1
    for spec in VARIANTS:
        panels = loaded[spec["key"]]
        fb = panels[0].bounds
        layout = (plan_layout(panels, forced_order=common) if len(panels) == 3
                  else plan_layout(panels, forced_side=side_of_nutrition))
        # Scale from the packshot's body silhouette (which is the label surface); the label height follows from its measured rows.
        px_per_m = panels[0].r / LABEL_RADIUS
        label_h = (LABEL_BOTTOM_ROW - LABEL_TOP_ROW) / px_per_m
        height = label_h + 2 * SEAM
        tex_h = int(min(TEX_W * label_h / (2 * math.pi * LABEL_RADIUS), TEX_H_MAX)) // 2 * 2
        strip = sharpen(unroll_panels(panels, layout, tex_h))
        # LOD1 (shelf display): half-resolution texture, coarse lathes, no hidden body, one mesh per material.
        small = strip.reshape(tex_h // 2, 2, TEX_W // 2, 2, 3).mean(axis=(1, 3))
        (tex_dir / "lod1").mkdir(exist_ok=True)
        lod1_img = save_jpeg(small, tex_dir / "lod1" / f"{spec['slug']}-label-lod1.jpg", f"{spec['slug']}-label-lod1", scene)
        SEG["segments"] = LOD1_SEGMENTS
        lod1 = build_can(spec, lod1_img, height, gold, silver, lod=1)
        lod1.name = spec["root"] + "_parts"
        for node in lod1.children:
            node.name += "_lod1"
        clone = merged_copy(lod1, spec["root"])
        export_glb(clone, HERE / "exports" / "lod1" / f"{spec['slug']}-lod1.glb")
        discard(clone)
        discard(lod1)
        for mat in [m for m in bpy.data.materials if m.name.endswith("LOD1")]:
            bpy.data.materials.remove(mat)
        bpy.data.images.remove(lod1_img)
        SEG["segments"] = SEGMENTS
        img = save_jpeg(strip, tex_dir / f"{spec['slug']}-label.jpg", f"{spec['slug']}-label", scene)
        root = build_can(spec, img, height, gold, silver)
        root.name = spec["root"] + "_parts"
        for node in root.children:  # keep source part names unique per variant so the export can use plain names
            node.name += f"_{spec['key']}"
            node.data.name += f"_{spec['key']}"
        clone = merged_copy(root, spec["root"])
        export_glb(clone, HERE / "exports" / f"{spec['slug']}.glb")
        discard(clone)
        root.name = spec["root"]
        reports["cans"][spec["slug"]] = dict(height_m=round(height, 5), diameter_m=DIAMETER, texture=[TEX_W, tex_h],
                                              front_bounds=fb, layout=layout,
                                              panels={p.name: spec[p.name] for p in panels},
                                              badge_fixes={p.name: {k: (v if not isinstance(v, list) else [round(x, 2) for x in v]) for k, v in p.warp.items() if k != 'rows'} for p in panels if p.warp},
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
    # QA renders: 24 turntable views (every 15 degrees) and six standard views per can, as contact sheets.
    qa_dir = HERE / "reports" / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    cyclorama = next(o for o in studio.children if o.name == "Cyclorama")
    tmp = str(qa_dir / "_tile.png")

    def render_tile(size):
        scene.render.resolution_x = scene.render.resolution_y = size
        scene.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        tile = bpy.data.images.load(tmp)
        arr = np.array(tile.pixels[:], dtype=np.float32).reshape(size, size, 4)[:, :, :3]
        bpy.data.images.remove(tile)
        return arr

    def sheet(tiles, columns, size):
        rows = (len(tiles) + columns - 1) // columns
        big = np.ones((rows * size, columns * size, 3), dtype=np.float32)
        for index, tile in enumerate(tiles):
            r, c = divmod(index, columns)
            y0 = (rows - 1 - r) * size  # Blender pixel rows run bottom-up
            big[y0:y0 + size, c * size:(c + 1) * size] = tile
        return big

    for spec, root, height in cans:
        for other, other_root, _ in cans:
            for node in (other_root, *other_root.children_recursive):
                node.hide_render = other_root is not root
        root.location = (0, 0, 0)
        cam.data.lens = 85
        views = []
        for degrees in range(0, 360, 15):
            root.rotation_euler = (0, 0, math.radians(degrees))
            cam.location = (0.0, -0.40, height * 0.55)
            cam.rotation_euler = (Vector((0, 0, height * 0.47)) - cam.location).to_track_quat("-Z", "Y").to_euler()
            views.append(render_tile(320))
        save_jpeg(sheet(views, 6, 320), qa_dir / f"{spec['slug']}-turntable-24.jpg", f"{spec['slug']}-turntable", scene)
        bpy.data.images.remove(bpy.data.images[f"{spec['slug']}-turntable"])
        six = []
        for name, yaw, cam_pos, target_z, hide_floor in (
                ("front", 0, (0.0, -0.40, height * 0.55), height * 0.47, False),
                ("back", 180, (0.0, -0.40, height * 0.55), height * 0.47, False),
                ("left", 90, (0.0, -0.40, height * 0.55), height * 0.47, False),
                ("right", -90, (0.0, -0.40, height * 0.55), height * 0.47, False),
                ("top", 0, (0.0, -0.20, height + 0.40), height, False),
                ("bottom", 0, (0.0, -0.20, -0.40), 0.0, True)):
            root.rotation_euler = (0, 0, math.radians(yaw))
            root.location = (0, 0, 0.0)
            cyclorama.hide_render = hide_floor
            cam.location = cam_pos
            cam.rotation_euler = (Vector((0, 0, target_z)) - cam.location).to_track_quat("-Z", "Y").to_euler()
            six.append(render_tile(400))
        cyclorama.hide_render = False
        save_jpeg(sheet(six, 3, 400), qa_dir / f"{spec['slug']}-six-views.jpg", f"{spec['slug']}-six", scene)
        bpy.data.images.remove(bpy.data.images[f"{spec['slug']}-six"])
        root.rotation_euler = (0, 0, 0)
    Path(tmp).unlink(missing_ok=True)
    reports["engine"] = scene.render.engine
    reports["blender"] = bpy.app.version_string
    (HERE / "reports").mkdir(exist_ok=True)
    (HERE / "reports/build.json").write_text(json.dumps(reports, indent=2) + "\n")
    print("done", scene.render.engine, bpy.app.version_string)


main()
