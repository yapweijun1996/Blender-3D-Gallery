"""Reimport the two deliverables and render orthographic gesture evidence in Blender."""
import argparse
import hashlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path

import blf
import bpy
import imbuf
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
GESTURES = ('fist', 'open_relaxed', 'point', 'thumbs_up', 'peace', 'ok', 'grip_small', 'pinch', 'open_wide')
SIDES = (('L', 'Left', 1), ('R', 'Right', -1))
VIEWS = ('palm', 'dorsal', 'thumb-side')
NEAR = ('pinch', 'ok', 'fist', 'open_relaxed')
DIGITS = ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky')
TILE = (384, 320)
MACRO = (540, 390)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_body(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if path.suffix == '.blend':
        bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
    else:
        bpy.ops.import_scene.gltf(filepath=str(path), import_pack_images=True)
    body, = (o for o in bpy.context.scene.objects if o.type == 'MESH' and o.find_armature())
    rig = body.find_armature()
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and o != body:
            o.hide_render = True
    return body, rig


def get_points(body):
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [ev.matrix_world @ v.co for v in ev.data.vertices]


def select_action(rig, action):
    ad = rig.animation_data_create()
    for t in ad.nla_tracks:
        t.mute = True
    ad.action = None
    for p in rig.pose.bones:
        p.matrix_basis = Matrix.Identity(4)
    if action:
        ad.action = action
        ad.action_slot = action.slots[0]
    bpy.context.scene.frame_set(int(action.frame_range.x) if action else 0)
    bpy.context.view_layer.update()


class Studio:
    def __init__(self, samples):
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        scene.render.threads_mode = 'FIXED'
        scene.render.threads = 4
        scene.render.use_compositing = False
        scene.render.use_sequencer = False
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGB'
        scene.view_settings.view_transform = 'AgX'
        scene.world = bpy.data.worlds.new('Neutral blue-grey studio')
        scene.world.use_nodes = True
        scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.115, .15, .19, 1)
        scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .57
        cd = bpy.data.cameras.new('Orthographic QA lens')
        cd.type = 'ORTHO'
        cd.clip_start = .005
        self.cam = bpy.data.objects.new('Orthographic QA', cd)
        scene.collection.objects.link(self.cam)
        scene.camera = self.cam
        self.scene = scene
        self.lights = []
        for power, size, color in ((1.9, .18, (1, .96, .91)), (.7, .19, (.89, .94, 1)), (1.25, .14, (1, .97, .93))):
            ld = bpy.data.lights.new('Softbox', 'AREA')
            ld.energy = power
            ld.size = size
            ld.color = color
            ld.shape = 'DISK'
            light = bpy.data.objects.new(ld.name, ld)
            scene.collection.objects.link(light)
            self.lights.append(light)

    def frame(self, path, points, direction, up, resolution=TILE, focus=None, field=None, full=False):
        direction = Vector(direction).normalized()
        up = Vector(up)
        up = (up - direction * up.dot(direction)).normalized()
        right = up.cross(direction).normalized()
        width, height = resolution
        self.scene.render.resolution_x = width
        self.scene.render.resolution_y = height
        axes = (right, up, direction)
        extents = [(min(p.dot(axis) for p in points), max(p.dot(axis) for p in points)) for axis in axes]
        center = sum((a * ((lo + hi) / 2) for a, (lo, hi) in zip(axes, extents)), Vector())
        if focus is not None:
            center = focus
        size = field or max(extents[0][1] - extents[0][0], (extents[1][1] - extents[1][0]) * width / height) * 1.14
        self.cam.rotation_euler = Matrix(axes).transposed().to_euler()
        self.cam.location = center + direction * 2
        self.cam.data.ortho_scale = size
        self.cam.data.clip_end = 2 + center.dot(direction) - extents[2][0] + .004
        mult = 5 if full else 1
        for light, (x, y, z), power, diameter in zip(self.lights, ((-.14, .18, .22), (.20, -.02, .23), (.1, .15, -.16)), (1.9, .7, 1.25), (.18, .19, .14)):
            light.location = center + mult * (right * x + up * y + direction * z)
            light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
            light.data.energy = power * mult * mult
            light.data.size = diameter * mult
        self.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        return dict(image=path.name, sha256=sha(path), pixels=list(resolution), ortho_width_m=size,
                    target_m=list(center), camera_direction=list(direction), screen_up=list(up))


