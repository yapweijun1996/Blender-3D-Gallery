"""Compose the trial fits into the demo's glTF configuration."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fit_geometry import *

def config(stage):
    result = dict(schema_version=1, units='metres', coordinates='glTF Y-up', quaternion_order='xyzw',
                  composition='joint world matrix × socket local TRS; replace the prop node TRS',
                  sockets={}, chair={})
    for name, (asset,node,reference,fps,end) in PROPS.items():
        trial_path=HERE/(name+'.trial.json')
        if not trial_path.exists():
            continue
        fit=json.loads(trial_path.read_text())
        item=dict(clip=name,prop=asset.relative_to(PARTS).as_posix(),node=node,bone=N+'RightHand',
                  gltf_joint_local=fit['socket'],left_hand='none',source_fps=fps)
        key=name if name!='take_item' else 'jar'
        result['sockets'][key]=item
        if name=='hold_box':
            item['left_hand']='baked support; use a single rigid right-hand parent'
        if name!='take_item':
            continue
        prop=stage.asset(asset)[node]
        p=points(prop)
        stage.frame(name,PICK)
        pick=stage.hand(PICK) @ trs(item['gltf_joint_local']) @ G
        stage.frame(name,end/fps)
        release=stage.hand(end/fps) @ trs(item['gltf_joint_local']) @ G
        pick_v=transform(p,pick)
        return_stop=pick.copy()
        # Slide over the single rail toward the most recent release Y position.
        return_stop.translation.x=pick.translation.x
        return_stop.translation.y=release.translation.y
        # Keep the two static stops level at their lowest surface witnesses.
        return_v=transform(p,return_stop)
        pick_low=pick_v[pick_v[:,2]<=pick_v[:,2].min()+.00020].mean(0)
        return_low=return_v[return_v[:,2]<=return_v[:,2].min()+.00020].mean(0)
        deck_height=float(pick_v[:,2].min())-.00007
        center=(pick_low+return_low)/2
        # Place the jar near the rail's left edge so it can clear the support
        # as the baked wrist pulls back and down.
        width_scale=.52
        deck_left=float(pick_low[0])-.00080
        rail_center_x=deck_left+.050*width_scale
        shelf_matrix=Matrix.Diagonal(Vector((width_scale,1,deck_height/.442,1)))
        shelf_matrix.translation.x=rail_center_x+.1455*width_scale
        shelf_matrix.translation.y=float(center[1]+.179)
        lift=return_stop.copy()
        lift.translation.x=min(release.translation.x,return_stop.translation.x)-.018
        lift.translation.z+=.013
        item['shelf']=dict(node='Display rail',fps=24,cycle_frames=48,attach_frame=29,
                           attach_seconds=29/24,release_frame=0,reset_lift_frame=4,return_frames=[8,18],
                           return_interpolation='smoothstep position and quaternion slerp',
                           first_play='Hold at pickup_stop_gltf until attach_frame.',
                           repeat_play='Release at release_pose_gltf on frame 0; lift to reset_lift_stop_gltf at frame 4; settle to return_stop_gltf at frame 8; slide to pickup_stop_gltf by frame 18; attach on frame 29.',
                           world_gltf=record(G@shelf_matrix@B,scale=True),
                           pickup_stop_gltf=record(G@pick@B),
                           return_stop_gltf=record(G@return_stop@B),
                           release_pose_gltf=record(G@release@B),
                           reset_lift_stop_gltf=record(G@lift@B),
                           deck_height_m=deck_height)
    chair=HERE/'chair.trial.json'
    if chair.exists():
        placement=json.loads(chair.read_text())
        result['chair']=dict(prop='actions-astra/chair.glb',node='Chair',world_gltf=placement,
                             seat_top_m=float((trs(placement)@Vector((0,.252,0))).y),clips=list(CHAIR),
                             scale_pivot='chair asset floor origin')
    return result

if __name__=='__main__':
    (HERE/'sockets_female.json').write_text(json.dumps(config(Stage()),indent=2)+'\n')
