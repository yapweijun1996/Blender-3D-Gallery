"""Measure skin continuity during original Mixamo Actions on the exported male body.

Run inside Blender 5 with -- <body.glb> <motion.glb> <output-dir>.
The script only changes a temporary scene. Original Actions bind through their slots.
"""
import argparse
from collections import defaultdict
import hashlib
import itertools
import json
from math import degrees, radians
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector
import numpy as np

CLIPS = ('walk', 'run', 'wave', 'jump', 'idle', 'nod', 'dance')
RENDERS = {'run': (8, (0.68, -1.0, 0.12)), 'wave': (19, (-0.22, -1, 0.1)),
           'jump': (9, (0.55, -1, 0.09)), 'joint_bends': (0, (0.9, -1, 0.09))}
STRESS = {
    'LeftArm': ('Y', 58), 'LeftForeArm': ('Z', -82),
    'RightArm': ('Y', -34), 'RightForeArm': ('Z', 32),
    'LeftUpLeg': ('X', -62), 'LeftLeg': ('X', 88),
    'RightUpLeg': ('X', 12), 'RightLeg': ('X', 20),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def imported(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), import_pack_images=True)
    objects = set(bpy.data.objects) - before
    rig, = [o for o in objects if o.type == 'ARMATURE']
    body, = [o for o in objects if o.type == 'MESH' and o.find_armature() == rig]
    return rig, body, objects


def world_coords(obj, evaluated=True):
    obj = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()) if evaluated else obj
    vertices = obj.data.vertices
    coords = np.empty(3 * len(vertices), dtype=np.float32)
    vertices.foreach_get('co', coords)
    matrix = np.array(obj.matrix_world)
    return coords.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3]


def edge_lengths(coords, ends):
    return np.linalg.norm(coords[ends[:, 0]] - coords[ends[:, 1]], axis=1)


def prepare(body, rig):
    rest = world_coords(body, evaluated=False)
    edges = np.array([tuple(e.vertices) for e in body.data.edges], dtype=np.int32)
    # UV, normal, material and disconnected-source splits all count when coincident.
    groups = defaultdict(list)
    for index, p in enumerate(rest):
        groups[tuple(np.round(p, 7))].append(index)
    seams = np.array([e for ids in groups.values() for e in itertools.combinations(ids, 2)],
                     dtype=np.int32).reshape(-1, 2)
    lengths = edge_lengths(rest, edges)
    edges, lengths = edges[lengths >= .0005], lengths[lengths >= .0005]
    middle = np.mean(rest[edges], axis=1)
    zones = {}
    for joint, label in [('Arm', 'shoulder'), ('ForeArm', 'elbow'),
                         ('UpLeg', 'hip'), ('Leg', 'knee')]:
        pivots = [rig.matrix_world @ rig.data.bones['mixamorig:' + side + joint].head_local
                  for side in ('Left', 'Right')]
        mask = np.minimum(*[np.linalg.norm(middle - np.array(pivot), axis=1)
                            for pivot in pivots]) <= (.08 if label == 'hip' else .055)
        zones[label] = np.flatnonzero(mask)
    zones['wrist'] = np.flatnonzero((np.abs(middle[:,0])>.245) & (np.abs(middle[:,0])<.345))
    return rest, edges, lengths, seams, zones


def studio():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 14
    scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 4
    scene.render.resolution_x, scene.render.resolution_y = 640, 704
    scene.render.resolution_percentage = 100
    scene.render.use_compositing = False
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    world = bpy.data.worlds.new('Motion QA backdrop')
    world.use_nodes = True
    scene.world = world
    bg = world.node_tree.nodes['Background']
    bg.inputs[0].default_value = (.21, .275, .355, 1)
    bg.inputs[1].default_value = .62
    camera_data = bpy.data.cameras.new('Motion QA camera')
    camera_data.type = 'ORTHO'
    camera_data.clip_start = .01
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    lights = []
    for name, energy, size, color in [
        ('Key', 36, 1.2, (1, .90, .82)), ('Fill', 19, 1.4, (.80, .89, 1)),
        ('Rim', 29, .9, (1, .94, .84))]:
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.size, data.color = energy, size, color
        lamp = bpy.data.objects.new(name, data)
        scene.collection.objects.link(lamp)
        lights.append(lamp)
    return scene, camera, lights


