"""Render the originals and final GLBs with identical six-view Cycles setups."""
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import zlib

import bpy
import numpy as np
from mathutils import Vector

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import OUT, REPO, VEHICLES, fit, load

SIZE = (420, 270)
VIEWS = {
    'FRONT': (0,-1,0), 'REAR': (0,1,0), 'LEFT': (-1,0,0),
    'RIGHT': (1,0,0), 'TOP': (0,0,1), 'THREE QUARTER': (-1,-1.45,.81),
}
SHEETS = OUT / 'contact-sheets'
SAMPLES = 16

GLYPHS = {
    'A': (14,17,17,31,17,17,17), 'B': (30,17,17,30,17,17,30),
    'C': (14,17,16,16,16,17,14), 'E': (31,16,16,30,16,16,31),
    'F': (31,16,16,30,16,16,16), 'G': (14,17,16,23,17,17,15),
    'H': (17,17,17,31,17,17,17), 'I': (14,4,4,4,4,4,14),
    'K': (17,18,20,24,20,18,17), 'L': (16,16,16,16,16,16,31),
    'N': (17,25,25,21,19,19,17), 'O': (14,17,17,17,17,17,14),
    'P': (30,17,17,30,16,16,16), 'Q': (14,17,17,17,21,18,13),
    'R': (30,17,17,30,20,18,17), 'T': (31,4,4,4,4,4,4),
    'V': (17,17,17,17,17,10,4), 'U': (17,17,17,17,17,17,14), 'W': (17,17,17,21,21,27,17),
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



def studio(center, span):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = SAMPLES
    scene.cycles.seed = 27
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 8
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.render.resolution_x, scene.render.resolution_y = SIZE
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX'
    scene.world = bpy.data.worlds.new('Studio')
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (.58,.65,.72,1)
    background.inputs['Strength'].default_value = .54

    bpy.ops.mesh.primitive_plane_add(size=span*18, location=(0,0,-span*.00025))
    ground = bpy.data.materials.new('Studio Ground')
    ground.use_nodes = True
    shader = ground.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (.24,.26,.28,1)
    shader.inputs['Roughness'].default_value = .92
    bpy.context.object.data.materials.append(ground)
    add_area('Key', (-.8,-1.05,1.65), 160, 1.35, center, span)
    add_area('Fill', (1.2,-.25,.8), 85, 1.2, center, span)
    add_area('Rim', (.15,1.2,1.10), 112, 1, center, span)
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.type = 'ORTHO'
    camera.data.clip_start = span*.0001
    camera.data.clip_end = span*35
    scene.camera = camera
    return scene, camera


def normalize(objects, offset, factor):
    # Apply the same uniform scale and ground origin as the game export for
    # framing. Preserve the baseline's full source geometry and materials.
    matrices = [obj.matrix_world.copy() for obj in objects]
    for obj, original in zip(objects, matrices, strict=True):
        obj.animation_data_clear()
        obj.parent = None
        obj.matrix_world = original
        obj.scale *= factor
        obj.location = (original.translation-offset)*factor
    bpy.context.view_layer.update()


def render_views(points):
    center = Vector((points.min(axis=0)+points.max(axis=0))/2)
    span = float(max(np.ptp(points, axis=0)))
    scene, camera = studio(center, span)
    width, height = SIZE
    scratch = OUT / '.view.png'
    images = []
    for label, coords in VIEWS.items():
        direction = Vector(coords).normalized()
        camera.location = center + direction*span*2.5
        camera.rotation_euler = (0,0,math.pi) if label == 'TOP' else (-direction).to_track_quat('-Z','Y').to_euler()
        rotation = camera.rotation_euler.to_matrix()
        right = np.array(rotation @ Vector((1,0,0)))
        up = np.array(rotation @ Vector((0,1,0)))
        axes = [points@right, points@up]
        camera.location += Vector(right)*((axes[0].min()+axes[0].max())/2-right@np.array(center))
        camera.location += Vector(up)*((axes[1].min()+axes[1].max())/2-up@np.array(center))
        camera.data.ortho_scale = max(np.ptp(axes[0]),np.ptp(axes[1])*width/height)*1.13
        scene.render.filepath = str(scratch)
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(str(scratch),check_existing=False)
        img.colorspace_settings.name = 'Non-Color'
        rgba = np.empty(height*width*4,dtype=np.float32)
        img.pixels.foreach_get(rgba)
        images.append((rgba.reshape((height,width,4))[::-1,:,:3]*255+.5).astype(np.uint8))
        bpy.data.images.remove(img)
    scratch.unlink()
    return images


def compare(key):
    slug, filename, length, _ = VEHICLES[key]
    source = REPO / 'models' / slug / 'exports' / filename
    candidate = OUT / f'{key}_hd.glb'
    objects = load(source)
    offset, factor = fit(objects, length)
    normalize(objects, offset, factor)
    points = np.array([tuple(obj.matrix_world @ v.co) for obj in objects for v in obj.data.vertices])
    original = render_views(points)
    load(candidate)
    game = render_views(points)

    width, height = SIZE
    gutter, header, label_height = 10, 42, 25
    sheet = np.full((header+3*(height+label_height+gutter)+gutter,
                     4*width+5*gutter, 3), (233,238,237), dtype=np.uint8)
    caption(sheet, slug.upper().replace('-', ' '), 15, 14, 3)
    for index, label in enumerate(VIEWS):
        row, pair = divmod(index, 2)
        y = header+gutter+row*(height+label_height+gutter)
        for side, (variant, panels) in enumerate((('ORIGINAL', original), ('GAME', game))):
            x = gutter+(2*pair+side)*(width+gutter)
            caption(sheet, f'{label}   {variant}', x+5, y, 2)
            sheet[y+label_height:y+label_height+height,x:x+width] = panels[index]
    path = SHEETS / f'{key}_comparison.png'
    write_png(path, sheet)
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    print(f'RENDERED {path.name}', flush=True)
    return dict(source=str(source.relative_to(REPO)), source_sha256=digest(source),
                file=candidate.name, glb_sha256=digest(candidate),
                sheet=path.name, sheet_sha256=digest(path))


if __name__ == '__main__':
    SHEETS.mkdir(exist_ok=True)
    manifest_path = SHEETS / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
        'blender': bpy.app.version_string, 'engine': 'Cycles CPU', 'threads': 2,
        'samples': SAMPLES, 'views': list(VIEWS), 'models': {},
    }
    for key in sys.argv[sys.argv.index('--')+1:] or VEHICLES:
        manifest['models'][key] = compare(key)
        manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
