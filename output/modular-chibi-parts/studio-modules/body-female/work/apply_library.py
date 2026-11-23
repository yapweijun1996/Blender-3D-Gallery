"""Recreate the named one-frame Blender actions and GLB directly from the editable JSON."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Euler, Matrix
OUT=Path(__file__).resolve().parent
def main():
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'body_female_v1.blend'),load_ui=False,use_scripts=False)
    rig=bpy.data.objects['Female_Rig']
    body=bpy.data.objects['Body_Female']
    library=json.loads((OUT/'hand_gestures_female.json').read_text())
    for action in list(bpy.data.actions):bpy.data.actions.remove(action)
    for name,rotations in library['gestures'].items():
        act=bpy.data.actions.new(name);act.use_fake_user=True;act.asset_mark()
        act.asset_data.description=name.split('_',1)[1].rsplit('_',1)[0].replace('_',' ')+' | '+('left' if name.endswith('_L') else 'right')+' hand, frame 1'
        slot=act.slots.new('OBJECT',rig.name)
        ad=rig.animation_data_create();ad.action=act;ad.action_slot=slot
        for bone,angles in rotations.items():
            pb=rig.pose.bones[bone]
            assert pb.rotation_mode=='QUATERNION'
            pb.rotation_quaternion=Euler(tuple(map(math.radians,angles)),'XYZ').to_quaternion()
            pb.keyframe_insert(data_path='rotation_quaternion',frame=1,group=bone)
        ad.action=None
        for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=str(OUT/'hand_gestures_female.glb'),export_format='GLB',use_selection=True,
        export_leaf_bone=False,export_rest_position_armature=True,export_def_bones=False,export_animations=True,
        export_animation_mode='ACTIONS',export_force_sampling=False,export_bake_animation=False,
        export_anim_single_armature=True,export_optimize_animation_size=False,
        export_frame_range=False,export_anim_slide_to_zero=True)
    body.select_set(True);rig.show_in_front=False
    # Open to a framed, material-colour front view; keep rig overlays out of the silhouette.
    from mathutils import Vector
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active;space.region_3d.view_distance=1.65
                space.region_3d.view_location=(0,0,.49)
                space.region_3d.view_rotation=Vector((0,1,0)).to_track_quat('-Z','Y')
                space.region_3d.view_perspective='ORTHO';space.overlay.show_overlays=False
                space.shading.color_type='TEXTURE'
    bpy.context.preferences.filepaths.save_version=0;bpy.context.preferences.filepaths.file_preview_type='NONE'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'body_female_v1.blend'))
if __name__=='__main__':main()