def render(name, frame, coords, output, setup):
    scene, cam, lights = setup
    direction = Vector(RENDERS[name][1]).normalized()
    right = Vector((0, 0, 1)).cross(direction).normalized()
    up = direction.cross(right).normalized()
    rotation = Matrix((right, up, direction)).transposed()
    basis = np.stack((right, up, direction), axis=0)
    projected = coords @ basis.T
    lower, upper = projected.min(axis=0), projected.max(axis=0)
    center = Vector((0, 0, 0))
    for axis, mid in zip((right, up, direction), (lower + upper) * .5):
        center += axis * mid
    cam.data.ortho_scale = max((upper[0]-lower[0])*704/640, upper[1]-lower[1])*1.15
    cam.rotation_euler = rotation.to_euler()
    cam.location = center + direction * 3
    for lamp, (x, y, z) in zip(lights, [(-.8, 1.0, 1.2), (.82, .24, .82), (.55, .9, -.9)]):
        lamp.location = center + right*x + up*y + direction*z
        lamp.rotation_euler = (center - lamp.location).to_track_quat('-Z', 'Y').to_euler()
    image = output / f'{name}_frame_{frame:03}.png'
    scene.render.filepath = str(image)
    bpy.ops.render.render(write_still=True)
    return {'file': image.name, 'sha256': sha256(image), 'frame': frame,
            'camera_direction': list(direction), 'ortho_scale_m': cam.data.ortho_scale}


def stress(rig):
    for name, (axis, angle) in STRESS.items():
        bone = rig.pose.bones['mixamorig:' + name]
        basis = (rig.matrix_world @ bone.bone.matrix_local).to_quaternion().normalized()
        bone.rotation_quaternion = basis.inverted() @ Quaternion(axis_vector(axis), radians(angle)) @ basis
    bpy.context.view_layer.update()


def axis_vector(axis):
    return Vector(tuple(int(component == axis) for component in 'XYZ'))


