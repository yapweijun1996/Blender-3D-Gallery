"""Import the supplied Tripo archive and export its two unmodified actions as GLB.

Run: blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python export.py
"""
import bpy
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
STEM = 'tripo_convert_1c818c0d-87d5-4ff0-a21c-bac7bb1956e7'
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
with TemporaryDirectory(prefix='tripo_fbx_') as directory:
    with ZipFile(HERE / (STEM + '.zip')) as archive:
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError('Unsafe ZIP entry')
        archive.extractall(directory)
    bpy.ops.import_scene.fbx(filepath=str(Path(directory) / (STEM + '.fbx')))
    rig = next(obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE')
    mesh = next(obj for obj in bpy.context.scene.objects if obj.type == 'MESH')
    # Keep the skin modifier while making the mesh a glTF scene root.
    # This avoids a skinned-mesh parent-transform warning in glTF viewers.
    world_matrix = mesh.matrix_world.copy()
    mesh.parent = None
    mesh.matrix_world = world_matrix
    actions = {}
    for action in bpy.data.actions:
        for name in ('run', 'sit'):
            if ('|' + name + '.') in action.name:
                if name in actions:
                    raise ValueError('Duplicate action: ' + name)
                actions[name] = action
    if set(actions) != {'run', 'sit'}:
        raise ValueError('Expected exactly run and sit actions')
    rig.animation_data_create()
    rig.animation_data.action = None
    for track in list(rig.animation_data.nla_tracks):
        rig.animation_data.nla_tracks.remove(track)
    for name, action in actions.items():
        track = rig.animation_data.nla_tracks.new()
        track.name = name
        start, end = action.frame_range
        strip = track.strips.new(name, int(start), action)
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

    # Preview a single clip in the editable file; the GLB already contains both.
    for track in rig.animation_data.nla_tracks:
        track.mute = True
    rig.animation_data.action = actions['sit']
    bpy.context.scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'character.blend'))
