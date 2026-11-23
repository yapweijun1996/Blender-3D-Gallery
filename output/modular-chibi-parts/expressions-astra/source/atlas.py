"""Reserve high texel density for the facial charts within a single standard base map."""
import numpy as np
from face import pixels,triangles,sample
from regions import CENTER

SIZE=1024
BODY_ROWS=557
PAD=6

def chart_groups(idx,mask):
    # Imported glTF vertices are already split along UV seams.
    neighbours={}
    for f in np.flatnonzero(mask):
        for v in idx[f]:
            neighbours.setdefault(v,[]).append(f)
    todo=set(np.flatnonzero(mask))
    while todo:
        group=[todo.pop()]
        for f in group:
            for v in idx[f]:
                for n in neighbours[v]:
                    if n in todo:
                        todo.remove(n)
                        group.append(n)
        yield np.array(group)

def layout(body):
    xyz,idx,uv=triangles(body)
    corners=xyz[idx]
    x,y,z=corners.transpose(2,0,1)
    inside=(np.abs(x-CENTER)<.154)&(y<-.067)&(z>.633)&(z<.845)
    charts=[]
    for ids in chart_groups(idx,inside.any(axis=1)):
        orig=uv[ids]
        lo=orig.min(axis=(0,1))
        hi=orig.max(axis=(0,1))
        charts.append((ids,lo,hi))
    # Horizontal shelves keep a six-texel gutter around every chart.
    def pack(scale):
        boxes=[]
        for k,(_,lo,hi) in enumerate(charts):
            extent=(hi-lo)*scale
            rotate=extent[1]>extent[0]
            w,h=np.ceil(extent[::-1] if rotate else extent).astype(int)+2*PAD
            boxes.append((k,w,h,rotate))
        shelves=[]
        rects={}
        for k,w,h,rotate in sorted(boxes,key=lambda item:-item[2]):
            if w>SIZE:return None
            for row in shelves:
                if h<=row[1] and row[2]+w<=SIZE:break
            else:
                y0=BODY_ROWS+2 if not shelves else shelves[-1][0]+shelves[-1][1]
                if y0+h>SIZE:return None
                row=[y0,h,0]
                shelves.append(row)
            rects[k]=(row[2],row[0],w,h,rotate)
            row[2]+=w
        return rects
    low,high=1.,20000.
    for _ in range(24):
        mid=(low+high)/2
        if pack(mid):low=mid
        else:high=mid
    scale=low
    rects=pack(scale)
    texture=pixels(next(n.image for n in body.data.materials[0].node_tree.nodes if n.type=="TEX_IMAGE"))[:,:,:3]
    h,w=texture.shape[:2]
    atlas=np.zeros((SIZE,SIZE,3),np.float32)
    atlas[:]=texture[h//2,w//2]
    # Area-average the downsampled body portion from the source pixel buffer.
    j,i=np.mgrid[:BODY_ROWS,:SIZE]
    body_img=np.zeros((BODY_ROWS,SIZE,3),np.float32)
    for dy in (-.375,-.125,.125,.375):
        for dx in (-.25,.25):
            body_img+=sample(texture,(i+.5+dx)*w/SIZE-.5,(j+.5+dy)*h/BODY_ROWS-.5)/8
    atlas[:BODY_ROWS]=body_img
    atlas[BODY_ROWS:BODY_ROWS+2]=body_img[-1]
    result=uv.copy()
    result[:,:,1]*=BODY_ROWS/SIZE
    for k,(ids,lo,hi) in enumerate(charts):
        x0,y0,bw,bh,rotate=rects[k]
        local=uv[ids]-lo
        if rotate:local=local[:,:,[1,0]]
        result[ids]=(local*scale+[x0+PAD,y0+PAD])/SIZE
        j,i=np.mgrid[:bh,:bw]
        pu=(i+.5-PAD)/scale
        pv=(j+.5-PAD)/scale
        if rotate:pu,pv=pv,pu
        atlas[y0:y0+bh,x0:x0+bw]=sample(texture,(pu+lo[0])*w-.5,(pv+lo[1])*h-.5)
    # Every source polygon is a triangle. Write per corner so the new face/body
    # boundary can be a UV seam without separating the physical surface.
    layer=body.data.uv_layers.active
    for t,coords in zip(body.data.loop_triangles,result):
        for loop,coord in zip(t.loops,coords):
            layer.data[loop].uv=coord
    print("ATLAS",len(charts),"facial charts",sum(len(g[0]) for g in charts),"triangles",
          round(scale/SIZE,3),"x original 1024-pixel atlas density",flush=True)
    return atlas
