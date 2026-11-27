"""Build the warehouse and dispatch conveyors inside Blender."""

import math
import sys
from pathlib import Path
from types import ModuleType


SOURCE = Path(sys._getframe().f_code.co_filename).resolve().parent
common = ModuleType("commerce_hub_common")
common.__file__ = str(SOURCE / "common.py")
exec(compile(Path(common.__file__).read_text(), common.__file__, "exec"), vars(common))

BASE = common.PLINTH_HEIGHT
LEFT, RIGHT = -1.65, 0.94
FRONT, BACK = -0.58, 1.83
EAVE = 1.70
RISE = 0.51
DOOR_LEFT, DOOR_RIGHT = -1.385, 0.625
DOOR_START, DOOR_END = -0.281, 1.200
WINDOW_START, WINDOW_END = 1.314, 1.748
WINDOW_BOTTOM, WINDOW_TOP = 0.797, 1.442
WARM_LIGHT = "Warehouse Warm Lamps"
WARM_FLOOR = "Fx_WarehouseWarmth"
ROLLER_RADIUS = 0.030
ROLLER_HEIGHT = 0.256
CONVEYORS = (
    # Centre, length, width, orientation, carton offset along the rollers' path, carton size.
    ((1.52, -1.03), 1.65, 0.454, True, -0.24, (0.287, 0.321, 0.273)),
    ((1.13, 0.16), 1.68, 0.459, False, 0.41, (0.334, 0.283, 0.285)),
    ((1.105, 0.935), 1.73, 0.451, False, 0.57, (0.316, 0.281, 0.273)),
)


def palette():
    paint = common.material
    return {
        "wall": paint("Warehouse Cream Siding", "#E6DFCD", roughness=0.53),
        "trim": paint("Warehouse Ivory Trim", "#F2EDE0", roughness=0.47),
        "green": paint("Warehouse Frame Green", "#638957", roughness=0.46),
        "roof": paint("Warehouse Roof Sage", "#5F8F66", roughness=0.39, metallic=0.10),
        "metal": paint("Warehouse Satin Roller Metal", "#ACADB2", roughness=0.36, metallic=0.34),
        "dark": paint("Warehouse Charcoal", "#434540", roughness=0.57),
        "beam": paint("Warehouse Rack Orange", "#E99B36", roughness=0.44),
        "board": paint("Warehouse Carton Kraft", "#E2AA63", roughness=0.75),
        "tape": paint("Warehouse Carton Tape", "#FFE2A4", roughness=0.58),
        "wood": paint("Warehouse Pallet Wood", "#BB844C", roughness=0.72),
        "yellow": paint("Warehouse Safety Yellow", "#F8C532", roughness=0.44),
        "light": paint(WARM_LIGHT, "#FFE2A3", emission="#FFD179", strength=2.2),
        "window": paint("Warehouse Amber Glazing", "#F2AD55", roughness=0.28, alpha=0.29),
    }


def panel(part, x0, x1, y0, y1, z0, z1, paint):
    part.box(((x0 + x1) / 2, (y0 + y1) / 2, BASE + (z0 + z1) / 2),
             (x1 - x0, y1 - y0, z1 - z0), paint)


