"""Build the delivery truck and pickup lockers inside Blender."""

import math
import sys
from pathlib import Path
from types import ModuleType


SOURCE = Path(sys._getframe().f_code.co_filename).resolve().parent
common = ModuleType("commerce_hub_common")
common.__file__ = str(SOURCE / "common.py")
exec(compile(Path(common.__file__).read_text(), common.__file__, "exec"), vars(common))

BASE = common.PLINTH_HEIGHT
TRUCK_Y = -0.94
LOCKER_X, LOCKER_FRONT = 0.12, 0.95
LOCKER_WIDTH_SCALE = 0.945
LOCKER_HEIGHT_SCALE = 0.845
WHEEL_RADIUS = 0.223
WHEEL_LOCATIONS = {
    "FL": (0.53, TRUCK_Y + 0.434),
    "FR": (0.53, TRUCK_Y - 0.434),
    "RL": (-1.30, TRUCK_Y + 0.434),
    "RR": (-1.30, TRUCK_Y - 0.434),
}
WARM_LIGHT = "Delivery Warm Lamps"


def palette():
    paint = common.material
    return {
        "ivory": paint("Delivery Ivory", "#EEE8D8", roughness=0.50),
        "sage": paint("Locker Canopy Sage", "#73966A", roughness=0.42),
        "green": paint("Pomelo Deep Green", "#254C2C", roughness=0.55),
        "doors": paint("Locker Cream Yellow", "#EDBF70", roughness=0.55, specular=0.30),
        "yellow": paint("Pomelo Yellow", "#F6BA39", roughness=0.48),
        "light": paint(WARM_LIGHT, "#FFE4A6", emission="#FFCD64", strength=2.2),
        "dark": paint("Delivery Charcoal", "#373A35", roughness=0.58),
        "board": paint("Parcel Kraft", "#DCAB68", roughness=0.70),
        "tape": paint("Parcel Paper Tape", "#FFE4B1", roughness=0.58),
        "leaf": paint("Delivery Leaf Green", "#879F29", roughness=0.40),
        "leaf_dark": paint("Delivery Leaf Shade", "#567925", roughness=0.44),
        "cargo": paint("Truck Cargo Cream", "#F6D594", roughness=0.39),
        "cab": paint("Truck Cab Pale Sage", "#BBD1B5", roughness=0.34),
        "glass": paint("Truck Smoked Glass", "#4A585C", roughness=0.30, metallic=0.13),
        "hub": paint("Truck Satin Wheel Metal", "#B6B9B4", roughness=0.32, metallic=0.60),
    }


def citrus(part, u, v, relief, radius, paints, place):
    segments = 8
    for scale, offset, paint in ((1, 0, "green"), (0.91, 0.001, "ivory")):
        ring = [place((u + scale * radius * math.cos(common.TAU * i / 32),
                       v + scale * radius * math.sin(common.TAU * i / 32), relief + offset))
                for i in range(32)]
        part.add(ring, [tuple(range(32))], paints[paint])
    for wedge in range(segments):
        middle = common.TAU * (wedge + 0.5) / segments
        points = [place((u + 0.075 * radius * math.cos(middle),
                         v + 0.075 * radius * math.sin(middle), relief + 0.002))]
        for i in range(5):
            angle = common.TAU * (wedge + 0.055 + i * 0.89 / 4) / segments
            points.append(place((u + 0.82 * radius * math.cos(angle),
                                 v + 0.82 * radius * math.sin(angle), relief + 0.002)))
        part.add(points, [tuple(range(len(points)))], paints["green" if wedge in (0, 1) else "yellow"])


def package_icon(part, u, v, relief, radius, paint, place):
    outline = ((0, 1), (-0.84, 0.52), (-0.84, -0.51), (0, -1),
               (0.84, -0.51), (0.84, 0.52))

    def point(p):
        return place((u + p[0] * radius, v + p[1] * radius, relief))

    for a, b in (*zip(outline, outline[1:] + outline[:1]),
                 (outline[1], (0, 0.02)), (outline[5], (0, 0.02)), (outline[3], (0, 0.02))):
        part.tube([point(a), point(b)], radius * 0.073, paint, sides=5, guide=(0, 1, 0))


