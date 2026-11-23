"""Run supplied checks, full half-frame coverage and matching Cycles renders."""
from contextlib import redirect_stdout
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_shoes_v2 import (BANKS, HERE, PARTS, SHARED, V1, V2, digest, evaluated_points,
                         load_actions, master_scene, mount, pose, sample_times, topology,
                         tree_for, write_report)
from fit_shoes import MASTER, signed_hits

CHECKS = HERE / 'checks'
SUPPLIED = Path('/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/'
                '26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular')
CHECKER_SUITES = {
    'shared': (SUPPLIED, None),
    'sit_hold': (PARTS / 'body-fix/act', BANKS[1][0]),
    'carry': (PARTS / 'body-fix/act2', BANKS[2][0]),
}
VIEWS = (
    ('front', (0, -1, .16)),
    ('front_left', (.73, -.94, .48)),
    ('front_right', (-.73, -.94, .48)),
    ('side', (1, 0, .12)),
    ('back', (0, 1, .2)),
    ('underside', (0, -.15, -1)),
)


def supplied(suite, mode):
    directory, extra = CHECKER_SUITES[suite]
    stem = 'motion_check_tri' if mode == 'triangle' else 'motion_check'
    if suite == 'shared' and mode == 'vertex':
        stem += '_dense'
    path = directory / f'{stem}.py'
    out = CHECKS / suite / mode
    out.mkdir(parents=True, exist_ok=True)
    export_hash = digest(V2)
    sys.argv = [str(path), '--', str(MASTER), str(SHARED), str(V2), str(out)]
    if extra:
        sys.argv.append(str(extra))
    sys.path.insert(0, str(directory))
    # Leave the supplied geometry, frame ranges and preview cameras intact.
    if extra and mode == 'triangle':
        entry = directory / 'motion_check.py'
        source = entry.read_text()
        assert source.count('    garment_check()') == 1
        source = source.replace('    garment_check()', '    garment_check(triangles=True)')
    else:
        entry, source = path, path.read_text()
    marker = ("scene" if extra else "sc") + ".render.engine='BLENDER_WORKBENCH'"
    assert source.count(marker) == 1
    source = source.replace(marker, 'checker_cycles(scene)' if extra else 'checker_cycles(sc)')
    env = dict(__name__='__main__', __file__=str(entry), checker_cycles=checker_cycles)
    with (out / f'{stem}.txt').open('w') as log, redirect_stdout(log):
        exec(compile(source, str(entry), 'exec'), env)
    assert digest(V2) == export_hash
    manifest = dict(export_sha256=export_hash, master_sha256=digest(MASTER),
                    shared_motion_sha256=digest(SHARED),
                    extra_motion_sha256=digest(extra) if extra else None,
                    supplied_entry=str(path), supplied_entry_sha256=digest(path),
                    checker_implementation_sha256=digest(entry))
    if extra:
        manifest['chibi_sha256'] = digest(directory / 'chibi.py')
    write_report(out / 'inputs.json', manifest)


def checker_cycles(scene):
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 4
    scene.cycles.max_bounces = 2
    scene.cycles.use_denoising = True
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.world = bpy.data.worlds.new('Checker light')
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes['Background']
    background.inputs['Color'].default_value = (.74, .78, .85, 1)
    background.inputs['Strength'].default_value = .8


def distances(tree, points):
    return signed_hits(tree, points)[0]


