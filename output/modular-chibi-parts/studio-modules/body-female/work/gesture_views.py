"""Render the two delivered glTF files together using Blender's glTF importer and Cycles CPU.

Pass -- --smoke to exercise capture using the existing round-two library, without replacing
deliverables. Temporary images and the combined inspection scene stay inside this directory.
"""
import argparse
import copy
import hashlib
import json
import math
import os
import struct
import sys
import tempfile
import zlib
from pathlib import Path

import blf
import bpy
import imbuf
import numpy as np
from mathutils import Matrix, Quaternion, Vector

WORK = Path(__file__).resolve().parent
REFERENCE = WORK.parents[2] / "generated2/female-body-tpose.png"
GESTURES = ("fist", "open_relaxed", "point", "thumbs_up", "peace", "ok", "grip_small", "pinch", "open_wide")
SIDES = (("L", "Left", 1), ("R", "Right", -1))
DIGITS = ("Thumb", "Index", "Middle", "Ring", "Pinky")
OVERVIEWS = ("Palm", "Dorsal", "Thumb side")
DETAILS = ("Palmar detail", "Oblique detail")
DETAIL_ROWS = ("rest", "fist", "thumbs_up", "pinch", "ok", "grip_small")
TILE = (320, 252)
ENLARGEMENT = (440, 330)


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def unpack(file):
    buffer = file.read_bytes()
    magic, version, size, length, kind = struct.unpack_from("<4sIIII", buffer)
    assert (magic, version, size, kind) == (b"glTF", 2, len(buffer), 0x4e4f534a)
    return json.loads(buffer[20:20+length]), buffer[28+length:]


def local_matrix(node):
    if "matrix" in node:
        return Matrix([node["matrix"][i:i+4] for i in (0, 4, 8, 12)]).transposed()
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    return Matrix.LocRotScale(Vector(node.get("translation", [0, 0, 0])),
                              Quaternion((w, x, y, z)), Vector(node.get("scale", [1, 1, 1])))


def inspection_glb(body_file, library_file, output):
    # Import animation on the body's actual skin. glTF also permits skeleton-only
    # clips with plain nodes, which Blender can otherwise import as dozens of empties.
    body, raw = unpack(body_file)
    lib, clip_raw = unpack(library_file)
    assert len(body.get("meshes", [])) == len(body.get("skins", [])) == 1
    assert not body.get("animations") and not lib.get('meshes')
    raw = raw[:body["buffers"][0]["byteLength"]]
    raw += bytes((-len(raw)) % 4)
    clip_raw = clip_raw[:lib["buffers"][0]["byteLength"]]
    merged = raw + clip_raw
    names = {node.get("name"): i for i, node in enumerate(body["nodes"])}
    view_offset, accessor_offset = len(body["bufferViews"]), len(body["accessors"])
    for original in lib["bufferViews"]:
        v = dict(original)
        assert v["buffer"] == 0
        v["byteOffset"] = v.get("byteOffset", 0) + len(raw)
        body["bufferViews"].append(v)
    for original in lib["accessors"]:
        a = dict(original)
        assert "sparse" not in a
        a["bufferView"] += view_offset
        body["accessors"].append(a)
    rest_error = 0
    channel_summary = {}
    signatures = {}
    for action in lib["animations"]:
        a = copy.deepcopy(action)
        name = a["name"]
        side = dict((tag, side) for tag, side, sign in SIDES)[name[-1]]
        for s in a["samplers"]:
            s["input"] += accessor_offset
            s["output"] += accessor_offset
        signature = hashlib.sha256()
        for source in action["channels"]:
            sampler = action["samplers"][source["sampler"]]
            target = source["target"]
            signature.update(repr((lib["nodes"][target["node"]]["name"],target["path"],sampler.get("interpolation","LINEAR"))).encode())
            for key in ("input","output"):
                acc = lib["accessors"][sampler[key]]
                view = lib["bufferViews"][acc["bufferView"]]
                offset = view.get("byteOffset",0) + acc.get("byteOffset",0)
                components = {"SCALAR":1, "VEC3":3, "VEC4":4}[acc["type"]]
                assert acc["componentType"] == 5126 and "byteStride" not in view
                signature.update(clip_raw[offset:offset+4*acc["count"]*components])
        signatures[name] = signature.hexdigest()
        for channel in a["channels"]:
            target = channel["target"]
            node = lib["nodes"][target["node"]]
            label = node["name"]
            assert any(label.startswith("mixamorig:"+side+"Hand"+digit) for digit in DIGITS), (name, label)
            target["node"] = names[label]
            a_mat, b_mat = local_matrix(node), local_matrix(body["nodes"][target["node"]])
            rest_error = max(rest_error, max(abs(a_mat[i][j]-b_mat[i][j]) for i in range(4) for j in range(4)))
        body.setdefault("animations", []).append(a)
        channel_summary[name] = len(a["channels"])
    assert rest_error < 0.0001, rest_error
    assert set(channel_summary) == {"hand_"+g+"_"+s for g in GESTURES for s, _, _ in SIDES}
    body["buffers"][0]["byteLength"] = len(merged)
    data = json.dumps(body, separators=(",", ":")).encode()
    data += b' '*((-len(data)) % 4)
    merged += bytes((-len(merged)) % 4)
    size = 28 + len(data) + len(merged)
    output.write_bytes(struct.pack("<4sIIII", b"glTF", 2, size, len(data), 0x4e4f534a)
                       + data + struct.pack("<II", len(merged), 0x004e4942) + merged)
    return {"matched_rest_matrix_max_component_error": rest_error, "exported_channels": channel_summary, "animation_sample_sha256": signatures}


