"""Render the exact delivered GLBs from six directions in Cycles CPU."""
from hashlib import sha256
from pathlib import Path
import struct
import sys
import zlib

import bpy
from mathutils import Vector
import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import OUT, reset

WIDTH, HEIGHT = 700, 460
VIEWS = [
    ('THREE QUARTER', (-.72, -1, .48)),
    ('FRONT', (0, -1, 0)),
    ('RIGHT', (1, 0, 0)),
    ('LEFT', (-1, 0, 0)),
    ('REAR', (0, 1, 0)),
    ('TOP', (0, 0, 1)),
]

GLYPHS = {
    'A': (14,17,17,31,17,17,17), 'E': (31,16,16,30,16,16,31),
    'F': (31,16,16,30,16,16,16), 'G': (14,17,16,23,17,17,15),
    'H': (17,17,17,31,17,17,17), 'I': (14,4,4,4,4,4,14),
    'L': (16,16,16,16,16,16,31), 'N': (17,25,25,21,19,19,17),
    'O': (14,17,17,17,17,17,14), 'P': (30,17,17,30,16,16,16),
    'Q': (14,17,17,17,21,18,13), 'R': (30,17,17,30,20,18,17),
    'T': (31,4,4,4,4,4,4), 'U': (17,17,17,17,17,17,14),
}


def caption(canvas, label, x, y):
    for letter in label:
        for row, bits in enumerate(GLYPHS.get(letter, ())):
            for col in range(5):
                if bits & (1 << (4-col)):
                    a, b = y+2*row, x+2*col
                    canvas[a:a+2,b:b+2] = (43,59,63)
        x += 12


def write_png(path, canvas, source_hash):
    def chunk(kind, data):
        return (struct.pack('>I', len(data)) + kind + data
                + struct.pack('>I', zlib.crc32(kind+data)))
    height, width, _ = canvas.shape
    raw = b''.join(b'\0'+row.tobytes() for row in canvas)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'
                     + chunk(b'IHDR', struct.pack('>IIBBBBB',width,height,8,2,0,0,0))
                     + chunk(b'sRGB', b'\x00')
                     + chunk(b'tEXt', b'GLB SHA-256\0' + source_hash.encode('ascii'))
                     + chunk(b'IDAT', zlib.compress(raw,6)) + chunk(b'IEND',b''))


def studio(center, span):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 6
    scene.cycles.adaptive_threshold = .18
    scene.cycles.seed = 27
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX'
    scene.world = bpy.data.worlds.new('Neutral studio')
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (.62,.71,.78,1)
    bg.inputs['Strength'].default_value = .36

    bpy.ops.mesh.primitive_plane_add(size=span*24, location=(0,0,-.018))
    backdrop = bpy.data.materials.new('Preview background')
    backdrop.use_nodes = True
    shader = backdrop.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (.116,.159,.168,1)
    shader.inputs['Roughness'].default_value = .9
    bpy.context.object.data.materials.append(backdrop)
    for direction, power, size in [((-.68,-.88,1.26),135,.72),
                                   ((.9,-.13,.75),44,1.12), ((.41,1.04,.82),80,1.08)]:
        bpy.ops.object.light_add(type='AREA', location=center+Vector(direction)*span)
        lamp = bpy.context.object
        lamp.rotation_euler = (center-lamp.location).to_track_quat('-Z','Y').to_euler()
        lamp.data.energy = power*span**2
        lamp.data.shape = 'DISK'
        lamp.data.size = size*span
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.data.type = 'ORTHO'
    cam.data.clip_end = span*30
    scene.camera = cam
    return scene, cam


def sheet(name):
    reset()
    source = OUT / (name+'.glb')
    source_hash = sha256(source.read_bytes()).hexdigest()
    bpy.ops.import_scene.gltf(filepath=str(source))
    bpy.context.view_layer.update()
    scene = bpy.context.scene
    points = [obj.matrix_world@v.co for obj in scene.objects if obj.type == 'MESH'
              for v in obj.data.vertices]
    lower = Vector([min(p[i] for p in points) for i in range(3)])
    upper = Vector([max(p[i] for p in points) for i in range(3)])
    span = max(upper-lower)
    scene, cam = studio((lower+upper)/2, span*.64)
    margin, label_height = 12, 38
    canvas = np.full((2*(HEIGHT+label_height)+3*margin,3*WIDTH+4*margin,3),
                     [232,239,239], dtype=np.uint8)
    temp = OUT / '.render-pass.png'
    for i, (label, direction) in enumerate(VIEWS):
        # A shallow elevation shows the actual waterfront layout in the oblique view.
        view = Vector(direction).normalized()
        rotation = (-view).to_track_quat('-Z','Y')
        if label == 'TOP':
            rotation = Vector((0,0,-1)).to_track_quat('-Z','Y')
        right, up = rotation @ Vector((1,0,0)), rotation @ Vector((0,1,0))
        h = [p.dot(right) for p in points]
        v = [p.dot(up) for p in points]
        shift = right*((min(h)+max(h))/2) + up*((min(v)+max(v))/2)
        cam.location = shift + view*(span*2.5)
        cam.rotation_euler = rotation.to_euler()
        cam.data.ortho_scale = max(max(h)-min(h),(max(v)-min(v))*WIDTH/HEIGHT)*1.16
        scene.render.filepath = str(temp)
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(str(temp), check_existing=False)
        rgba = np.empty(WIDTH*HEIGHT*4, dtype=np.float32)
        im.pixels.foreach_get(rgba)
        rgb = rgba.reshape((HEIGHT, WIDTH, 4))[::-1,:,:3]
        rgb = np.uint8(np.clip(rgb*255 + .5, 0, 255))
        y = margin+(i//3)*(HEIGHT+label_height+margin)
        x = margin+(i%3)*(WIDTH+margin)
        canvas[y:y+HEIGHT,x:x+WIDTH] = rgb
        caption(canvas, label, x+12, y+HEIGHT+11)
        bpy.data.images.remove(im)
    temp.unlink()
    if sha256(source.read_bytes()).hexdigest() != source_hash:
        raise RuntimeError(f'{source.name} changed during rendering')
    write_png(OUT / (name+'_contact.png'), canvas, source_hash)


if __name__ == '__main__':
    requested = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    for target in requested or ('merlion','merlion_park'):
        sheet(target)
