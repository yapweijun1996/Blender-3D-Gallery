"""Build the glazed Pomelo Store miniature from local Blender geometry."""

import math
import sys
from pathlib import Path
from types import ModuleType


SOURCE = Path(sys._getframe().f_code.co_filename).resolve().parent
common = ModuleType("commerce_hub_common")
common.__file__ = str(SOURCE / "common.py")
exec(compile(Path(common.__file__).read_text(), common.__file__, "exec"), vars(common))

BASE = common.PLINTH_HEIGHT
LEFT, RIGHT = -1.89, 1.89
FRONT, BACK = -1.03, 1.32
CEILING = BASE + 1.81
DOOR_LEFT, DOOR_RIGHT = -0.34, 0.50
DOOR_TOP = BASE + 1.49
VIEW_DIRECTION = (-0.68, -1.0, 0.412)


def shop_palette():
    return {
        "ivory": common.material("Porcelain Trim", "#EEECE0", roughness=0.37),
        "roof": common.material("Recessed Roof Grey", "#C2C8C6", roughness=0.52),
        "sage": common.material("Sage Cornice", "#538A57", roughness=0.33),
        "frame": common.material("Glazing Mullions", "#577261", roughness=0.34),
        "glass": common.material("Shop Glass", "#E3F1E8", roughness=0.16, alpha=0.07),
        "tile": common.material("Warm Ivory Tile", "#E5C8A2", roughness=0.54,
                                emission="#FFC17C", strength=0.24),
        "grout": common.material("Warm Tile Joints", "#CFAC84", roughness=0.70,
                                 emission="#EDB079", strength=0.13),
        "wood": common.material("Honey Maple", "#D3A269", roughness=0.50,
                                emission="#FFC078", strength=0.25),
        "cream": common.material("Vanilla Ceramic and Paper", "#FFF0CC", roughness=0.31),
        "green": common.material("Fern Ceramic and Paper", "#66834D", roughness=0.34),
        "kraft": common.material("Pomelo Yellow Paper", "#F6B752", roughness=0.51),
        "citrus": common.material("Pomelo Orange", "#F69524", roughness=0.50),
        "brass": common.material("Satin Brass", "#D6A45C", roughness=0.32, metallic=0.52),
        "light": common.material("Warm Pendant Glass", "#FFEBB4", roughness=0.28,
                                 emission="#FFE3A1", strength=1.43),
        "leaf": common.material("Leaf Green", "#376C27", roughness=0.38),
        "leaf_light": common.material("Leaf New Growth", "#669629", roughness=0.38),
        "vine": common.material("Vine Green", "#69921C", roughness=0.42),
        "vine_light": common.material("Vine New Growth", "#9EBD2C", roughness=0.41),
        "soil": common.material("Potting Soil", "#6B5030", roughness=0.85),
        "board": common.material("Pomelo Sign Green", "#4F7754", roughness=0.52),
    }


