"""Author a standalone Christmas wreath and export its editable saved source."""

import argparse
from math import cos, pi, sin
from pathlib import Path
from random import Random
import sys

import bpy
from mathutils import Vector

BASE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE))
from geometry import Builder, TAU, colour, local, material, point

SLUG = "christmas-wreath"
ROOT = "ASSET_ChristmasWreath"
SOURCE = BASE / "sources" / (SLUG + ".blend")
RAND = Random(2512)


def collection(name):
    group = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(group)
    return group


def pos(angle, radius, depth):
    return point(radius * cos(angle), radius * sin(angle), depth)


def palette():
    return {
        "vine": material("Coppiced willow bark", (75, 52, 35), 0.83),
        "twig": material("Cinnamon fir stems", (74, 70, 38), 0.83),
        "binding": material("Dark green binding wire", (53, 65, 49), 0.59, 0.27),
        "brass": material("Aged brass hanging wire", (135, 105, 64), 0.36, 0.63),
        "fir": material("Evergreen needle bloom", (69, 106, 83), 0.65, tinted=True),
        "holly": material("Blue-green holly lamina", (33, 80, 58), 0.38),
        "vein": material("Holly midrib", (97, 119, 67), 0.62),
        "fruit": material("Cranberry red fruit skin", (165, 31, 36), 0.28),
        "fruit2": material("Deep garnet fruit skin", (126, 19, 30), 0.34),
        "calyx": material("Dried calyx", (62, 39, 30), 0.79),
        "cone": material("Dark fir-cone core", (74, 43, 29), 0.86),
        "scale": material("Cinnamon cone scales", (118, 77, 46), 0.76),
        "tip": material("Weathered scale edges", (150, 105, 66), 0.80),
        "velvet": material("Crimson velvet ribbon", (148, 17, 39), 0.58, sheen=0.26),
        "edge": material("Warm red woven selvedge", (177, 42, 48), 0.54, sheen=0.24),
        "gold": material("Fine old-gold ribbon stitching", (186, 144, 77), 0.43, 0.27),
        "liner": material("Brick-red ribbon reverse", (109, 16, 32), 0.66, sheen=0.16),
    }


def core(group, root, m):
    wire = Builder()
    for strand in range(5):
        phase = TAU * strand / 5
        pts = []
        for i in range(128):
            a = TAU * i / 128
            r = 0.173 + 0.0090 * cos(8 * a + phase) + 0.004 * sin(3 * a - 0.6) + 0.003 * cos(5 * a)
            depth = 0.023 + 0.0080 * sin(8 * a + phase) + 0.0008 * cos(15 * a + strand)
            pts.append(pos(a, r, depth))
        wire.tube(
            pts,
            [0.0041 + 0.0005 * sin(i * 0.19 + phase) for i in range(len(pts))],
            m["vine"] if strand % 2 == 0 else m["twig"],
            6,
            True,
        )
    wire.make("Five woven willow strands", group, root)
    binding = Builder()
    for i in range(8):
        a = TAU * i / 8 + 0.08
        base = pos(a, 0.174 + 0.004 * sin(3 * a - 0.6) + 0.003 * cos(5 * a), 0.023)
        radial = pos(a, 1, 0)
        pts = [
            base + radial * (0.015 * cos(TAU * j / 32)) + point(0, 0, 0.0145 * sin(TAU * j / 32))
            for j in range(32)
        ]
        binding.tube(pts, [0.00085] * 32, m["binding"], 6, True, reference=pos(a + pi / 2, 1, 0))
    binding.make("Eight floristry wire ties", group, root)
    hanger = Builder()
    # A closed keyhole with two turns of wire lashing the lower bar to the willow.
    pts = [
        point(x, y, 0.0055)
        for x, y in [
            (-0.014, 0.170),
            (0.014, 0.170),
            (0.0155, 0.173),
            (0.015, 0.184),
            (0.012, 0.199),
            (0.009, 0.215),
            (0.007, 0.222),
            (0.004, 0.225),
            (0, 0.226),
            (-0.004, 0.225),
            (-0.007, 0.222),
            (-0.009, 0.215),
            (-0.012, 0.199),
            (-0.015, 0.184),
            (-0.0155, 0.173),
        ]
    ]
    hanger.tube(pts, [0.002] * len(pts), m["brass"], 9, True)
    for x in [-0.009, 0.009]:
        bar = [
            point(x, 0.171 + 0.012 * cos(TAU * j / 32), 0.0185 + 0.015 * sin(TAU * j / 32))
            for j in range(32)
        ]
        hanger.tube(bar, [0.00125] * 32, m["brass"], 7, True, reference=point(1, 0, 0))
    hanger.make("Rear keyhole and twin wire lashings", group, root)