def verify_native():
    _, master_arm, _ = master_scene()
    rotation_modes = {bone.name: bone.rotation_mode for bone in master_arm.pose.bones}
    file = V2.with_suffix('.blend')
    bpy.ops.wm.open_mainfile(filepath=str(file), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, boot = scene.objects['Armature'], scene.objects[V2.stem]
    images = {node.image for material in boot.data.materials for node in material.node_tree.nodes
              if node.type == 'TEX_IMAGE'}
    assert len(images) == 3 and all(image.packed_file and max(image.size) <= 1024 for image in images)
    assert {bone.name: bone.rotation_mode for bone in arm.pose.bones} == rotation_modes
    assert boot.parent == arm and any(mod.type == 'ARMATURE' and mod.object == arm
                                      for mod in boot.modifiers)
    assert not bpy.data.actions
    assert scene.objects['Base_Body'].hide_get()
    write_report(CHECKS / 'native_blend.json', dict(
        sha256=digest(file), triangles=len(topology(boot)), joints=len(arm.data.bones),
        rotation_modes_match_master=True, body_reference_hidden=True,
        packed_textures={image.name: list(image.size) for image in sorted(images, key=lambda i: i.name)},
        min_rest_z_m=float(evaluated_points(boot)[:, 2].min())))


def inspect_half_frames():
    export_hash = digest(V2)
    scene, arm, body = master_scene()
    boot = mount(V2, arm)
    arm.animation_data_create()
    for obj in list(scene.objects):
        if obj not in (arm, body, boot):
            obj.hide_viewport = True
    body_faces = topology(body).tolist()
    boot_faces = topology(boot).tolist()

    def measure(time):
        tree = tree_for(evaluated_points(body), body_faces)
        boot_points = evaluated_points(boot)
        signed = distances(tree, boot_points)
        return dict(frame=time, inside=int((signed < 0).sum()),
                    overlaps=len(tree.overlap(tree_for(boot_points, boot_faces))),
                    min_signed_m=float(signed.min()))

    pose(scene, arm, None, 1)
    details = {'rest': [measure(1.0)]}
    for idx, (file, names) in enumerate(BANKS):
        if idx:
            scene.render.fps = 30
            scene.render.fps_base = 1
        for name, action in load_actions(file, names).items():
            frames = []
            for time in sample_times(action):
                pose(scene, arm, action, time)
                frames.append(measure(time))
            details[name] = frames
            print('SAMPLED', name, len(frames), flush=True)
    summary = {}
    for clip, frames in details.items():
        closest = min(frames, key=lambda row: row['min_signed_m'])
        summary[clip] = dict(samples=len(frames), max_inside=max(row['inside'] for row in frames),
                             max_overlap_pairs=max(row['overlaps'] for row in frames),
                             min_signed_m=closest['min_signed_m'], closest_frame=closest['frame'])
        print('RESULT', clip, summary[clip], flush=True)
    assert digest(V2) == export_hash
    report = dict(export_sha256=export_hash, master_sha256=digest(MASTER),
                  clip_bank_sha256={file.name: digest(file) for file, _ in BANKS},
                  total_samples=sum(row['samples'] for row in summary.values()),
                  summary=summary, frames=details)
    write_report(CHECKS / 'half_frame_gate.json', report)
    assert all(row['max_inside'] == row['max_overlap_pairs'] == 0 and row['min_signed_m'] >= .0005
               for row in summary.values())


def setup_camera(scene, center, width, height):
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 5
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.film_transparent = False
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.world = bpy.data.worlds.new('Boot QA world')
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes['Background']
    background.inputs['Color'].default_value = (.72, .77, .85, 1)
    background.inputs['Strength'].default_value = .55
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    camera = bpy.data.objects.new('Boot QA camera', bpy.data.cameras.new('Boot QA camera'))
    camera.data.type = 'ORTHO'
    scene.collection.objects.link(camera)
    scene.camera = camera
    lights = (
        ('Soft key', (-.52, -.65, .82), 32, .75),
        ('Soft fill', (.72, -.39, .48), 15, .66),
        ('White rim', (.22, .61, .68), 26, .59),
        ('Sole fill', (-.18, .05, -.64), 12, .48),
    )
    for name, offset, power, size in lights:
        light = bpy.data.lights.new(name, 'AREA')
        light.energy, light.shape, light.size = power, 'DISK', size
        obj = bpy.data.objects.new(name, light)
        scene.collection.objects.link(obj)
        obj.location = center + Vector(offset)
        obj.rotation_euler = (-Vector(offset)).to_track_quat('-Z', 'Y').to_euler()
    return camera


def aim(camera, center, direction, scale):
    camera.location = center + Vector(direction)
    camera.rotation_euler = (-Vector(direction)).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = scale


def render(scene, path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def stitch(paths, columns, output):
    rows = math.ceil(len(paths) / columns)
    tiles = []
    for path in paths:
        image = bpy.data.images.load(str(path), check_existing=False)
        width, height = image.size
        pixels = np.empty(width * height * 4, np.float32)
        image.pixels.foreach_get(pixels)
        tiles.append(pixels.reshape(height, width, 4))
        bpy.data.images.remove(image)
    sheet = np.zeros((height * rows, width * columns, 4), dtype=np.float32)
    for i, tile in enumerate(tiles):
        row, col = rows - 1 - i // columns, i % columns
        sheet[row*height:(row+1)*height, col*width:(col+1)*width] = tile
    image = bpy.data.images.new(output.stem, sheet.shape[1], sheet.shape[0], alpha=False)
    image.pixels.foreach_set(sheet.ravel())
    image.filepath_raw = str(output)
    image.file_format = 'PNG'
    image.save()
    bpy.data.images.remove(image)


def prepare_scene(path):
    scene, arm, body = master_scene()
    boot = mount(path, arm)
    arm.animation_data_create()
    for obj in scene.objects:
        obj.hide_render = obj not in (body, boot)
    return scene, arm, body, boot


def views(version):
    source = V1 if version == 'v1' else V2
    evidence = HERE / 'visual'
    scratch = evidence / 'tiles'
    scratch.mkdir(exist_ok=True, parents=True)
    scene, arm, body, boot = prepare_scene(source)
    center = Vector((0, -.028, .066))
    body.hide_render = True
    camera = setup_camera(scene, center, 460, 360)
    tiles = []
    for name, direction in VIEWS:
        aim(camera, center, direction, .455)
        path = scratch / f'{version}_{name}.png'
        render(scene, path)
        tiles.append(path)
    output = HERE / 'fit_views_v2.png' if version == 'v2' else evidence / 'fit_views_v1.png'
    stitch(tiles, 3, output)
    for tile in tiles:
        tile.unlink()
    write_report(evidence / f'views_{version}.json', dict(
        glb_sha256=digest(source), image_sha256=digest(output), views=VIEWS,
        center=tuple(center), ortho_scale_m=.455, tile_px=[460, 360], engine='Cycles CPU',
        blender_version=bpy.app.version_string, samples=16, pose='rest'))


def deepest(version):
    import json
    evidence = HERE / 'visual'
    evidence.mkdir(exist_ok=True)
    fit = json.loads((HERE / 'fit_report.json').read_text())
    time = fit['baseline_deepest']['frame']
    source = V1 if version == 'v1' else V2
    scene, arm, body, boot = prepare_scene(source)
    run = load_actions(SHARED, ('run',))['run']
    pose(scene, arm, run, time)
    # Frame both boots from shared posed skin bounds, for matching before/after framing.
    rest = np.array([tuple(v.co) for v in body.data.vertices])
    posed = evaluated_points(body)[rest[:, 2] < .17]
    center = Vector((posed.min(axis=0) + posed.max(axis=0)) / 2)
    center.z += .018
    camera = setup_camera(scene, center, 720, 620)
    scene.cycles.samples = 12
    direction = (.92, -.85, .37)
    aim(camera, center, direction, .54)
    picture = HERE / 'run_deepest_v2.png' if version == 'v2' else evidence / 'run_deepest_v1.png'
    render(scene, picture)
    tree = tree_for(evaluated_points(body), topology(body).tolist())
    signed = distances(tree, evaluated_points(boot))
    write_report(evidence / f'run_deepest_{version}.json', dict(
        glb_sha256=digest(source), image_sha256=digest(picture), motion_sha256=digest(SHARED),
        frame=time, max_inside=int((signed < 0).sum()), min_signed_m=float(signed.min()),
        direction=direction, center=tuple(center), ortho_scale_m=.54, engine='Cycles CPU',
        blender_version=bpy.app.version_string, samples=scene.cycles.samples))


if __name__ == '__main__':
    mode, *args = sys.argv[sys.argv.index('--') + 1:]
    CHECKS.mkdir(exist_ok=True)
    commands = {'checker': supplied, 'half-frames': inspect_half_frames,
                'views': views, 'deepest': deepest, 'native': verify_native}
    commands[mode](*args)