def shell(model, paints):
    part = common.MeshPart(model, "Shop_Shell")
    midpoint = (FRONT + BACK) / 2
    width = RIGHT - LEFT
    depth = BACK - FRONT
    part.box((0, midpoint, BASE + 0.037), (width, depth, 0.074), paints["grout"])
    for column in range(7):
        for row in range(6):
            w, d = (width - 0.025) / 7, (depth - 0.025) / 6
            x = LEFT + 0.0125 + w * (column + 0.5)
            y = FRONT + 0.0125 + d * (row + 0.5)
            part.box((x, y, BASE + 0.079), (w - 0.006, d - 0.006, 0.013), paints["tile"])
    height = CEILING - BASE
    for center, size in (
        ((0, BACK - 0.044, BASE + height / 2), (width, 0.084, height)),
        ((RIGHT - 0.043, midpoint, BASE + height / 2), (0.088, depth, height)),
    ):
        # The inside walls share the warm tile material and its existing primitive.
        part.box(center, size, paints["tile"], edge=0.014, steps=1)
    part.finish()

    roof = common.MeshPart(model, "Shop_Roof")
    roof.box((0, midpoint, CEILING + 0.080), (width + 0.18, depth + 0.11, 0.160),
             paints["ivory"], edge=0.016, bevel_steps=2)
    roof.box((0, midpoint, CEILING + 0.221), (width + 0.34, depth + 0.25, 0.150),
             paints["sage"], edge=0.024, bevel_steps=2)
    roof.box((0, midpoint, CEILING + 0.332), (width + 0.20, depth + 0.13, 0.080),
             paints["roof"], edge=0.018)
    # Join the four parapet sides into a continuous coping without corner seams.
    w, d, thickness = width + 0.21, depth + 0.14, 0.105
    z0, z1 = CEILING + 0.289, CEILING + 0.600
    vertices = [
        (x, midpoint + y, level)
        for level, inset in ((z0, 0), (z1 - 0.014, 0), (z1, 0.012),
                             (z1, thickness - 0.012), (z1 - 0.014, thickness),
                             (z0, thickness))
        for x, y in common.rounded_rect(w - 2 * inset, d - 2 * inset, 0.13 - inset, 5)
    ]
    span = len(vertices) // 6
    faces = [
        (layer * span + i, layer * span + (i + 1) % span,
         ((layer + 1) % 6) * span + (i + 1) % span, ((layer + 1) % 6) * span + i)
        for layer in range(6)
        for i in range(span)
    ]
    roof.add(vertices, faces, paints["ivory"])

    vent_x, vent_y, vent_z = -0.98, 0.18, CEILING + 0.371
    vent_height = 0.204
    roof.box((vent_x, vent_y, vent_z + vent_height / 2), (0.84, 0.70, vent_height), paints["sage"],
             edge=0.043, bevel_steps=3)
    grille_z = vent_z + vent_height - 0.004
    roof.lathe((vent_x, vent_y, grille_z),
               [(0.253, 0), (0.244, 0.018), (0.210, 0.020), (0.197, 0.004)],
               paints["frame"], sides=30, caps=(False, False))
    roof.lathe((vent_x, vent_y, grille_z),
               [(0.201, 0), (0.201, 0.010)], paints["frame"], sides=30)
    for i in range(-3, 4):
        offset = i * 0.048
        length = 2 * math.sqrt(0.188 ** 2 - offset ** 2)
        roof.box((vent_x, vent_y + offset, grille_z + 0.012), (length, 0.018, 0.009),
                 paints["sage"])
    roof.finish()


def glass_panel(part, a, b, low, high, paint):
    part.add([(a[0], a[1], low), (b[0], b[1], low),
              (b[0], b[1], high), (a[0], a[1], high)],
             [(0, 1, 2, 3)], paint)


