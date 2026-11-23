"""Build or re-export the 2 m straight floor. See README.md for commands."""
import argparse
import math
import struct
import sys
import tempfile
import zlib
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'mall-floor-module-2m'
SOURCE = HERE / 'sources' / f'{SLUG}.blend'
# 500 mm pavers, 4 mm filled joints, and a 70 mm precast base.
PITCH = .5
HALF_JOINT = .002
RADIUS = .006
TOP = .1
GROUT = (125, 126, 115)
PRECAST = (148, 145, 134)
BOND = (98, 95, 86)
SURFACE = 488
SIZE = 512


def material(name, color, roughness, image=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    rgba = [v / 255 for v in color]
    rgba = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgba] + [1]
    mat.diffuse_color = rgba
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = rgba
    bsdf.inputs['Roughness'].default_value = roughness
    if image:
        tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = image
        mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    return mat


def stone_uv(dx, dy, turn):
    # Match the metre-to-texel ratio of the 596 mm legacy finish.
    u, v = dx / .596 + .5, dy / .596 + .5
    for _ in range(turn):
        u, v = v, 1 - u
    return u, v


def atlas(texture):
    raw = np.empty(4 * texture.size[0] * texture.size[1], np.float32)
    texture.pixels.foreach_get(raw)
    pixels = raw.reshape(texture.size[1], texture.size[0], 4)[:, :, :3]
    # Blender exposes the byte image as normalized sRGB. Preserve the colour
    # bytes when writing the new sRGB atlas.
    if texture.is_float or texture.colorspace_settings.name != 'sRGB':
        raise ValueError('Expected the original 8-bit sRGB terrazzo artwork')
    pixels = pixels * 255
    # One 512 px texture supplies all colours. The 488 px top square has
    # at least 8 px of padding on every side. Four subpixel taps keep 4 mm grout visible at distance.
    yy, xx = np.indices((SIZE, SIZE))
    top = np.zeros((SIZE, SIZE, 3), np.float32)
    for sx, sy in ((.25, .25), (.25, .75), (.75, .25), (.75, .75)):
        x = np.clip((xx + sx - 8) / SURFACE, 0, .999999) * 2
        y = np.clip((yy + sy - 16) / SURFACE, 0, .999999) * 2
        col, row = (x / PITCH).astype(int), (y / PITCH).astype(int)
        dx, dy = x % PITCH - PITCH / 2, y % PITCH - PITCH / 2
        # Signed distance to the rounded finished tile.
        qx, qy = abs(dx) - (PITCH / 2 - HALF_JOINT - RADIUS), abs(dy) - (PITCH / 2 - HALF_JOINT - RADIUS)
        stone = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) <= RADIUS
        turn = (col + 3 * row) % 4
        us = np.zeros_like(dx)
        vs = np.zeros_like(dy)
        for orient in range(4):
            u, v = stone_uv(dx, dy, orient)
            np.copyto(us, u, where=turn == orient)
            np.copyto(vs, v, where=turn == orient)
        sample = pixels[(vs * texture.size[1]).astype(int), (us * texture.size[0]).astype(int)]
        top += np.where(stone[:, :, None], sample, GROUT) / 4
    # The underside and edge rings sample the middle of these wide swatches.
    for col, rgb in enumerate([PRECAST, BOND, GROUT]):
        top[:8, col * 160:(col + 1) * 160] = rgb
    rows = np.uint8(np.clip(np.rint(top[::-1]), 0, 255))
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data))
    packed = b''.join(b'\x00' + row.tobytes() for row in rows)
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', SIZE, SIZE, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(packed, 9)) + chunk(b'IEND', b''))
    with tempfile.TemporaryDirectory() as folder:
        file = Path(folder) / 'Floor 2m distant surface.png'
        file.write_bytes(png)
        image = bpy.data.images.load(str(file))
        image.pack()
        image.filepath = '//Floor 2m distant surface.png'
    return image


