"""Render matched, six-angle comparisons of original and final GLBs."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import MODELS, KIT, load, original

# Offsets put the game-ready geometry back on the reference drawing datum.
OFFSETS = {'hdb_coffee_shop': 1.525, 'provision_shop': 1.175, 'mrt_entrance': -.9}
VIEWS = {
    'front': (0,-1,0), 'street_oblique': (1,-1.55,.27), 'right': (1,0,0),
    'rear': (0,1,0), 'left': (-1,0,0), 'elevated': (-1.1,-1.4,1.15),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds(path):
    load(path)
    return [obj.matrix_world @ vertex.co for obj in bpy.context.scene.objects
            if obj.type == 'MESH' for vertex in obj.data.vertices]


def aim(obj, target):
    obj.rotation_euler = (target-obj.location).to_track_quat('-Z','Y').to_euler()


def setup(center, dimension):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 10
    scene.cycles.use_denoising = True
    scene.world = bpy.data.worlds.new('Neutral studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.72,.79,.88,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .43
    bpy.ops.mesh.primitive_plane_add(size=dimension * 200, location=(0,0,-.003))
    ground = bpy.data.materials.new('Review backdrop')
    ground.diffuse_color = (.49,.53,.55,1)
    bpy.context.object.data.materials.append(ground)
    for offset, strength, color, size in [
        ((-.8,-1.2,1.45), 200, (1,.92,.81), 1.7),
        ((1,-.6,.95), 105, (.82,.89,1), 1.5),
        ((.3,1.2,1.65), 140, (1,.96,.93), 1.4),
    ]:
        bpy.ops.object.light_add(type='AREA', location=center+Vector(offset)*dimension)
        lamp = bpy.context.object
        lamp.data.energy = strength * dimension**2
        lamp.data.color = color
        lamp.data.shape = 'DISK'
        lamp.data.size = size*dimension
        aim(lamp, center)
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.clip_end = dimension*200
    scene.render.resolution_x = scene.render.resolution_y = 400
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    return scene


def render(slug, candidate_only=False):
    stem = MODELS[slug][0]
    sources = (original(slug), KIT/f'{stem}.glb')
    offset = Vector((0,OFFSETS.get(stem,0),0))
    points = bounds(sources[0])+[point+offset for point in bounds(sources[1])]
    low = Vector([min(v[i] for v in points) for i in range(3)])
    high = Vector([max(v[i] for v in points) for i in range(3)])
    center, dimension = (low+high)/2, max(high-low)
    work = KIT/'.work'/stem
    work.mkdir(exist_ok=True)
    for label, path in zip(('original','kit'), sources):
        if label == 'original' and candidate_only:
            continue
        load(path)
        if label == 'kit':
            for obj in tuple(bpy.context.scene.objects):
                if obj.parent is None:
                    obj.location += offset
        scene = setup(center, dimension)
        for view, delta in VIEWS.items():
            direction = Vector(delta).normalized()
            orientation = (-direction).to_track_quat('-Z','Y')
            right, up = orientation @ Vector((1,0,0)), orientation @ Vector((0,1,0))
            uu, vv = ([axis.dot(point-center) for point in points] for axis in (right,up))
            target = center+right*((min(uu)+max(uu))/2)+up*((min(vv)+max(vv))/2)
            scene.camera.location = target+direction*(dimension*3)
            scene.camera.rotation_euler = orientation.to_euler()
            scene.camera.data.ortho_scale = 1.15*max(max(uu)-min(uu),max(vv)-min(vv))
            scene.render.filepath = str(work/f'{label}-{view}.png')
            bpy.ops.render.render(write_still=True)
    comparisons = KIT/'comparisons'
    comparisons.mkdir(exist_ok=True)
    sheet = comparisons/f'{stem}.png'
    tiles = [work/f'{label}-{view}.png' for start in (0,3)
             for label in ('original','kit') for view in list(VIEWS)[start:start+3]]
    layout = '|'.join(f'{(i%3)*404}_{(i//3)*404}' for i in range(12))
    arguments = ['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y']
    for path in tiles:
        arguments += ['-threads','1','-i',str(path)]
    arguments += ['-filter_complex_threads','1','-filter_complex',f'xstack=inputs=12:layout={layout}:fill=0x293239',
                  '-frames:v','1','-threads','1',str(sheet)]
    subprocess.run(arguments, check=True)
    evidence = {'reference': str(sources[0].relative_to(KIT.parents[2])), 'reference_sha256': digest(sources[0]),
                'candidate': sources[1].name, 'candidate_sha256': digest(sources[1]),
                'comparison': sheet.name, 'comparison_sha256': digest(sheet),
                'views': list(VIEWS), 'renderer': f'Blender {bpy.app.version_string} Cycles CPU',
                'samples': 10, 'threads': 2, 'tile_pixels': [400,400]}
    (work/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(f'SHEET {stem}', flush=True)


if __name__ == '__main__':
    arguments = sys.argv[sys.argv.index('--')+1:]
    for slug in [arg for arg in arguments if arg != '--candidate-only'] or MODELS:
        render(slug, '--candidate-only' in arguments)
