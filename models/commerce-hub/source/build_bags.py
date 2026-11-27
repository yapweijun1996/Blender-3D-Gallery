"""Build the three shopping bags from hollow paper meshes inside Blender."""

import math
import sys
from pathlib import Path
from types import ModuleType


SOURCE = Path(sys._getframe().f_code.co_filename).resolve().parent
common = ModuleType("commerce_hub_common")
common.__file__ = str(SOURCE / "common.py")
exec(compile(Path(common.__file__).read_text(), common.__file__, "exec"), vars(common))


def paper_bag(model, name, position, dims, arch, yaw, paints):
    width, depth, height = dims
    x, y, z = position
    sine, cosine = math.sin(yaw), math.cos(yaw)

    def place(px, py, pz):
        return x + px * cosine - py * sine, y + px * sine + py * cosine, z + pz

    def half_depth(level):
        return depth * (0.5 - 0.135 * level / height)

    def section(level, span, fold, recess=0.0, inset=0.0):
        w = width * span / 2 - inset
        d = half_depth(level) - inset
        return [
            place(-w, -d, level), place(w, -d, level),
            place(w - fold, 0, level - recess), place(w, d, level),
            place(-w, d, level), place(-w + fold, 0, level - recess),
        ]

    # Pair the lining with the outer gusset at every bend in the paper.
    fold, recess = 0.065 * width, 0.046 * height
    floor = (0.077, 0.997, 0.015 * width)
    crease = (0.33 * height, 0.984, 0.041 * width)
    outside = [(0.0, 0.965, 0.0), (0.014, 1.0, 0.009 * width), floor, crease,
               (height - 0.019, 0.932, fold, recess), (height, 0.928, fold, recess)]
    inside = [(height - 0.006, 0.928, fold, recess), outside[-2], crease, floor]
    rings = [section(*profile) for profile in outside]
    rings.extend(section(*profile, inset=0.019) for profile in inside)
    shell = common.MeshPart(model, name, origin=position)
    shell.vertices.extend(v for ring in rings for v in ring)
    shell.materials.extend(paints[:3])
    for layer, material_index in enumerate((0, 0, 0, 0, 2, 2, 1, 1, 1)):
        for point in range(6):
            following = (point + 1) % 6
            start = 6 * layer
            a, b = start + point, start + following
            c, d = b + 6, a + 6
            # Opposite winding on the lining still uses the outer panel's physical diagonal.
            faces = ((a, b, d), (b, c, d)) if material_index == 1 else ((a, b, c), (a, c, d))
            shell.faces.extend(faces)
            shell.face_settings.extend([(material_index, False)] * len(faces))
    for start, level, paint in ((0, 0.0, 0), (6 * (len(rings) - 1), floor[0], 1)):
        center = len(shell.vertices)
        shell.vertices.append(place(0, 0, level))
        for i in range(6):
            face = (center, start + i, start + (i + 1) % 6)
            shell.faces.append(face if start else face[::-1])
            shell.face_settings.append((paint, False))
    shell.finish()

    handles = common.MeshPart(model, f"{name}_Handles", origin=position)
    grip_radius = 0.022 + 0.008 * width
    attachment = 0.086 * height
    anchor_depth = half_depth(height - attachment) - 0.006
    for face in (-1, 1):
        points = [
            place(width * 0.214 * math.cos(t),
                  face * (anchor_depth + 0.060 * math.sqrt(math.sin(t))),
                  height - attachment + (arch + attachment) * math.sin(t))
            for t in (math.pi * i / 24 for i in range(25))
        ]
        handles.tube(points, grip_radius, paints[3], sides=10,
                     guide=(-sine, cosine, 0), end_radius=grip_radius * 0.29)
    handles.finish()


def model_bags(model, effects):
    warm_light = common.material("Warm Light Ring", "#A86618", roughness=0.58,
                                 emission="#FFD06B", strength=0.90, specular=0.20)
    ring = common.MeshPart(model, "GlowRing")
    size, radius = common.PLINTH_INNER_SIZE - 0.31, 0.404
    border = common.rounded_rect(size, size, radius, steps=12)
    ring.tube([(x, y, common.PLINTH_HEIGHT + 0.013) for x, y in border],
              0.027, warm_light, sides=10, guide=(0, 0, 1), closed=True)
    ring.finish()
    common.perimeter_gradient(model, "Fx_RingHalo", effects, size, radius,
                              common.PLINTH_HEIGHT + 0.003, "#FFCA62",
                              [(spread, 0, 0, alpha) for spread, alpha in (
                                  (-0.17, 0), (-0.11, 0.075), (-0.059, 0.27),
                                  (-0.029, 0.59), (0, 0.68), (0.026, 0.59),
                                  (0.047, 0.32), (0.069, 0.090), (0.087, 0),
                              )], steps=12)

    paints = (
        common.material("Bag Paper", roughness=0.80, specular=0.18),
        common.material("Bag Lining", roughness=0.82, specular=0.18),
        common.material("Bag Lip", roughness=0.66, specular=0.22),
        common.material("Bag Handle", roughness=0.55, specular=0.28),
    )
    base = common.PLINTH_HEIGHT
    paper_bag(model, "Bag_Large", (-0.085, 0.65, base), (2.56, 1.18, 2.24),
              0.48, math.radians(3), paints)
    paper_bag(model, "Bag_Medium", (0.88, -0.845, base), (1.30, 0.70, 1.47),
              0.34, math.radians(-86), paints)
    paper_bag(model, "Bag_Small", (-0.31, -0.905, base), (1.34, 0.70, 1.365),
              0.245, math.radians(-86), paints)


result = common.build(
    "bags", model_bags,
    {"triangles": 15000, "bytes": 500000, "primitives": 20},
    direction=(-0.96, -1.0, 0.73),
    frame=(0.144, 0.049, 0.860, 0.913),
    review_features={
        "silhouette": "Three upright tapered bags: large back-left, medium back-right, small front.",
        "paper": "Hollow orange interiors, thin bright mouths, folded end gussets, two rounded handles each.",
        "plinth": "Rounded sage outer tier, lighter inset tier, warm perimeter glow and contact shadow.",
        "presentation": "Cream studio, warm-to-neutral balance, similar scale and three-quarter framing.",
    },
)