def building(part, p):
    thick = 0.086
    for x0, x1, z0 in ((LEFT, DOOR_LEFT, 0), (DOOR_RIGHT, RIGHT, 0),
                       (DOOR_LEFT, DOOR_RIGHT, 1.525)):
        panel(part, x0, x1, FRONT, FRONT + thick, z0, EAVE, p["wall"])
    for y0, y1, z0, z1 in (
        (FRONT + thick, DOOR_START, 0, EAVE),
        (DOOR_START, DOOR_END, 1.495, EAVE),
        (DOOR_END, WINDOW_START, 0, EAVE),
        (WINDOW_START, WINDOW_END, 0, WINDOW_BOTTOM),
        (WINDOW_START, WINDOW_END, WINDOW_TOP, EAVE),
        (WINDOW_END, BACK - thick, 0, EAVE),
    ):
        panel(part, RIGHT - thick, RIGHT, y0, y1, z0, z1, p["wall"])
    panel(part, LEFT, LEFT + thick, FRONT + thick, BACK - thick, 0, EAVE, p["wall"])
    panel(part, LEFT, RIGHT, BACK - thick, BACK, 0, EAVE, p["wall"])

    ridge = (LEFT + RIGHT) / 2
    for y0 in (FRONT, BACK - thick):
        gable = [(LEFT, y0, BASE + EAVE), (RIGHT, y0, BASE + EAVE),
                 (ridge, y0, BASE + EAVE + RISE)]
        part.add(gable + [(x, y + thick, z) for x, y, z in gable],
                 [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], p["wall"])
    for x in (ridge + index * 0.278 for index in range(-4, 5)):
        top = EAVE + RISE * (1 - abs(x - ridge) / (RIGHT - ridge))
        bottom = 1.565 if DOOR_LEFT < x < DOOR_RIGHT else 1.410
        panel(part, x - 0.003, x + 0.003, FRONT - 0.004, FRONT, bottom, top - 0.034, p["trim"])

    angle = math.atan2(RISE, RIGHT - ridge)
    slope = (RIGHT - ridge) / math.cos(angle)
    roof_center = (FRONT + BACK) / 2
    roof_length = BACK - FRONT + 0.23
    for sign in (-1, 1):
        def slope_face(point):
            u, v, w = point
            return (ridge + u * math.cos(angle) + sign * w * math.sin(angle), v,
                    BASE + EAVE + RISE - sign * u * math.sin(angle) + w * math.cos(angle))

        panel_width = slope + 0.104
        part.box((sign * (panel_width / 2 - 0.005), roof_center, 0.029),
                 (panel_width + 0.010, roof_length, 0.067), p["roof"],
                 edge=0.010, steps=2, transform=slope_face)
        for index in range(12):
            y = roof_center - roof_length * 0.455 + index * roof_length * 0.91 / 11
            part.box((sign * (panel_width / 2 + 0.004), y, 0.068),
                     (panel_width - 0.030, 0.018, 0.023), p["roof"],
                     edge=0.004, steps=1, transform=slope_face)
        part.box((sign * (panel_width - 0.011), roof_center, 0.041),
                 (0.047, roof_length + 0.022, 0.075), p["green"],
                 edge=0.008, steps=2, transform=slope_face)
    part.box((ridge, roof_center, BASE + EAVE + RISE + 0.062), (0.089, roof_length, 0.054),
             p["roof"], edge=0.009, steps=2)

    def front_face(point):
        u, v, w = point
        return (u, FRONT - w, BASE + v)

    def right_face(point):
        u, v, w = point
        return (RIGHT + w, u, BASE + v)

    roller_door(part, p, front_face, DOOR_LEFT, DOOR_RIGHT, 1.540, 1.141)
    roller_door(part, p, right_face, DOOR_START, DOOR_END, 1.503, 1.084)

    middle = (WINDOW_START + WINDOW_END) / 2
    center_z = (WINDOW_BOTTOM + WINDOW_TOP) / 2
    width, height = WINDOW_END - WINDOW_START, WINDOW_TOP - WINDOW_BOTTOM
    for u in (WINDOW_START, WINDOW_END):
        part.box((u, center_z, 0.014), (0.067, height + 0.102, 0.074), p["trim"],
                 edge=0.007, steps=1, transform=right_face)
    for z in (WINDOW_BOTTOM, WINDOW_TOP):
        part.box((middle, z, 0.014), (width + 0.102, 0.059, 0.075), p["trim"],
                 edge=0.007, steps=1, transform=right_face)
    for u in (WINDOW_START + 0.047, middle, WINDOW_END - 0.047):
        part.box((u, center_z, 0.018), (0.026, height - 0.044, 0.046), p["green"],
                 edge=0.004, steps=1, transform=right_face)
    for z in (WINDOW_BOTTOM + 0.033, center_z, WINDOW_TOP - 0.033):
        part.box((middle, z, 0.018), (width - 0.065, 0.029, 0.046), p["green"],
                 edge=0.004, steps=1, transform=right_face)
    part.box((middle, center_z, -0.015), (width - 0.061, height - 0.033, 0.007),
             p["window"], transform=right_face)

    vent_z = 1.785
    part.box((ridge, vent_z, 0.022), (0.265, 0.218, 0.053), p["trim"],
             edge=0.009, steps=2, transform=front_face)
    part.box((ridge, vent_z, 0.048), (0.214, 0.166, 0.019), p["dark"],
             edge=0.004, steps=1, transform=front_face)
    for i in range(6):
        part.box((ridge, vent_z - 0.066 + i * 0.027, 0.063), (0.209, 0.013, 0.019),
                 p["trim"], transform=front_face)

    part.box((ridge, 2.014, 0.021), (0.086, 0.103, 0.048), p["green"],
             edge=0.008, steps=1, transform=front_face)
    stem = [(ridge, 2.016, 0.040), (ridge, 2.070, 0.057), (ridge, 2.080, 0.103),
            (ridge, 2.066, 0.147), (ridge, 2.025, 0.169), (ridge, 1.978, 0.169)]
    part.tube([front_face(point) for point in stem], 0.016, p["green"], sides=7, guide=(1, 0, 0))
    part.lathe((ridge, FRONT - 0.169, BASE + 1.954),
               [(0.095, 0), (0.101, 0.013), (0.089, 0.032), (0.038, 0.047)],
               p["green"], sides=16)
    part.lathe((ridge, FRONT - 0.169, BASE + 1.952), [(0.078, 0), (0.084, 0.009)],
               p["light"], sides=16)
    for y in (0.26, 1.18):
        part.box((-0.02, y, BASE + 1.553), (1.42, 0.052, 0.042),
                 p["light"], edge=0.008, steps=2)


