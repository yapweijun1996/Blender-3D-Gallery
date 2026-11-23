"""Map the six-view dark pixels back to the rendered GLB triangles."""
from pathlib import Path
import sys,json,hashlib
import bpy,numpy as np
from mathutils import Vector
H=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.path.insert(0,str(H))
from render_views import read_image,save_sheet
from fit_hair import MASTER,GLB,make_tree
info=json.loads((H/'pixels_v1.json').read_text())
assert info['asset_sha256']==hashlib.sha256(GLB.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(MASTER),use_scripts=False)
bpy.ops.import_scene.gltf(filepath=str(GLB))
o=bpy.data.objects['Hair_High_Ponytail'];bt=make_tree(bpy.data.objects['Base_Body']);ht=make_tree(o)
uv=o.data.uv_layers.active
fitted=[min(uv.data[l].uv.y for l in f.loop_indices)>.847 for f in o.data.polygons]
sheet=read_image(H/'fit_views_v1.png');out={}
n=512;target=Vector((.039,.025,.861))
views=[(0,-1,0),(.68,-1,.055),(-.68,-1,.055),(1,0,.025),(0,1,.035),(-1,0,.025)]
for i,(view,camdir) in enumerate(zip(info['views'],views)):
    x,y=i%3*n,(1-i//3)*n;tile=sheet[y:y+n,x:x+n]
    dark=tile[:,:,:3]@np.array([.2126,.7152,.0722])<.12
    normal=Vector(camdir).normalized();d=-normal
    rot=d.to_track_quat('-Z','Y');dx=rot@Vector((.61/n,0,0));dy=rot@Vector((0,.61/n,0));start=target+2*normal-(n-1)/2*(dx+dy)
    counts=dict(fringe_and_front_rim=0,rear_rim_and_nape=0,upper_cap_and_ponytail=0)
    for row,col in zip(*np.where(dark)):
        p=start+dx*int(col)+dy*int(row)
        hit,_,ix,dist=ht.ray_cast(p,d,3)
        if ix is None or bt.ray_cast(p,d,dist)[0] is not None:continue
        zone='upper_cap_and_ponytail' if not fitted[ix] else ('fringe_and_front_rim' if hit.y<0 else 'rear_rim_and_nape')
        counts[zone]+=1;tile[row,col,:3]=[.05,.93,.95]
    assert sum(counts.values())==info['views'][view]['near_black'],(view,counts)
    out[view]=counts
save_sheet(H/'checks/near_black_overlay.png',sheet)
(H/'checks/near_black_regions.json').write_text(json.dumps(dict(asset_sha256=info['asset_sha256'],views=out,method='Frontmost hair hit. Original upper charts versus new hem/lining atlas band, with body-space Y=0 dividing front and rear rim.'),indent=2)+'\n')
print(out,flush=True)