class Hand:
    def __init__(self, body, rig, rest, side, sign):
        pre = 'mixamorig:' + side + 'Hand'
        world = rig.matrix_world
        wrist = world @ rig.data.bones[pre].head_local
        self.ids = [i for i, p in enumerate(rest) if sign * (p.x - wrist.x) >= -.012]
        self.caps = {}
        self.owners = {}
        for digit in DIGITS:
            root = world @ rig.data.bones[pre + digit + '1'].head_local
            end = world @ rig.data.bones[pre + digit + '4'].head_local
            axis = (end - root).normalized()
            candidates = [i for i in self.ids if any(body.vertex_groups[g.group].name.startswith(pre + digit) and g.weight > .15
                          for g in body.data.vertices[i].groups)]
            far = max(rest[i].dot(axis) for i in candidates)
            self.caps[digit] = [i for i in candidates if rest[i].dot(axis) >= far - .0025]
            self.owners[digit] = candidates

    def tip(self, digit, points):
        indices = self.caps[digit]
        return sum((points[i] for i in indices), Vector()) / len(indices)


def detail_direction(body, points, hand, sign):
    # Maximize visibility of both terminal surfaces, viewing across their line of approach.
    thumb = hand.tip('Thumb', points)
    index = hand.tip('Index', points)
    axis = (thumb - index).normalized()
    center = (thumb + index) * .5
    tri = [tuple(p.vertices) for p in body.data.polygons]
    tree = BVHTree.FromPolygons(points, tri)
    best = None
    hints = [Vector((x * sign, y, z)) for x in (-.72, .05, .72) for y in (-1, -.35, .35, .9) for z in (-.9, -.35, .35, .95)]
    for hint in hints:
        direction = hint - axis * hint.dot(axis)
        if direction.length < .02:
            continue
        direction.normalize()
        depths = []
        for tip in (thumb, index, center):
            hit = tree.ray_cast(tip + direction * .25, -direction, .40)
            depths.append(0 if hit[0] is None else max(0, (hit[0] - tip).dot(direction)))
        cost = max(depths) + .2 * sum(depths) + .00022 * max(direction.y, 0)
        if best is None or cost < best[0]:
            best = (cost, direction.copy())
    return best[1], center