def truck_position(point):
    x, y, z = point
    return (-0.245 + (x + 0.34) * 1.085, TRUCK_Y - 0.19 + (y - TRUCK_Y) * 1.10,
            BASE + (z - BASE) * 1.085)


def finish_truck_part(part):
    part.vertices = [truck_position(point) for point in part.vertices]
    part.finish()


def truck_body(model, p):
    truck = common.MeshPart(model, "Truck_Body", origin=truck_position((-0.34, TRUCK_Y, BASE)))
    cargo_z = BASE + 0.953
    truck.box((-1.013, TRUCK_Y, cargo_z), (1.74, 1.078, 1.036), p["cargo"],
              edge=0.053, corner=0.067, steps=4, bevel_steps=3)
    truck.box((-0.40, TRUCK_Y, BASE + 0.315), (2.44, 0.71, 0.19), p["dark"],
              edge=0.032, steps=2)
    truck.box((-0.50, TRUCK_Y - 0.347, BASE + 0.27), (0.53, 0.14, 0.19), p["dark"],
              edge=0.021, steps=2)
    truck.box((-1.816, TRUCK_Y, BASE + 0.31), (0.115, 0.96, 0.139), p["dark"],
              edge=0.022, steps=2)
    for side in (-1, 1):
        truck.box((-1.844, TRUCK_Y + side * 0.37, BASE + 0.336),
                  (0.061, 0.115, 0.083), p["yellow"], edge=0.012, steps=1)

        def cargo_face(point):
            u, v, relief = point
            return (-side * u, TRUCK_Y + side * (0.539 + relief), v)

        # Thin relief on the broad cargo sides keeps the brand legible without textures.
        center = side * 1.013
        truck.box((center, cargo_z, 0.002), (1.58, 0.89, 0.016),
                  p["cargo"], edge=0.004, corner=0.026, steps=3, transform=cargo_face)
        citrus(truck, center - 0.49, BASE + 1.10, 0.012, 0.166, p, cargo_face)
        common.geometry_text(truck, "POMELO STEM", (center + 0.24, BASE + 1.12, 0.013),
                             0.88, 0.110, p["green"], cargo_face, weight=0.024)
        common.geometry_text(truck, "Delivery", (center + 0.036, BASE + 0.98, 0.013),
                             0.46, 0.110, p["green"], cargo_face, weight=0.022)
        truck.box((center + 0.036, BASE + 0.908, 0.014), (0.40, 0.009, 0.004), p["green"],
                  transform=cargo_face)
        for stripe, paint in ((0, "green"), (0.099, "cab")):
            vertices = []
            for i in range(13):
                t = i / 12
                u = center - 0.72 + t * (1.11 + stripe)
                v = BASE + 0.735 + stripe - 0.19 * t * t
                half = (0.039 - stripe * 0.08) * (1 - 0.98 * t)
                vertices.extend((cargo_face((u, v - half, 0.012)),
                                 cargo_face((u, v + half, 0.012))))
            truck.add(vertices, [(i, i + 2, i + 3, i + 1) for i in range(0, 24, 2)], p[paint])

    # The cab's sloping upper nose carries the windshield. Its wide lower lip wraps the fenders.
    levels = (
        (0.205, -0.19, 0.800, 0.773, 0.065), (0.245, -0.19, 0.888, 0.816, 0.080),
        (0.48, -0.19, 0.901, 0.948, 0.086), (0.61, -0.19, 0.886, 0.944, 0.092),
        (1.075, -0.18, 0.627, 0.890, 0.083), (1.142, -0.14, 0.553, 0.838, 0.074),
        (1.157, -0.105, 0.512, 0.771, 0.067),
    )
    truck.loft([[(cx + (rear + nose) / 2, TRUCK_Y + cy, BASE + h)
                 for cx, cy in common.rounded_rect(nose - rear, width, radius, 4)]
                for h, rear, nose, width, radius in levels], p["cab"])

    def windshield(point):
        u, v, relief = point
        return (0.886 - (v - 0.61) * (0.259 / 0.465) + relief, TRUCK_Y + u, BASE + v)

    truck.box((0, 0.853, 0.004), (0.754, 0.378, 0.020), p["dark"], edge=0.006,
              corner=0.043, steps=3, transform=windshield)
    truck.box((0, 0.853, 0.017), (0.716, 0.345, 0.014), p["glass"], edge=0.004,
              corner=0.030, steps=3, transform=windshield)
    for side in (-1, 1):
        def door_face(point):
            u, v, relief = point
            half_width = 0.472 - (v - 0.61) * (0.027 / 0.465)
            return (side * u, TRUCK_Y - side * (half_width + relief), BASE + v)

        for inset, paint in ((0, "dark"), (0.027, "glass")):
            profile = [(-0.098 + inset, 0.664 + inset),
                       (0.614 - inset, 0.664 + inset),
                       (0.462 - inset, 1.056 - inset),
                       (-0.098 + inset, 1.056 - inset)]
            if side == -1:
                profile = [(-u, v) for u, v in reversed(profile)]
            truck.add([door_face((u, v, 0.008 + inset / 4)) for u, v in profile],
                      [(0, 1, 2, 3)], p[paint])
        truck.box((-side * 0.038, 0.568, 0.008), (0.115, 0.035, 0.016), p["dark"],
                  edge=0.005, steps=1, transform=door_face)
        mirror_y = TRUCK_Y + side * 0.565
        truck.tube([(0.585, TRUCK_Y + side * 0.434, BASE + 0.677),
                    (0.615, mirror_y, BASE + 0.656),
                    (0.638, mirror_y, BASE + 0.806)],
                   0.020, p["dark"], sides=8, guide=(1, 0, 0))
        truck.box((0.638, mirror_y, BASE + 0.806), (0.099, 0.082, 0.184), p["dark"],
                  edge=0.016, steps=2)
        truck.box((0.589, mirror_y, BASE + 0.806), (0.013, 0.060, 0.144), p["glass"],
                  edge=0.011, steps=2)
        for a, b, radius in (((side * 0.066, 0.690), (side * 0.202, 0.741), 0.006),
                             ((side * 0.103, 0.717), (side * 0.297, 0.781), 0.009)):
            truck.tube([windshield((*a, 0.031)), windshield((*b, 0.031))],
                       radius, p["dark"], sides=5, guide=(1, 0, 0))

    truck.box((0.854, TRUCK_Y, BASE + 0.253), (0.161, 0.975, 0.141), p["dark"],
              edge=0.026, steps=3)
    for z in (0.404, 0.477):
        truck.box((0.893, TRUCK_Y, BASE + z), (0.037, 0.445, 0.034), p["dark"],
                  edge=0.008, steps=2)
    truck.box((0.932, TRUCK_Y, BASE + 0.255), (0.016, 0.205, 0.053), p["dark"],
              edge=0.004, steps=1)
    for side in (-1, 1):
        y = TRUCK_Y + side * 0.356
        truck.box((0.894, y, BASE + 0.397), (0.042, 0.19, 0.139), p["yellow"],
                  edge=0.012, steps=2)
        truck.box((0.918, y, BASE + 0.401), (0.015, 0.142, 0.095), p["ivory"],
                  edge=0.004, steps=2)
    finish_truck_part(truck)


