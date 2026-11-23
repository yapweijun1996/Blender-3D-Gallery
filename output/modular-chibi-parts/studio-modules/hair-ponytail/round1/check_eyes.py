"""Check the exported fringe against the master's textured eye marks in front projection."""
import sys,json,hashlib
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
from mathutils.geometry import barycentric_transform
H=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.path.insert(0,str(H))
from fit_hair import GLB,MASTER,make_tree
bpy.ops.wm.open_mainfile(filepath=str(MASTER),use_scripts=False)
b=bpy.data.objects['Base_Body'];bt=make_tree(b)
bpy.ops.import_scene.gltf(filepath=str(GLB));ht=make_tree(bpy.data.objects['Hair_High_Ponytail'])
bs=b.active_material.node_tree.nodes.get('Principled BSDF');im=bs.inputs['Base Color'].links[0].from_node.image
im.colorspace_settings.name='Non-Color';w,h=im.size
pix=np.empty((h,w,4),'f');im.pixels.foreach_get(pix.ravel())
uv=b.data.uv_layers.active;tris=[];tex=[]
for f in b.data.polygons:
    tris.append([b.matrix_world@b.data.vertices[i].co for i in f.vertices])
    tex.append([Vector((*uv.data[i].uv,0)) for i in f.loop_indices])
d=Vector((0,1,0));step=.0005;result={}
for name,(x0,x1) in {'viewer_left':(-.144,-.031),'viewer_right':(.031,.145)}.items():
    count=occluded=0;gaps=[]
    for x in np.arange(x0,x1+step/2,step):
        top=None;first_hair=None
        for z in np.arange(.686,.851,step):
            p=Vector((x,-1,z));bpos,_,ix,dist=bt.ray_cast(p,d,2)
            if bpos is None:continue
            hair=ht.ray_cast(p,d,dist)[0] is not None
            if hair and first_hair is None:first_hair=z
            if z>.79:continue
            st=barycentric_transform(bpos,*tris[ix],*tex[ix]);rgb=pix[min(h-1,max(0,int(st.y*h))),min(w-1,max(0,int(st.x*w))),:3]
            # On the neutral master the iris and upper lid are the only dark
            # base-colour marks within these two front eye windows.
            if float(rgb@np.array([.2126,.7152,.0722]))<.43:
                count+=1;occluded+=int(hair);top=z
        if top is not None and first_hair is not None:gaps.append(first_hair-top)
    result[name]=dict(eye_samples=count,occluded=occluded,min_projected_margin_m=min(gaps))
out=dict(asset_sha256=hashlib.sha256(GLB.read_bytes()).hexdigest(),master_sha256=hashlib.sha256(MASTER.read_bytes()).hexdigest(),sampling_pitch_m=step,eye_mark_max_encoded_luminance=.43,eyes=result)
(H/'eyes_check.json').write_text(json.dumps(out,indent=2)+'\n');print(out,flush=True)

