"""Measure exported sole contact with the documented forward controller speeds.

Run with Blender: blender -b --python-exit-code 1 --python audit_gait.py -- [model.glb] [--report-only]
"""
import json
import math
import os
import sys
import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
report_only = '--report-only' in args
paths = [a for a in args if a != '--report-only']
path = paths[0] if paths else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'character-motion.glb')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=path)
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
scene = bpy.context.scene

# Anchor samples are actual sole vertices dominated by each foot or toe group.
rig.data.pose_position = 'REST'
scene.frame_set(0)
graph = bpy.context.evaluated_depsgraph_get()
evaluated = mesh.evaluated_get(graph)
data = evaluated.to_mesh()
rest_positions = [evaluated.matrix_world @ v.co for v in data.vertices]
evaluated.to_mesh_clear()
rig.data.pose_position = 'POSE'
soles = {}
for side in ('Left', 'Right'):
    groups = {g.index for g in mesh.vertex_groups if side in g.name and ('Foot' in g.name or 'Toe' in g.name)}
    choices = [v.index for v in mesh.data.vertices if any(g.group in groups and g.weight > .5 for g in v.groups)]
    if not choices:
        raise ValueError('No weighted foot vertices for ' + side)
    bottom = min(rest_positions[i].z for i in choices)
    soles[side] = [i for i in choices if rest_positions[i].z < bottom + .008]

results = {}
for clip, steps, stance, stride in (('Walk_InPlace', 29, .60, .09), ('Run_InPlace', 20, .45, .105)):
    action = bpy.data.actions[clip]
    rig.animation_data.action = action
    start = float(action.frame_range[0])
    if abs(float(action.frame_range[1]) - start - steps) > .001:
        raise ValueError('Unexpected duration for ' + clip)
    speed = stride / (stance * steps / 24)
    rows = {side: [] for side in soles}
    swing_heights = {side: [] for side in soles}
    hips = []
    # Two cycles at half-frame intervals include a stance crossing the loop seam.
    for tick in range(steps * 4 + 1):
        t = tick / 2
        frame = start + t % steps
        scene.frame_set(math.floor(frame), subframe=frame % 1)
        graph = bpy.context.evaluated_depsgraph_get()
        evaluated = mesh.evaluated_get(graph)
        data = evaluated.to_mesh()
        hips.append(rig.matrix_world @ rig.pose.bones['mixamorig:Hips'].head)
        for side, offset in (('Left', 0), ('Right', .5)):
            phase = (t / steps + offset) % 1
            # Exclude transition edges; stance stability and swing are distinct phases.
            if .02 < phase < stance - .02:
                points = [evaluated.matrix_world @ data.vertices[i].co for i in soles[side]]
                x = sum(v.x for v in points) / len(points)
                y = sum(v.y for v in points) / len(points) - speed * t / 24
                z = min(v.z for v in points)
                rows[side].append((t, phase, x, y, z))
            elif stance + .05 < phase < .95:
                points = [evaluated.matrix_world @ data.vertices[i].co for i in soles[side]]
                swing_heights[side].append(min(v.z for v in points))
        evaluated.to_mesh_clear()
    sides = {}
    for side, samples in rows.items():
        segments, segment = [], []
        for sample in samples:
            if segment and (sample[0] - segment[-1][0] > .51 or sample[1] < segment[-1][1]):
                segments.append(segment)
                segment = []
            segment.append(sample)
        if segment:
            segments.append(segment)
        if len(samples) < 20 or not segments:
            raise ValueError('Insufficient stance samples for ' + clip + ' ' + side)
        drift = max(math.hypot(p[2] - seg[0][2], p[3] - seg[0][3]) for seg in segments for p in seg)
        low = min(p[4] for p in samples)
        high = max(p[4] for p in samples)
        sides[side] = {'samples': len(samples), 'max_drift_m': drift, 'min_height_m': low, 'max_height_m': high, 'swing_peak_m': max(swing_heights[side], default=0)}
    horizontal = max(max(v.x for v in hips) - min(v.x for v in hips), max(v.y for v in hips) - min(v.y for v in hips))
    endpoints = []
    for frame in (start, start + steps):
        scene.frame_set(math.floor(frame), subframe=frame % 1)
        evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        data = evaluated.to_mesh()
        endpoints.append([evaluated.matrix_world @ v.co for v in data.vertices])
        evaluated.to_mesh_clear()
    endpoint_error = max((a - b).length for a, b in zip(*endpoints))
    results[clip] = {'speed_m_s': speed, 'horizontal_hip_range_m': horizontal, 'endpoint_error_m': endpoint_error, 'feet': sides}

print('GAIT_AUDIT', json.dumps(results, sort_keys=True))
if not report_only:
    for clip, result in results.items():
        assert result['horizontal_hip_range_m'] < .001, clip + ': root moved horizontally'
        assert result['endpoint_error_m'] < .00001, clip + ': loop endpoints differ'
        for side, foot in result['feet'].items():
            assert foot['swing_peak_m'] > .02, clip + ' ' + side + ': swing foot does not lift'
            assert foot['max_drift_m'] < .004, clip + ' ' + side + ': stance drift exceeds 4 mm'
            assert foot['min_height_m'] >= -.001, clip + ' ' + side + ': sole penetrates by over 1 mm'
            assert foot['max_height_m'] <= .002, clip + ' ' + side + ': stance sole is over 2 mm above ground'
    print('GAIT_AUDIT PASS')
