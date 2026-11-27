"""Build the automation label dispenser inside Blender."""

import math
import sys
from pathlib import Path
from types import ModuleType


SOURCE = Path(sys._getframe().f_code.co_filename).resolve().parent
common = ModuleType("commerce_hub_common")
common.__file__ = str(SOURCE / "common.py")
exec(compile(Path(common.__file__).read_text(), common.__file__, "exec"), vars(common))

BASE = common.PLINTH_HEIGHT
WIDTH, DEPTH, HEIGHT = 2.22, 2.08, 1.83
FRONT, SLOT_Z = -0.66, 0.990
LAMP = "Automation Warm Light"

# Hand-drawn 11 × 11 artwork with no payload, format fields or error correction.
DECORATIVE_CODE = (
    "11111001001",
    "10001011100",
    "10101000111",
    "10001011001",
    "11111001100",
    "00100110111",
    "11011100010",
    "01000111111",
    "11110010001",
    "10010110101",
    "11010111111",
)


def front_face(point):
    u, height, relief = point
    return (u, FRONT - relief, BASE + height)


def right_face(point):
    u, height, relief = point
    return (WIDTH / 2 + relief, u, BASE + height)


def contour(width, height, radius, z, relief):
    return [front_face((u, v + z, relief))
            for u, v in common.rounded_rect(width, height, radius, 4)]


def machine_shell(body, p):
    shell = []
    for relief, inset in (
        (-DEPTH, 0.136), (-DEPTH + 0.032, 0.052), (-DEPTH + 0.083, 0.013),
        (-DEPTH + 0.136, 0), (-0.136, 0), (-0.083, 0.013), (-0.032, 0.052), (0, 0.136),
    ):
        shell.append(contour(WIDTH - 2 * inset, HEIGHT - 2 * inset, 0.228 - inset,
                             HEIGHT / 2, relief))
    body.loft(shell, p["sage"], caps=(True, False))

    # Continue the front face into a real opening and recess behind the amber frame.
    frame = [contour(w, h, radius, SLOT_Z, relief) for w, h, radius, relief in (
        (1.54, 0.476, 0.111, 0),
        (1.54, 0.476, 0.111, 0.027),
        (1.506, 0.442, 0.096, 0.050),
        (1.274, 0.288, 0.057, 0.050),
        (1.238, 0.258, 0.047, 0.030),
        (1.238, 0.258, 0.047, -0.057),
    )]
    body.loft((shell[-1], frame[0]), p["sage"], caps=(False, False), smooth=False)
    body.loft(frame, p["amber"], caps=(False, False))
    body.loft((frame[-1], contour(1.238, 0.258, 0.047, SLOT_Z, -0.224)),
              p["recess"], caps=(False, True), smooth=False)
    body.box((0, SLOT_Z + 0.093, -0.074), (1.074, 0.034, 0.039), p["light"],
             edge=0.005, corner=0.013, steps=2, transform=front_face)


def side_branding(body, p):
    rim, hole = [], []
    for tooth in range(8):
        for fraction, radius in ((0, 0.181), (0.19, 0.220), (0.63, 0.220), (0.82, 0.181)):
            angle = common.TAU * (tooth + fraction) / 8
            co, si = math.cos(angle), math.sin(angle)
            rim.append((0.37 + radius * co, 1.31 + radius * si))
            hole.append((0.37 + 0.096 * co, 1.31 + 0.096 * si))
    gear = [[right_face((u, z, depth)) for u, z in ring]
            for ring, depth in ((rim, 0.001), (rim, 0.024), (hole, 0.024), (hole, 0.001))]
    body.loft(gear + [gear[0]], p["ivory"], caps=(False, False), smooth=False)
    common.geometry_text(body, "Automation", (0.371, 0.902, 0.008), 1.49, 0.205,
                         p["ivory"], right_face, weight=0.018, resolution=4)

    ribbon = []
    for i in range(15):
        t = i / 14
        u = -0.475 + 1.65 * t
        z = 0.257 + 0.251 * (t * t * (3 - 2 * t))
        width = 0.032 + 0.118 * t
        ribbon.extend((right_face((u, z, 0.006)), right_face((u, z + width, 0.006))))
    body.add(ribbon, [(i, i + 2, i + 3, i + 1) for i in range(0, len(ribbon) - 2, 2)],
             p["swoosh"])


