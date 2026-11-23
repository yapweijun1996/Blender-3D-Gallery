"""Character meshes are authored in the same rest space as the rig."""
import importlib.util
import math
from pathlib import Path

import bmesh
import bpy

source = Path(__file__).resolve().parents[1] / "chibi-mall-guide-v5" / "kit.py"
spec = importlib.util.spec_from_file_location("mall_guide_geometry", source)
geo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geo)


def mat(name, hex_srgb, rough=.45, metallic=0):
    existing = bpy.data.materials.get(name)
    if existing:
        return existing
    value = hex_srgb.lstrip("#")
    c = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    rgba = tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c) + (1.,)
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgba
    m.use_nodes = True
    shader = m.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = rgba
    shader.inputs["Roughness"].default_value = rough
    shader.inputs["Metallic"].default_value = metallic
    return m


def ell(name, loc, scale, material, segments=24, rings=14):
    bm = bmesh.new()
    geo.add_super(bm, loc, scale, seg=segments, rings=rings)
    return geo.finish(name, bm, [material])


def tube(name, points, radius, material, radii=None):
    bm = bmesh.new()
    sizes = [radius * r for r in radii] if radii is not None else [radius] * len(points)
    geo.add_tube(bm, points, sizes, sides=10)
    return geo.finish(name, bm, [material])


def loft(name, rows, material, segments=32):
    bm = bmesh.new()
    bands = []
    for z, cx, cy, rx, ry in rows:
        if rx == 0 and ry == 0:
            bands.append([bm.verts.new((cx, cy, z))])
        else:
            bands.append([bm.verts.new((cx + rx * math.cos(math.tau * j / segments),
                                        cy + ry * math.sin(math.tau * j / segments), z))
                          for j in range(segments)])
    for low, high in zip(bands, bands[1:]):
        for j in range(segments):
            k = (j + 1) % segments
            if len(low) == 1:
                bm.faces.new((low[0], high[k], high[j]))
            elif len(high) == 1:
                bm.faces.new((low[j], low[k], high[0]))
            else:
                bm.faces.new((low[j], low[k], high[k], high[j]))
    if len(bands[0]) > 2:
        bm.faces.new(list(reversed(bands[0])))
    if len(bands[-1]) > 2:
        bm.faces.new(bands[-1])
    return geo.finish(name, bm, [material])