def storefront(model, paints):
    frame = common.MeshPart(model, "Shop_Glazing_Frame")
    glass = common.MeshPart(model, "Shop_Glass")
    zlo, zhi = BASE + 0.145, CEILING - 0.028
    for x in (LEFT, -0.92, DOOR_LEFT, DOOR_RIGHT, RIGHT):
        frame.box((x, FRONT, (zlo + zhi) / 2), (0.061, 0.068, zhi - zlo + 0.10),
                  paints["frame"], edge=0.008, steps=1)
    for y in (0.20, BACK):
        frame.box((LEFT, y, (zlo + zhi) / 2), (0.068, 0.061, zhi - zlo + 0.10),
                  paints["frame"], edge=0.008, steps=1)

    for first, last in ((LEFT, DOOR_LEFT), (DOOR_RIGHT, RIGHT)):
        frame.box(((first + last) / 2, FRONT, BASE + 0.085),
                  (last - first, 0.112, 0.17), paints["sage"], edge=0.013)
    frame.box((LEFT, (FRONT + BACK) / 2, BASE + 0.085),
              (0.112, BACK - FRONT, 0.17), paints["sage"], edge=0.013)
    frame.box((0, FRONT, zhi), (RIGHT - LEFT, 0.058, 0.045), paints["frame"])
    frame.box((LEFT, (FRONT + BACK) / 2, zhi),
              (0.058, BACK - FRONT, 0.045), paints["frame"])
    frame.box(((DOOR_LEFT + DOOR_RIGHT) / 2, FRONT, DOOR_TOP),
              (DOOR_RIGHT - DOOR_LEFT, 0.068, 0.064), paints["frame"], edge=0.007)
    frame.box(((DOOR_LEFT + DOOR_RIGHT) / 2, FRONT, BASE + 0.024),
              (DOOR_RIGHT - DOOR_LEFT, 0.18, 0.042), paints["brass"], edge=0.006)
    frame.finish()

    for first, last in ((LEFT, -0.92), (-0.92, DOOR_LEFT), (DOOR_RIGHT, RIGHT)):
        glass_panel(glass, (first + 0.024, FRONT), (last - 0.024, FRONT), zlo, zhi,
                    paints["glass"])
    for first, last in ((FRONT, 0.20), (0.20, BACK)):
        glass_panel(glass, (LEFT, last - 0.024), (LEFT, first + 0.024), zlo, zhi,
                    paints["glass"])
    glass_panel(glass, (DOOR_LEFT + 0.027, FRONT), (DOOR_RIGHT - 0.027, FRONT),
                DOOR_TOP + 0.028, zhi, paints["glass"])
    glass.finish()

    middle = (DOOR_LEFT + DOOR_RIGHT) / 2
    for name, first, last, hinge, handle in (
        ("Shop_Door", DOOR_LEFT + 0.034, middle - 0.009, DOOR_LEFT, middle - 0.065),
        ("Shop_Door_Right", middle + 0.009, DOOR_RIGHT - 0.034, DOOR_RIGHT, middle + 0.065),
    ):
        foot, head = BASE + 0.046, DOOR_TOP - 0.045
        door = common.MeshPart(model, name, origin=(hinge, FRONT, foot))
        for x in (first + 0.015, last - 0.015):
            door.box((x, FRONT, (head + foot) / 2), (0.03, 0.041, head - foot),
                     paints["frame"], edge=0.004, steps=1)
        for z in (foot + 0.015, head - 0.015):
            door.box(((first + last) / 2, FRONT, z), (last - first - 0.054, 0.041, 0.034),
                     paints["frame"], edge=0.004, steps=1)
        glass_panel(door, (first + 0.025, FRONT), (last - 0.025, FRONT), foot + 0.028,
                    head - 0.028, paints["glass"])
        for side in (-1, 1):
            door.tube([(handle, FRONT + side * 0.010, BASE + 0.48),
                       (handle, FRONT + side * 0.067, BASE + 0.48),
                       (handle, FRONT + side * 0.071, BASE + 0.515),
                       (handle, FRONT + side * 0.071, BASE + 0.77),
                       (handle, FRONT + side * 0.067, BASE + 0.805),
                       (handle, FRONT + side * 0.010, BASE + 0.805)],
                      0.014, paints["brass"], guide=(1, 0, 0))
        door.finish()


def mug(part, x, y, z, paint, scale=1):
    profile = [(0.060, 0), (0.071, 0.009), (0.078, 0.123), (0.077, 0.135),
               (0.066, 0.135), (0.064, 0.121), (0.054, 0.021)]
    part.lathe((x, y, z), [(r * scale, h * scale) for r, h in profile], paint, sides=14)
    part.tube([(x + scale * (0.071 + 0.044 * math.sin(t)), y,
                z + scale * (0.073 + 0.037 * math.cos(t)))
               for t in (math.pi * i / 10 for i in range(11))],
              0.010 * scale, paint, sides=6)


def pomelo(part, x, y, radius, z, paints, place):
    # The pith and segment shapes are separate meshes sharing the same relief plane.
    count = 32
    outline = [place((x, y, z)), *[
        place((x + radius * math.cos(common.TAU * i / count),
               y + radius * math.sin(common.TAU * i / count), z)) for i in range(count)]]
    part.add(outline, [(0, i + 1, (i + 1) % count + 1) for i in range(count)], paints["cream"])
    for j in range(8):
        angles = [common.TAU / 8 * (j + 0.046 + i * 0.908 / 4) for i in range(5)]
        wedge = [place((x + 0.0017 * math.cos(angles[2]),
                        y + 0.0017 * math.sin(angles[2]), z + 0.001))]
        wedge.extend(place((x + radius * 0.88 * math.cos(t), y + radius * 0.88 * math.sin(t),
                            z + 0.001)) for t in angles)
        part.add(wedge, [tuple(range(len(wedge)))], paints["citrus"])


