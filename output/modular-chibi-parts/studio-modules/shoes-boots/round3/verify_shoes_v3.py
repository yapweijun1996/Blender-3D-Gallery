"""Check the shipped asset with the supplied checkers and fixed-camera renders."""
import json
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_shoes_v3 import HERE, TARGET, V2, WELD_M, count_edges, digest, mount, write_report
import verify_shoes_v2 as previous

CHECKS = HERE / 'checks'
VISUAL = HERE / 'renders'
GLB = TARGET.with_suffix('.glb')
VIEWS = (
    ('front', (0, -1, .16)),
    ('side', (1, 0, .12)),
    ('opposite_side', (-1, 0, .12)),
    ('rear', (0, 1, .2)),
    ('top', (0, -.15, 1)),
    ('underside', (0, -.15, -1)),
)


def raw_qa(command, args):
    previous.CHECKS, previous.V2 = CHECKS, GLB
    if command == 'checker':
        setup_preview = previous.checker_cycles

        def preview(scene):
            setup_preview(scene)
            scene.cycles.samples = 2
            scene.render.resolution_percentage = 40
            scene.render.threads_mode = 'FIXED'
            scene.render.threads = 2

        previous.checker_cycles = preview
    commands = {'checker': previous.supplied, 'half-frames': previous.inspect_half_frames,
                'native': previous.verify_native}
    commands[command](*args)
    if command == 'native':
        boot = bpy.context.scene.objects[TARGET.name]
        mesh = bmesh.new()
        mesh.from_mesh(boot.data)
        edges = count_edges(mesh)
        assert all(edge.is_contiguous for edge in mesh.edges)
        mesh.free()
        assert all(row['boundary'] == row['overfull'] == row['wire'] == 0 for row in edges)
        report = CHECKS / 'native_blend.json'
        data = json.loads(report.read_text())
        data['direct_mesh_edges'] = edges
        write_report(report, data)


def topology_report():
    rows = {}
    for path in (V2, GLB):
        _, arm, _ = previous.master_scene()
        boot = mount(path, arm)
        bm = bmesh.new()
        bm.from_mesh(boot.data)
        raw = count_edges(bm)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=WELD_M)
        rows[path.stem] = dict(sha256=digest(path), exported_index_edges=raw,
                               welded_geometric_edges=count_edges(bm))
        bm.free()
    write_report(CHECKS / 'export_topology.json', dict(weld_distance_m=WELD_M, assets=rows))
    assert all(row['boundary'] == row['overfull'] == row['wire'] == 0
               for row in rows[GLB.stem]['welded_geometric_edges'])


def camera_for(scene, center, width, height):
    camera = previous.setup_camera(scene, center, width, height)
    scene.render.threads = 2
    return camera