FIR_COLOURS = [(23, 65, 39), (30, 77, 43), (36, 84, 45), (45, 92, 53), (37, 83, 50)]
SILVER_COLOURS = [(49, 90, 68), (57, 102, 83), (47, 92, 72), (68, 108, 88)]
CEDAR_COLOURS = [(89, 112, 65), (81, 109, 73), (94, 119, 74), (74, 102, 62)]


def tint(palette, variation):
    base = RAND.choice(palette)
    return tuple(max(0, min(255, int(channel * variation))) for channel in base)


def fir_spray(b, a, outer, m):
    sweep = RAND.uniform(0.53, 0.75)
    r0 = RAND.uniform(0.151, 0.175) if outer else RAND.uniform(0.163, 0.180)
    r1 = RAND.uniform(0.211, 0.237) if outer else RAND.uniform(0.143, 0.166)
    d0 = RAND.uniform(0.027, 0.038) if outer else RAND.uniform(0.044, 0.055)
    d1 = RAND.uniform(0.054, 0.081) if outer else RAND.uniform(0.077, 0.100)
    wiggle = RAND.uniform(-0.006, 0.006)

    def spine(u):
        return pos(
            a + sweep * u,
            r0 + (r1 - r0) * u + wiggle * sin(pi * u),
            d0 + (d1 - d0) * u + 0.009 * sin(pi * u),
        )

    pts = [spine(j / 10) for j in range(11)]
    b.tube(pts, [0.00165 * (1 - j / 11) + 0.00027 for j in range(11)], m["twig"], 5)
    tones = FIR_COLOURS if outer or RAND.random() < 0.42 else SILVER_COLOURS
    variant = RAND.uniform(0.92, 1.11)
    for j in range(8):
        for side in [-1, 1]:
            u = 0.11 + 0.100 * j + RAND.uniform(-0.012, 0.012)
            start = spine(u)
            tangent = (spine(u + 0.015) - spine(u - 0.015)).normalized()
            radial = pos(a + sweep * u, 1, 0)
            length = (0.055 if outer else 0.049) * (1 - 0.62 * u) * RAND.uniform(0.82, 1.15)
            cross = (
                radial * side * 0.79 + tangent * 0.58 + point(0, 0, RAND.uniform(-0.12, 0.27))
            ).normalized()
            end = start + cross * length
            middle = start.lerp(end, 0.53) + point(0, 0, 0.003)
            b.tube([start, middle, end], [0.00072, 0.00047, 0.00018], m["twig"], 4)
            wing = point(-cross.y, cross.x, 0).normalized()
            for k in range(7):
                t = (k + 0.5) / 7.5
                base = start.lerp(end, t) + point(0, 0, 0.003 * sin(pi * t))
                for s in [-1, 1]:
                    v = min(0.99, t + RAND.uniform(-0.027, 0.027) + s * 0.030)
                    base = start.lerp(end, v) + point(0, 0, 0.003 * sin(pi * v))
                    length_n = RAND.uniform(0.019, 0.029) * (1 - 0.40 * t) * (1 - 0.18 * u)
                    aim = (
                        cross * 0.56 + s * wing * 0.83 + point(0, 0, RAND.uniform(-0.43, 0.63))
                    ).normalized()
                    b.blade(
                        base,
                        base + aim * length_n,
                        RAND.uniform(0.00125, 0.0020),
                        0.00036,
                        tint(tones, variant),
                        m["fir"],
                    )
            b.blade(
                end - cross * 0.003,
                end + cross * 0.011,
                0.0012,
                0.00032,
                tint(tones, variant * 1.06),
                m["fir"],
            )
    for j in range(9):
        u = 0.79 + j * 0.023
        direction = (spine(u + 0.012) - spine(u - 0.012)).normalized()
        for s in [-1, 1]:
            vec = (
                direction * 0.77 + pos(a + sweep * u, 1, 0) * s * 0.58 + point(0, 0, 0.19)
            ).normalized()
            b.blade(
                spine(u),
                spine(u) + vec * (0.016 - 0.0009 * j),
                0.00115,
                0.00030,
                tint(tones, variant),
                m["fir"],
            )