def roller_door(part, p, place, start, end, top, bottom):
    center, span = (start + end) / 2, end - start
    for u in (start, end):
        part.box((u, top / 2, 0.016), (0.053, top, 0.080), p["trim"],
                 edge=0.007, steps=1, transform=place)
        part.box((u + (0.031 if u == start else -0.031), top / 2, -0.007),
                 (0.021, top - 0.047, 0.040), p["dark"], transform=place)
    part.box((center, top, 0.018), (span + 0.060, 0.058, 0.086), p["trim"],
             edge=0.008, steps=2, transform=place)
    slat_height = (top - bottom - 0.016) / 6
    for row in range(6):
        z = bottom + slat_height * (row + 0.5)
        part.box((center, z, 0.005), (span - 0.052, slat_height - 0.003, 0.042),
                 p["metal"], edge=0.006, steps=1, transform=place)
    part.box((center, bottom, 0.024), (span - 0.059, 0.024, 0.043),
             p["metal"], edge=0.005, steps=1, transform=place)
    part.box((center, 0.004, 0), (span - 0.049, 0.009, 0.107), p["trim"], transform=place)


def carton(part, p, x, y, z, width, depth, height):
    common.carton(part, (x, y, BASE + z), (width, depth, height), p["board"], p["tape"], p["dark"])


def rack(part, p, center, length, depth, rows, *, turned=False, count=3):
    x, y = center
    post = 0.043
    end = length / 2
    half_depth = depth / 2

    def place(point):
        u, v, w = point
        return (x - v, y + u, BASE + w) if turned else (x + u, y + v, BASE + w)

    def beam(point, dims, paint, edge=0):
        part.box(point, dims, paint, edge=edge, steps=1, transform=place)

    top = rows[-1] + 0.227
    for u in (-end, end):
        for v in (-half_depth, half_depth):
            beam((u, v, top / 2), (post, post, top), p["green"], 0.005)
            beam((u, v, 0.017), (0.075, 0.072, 0.030), p["green"])
        for index, height in enumerate(rows):
            high = rows[index + 1] if index + 1 < len(rows) else top - 0.070
            for start, stop in ((-half_depth, half_depth), (half_depth, -half_depth)):
                part.tube([place((u, start, height + 0.02)), place((u, stop, high - 0.02))],
                          0.010, p["green"], sides=5, guide=(1, 0, 0))
    for row, height in enumerate(rows):
        beam((0, 0, height - 0.022), (length, depth + 0.016, 0.044), p["beam"], 0.006)
        for sign in (-1, 1):
            beam((0, sign * half_depth, height - 0.035), (length + 0.012, 0.029, 0.052),
                 p["beam"], 0.004)
        slots = count - int(row == 2)
        pitch = (length - 0.035) / slots
        for index in range(slots):
            u = (index - (slots - 1) / 2) * pitch
            v = (index % 2 - 0.5) * 0.022
            cx, cy, _ = place((u, v, height))
            width = pitch * (0.90 - 0.04 * (index % 2))
            box_depth = depth * (0.82 + 0.06 * (index % 2))
            size_x, size_y = (box_depth, width) if turned else (width, box_depth)
            carton(part, p, cx, cy, height, size_x, size_y, 0.224 + 0.018 * ((index + row) % 3))


def pallet(part, paint, x, y, width, depth):
    for dx in (-0.35 * width, 0, 0.35 * width):
        part.box((x + dx, y, BASE + 0.015), (width * 0.17, depth, 0.030), paint)
        for dy in (-0.36 * depth, 0, 0.36 * depth):
            part.box((x + dx, y + dy, BASE + 0.051), (width * 0.17, depth * 0.17, 0.046), paint)
    for dy in (-0.40, -0.20, 0, 0.20, 0.40):
        part.box((x, y + dy * depth, BASE + 0.088), (width, depth * 0.175, 0.028), paint)
    return 0.102


