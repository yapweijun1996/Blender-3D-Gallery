"""Render the delivered GLBs using Cycles CPU and compose labeled review sheets in Blender."""
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
import blf
import imbuf
import numpy as np
from mathutils import Vector, Matrix
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from hand_common import OUT, GESTURES, SIDES, clean_pose, prefix, set_action, run_batch
from importlib.util import spec_from_file_location, module_from_spec
spec=spec_from_file_location('first_pass_studio',OUT.parent/'render_hands.py')
studio_module=module_from_spec(spec)
spec.loader.exec_module(studio_module)
VIEWS=('palm','back','thumb-side')
CACHE=OUT/'.work'/'views'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def capture():
    CACHE.mkdir(exist_ok=True,parents=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(OUT/'base_body.glb'))
    body=bpy.data.objects['Base_Body']
    rig=bpy.data.objects['Armature']
    bpy.ops.import_scene.gltf(filepath=str(OUT/'hand_gestures.glb'))
    clean_pose(rig)
    scene=bpy.context.scene
    studio=studio_module.Studio(body)
    cam=studio.camera
    deps=bpy.context.evaluated_depsgraph_get()
    rest=[body.matrix_world@v.co for v in body.data.vertices]
    partial='--proof' in sys.argv
    pose_filter=next((s.split('=')[1].split(',') for s in sys.argv if s.startswith('--poses=')),None)
    for tag,side,sg in SIDES:
        ids=[i for i,p in enumerate(rest) if sg*p.x>.257]
        for g in GESTURES:
            if pose_filter and g not in pose_filter:continue
            name='hand_'+g+'_'+tag
            set_action(rig,bpy.data.actions[name])
            ev=body.evaluated_get(deps)
            pts=[ev.matrix_world@v.co for v in ev.data.vertices]
            dirs={'palm':(.20*sg,-.09,-1),'back':(.20*sg,.09,1),'thumb-side':(.24*sg,-1,-.33)}
            if g=='thumbs_up':dirs.update(palm=(.32*sg,-.93,-.78),back=(.12*sg,.90,.79))
            if g=='grip_small':dirs['thumb-side']=(.45*sg,-1,0)
            if g in ('pinch','ok'):dirs.update(detail_palm=dirs['palm'],detail_oblique=(-.10*sg,-1,-.75))
            for view,vec in dirs.items():
                macro=view.startswith('detail')
                width,height=(576,448) if macro else (384,336)
                if partial:width,height=width//2,height//2
                scene.render.resolution_x,scene.render.resolution_y=width,height
                scene.cycles.samples=4 if partial else (24 if macro else 14)
                direction=Vector(vec).normalized()
                up=Vector((0,0,1) if g=='thumbs_up' else (sg,0,0))
                up=(up-direction*direction.dot(up)).normalized()
                right=up.cross(direction).normalized()
                cam.rotation_euler=Matrix((right,up,direction)).transposed().to_euler()
                center=Vector();sizes=[]
                for axis in (right,up,direction):
                    dist=[pts[i].dot(axis) for i in ids]
                    center+=axis*((min(dist)+max(dist))/2);sizes.append(max(dist)-min(dist))
                scale=max(sizes[0],sizes[1]*width/height)*1.18
                if macro:
                    contact=[]
                    for digit in ('Thumb','Index'):
                        bone=rig.pose.bones[prefix(side)+digit+'4']
                        bind=rig.matrix_world@bone.bone.head_local
                        distal=(rig.matrix_world.to_3x3()@bone.bone.matrix_local.col[1].xyz).normalized()
                        owned=[i for i in ids if any(body.vertex_groups[w.group].name.startswith(prefix(side)+digit) and w.weight>.25 for w in body.data.vertices[i].groups)]
                        end=max((rest[i]-bind).dot(distal) for i in owned)
                        cap=[i for i in owned if (rest[i]-bind).dot(distal)>end-.0022]
                        contact.append(sum((pts[i] for i in cap),Vector())/len(cap))
                    center=sum(contact,Vector())*.5
                    scale=.062 if view=='detail_palm' else .038
                cam.location=center+direction*.55
                cam.data.ortho_scale=scale
                cam.data.clip_end=.65 if macro else .55+sizes[2]/2+.005
                for light,(x,y,z) in zip(studio.lights,[(-.14,.18,.2),(.2,-.02,.23),(.12,.13,-.16)]):
                    light.location=center+x*right+y*up+z*direction
                    light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
                suffix='_proof' if partial else ''
                scene.render.filepath=str(CACHE/(name+'_'+view+suffix+'.png'))
                bpy.ops.render.render(write_still=True)
                if not partial and g=='grip_small' and view=='thumb-side':
                    from bpy_extras.object_utils import world_to_camera_view
                    from hand_common import rest_data
                    # Use the fixed round-one cylinder axis reference in world space.
                    rest_p=json.loads((OUT.parent/'hand_check.json').read_text())['rest'][tag]['palm_center_m']
                    guide=Vector(rest_p)+Vector((.005*sg,0,-.023))
                    c=world_to_camera_view(scene,cam,guide)
                    (CACHE/(name+'_guide.json')).write_text(json.dumps([c.x,c.y,.020/scale]))
    if not partial:
        (CACHE/'exports.json').write_text(json.dumps({f:sha(OUT/f) for f in ['base_body.glb','hand_gestures.glb']}))