def load_scene(file):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(file))
    rig, = (o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    body, = (o for o in bpy.context.scene.objects if o.type == 'MESH' and o.find_armature() == rig)
    data = rig.animation_data_create()
    for track in data.nla_tracks:
        track.mute = True
    return rig, body


def set_clip(rig, name):
    data = rig.animation_data_create()
    data.action = None
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    if name is None:
        bpy.context.view_layer.update()
        return
    action = bpy.data.actions.get(name)
    if not action:
        action, = (a for a in bpy.data.actions if a.name.startswith(name+'.'))
    slots = [s for s in action.slots if s.target_id_type == 'OBJECT']
    data.action = action
    data.action_slot = slots[0]
    bpy.context.scene.frame_set(round(float(action.frame_range[0])))
    bpy.context.view_layer.update()


def setup_studio():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 3
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 4
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.render.use_persistent_data = True
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.view_settings.view_transform = 'AgX'
    world = bpy.data.worlds.new("Review backdrop")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.145, .195, .25, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .60
    camera_data = bpy.data.cameras.new('Hand review')
    camera_data.type = 'ORTHO'
    camera = bpy.data.objects.new('Hand review', camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    lights = []
    for power, size, c in [(2.25, .16, (1, .91, .82)), (.75, .20, (.83, .91, 1)), (1.72, .16, (1, .94, .86))]:
        data = bpy.data.lights.new('Area softbox', 'AREA')
        data.shape = 'DISK'
        data.energy, data.size, data.color = power, size, c
        light = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(light)
        lights.append(light)
    return scene, camera, lights


def hand_selection(rig, body, rest, side, sign):
    prefix = 'mixamorig:'+side+'Hand'
    wrist = (rig.matrix_world @ rig.data.bones[prefix].head_local).x
    hand = [v.index for v in body.data.vertices if (rest[v.index].x - wrist)*sign > -.007]
    digit_vertices, cap = {}, {}
    for digit in DIGITS:
        prefix_d = prefix + digit
        owned = [i for i in hand if sum(g.weight for g in body.data.vertices[i].groups
                                        if body.vertex_groups[g.group].name.startswith(prefix_d))>.45]
        first = rig.matrix_world @ rig.data.bones[prefix_d+'2'].head_local
        last = rig.matrix_world @ rig.data.bones[prefix_d+'4'].head_local
        axis = (last-first).normalized()
        end = max(rest[i].dot(axis) for i in owned)
        cap[digit] = [i for i in owned if rest[i].dot(axis) >= end-.0035]
        digit_vertices[digit] = owned
    return hand, digit_vertices, cap


def apply_gauge(file, scene, camera, center, right):
    # In this view the camera looks straight down the measured cylinder axis.
    # Draw the cross section at its measured world position at exactly 20 mm radius.
    from bpy_extras.object_utils import world_to_camera_view
    projected = world_to_camera_view(scene,camera,center)
    rim = world_to_camera_view(scene,camera,center+right*.020)
    image = bpy.data.images.load(str(file),check_existing=False)
    image.colorspace_settings.name='Non-Color'
    w,h = image.size
    raw = np.empty(w*h*4,np.float32)
    image.pixels.foreach_get(raw)
    pix = np.rint(raw.reshape(h,w,4)[::-1,:,:3]*255).astype(np.uint8)
    bpy.data.images.remove(image)
    yy,xx=np.ogrid[:h,:w]
    dx=xx+.5-projected.x*w
    dy=yy+.5-(1-projected.y)*h
    dist=np.hypot(dx,dy)
    radius=(rim.x-projected.x)*w
    alpha=np.clip(1.65-np.abs(dist-radius),0,1)*((np.arctan2(dy,dx)*18/np.pi)%2<1.17)
    rgb=np.array([56,207,214],dtype=float)
    pix=np.rint((1-alpha[:,:,None])*pix+alpha[:,:,None]*rgb).astype(np.uint8)
    write_rgb(file,pix)


def capture(scene, camera, lights, points, indices, gesture, sign, view, cap, file, quick, gauge=None):
    macro = view in DETAILS
    width, height = ENLARGEMENT if macro else TILE
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.cycles.samples = 2 if quick else (6 if macro else 4)
    palm = (.18*sign, -.11, -1)
    dirs = {'Palm': palm, 'Dorsal': (.13*sign, .10, 1), 'Thumb side': (.20*sign, -1, -.24),
            'Palmar detail': palm, 'Oblique detail': (-.1*sign, -1, -.62)}
    if gesture == 'thumbs_up':
        dirs.update({'Palm': (.16*sign,-.85,-.73), 'Dorsal': (.16*sign,.9,.8),
                     'Palmar detail': (.48*sign,-1,-.50), 'Oblique detail': (.55*sign,-1,.24)})
    if gesture == 'rest':
        dirs['Oblique detail'] = (.72*sign,-.49,.57)
    if gesture == 'fist':
        dirs['Oblique detail'] = (.58*sign,-.75,-.65)
    gauge_view = gesture=='grip_small' and view=='Oblique detail' and gauge
    if gauge_view:
        d = Vector(gauge['axis']).normalized()
        dirs[view] = -d if d.y>0 else d
    direction = Vector(dirs[view]).normalized()
    up = Vector((0,0,1) if gesture=='thumbs_up' else (sign,0,0))
    up = (up-direction*up.dot(direction)).normalized()
    right = up.cross(direction).normalized()
    center, size = Vector(), []
    for axis in (right, up, direction):
        extent = [points[i].dot(axis) for i in indices]
        bottom, top = min(extent), max(extent)
        center += axis*((top+bottom)*.5)
        size.append(top-bottom)
    far_center = center.dot(direction)
    scale = max(size[0], size[1]*width/height) * (1.11 if macro else 1.18)
    if macro and gesture in ('pinch','ok'):
        center = sum((sum((points[i] for i in cap[d]),Vector()) / len(cap[d])
                      for d in ('Thumb','Index')),Vector())*.5
        scale = .061 if view=='Palmar detail' else .041
    camera.location = center + direction*.56
    camera.rotation_euler = Matrix((right,up,direction)).transposed().to_euler()
    camera.data.ortho_scale = scale
    depth = .56 + center.dot(direction) - far_center
    camera.data.clip_start = max(.005, depth-size[2]/2-.010)
    camera.data.clip_end = depth+size[2]/2+.010
    for light, (x,y,z) in zip(lights, [(-.14,.18,.22),(.20,-.02,.23),(.12,.13,-.14)]):
        light.location = center+x*right+y*up+z*direction
        light.rotation_euler = (center-light.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath = str(file)
    bpy.ops.render.render(write_still=True)
    if gauge_view:
        apply_gauge(file,scene,camera,Vector(gauge['center_mm'])*.001,right)


def write_rgb(file, pixels):
    def chunk(kind,data):
        return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data))
    height,width=pixels.shape[:2]
    header=struct.pack('>IIBBBBB',width,height,8,2,0,0,0)
    compressed=zlib.compress(b''.join(b'\0'+row.tobytes() for row in pixels),6)
    file.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',header)+chunk(b'IDAT',compressed)+chunk(b'IEND',b''))


def write_sheet(file, root, rows, views, tile_size, title, gauged=False):
    cw, ch = tile_size
    margin, top, group, gutter = 157, 94, 12, 3
    width = margin+2*len(views)*(cw+gutter)+group+13
    height = top+len(rows)*(ch+gutter)+12
    canvas = np.empty((height,width,3), dtype=np.uint8)
    canvas[:] = [246,244,239]
    labels = [(18,33,24,title)]
    for si, (tag,side,_) in enumerate(SIDES):
        x0 = margin+si*(len(views)*(cw+gutter)+group)
        labels.append((x0,57,17,side+' hand'))
        for ci, view in enumerate(views):
            x = x0+ci*(cw+gutter)
            labels.append((x,82,15,view))
            for ri, gesture in enumerate(rows):
                y = top+ri*(ch+gutter)
                if not si and not ci:
                    label = {'ok':'OK','rest':'Rest thumb'}.get(gesture,gesture.replace('_',' ').capitalize())
                    labels.append((17,y+ch//2,18,label))
                    if gauged and gesture=='grip_small':
                        labels.append((17,y+ch//2+24,13,'Ø40 mm gauge'))
                image = bpy.data.images.load(str(root / f"{gesture}-{tag}-{view}.png"),check_existing=False)
                image.colorspace_settings.name = 'Non-Color'
                a = np.empty(cw*ch*4, dtype=np.float32)
                image.pixels.foreach_get(a)
                canvas[y:y+ch,x:x+cw] = np.rint(a.reshape(ch,cw,4)[::-1,:,:3]*255).astype(np.uint8)
                bpy.data.images.remove(image)
    write_rgb(file,canvas)
    buf = imbuf.load(str(file))
    with blf.bind_imbuf(0,buf):
        for x,y,size,label in labels:
            blf.size(0,size)
            blf.color(0,.08,.14,.17,1)
            blf.position(0,x,height-y,0)
            blf.draw_buffer(0,label)
    imbuf.write(buf,filepath=str(file))



def compare_body_appearance(body_file, cache):
    source = WORK.parent/'studio_rigged.glb'
    images = []
    for i, file in enumerate((source,body_file)):
        load_scene(file)
        scene, camera, lights = setup_studio()
        scene.render.resolution_x = scene.render.resolution_y = 440
        scene.render.film_transparent = True
        scene.render.image_settings.color_mode = 'RGBA'
        scene.cycles.samples=8
        camera.location=(0,-1.8,.489)
        camera.rotation_euler=(math.pi/2,0,0)
        camera.data.ortho_scale=1.045
        camera.data.clip_start=.01
        camera.data.clip_end=4
        target=Vector((0,0,.52))
        for light, position, power, size in zip(lights,[(-.58,-.88,1.4),(.65,-.55,.76),(-.05,.55,1.25)],
                                                [23,12,22],[.7,.7,.65]):
            light.location=position
            light.data.energy, light.data.size=power,size
            light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
        png=cache/f"look-{i}.png"
        scene.render.filepath=str(png)
        bpy.ops.render.render(write_still=True)
        im=bpy.data.images.load(str(png),check_existing=False)
        im.colorspace_settings.name='Non-Color'
        rgba=np.empty(440*440*4,np.float32)
        im.pixels.foreach_get(rgba)
        images.append(rgba.reshape(440,440,4)[::-1].copy())
        bpy.data.images.remove(im)
    original, candidate=images
    x=np.broadcast_to((np.arange(440)+.5-220)*1.045/440,(440,440))
    z=np.broadcast_to((.489+(220-np.arange(440)-.5)*1.045/440)[:,None],(440,440))
    inside=(original[:,:,3]>.995)&(candidate[:,:,3]>.995)&(np.abs(x)<.258)
    difference=np.mean(np.abs(original[:,:,:3]-candidate[:,:,:3]),axis=2)*255
    stats={}
    for name,region in [('face_head',z>.615),('body',z<=.615),('nonhand',np.ones_like(inside))]:
        sample=difference[inside&region]
        stats[name]={'pixels':len(sample),'mean_abs_srgb_8bit':float(sample.mean()),
                     'p95':float(np.percentile(sample,95)),'p99':float(np.percentile(sample,99))}
    for im in images:
        alpha=im[:,:,3:4]
        im[:,:,:3]=im[:,:,:3]*alpha+(.75,.76,.78)*(1-alpha)
    rgb=np.concatenate([im[:,:,:3] for im in images],1)
    write_rgb(WORK/'body_comparison.png',np.rint(rgb*255).astype(np.uint8))
    return {'file':'body_comparison.png','left':'Read-only Studio input studio_rigged.glb',
            'right':'Repaired module body_female_v1.glb','source_sha256':digest(source),'body_sha256':digest(body_file),
            'render':'440 px front orthographic, Cycles CPU, same camera, 3 area lights, 8 samples, AgX. Alpha > 0.995 in both images and |X| < 0.258 m. Mean RGB-channel absolute deviation in display-referred 8-bit values.',
            'comparison':stats}

def run():
    p = argparse.ArgumentParser()
    p.add_argument('--smoke',action='store_true')
    p.add_argument('--poses',nargs='+',help='Capture selected poses into the temporary runtime cache for inspection.')
    p.add_argument('--views',nargs='+', choices=(*OVERVIEWS,*DETAILS))
    p.add_argument('--left-only',action='store_true')
    opt = p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    body_file, lib_file = WORK/'body_female_v1.glb', WORK/'hand_gestures_female.glb'
    if opt.smoke:
        base = WORK.parents[2]/'hand-gestures-astra/round2'
        body_file, lib_file = base/'base_body.glb', base/'hand_gestures.glb'
    with tempfile.TemporaryDirectory(prefix='.gesture-review-',dir=WORK) as t:
        cache = Path(t)
        combined = cache/'inspection.glb'
        inputs = (REFERENCE,body_file) if opt.poses==['rest'] else (REFERENCE,body_file,lib_file)
        input_ids = {f.name:digest(f) for f in inputs}
        if opt.poses==['rest']:
            rig, body = load_scene(body_file)
            report = {}
        else:
            report = inspection_glb(body_file,lib_file,combined)
            rig, body = load_scene(combined)
        assert all(input_ids[f.name]==digest(f) for f in inputs)
        scene, camera, lights = setup_studio()
        rest = [body.matrix_world@v.co for v in body.data.vertices]
        rows = ('pinch',) if opt.smoke else GESTURES
        details = ('pinch',) if opt.smoke else DETAIL_ROWS
        cache_base = cache if opt.smoke else WORK/'.gesture-runtime'/'tiles'
        cache_base.mkdir(exist_ok=True,parents=True)
        common = input_ids[body_file.name] + digest(Path(__file__))
        library_json = WORK/'hand_gestures_female.json'
        gauges = json.loads(library_json.read_text()).get('grip_gauges',{}) if library_json.exists() and not opt.smoke else {}
        poses = tuple(dict.fromkeys((*details,*rows))) if not opt.poses else opt.poses
        for gesture in poses:
            for tag,side,sign in (SIDES[:1] if opt.left_only else SIDES):
                hand, owned, cap = hand_selection(rig,body,rest,side,sign)
                clip = None if gesture=='rest' else 'hand_'+gesture+'_'+tag
                set_clip(rig,clip)
                ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
                points = [ev.matrix_world@v.co for v in ev.data.vertices]
                views = OVERVIEWS if gesture in rows else ()
                if gesture in details:
                    views = (*views,*DETAILS)
                sample_id = report['animation_sample_sha256'][clip] if clip else 'bind pose'
                gauge = gauges.get(tag) if gesture=='grip_small' else None
                signature = tag+gesture+sample_id+common+json.dumps(gauge,sort_keys=True)
                fingerprint = hashlib.sha256(signature.encode()).hexdigest()
                for view in views:
                    if opt.views and view not in opt.views:
                        continue
                    indices = hand
                    if view in DETAILS and gesture in ('fist','thumbs_up'):
                        indices = sorted(set(i for digit_ids in owned.values() for i in digit_ids))
                    if gesture == 'rest':
                        indices = owned['Thumb']
                    tile_path = cache_base / f"{fingerprint}-{view}.png"
                    if not tile_path.exists():
                        capture(scene,camera,lights,points,indices,gesture,sign,view,cap,tile_path,opt.smoke,gauge)
                    os.link(tile_path,cache/f"{gesture}-{tag}-{view}.png")
        if opt.poses or opt.views or opt.left_only:
            preview = WORK/'.gesture-runtime'/'previews'
            preview.mkdir(exist_ok=True,parents=True)
            for tile in cache.glob('*-L-*.png'):
                dest = preview/tile.name
                dest.unlink(missing_ok=True)
                os.link(tile,dest)
            print('Selected poses captured in '+str(cache_base))
            return
        assert all(input_ids[f.name] == digest(f) for f in (body_file,lib_file)), 'An input changed during capture. Rerun to reuse unaffected exact-input tiles.'
        target = cache if opt.smoke else WORK
        write_sheet(target/'contact_sheet.png',cache,rows,OVERVIEWS,TILE,'Female body hand gestures')
        write_sheet(target/'gesture_closeups.png',cache,details,DETAILS,ENLARGEMENT,'Grip and fingertip details',gauged=bool(gauges))
        if not opt.smoke:
            report['body_comparison']=compare_body_appearance(body_file,cache)
            report.update({
                'sha256': {**input_ids,**{k.name:digest(k) for k in (target/'contact_sheet.png',target/'gesture_closeups.png',target/'body_comparison.png')}},
                'renderer': 'Cycles CPU with the exported materials and a three-area-light studio',
                'blender':bpy.app.version_string, 'overview_tiles':54,'detail_tiles':24,'grip_gauges':gauges,
                'inputs': 'The original animation accessors from the library target the exact body nodes by name. Blender imports the inspection copy with its skin and evaluates each rotation using the imported action and action_slot.',
            })
            (WORK/'visual_review.json').write_text(json.dumps(report,indent=2)+'\n')
        print('Gesture sheets assembled and inspected for valid image pixels.',flush=True)


if __name__ == '__main__':
    run()