def output_card(model, p):
    center_y = -1.195
    card_z = BASE + SLOT_Z - 0.055
    card = common.MeshPart(model, "Output_Card", origin=(0, FRONT, card_z))
    card.box((0, center_y, card_z), (1.105, 1.344, 0.059), p["paper"],
             edge=0.015, corner=0.084, steps=3, bevel_steps=2)
    ink_z = card_z + 0.0305
    card.box((-0.371, center_y, ink_z), (0.175, 1.078, 0.0025), p["swoosh"],
             edge=0.0008, corner=0.012, steps=1)

    def print_block(x, y, width, depth):
        left, right = x - width / 2, x + width / 2
        near, far = y - depth / 2, y + depth / 2
        card.add([(left, near, ink_z), (right, near, ink_z),
                  (right, far, ink_z), (left, far, ink_z)], [(0, 1, 2, 3)], p["ink"])

    dot = 0.030
    for index, row in enumerate(DECORATIVE_CODE):
        for column, cell in enumerate(row):
            if cell == "1":
                print_block(0.105 + (column - 5) * dot, -1.132 - (index - 5) * dot,
                            dot * 0.94, dot * 0.94)
    for x, width in zip((-0.004, 0.049, 0.104, 0.159, 0.216),
                        (0.020, 0.034, 0.017, 0.034, 0.023), strict=True):
        print_block(x, -1.567, width, 0.176)
    card.finish()


def model_automation(model, _fx):
    paint = common.material
    p = {
        "sage": paint("Automation Sage", "#78A372", roughness=0.37),
        "swoosh": paint("Automation Light Green", "#8AB85A", roughness=0.48),
        "amber": paint("Automation Amber Trim", "#F2B63C", roughness=0.37),
        "light": paint(LAMP, "#FFE39B", emission="#FFD275", strength=2.30),
        "recess": paint("Automation Slot Shade", "#563C1D", roughness=0.64),
        "ivory": paint("Automation Ivory Lettering", "#F9F6E9", roughness=0.46),
        "paper": paint("Automation Label Stock", "#F5E5BB", roughness=0.58),
        "ink": paint("Automation Label Ink", "#665239", roughness=0.66),
    }
    body = common.MeshPart(model, "Machine_Body", origin=(0, FRONT + DEPTH / 2, BASE))
    machine_shell(body, p)
    side_branding(body, p)
    body.finish()
    output_card(model, p)

    indicator_base = (-0.077, -0.288, BASE + HEIGHT)
    pill = common.MeshPart(model, "Indicator", origin=indicator_base)
    x, y, z = indicator_base
    pill.box((x, y, z + 0.013), (0.484, 0.138, 0.044), p["amber"],
             edge=0.012, corner=0.064, steps=4)
    pill.box((x, y, z + 0.033), (0.435, 0.102, 0.023), p["light"],
             edge=0.007, corner=0.049, steps=4)
    pill.finish()


result = common.build(
    "automation", model_automation,
    {"triangles": 6000, "bytes": 180000, "primitives": 16},
    direction=(1.08, -1.0, 0.850),
    frame=(0.120, 0.053, 0.886, 0.958),
    emissive_materials=(LAMP,),
    required_parts=("Machine_Body", "Output_Card", "Indicator"),
    studio_lights=(
        ("Slot Warm Bounce", (0, FRONT + 0.012, BASE + SLOT_Z + 0.062),
         (0, FRONT - 0.34, BASE + SLOT_Z - 0.082), 5, 0.30, "#FFCA68"),
    ),
    review_features={
        "machine": "Rounded sage housing with an amber indicator, a recessed warm-lit slot and right-face gear, lettering and swoosh.",
        "label": "Protruding cream card with a green stripe, fixed non-encoding square artwork and five barcode bars.",
        "motion": "Named machine and indicator meshes, with an output card pivot at the slot.",
    },
)