def cedar_spray(b, a, m):
    start = pos(a, RAND.uniform(0.155, 0.183), 0.060)
    radial = pos(a, 1, 0)
    tangent = pos(a + pi / 2, 1, 0)
    axis = (tangent + radial * RAND.uniform(-0.28, 0.42) + point(0, 0, 0.24)).normalized()
    length = RAND.uniform(0.075, 0.102)
    end = start + axis * length
    b.tube(
        [start, start.lerp(end, 0.55) + point(0, 0, 0.003), end],
        [0.0014, 0.0009, 0.00025],
        m["twig"],
        5,
    )
    for j in range(6):
        for side in [-1, 1]:
            u = 0.10 + j * 0.125
            base = start.lerp(end, u) + point(0, 0, 0.002 * sin(pi * u))
            direction = (
                axis * 0.59 + radial * (side * 0.90) + point(0, 0, RAND.uniform(-0.22, 0.2))
            ).normalized()
            tip = base + direction * (0.035 * (1 - 0.59 * u))
            b.tube([base, tip], [0.00075, 0.00026], m["twig"], 4)
            wing = point(-direction.y, direction.x, 0).normalized()
            for k in range(6):
                v = k / 6
                foot = base.lerp(tip, v)
                for s in [-1, 1]:
                    crest = (direction * 0.9 + wing * 0.44 * s + point(0, 0, 0.15)).normalized()
                    b.blade(
                        foot,
                        foot + crest * 0.014 * (1 - 0.43 * v),
                        0.0025 * (1 - 0.3 * v),
                        0.00055,
                        tint(CEDAR_COLOURS, 1 + 0.08 * v),
                        m["fir"],
                    )
            b.blade(
                tip - direction * 0.003,
                tip + direction * 0.009,
                0.0019,
                0.00042,
                tint(CEDAR_COLOURS, 1.15),
                m["fir"],
            )


def cedar_underlay(group, root, m):
    # Broad, finely toothed scale sprays under the fine fir establish the shadowed body.
    for half in range(2):
        b = Builder()
        for i in range(12):
            a = TAU * (i + 12 * half) / 24 + RAND.uniform(-0.06, 0.06)
            start = pos(a, RAND.uniform(0.150, 0.168), RAND.uniform(0.036, 0.049))
            radial = pos(a, 1, 0)
            tangent = pos(a + pi / 2, 1, 0)
            axis = (tangent + radial * RAND.uniform(0.11, 0.48) + point(0, 0, 0.18)).normalized()
            end = start + axis * RAND.uniform(0.115, 0.14)
            first = len(b.vertices)
            b.tube([start, end], [0.0018, 0.00037], m["twig"], 5)
            for j in range(5):
                for turn in [-1, 1]:
                    along = (j + 0.8) / 6.15
                    base = start.lerp(end, along)
                    direction = (
                        axis * 0.48
                        + radial * (turn * 0.89)
                        + point(0, 0, RAND.uniform(-0.13, 0.23))
                    ).normalized()
                    width = RAND.uniform(0.0048, 0.0075) * (1 - 0.35 * along)
                    length = RAND.uniform(0.039, 0.056) * (1 - 0.43 * along)
                    wing = point(-direction.y, direction.x, 0).normalized()
                    rings = []
                    tone = tint(
                        [(23, 61, 38), (31, 76, 39), (36, 78, 48), (42, 81, 46)],
                        RAND.uniform(0.92, 1.15),
                    )
                    for k in range(15):
                        u = k / 14
                        centre = base + direction * length * u + point(0, 0, 0.0035 * sin(pi * u))
                        spread = (
                            width * (0.15 + 0.85 * sin(pi * u) ** 0.80) * (1 if k % 2 else 0.74)
                        )
                        if k == 14:
                            spread = 0.00022
                        if k == 0:
                            spread = 0.00040
                        shade = tuple(min(255, round(c * (0.80 + 0.28 * u))) for c in tone)
                        rings.append(
                            [
                                b.vertex(centre - wing * spread, shade),
                                b.vertex(
                                    centre + point(0, 0, 0.0016 * sin(pi * u) + 0.00015), shade
                                ),
                                b.vertex(centre + wing * spread, shade),
                            ]
                        )
                    for back, next_row in zip(rings, rings[1:]):
                        for q in range(2):
                            b.face(
                                [back[q], next_row[q], next_row[q + 1], back[q + 1]],
                                m["fir"],
                                True,
                            )
            b.tag("Flat cedar spray %02d" % (12 * half + i + 1), first)
        b.make("Shadow cedar underlay " + str(half + 1), group, root)