def run(body_file, motion_file, out, no_renders):
    out.mkdir(exist_ok=True, parents=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rig, body, _ = imported(body_file)
    source, _, source_objects = imported(motion_file)
    for ob in source_objects:
        ob.hide_render = True
    rigs = (source, rig)
    hierarchy = [{b.name: b.parent.name if b.parent else None for b in r.pose.bones} for r in rigs]
    if hierarchy[0] != hierarchy[1] or len(hierarchy[0]) != 65:
        raise ValueError('Input Mixamo joint hierarchies disagree')
    channels = {t.name: (t.strips[0].action, t.strips[0].action_slot)
                for t in source.animation_data.nla_tracks}
    if set(channels) != set(CLIPS):
        raise ValueError('Unexpected motion library')
    # The imported source keeps NLA tracks. Only the target receives the Action under test.
    for t in source.animation_data.nla_tracks:
        t.mute = True
    source.animation_data.action = None
    animation = rig.animation_data_create()
    for t in animation.nla_tracks:
        t.mute = True
    if any(b.rotation_mode != 'QUATERNION' for b in rig.pose.bones):
        raise ValueError('Expected the target importer to preserve quaternion mode')
    rest, edges, lengths, seams, zones = prepare(body, rig)
    report = {'body_sha256': sha256(body_file), 'body_file': body_file.name,
              'motion_sha256': sha256(motion_file), 'blender_version': bpy.app.version_string,
              'joint_hierarchy_matches': True, 'vertices': len(rest), 'seam_pairs': len(seams),
              'edge_counts': dict(all=len(edges), **{z:len(e) for z,e in zones.items()}),
              'method': 'Direct original Action + action_slot on target, sampled every integer frame inclusive at 24 fps. '
                        'Tear diagnostic measures separation of pairs coincident within a 0.1 micrometre rounded grid in rest pose. '
                        'Edge strain uses edges of at least 0.5 mm rest length, with hip zone within 80 mm and shoulder, elbow and knee zones within 55 mm of bilateral pivots. '
                        'Wrist strain uses both rest-space x strips from 245 to 345 mm lateral. An intact shared edge can stretch without creating a seam. '
                        'Renders use the complete imported target, its materials, orthographic three-quarter views and Cycles CPU.',
              'clips': {}, 'images': {}, 'joint_bend_degrees': STRESS}
    scene = bpy.context.scene
    setup = None if no_renders else studio()
    transfer = []
    differences = {}
    for bone in rig.pose.bones:
        source_bone = source.pose.bones[bone.name]
        source_basis = (source.matrix_world @ source_bone.bone.matrix_local).to_3x3()
        body_basis = (rig.matrix_world @ bone.bone.matrix_local).to_3x3()
        conversion = body_basis.inverted() @ source_basis
        rotation = conversion.to_quaternion().normalized()
        transfer.append((bone, source_bone, rotation, rotation.inverted(), conversion))
        differences[bone.name] = degrees(2*np.arccos(np.clip(abs(rotation.w), 0, 1)))
    report['rest_basis_difference_degrees'] = differences
    report['raw_direct_clips'] = {}
    aligned = max(angle for name, angle in differences.items() if not name[-1].isdigit()
                  or 'Hand' not in name) < .1
    capture_mode = 'direct' if aligned else 'rest_basis'
    report['render_playback_mode'] = capture_mode
    report['method'] += (' Both the untouched local-quaternion assignment and source-to-target world-rest-basis transfer '
                         'are evaluated. Images show direct binding if all 25 nonfinger frames differ by under 0.1 degree, otherwise the transfer. '
                         'Local joint translations are converted through the corresponding 3x3 rest-basis transformation. '
                         'Only evaluation changes; no retargeted Action is saved in either delivered asset.')
    for mode, name in ([('direct', clip) for clip in CLIPS] +
                       [('rest_basis', clip) for clip in CLIPS] + [('stress', 'joint_bends')]):
        animation.action = None
        source.animation_data.action = None
        for skeleton in (rig, source):
            for b in skeleton.pose.bones:
                b.matrix_basis = Matrix.Identity(4)
        if name in channels:
            action, slot = channels[name]
            owner = animation if mode == 'direct' else source.animation_data
            owner.action = action
            owner.action_slot = slot
            bag = action.layers[0].strips[0].channelbag(slot)
            if any('rotation_euler' in curve.data_path for curve in bag.fcurves):
                raise ValueError('Unexpected Euler data')
            start, end = (int(round(x)) for x in action.frame_range)
            child = {'slot': slot.name_display, 'quaternion_fcurves': sum(
                'rotation_quaternion' in c.data_path for c in bag.fcurves)}
        else:
            stress(rig)
            start = end = 0
            child = {'slot': None}
        child.update(frames=[start,end], count=end-start+1, max_seam_gap_mm=0,
                     max_seam_pairs_over_0p1mm=0, max_seam_pairs_over_0p5mm=0,
                     max_edge_stretch_ratio={}, max_vertices_displacement_mm=0,
                     min_z_m=None, max_sole_z_m=None)
        target = report['raw_direct_clips'] if mode == 'direct' else report['clips']
        target[name] = child
        for frame in range(start, end+1):
            scene.frame_set(frame)
            if mode == 'rest_basis':
                for bone, source_bone, basis, inverse, conversion in transfer:
                    bone.rotation_quaternion = basis @ source_bone.rotation_quaternion @ inverse
                    bone.location = conversion @ source_bone.location
                    bone.scale = source_bone.scale
                bpy.context.view_layer.update()
            if name == 'wave' and frame == 19:
                elbow, wrist = (rig.matrix_world @ rig.pose.bones['mixamorig:Right'+joint].head
                                for joint in ('ForeArm', 'Hand'))
                child['frame_19_right_wrist_above_elbow_mm'] = 1000*(wrist.z-elbow.z)
            coords = world_coords(body)
            assert np.isfinite(coords).all()
            gap = edge_lengths(coords, seams)*1000
            if len(gap):
                child['max_seam_gap_mm'] = max(child['max_seam_gap_mm'], float(gap.max()))
                for limit,key in ((.1,'max_seam_pairs_over_0p1mm'),(.5,'max_seam_pairs_over_0p5mm')):
                    child[key] = max(child[key], int(np.count_nonzero(gap>limit)))
            strain = edge_lengths(coords, edges)/lengths
            for region, indices in dict(all=slice(None), **zones).items():
                maximum = float(strain[indices].max())
                if maximum>child['max_edge_stretch_ratio'].get(region,{}).get('ratio',0):
                    edge_i=int(np.argmax(strain)) if region=='all' else int(indices[np.argmax(strain[indices])])
                    child['max_edge_stretch_ratio'][region] = {
                        'ratio':maximum, 'frame':frame, 'rest_edge_mm':float(lengths[edge_i]*1000),
                        'rest_midpoint_m':[float(v) for v in rest[edges[edge_i]].mean(axis=0)]}
            height = float(coords[:,2].min())
            child['min_z_m'] = min(height, child['min_z_m']) if child['min_z_m'] is not None else height
            child['max_sole_z_m'] = max(height, child['max_sole_z_m']) if child['max_sole_z_m'] is not None else height
            child['max_vertices_displacement_mm'] = max(
                child['max_vertices_displacement_mm'], float(np.linalg.norm(coords-rest, axis=1).max()*1000))
            if setup and mode in (capture_mode, 'stress') and name in RENDERS and RENDERS[name][0] == frame:
                report['images'][name] = render(name,frame,coords,out,setup)
        assert child['max_vertices_displacement_mm'] > 1.0, f'Unevaluated Action: {name}'
        print(mode, name, child, flush=True)
    assert all(b.rotation_mode=='QUATERNION' for b in rig.pose.bones)
    report['all_rotation_modes_quaternion'] = True
    (out/'motion_check.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('body',type=Path)
    parser.add_argument('motion',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--no-renders', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    run(args.body.resolve(), args.motion.resolve(), args.output.resolve(), args.no_renders)
