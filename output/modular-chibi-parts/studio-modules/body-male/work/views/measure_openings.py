"""Measure enclosed background areas in the untouched radial fist/raised-thumb PNGs."""
import collections
import json
import math
from pathlib import Path
import bpy
import numpy as np
import hashlib

folder=Path(__file__).resolve().parent/'renders'
out={}
for tag in ('L','R'):
    m=json.loads((folder/f'manifest_{tag}.json').read_text())
    for pose in ('fist','thumbs_up'):
        name=f'hand_{pose}_{tag}_thumb-side.png'
        frame=next(f for f in m['frames'] if f['image']==name)
        p=folder/name
        assert hashlib.sha256(p.read_bytes()).hexdigest()==frame['sha256']
        im=bpy.data.images.load(str(p));im.colorspace_settings.name='Non-Color'
        w,h=im.size[:]
        data=np.empty(w*h*4,np.float32);im.pixels.foreach_get(data)
        rgb=np.round(255*data.reshape(h,w,4)[::-1,:,:3]).astype(np.int16)
        bg=np.median(rgb[:10,:10,:],axis=(0,1))
        remaining=np.max(np.abs(rgb-bg),axis=2)<=3
        pp=1000*frame['ortho_width_m']/w
        holes=[]
        for y,x in np.argwhere(remaining):
            if not remaining[y,x]:
                continue
            queue=collections.deque([(x,y)]);remaining[y,x]=False;coords=[]
            while queue:
                xx,yy=queue.popleft();coords.append((xx,yy))
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                    a,b=xx+dx,yy+dy
                    if 0<=a<w and 0<=b<h and remaining[b,a]:
                        remaining[b,a]=False
                        queue.append((a,b))
            if len(coords)<4:
                continue
            co=np.array(coords)
            lo=co.min(0);hi=co.max(0)
            if lo.min()==0 or hi[0]==w-1 or hi[1]==h-1:continue
            area=len(coords)*pp**2
            holes.append({'pixels':len(coords),'area_mm2':round(area,3),'bbox_mm':[round(float(x),3) for x in ((hi-lo+1)*pp)],'equivalent_diameter_mm':round(2*math.sqrt(area/math.pi),3)})
        holes.sort(key=lambda h:h['pixels'],reverse=True)
        out[name]={'body_sha256':m['body'][1],'library_sha256':m['library'][1],'image_sha256':frame['sha256'],'mm_per_pixel':pp,'enclosed_background':holes}
print(json.dumps(out,indent=2))
(folder.parent/'fold_openings.json').write_text(json.dumps({'method':'Enclosed 8-connected background pixels, max RGB deviation 3 from the upper-left studio color; components smaller than 4 pixels omitted. Areas are orthographic projections and depend on view.','views':out},indent=2))