def foliage(group, root, m):
    cedar_underlay(group, root, m)
    for name, count, offset in [
        ("Outer fir", 22, 0),
        ("Inner silver fir", 17, 0.21),
        ("Cedar fans", 12, 0.33),
    ]:
        b = Builder()
        for i in range(count):
            first = len(b.vertices)
            a = TAU * i / count + offset + RAND.uniform(-0.045, 0.045)
            if name == "Cedar fans":
                cedar_spray(b, a, m)
            else:
                fir_spray(b, a, name == "Outer fir", m)
            b.tag("Sprig %02d" % (i + 1), first)
        b.make(name, group, root)


def holly_leaf(b, base, vec, width, m):
    end = base + vec
    along = vec.normalized()
    side = point(-along.y, along.x, 0).normalized()
    rings = []
    for u, w in [
        (0, 0.01),
        (0.16, 0.60),
        (0.23, 0.36),
        (0.36, 0.89),
        (0.44, 0.61),
        (0.57, 1),
        (0.64, 0.62),
        (0.78, 0.72),
        (0.84, 0.38),
        (1, 0.012),
    ]:
        centre = base.lerp(end, u) + point(0, 0, 0.006 * sin(pi * u))
        span = width * w
        lift = point(0, 0, 0.003 * w)
        rings.append(
            [
                b.vertex(centre - side * span - lift),
                b.vertex(centre + lift),
                b.vertex(centre + side * span - lift),
            ]
        )
    # Both sides of wax-coated leaves are visible on the reverse.
    for p, q in zip(rings, rings[1:]):
        b.face([p[0], q[0], q[1], p[1]], m["holly"], True)
        b.face([p[1], q[1], q[2], p[2]], m["holly"], True)
    veins = [base.lerp(end, u) + point(0, 0, 0.008 * sin(pi * u)) for u in (0, 0.25, 0.5, 0.75, 1)]
    b.tube(veins, [0.0006, 0.00055, 0.0004, 0.00022, 0.00008], m["vein"], 4)


def berry_clusters(group, root, m):
    for n, (a, r, angle) in enumerate(
        [(2.43, 0.187, 0.93), (0.85, 0.209, -0.6), (0.16, 0.163, 0.35), (-2.64, 0.179, 0.12)]
    ):
        b = Builder()
        origin = pos(a, r, 0.073)
        radial = pos(a, 1, 0)
        tang = pos(a + pi / 2, 1, 0)
        for i in range(3):
            az = angle + (i - 1) * 0.83
            aim = (radial * cos(az) + tang * sin(az) + point(0, 0, 0.20)).normalized()
            holly_leaf(b, origin, aim * RAND.uniform(0.041, 0.057), RAND.uniform(0.009, 0.013), m)
        for i in range(7 if n != 2 else 5):
            az = TAU * i / 6 + 0.33 * n
            spread = 0.012 + 0.008 * (i % 3)
            if i == 6:
                spread = 0.0025
            c = (
                origin
                + radial * (spread * cos(az))
                + tang * (spread * sin(az))
                + point(0, 0, 0.012 + 0.009 * (i % 3))
            )
            mid = origin.lerp(c, 0.52) + point(0, 0, 0.003)
            b.tube([origin, mid, c], [0.0010, 0.00078, 0.00062], m["twig"], 5)
            rad = RAND.uniform(0.0061, 0.0088)
            b.oval(
                c,
                [point(rad, 0, 0), point(0, rad * 0.98, 0), point(0, 0, rad * 0.91)],
                m["fruit"] if i % 4 else m["fruit2"],
                7,
                10,
            )
            cap = c + point(0, 0, rad * 0.90)
            for k in range(5):
                az2 = TAU * k / 5 + n
                triangle = [
                    b.vertex(cap),
                    b.vertex(cap + pos(az2 - 0.27, 0.0008, 0.00012)),
                    b.vertex(cap + pos(az2, 0.0018, -0.00013)),
                ]
                b.face(triangle, m["calyx"])
        b.make("Holly and berry cluster " + str(n + 1), group, root)


