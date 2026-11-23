"""Render the final socket JSON on the original assets in Cycles CPU."""
import argparse
import struct
import zlib

import blf
import imbuf
from verify import *


SIZE = (336, 364)
FRAMES = {
    'hold_item': (0,15,30,45), 'hold_box': (0,12,24,36), 'hold_bag': (0,12,24,36),
    'take_item': (0,16,29,39), 'sit_down': (0,12,24,36), 'sit_idle': (0,22,45,68),
    'stand_up': (0,10,20,30),
}
VIEWS = {'front': (0,-1,.04), 'side': (-1,0,.045)}


def setup(scene):
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = SIZE
    scene.render.resolution_percentage = 100
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.image_settings.file_format = 'PNG'
    scene.world = bpy.data.worlds.new('Studio ambient')
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes['Background']
    bg.inputs[0].default_value = (.78,.85,.90,1)
    bg.inputs[1].default_value = .52
    bpy.ops.mesh.primitive_plane_add(size=30,location=(0,0,-.0003))
    mat = bpy.data.materials.new('Studio floor')
    mat.diffuse_color = (.43,.55,.57,1)
    bpy.context.object.data.materials.append(mat)
    for pos, power, size, color in (
            ((-1.4,-2.2,2.7),150,1.6,(1,.91,.81)),((1.5,-.9,1.7),47,1.2,(.85,.94,1)),
            ((.4,1.4,2.1),82,1.25,(1,.96,.84))):
        light = bpy.data.lights.new('Softbox','AREA')
        light.energy, light.size, light.color = power,size,color
        o = bpy.data.objects.new(light.name,light)
        scene.collection.objects.link(o)
        o.location = pos
        o.rotation_euler = (Vector((0,0,.5))-o.location).to_track_quat('-Z','Y').to_euler()
    cam = bpy.data.cameras.new('Orthographic review')
    cam.type = 'ORTHO'
    cam.clip_start = .01
    camera = bpy.data.objects.new(cam.name,cam)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return camera


def review_sheet(directory, clip, frames, view_rows):
    w,h = SIZE
    width,height = 4*w+24,2*(h+29)+50
    rgb = np.full((height,width,3), (236,242,242),dtype=np.uint8)
    labels = [(10,28,22,clip.replace('_',' ').title())]
    for row,(view,panels) in enumerate(view_rows.items()):
        for col,(f,panel) in enumerate(zip(frames,panels)):
            x,y = 7+col*(w+3),42+row*(h+29)
            rgb[y:y+h,x:x+w] = panel
            labels.append((x+2,y+h+18,14,f'{view.title()}   /   Frame {f}'))
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    path = directory/f'.{clip}.{os.getpid()}.png'
    header = struct.pack('>IIBBBBB',width,height,8,2,0,0,0)
    data = zlib.compress(b''.join(b'\0'+row.tobytes() for row in rgb))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',header)+chunk(b'IDAT',data)+chunk(b'IEND',b''))
    buf = imbuf.load(str(path))
    with blf.bind_imbuf(0,buf):
        for x,y,size,label in labels:
            blf.size(0,size)
            blf.color(0,.055,.113,.125,1)
            blf.position(0,x,height-y,0)
            blf.draw_buffer(0,label)
    imbuf.write(buf,filepath=str(path))
    path.replace(directory/(clip+'.png'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('clips',nargs='*',metavar='CLIP')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    unexpected = set(args.clips)-FRAMES.keys()
    if unexpected:
        parser.error('Unknown clips: '+', '.join(sorted(unexpected)))
    cfg = json.loads(FILE.read_text())
    replay = Replay()
    camera = setup(replay.scene)
    directory = HERE/'renders'
    directory.mkdir(exist_ok=True)
    temp = directory/f'.panel.{os.getpid()}.png'
    for clip in args.clips or FRAMES:
        prop, extra = asset_scene(replay,cfg,clip)
        replay.select(clip)
        panels = {view:[] for view in VIEWS}
        for frame in FRAMES[clip]:
            sec = frame/SOURCE_FPS[clip]
            points,hand = replay.time(sec)
            if clip in CARRY:
                prop.obj.matrix_world = moving_pose(cfg,clip,sec,hand)
                # Frame the grip against the torso at enough resolution to see skin contact.
                center = np.array(prop.obj.matrix_world.translation)
                if clip=='hold_box':
                    center += [0,0,.125]
                if clip=='hold_bag':
                    center += [.025,0,-.095]
                if clip=='take_item':
                    center[0] += .065
                    center[2] -= .055
                scale = {'hold_item':.49,'hold_box':.60,'hold_bag':.52,'take_item':.65}[clip]
            else:
                center = (0,-.08,.53)
                scale = 1.22
            focus = Vector(center)
            camera.data.ortho_scale = scale
            for view,aim in VIEWS.items():
                camera.location = focus+Vector(aim).normalized()*3
                camera.rotation_euler = (focus-camera.location).to_track_quat('-Z','Y').to_euler()
                replay.scene.render.filepath = str(temp)
                bpy.ops.render.render(write_still=True)
                img = bpy.data.images.load(str(temp),check_existing=False)
                img.colorspace_settings.name = 'Non-Color'
                pixels = np.empty(SIZE[0]*SIZE[1]*4,dtype=np.float32)
                img.pixels.foreach_get(pixels)
                panels[view].append(np.uint8(np.clip(pixels.reshape(SIZE[1],SIZE[0],4)[::-1,:,:3],0,1)*255+.5))
                bpy.data.images.remove(img)
        review_sheet(directory,clip,FRAMES[clip],panels)
        for item in (prop,*extra):
            bpy.data.objects.remove(item.obj,do_unlink=True)
    temp.unlink(missing_ok=True)


if __name__=='__main__':
    main()