def wheels(model, p):
    for suffix, (x, y) in WHEEL_LOCATIONS.items():
        z = BASE + WHEEL_RADIUS
        wheel = common.MeshPart(model, f"Truck_Wheel_{suffix}", origin=truck_position((x, y, z)))

        def revolve(profile, paint):
            # The +Y axle and hub-centred pivot are shared by all four wheels.
            sides = 20
            rings = [[(x + r * math.cos(common.TAU * i / sides), y + offset,
                       z - r * math.sin(common.TAU * i / sides)) for i in range(sides)]
                     for r, offset in profile]
            wheel.loft(rings, paint)

        revolve([(0.171, -0.099), (0.198, -0.091), (0.216, -0.075), (WHEEL_RADIUS, -0.048),
                 (WHEEL_RADIUS, 0.048), (0.216, 0.075), (0.198, 0.091), (0.171, 0.099)], p["dark"])
        revolve([(0.099, -0.112), (0.136, -0.112), (0.153, -0.104), (0.157, -0.093),
                 (0.157, 0.093), (0.153, 0.104), (0.136, 0.112), (0.099, 0.112)], p["hub"])
        revolve([(0.055, -0.116), (0.082, -0.117), (0.087, -0.113), (0.087, 0.113),
                 (0.082, 0.117), (0.055, 0.116)], p["dark"])
        finish_truck_part(wheel)


