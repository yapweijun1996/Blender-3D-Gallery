"""Build three floating payment cards inside Blender."""

import math
import sys
from pathlib import Path
from types import ModuleType


SOURCE = Path(sys._getframe().f_code.co_filename).resolve().parent
common = ModuleType("commerce_hub_common")
common.__file__ = str(SOURCE / "common.py")
exec(compile(Path(common.__file__).read_text(), common.__file__, "exec"), vars(common))

BASE = common.PLINTH_HEIGHT
WIDTH, DEPTH, THICKNESS = 3.14, 2.00, 0.117
CORNER = 0.20
ANGLE = math.radians(8)
CONTACT = "Fx_CardContactShadows"
CARDS = (
    ("Card_Bottom", -0.065, BASE + 0.132, "dark"),
    ("Card_Middle", -0.022, BASE + 0.465, "amber"),
    ("Card_Top", 0.036, BASE + 0.798, "sage"),
)


def place(point):
    u, v, z = point
    return (u * math.cos(ANGLE) - v * math.sin(ANGLE),
            u * math.sin(ANGLE) + v * math.cos(ANGLE), z)


def mark(part, p, z, face):
    # A single sliced citrus medallion gives the card its own network emblem.
    u, v, radius = 1.10, -0.62, 0.188
    for size, lift, paint in ((1, 0, "dark"), (0.90, 0.002, "ivory")):
        rim = [face((u + radius * size * math.cos(common.TAU * i / 24),
                      v + radius * size * math.sin(common.TAU * i / 24), z + lift))
               for i in range(24)]
        part.add(rim, [tuple(range(len(rim)))], p[paint])
    for sector in range(7):
        middle = common.TAU * (sector + 0.5) / 7
        vertices = [face((u + radius * 0.10 * math.cos(middle),
                           v + radius * 0.10 * math.sin(middle), z + 0.004))]
        for i in range(4):
            angle = common.TAU * (sector + 0.055 + i * 0.89 / 3) / 7
            vertices.append(face((u + radius * 0.80 * math.cos(angle),
                                   v + radius * 0.80 * math.sin(angle), z + 0.004)))
        part.add(vertices, [(0, 1, 2, 3, 4)], p["amber" if sector in (1, 2) else "gold"])


def card_face(part, p, z, face):
    # The thinner, darker metallic strokes sit just above the recessed-looking chip seams.
    chip_x, chip_y = -0.92, 0.44
    part.box((chip_x, chip_y, z + 0.010), (0.63, 0.43, 0.025), p["gold"],
             edge=0.006, corner=0.068, steps=3, transform=face)
    seam_z = z + 0.0235
    for dx in (-0.090, 0.090):
        part.box((chip_x + dx, chip_y, seam_z), (0.011, 0.374, 0.002),
                 p["amber"], transform=face)
    for dy in (-0.074, 0.074):
        for dx, width in ((-0.187, 0.178), (0, 0.167), (0.187, 0.178)):
            part.box((chip_x + dx, chip_y + dy, seam_z), (width, 0.011, 0.002),
                     p["amber"], transform=face)
    part.box((chip_x, chip_y, seam_z + 0.002), (0.164, 0.134, 0.005), p["gold"],
             edge=0.0014, corner=0.019, steps=1, transform=face)

    for u in (-1.04, -0.35, 0.34, 1.03):
        part.box((u, -0.184, z + 0.013), (0.493, 0.10, 0.026), p["ivory"],
                 edge=0.007, corner=0.028, steps=1, transform=face)
    part.box((-0.85, -0.66, z + 0.012), (0.86, 0.086, 0.024), p["ivory"],
             edge=0.006, corner=0.022, steps=1, transform=face)
    for radius in (0.091, 0.160, 0.229):
        path = []
        for i in range(8):
            angle = math.radians(-49 + 98 * i / 7)
            path.append(face((0.94 + radius * math.cos(angle),
                               0.47 + radius * math.sin(angle), z + 0.017)))
        part.tube(path, 0.015, p["ivory"], sides=5, guide=(0, 0, 1), end_radius=0.007)
    mark(part, p, z + 0.003, face)


def contact_shadows(model, fx):
    shadow = common.MeshPart(model, CONTACT)
    vertices, faces, alphas = [], [], []
    for _, shift, center_z, _ in CARDS[:-1]:
        start = len(vertices)
        stops = ((0.48, 0.34), (0.72, 0.29), (0.88, 0.14), (1.0, 0))
        for scale, alpha in stops:
            rect = common.rounded_rect(2.94 * scale, 1.83 * scale, 0.19 * scale, 3)
            vertices.extend(place((u + 0.025, v + shift + 0.028, center_z + THICKNESS / 2 + 0.002))
                            for u, v in rect)
            alphas.extend([alpha] * len(rect))
        count = len(rect)
        faces.append(tuple(range(start, start + count)))
        faces.extend(tuple(reversed(face)) for face in common.strip_faces(start, count, len(stops)))
    common.gradient_surface(shadow, fx, vertices, faces, "#283422", alphas)


def model_payment(model, fx):
    paint = common.material
    p = {
        "dark": paint("Payment Dark Sage", "#527B4E", roughness=0.38),
        "amber": paint("Payment Amber", "#EBAA32", roughness=0.36),
        "sage": paint("Payment Sage", "#84AE7B", roughness=0.39),
        "gold": paint("Payment Chip Gold", "#F7CC60", roughness=0.34, metallic=0.28),
        "ivory": paint("Payment Ivory Details", "#FFF3E0", roughness=0.45),
    }
    for name, shift, center_z, color in CARDS:
        card = common.MeshPart(model, name, origin=place((0, shift, center_z)))

        def face(point):
            u, v, z = point
            return place((u, v + shift, z))

        card.box((0, 0, center_z), (WIDTH, DEPTH, THICKNESS), p[color],
                 edge=0.034, corner=CORNER, steps=4, bevel_steps=2, transform=face)
        top = center_z + THICKNESS / 2
        if name == "Card_Top":
            card_face(card, p, top, face)
        else:
            card.box((-0.84, -0.72, top + 0.010), (0.89, 0.088, 0.020), p["ivory"],
                     edge=0.005, corner=0.025, steps=1, transform=face)
        card.finish()
    contact_shadows(model, fx)


result = common.build(
    "payment", model_payment,
    {"triangles": 5000, "bytes": 150000, "primitives": 14},
    direction=(0.88, -1.0, 0.94),
    frame=(0.102, 0.090, 0.898, 0.958),
    extra_effects=(CONTACT,),
    required_parts=tuple(name for name, *_ in CARDS),
    review_features={
        "layout": "Three rounded floating cards above the common neutral grey plinth.",
        "face": "Gold chip with contact grooves, number and name bars, contactless arcs, and an original citrus medallion.",
        "motion": "Three separately named card meshes, each with its face details and a centred pivot.",
        "presentation": "Soft exported contact shadows between cards and a warm floor glow.",
    },
)