def cargo(part, p):
    rack(part, p, (-1.60, -1.175), 1.08, 0.40, (0.223, 0.654, 1.078), turned=True)
    rack(part, p, (-1.28, 0.43), 1.56, 0.353, (0.227, 0.618, 1.010), turned=True, count=4)
    rack(part, p, (0.055, 1.485), 1.37, 0.406, (0.218, 0.596, 0.972), count=4)

    x, y = -0.130, -0.130
    deck = pallet(part, p["wood"], x, y, 0.75, 0.626)
    carton(part, p, x, y, deck, 0.68, 0.55, 0.535)

    x, y = -0.729, -1.235
    for dx in (-0.568, 0.568):
        part.box((x + dx, y, BASE + 0.001), (0.037, 1.033, 0.002), p["yellow"])
    for dy in (-0.498, 0.498):
        part.box((x, y + dy, BASE + 0.001), (1.100, 0.037, 0.002), p["yellow"])
    deck = pallet(part, p["wood"], x, y, 0.78, 0.68)
    for dx, dy, width, depth, height in (
        (-0.181, -0.151, 0.365, 0.295, 0.247), (0.148, -0.161, 0.279, 0.30, 0.205),
        (-0.170, 0.154, 0.351, 0.30, 0.270), (0.163, 0.159, 0.306, 0.311, 0.365),
    ):
        carton(part, p, x + dx, y + dy, deck, width, depth, height)
    carton(part, p, x - 0.160, y + 0.157, deck + 0.270, 0.356, 0.294, 0.225)

    for x in (DOOR_LEFT - 0.024, DOOR_RIGHT + 0.030):
        y = FRONT - 0.151
        for i in range(5):
            part.box((x, y, BASE + 0.066 + i * 0.063), (0.076, 0.077, 0.065),
                     p["yellow"] if i % 2 == 0 else p["dark"], edge=0.009, steps=2)
        part.box((x, y, BASE + 0.025), (0.093, 0.098, 0.038), p["yellow"],
                 edge=0.005, steps=1)
    pallet_jack(part, p, -0.238, -1.225)


def pallet_jack(part, p, x, y):
    for side in (-1, 1):
        fy = y + side * 0.119
        part.box((x - 0.19, fy, BASE + 0.044), (0.52, 0.054, 0.035), p["yellow"],
                 edge=0.007, steps=1)
        hy = y + side * 0.120
        part.tube([(x + 0.078, hy - 0.020, BASE + 0.058),
                   (x + 0.078, hy + 0.020, BASE + 0.058)],
                  0.056, p["dark"], sides=12, guide=(1, 0, 0))
        part.tube([(x + 0.078, hy + side * 0.020, BASE + 0.058),
                   (x + 0.078, hy + side * 0.024, BASE + 0.058)],
                  0.025, p["metal"], sides=10, guide=(1, 0, 0))
    part.box((x - 0.024, y, BASE + 0.078), (0.187, 0.305, 0.113), p["yellow"],
             edge=0.014, steps=2)
    part.tube([(x - 0.078, y, BASE + 0.104), (x + 0.014, y, BASE + 0.255)],
              0.067, p["yellow"], sides=10)
    part.tube([(x + 0.028, y, BASE + 0.137), (x + 0.11, y, BASE + 0.506)],
              0.029, p["dark"], sides=10)
    points = [(x + 0.101, y + dy, BASE + z) for dy, z in
              ((-0.010, 0.463), (-0.107, 0.524), (-0.122, 0.647), (-0.085, 0.691),
               (0.085, 0.691), (0.122, 0.647), (0.107, 0.524), (0.010, 0.463))]
    part.tube(points, 0.018, p["dark"], sides=7, guide=(1, 0, 0), closed=True)