def lockers(part, p):
    first_vertex = len(part.vertices)
    center_x, front, depth = LOCKER_X, LOCKER_FRONT, 0.86
    width, height = 3.19, 1.95
    right_x = center_x + width / 2
    part.box((center_x, front + depth / 2, BASE + height / 2), (width, depth, height),
             p["ivory"], edge=0.036, steps=3, bevel_steps=2)
    part.box((center_x, front + depth / 2, BASE + 0.042), (width + 0.03, depth + 0.03, 0.084),
             p["sage"], edge=0.016, steps=2)
    part.box((center_x, front + depth / 2 - 0.017, BASE + height + 0.036),
             (width + 0.21, depth + 0.23, 0.145), p["sage"], edge=0.031, steps=4, bevel_steps=2)
    part.box((center_x, front + depth / 2, BASE + height + 0.111),
             (width + 0.16, depth + 0.17, 0.057), p["sage"], edge=0.018, steps=4)

    for bank in (center_x - 0.92, center_x + 0.92):
        part.box((bank, front - 0.021, BASE + 0.962), (1.249, 0.058, 1.769),
                 p["green"], edge=0.010, steps=2)
        for dx in (-0.307, 0.307):
            for bottom, top in zip(
                    (0.094, 0.407, 0.720, 1.033, 1.346, 1.563),
                    (0.407, 0.720, 1.033, 1.346, 1.563, 1.814), strict=True):
                part.box((bank + dx, front - 0.063, BASE + (bottom + top) / 2),
                         (0.594, 0.044, top - bottom - 0.025), p["doors"],
                         edge=0.006, steps=2)
        part.box((bank, front - 0.080, BASE + 1.870), (1.047, 0.123, 0.047),
                 p["sage"], edge=0.010, steps=2)
        part.box((bank, front - 0.119, BASE + 1.856), (0.982, 0.046, 0.022),
                 p["light"], edge=0.005, steps=2)

    part.box((center_x, front - 0.043, BASE + 0.981), (0.65, 0.105, 1.820),
             p["sage"], edge=0.018, steps=3)
    part.box((center_x, front - 0.099, BASE + 0.978), (0.589, 0.026, 1.746),
             p["ivory"], edge=0.011, steps=2)
    for z, h in ((0.322, 0.438), (1.655, 0.237)):
        part.box((center_x, front - 0.120, BASE + z), (0.494, 0.032, h),
                 p["ivory"], edge=0.008, corner=0.019, steps=2)
    angle = math.radians(15)

    def screen(point):
        u, v, relief = point
        return (center_x + u, front - 0.133 + v * math.sin(angle) - relief * math.cos(angle),
                BASE + 1.118 + v * math.cos(angle) + relief * math.sin(angle))

    part.box((0, 0, 0), (0.476, 0.556, 0.091), p["sage"], edge=0.021, steps=3,
             transform=screen)
    part.box((0, 0.035, 0.055), (0.392, 0.418, 0.047), p["green"], edge=0.013,
             steps=2, transform=screen)
    part.box((0, 0.035, 0.082), (0.329, 0.351, 0.010), p["doors"], edge=0.003,
             steps=2, transform=screen)
    package_icon(part, 0, 0.047, 0.091, 0.102, p["ivory"], screen)
    part.box((-0.101, -0.225, 0.046), (0.082, 0.056, 0.010), p["dark"],
             edge=0.002, steps=1, transform=screen)

    sign_y = front + 0.24
    sign_z = BASE + 2.256

    def sign_face(point):
        u, v, relief = point
        return (center_x + u, sign_y - relief, sign_z + v)

    part.box((0, -0.003, 0), (1.894, 0.410, 0.135), p["green"], edge=0.033,
             corner=0.072, steps=4, bevel_steps=2, transform=sign_face)
    package_icon(part, -0.648, 0.002, 0.074, 0.113, p["ivory"], sign_face)
    common.geometry_text(part, "Pickup Locker", (0.143, 0.002, 0.071), 1.245, 0.174, p["ivory"],
                         sign_face, weight=0.013)

    def side_face(point):
        u, v, relief = point
        return (right_x + relief, front + depth / 2 + u, BASE + v)

    citrus(part, 0.04, 1.454, 0.005, 0.171, p, side_face)
    common.geometry_text(part, "POMELO", (0.04, 1.165, 0.006), 0.520, 0.110, p["green"],
                         side_face, weight=0.024)
    common.geometry_text(part, "STEM", (0.04, 1.019, 0.006), 0.345, 0.108, p["green"],
                         side_face, weight=0.024)
    mount = (right_x + 0.009, front + depth * 0.71, BASE + 1.665)
    part.box(mount, (0.045, 0.075, 0.107), p["dark"], edge=0.008, steps=2)
    pivot = (right_x + 0.134, mount[1] - 0.018, mount[2] + 0.027)
    part.tube([mount, pivot], 0.031, p["dark"], sides=8, guide=(0, 0, 1))
    tail = (pivot[0] - 0.019, pivot[1] + 0.119, pivot[2] + 0.077)
    lens = (pivot[0] + 0.021, pivot[1] - 0.114, pivot[2] + 0.036)
    part.tube([tail, lens], 0.059, p["ivory"], sides=12, guide=(0, 0, 1))
    face = (lens[0] + 0.002, lens[1] - 0.012, lens[2] - 0.002)
    part.tube([lens, face], 0.041, p["dark"], sides=12, guide=(0, 0, 1))
    part.tube([face, (face[0] + 0.001, face[1] - 0.004, face[2] - 0.001)],
              0.021, p["ivory"], sides=10, guide=(0, 0, 1))
    part.vertices[first_vertex:] = [
        (center_x + (x - center_x) * LOCKER_WIDTH_SCALE, y,
         BASE + (z - BASE) * LOCKER_HEIGHT_SCALE)
        for x, y, z in part.vertices[first_vertex:]
    ]