def capture(args):
    directory = args.destination
    directory.mkdir(exist_ok=True, parents=True)
    body, rig = load_body(args.body)
    select_action(rig, None)
    rest = get_points(body)
    studio = Studio(args.samples)
    result = {'body': [args.body.name, sha(args.body)], 'blender': bpy.app.version_string, 'samples': args.samples, 'renderer': 'Cycles CPU', 'material': 'Imported GLB material', 'frames': []}
    if args.baseline or args.rest:
        for suffix, direction in (('front', (0,-1,0)), ('three_quarter', (.62,-1,.04))):
            path = directory / ('rest_' + suffix + '.png')
            result['frames'].append(studio.frame(path, rest, direction, (0,0,1), (640,640), full=True))
        for tag, side, sg in SIDES:
            hand = Hand(body, rig, rest, side, sg)
            points = [rest[i] for i in hand.ids]
            for name, direction in (('palm', (.12*sg,-.09,-1)), ('dorsal', (.12*sg,.09,1)), ('thumb-side', (.26*sg,-1,-.12))):
                result['frames'].append(studio.frame(directory / ('rest_' + tag + '_' + name + '.png'), points, direction, (sg,0,0)))
        if args.baseline:
            (directory/'manifest.json').write_text(json.dumps(result, indent=2))
            return
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(args.library))
    for ob in set(bpy.context.scene.objects) - before:
        ob.hide_render = True
    result['library'] = [args.library.name, sha(args.library)]
    for tag, side, sg in SIDES:
        if tag not in args.sides:
            continue
        hand = Hand(body, rig, rest, side, sg)
        for gesture in args.poses:
            name = 'hand_' + gesture + '_' + tag
            candidate = bpy.data.actions.get(name)
            if candidate is None:
                raise RuntimeError(f'Missing {name}. Imported actions: {list(bpy.data.actions.keys())}')
            select_action(rig, candidate)
            points = get_points(body)
            selected = [points[i] for i in hand.ids]
            if max((points[i]-rest[i]).length for i in hand.ids) < .0002:
                raise RuntimeError(f'{name} did not visibly move the skin. Check imported clip binding.')
            dirs = dict(palm=(.16*sg, -.10, -1), dorsal=(.16*sg,.10,1), **{'thumb-side':(.26*sg,-1,-.16)})
            if gesture == 'thumbs_up':
                dirs.update(palm=(.33*sg,-.9,-.70), dorsal=(.15*sg,.89,.72))
            for view, direction in dirs.items():
                upright = (0,0,1) if gesture == 'thumbs_up' else (sg,0,0)
                result['frames'].append(studio.frame(directory/f'{name}_{view}.png', selected, direction, upright))
            if gesture in NEAR:
                if gesture in ('pinch','ok'):
                    direction, center = detail_direction(body, points, hand, sg)
                    camera_specs = [('clearance',direction,center,.049), ('oblique',(.25*sg,-.75,-1),center,.073)]
                elif gesture == 'fist':
                    center = sum((hand.tip(d, points) for d in DIGITS), Vector()) / len(DIGITS)
                    camera_specs = [('clearance',(.64*sg,-.3,-1),center,.091),('oblique',(-.55*sg,-1,-.52),center,.087)]
                else:
                    cloud = [points[i] for i in hand.owners['Thumb']]
                    center = (hand.tip('Thumb',points) + sum(cloud,Vector())/len(cloud))*.5
                    camera_specs = [('clearance',(.31*sg,-.13,-1),center,.094),('oblique',(.77*sg,-.50,.73),center,.090)]
                for label, direction, center, field in camera_specs:
                    up = Vector((sg,0,0))
                    if abs(Vector(direction).normalized().dot(up)) > .9:
                        up = Vector((0,0,1))
                    result['frames'].append(studio.frame(directory/f'{name}_{label}.png', selected, direction, up, MACRO, center, field))
    output = directory/('manifest_' + ''.join(args.sides) + '.json')
    output.write_text(json.dumps(result, indent=2))


def png(path, rgb):
    height,width,_ = rgb.shape
    def chunk(kind, data):
        return struct.pack('>I',len(data)) + kind + data + struct.pack('>I',zlib.crc32(kind+data))
    head = struct.pack('>IIBBBBB',width,height,8,2,0,0,0)
    raw = b''.join(b'\0'+row.tobytes() for row in rgb)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR',head) + chunk(b'IDAT',zlib.compress(raw,5)) + chunk(b'IEND',b''))


