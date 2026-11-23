"""Shared coordinates, texture sampling and source inspection for the expression build."""
from pathlib import Path
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / "hand-gestures-astra/round2/base_body.glb"
HAIR = ROOT.parent / "hair-fit-astra/round2/hair_bob_v2.glb"
WORK = ROOT / ".work"
NAMES = ("neutral", "happy", "surprised", "sad")

def open_body(path=BASE):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.view_layer.update()
    return next(o for o in bpy.context.scene.objects if o.type == "MESH")

def color_image(body):
    return next(n.image for n in body.data.materials[0].node_tree.nodes if n.type == "TEX_IMAGE")

def pixels(im):
    a = np.empty(im.size[0]*im.size[1]*4, np.float32)
    im.pixels.foreach_get(a)
    return a.reshape(im.size[1], im.size[0], 4)

def save_rgb(path, rgb):
    # The input and output use byte-backed sRGB Blender images. bpy exposes
    # normalized encoded bytes for these pixel buffers.
    h,w = rgb.shape[:2]
    im = bpy.data.images.new(path.stem, width=w, height=h, alpha=False)
    rgba = np.ones((h,w,4),np.float32)
    rgba[:,:,:3] = np.clip(rgb,0,1)
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = str(path)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)

def sample(image, x, y):
    h,w = image.shape[:2]
    x,y = np.clip(x,0,w-1),np.clip(y,0,h-1)
    i,j = np.floor(x).astype(int),np.floor(y).astype(int)
    a,b = (x-i)[...,None],(y-j)[...,None]
    return (1-b)*((1-a)*image[j,i]+a*image[j,np.minimum(i+1,w-1)]) + b*((1-a)*image[np.minimum(j+1,h-1),i]+a*image[np.minimum(j+1,h-1),np.minimum(i+1,w-1)])

def triangles(body):
    m = body.data
    m.calc_loop_triangles()
    xyz = np.array([tuple(body.matrix_world @ v.co) for v in m.vertices])
    idx = np.array([t.vertices[:] for t in m.loop_triangles])
    uv = np.array([d.uv[:] for d in m.uv_layers.active.data])
    loops = np.array([t.loops[:] for t in m.loop_triangles])
    return xyz, idx, uv[loops]

def raster(tri, width, height, pad=0):
    lo = np.maximum(0,np.ceil(tri.min(axis=0)-pad).astype(int))
    hi = np.minimum([width-1,height-1],np.floor(tri.max(axis=0)+pad).astype(int))
    if np.any(lo>hi):
        return None
    dx1,dy1=tri[1]-tri[0]
    dx2,dy2=tri[2]-tri[0]
    det=dx1*dy2-dx2*dy1
    if abs(det)<1e-8:
        return None
    j,i=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
    x,y=i-tri[0,0],j-tri[0,1]
    b=(x*dy2-y*dx2)/det
    c=(dx1*y-dy1*x)/det
    a=1-b-c
    if pad:
        # Perpendicular distance to the three edge lines in pixel units.
        alts=np.abs(det)/np.maximum(np.linalg.norm(tri[[2,0,1]]-tri[[1,2,0]],axis=1),1e-8)
        mask=(a*alts[0]>=-pad)&(b*alts[1]>=-pad)&(c*alts[2]>=-pad)
    else:
        mask=(a>=-1e-8)&(b>=-1e-8)&(c>=-1e-8)
    return j[mask],i[mask],np.stack([a[mask],b[mask],c[mask]],axis=1)

# A metric, orthographic front canvas. Pixel (0,0) is bottom left.
LEFT, BOTTOM, SCALE, W, H = -.215, .595, 2000, 860, 830

def project(body):
    xyz,idx,uv=triangles(body)
    texture=pixels(color_image(body))[:,:,:3]
    h,w=texture.shape[:2]
    face=np.zeros((H,W,3),np.float32)
    depth=np.full((H,W),np.inf)
    labels=np.full((H,W),-1,int)
    for n,vs in enumerate(xyz[idx]):
        if vs[:,2].max()<BOTTOM: continue
        r=raster((vs[:,[0,2]]-[LEFT,BOTTOM])*SCALE-.5,W,H)
        if r is None: continue
        j,i,b=r
        d=b@vs[:,1]
        sel=d<depth[j,i]
        j,i,b,d=j[sel],i[sel],b[sel],d[sel]
        tex=(b@uv[n])*[w,h]-.5
        face[j,i]=sample(texture,tex[:,0],tex[:,1])
        depth[j,i]=d
        labels[j,i]=n
    return face,depth,labels