def pinecone(group, root, m, index, a, r, angle, length):
    b = Builder()
    centre = pos(a, r, 0.079)
    axis = (pos(angle, 1, 0) + point(0, 0, 0.30)).normalized()
    side = point(-axis.y, axis.x, 0).normalized()
    front = axis.cross(side).normalized()
    b.oval(centre, [side * 0.015, front * 0.015, axis * length * 0.49], m["cone"], 8, 12)
    for row in range(8):
        u = (row + 0.45) / 8
        radius = 0.0200 * (sin(pi * (0.07 + 0.87 * u)) ** 0.63)
        total = 8 if row < 6 else (7 if row == 6 else 5)
        for j in range(total):
            phi = TAU * (j + row * 0.38) / total
            normal = side * cos(phi) + front * sin(phi)
            tangent = -side * sin(phi) + front * cos(phi)
            foot = centre + axis * ((u - 0.54) * length) + normal * (radius * 0.65)
            tip = foot + axis * (length * (0.21 - 0.035 * u)) + normal * (radius * 0.44 + 0.0018)
            width = 0.0087 * (0.68 + 0.32 * sin(pi * u))
            coords = [
                foot,
                foot.lerp(tip, 0.56) - tangent * width * 0.65,
                tip - tangent * width - axis * 0.0020,
                tip - tangent * width * 0.53 + axis * 0.0011,
                tip + tangent * width * 0.50 + axis * 0.0015,
                tip + tangent * width - axis * 0.0023,
                foot.lerp(tip, 0.56) + tangent * width * 0.66,
            ]
            ids = [b.vertex(p) for p in coords]
            crest = b.vertex(foot.lerp(tip, 0.68) + normal * 0.0019)
            base = b.vertex(foot.lerp(tip, 0.64) - normal * 0.0017)
            for k in range(len(ids)):
                n = (k + 1) % len(ids)
                b.face([ids[n], ids[k], crest], m["tip"] if k in (2, 3, 4) else m["scale"])
                b.face([ids[k], ids[n], base], m["cone"])
    b.make("Woodland pine cone " + str(index), group, root)


def cloth(name, group, root, m, surface, closed, steps, width_steps=10, stitches=True):
    b = Builder()
    rings = []
    for i in range(steps if closed else steps + 1):
        u = i / steps
        row = []
        for j in range(width_steps + 1):
            v = -1 + 2 * j / width_steps
            dt = 0.0002
            ut0 = (u - dt) % 1 if closed else max(0, u - dt)
            ut1 = (u + dt) % 1 if closed else min(1, u + dt)
            along = surface(ut1, v) - surface(ut0, v)
            across = surface(u, min(1, v + dt)) - surface(u, max(-1, v - dt))
            normal = along.cross(across).normalized()
            centre = surface(u, v)
            row.append((b.vertex(centre + normal * 0.0004), b.vertex(centre - normal * 0.0004)))
        rings.append(row)
    for i in range(steps):
        row = rings[i]
        nxt = rings[(i + 1) % len(rings)]
        for j in range(width_steps):
            b.face([row[j][0], nxt[j][0], nxt[j + 1][0], row[j + 1][0]], m["velvet"], True)
            b.face([row[j][1], row[j + 1][1], nxt[j + 1][1], nxt[j][1]], m["liner"], True)
        for j in [0, width_steps]:
            f = [row[j][0], row[j][1], nxt[j][1], nxt[j][0]]
            b.face(reversed(f) if j == width_steps else f, m["edge"], True)
    if not closed:
        for i in [0, -1]:
            row = rings[i]
            for j in range(width_steps):
                f = [row[j][0], row[j + 1][0], row[j + 1][1], row[j][1]]
                b.face(f if i == 0 else reversed(f), m["edge"], True)
    if stitches:
        for side in [-1, 1]:
            for inset, radius, mat in [(0.998, 0.00085, "edge"), (0.94, 0.00042, "gold")]:
                pts = [
                    surface(i / steps, side * inset) + point(0, 0, 0.00055)
                    for i in range(len(rings))
                ]
                b.tube(pts, [radius] * len(pts), m[mat], 5, closed, reference=point(0, 1, 0))
    return b.make(name, group, root)