def compose(close=False, proof=False):
    import struct, zlib
    # Keep PNGs display-referred through assembly; Blender supplies all pixels and fonts.
    suffix='_proof' if proof else ''
    rows=('pinch','ok') if close else GESTURES
    cols=('detail_palm','detail_oblique') if close else VIEWS
    cw,ch=((576,448) if close else (384,336))
    if proof:cw,ch=cw//2,ch//2
    left=160 if proof else 185
    top=108;sep=4;group=16
    width=left+2*(len(cols)*(cw+sep))+group+20
    height=top+len(rows)*(ch+sep)+18
    bg=np.array([244,242,236],np.uint8)
    pixels=np.empty((height,width,3),np.uint8);pixels[:]=bg
    labels=[]
    def txt(x,y,s,t):labels.append((x,y,s,t))
    txt(18,38,30,'Fingertip contact' if close else 'Chibi hand gestures')
    for si,(tag,side,sg) in enumerate(SIDES):
        x0=left+si*(len(cols)*(cw+sep)+group)
        txt(x0,65,21,side+' hand')
        for ci,v in enumerate(cols):
            x=x0+ci*(cw+sep)
            txt(x,91,16,{'palm':'Palm','back':'Dorsal','thumb-side':'Thumb side','detail_palm':'Palmar close-up','detail_oblique':'Oblique close-up'}[v])
            for ri,g in enumerate(rows):
                y=top+ri*(ch+sep)
                if not si and not ci:txt(18,y+ch//2,21,g.replace('_',' ').capitalize() if g!='ok' else 'OK')
                path=CACHE/('hand_'+g+'_'+tag+'_'+v+suffix+'.png')
                if not path.exists() and proof:continue
                im=bpy.data.images.load(str(path),check_existing=False)
                im.colorspace_settings.name='Non-Color'
                a=np.empty(cw*ch*4,np.float32);im.pixels.foreach_get(a)
                tile=(a.reshape(ch,cw,4)[::-1,:,:3]*255+.5).astype(np.uint8)
                if not proof and g=='grip_small' and v=='thumb-side':
                    cx,cy,r=json.loads((CACHE/('hand_'+g+'_'+tag+'_guide.json')).read_text())
                    yy,xx=np.ogrid[:ch,:cw];dx=xx-cx*cw;dy=yy-(1-cy)*ch
                    ring=(abs(np.hypot(dx,dy)-r*cw)<.85)&((np.arctan2(dy,dx)*14/np.pi)%2<1.14)
                    tile[ring]=[153,205,211]
                    if not si:txt(18,y+ch//2+25,15,'Ø 40 mm guide')
                pixels[y:y+ch,x:x+cw]=tile
                bpy.data.images.remove(im)
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    name=('pinch_ok_closeups' if close else 'contact_sheet')+suffix+'.png'
    file=(OUT/'.work' if proof else OUT)/name
    h=struct.pack('>IIBBBBB',width,height,8,2,0,0,0)
    file.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',h)+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+r.tobytes() for r in pixels),5))+chunk(b'IEND',b''))
    buf=imbuf.load(str(file))
    with blf.bind_imbuf(0,buf):
        for x,y,s,t in labels:
            blf.size(0,s);blf.color(0,.08,.14,.17,1);blf.position(0,x,height-y,0);blf.draw_buffer(0,t)
    imbuf.write(buf,filepath=str(file))


def main():
    if '--compose' not in sys.argv:capture()
    if '--capture' not in sys.argv:
        for close in (False,True):compose(close,'--proof' in sys.argv)
if __name__=='__main__':run_batch(main)
