"""Capture six bind-pose views of the selected GLB with the shipped outfit."""
from pathlib import Path
import sys

from asset_io import HERE, MOTION, bpy, write_json
from body_audit import load_body_motion, set_frame, use_action
from fit_module import read_module
from gate_module import BODY, companions, sha
from render_modules import VIEWS, baked, contact_sheet, crop_views, studio


def render(path, item):
    scene, arm, _, _ = load_body_motion(MOTION)
    bpy.context.scene.objects['Base_Body'].hide_render = True
    refs = companions(item)
    objects = [read_module(file,arm) for file in (BODY,path,*refs)]
    use_action(arm,None)
    set_frame(scene,0)
    folder = HERE/'renders'/item
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
    write_json(folder/'manifest.json',dict(sha256=sha(path),views=views,sheet=str(sheet.relative_to(HERE)),
        context_sha256={ref.name:sha(ref) for ref in refs}))


if __name__=='__main__':
    path,item = sys.argv[sys.argv.index('--')+1:]
    render(Path(path),item)