def merchandise_box(part, x, y, z, size, color, paints, decoration):
    part.box((x, y, z + size / 2), (size, size * 0.86, size), paints[color], edge=0.010, steps=1)
    if decoration == "ribbon":
        part.box((x + size * 0.16, y - size * 0.431, z + size * 0.5),
                 (size * 0.15, 0.003, size * 0.99), paints["kraft"])
        part.box((x + size * 0.16, y, z + size * 1.002),
                 (size * 0.15, size * 0.87, 0.004), paints["kraft"])
    elif decoration == "pomelo":
        def place(point):
            horizontal, vertical, relief = point
            return (x + horizontal, y - size * 0.43 - relief, z + size * 0.52 + vertical)

        pomelo(part, 0, 0, size * 0.23, 0.002, paints, place)


def pendant_halo(model, effects, center):
    # Two crossed, feathered discs keep the halo visible as the module turns.
    part = common.MeshPart(model, "Fx_PendantHalo", origin=center)
    sight_x, sight_y, _ = VIEW_DIRECTION
    face_angle = math.atan2(sight_x, -sight_y)
    stops = ((0.10, 0.41), (0.15, 0.35), (0.205, 0.22),
             (0.275, 0.11), (0.355, 0.035), (0.43, 0))
    count = 24
    x, y, z = center
    angles = [common.TAU * i / count for i in range(count)]
    vertices, faces, alphas = [], [], []
    for angle in (face_angle, face_angle + math.pi / 2):
        u, v = math.cos(angle), math.sin(angle)
        start = len(vertices)
        vertices.append(center)
        alphas.append(0.43)
        for radius, alpha in stops:
            vertices.extend((x + u * radius * math.cos(t), y + v * radius * math.cos(t),
                             z + radius * math.sin(t)) for t in angles)
            alphas.extend([alpha] * count)
        faces.extend((start, start + 1 + i, start + 1 + (i + 1) % count)
                     for i in range(count))
        faces.extend(common.strip_faces(start + 1, count, len(stops)))
    common.gradient_surface(part, effects, vertices, faces, "#FFDB87", alphas)


def interior(model, effects, paints):
    wood = common.MeshPart(model, "Shop_Shelving")
    stock = common.MeshPart(model, "Shop_Merchandise")
    levels = (BASE + 0.20, BASE + 0.70, BASE + 1.20)
    lower, middle, upper = (level + 0.035 for level in levels)
    racks = ((-1.26, 1.05, 1.02, 0.44), (-0.23, 1.05, 0.88, 0.44),
             (1.28, 0.93, 0.94, 0.43), (1.38, -0.23, 0.89, 0.37))
    for x, y, width, depth in racks:
        wood.box((x, y + depth / 2 - 0.024, BASE + 0.87),
                 (width, 0.045, 1.48), paints["wood"],
                 edge=0.012, steps=1)
        for level in levels:
            wood.box((x, y, level), (width, depth, 0.070), paints["wood"], edge=0.014)
        for j in range(3):
            offset = (j - 1) * width * 0.30
            merchandise_box(stock, x + offset, y - 0.065, lower, width * 0.27,
                            "cream" if j != 1 else "kraft", paints,
                            "pomelo" if j != 1 else "ribbon")
            mug(stock, x + offset, y - 0.080, middle,
                paints["green" if j != 1 else "cream"], 1.21 + 0.06 * j)
            if j == 1:
                merchandise_box(stock, x + offset, y - 0.050, upper, width * 0.26,
                                "green", paints, "ribbon")
            elif j == 2 and x > 0:
                merchandise_box(stock, x + offset, y - 0.058, upper, width * 0.27,
                                "cream", paints, "pomelo")
            else:
                mug(stock, x + offset, y - 0.075, upper, paints["cream"], 1.17)

    deck = BASE + 0.21
    for x, y, w, d in ((-1.12, -0.65, 1.36, 0.60), (1.34, -0.73, 0.93, 0.48)):
        wood.box((x, y, deck - 0.061), (w, d, 0.122), paints["wood"],
                 edge=0.024, bevel_steps=2)
        for off, height in ((-w * 0.24, 0.25), (w * 0.23, 0.15)):
            stock.box((x + off, y + d * 0.19, deck + height / 2),
                      (w * 0.37, d * 0.48, height), paints["cream"], edge=0.016)
            mug(stock, x + off, y + d * 0.19, deck + height,
                paints["green" if height > 0.2 else "cream"], 1.30)
        merchandise_box(stock, x - w * 0.07, y - d * 0.30, deck, 0.19, "green", paints, "ribbon")
        mug(stock, x + w * 0.34, y - d * 0.30, deck, paints["cream"], 1.12)
    side_display = BASE + 0.485
    wood.box((-1.55, 0.48, side_display - 0.20), (0.55, 0.58, 0.40),
             paints["wood"], edge=0.025)
    merchandise_box(stock, -1.64, 0.42, side_display, 0.24, "cream", paints, "pomelo")
    mug(stock, -1.44, 0.61, side_display, paints["green"], 1.17)
    wood.finish()
    stock.finish()

    fixture = common.MeshPart(model, "Shop_Pendant")
    x, y, shade = -0.86, -0.32, BASE + 1.04
    fixture.lathe((x, y, shade + 0.15), [(0.013, 0), (0.013, CEILING - shade - 0.15)],
                  paints["brass"])
    fixture.lathe((x, y, shade + 0.10), [(0.079, 0), (0.057, 0.051), (0.035, 0.076)],
                  paints["ivory"])
    fixture.lathe((x, y, shade), [(0.058, 0), (0.128, 0.016), (0.149, 0.044),
                                   (0.131, 0.075), (0.079, 0.111)],
                  paints["light"], sides=24)
    for offset in (-1.26, 1.40):
        fixture.box((offset, -0.48, CEILING - 0.006),
                    (0.78, 0.036, 0.017), paints["light"], edge=0.004)
    fixture.finish()
    pendant_halo(model, effects, (x, y, shade + 0.041))


