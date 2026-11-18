"""Bake four opaque finish swatches and their distance detail into a single UV sheet."""
import struct
import zlib
from math import pi

import bpy
import numpy as np


def packed_image(name, pixels, data=False):
    """Write RGB PNG in memory. Keep identical PNG bytes in the blend and the GLB."""
    height, width, _ = pixels.shape
    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload)))
    rows = b"".join(b"\0" + row.tobytes() for row in pixels[::-1])
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
           + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))
    image = bpy.data.images.new(name, width=width, height=height, alpha=False)
    image.filepath_raw = "//" + name + ".png"
    image.source = "FILE"
    image.colorspace_settings.name = "Non-Color" if data else "sRGB"
    image.pack(data=png, data_len=len(png))
    return image


def pattern(slot, x, y, row):
    # The bottom row preserves a flat reference sample of each programme hex.
    if row == 0:
        return np.ones_like(x)
    if row == 1 and slot == "S02":
        # Offset hammer impressions keep the copper canopy distinct from timber.
        row_index = np.floor(y*9)
        dx = (x*12 + .5*(row_index%2))%1-.5
        dy = (y*9)%1-.5
        return .965 + .105*dx*np.exp(-5*(dx*dx+dy*dy))
    if row == 1:
        return .94 + .035*np.sin(2*pi*(13*x + .48*np.sin(6*y))) + .016*np.cos(2*pi*28*y)
    if row == 2:
        designs = {
            "S01": lambda: np.cos(2*pi*(4*x + .46*np.cos(2*pi*2*y)))**12,
            "S04": lambda: np.exp(-50*((x*7 % 1-.5)**2+(y*9 % 1-.5)**2)),
            "S05": lambda: ((x*2 % 1 < .045) | (y*5 % 1 < .065)).astype(float)
                           + .60*np.exp(-50*((x*2 % 1-.5)**2 + (y*5 % 1-.53)**2)),
            "S06": lambda: np.cos(2*pi*(5*x+.07*np.sin(6*y)))**8,
            "S07": lambda: np.cos(2*pi*5*x)**8,
            "S10": lambda: (.5+.5*np.cos(34*np.arctan2(x-.5,.09+.89*y)))**2*.48,
            "S12": lambda: .9*(1-x)**2 + .10*np.cos(12*pi*y)**8,
            "S14": lambda: 1.28+.72*y-.6*np.exp(-((x+.59*y-.66)/.19)**2),
            "S15": lambda: np.maximum((x*7 % 1 < .055)*.45,
                          ((np.minimum(x*7 % 1,1-x*7 % 1)<.26) &
                           (np.rint(x*7).astype(int)%7 != 3) &
                           (np.rint(x*7).astype(int)%7 != 0) & (y>.42))*2.38),
            "S16": lambda: np.exp(-38*((x*8 % 1-.5)**2+(y*8 % 1-.5)**2)),
            "S17": lambda: (np.cos(3*pi*x)**40)*(.45+.55*np.cos(17*pi*y)**4),
        }
        relief = designs.get(slot, lambda: np.cos(4*pi*y)**8)()
        return .99 - .36 * relief
    # Inlaid border with a shadow just inside the lip.
    edge = np.minimum(np.minimum(x,1-x),np.minimum(y,1-y))
    return .87 + .12*(edge > .055) - .23*np.exp(-((edge-.065)/.016)**2)


def make_surface(spec):
    swatches = spec["palette"]
    n = 64
    y, x = np.mgrid[0:n,0:n] / (n-1)
    rgb = np.zeros((4*n,4*n,3),dtype=np.uint8)
    mr = np.zeros((4,4,3),dtype=np.uint8)
    for column, swatch in enumerate(swatches):
        color = np.array(list(bytes.fromhex(swatch["hex"][1:])))
        name = swatch["material"].lower()
        metal = any(k in name for k in ("steel","brass","copper","tinplate","aluminium","anodised","bronze","nickel","silver","zinc"))
        rough = .33 if metal else (.36 if any(k in name for k in ("glaze","lacquer","glass","resin","ceramic")) else .65)
        mr[:,column,:] = (255, round(255*rough), round(255*(.78 if metal else .04)))
        for row in range(4):
            shade = pattern(spec["slot"],x,y,row)
            rgb[n*row:n*(row+1),n*column:n*(column+1)] = np.rint(color*shade[:,:,None]).clip(0,255)
    mat = bpy.data.materials.new(spec["style"] + " | shared finish atlas")
    mat.use_nodes = True
    mat.use_backface_culling = True
    tree = mat.node_tree
    shader = tree.nodes.get("Principled BSDF")
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.image = packed_image(spec["slug"]+"-colour", rgb)
    base_color = tex.outputs["Color"]
    if spec["slot"] == "S16":
        color = tree.nodes.new("ShaderNodeVertexColor")
        color.layer_name = "Parts tint"
        mix = tree.nodes.new("ShaderNodeMixRGB")
        mix.blend_type = "MULTIPLY"
        mix.inputs[0].default_value = 1
        tree.links.new(base_color,mix.inputs[1])
        tree.links.new(color.outputs["Color"],mix.inputs[2])
        base_color = mix.outputs[0]
    tree.links.new(base_color,shader.inputs["Base Color"])
    packed = tree.nodes.new("ShaderNodeTexImage")
    packed.image = packed_image(spec["slug"]+"-finish", mr, True)
    packed.interpolation = "Closest"
    separate = tree.nodes.new("ShaderNodeSeparateColor")
    tree.links.new(packed.outputs["Color"], separate.inputs["Color"])
    tree.links.new(separate.outputs["Green"], shader.inputs["Roughness"])
    tree.links.new(separate.outputs["Blue"], shader.inputs["Metallic"])
    if spec["slot"] == "S12":
        edge = np.zeros((4,4,3),dtype=np.uint8)
        edge[0,1] = [94,139,132]
        glow = tree.nodes.new("ShaderNodeTexImage")
        glow.image = packed_image("Index-edge-glow",edge)
        glow.interpolation = "Closest"
        tree.links.new(glow.outputs["Color"],shader.inputs["Emission Color"])
        shader.inputs["Emission Strength"].default_value = .45
    return mat
