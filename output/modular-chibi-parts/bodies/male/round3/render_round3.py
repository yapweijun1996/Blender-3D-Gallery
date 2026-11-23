"""Render the exact delivered modules and the two requested outfits."""
from pathlib import Path

import render_modules
from asset_io import MASTER, bpy, write_json
from body_audit import load_body_motion, posed, set_frame, use_action
from fit_module import read_module
from fitting_geometry import arrays, tree
from motion_repair import FIXED
from render_modules import CELL_H, CELL_W, VIEWS, baked, contact_sheet, crop_views, hash_file, studio
from verify_round3 import module_path

OUT = Path(__file__).resolve().parent
RENDERS = OUT / 'renders'
OUTFITS = (
    ('Spiky, T-shirt and jeans', ('hair-spiky', 'tshirt', 'jeans', 'sneakers')),
    ('Bob and dress', ('hair-bob', 'dress', 'sneakers')),
)
LAYER_PAIRS = (('tshirt', 'jeans'), ('jeans', 'sneakers'), ('dress', 'sneakers'))


def render():
    scene, arm, body, actions = load_body_motion(FIXED)
    keys = dict.fromkeys(part for _, parts in OUTFITS for part in parts)
    modules = {k: read_module(module_path(k), arm) for k in keys}
    objects = {'body': body, **modules}
    body_faces = {key: arrays(obj)[1].tolist() for key, obj in modules.items()}
    manifest = {
        'renderer': 'Cycles CPU', 'resolution_per_view': [CELL_W, CELL_H],
        'clip': 'idle', 'frame': 24,
        'motion_sha256': hash_file(FIXED), 'body_master_sha256': hash_file(MASTER),
        'assets': {k: hash_file(module_path(k)) for k in modules}, 'views': {},
        'outfit_layers': {},
    }
    for label, clip, frame in (('rest', None, 0), ('idle_f24', 'idle', 24)):
        use_action(arm, actions.get(clip))
        set_frame(scene, frame)
        poses = {k: tree(posed(o), body_faces[k]) for k, o in modules.items()}
        manifest['outfit_layers'][label] = {f'{a}/{b}': len(poses[a].overlap(poses[b]))
                                             for a, b in LAYER_PAIRS}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    baked_objects = {k: baked(o, depsgraph) for k, o in objects.items()}
    for obj in objects.values():
        obj.hide_render = True
    render_modules.HERE = OUT
    ink = studio(scene)
    for key in ('dress', 'jeans'):
        folder = RENDERS / key
        folder.mkdir(parents=True, exist_ok=True)
        sheet = folder / 'six-views.png'
        contact_sheet(scene, ink, [(name.replace('-', ' ').title(), angle,
                                   [baked_objects['body'], baked_objects[key]]) for name, angle in VIEWS], sheet)
        views = crop_views(sheet, [name for name, _ in VIEWS], folder)
        manifest['views'][key] = {
            'sheet': str(sheet.relative_to(OUT)), 'sheet_sha256': hash_file(sheet),
            'panels': {path: hash_file(OUT / path) for path in views},
        }
    sheet = RENDERS / 'outfits.png'
    contact_sheet(scene, ink, [(title, angle, [baked_objects[k] for k in ('body', *parts)])
                               for title, parts in OUTFITS for angle in (0, 35, 155)], sheet)
    manifest['outfits'] = {'sheet': str(sheet.relative_to(OUT)), 'sha256': hash_file(sheet)}
    write_json(RENDERS / 'manifest.json', manifest)
    write_json(OUT / 'qa/outfit_layers.json', {
        'assets': manifest['assets'], 'motion_sha256': manifest['motion_sha256'],
        'pairs': manifest['outfit_layers'],
    })
    print('OUTFIT LAYERS', manifest['outfit_layers'], flush=True)


if __name__ == '__main__':
    render()