def leaflet(part, start, tip, width, rise, paints, colors):
    start, tip = common.Vector(start), common.Vector(tip)
    travel = tip - start
    cross = common.Vector((-travel.y, travel.x, 0)).normalized()
    verts = [tuple(start)]
    for t in (0.18, 0.40, 0.64, 0.84):
        center = start.lerp(tip, t) + common.Vector((0, 0, rise * math.sin(math.pi * t)))
        spread = cross * (width * math.sin(math.pi * t) ** 0.86)
        edge_drop = common.Vector((0, 0, -width * 0.22 * math.sin(math.pi * t)))
        verts.extend((tuple(center - spread + edge_drop), tuple(center),
                      tuple(center + spread + edge_drop)))
    verts.append(tuple(tip))
    left = [(0, 1, 2), (10, 13, 11)]
    right = [(0, 2, 3), (11, 13, 12)]
    for i in (1, 4, 7):
        left.append((i, i + 3, i + 4, i + 1))
        right.append((i + 1, i + 4, i + 5, i + 2))
    # Keep both halves connected so their shared midrib shades smoothly.
    offset = len(part.vertices)
    part.vertices.extend(verts)
    for faces, color in zip((left, right), colors, strict=True):
        paint = paints[color]
        if paint not in part.materials:
            part.materials.append(paint)
        part.faces.extend(tuple(offset + i for i in face) for face in faces)
        part.face_settings.extend([(part.materials.index(paint), True)] * len(faces))


def greenery(model, paints):
    plants = common.MeshPart(model, "Shop_Greenery")
    x, y, z = 1.53, -1.49, BASE
    plants.lathe((x, y, z), [(0.139, 0), (0.179, 0.035), (0.230, 0.248), (0.238, 0.311),
                             (0.228, 0.328), (0.204, 0.325), (0.198, 0.287)],
                 paints["ivory"], sides=28)
    plants.lathe((x, y, z + 0.281), [(0.197, 0), (0.202, 0.012)], paints["soil"], sides=28)
    root = (x, y, z + 0.291)
    for index, (angle, length, height, width) in enumerate((
        (10, 0.45, 0.50, 0.10), (63, 0.29, 0.76, 0.093), (112, 0.43, 0.66, 0.095),
        (160, 0.52, 0.56, 0.116), (212, 0.45, 0.47, 0.093), (268, 0.39, 0.38, 0.092),
        (320, 0.53, 0.36, 0.103), (44, 0.52, 0.37, 0.105), (282, 0.19, 0.68, 0.070),
    )):
        angle = math.radians(angle)
        dx, dy = length * math.cos(angle), length * math.sin(angle)
        stem = (x + dx * 0.21, y + dy * 0.21, root[2] + height * 0.54)
        plants.tube([root, (x + dx * 0.10, y + dy * 0.10, root[2] + height * 0.27), stem],
                    0.0095, paints["leaf"], sides=6, guide=(0, 0, 1))
        leaflet(plants, stem, (x + dx, y + dy, root[2] + height),
                width * 1.48, 0.065 + 0.009 * (index % 3), paints,
                ("leaf_light", "leaf"))

    for strand, length in enumerate((1.24, 1.36, 1.04, 0.80, 0.69)):
        start_x = LEFT + 0.12 + 0.040 * strand
        start_y = 0.91 + 0.052 * strand
        nodes = [(start_x + 0.024 * math.sin(i * 0.72 + strand),
                  start_y + i * 0.006, CEILING + 0.006 - length * i / 9) for i in range(10)]
        plants.tube(nodes, 0.006, paints["vine"], sides=5, guide=(1, 0, 0))
        for i, (px, py, pz) in enumerate(nodes[:-1]):
            sign = (-1) ** (i + strand)
            leaflet(plants, (px, py, pz), (px + sign * 0.084, py - 0.088, pz - 0.161),
                    0.040 + 0.012 * (1 - i / 9), 0.030, paints, ("vine_light", "vine"))
    plants.finish()


