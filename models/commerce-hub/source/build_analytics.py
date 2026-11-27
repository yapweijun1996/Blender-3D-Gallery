"""Build the analytics chart diorama inside Blender."""

import math
import sys
from pathlib import Path
from types import ModuleType


SOURCE = Path(sys._getframe().f_code.co_filename).resolve().parent
common = ModuleType("commerce_hub_common")
common.__file__ = str(SOURCE / "common.py")
exec(compile(Path(common.__file__).read_text(), common.__file__, "exec"), vars(common))

BASE = common.PLINTH_HEIGHT
TIER_HEIGHT = 0.146
DECK = BASE + TIER_HEIGHT
PANEL_X, PANEL_HEIGHT, PANEL_THICKNESS = -1.08, 2.06, 0.068
GLASS = "Analytics Frosted Glass"
ANGLE = math.radians(-12)
BARS = (
    ("Bar_Low", -0.96, 0.77, "cream"),
    ("Bar_Mid", 0.00, 1.27, "pale"),
    ("Bar_High", 0.96, 1.91, "amber"),
)


def place(point):
    x, y, z = point
    return (x * math.cos(ANGLE) - y * math.sin(ANGLE),
            x * math.sin(ANGLE) + y * math.cos(ANGLE), z)


def panel_face(point):
    u, height, relief = point
    return place((PANEL_X + relief, u, DECK + height))


def chart(model, p):
    glass = common.MeshPart(model, "Panel_Glass", origin=panel_face((0, 0, 0)))
    glass.box((0, PANEL_HEIGHT / 2, 0), (3.07, PANEL_HEIGHT, PANEL_THICKNESS), p["glass"],
              edge=0.017, corner=0.206, steps=3, transform=panel_face)
    glass.finish()

    details = common.MeshPart(model, "Chart_Details")
    surface = PANEL_THICKNESS / 2 + 0.009
    for i, height in enumerate((0.117, 0.220, 0.332, 0.463)):
        details.box((-1.285 + 0.155 * i, 1.225 + height / 2, surface),
                    (0.112, height, 0.019), p["line"], edge=0.005, corner=0.017,
                    steps=1, transform=panel_face)
    for width, height in ((0.71, 1.710), (0.51, 1.542)):
        details.box((-0.562 + width / 2, height, surface), (width, 0.068, 0.019),
                    p["pale"], edge=0.005, corner=0.030, steps=1, transform=panel_face)
    details.finish()

    trend = common.MeshPart(model, "Chart_Line", origin=panel_face((0, 0, surface)))
    path = ((-1.24, 0.415), (-0.62, 0.887), (-0.335, 0.920), (-0.255, 0.950),
            (0.296, 1.306), (0.423, 1.347), (1.135, 1.770))
    relief = surface + 0.023
    trend.tube([panel_face((*point, relief)) for point in path], 0.029,
               p["line"], sides=6, guide=place((1, 0, 0)))
    for index in (1, 4, 6):
        trend.tube([panel_face((*path[index], depth)) for depth in (surface - 0.004, relief + 0.034)],
                   0.098, p["line"], sides=14, guide=(0, 0, 1))
    trend.finish()


def model_analytics(model, _fx):
    paint = common.material
    p = {
        "tier": paint("Analytics Platform Sage", "#77A36D", roughness=0.38),
        "cream": paint("Analytics Bar Cream", "#F3DDAA", roughness=0.38),
        "pale": paint("Analytics Bar Light Sage", "#AFC38C", roughness=0.37),
        "amber": paint("Analytics Bar Amber", "#F0B33D", roughness=0.36),
        "line": paint("Analytics Chart Green", "#4B9D46", roughness=0.44),
        "glass": paint(GLASS, "#F0F2E4", roughness=0.46, alpha=0.57, specular=0.34),
    }
    p["glass"].use_backface_culling = True
    tier = common.MeshPart(model, "Analytics_Tier", origin=(0, 0, BASE))
    tier.box((0, 0, BASE + TIER_HEIGHT / 2), (2.71, 3.20, TIER_HEIGHT), p["tier"],
             edge=0.044, corner=0.31, steps=4, bevel_steps=2, transform=place)
    tier.finish()

    for name, y, height, color in BARS:
        base = (0.24, y, DECK)
        bar = common.MeshPart(model, name, origin=place(base))
        bar.box((base[0], y, DECK + height / 2), (0.76, 0.745, height), p[color],
                edge=0.087, corner=0.130, steps=3, bevel_steps=2, transform=place)
        bar.finish()
    chart(model, p)


result = common.build(
    "analytics", model_analytics,
    {"triangles": 4500, "bytes": 140000, "primitives": 14},
    direction=(1.16, -1.0, 0.837),
    frame=(0.133, 0.026, 0.864, 0.965),
    required_parts=(*(name for name, *_ in BARS), "Chart_Line", "Panel_Glass"),
    blended_materials=(GLASS,),
    review_features={
        "layout": "A sage third tier with ascending cream, light sage and amber bars.",
        "chart": "Frosted translucent panel with a four-bar icon, two text lines and a three-node trend.",
        "motion": "Three bars pivot at their bases, with separate trend and glass objects.",
    },
)
