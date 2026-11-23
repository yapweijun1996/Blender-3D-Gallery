"""Render the final socket JSON on the original assets in Cycles CPU."""
import struct
import zlib

import blf
import imbuf
from parcel import *


SIZE = (384, 416)
FRAMES = (0, 12, 30, 45)
VIEWS = {'front': (0,-1,.04), 'right side': (-1,0,.045), 'left side': (1,0,.045)}


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
    width,height = len(frames)*w+24,len(view_rows)*(h+29)+50
    rgb = np.full((height,width,3), (236,242,242),dtype=np.uint8)
    labels = [(10,28,22,BODY_NAME.title()+' parcel carry')]
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
    cfg = json.loads(SOCKET_FILE.read_text())
    replay = ParcelReplay(cfg)
    camera = setup(replay.scene)
    camera.data.ortho_scale = .62
    directory = HERE/'renders'
    directory.mkdir(exist_ok=True)
    temp = directory/f'.panel.{os.getpid()}.png'
    prop, _ = replay.prop(CLIP)
    local = bpy_pose(cfg['sockets'][CLIP])
    panels = {view:[] for view in VIEWS}
    try:
        for frame in FRAMES:
            _, hand = replay.time(frame/24)
            prop.obj.matrix_world = hand @ local
            q = transform(prop.points, prop.obj.matrix_world)
            focus = Vector((q.min(0)+q.max(0))/2 + np.array([0,0,.055]))
            for view,aim in VIEWS.items():
                camera.location = focus+Vector(aim).normalized()*3
                camera.rotation_euler = (focus-camera.location).to_track_quat('-Z','Y').to_euler()
                replay.scene.render.filepath = str(temp)
                bpy.ops.render.render(write_still=True)
                img = bpy.data.images.load(str(temp),check_existing=False)
                img.colorspace_settings.name = 'Non-Color'
                pixels = np.empty(SIZE[0]*SIZE[1]*4,dtype=np.float32)
                img.pixels.foreach_get(pixels)
                rgb = pixels.reshape(SIZE[1],SIZE[0],4)[::-1,:,:3]
                panels[view].append(np.uint8(np.clip(rgb,0,1)*255+.5))
                bpy.data.images.remove(img)
        review_sheet(directory,CLIP,FRAMES,panels)
    finally:
        temp.unlink(missing_ok=True)


if __name__=='__main__':
    main()
