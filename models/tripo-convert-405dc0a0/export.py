"""Import the supplied Tripo FBX and export the original walk Action."""

from pathlib import Path
from stat import S_IFREG, S_IFMT
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import bpy

HERE = Path(__file__).resolve().parent
STEM = 'tripo_convert_405dc0a0-5953-4840-91af-c1d285541ecd'
FBX = f'{STEM}.fbx'
TEXTURE = f'{STEM}.fbm/tripo_rgb_47b0b0be-5a92-4f81-a124-809f20dd8d87.jpg'


def extract_source(directory):
    with ZipFile(HERE / f'{STEM}.zip') as archive:
        entries = archive.infolist()
        if len(entries) != 2 or {item.orig_filename for item in entries} != {FBX, TEXTURE}:
            raise ValueError('Unexpected or unsafe ZIP entry; expected only the original FBX and JPEG paths')
        if any(S_IFMT(item.external_attr >> 16) not in (0, S_IFREG) for item in entries):
            raise ValueError('ZIP entries must be regular files')
        archive.extractall(directory, entries)


def import_character(directory):
    extract_source(directory)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(Path(directory) / FBX), use_image_search=False)
    rig, = (obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE')
    mesh, = (obj for obj in bpy.context.scene.objects if obj.type == 'MESH')
    action, = bpy.data.actions
    if action.name != 'Armature|walk.001' or tuple(action.frame_range) != (1, 57):
        raise ValueError('Expected the sole source Action Armature|walk.001 on frames 1–57')
    return rig, mesh, action


def export_character(directory):
    rig, mesh, action = import_character(directory)

    # Keep the skin modifier and world transform as the mesh becomes a glTF scene root.
    world_matrix = mesh.matrix_world.copy()
    mesh.parent = None
    mesh.matrix_world = world_matrix

    animation = rig.animation_data
    slot = animation.action_slot
    animation.action = None
    for track in list(animation.nla_tracks):
        animation.nla_tracks.remove(track)
    track = animation.nla_tracks.new()
    track.name = 'walk'
    start, end = action.frame_range
    strip = track.strips.new('walk', int(start), action)
    strip.action_slot = slot
    strip.action_frame_start = start
    strip.action_frame_end = end

    bpy.ops.file.pack_all()
    bpy.ops.object.select_all(action='DESELECT')
    for obj in (rig, mesh):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=str(HERE / 'character.glb'), export_format='GLB',
                              use_selection=True, export_animations=True,
                              export_animation_mode='NLA_TRACKS')

    # Make the original Action directly editable and playable in Blender.
    track.mute = True
    animation.action = action
    animation.action_slot = slot
    scene = bpy.context.scene
    scene.frame_start = int(start)
    scene.frame_end = int(end)
    scene.frame_set(int(start))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'character.blend'))


if __name__ == '__main__':
    with TemporaryDirectory(prefix='tripo_fbx_') as source_directory:
        export_character(source_directory)