def bow(group, root, m):
    origin = point(-0.031, -0.172, 0.130)
    for s, name, reach in [(-1, "Left", 0.095), (1, "Right", 0.102)]:

        def loop(u, v):
            theta = TAU * u
            sweep = (1 - cos(theta)) / 2
            width = 0.010 + 0.020 * (sin(pi * sweep * 0.72) ** 0.7)
            along = reach * sweep
            rise = (0.016 if s < 0 else 0.027) * sweep + 0.013 * sin(theta)
            fold = 0.0075 * sin(1.90 * pi * v + 0.55 * sweep) * (1 - 0.65 * sweep) + 0.0014 * sin(
                3 * pi * v + 0.8 * sweep
            )
            depth = 0.015 + 0.022 * sin(theta) + 0.012 * sweep + fold
            return origin + point(
                s * (0.006 + along + v * 0.008 * sweep), rise + v * width, depth + v * 0.006 * sweep
            )

        if s == 1:
            cloth(name + " shaped velvet loop", group, root, m, loop, True, 48)
        else:
            cloth(
                name + " shaped velvet loop", group, root, m, lambda u, v: loop(1 - u, v), True, 48
            )
    for s, name, length in [(-1, "Left", 0.105), (1, "Right", 0.125)]:

        def tail(u, v):
            x = s * (0.006 + 0.039 * u + 0.015 * sin(pi * u)) + v * (0.013 + 0.008 * u)
            notch = 0.020 * (1 - abs(v)) * (u**5)
            y = -length * u + notch + s * v * 0.006 * u
            depth = -0.002 + 0.013 * sin(TAU * u - 0.42) + 0.008 * cos(1.2 * pi * v + u * 2.5)
            return origin + point(x, y, depth)

        cloth(name + " cut velvet tail", group, root, m, tail, False, 32, 12)
    ties = Builder()
    for side in [-1, 1]:
        pts = [
            origin + point(side * 0.005, 0.003, 0),
            point(-0.031 + side * 0.010, -0.166, 0.072),
            point(-0.031 + side * 0.014, -0.167, 0.038),
            point(-0.031 + side * 0.010, -0.171, 0.020),
        ]
        ties.tube(pts, [0.0012] * 4, m["binding"], 6)
    ties.make("Bow attachment wire", group, root)

    def knot(u, v):
        theta = TAU * u
        return origin + point(
            v * (0.014 + 0.005 * (0.5 + 0.5 * cos(theta))) + 0.0025 * sin(theta + v * 1.3),
            0.020 * cos(theta) + 0.003 * v,
            0.016 + (0.019 + 0.0027 * cos(v * pi * 1.6)) * sin(theta),
        )

    cloth("Pinched wrap at bow centre", group, root, m, knot, True, 28, 10, False)


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def studio():
    scene = bpy.context.scene
    group = collection("Studio | excluded from GLB")
    mesh = bpy.data.meshes.new("Studio plaster wall")
    mesh.from_pydata(
        [(-3, 0.009, -3), (3, 0.009, -3), (3, 0.009, 3), (-3, 0.009, 3)], [], [(0, 1, 2, 3)]
    )
    wall = bpy.data.objects.new("Studio warm limestone wall", mesh)
    group.objects.link(wall)
    wallmat = material("Studio limestone", (203, 194, 172), 0.89)
    mesh.materials.append(wallmat)
    nodes = wallmat.node_tree.nodes
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 210
    noise.inputs["Detail"].default_value = 2
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.00036
    wallmat.node_tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    wallmat.node_tree.links.new(
        bump.outputs["Normal"], nodes.get("Principled BSDF").inputs["Normal"]
    )
    for name, where, energy, size, shade in [
        ("Winter window", (-0.62, -0.64, 0.83), 21, 0.62, (1, 0.91, 0.78)),
        ("Soft fill", (0.65, -0.84, 0.18), 12, 0.66, (0.80, 0.91, 1)),
        ("Top glint", (0.30, -0.12, 0.68), 7.5, 0.37, (1, 0.82, 0.63)),
    ]:
        lamp = bpy.data.lights.new(name, "AREA")
        lamp.energy = energy
        lamp.shape = "DISK"
        lamp.size = size
        lamp.color = shade
        light = bpy.data.objects.new(name, lamp)
        group.objects.link(light)
        light.location = where
        aim(light, (0, 0, 0))
    cam = bpy.data.objects.new("Wreath studio camera", bpy.data.cameras.new("Wreath camera"))
    group.objects.link(cam)
    scene.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 0.628
    cam.location = (0.15, -1.70, 0.095)
    aim(cam, (0, -0.046, -0.021))
    scene.world = bpy.data.worlds.new("Warm gallery daylight")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.48, 0.53, 0.61, 1)
    bg.inputs["Strength"].default_value = 0.39
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.quality = 93
    scene.view_settings.view_transform = "AgX"
    return group


