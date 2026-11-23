"""Render matched Cycles CPU comparisons from fresh reads of the actual assets."""
import math
import struct
import sys
import zlib
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate_actions import mount
import blf
import imbuf
W,H=310,344
RENDERS=OUT/'renders'
TEMP=OUT/'.runtime'/'render_tiles'
FRAMES={'sit_down':[0,12,24,36],'sit_idle':[0,22,45,68],'stand_up':[0,10,20,30],'hold_item':[0,15,30,44]}

def light_scene(sc,body):
    for ob in sc.objects:
        if ob.type=='MESH' and ob!=body:ob.hide_render=True
    sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=12
    sc.cycles.use_denoising=True
    sc.render.resolution_x=W;sc.render.resolution_y=H;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
    sc.render.use_compositing=False;sc.render.use_sequencer=False
    sc.world=bpy.data.worlds.new('Studio world');sc.world.use_nodes=True
    bg=sc.world.node_tree.nodes['Background'];bg.inputs[0].default_value=(.64,.70,.80,1);bg.inputs[1].default_value=.55
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.00045))
    floor=bpy.data.materials.new('Studio floor');floor.diffuse_color=(.36,.40,.43,1);bpy.context.object.data.materials.append(floor)
    for pos,power,size,col in [((-1.6,-2.5,3.),170,2.,(1,.91,.83)),((1.4,-1,1.8),65,1.6,(.82,.91,1)),((.3,1.4,2.1),110,1.7,(1,.96,.88))]:
        d=bpy.data.lights.new('Softbox','AREA');d.energy=power;d.size=size;d.color=col
        ob=bpy.data.objects.new('Softbox',d);sc.collection.objects.link(ob);ob.location=pos
        ob.rotation_euler=(Vector((0,0,.5))-ob.location).to_track_quat('-Z','Y').to_euler()
    d=bpy.data.cameras.new('Comparison');d.type='ORTHO';d.clip_start=.01
    cam=bpy.data.objects.new('Comparison',d);sc.collection.objects.link(cam);sc.camera=cam
    return cam

def tile_path(clip,f,stage,authored):
    return TEMP/f'{clip}_{f}_{stage}_{int(authored)}.png'

def capture(stage,path,authored,selected):
    if authored:
        chibi.fresh();scene=bpy.context.scene;arm=chibi.armature(chibi.load(chibi.BODY))
        body=scene.objects['Base_Body'];chibi.load(path);actions=bpy.data.actions
    else:
        scene,arm,body,actions=load(path)
    cam=light_scene(scene,body)
    chair,=chibi.load(ASSETS/'chair.glb');cup,=chibi.load(ASSETS/'prop.glb')
    for clip,fs in FRAMES.items():
        if (authored and clip!='hold_item') or clip not in selected:continue
        chibi.bind(arm,actions[clip]);hold=clip=='hold_item'
        chair.hide_render=hold;cup.hide_render=not hold
        target=Vector((0,-.09,.55)) if not hold else Vector((0,-.03,.51))
        direction=Vector((.64,-1,.16) if not hold else (-.40,-1,.15))
        if clip=='sit_idle':direction=Vector((-.56,-1,.20))
        cam.location=target+direction.normalized()*3
        cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
        cam.data.ortho_scale=1.24 if not hold else 1.10
        for f in fs:
            at(scene,f)
            cup.matrix_world=arm.matrix_world@bone(arm,'RightHand').matrix@mount()
            scene.render.filepath=str(tile_path(clip,f,stage,authored))
            bpy.ops.render.render(write_still=True)

def plate(clip,authored):
    pad,gap,head,caption=12,16,42,25
    width=W*4+gap+2*pad+6;height=head+2*(H+caption)+pad
    pix=np.full((height,width,3),241,np.uint8)
    title=f'{clip}    /    '+('Authored grip body' if authored else 'Master body')
    labels=[(pad,28,22,title)]
    for n,f in enumerate(FRAMES[clip]):
        for col,stage in enumerate(('Before','After')):
            tile=tile_path(clip,f,stage,authored)
            im=bpy.data.images.load(str(tile),check_existing=False);im.colorspace_settings.name='Non-Color'
            arr=np.empty(W*H*4,np.float32);im.pixels.foreach_get(arr);bpy.data.images.remove(im)
            x=pad+(n%2)*(2*W+gap+3)+col*(W+3);y=head+(n//2)*(H+caption)
            pix[y:y+H,x:x+W]=np.uint8(np.clip(arr.reshape(H,W,4)[::-1,:,:3]*255+.5,0,255))
            labels.append((x+5,y+H+17,14,f'{stage}    /    frame {f}'))
    def chunk(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d))
    dest=RENDERS/(clip+('_authored_grip' if authored else '')+'_before_after.png')
    dest.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+
                     chunk(b'IDAT',zlib.compress(b''.join(b'\0'+r.tobytes() for r in pix)))+chunk(b'IEND',b''))
    buf=imbuf.load(str(dest))
    with blf.bind_imbuf(0,buf):
        for x,y,size,label in labels:
            blf.size(0,size);blf.color(0,.06,.075,.08,1);blf.position(0,x,height-y,0);blf.draw_buffer(0,label)
    imbuf.write(buf,filepath=str(dest))

if __name__=='__main__':
    RENDERS.mkdir(exist_ok=True);TEMP.mkdir(exist_ok=True,parents=True)
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    selected=set(args) if args else set(FRAMES)
    for authored in (False,True):
        if authored and 'hold_item' not in selected:continue
        for stage,path in [('Before',SOURCE),('After',FIXED)]:capture(stage,path,authored,selected)
        for clip in selected:
            if not authored or clip=='hold_item':plate(clip,authored)