def planter(part, p):
    x, y = 1.80, 1.23
    part.lathe((x, y, BASE), [(0.124, 0), (0.150, 0.023), (0.187, 0.272),
                             (0.185, 0.295), (0.169, 0.299), (0.157, 0.255)],
               p["ivory"], sides=20)
    part.lathe((x, y, BASE + 0.248), [(0.151, 0), (0.163, 0.012)], p["dark"], sides=20)
    root = common.Vector((x, y, BASE + 0.259))
    for index, (azimuth, length, height, width) in enumerate((
        (10, 0.34, 0.37, 0.087), (56, 0.39, 0.56, 0.090), (84, 0.26, 0.59, 0.092),
        (204, 0.16, 0.52, 0.090), (241, 0.32, 0.37, 0.093), (264, 0.32, 0.23, 0.086),
        (298, 0.34, 0.26, 0.091), (342, 0.30, 0.21, 0.073), (114, 0.19, 0.35, 0.087),
    )):
        angle = math.radians(azimuth)
        direction = common.Vector((math.cos(angle), math.sin(angle), 0))
        cross = common.Vector((-direction.y, direction.x, 0))
        up = common.Vector((0, 0, 1))
        stem = root + direction * (length * 0.24) + up * (height * 0.49)
        part.tube([root, root.lerp(stem, 0.5), stem], 0.008, p["leaf_dark"], sides=5,
                  guide=(1, 0, 0))
        tip = root + direction * length + up * height
        points = [tuple(stem)]
        for t in (0.20, 0.41, 0.64, 0.83):
            bulge = math.sin(math.pi * t)
            mid = stem.lerp(tip, t) + up * (0.084 * bulge)
            edge = 1.25 * width * bulge ** 0.72
            points.extend((tuple(mid - cross * edge - up * (0.025 * bulge)), tuple(mid),
                           tuple(mid + cross * edge - up * (0.025 * bulge))))
        points.append(tuple(tip))
        faces = [(0, 1, 2), (0, 2, 3)]
        for i in (1, 4, 7):
            faces.extend(((i, i + 3, i + 4, i + 1), (i + 1, i + 4, i + 5, i + 2)))
        faces.extend(((10, 13, 11), (11, 13, 12)))
        part.add(points, faces, p["leaf_dark" if index in (1, 5, 7) else "leaf"], smooth=True)


