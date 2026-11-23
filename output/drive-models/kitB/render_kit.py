"""Render six orthographic views of each exported GLB with Cycles CPU."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

import bpy
from mathutils import Vector
import numpy as np

ROOT = Path(__file__).resolve().parent
SHEETS = ROOT / 'contact-sheets'
WIDTH, HEIGHT = 374, 314
VIEWS = {
    'FRONT': (0,-1,0), 'BACK': (0,1,0), 'LEFT': (-1,0,0),
    'RIGHT': (1,0,0), 'TOP': (0,0,1), 'THREE QUARTER': (1,-1.45,.81),
}

# Seven rows of five bits per glyph. The sheet remains portable without font dependencies.
GLYPHS = {
    'A': (14,17,17,31,17,17,17), 'B': (30,17,17,30,17,17,30),
    'C': (14,17,16,16,16,17,14), 'E': (31,16,16,30,16,16,31),
    'F': (31,16,16,30,16,16,16), 'G': (14,17,16,23,17,17,15),
    'H': (17,17,17,31,17,17,17), 'I': (14,4,4,4,4,4,14),
    'K': (17,18,20,24,20,18,17), 'L': (16,16,16,16,16,16,31),
    'N': (17,25,25,21,19,19,17), 'O': (14,17,17,17,17,17,14),
    'P': (30,17,17,30,16,16,16), 'Q': (14,17,17,17,21,18,13),
    'R': (30,17,17,30,20,18,17), 'T': (31,4,4,4,4,4,4),
    'U': (17,17,17,17,17,17,14), 'W': (17,17,17,21,21,27,17),
    'D': (30,17,17,17,17,17,30), 'S': (15,16,16,14,1,1,30),
    'Y': (17,17,10,4,4,4,4), 'M': (17,27,21,21,17,17,17),
    'Z': (31,1,2,4,8,16,31),
}


def caption(canvas, label, x, y, size=2):
    for letter in label:
        for row, bits in enumerate(GLYPHS.get(letter, ())):
            for col in range(5):
                if bits & (1 << (4-col)):
                    a, b = y+row*size, x+col*size
                    canvas[a:a+size,b:b+size] = (37,51,56)
        x += 6*size


def write_png(path, data):
    def chunk(tag, payload):
        return (struct.pack('>I',len(payload)) + tag + payload
                + struct.pack('>I',zlib.crc32(tag+payload)))
    rows, cols, _ = data.shape
    raw = b''.join(b'\0'+row.tobytes() for row in data)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'
                     + chunk(b'IHDR', struct.pack('>IIBBBBB',cols,rows,8,2,0,0,0))
                     + chunk(b'IDAT',zlib.compress(raw,6))
                     + chunk(b'IEND',b''))


def add_area(name, direction, energy, size, center, span):
    bpy.ops.object.light_add(type='AREA', location=center+Vector(direction)*span)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = (center-obj.location).to_track_quat('-Z','Y').to_euler()
    obj.data.energy = energy * span**2
    obj.data.shape = 'DISK'
    obj.data.size = size*span


def render(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    scene = bpy.context.scene
    meshes = [obj for obj in scene.objects if obj.type == 'MESH']
    points = np.array([tuple(obj.matrix_world @ v.co) for obj in meshes for v in obj.data.vertices])
    minimum, maximum = points.min(axis=0), points.max(axis=0)
    center = Vector((minimum+maximum)/2)
    span = max(maximum-minimum)

    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 8
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 5
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'AgX'
    scene.world = bpy.data.worlds.new('Studio')
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (.58,.65,.72,1)
    background.inputs['Strength'].default_value = .43

    bpy.ops.mesh.primitive_plane_add(size=span*18, location=(0,0,-span*.00012))
    ground = bpy.data.materials.new('Studio Ground')
    ground.use_nodes = True
    shader = ground.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (.30,.34,.34,1)
    shader.inputs['Roughness'].default_value = .92
    bpy.context.object.data.materials.append(ground)
    add_area('Key', (-.8,-1.05,1.65), 125, 1.35, center, span)
    add_area('Fill', (1.2,-.25,.8), 49, 1.2, center, span)
    add_area('Rim', (.15,1.2,1.10), 79, 1, center, span)
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.type = 'ORTHO'
    camera.data.clip_start = span*.0001
    camera.data.clip_end = span*35
    scene.camera = camera

    gutter, header, label_height = 9, 35, 27
    sheet = np.full((2*(HEIGHT+label_height)+header+gutter*3,3*WIDTH+gutter*4,3),
                    (233,238,237),dtype=np.uint8)
    caption(sheet,path.stem.upper().replace('_',' '),gutter+9,14)
    scratch = ROOT / '.view.png'
    for index,(label, coords) in enumerate(VIEWS.items()):
        direction = Vector(coords).normalized()
        camera.location = center + direction*span*2.5
        if label == 'TOP':
            camera.rotation_euler = (0,0,np.pi)
        else:
            camera.rotation_euler = (-direction).to_track_quat('-Z','Y').to_euler()
        rotation = camera.rotation_euler.to_matrix()
        right = np.array(rotation @ Vector((1,0,0)))
        up = np.array(rotation @ Vector((0,1,0)))
        axes = [points@right, points@up]
        camera.location += Vector(right)*((axes[0].min()+axes[0].max())/2-right@np.array(center))
        camera.location += Vector(up)*((axes[1].min()+axes[1].max())/2-up@np.array(center))
        camera.data.ortho_scale = max(np.ptp(axes[0]),np.ptp(axes[1])*WIDTH/HEIGHT)*1.15
        scene.render.filepath = str(scratch)
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(str(scratch),check_existing=False)
        img.colorspace_settings.name = 'Non-Color'
        rgba = np.empty(HEIGHT*WIDTH*4,dtype=np.float32)
        img.pixels.foreach_get(rgba)
        rgb = (rgba.reshape((HEIGHT,WIDTH,4))[::-1,:,:3]*255+.5).astype(np.uint8)
        bpy.data.images.remove(img)
        col,row = index%3,index//3
        x = gutter+col*(gutter+WIDTH)
        y = header+gutter+row*(gutter+HEIGHT+label_height)
        sheet[y:y+HEIGHT,x:x+WIDTH] = rgb
        caption(sheet,label,x+8,y+HEIGHT+7)
    scratch.unlink()
    out = SHEETS / f'{path.stem}.png'
    write_png(out,sheet)
    print(f'RENDERED {out.name}',flush=True)
    return {'glb_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'sheet_sha256':hashlib.sha256(out.read_bytes()).hexdigest()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('models', nargs='*')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    SHEETS.mkdir(exist_ok=True)
    manifest_path = SHEETS / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
        'blender':bpy.app.version_string, 'engine':'Cycles CPU', 'threads':2,
        'samples':8, 'views':list(VIEWS), 'models':{},
    }
    selected = [ROOT/f'{name}.glb' for name in args.models] or sorted(ROOT.glob('*.glb'))
    for path in selected:
        manifest['models'][path.stem] = render(path)
        manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