def build(path):
    if path.exists():
        raise FileExistsError(
            "Source already exists. Use --export-source, or give --source a new filename."
        )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    RAND.seed(2512)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    root = bpy.data.objects.new(ROOT, None)
    scene.collection.objects.link(root)
    root.empty_display_size = 0.027
    m = palette()
    core(collection("01 | Willow base and hanger"), root, m)
    foliage(collection("02 | Bound evergreen sprays"), root, m)
    group = collection("03 | Holly and pinecones")
    berry_clusters(group, root, m)
    for i, (a, r, angle, length) in enumerate(
        [(-0.47, 0.183, -0.81, 0.062), (-0.79, 0.203, -1.19, 0.052), (2.03, 0.188, 2.31, 0.061)]
    ):
        pinecone(group, root, m, i + 1, a, r, angle, length)
    bow(collection("04 | Velvet bow"), root, m)
    studio_group = studio()
    for obj in studio_group.objects:
        obj.hide_set(True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                view = area.spaces.active
                view.region_3d.view_perspective = "ORTHO"
                view.region_3d.view_distance = 0.87
                view.region_3d.view_location = (0, -0.03, -0.02)
                view.region_3d.view_rotation = scene.camera.rotation_euler.to_quaternion()
                view.shading.color_type = "MATERIAL"
    bpy.context.preferences.filepaths.save_version = 0
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True, relative_remap=False)


def export(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    root = bpy.data.objects[ROOT]
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    for obj in root.children_recursive:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_apply=True,
        export_animations=False,
        export_extras=False,
        export_lights=False,
        export_cameras=False,
        export_use_gltfpack=False,
    )


def render_rear(path):
    # Move only studio fixtures to show how the loop is captured around the core.
    scene = bpy.context.scene
    target = (0, -0.020, 0.184)
    bpy.data.objects["Studio warm limestone wall"].location.y = -0.215
    for name, where in [
        ("Winter window", (-0.32, 0.43, 0.62)),
        ("Soft fill", (0.39, 0.54, 0.12)),
        ("Top glint", (0.20, 0.05, 0.53)),
    ]:
        obj = bpy.data.objects[name]
        obj.location = where
        aim(obj, target)
    cam = scene.camera
    cam.location = (0.07, 0.83, 0.285)
    cam.data.ortho_scale = 0.175
    aim(cam, target)
    scene.render.resolution_x = 720
    scene.render.resolution_y = 540
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path.resolve())
    bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--export-source", action="store_true")
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=BASE / "exports" / (SLUG + ".glb"))
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--rear-preview", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if args.build:
        build(args.source.resolve())
    else:
        bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()), load_ui=False)
    export(args.out.resolve())
    if args.preview or args.rear_preview:
        # The catalogue images show the shipped glTF interpreted by Blender's importer.
        # Preserve the editable source and leave the existing studio lights in place.
        for obj in bpy.data.objects[ROOT].children_recursive:
            obj.hide_render = True
        bpy.ops.import_scene.gltf(filepath=str(args.out.resolve()))
    if args.preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        bpy.context.scene.render.filepath = str(args.preview.resolve())
        bpy.ops.render.render(write_still=True)
    if args.rear_preview:
        render_rear(args.rear_preview)


if __name__ == "__main__":
    main()