def compose(args, detail):
    cols = ('clearance','oblique') if detail else VIEWS
    rows = NEAR if detail else GESTURES
    cw,ch = MACRO if detail else TILE
    margin,header,gap = 164,104,4
    block = len(cols) * (cw+gap) + 13
    height = header + len(rows)*(ch+gap)+16
    width = margin+2*block+8
    page = np.full((height,width,3), (241,242,239),dtype=np.uint8)
    labels = [(16,38,28,'Hand detail' if detail else 'Male hand gestures')]
    names = {'palm':'Palm','dorsal':'Dorsal','thumb-side':'Thumb side','clearance':'Detail','oblique':'Oblique'}
    for side_i,(tag,side,_) in enumerate(SIDES):
        x0 = margin+side_i*block
        labels.append((x0,63,21,side+' hand'))
        for col_i, col in enumerate(cols):
            x = x0+col_i*(cw+gap)
            labels.append((x,88,16,names[col]))
            for row_i,gesture in enumerate(rows):
                y = header+row_i*(ch+gap)
                if side_i==col_i==0:
                    name = 'OK' if gesture=='ok' else gesture.replace('_',' ').capitalize()
                    labels.append((15,y+ch//2,21,name))
                img = bpy.data.images.load(str(args.destination/f'hand_{gesture}_{tag}_{col}.png'),check_existing=False)
                img.colorspace_settings.name = 'Non-Color'
                arr = np.empty(ch*cw*4,np.float32)
                img.pixels.foreach_get(arr)
                page[y:y+ch,x:x+cw] = (arr.reshape(ch,cw,4)[::-1,:,:3]*255+.5).astype(np.uint8)
                bpy.data.images.remove(img)
    path = (HERE/'hand_closeups.png') if detail else (WORK/'contact_sheet.png')
    png(path,page)
    buf = imbuf.load(str(path))
    with blf.bind_imbuf(0,buf):
        for x,y,size,label in labels:
            blf.size(0,size)
            blf.color(0,.075,.13,.15,1)
            blf.position(0,x,height-y,0)
            blf.draw_buffer(0,label)
    imbuf.write(buf, filepath=str(path))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--body',type=Path,default=WORK/'body_male_v1.glb')
    p.add_argument('--library',type=Path,default=WORK/'hand_gestures_male.glb')
    p.add_argument('--destination',type=Path,default=HERE/'renders')
    p.add_argument('--rest',action='store_true')
    p.add_argument('--baseline',action='store_true')
    p.add_argument('--compose',action='store_true')
    p.add_argument('--poses',nargs='+',choices=GESTURES,default=GESTURES)
    p.add_argument('--sides',nargs='+',choices=('L','R'),default=('L','R'))
    p.add_argument('--samples',type=int,default=12)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    args.body=args.body.resolve()
    args.library=args.library.resolve()
    args.destination=args.destination.resolve()
    if args.compose:
        manifests = [json.loads(p.read_text()) for p in sorted(args.destination.glob('manifest_*.json'))]
        expected = (sha(args.body), sha(args.library))
        captured = {}
        for item in manifests:
            if (item['body'][1],item['library'][1]) != expected:
                raise RuntimeError('Source GLBs changed after capture. Regenerate the affected views.')
            for frame in item['frames']:
                if sha(args.destination/frame['image']) != frame['sha256']:
                    raise RuntimeError(f"Frame changed after capture: {frame['image']}")
                captured[frame['image']] = frame['sha256']
        wanted = {f'hand_{g}_{tag}_{v}.png' for g in GESTURES for tag,_,_ in SIDES for v in VIEWS}
        wanted |= {f'hand_{g}_{tag}_{v}.png' for g in NEAR for tag,_,_ in SIDES for v in ('clearance','oblique')}
        if missing := wanted.difference(captured):
            raise RuntimeError(f'Missing independently identified views: {sorted(missing)}')
        compose(args,False)
        compose(args,True)
        record = {
            'body_sha256': expected[0], 'library_sha256': expected[1],
            'source_reference_sha256': sha(WORK.parents[2]/'generated2'/'male-body-tpose.png'),
            'standard_frames': 54, 'macro_frames': 16,
            'sheet_sha256': sha(WORK/'contact_sheet.png'),
            'details_sha256': sha(HERE/'hand_closeups.png')
        }
        (HERE/'sheet_manifest.json').write_text(json.dumps(record, indent=2))
    else:
        capture(args)


if __name__=='__main__':
    import traceback
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.stdout.flush()
        raise SystemExit(1)