def capture(path):
    folder = VISUAL / path.stem
    folder.mkdir(exist_ok=True, parents=True)
    scene, arm, body, boot = previous.prepare_scene(path)
    center = Vector((0, -.028, .066))
    body.hide_render = True
    camera = camera_for(scene, center, 460, 360)
    by_view = {}
    for view, direction in VIEWS:
        previous.aim(camera, center, direction, .455)
        image = folder / f'{view}.png'
        previous.render(scene, image)
        by_view[view] = dict(image=image.name, sha256=digest(image), direction=direction)
        if view == 'underside':
            by_view[view]['pixel_count'] = sole_dark_pixels(boot, scene, camera, image)
    previous.stitch([folder / row['image'] for row in by_view.values()], 3, folder / 'rest_views.png')
    body.hide_render = False
    data = json.loads((CHECKS / 'half_frame_gate.json').read_text()) if (CHECKS / 'half_frame_gate.json').exists() else None
    frames = {3.0}
    if data:
        frames.add(data['summary']['run']['closest_frame'])
    camera = camera_for(scene, center, 720, 620)
    scene.cycles.samples = 16
    run = previous.load_actions(previous.SHARED, ('run',))['run']
    for time in sorted(frames):
        previous.pose(scene, arm, run, time)
        rest = np.array([v.co[:] for v in body.data.vertices])
        posed = previous.evaluated_points(body)[rest[:, 2] < .17]
        focus = Vector((posed.min(axis=0) + posed.max(axis=0)) / 2)
        focus.z += .018
        for variant, direction, scale in (('deepest', (.92, -.85, .37), .54),
                                           ('toe', (1, -.89, .20), .32)):
            previous.aim(camera, focus, direction, scale)
            image = folder / f'run_{time:g}_{variant}.png'
            previous.render(scene, image)
            by_view[image.stem] = dict(image=image.name, sha256=digest(image), direction=direction,
                                       run_frame=time, center=tuple(focus), ortho_scale_m=scale)
    write_report(folder / 'manifest.json', dict(
        asset_sha256=digest(path), motion_sha256=digest(previous.SHARED), blender=bpy.app.version_string,
        engine='Cycles CPU', samples=16, threads=2, rest_center=tuple(center),
        rest_ortho_scale_m=.455, rest_contact_sheet_sha256=digest(folder/'rest_views.png'), views=by_view))


def sole_dark_pixels(boot, scene, camera, png):
    """Count rendered near-black pixels inside each sole and its 40 px inner outline."""
    bpy.context.view_layer.update()
    image = bpy.data.images.load(str(png), check_existing=False)
    width, height = image.size
    values = np.empty(width * height * 4, np.float32)
    image.pixels.foreach_get(values)
    rgb = values.reshape(height, width, 4)[::-1, :, :3]
    black = np.max(rgb, axis=2) <= 24 / 255
    bpy.data.images.remove(image)
    cam_to_boot = boot.matrix_world.inverted() @ camera.matrix_world
    camera_box = camera.data.view_frame(scene=scene)
    xmin, xmax = min(v.x for v in camera_box), max(v.x for v in camera_box)
    ymin, ymax = min(v.y for v in camera_box), max(v.y for v in camera_box)
    direction = cam_to_boot.to_3x3() @ Vector((0, 0, -1))
    dg = bpy.context.evaluated_depsgraph_get()
    sides = np.zeros((height, width), dtype=np.int8)
    for y in range(height):
        py = ymax - (y+.5)/height * (ymax-ymin)
        for x in range(width):
            px = xmin + (x+.5)/width * (xmax-xmin)
            hit, location, _, _ = boot.ray_cast(cam_to_boot @ Vector((px, py, 0)),
                                                 direction, depsgraph=dg)
            if hit:
                sides[y, x] = 1 if location.x > 0 else -1
    results = {}
    for side, sign in (('image_left', -1), ('image_right', 1)):
        silhouette = sides == sign
        # Erode the projected silhouette with the 4-neighbour (Manhattan) metric.
        core = silhouette.copy()
        for _ in range(40):
            old = np.pad(core, 1)
            core &= old[:-2, 1:-1] & old[2:, 1:-1] & old[1:-1, :-2] & old[1:-1, 2:]
        outline = silhouette & ~core
        results[side] = dict(outline_pixels=int(outline.sum()), sole_pixels=int(silhouette.sum()),
                             near_black_outline=int((black & outline).sum()),
                             near_black_sole=int((black & silhouette).sum()))
    return dict(threshold_srgb_max_code=24, inward_outline_width_px=40,
                raster_px=[width, height], measurements=results)


if __name__ == '__main__':
    command, *args = sys.argv[sys.argv.index('--') + 1:]
    CHECKS.mkdir(exist_ok=True)
    if command == 'topology':
        topology_report()
    elif command == 'renders':
        paths = {'v2': (V2,), 'v3': (GLB,), 'both': (V2, GLB)}[args[0] if args else 'both']
        for path in paths:
            capture(path)
    else:
        raw_qa(command, args)