def model_delivery(model, _effects):
    p = palette()
    static = common.MeshPart(model, "Delivery_Static")
    lockers(static, p)
    line_z = BASE + 0.001
    for x in (-1.78, 1.27):
        static.box((x, -1.03, line_z), (0.052, 1.35, 0.002), p["ivory"])
    static.box((0.984, -1.68, line_z), (0.60, 0.052, 0.002), p["ivory"])
    common.carton(static, (1.61, 0.32, BASE), (0.60, 0.54, 0.375),
                  p["board"], p["tape"], p["dark"])
    common.carton(static, (1.61, 0.355, BASE + 0.375), (0.435, 0.410, 0.305),
                  p["board"], p["tape"], p["dark"])
    planter(static, p)
    static.finish()
    truck_body(model, p)
    wheels(model, p)


result = common.build(
    "delivery", model_delivery,
    {"triangles": 20000, "bytes": 650000, "primitives": 30},
    direction=(0.82, -1.0, 0.42),
    frame=(0.039, 0.062, 0.952, 0.972),
    emissive_materials=(WARM_LIGHT,),
    required_parts=("Truck_Body", *(f"Truck_Wheel_{suffix}" for suffix in WHEEL_LOCATIONS)),
    studio_lights=(
        ("Locker Left Spill", (LOCKER_X - 0.92, LOCKER_FRONT - 0.16, BASE + 1.55),
         (LOCKER_X - 0.92, LOCKER_FRONT - 0.05, BASE + 1.25), 4, 0.64, "#FFCD82"),
        ("Locker Right Spill", (LOCKER_X + 0.92, LOCKER_FRONT - 0.16, BASE + 1.55),
         (LOCKER_X + 0.92, LOCKER_FRONT - 0.05, BASE + 1.25), 4, 0.64, "#FFCD82"),
    ),
    review_features={
        "layout": "Left foreground box truck, two-bank locker at the back and parcels and plant at right.",
        "details": "Handle-free cream-yellow doors with visible seams, two warm locker strips, citrus branding, and detailed cab.",
        "motion": "Independent truck body and four hub-centred wheels with local +Y axle.",
        "presentation": "Front-right orthographic view, neutral grey upper plinth and warm perimeter glow.",
    },
)
