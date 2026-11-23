"""Align Blender body joint frames to the existing motion GLB, preserving joint pivots.

Call align_body_motion_rest(rig, motion_glb) in OBJECT mode after applying object
transforms and before authoring gestures. Finger joint frames remain authored axes.
"""
from math import pi
import json
from pathlib import Path
import struct

import bpy
from mathutils import Matrix, Quaternion, Vector


def motion_world_rest(path):
    with Path(path).open('rb') as stream:
        magic, version, _ = struct.unpack('<4sII', stream.read(12))
        size, kind = struct.unpack('<I4s', stream.read(8))
        if (magic, version, kind) != (b'glTF', 2, b'JSON'):
            raise ValueError('Expected glTF 2.0 binary with a JSON first chunk.')
        document = json.loads(stream.read(size))
    nodes = document['nodes']
    parents = {child: i for i, node in enumerate(nodes) for child in node.get('children', ())}
    matching = {}
    cache = {}
    def world(index):
        if index in cache:
            return cache[index]
        node = nodes[index]
        if 'matrix' in node:
            values = node['matrix']
            local = Matrix([values[start:start+4] for start in range(0,16,4)]).transposed()
        else:
            x, y, z, w = node.get('rotation', (0,0,0,1))
            local = Matrix.LocRotScale(Vector(node.get('translation', (0,0,0))),
                                       Quaternion((w,x,y,z)), Vector(node.get('scale', (1,1,1))))
        # Blender's glTF importer/exporter rotate the world between Y-up and Z-up.
        base = world(parents[index]) if index in parents else Matrix.Rotation(pi/2, 4, 'X')
        cache[index] = base @ local
        return cache[index]
    for index, node in enumerate(nodes):
        if node.get('name', '').startswith('mixamorig:'):
            matching[node['name']] = world(index)
    return matching


def align_body_motion_rest(rig, motion_glb, include_wrists=True):
    rotations = motion_world_rest(motion_glb)
    if set(rotations) != set(rig.data.bones.keys()):
        raise ValueError('Source and target joint names must agree.')
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bones = rig.data.edit_bones
    # A Blender connected child shares its parent's tail. Source and target limb
    # lengths and centerlines differ. Unlink this geometric constraint to preserve
    # every real joint head while setting an independent local frame.
    connected = {b.name for b in bones if b.use_connect}
    for bone in bones:
        bone.use_connect = False
    heads = {b.name: b.head.copy() for b in bones}
    lengths = {b.name: b.length for b in bones}
    inverse = rig.matrix_world.inverted_safe()
    aligned = []
    for bone in bones:
        if 'Hand' in bone.name and (bone.name[-1].isdigit() or not include_wrists):
            continue
        rotation = (inverse @ rotations[bone.name]).to_quaternion().normalized()
        bone.head = heads[bone.name]
        bone.tail = bone.head + (rotation @ Vector((0,1,0)))*lengths[bone.name]
        bone.align_roll(rotation @ Vector((0,0,1)))
        aligned.append(bone.name)
    for name in connected:
        bone = bones[name]
        if (bone.head-bone.parent.tail).length < 1e-7:
            bone.use_connect = True
    drift = max((b.head-heads[b.name]).length for b in bones)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()
    if drift > 1e-6:
        raise ValueError(f'Joint pivots moved by {drift} m.')
    return {'aligned_joint_names': aligned, 'max_pivot_displacement_m': drift}