def text_mesh(part, text, size, x, y, z, mat, place):
    bpy = common.bpy
    curve = bpy.data.curves.new(f"Sign Font {text}", "FONT")
    curve.body = text
    curve.size = size
    curve.align_x = "CENTER"
    obj = bpy.data.objects.new(f"Sign Font {text}", curve)
    part.collection.objects.link(obj)
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        part.add([place((x + v.co.x, y + v.co.y, z)) for v in mesh.vertices],
                 [tuple(poly.vertices) for poly in mesh.polygons], mat)
    finally:
        evaluated.to_mesh_clear()
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.curves.remove(curve)


def swing_sign(model, paints):
    x, y, z = -1.18, -1.62, BASE + 0.012
    sign = common.MeshPart(model, "Shop_Pomelo_Sign", origin=(x, y, z))
    angle = math.radians(77)
    sine, cosine = math.sin(angle), math.cos(angle)

    def front(point):
        px, py, pz = point
        return x + px, y + py * cosine - pz * sine, z + py * sine + pz * cosine

    def back(point):
        px, py, pz = point
        return x + px, y + 0.302 - py * cosine - pz * sine, z + py * sine - pz * cosine

    for transform in (front, back):
        for rail in (-0.235, 0.235):
            sign.box((rail, 0.357, 0), (0.050, 0.715, 0.050), paints["ivory"], edge=0.008,
                     steps=1, transform=transform)
        for height in (0.099, 0.671):
            sign.box((0, height, 0), (0.469, 0.047, 0.050), paints["ivory"], edge=0.007,
                     steps=1, transform=transform)
    sign.box((0, 0.384, 0.008), (0.429, 0.552, 0.026), paints["board"], edge=0.006,
             steps=1, transform=front)
    pomelo(sign, 0, 0.507, 0.085, 0.024, paints, front)
    text_mesh(sign, "POMELO", 0.084, 0, 0.346, 0.026, paints["cream"], front)
    text_mesh(sign, "STORE", 0.084, 0, 0.252, 0.026, paints["cream"], front)
    sign.box((0, 0.193, 0.024), (0.14, 0.009, 0.004), paints["cream"], transform=front)
    for off in (-0.233, 0.233):
        sign.box((x + off, y + 0.156, z + 0.192), (0.025, 0.216, 0.033),
                 paints["ivory"], edge=0.005, steps=1)
    sign.finish()


def model_shop(model, effects):
    paints = shop_palette()
    shell(model, paints)
    storefront(model, paints)
    interior(model, effects, paints)
    greenery(model, paints)
    swing_sign(model, paints)


result = common.build(
    "shop", model_shop,
    {"triangles": 30000, "bytes": 1000000, "primitives": 40},
    direction=VIEW_DIRECTION,
    frame=(0.100, 0.025, 0.901, 0.958),
    review_features={
        "architecture": "Sage and ivory trim, recessed flat roof with raised coping and grille.",
        "glazing": "Front and left return glazing; visually readable paired doors, brass pulls and warm interior.",
        "interior": "Honey shelves with miniature hollow mugs, packages, window displays and a lit pendant.",
        "street_detail": "Geometry-only A-frame sign with pith and citrus segments, trailing leaves and potted plant.",
        "presentation": "Shared two-tier plinth, cream studio, soft contact shadows and three-quarter framing.",
    },
)
