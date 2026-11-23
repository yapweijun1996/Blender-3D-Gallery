"""Render the actual layered candidate at rest and skirt motion witnesses."""
from pathlib import Path
import sys

from asset_io import HERE, MALE, MOTION, bpy, json, write_json
from body_audit import load_body_motion, set_frame, use_action
from fit_module import read_module
from gate_module import sha
from render_modules import VIEWS, baked, contact_sheet, crop_views, studio


def render(path, item, gate):
    scene, arm, body, actions = load_body_motion(MOTION)
    objects = [body, read_module(path, arm), read_module(MALE/'male-tshirt.glb', arm)]
    complementary = 'male-jeans.glb' if item.startswith('shoes-') else 'male-sneakers.glb'
    objects.append(read_module(MALE/complementary, arm))
    folder = HERE/'renders'/item
    folder.mkdir(parents=True, exist_ok=True)
    ink = studio(scene)
    scene.cycles.samples = 6
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    for obj in objects:
        obj.hide_render = True

    def capture(action=None, frame=0):
        use_action(arm, action)
        set_frame(scene, frame)
        dg = bpy.context.evaluated_depsgraph_get()
        return [baked(obj, dg) for obj in objects]

    pose = capture()
    sheet = folder/'six-views.png'
    contact_sheet(scene, ink, [(name.replace('-', ' ').title(), angle, pose) for name, angle in VIEWS], sheet)
    files = crop_views(sheet, [name for name, _ in VIEWS], folder)
    report = dict(sha256=sha(path), views=files, rest_sheet=str(sheet.relative_to(HERE)),
                  context_sha256={key:sha(MALE/key) for key in ('male-tshirt.glb',complementary)})
    if item == 'bottom-skirt':
        tiles = []
        rows = json.loads(gate.read_text())['clips']
        for clip in ('walk','run','sit_down'):
            frame = rows[clip]['minimum_frame']
            pose = capture(actions[clip], frame)
            tiles.extend([(f'{clip} / {frame}', 0, pose), (f'{clip} / {frame}', 75, pose)])
        sheet = folder/'motion-views.png'
        contact_sheet(scene, ink, tiles, sheet)
        report['motion_sheet'] = str(sheet.relative_to(HERE))
    write_json(folder/'manifest.json', report)


if __name__ == '__main__':
    path, item, gate = sys.argv[sys.argv.index('--')+1:]
    render(Path(path), item, Path(gate))