def conveyor(static, p, center, length, width, *, turned=False):
    x, y = center

    def place(point):
        u, v, w = point
        return (x - v, y + u, BASE + w) if turned else (x + u, y + v, BASE + w)

    static.box((0, 0, ROLLER_HEIGHT - 0.052), (length - 0.044, width - 0.060, 0.018),
               p["dark"], transform=place)
    for sign in (-1, 1):
        side = sign * (width / 2 - 0.023)
        static.box((0, side, ROLLER_HEIGHT - 0.037), (length, 0.047, 0.100), p["green"],
                   edge=0.008, steps=2, transform=place)
        static.box((0, side, ROLLER_HEIGHT + 0.014), (length, 0.033, 0.026), p["metal"],
                   edge=0.006, steps=2, transform=place)
        for u in (-length / 2 + 0.082, 0, length / 2 - 0.082):
            static.box((u, side, 0.111), (0.045, 0.045, 0.214), p["green"],
                       edge=0.005, steps=1, transform=place)
            static.box((u, side, 0.012), (0.069, 0.064, 0.021), p["green"], transform=place)
    for u in (-length / 2 + 0.082, length / 2 - 0.082):
        static.box((u, 0, 0.061), (0.028, width - 0.039, 0.028), p["green"], transform=place)

    rollers = round((length - 0.08) / 0.078) + 1
    guide = (0, 1, 0) if turned else (1, 0, 0)
    for index in range(rollers):
        u = (index / (rollers - 1) - 0.5) * (length - 0.073)
        static.tube([place((u, v, ROLLER_HEIGHT)) for v in (-width / 2 + 0.037, width / 2 - 0.037)],
                    ROLLER_RADIUS, p["metal"], sides=12, guide=guide)


def interior_warmth(model, effects):
    vertices, faces, alphas = [], [], []
    offset = BASE + 0.004
    # Floor spill is exported as a feathered mesh and follows both open thresholds.
    for x, y, width, depth, peak in ((-0.30, -0.25, 1.85, 1.29, 0.23),
                                     (0.70, 0.52, 1.22, 1.20, 0.19)):
        start = len(vertices)
        steps = 24
        for scale, alpha in ((0.23, peak), (0.51, peak * 0.82), (0.76, peak * 0.35), (1, 0)):
            for i in range(steps):
                angle = common.TAU * i / steps
                vertices.append((x + width / 2 * scale * math.cos(angle),
                                 y + depth / 2 * scale * math.sin(angle), offset))
                alphas.append(alpha)
        faces.append(tuple(range(start, start + steps)))
        faces.extend(tuple(reversed(face)) for face in common.strip_faces(start, steps, 4))
    spill = common.MeshPart(model, WARM_FLOOR, origin=(0, 0, offset))
    common.gradient_surface(spill, effects, vertices, faces, "#FFC879", alphas)


def model_warehouse(model, effects):
    p = palette()
    static = common.MeshPart(model, "Warehouse_Static")
    building(static, p)
    cargo(static, p)
    for center, length, width, turned, _, _ in CONVEYORS:
        conveyor(static, p, center, length, width, turned=turned)
    z = ROLLER_HEIGHT + ROLLER_RADIUS
    carton(static, p, RIGHT - 0.055, CONVEYORS[1][0][1], z, 0.285, 0.253, 0.243)
    static.finish()
    for index, ((x, y), _, _, turned, offset, size) in enumerate(CONVEYORS, start=1):
        if turned:
            y += offset
        else:
            x += offset
        box = common.MeshPart(model, f"Conveyor_Box_{index}", origin=(x, y, BASE + z))
        carton(box, p, x, y, z, *size)
        box.finish()
    interior_warmth(model, effects)


result = common.build(
    "warehouse", model_warehouse,
    {"triangles": 30000, "bytes": 950000, "primitives": 28},
    direction=(0.87, -1.0, 0.407),
    frame=(0.025, 0.022, 0.973, 0.993),
    extra_effects=(WARM_FLOOR,),
    emissive_materials=(WARM_LIGHT,),
    required_parts=("Conveyor_Box_1", "Conveyor_Box_2", "Conveyor_Box_3"),
    studio_lights=(
        ("Warehouse Interior Front", (-0.065, -0.044, BASE + 1.47),
         (-0.40, 0.38, BASE + 0.21), 75, 0.78, "#FFD498"),
        ("Warehouse Interior Side", (0.52, 0.69, BASE + 1.46),
         (0.95, 0.38, BASE + 0.17), 54, 0.62, "#FFD08A"),
        ("Gable Lamp Spill", ((LEFT + RIGHT) / 2, FRONT - 0.18, BASE + 1.934),
         ((LEFT + RIGHT) / 2, FRONT, BASE + 1.677), 6, 0.17, "#FFD480"),
    ),
    review_features={
        "architecture": "Cream gable shed, sage standing-seam roof, open front and side roller doors.",
        "stock": "Shelving through both doors, a single large pallet load behind the front threshold, and a fully exposed exterior rack.",
        "conveyors": "Three separated paths with spaced silver rollers, three travelling cartons and a carton at the side threshold.",
        "presentation": "Front-right orthographic framing, neutral grey upper plinth and warm perimeter glow.",
    },
)
