"""Render the exported body, motion and props. Compose the review sheets in Blender."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from chibi import *
import blf
import imbuf

RENDERS=OUT/'renders'
SIZE=(322,370)
FRAMES={'sit_down':(0,12,24,36),'stand_up':(0,10,20,30),
        'sit_idle':(0,22,45,68),'hold_item':(0,15,30,45)}


def mount():
    data=json.loads((OUT/'attachment.json').read_text())['blender_pose_bone_head_local']
    x,y,z,w=data['quaternion_xyzw']
    return Matrix.LocRotScale(Vector(data['translation_m']),Quaternion((w,x,y,z)),Vector((1,1,1)))


def capture():
    RENDERS.mkdir(exist_ok=True)
    fresh()
    arm=armature(load(BODY));load(OUT/'actions.glb')
    chair,=load(OUT/'chair.glb')
    cup,=load(OUT/'prop.glb')
    sc=bpy.context.scene
    sc.render.engine='CYCLES'
    sc.cycles.device='CPU'
    sc.cycles.samples=12
    sc.cycles.use_denoising=True
    sc.render.resolution_x,sc.render.resolution_y=SIZE
    sc.render.resolution_percentage=100
    sc.render.use_compositing=False
    sc.render.use_sequencer=False
    sc.world=bpy.data.worlds.new('Paper daylight')
    sc.world.use_nodes=True
    bg=sc.world.node_tree.nodes['Background']
    bg.inputs[0].default_value=(.70,.78,.85,1)
    bg.inputs[1].default_value=.48
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.00035))
    ground=bpy.context.object
    floor=bpy.data.materials.new('Studio floor')
    floor.diffuse_color=(.53,.60,.61,1)
    ground.data.materials.append(floor)
    for pos,power,size,color in [((-1.6,-2.5,3.0),170,2.0,(1,.90,.80)),((1.4,-1.2,1.5),58,1.6,(.83,.91,1)),((.2,1.5,2),88,1.25,(1,.95,.86))]:
        l=bpy.data.lights.new('Softbox','AREA')
        l.energy=power;l.size=size;l.color=color
        ob=bpy.data.objects.new(l.name,l);sc.collection.objects.link(ob)
        ob.location=pos;ob.rotation_euler=(Vector((0,0,.45))-ob.location).to_track_quat('-Z','Y').to_euler()
    cam=bpy.data.cameras.new('Review')
    camera=bpy.data.objects.new('Review',cam);sc.collection.objects.link(camera);sc.camera=camera
    cam.type='ORTHO';cam.clip_start=.01
    def render(target,direction,scale,file):
        camera.location=Vector(target)+Vector(direction).normalized()*3
        camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
        cam.ortho_scale=scale
        sc.render.filepath=str(file)
        bpy.ops.render.render(write_still=True)
    proof='--proof' in sys.argv
    selected={s[7:] for s in sys.argv if s.startswith('--clip=')}
    for name,frames in FRAMES.items():
        if selected and name not in selected:continue
        hold=name=='hold_item'
        chair.hide_render=hold;cup.hide_render=not hold
        bind(arm,bpy.data.actions[name])
        for f in (frames[:1] if proof else frames):
            sc.frame_set(f)
            cup.matrix_world=arm.matrix_world@arm.pose.bones[N+'RightHand'].matrix@mount()
            for view,direction in [('front',(0,-1,.075)),('side',(-1,0,.065))]:
                render((0,-.087 if not hold else -.01,.505 if hold else .552),direction,1.17 if hold else 1.29,RENDERS/f'{name}_{f:03d}_{view}.png')
            if hold and f==0:
                render(cup.matrix_world.translation,(-.80,-1,.48),.211,RENDERS/'cup_detail.png')


def sheet(name):
    import zlib
    w,h=SIZE
    W,H=4*w+24,2*(h+30)+58
    pix=np.zeros((H,W,3),np.uint8)+239
    labels=[(9,30,24,name)]
    for row,view in enumerate(['front','side']):
        for col,f in enumerate(FRAMES[name]):
            p=RENDERS/f'{name}_{f:03d}_{view}.png'
            img=bpy.data.images.load(str(p),check_existing=False)
            img.colorspace_settings.name='Non-Color'
            a=np.empty(w*h*4,np.float32);img.pixels.foreach_get(a)
            x=6+col*(w+3);y=48+row*(h+30)
            pix[y:y+h,x:x+w]=np.uint8(a.reshape(h,w,4)[::-1,:,:3]*255+.5)
            labels.append((x+3,y+h+19,15,f'{view.title()}   /   {f/FPS:.2f} s'))
            bpy.data.images.remove(img)
    def chunk(t,data):
        return struct.pack('>I',len(data))+t+data+struct.pack('>I',zlib.crc32(t+data))
    png=RENDERS/(name+'.png')
    head=struct.pack('>IIBBBBB',W,H,8,2,0,0,0)
    png.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',head)+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+r.tobytes() for r in pix)))+chunk(b'IEND',b''))
    buf=imbuf.load(str(png))
    with blf.bind_imbuf(0,buf):
        for x,y,size,s in labels:
            blf.size(0,size);blf.color(0,.065,.12,.13,1);blf.position(0,x,H-y,0);blf.draw_buffer(0,s)
    imbuf.write(buf,filepath=str(png))


if __name__=='__main__':
    capture()
    if '--proof' not in sys.argv:
        for name in FRAMES:sheet(name)
