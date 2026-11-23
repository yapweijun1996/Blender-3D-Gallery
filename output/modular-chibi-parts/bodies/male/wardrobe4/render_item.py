"""Capture six bind-pose views of the selected GLB with the shipped outfit."""
from pathlib import Path
import sys

from asset_io import HERE, MOTION, bpy, write_json
from body_audit import load_body_motion, set_frame, use_action
from fit_module import read_module
from gate_module import BODY, BOOTS, companions, grids, sha
from render_modules import VIEWS, baked, contact_sheet, crop_views, studio


def render(path, name, item=None):
    item = item or name
    scene, arm, _, actions = load_body_motion(MOTION)
    bpy.context.scene.objects['Base_Body'].hide_render = True
    refs = tuple(ref for ref in companions(item) if ref != BOOTS)
    objects = [read_module(file,arm) for file in (BODY,path,*refs)]
    use_action(arm,None)
    set_frame(scene,0)
    folder = HERE/'renders'/name
    folder.mkdir(parents=True,exist_ok=True)
    ink = studio(scene)
    scene.cycles.samples = 6
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    dg = bpy.context.evaluated_depsgraph_get()
    geometry = [baked(obj,dg) for obj in objects]
    for obj in objects:
        obj.hide_render = True
    sheet = folder/'six-views.png'
    tiles = [(name.replace('-',' ').title(),angle,geometry) for name,angle in VIEWS]
    contact_sheet(scene,ink,tiles,sheet)
    views = crop_views(sheet,[name for name,_ in VIEWS],folder)
    manifest = dict(sha256=sha(path),views=views,sheet=str(sheet.relative_to(HERE)),
                    context_sha256={ref.name:sha(ref) for ref in refs})
    chosen = ('walk','wave','dance') if item.startswith('top') else ('walk','run','sit_idle')
    motion_tiles, frames = [], {}
    for clip in chosen:
        action = actions[clip]
        sample = grids(action, scene.render.fps)
        frame = sample[int((.42 if clip=='wave' else .31)*len(sample))]
        use_action(arm, action)
        set_frame(scene, frame)
        dg = bpy.context.evaluated_depsgraph_get()
        posed = [baked(obj,dg) for obj in objects]
        frames[clip] = frame
        motion_tiles.append((clip.replace('_',' ').title(),posed))
    motion_sheet = folder/'motion-views.png'
    contact_sheet(scene,ink,[(f'{clip} / {label}',angle,items)
                            for label,angle in (('Front',0),('Back',180))
                            for clip,items in motion_tiles],motion_sheet)
    manifest.update(motion_sheet=str(motion_sheet.relative_to(HERE)),motion_frames=frames,
                    motion_sha256=sha(MOTION),body_sha256=sha(BODY),views_sha256={
                        f:sha(HERE/f) for f in [manifest['sheet'],*views,str(motion_sheet.relative_to(HERE))]})
    write_json(folder/'manifest.json',manifest)


if __name__=='__main__':
    path,item = sys.argv[sys.argv.index('--')+1:]
    render(Path(path),item)
