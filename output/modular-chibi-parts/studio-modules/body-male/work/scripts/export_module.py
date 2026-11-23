"""Rebuild the body and clips from the generated mesh and the delivered pose JSON."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]


def select(items, armature):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in items:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armature


def clear(armature):
    armature.animation_data_create().action = None
    for bone in armature.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT)
    parser.add_argument('--poses', type=Path, default=ROOT / 'hand_gestures_male.json')
    options = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    out = options.output_dir.resolve()
    if out != ROOT and ROOT not in out.parents:
        raise ValueError('Output must be inside the module workspace.')
    out.mkdir(parents=True, exist_ok=True)
    library = json.loads(options.poses.read_text())
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / '.build/body_raw.blend'), load_ui=False, use_scripts=False)
    armature = bpy.data.objects['Armature']
    body = bpy.data.objects['Body_Male']
    for name, bones in library['gestures'].items():
        clear(armature)
        action = bpy.data.actions.new(name)
        action.use_fake_user = True
        action.asset_mark()
        gesture, suffix = name[5:].rsplit('_', 1)
        action.asset_data.description = ('Left' if suffix == 'L' else 'Right') + ' hand • ' + gesture.replace('_', ' ')
        data = armature.animation_data_create()
        data.action = action
        data.action_slot = action.slots.new('OBJECT', armature.name)
        for bone_name, degrees in bones.items():
            bone = armature.pose.bones[bone_name]
            assert bone.rotation_mode == 'QUATERNION'
            bone.rotation_quaternion = Euler([math.radians(v) for v in degrees], 'XYZ').to_quaternion()
            bone.keyframe_insert('rotation_quaternion', frame=1, group=bone_name)

    clear(armature)
    bpy.context.scene.frame_set(1)
    select([body, armature], armature)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.preferences.filepaths.file_preview_type = 'NONE'
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                space.region_3d.view_rotation = Quaternion((1, 0, 0), math.pi/2)
                space.region_3d.view_distance = 1.75
                space.region_3d.view_location = Vector((0, 0, .49))
                space.region_3d.view_perspective = 'ORTHO'
                space.overlay.show_overlays = False
                space.shading.color_type = 'TEXTURE'
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'body_male_v1.blend'))

    opts = dict(export_format='GLB', use_selection=True, export_def_bones=False,
                export_leaf_bone=False, export_rest_position_armature=True)
    # Separate scene roots comply with Khronos skin semantics. The Armature modifier
    # continues to identify the exact rig during export.
    body.parent = None
    body.matrix_world = Matrix.Identity(4)
    bpy.ops.export_scene.gltf(filepath=str(out / 'body_male_v1.glb'), export_animations=False,
                              export_influence_nb=4, export_tangents=True, **opts)
    body.parent = armature
    body.matrix_parent_inverse = Matrix.Identity(4)
    body.matrix_basis = Matrix.Identity(4)
    select([armature], armature)
    bpy.ops.export_scene.gltf(filepath=str(out / 'hand_gestures_male.glb'), export_animations=True,
                              export_animation_mode='ACTIONS', export_anim_single_armature=True,
                              export_force_sampling=False, export_bake_animation=False,
                              export_optimize_animation_size=False, export_frame_range=False,
                              export_negative_frame='SLIDE', export_anim_slide_to_zero=True, **opts)


if __name__ == '__main__':
    main()