def create_module(level, mats):
    vertices, faces, indices, uv_faces = [], [], [], []
    unique = {}

    def face(coords, mat, uv=None):
        ids = []
        for p in coords:
            key = tuple(round(v, 8) for v in p)
            if key not in unique:
                unique[key] = len(vertices)
                vertices.append(key)
            ids.append(unique[key])
        faces.append(ids)
        indices.append(0 if level == 2 else mat)
        uv_faces.append(uv if uv is not None else [(0, 0)] * len(coords))

    def top_face(points, mat, uvs=None):
        face([(x, y, TOP) for x, y in points], mat, uvs)

    if level < 2:
        segments = 5 if level == 0 else 1
        for row in range(4):
            for col in range(4):
                cx, cy = (col + .5) * PITCH - 1, (row + .5) * PITCH - 1
                outside, arcs = [], []
                for i, (ix, iy) in enumerate([(-1,-1), (1,-1), (1,1), (-1,1)]):
                    outside.append((cx + ix * PITCH / 2, cy + iy * PITCH / 2))
                    reach = PITCH / 2 - HALF_JOINT - RADIUS
                    arc = []
                    for step in range(segments + 1):
                        theta = math.radians(180 + 90 * i + 90 * step / segments)
                        arc.append((cx + ix * reach + RADIUS * math.cos(theta),
                                    cy + iy * reach + RADIUS * math.sin(theta)))
                    arcs.append(arc)
                paver = [point for arc in arcs for point in arc]
                top_face(paver, 0, [stone_uv(x-cx, y-cy, (col + 3*row) % 4) for x,y in paver])
                for i, arc in enumerate(arcs):
                    for a,b in zip(arc,arc[1:]):
                        top_face([outside[i], b, a], 1)
                    n = (i+1)%4
                    top_face([outside[i], outside[n], arcs[n][0], arc[-1]], 1)
    else:
        square = [(-1,-1), (1,-1), (1,1), (-1,1)]
        top_face(square, 0, [((8+(x+1)*SURFACE/2)/SIZE, (16+(y+1)*SURFACE/2)/SIZE) for x,y in square])

    # All LODs share the same 2 mm underside bevel and 3 mm bond course.
    # High-detail top cell boundaries meet matching vertices in the side rings.
    n = 4 if level < 2 else 1
    boundary = []
    square = [(-1,-1), (1,-1), (1,1), (-1,1)]
    for i,(x,y) in enumerate(square):
        nx,ny = square[(i+1)%4]
        boundary.extend([(x+(nx-x)*k/n, y+(ny-y)*k/n) for k in range(n)])
    def ring(scale, height):
        return [(x*scale, y*scale, height) for x,y in boundary]
    def swatch(index, count):
        return [((80 + index*160)/SIZE, 4/SIZE)]*count
    last = ring(.998, 0)
    face(last[::-1], 2, swatch(0,len(last)))
    for width, height, material_id, palette in [(1,.002,2,0), (1,.070,2,0), (1,.073,3,1), (1,TOP,1,2)]:
        nxt = ring(width, height)
        for i in range(len(last)):
            j = (i+1) % len(last)
            face([last[i],last[j],nxt[j],nxt[i]],material_id,swatch(palette,4))
        last = nxt

    name = f'MODULE_StraightFloor_L{level}'
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    for mat in mats:
        mesh.materials.append(mat)
    uv = mesh.uv_layers.new(name='Surface coordinates')
    for poly, index, coords in zip(mesh.polygons, indices, uv_faces):
        poly.material_index = index
        for li, co in zip(poly.loop_indices, coords):
            uv.data[li].uv = co
    obj['registry_id'] = 'MALL-STR-001'
    obj['pitch_m'] = 2.0
    obj['finished_surface_m'] = TOP
    obj['origin'] = 'Underside centre'
    obj['lod'] = level
    return obj


def export_models():
    for level in range(3):
        bpy.ops.object.select_all(action='DESELECT')
        obj = bpy.data.objects[f'MODULE_StraightFloor_L{level}']
        obj.hide_set(False)
        obj.hide_render = False
        obj.select_set(True)
        name = SLUG + (f'-lod{level}' if level else '') + '.glb'
        bpy.ops.export_scene.gltf(filepath=str(HERE/'exports'/name), export_format='GLB',
                                  use_selection=True, export_animations=False,
                                  export_lights=False, export_cameras=False, export_extras=True,
                                  export_image_format='JPEG' if level == 2 else 'AUTO',
                                  export_image_quality=86)
        obj.hide_set(level != 0)
        obj.hide_render = level != 0


def preview(level):
    name = SLUG + (f'-lod{level}' if level else '')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(HERE/'exports'/f'{name}.glb'))
    scene = bpy.context.scene
    target = Vector((0, 0, .045))
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.0005))
    bpy.context.object.data.materials.append(material('Studio', (47,60,63), .84))
    for light_name, xyz, energy, size in [('Key', (-3,-4,5), 560, 4), ('Fill',(3,1,3),260,3), ('Rim',(-1,3,5),400,3)]:
        bpy.ops.object.light_add(type='AREA', location=xyz)
        lamp = bpy.context.object
        lamp.name = light_name
        lamp.data.energy = energy
        lamp.data.shape = 'DISK'
        lamp.data.size = size
        lamp.rotation_euler = (target - lamp.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.object.camera_add(location=(2.6,-3.5,2.65))
    cam = bpy.context.object
    cam.rotation_euler = (target-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 3.25
    scene.camera = cam
    scene.world = bpy.data.worlds.new('Soft studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .42
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 20
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 900, 675
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'WEBP'
    scene.render.image_settings.quality = 90
    scene.render.filepath = str(HERE/'previews'/f'{name}.webp')
    bpy.ops.render.render(write_still=True)


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--texture', type=Path, default=HERE.parent/'mall-floor-tile/textures/terrazzo-original.png')
    args.add_argument('--export-source', action='store_true')
    args.add_argument('--skip-render', action='store_true')
    args.add_argument('--lod-previews', action='store_true', help='Also render the mid and distant GLBs')
    options = args.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for directory in ('exports','sources','previews'):
        (HERE/directory).mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if options.export_source:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
    else:
        if SOURCE.exists():
            raise FileExistsError(f'{SOURCE} exists. Use --export-source to preserve edits.')
        bpy.context.scene.unit_settings.system = 'METRIC'
        texture = bpy.data.images.load(str(options.texture.resolve()))
        texture.pack()
        texture.filepath = '//../../mall-floor-tile/textures/terrazzo-original.png'
        mats = [material('Honed ivory terrazzo, seed 421',(255,255,255),.32, texture),
                material('Flush warm grey grout',GROUT,.83),
                material('Precast backing',PRECAST,.78),material('Bond course',BOND,.73)]
        low_mat = material('Distant floor surface',(255,255,255),.37,atlas(texture))
        for level in range(3):
            obj = create_module(level,[low_mat] if level == 2 else mats)
            obj.hide_set(level != 0)
            obj.hide_render = level != 0
        active = bpy.data.objects['MODULE_StraightFloor_L0']
        active.select_set(True)
        bpy.context.view_layer.objects.active = active
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.region_3d.view_distance = 3.7
                area.spaces.active.region_3d.view_location = (0, 0, TOP/2)
        bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE),compress=True,relative_remap=False)
    export_models()
    if not options.skip_render:
        for level in range(3 if options.lod_previews else 1):
            preview(level)


if __name__ == '__main__':
    main()
