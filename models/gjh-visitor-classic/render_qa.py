"""Render the exported model in a clean Blender scene at locked orbit angles."""
import bpy
import math
import os
import sys
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from build import studio,camera_view,GLB

bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
studio(sc)
bpy.ops.import_scene.gltf(filepath=str(HERE/'exports'/GLB))
rig=next(o for o in sc.objects if o.type=='ARMATURE')
anim=rig.animation_data
if anim:
    anim.action=None
    for track in anim.nla_tracks:
        track.mute=True
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
sc.frame_set(0)
out=Path(os.getenv('QA_DEST',str(HERE/'qa')))
out.mkdir(parents=True,exist_ok=True)
sc.render.resolution_percentage=int(os.getenv('QA_RES','100'))
sc.cycles.samples=int(os.getenv('QA_SAMPLES','16'))
views={'front':0,'portrait':18,'three-quarter':-32,'profile':-88,'back':180,'back-quarter':138}
for label in os.getenv('QA_VIEWS','front,portrait,three-quarter,profile,back').split(','):
    if label in views:
        camera_view(sc,views[label])
    else:
        angle=59 if label=='sit' else -30
        camera_view(sc,angle)
        for track in anim.nla_tracks: track.mute=True
        strip=next(track.strips[0] for track in anim.nla_tracks if track.name.split('.')[0]==label)
        anim.action=strip.action
        anim.action_slot=strip.action_slot
        sc.frame_set(round(strip.frame_end if label=='sit' else strip.frame_start+(strip.frame_end-strip.frame_start)*.22))
        if label=='sit':
            bpy.ops.mesh.primitive_cube_add(size=1,location=(0,.20,.071125))
            seat=bpy.context.object;seat.name='Seat contact fixture'
            seat.dimensions=(.38,.31,.14225); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
            bevel=seat.modifiers.new('Edge finish','BEVEL');bevel.width=.006;bevel.segments=2
            mat=bpy.data.materials.new('Seat • amber');mat.diffuse_color=(.52,.32,.19,1);seat.data.materials.append(mat)
    sc.render.filepath=str(out/(label+'.png'))
    bpy.ops.render.render(write_still=True)
    if label=='sit':
        bpy.data.objects.remove(seat,do_unlink=True)

# Collection instances share the exact rest-pose GLB geometry across all three views.
if os.getenv('QA_BOARD')=='1':
    anim.action=None
    for track in anim.nla_tracks:
        track.mute=True
    from mathutils import Matrix
    for bone in rig.pose.bones:
        bone.matrix_basis=Matrix.Identity(4)
    sc.frame_set(0)
    subject=bpy.data.collections.new('Classic visitor turntable')
    for ob in list(sc.objects):
        if ob==rig or (ob.type=='MESH' and ob.get('partSlot')):
            for collection in list(ob.users_collection):
                collection.objects.unlink(ob)
            subject.objects.link(ob)
    for label,x,angle in [('Front',-.83,8),('Profile',0,-79),('Back',.83,174)]:
        turn=bpy.data.objects.new(label,None)
        turn.instance_type='COLLECTION';turn.instance_collection=subject
        sc.collection.objects.link(turn)
        turn.location.x=x; turn.rotation_euler.z=math.radians(angle)
    camera_view(sc,0)
    sc.camera.data.ortho_scale=2.80
    sc.render.resolution_x=1600;sc.render.resolution_y=860
    sc.render.resolution_percentage=100;sc.cycles.samples=24
    sc.render.filepath=str(out/'turnaround.png')
    bpy.ops.render.render(write_still=True)
