"""Rebuild the second-pass source and its two GLBs from the read-only first pass."""
import json
import math
import sys
from pathlib import Path
import bpy
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hand_common import OUT, clean_pose, run_batch
from round2_mesh import refine_dorsum, soften_pads, distribute_proximal_flex


def main():
    bpy.ops.wm.open_mainfile(filepath=str(OUT.parent/'hands_gestures.blend'),load_ui=False,use_scripts=False)
    rig=bpy.data.objects['Armature']
    body=bpy.data.objects['Base_Body']
    clean_pose(rig)
    refine_dorsum(body)
    soften_pads(body,rig)
    distribute_proximal_flex(body,rig)
    library=json.loads((OUT/'hand_gestures.json').read_text())
    for name, angles in library['gestures'].items():
        action=bpy.data.actions[name]
        data=rig.animation_data_create()
        data.action=action
        data.action_slot=action.slots[0]
        for bone,deg in angles.items():
            pb=rig.pose.bones[bone]
            pb.rotation_mode='XYZ'
            pb.rotation_euler=[math.radians(v) for v in deg]
            pb.keyframe_insert(data_path='rotation_euler',frame=1,group=bone)
        for bone, scale in library.get('scales',{}).get(name,{}).items():
            pb=rig.pose.bones[bone]
            pb.scale=scale
            pb.keyframe_insert(data_path='scale',frame=1,group=bone)
    clean_pose(rig)
    bpy.context.scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version=0
    bpy.context.preferences.filepaths.file_preview_type='NONE'
    bpy.ops.object.select_all(action='DESELECT')
    for ob in (body,rig):ob.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'hands_gestures.blend'))
    opts=dict(export_format='GLB',use_selection=True,export_def_bones=False,export_leaf_bone=False,export_rest_position_armature=True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/'base_body.glb'),export_animations=False,export_influence_nb=4,**opts)
    body.select_set(False)
    bpy.ops.export_scene.gltf(filepath=str(OUT/'hand_gestures.glb'),export_animations=True,export_animation_mode='ACTIONS',
                              export_force_sampling=False,export_bake_animation=False,export_anim_single_armature=True,
                              export_optimize_animation_size=False,export_frame_range=False,export_negative_frame='SLIDE',
                              export_anim_slide_to_zero=True,**opts)
def embed_previews():
    from render_hands import CACHE, sha
    expected=json.loads((CACHE/'exports.json').read_text())
    assert all(sha(OUT/f)==h for f,h in expected.items())
    path=OUT/'hands_gestures.blend'
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    bpy.context.preferences.filepaths.save_version=0
    bpy.context.preferences.filepaths.file_preview_type='NONE'
    for action in bpy.data.actions:
        name=action.name
        if not name.startswith('hand_'):continue
        view='thumb-side' if 'grip_small' in name else 'palm'
        im=bpy.data.images.load(str(CACHE/(name+'_'+view+'.png')),check_existing=False)
        im.colorspace_settings.name='Non-Color'
        preview=action.preview_ensure()
        for attr,sz in [('image',(256,224)),('icon',(32,28))]:
            im.scale(*sz)
            setattr(preview,attr+'_size',sz)
            getattr(preview,attr+'_pixels_float')[:]=im.pixels[:]
        bpy.data.images.remove(im)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))


if __name__=='__main__':run_batch(embed_previews if '--embed-previews' in sys.argv else main)
