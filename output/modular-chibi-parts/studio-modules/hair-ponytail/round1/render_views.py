"""Render the exported GLB on the master. Count only frontmost hair pixel centres."""
import bpy,sys,math,json,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE))
from fit_hair import MASTER,GLB,bob,make_tree
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def read_image(path):
    im=bpy.data.images.load(str(path),check_existing=False);im.colorspace_settings.name='Non-Color'
    w,h=im.size;a=np.empty((h,w,4),'f');im.pixels.foreach_get(a.ravel());bpy.data.images.remove(im)
    return a
def save_sheet(p,arr):
    h,w=arr.shape[:2];im=bpy.data.images.new('six views',w,h,alpha=False);im.colorspace_settings.name='Non-Color'
    im.pixels.foreach_set(arr.ravel());im.file_format='PNG';im.filepath_raw=str(p);im.save();bpy.data.images.remove(im)
def main():
    sc=bpy.context.scene
    bpy.ops.wm.open_mainfile(filepath=str(MASTER),use_scripts=False)
    bpy.ops.import_scene.gltf(filepath=str(GLB));sc=bpy.context.scene
    hair=sc.objects['Hair_High_Ponytail'];body=sc.objects['Base_Body']
    bt,ht=make_tree(body),make_tree(hair)
    bob.cpu_studio(sc)
    cd=bpy.data.cameras.new('Fit orthographic');cd.type='ORTHO'
    cam=bpy.data.objects.new(cd.name,cd);sc.collection.objects.link(cam);sc.camera=cam
    def view(direction,target,scale,res):
        cd.ortho_scale=scale
        target=Vector(target);cam.location=target+Vector(direction).normalized()*2
        cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
        sc.render.resolution_x=sc.render.resolution_y=res
        bpy.context.view_layer.update()
    def capture(path):
        sc.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    def count(arr):
        h,w=arr.shape[:2];q=cam.rotation_euler.to_quaternion()
        right=q@Vector((cd.ortho_scale/w,0,0));up=q@Vector((0,cd.ortho_scale/h,0))
        d=q@Vector((0,0,-1));start=cam.location-right*((w-1)/2)-up*((h-1)/2)
        mask=np.zeros((h,w),bool)
        for j in range(h):
            orig=start+up*j
            for i in range(w):
                p=orig+right*i;_,_,idx,dist=ht.ray_cast(p,d,3)
                if idx is not None:mask[j,i]=bt.ray_cast(p,d,dist)[0] is None
        rgb=arr[:,:,:3][mask]
        l=rgb@np.array([.2126,.7152,.0722])
        return dict(hair_pixels=int(mask.sum()),near_black=int((l<.12).sum()))
    views=[('front',(0,-1,0)),('three_quarter_left',(.68,-1,.055)),('three_quarter_right',(-.68,-1,.055)),('left',(1,0,.025)),('back',(0,1,.035)),('right',(-1,0,.025))]
    draft='quick' in sys.argv
    n=320 if draft else 512
    if draft:sc.cycles.samples=4
    sheet=np.empty((n*2,n*3,4),'f');report={}
    target=(.039,.025,.861)
    for k,(name,d) in enumerate(views):
        view(d,target,.61,n);f=HERE/'.runtime'/('view_'+name+'.png');capture(f);arr=read_image(f)
        x,y=k%3*n,(1-k//3)*n;sheet[y:y+n,x:x+n]=arr
        if not draft:report[name]=count(arr)
    save_sheet(HERE/('.runtime/quick.png' if draft else 'fit_views_v1.png'),sheet)
    if draft:return
    captures={}
    for name,d,t,scale in [('fringe',(0,-1,.025),(.002,-.09,.832),.409),('side',(-.96,-.42,.005),(-.02,0,.79),.416),('nape',(0,1,-.13),(.006,.08,.756),.452)]:
        view(d,t,scale,720);f=HERE/('closeup_'+name+'.png');capture(f);captures[f.name]=sha(f)
    (HERE/'pixels_v1.json').write_text(json.dumps(dict(asset_sha256=sha(GLB),threshold='Rec.709 weighted encoded sRGB < 0.12',mask='pixel-centre hair hit strictly before master body',views=report,sheet_sha256=sha(HERE/'fit_views_v1.png'),closeups=captures),indent=2)+'\n')
if __name__=='__main__':main()

