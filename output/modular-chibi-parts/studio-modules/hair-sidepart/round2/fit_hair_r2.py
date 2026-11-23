"""Rebuild and verify the boy's side-part in Blender. See NOTES.md for stages."""
import hashlib
import json
import math
from pathlib import Path
import runpy
import subprocess
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE.parent))
import fit_hair as v1

bob = v1.bob
ROOT = v1.ROOT
ORIGINAL = HERE.parent / "hair_sidepart_v1.glb"
GLB = HERE / "hair_sidepart_v2.glb"
VIEWS = [(0,-1,0), (.6,-1,.08), (-.6,-1,.08), (1,0,.03), (0,1,.06), (-1,0,.03)]
LABELS = ["front", "three_quarter_left", "three_quarter_right", "left", "back", "right"]
ANGLES = np.arange(360) * math.pi / 180
TMP = HERE / ".scratch"
TMP.mkdir(exist_ok=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_scene(path):
    bpy.ops.wm.open_mainfile(filepath=str(v1.MASTER))
    bpy.ops.import_scene.gltf(filepath=str(path))
    hair = bpy.context.scene.objects["Hair_Sidepart"]
    return bpy.context.scene, hair


def image_array(path):
    im = bpy.data.images.load(str(path))
    im.colorspace_settings.name = "Non-Color"
    w,h = im.size
    pixels = np.empty(w*h*4, np.float32)
    im.pixels.foreach_get(pixels)
    bpy.data.images.remove(im)
    return pixels.reshape(h,w,4)


def save_pixels(path, array):
    h,w,_ = array.shape
    im = bpy.data.images.new(path.stem, w, h, alpha=True)
    im.colorspace_settings.name = "Non-Color"
    im.pixels.foreach_set(np.ascontiguousarray(array, np.float32).ravel())
    im.filepath_raw = str(path)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)


def set_camera(sc):
    bob.cpu_studio(sc)
    data = bpy.data.cameras.new("Fit camera")
    cam = bpy.data.objects.new("Fit camera", data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    data.type, data.ortho_scale = "ORTHO", .55
    sc.render.resolution_x = sc.render.resolution_y = 520
    return cam


def aim(cam, direction):
    target = Vector((0,0,.807))
    cam.location = target + Vector(direction).normalized()*2
    cam.rotation_euler = (target-cam.location).to_track_quat("-Z","Y").to_euler()
    bpy.context.view_layer.update()


def visible_mask(cam, body, hair):
    # Pixel-centre orthographic rays. The nearest body intersection clips the
    # ray so hair occluded by the ears, neck or head does not enter the mask.
    rot = cam.rotation_euler.to_quaternion()
    dx,dy = [rot @ vec * (.55/520) for vec in [Vector((1,0,0)),Vector((0,1,0))]]
    direction = rot @ Vector((0,0,-1))
    start = cam.location - 259.5*(dx+dy)
    result = np.zeros((520,520),bool)
    for row in range(520):
        base = start + row*dy
        for col in range(520):
            p = base + col*dx
            _,_,ix,dh = hair.ray_cast(p,direction,3)
            if ix is not None:
                result[row,col] = body.ray_cast(p,direction,dh)[0] is None
    return result


def views(stage):
    original = stage == "baseline"
    path = ORIGINAL if original else GLB
    sc,hair = load_scene(path)
    cam = set_camera(sc)
    body_tree = bob.tree_for(sc.objects["Base_Body"])
    hair_tree = bob.tree_for(hair)
    sheet = image_array(HERE.parent/"fit_views.png") if original else np.empty((1040,1560,4),"f")
    stats = {}
    for i,direction in enumerate(VIEWS):
        aim(cam,direction)
        y,x = (1-i//3)*520,(i%3)*520
        if not original:
            sc.render.filepath = str(TMP/"tile.png")
            bpy.ops.render.render(write_still=True)
            sheet[y:y+520,x:x+520] = image_array(sc.render.filepath)
        mask = visible_mask(cam,body_tree,hair_tree)
        rgb = sheet[y:y+520,x:x+520,:3][mask]
        luma = rgb @ np.array([.2126,.7152,.0722])
        # Also record physically linear luminance to disambiguate the threshold.
        linear = np.where(rgb <= .04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
        stats[LABELS[i]] = dict(hair_pixels=int(mask.sum()), dark=int((luma<.12).sum()),
                                linear_dark=int((linear @ [.2126,.7152,.0722]<.12).sum()))
    if not original:
        save_pixels(HERE/"fit_views_v2.png",sheet)
    info = dict(asset_sha256=digest(path), views=stats)
    (HERE/("pixels_v1.json" if original else "pixels_v2.json")).write_text(json.dumps(info,indent=2)+"\n")
    print(info,flush=True)


def closeups():
    sc,_ = load_scene(GLB)
    cam = set_camera(sc)
    sc.render.resolution_x = sc.render.resolution_y = 1040
    sc.render.use_border = sc.render.use_crop_to_border = True
    for i,box in [(3,(60,136,438,362)),(4,(61,308,459,389)),(5,(71,111,476,364))]:
        aim(cam,VIEWS[i])
        x0,y0,x1,y1 = box  # 520-pixel reference frame, top left origin
        sc.render.border_min_x,sc.render.border_max_x = x0/520,x1/520
        sc.render.border_min_y,sc.render.border_max_y = 1-y1/520,1-y0/520
        sc.render.filepath = str(HERE/f"closeup_{LABELS[i]}.png")
        bpy.ops.render.render(write_still=True)


def polar(p):
    x,y,z = p-ROOT
    return math.atan2(x,-y), math.atan2(z,math.hypot(x,y))


def direction(a,e):
    return Vector((math.sin(a)*math.cos(e), -math.cos(a)*math.cos(e), math.sin(e)))


def read_hem(tree):
    heights = []
    for a in ANGLES:
        for degree in np.arange(-50.,45.,.35):
            ray = direction(a,math.radians(degree))
            if tree.ray_cast(ROOT+ray*.55,-ray,.55)[0] is not None:
                heights.append(math.radians(degree-.175))
                break
    assert len(heights)==360
    # A small circular filter removes the old polygon corners but leaves the
    # two narrow points in front of the ears and the offset brow opening.
    return np.average([np.roll(heights,i) for i in range(-4,5)],axis=0,
                      weights=[1,3,6,10,13,10,6,3,1])


def at_angle(values,a):
    return np.interp(a%(2*math.pi),ANGLES,values,period=2*math.pi)


def active(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj


def ramp(lo,hi,x):
    t=np.clip((x-lo)/(hi-lo),0,1)
    return t*t*(3-2*t)


def blur(a,sx,sy):
    result=a.astype("f",copy=True)
    for axis,sigma in [(1,sx),(0,sy)]:
        if sigma<=0: continue
        radius=int(math.ceil(3*sigma))
        taps=np.arange(-radius,radius+1)
        weights=np.exp(-.5*(taps/sigma)**2)
        weights/=weights.sum()
        if axis==1:
            result=sum(w*np.roll(result,int(k),axis=1) for k,w in zip(taps,weights)).astype("f")
        else:
            pad=np.pad(result,[(radius,radius),(0,0)]+[(0,0)]*(a.ndim-2),mode="edge")
            result=sum(w*pad[k:k+len(result)] for k,w in enumerate(weights)).astype("f")
    return result


def resample(array,x,y):
    x=np.asarray(x)
    y=np.clip(y,0,array.shape[0]-1)
    i=np.floor(x).astype(int)
    j=np.floor(y).astype(int)
    fx,fy=np.broadcast_arrays(x-i,y-j)
    if array.ndim==3:
        fx,fy=fx[...,None],fy[...,None]
    i1=(i+1)%array.shape[1]
    i=i%array.shape[1]
    j1=np.minimum(j+1,array.shape[0]-1)
    return (array[j,i]*(1-fx)+array[j,i1]*fx)*(1-fy)+(array[j1,i]*(1-fx)+array[j1,i1]*fx)*fy


def source_samples(obj,skin,hem,im):
    # A ray from outside the old cut finds the FIRST surface. This preserves
    # overlapping locks without projecting across to their dark back walls.
    n,m=768,321
    az=(np.arange(n)/n*2-1)*math.pi
    low=at_angle(hem,az)-np.radians(.8)*np.maximum(0,-np.cos(az))**3
    aa=np.abs(np.degrees(az))
    nape=np.radians(-20.4-8.3*np.sin(np.radians(np.clip(aa-100,0,80)*90/80)))
    low+=(nape-low)*ramp(107,146,aa)
    t=np.linspace(0,1,m)[:,None]
    el=low+(math.pi/2-low)*t
    directions=np.stack(np.broadcast_arrays(np.sin(az)*np.cos(el),-np.cos(az)*np.cos(el),np.sin(el)),axis=-1)
    tree=bob.tree_for(obj)
    radius=np.empty((m,n),"f")
    skull=np.empty_like(radius)
    src=np.zeros((m,n),int)
    hit=np.empty((m,n,3),"f")
    for r in range(m):
        for c in range(n):
            d=Vector(directions[r,c])
            start=ROOT+.56*d
            p,ns,_,ds=skin.ray_cast(start,-d,.56)
            skull[r,c]=.56-ds+.0074/max(.38,ns.dot(d))
            q,_,face,dist=tree.ray_cast(start,-d,.56)
            if q is None:
                q,_,face,_=tree.find_nearest(ROOT+d*skull[r,c])
                radius[r,c]=skull[r,c]+.0015
            else:
                radius[r,c]=.56-dist
            src[r,c],hit[r,c]=face,q
    me=obj.data
    tris=np.array([f.vertices[:] for f in me.polygons])
    uv=np.array([l.uv[:] for l in me.uv_layers.active.data])
    tex=uv[np.array([f.loop_indices[:] for f in me.polygons])]
    xyz=np.array([v.co[:] for v in me.vertices])[tris]
    a,b,c=np.moveaxis(xyz[src],2,0)
    u,v,p=b-a,c-a,hit-a
    dot=lambda x,y:np.sum(x*y,axis=-1)
    uu,vv,uv=dot(u,u),dot(v,v),dot(u,v)
    den=np.maximum(1e-20,uu*vv-uv*uv)
    s=(vv*dot(u,p)-uv*dot(v,p))/den
    q=(uu*dot(v,p)-uv*dot(u,p))/den
    coord=np.einsum("...ij,...i->...j",tex[src],np.stack((1-s-q,s,q),axis=-1))
    im.colorspace_settings.name="Non-Color"
    color=np.empty(len(im.pixels),"f")
    im.pixels.foreach_get(color)
    iw,ih=im.size
    sampled=resample(color.reshape(ih,iw,4)[:,:,:3],coord[:,:,0]*iw-.5,coord[:,:,1]*ih-.5)
    vertex_normals=np.array([v.normal[:] for v in me.vertices])
    bary=np.stack((1-s-q,s,q),axis=-1)
    surface_n=unit(np.einsum("...ij,...i->...j",vertex_normals[tris[src]],bary))
    return az,low,el,radius,skull,sampled,surface_n


def unit(v):
    return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-12)


def bake_relief(mesh,mat,shader,field,left,right,bottom,top):
    # Encode the dense sculpt normal relative to the final triangle tangent
    # frame. A low-poly vertex normal alone cannot describe a swept furrow.
    mesh.calc_loop_triangles()
    mesh.calc_tangents()
    uv=mesh.uv_layers.active
    table=np.array([l.uv[:] for l in uv.data])*1024-.5
    normals=np.array([v.vector[:] for v in mesh.corner_normals])
    tangents=np.array([l.tangent[:] for l in mesh.loops])
    signs=np.array([l.bitangent_sign for l in mesh.loops])
    atlas=np.empty((1024,1024,4),"f")
    atlas[:]=(.5,.5,1,1)
    for f in mesh.loop_triangles:
        ids=list(f.loops)
        tri=table[ids]
        if tri[:,1].max()<bottom-1: continue
        x0,y0=np.maximum(0,np.ceil(tri.min(axis=0)).astype(int))
        x1,y1=np.minimum(1023,np.floor(tri.max(axis=0)).astype(int))
        yy,xx=np.mgrid[y0:y1+1,x0:x1+1]
        a,b,c=tri
        u,v=b-a,c-a
        det=u[0]*v[1]-u[1]*v[0]
        if abs(det)<1.e-9: continue
        t=((xx-a[0])*v[1]-(yy-a[1])*v[0])/det
        s=(u[0]*(yy-a[1])-u[1]*(xx-a[0]))/det
        w=np.stack((1-t-s,t,s),axis=-1)
        keep=w.min(axis=-1)>=-1e-6
        w=w[keep]
        xx,yy=xx[keep],yy[keep]
        nn=unit(w@normals[ids])
        tt=w@tangents[ids]
        tt=unit(tt-nn*np.sum(nn*tt,axis=1,keepdims=True))
        bb=np.cross(nn,tt)*np.sign(w@signs[ids])[:,None]
        ny,nx=field.shape[:2]
        target=unit(resample(field,(xx+.5-left)*nx/(right-left),(yy+.5-bottom)*(ny-1)/(top-bottom)))
        tangent=unit(np.stack([np.sum(target*axis,axis=1) for axis in (tt,bb,nn)],axis=1))
        tangent[:,2]=np.maximum(.38,tangent[:,2])
        atlas[yy,xx,:3]=.5+.5*unit(tangent)
    # The chart is periodic and the lining uses flat normals. Extend the
    # edge texels for mip levels and avoid introducing a second longitude.
    atlas[:, :left]=atlas[:,right-left:right]
    atlas[:, right:]=atlas[:,left:2*left]
    atlas[bottom-16:bottom]=atlas[bottom:bottom+1]
    atlas[top:]=atlas[top-1:top]
    tmp=TMP/"QuiffNormals.png"
    save_pixels(tmp,atlas)
    image=bpy.data.images.load(str(tmp))
    image.name="Quiff sculpt normals"
    image.colorspace_settings.name="Non-Color"
    image.pack()
    image.filepath_raw="//QuiffNormals.png"
    tex=mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image=image
    tex.location=(-600,-130)
    normal=mat.node_tree.nodes.new("ShaderNodeNormalMap")
    normal.uv_map=uv.name
    normal.inputs["Strength"].default_value=.82
    normal.location=(-260,-120)
    mat.node_tree.links.new(tex.outputs["Color"],normal.inputs["Color"])
    mat.node_tree.links.new(normal.outputs["Normal"],shader.inputs["Normal"])


def sculpt(obj,skin,hem,im):
    az,low,el,radius,skull,color,source_n=source_samples(obj,skin,hem,im)
    m,n=radius.shape
    height=np.degrees(el)
    above=np.degrees(el-low)
    side=ramp(44,85,np.abs(np.degrees(az)))
    rear=ramp(110,150,np.abs(np.degrees(az)))
    temple=side*(1-ramp(6,28,height))
    # The taper underneath the right curl was a narrow fold crossing the
    # otherwise uninterrupted temple. Reconstruct its local envelope from
    # neighbouring samples, using a smooth, finite support around the fold.
    aa=np.degrees(az)
    patch=1-ramp(.63,1.6,np.sqrt(((aa+62.5)/8.0)**2+((height-16)/8.5)**2))
    # Smooth the radial envelope in physical angle. Under-cut valleys meet
    # their neighbours on a continuous sheet; no slit or floating card is
    # introduced. Retain the higher-frequency crown and front sweep.
    fine=blur(radius,1.4,1.7)
    mid=blur(radius,3.6,3.8)
    broad=blur(radius,11,9)
    outer=fine+(mid-fine)*temple
    outer+=np.maximum(0,broad-outer+.001)*temple*.63
    outer+=(blur(outer,10,11)-outer)*patch
    smooth_skull=blur(skull,3,2)
    # A cubic cross section gives the nape one continuous tangent from
    # its lower contour to the rounded occiput.
    rim_height=6+11*side+6*rear
    column=np.arange(n)
    row=rim_height/(90-np.degrees(low))*(m-1)
    r0=smooth_skull[0]+.002
    r1=resample(outer,column,row)
    slope=(resample(outer,column,row+2)-resample(outer,column,row-2))*row/4
    progress=np.clip(above/rim_height,0,1)
    delta=r1-r0
    slope=np.clip(slope,-.3*np.abs(delta),1.8*np.abs(delta))
    t2=progress**2
    t3=t2*progress
    cubic=r0+(3*t2-2*t3)*delta+(t3-2*t2+progress)*1.25*delta+(t3-t2)*slope
    outer=np.where(above<rim_height,cubic,outer)
    outer=np.maximum(outer,skull+.0026)
    # A cylinder has a coordinate singularity at the pole. Fade differences
    # over the last few millimetres into a single continuous vertex.
    pole=ramp(84,90,height)
    outer=(1-pole)*outer+pole*np.mean(outer,axis=1,keepdims=True)
    # Rebuild broad daylight albedo from the visible side. Soften tiny dark
    # samples more strongly at the temples, retaining the part and long sweep.
    corrected=blur(color,1.15,1.4)
    middle=blur(color,3.8,4.3)
    corrected+=(middle-corrected)*temple[:,:,None]
    restored=corrected*np.array([.79,.78,.76])+np.array([.114,.059,.040])
    relief=np.clip((outer-blur(outer,10,10))/.009,-1,1)
    restored+=relief[:,:,None]*np.array([.037,.024,.018])
    cap=np.array([.318,.146,.104])+ramp(0,38,above)[:,:,None]*np.array([.090,.064,.052])
    comb=np.cos(az*8+el*2+.6*np.sin(az*3+el))
    cap+=comb[:,:,None]*np.array([.010,.006,.004])
    blend=np.maximum.reduce(np.broadcast_arrays(
        (1-ramp(1,10,above))*(1-side),side*(1-ramp(3,19,height)),rear*(1-ramp(31,56,height))))
    paint=restored*(1-blend[:,:,None])+cap*blend[:,:,None]
    paint+=(blur(paint,12,12)-paint)*patch[:,:,None]
    paint*=np.array([.94,.91,.91])
    paint+=(np.mean(paint,axis=1,keepdims=True)-paint)*pole[:,:,None]

    # Periodic UVs put the single longitudinal join on the back. Texels
    # beyond the seam and the top/bottom of the chart are extended 16 px
    # into padding. The fitted lining has its own solid chestnut swatch.
    left,right,bottom,top=16,1008,80,1008
    iy,ix=np.mgrid[:1024,:1024]
    atlas=np.ones((1024,1024,4),"f")
    atlas[:,:,:3]=np.clip(resample(paint,(ix+.5-left)*n/(right-left),(iy+.5-bottom)*(m-1)/(top-bottom)),0,1)
    atlas[:bottom-16,:,:3]=(.322,.151,.106)
    png=TMP/"Chestnut.png"
    save_pixels(png,atlas)
    image=bpy.data.images.load(str(png))
    image.name="Chestnut side-part"
    image.pack()
    image.filepath_raw="//Chestnut.png"
    mat=bpy.data.materials.new("Combed chestnut")
    mat.use_nodes=True
    shader=mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Metallic"].default_value=.30
    shader.inputs["Roughness"].default_value=.48
    shader.inputs["Specular IOR Level"].default_value=.30
    tex=mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image=image
    tex.location=(-400,240)
    mat.node_tree.links.new(tex.outputs["Color"],shader.inputs["Base Color"])
    mat.diffuse_color=(.14,.046,.026,1)
    verts=[]
    faces=[]
    zones=[]
    def vertex(p):
        verts.append(tuple(p))
        return len(verts)-1
    def face(c,zone):
        faces.append(c)
        zones.append(zone)
    def link(a,b,zone,angular=False):
        # The zipper supports different circumferential sampling densities.
        if angular:
            def phases(row):
                angles=np.unwrap([polar(Vector(verts[v]))[0] for v in row])
                angles-=math.tau*round((angles[0]+math.pi)/math.tau)
                return np.append(angles,angles[0]+math.tau)
            aa,bb=phases(a),phases(b)
        else:
            aa=np.arange(len(a)+1)/len(a)
            bb=np.arange(len(b)+1)/len(b)
        i=j=0
        while i<len(a) or j<len(b):
            if j==len(b) or (i<len(a) and aa[i+1]<=bb[j+1]):
                face((a[i%len(a)],a[(i+1)%len(a)],b[j%len(b)]),zone)
                i+=1
            else:
                face((a[i%len(a)],b[(j+1)%len(b)],b[j%len(b)]),zone)
                j+=1
    count=240
    def make_ring(t,count,inside=False):
        a=(np.arange(count)/count*2-1)*math.pi
        bottom_e=np.interp(a,az,low,period=math.tau)
        e=bottom_e+(math.pi/2-bottom_e)*t
        if inside:
            return [vertex(v1.get_surface(skin,direction(aa,ee),.0045 if t<.04 else .0060)) for aa,ee in zip(a,e)]
        rr=resample(outer,np.arange(count)/count*n,np.full(count,t*(m-1)))
        return [vertex(ROOT+direction(aa,ee)*r) for aa,ee,r in zip(a,e,rr)]
    # Reduce the upper quiff separately; its simplifier cannot remove the
    # evenly spaced courses at the nape and the crease in front of the ear.
    t_start=.10
    prev=make_ring(t_start,count)
    for t in np.linspace(t_start,1,108)[1:-1]:
        ring_count=count if t<.75 else (120 if t<.94 else 60)
        ring=make_ring(t,ring_count)
        link(prev,ring,0)
        prev=ring
    pole_v=vertex(ROOT+Vector((0,0,float(outer[-1,0]))))
    for i in range(len(prev)):
        face((prev[i],prev[(i+1)%len(prev)],pole_v),0)
    high=bpy.data.meshes.new("Sculpted crown")
    high.from_pydata(verts,[],faces)
    high.update()
    obj.data=high
    # Fixed course counts reserve a true bevel. The remaining allowance
    # goes to the upper sculpt; the iterative allowance includes its border.
    budget=2000
    for attempt in range(8):
        obj.data=high.copy()
        v1.decimate(obj,budget)
        reduced=obj.data
        bm=bmesh.new()
        bm.from_mesh(reduced)
        border,=v1.rim_loops(bm)
        # Bound the arc length of the cut ring. A long chord on the concave
        # brow would pass through the lining even if both endpoints clear it.
        for edge in [e for e in bm.edges if e.is_boundary]:
            x,y=edge.verts
            ax,ay=polar(x.co)[0],polar(y.co)[0]
            span=(ay-ax+math.pi)%math.tau-math.pi
            pieces=int(math.ceil(abs(span)/math.radians(5)))
            tail=x
            for piece in range(1,pieces):
                e=bm.edges.get((tail,y))
                _,insert=bmesh.utils.edge_split(e,tail,1/(pieces-piece+1))
                tail=insert
        border,=v1.rim_loops(bm)
        for v in border:
            a=polar(v.co)[0]
            lo=np.interp(a,az,low,period=math.tau)
            e=lo+(math.pi/2-lo)*t_start
            rr=resample(outer,(a/math.tau+.5)*n,t_start*(m-1))
            v.co=ROOT+direction(a,e)*rr
        bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
        bm.to_mesh(reduced)
        bm.verts.index_update()
        boundary=sorted([v.index for v in border],key=lambda i:polar(reduced.vertices[i].co)[0])
        bm.free()
        # The cut is a circle in parameter space; preserve actual edge order.
        edges={tuple(sorted(e.vertices[:])) for e in reduced.edges}
        assert all(tuple(sorted((j,k))) in edges for j,k in zip(boundary,boundary[1:]+boundary[:1]))
        verts=[v.co[:] for v in reduced.vertices]
        faces=[f.vertices[:] for f in reduced.polygons]
        zones=[0]*len(faces)
        prev=boundary
        for t,k in ((.052,72),(.011,112),(0,112)):
            row=make_ring(t,k)
            link(row,prev,0,angular=True)
            prev=row
        for t,k in ((.012,80),(.13,48),(.265,42),(.425,36),(.595,32),(.76,24),(.90,16)):
            row=make_ring(t,k,True)
            link(row,prev,1)
            prev=row
        pole_v=vertex(v1.get_surface(skin,Vector((0,0,1)),.006))
        for i in range(len(prev)):
            face((prev[(i+1)%len(prev)],prev[i],pole_v),1)
        difference=2996-len(faces)
        if 0<=difference<=12: break
        budget+=difference if difference>=0 else difference-2
    assert len(faces)<=3000
    mesh=bpy.data.meshes.new("Sidepart shell")
    mesh.from_pydata(verts,[],faces)
    mesh.materials.append(mat)
    mesh.materials.append(mat)
    for f,zone in zip(mesh.polygons,zones):
        f.material_index=zone
        f.use_smooth=True
    mesh.update()
    obj.data=mesh
    bm=bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    # Check the actual airway-facing side of the lining for local shortages;
    # keep a lower fitting clearance there so the lining stays under the brow.
    for v in mesh.vertices:
        for _ in range(4):
            q,nn,_,_=skin.find_nearest(v.co)
            signed=(v.co-q).dot(nn)
            if signed>=.0039: break
            v.co+=nn*(.0041-signed)
    mesh.update()
    bob.support_faces(obj,skin)
    uv=mesh.uv_layers.new(name="Combed chestnut")
    for f in mesh.polygons:
        idx=list(f.loop_indices)
        angles=[]
        vcoords=[]
        pole_index=None
        for k,vi in enumerate(f.vertices):
            p=mesh.vertices[vi].co
            a,e=polar(p)
            if math.hypot(p.x-ROOT.x,p.y-ROOT.y)<.0001: pole_index=k
            e0=np.interp(a,az,low,period=math.tau)
            u=(a/math.tau+.5)%1
            v=np.clip((e-e0)/(math.pi/2-e0),0,1)
            angles.append(u)
            vcoords.append(v)
        if max(angles)-min(angles)>.5:
            angles=[x+1 if x<.5 else x for x in angles]
        if pole_index is not None:
            angles[pole_index]=np.mean([x for k,x in enumerate(angles) if k!=pole_index])
        for k,l in enumerate(idx):
            if not f.material_index:
                uv.data[l].uv=((left+(right-left)*angles[k])/1024,(bottom+(top-bottom)*vcoords[k])/1024)
            else:
                p=mesh.vertices[mesh.loops[l].vertex_index].co
                uv.data[l].uv=(.45+p.x*.25,.027+p.y*.06)
        f.material_index=0
        f.use_smooth=True
    mesh.materials.pop(index=1)
    # Analytic exterior normal field. Position and shading use the same
    # periodic sculpt, including both sides of the rear UV seam.
    directions=np.stack(np.broadcast_arrays(np.sin(az)*np.cos(el),-np.cos(az)*np.cos(el),np.sin(el)),axis=-1)
    points=directions*outer[:,:,None]
    du=np.roll(points,-1,axis=1)-np.roll(points,1,axis=1)
    dv=np.gradient(points,axis=0)
    normal_field=unit(np.cross(du,dv))
    normal_field[-1,:,:]=(0,0,1)
    normal_field=unit(blur(normal_field,1.15,1.2))
    # Smooth source vertex normals retain how the original swept bands
    # catch light. Differentiating a low-poly source radius alone repeats
    # its planar triangles in the baked highlights.
    source_n=unit(blur(source_n,2.4,2.6))
    alignment=np.sum(source_n*directions,axis=-1)
    swept=ramp(-.30,.34,alignment)*ramp(4,14,above)*(1-.72*temple)
    swept*=1-patch
    normal_field=unit(normal_field*(1-.88*swept[:,:,None])+source_n*(.88*swept[:,:,None]))
    normal_field=unit(normal_field+(unit(blur(normal_field,9,10))-normal_field)*patch[:,:,None])
    # The occipital cap is an uninterrupted dome. Its normal follows a
    # fitted ellipsoid. Blend into the actual combed ridges near the crown,
    # and into the rolled lower edge at the neck.
    cap_normal=unit((points-np.array([0,.010,.004]))/np.array([.216,.221,.240])**2)
    dome=ramp(102,139,np.abs(aa))*(1-ramp(50,71,height))*ramp(1,13,above)
    normal_field=unit(normal_field*(1-dome[:,:,None])+cap_normal*dome[:,:,None])
    normal_field[-1,:,:]=[0,0,1]
    outer_ids={i for f,zone in zip(mesh.polygons,zones) if zone==0 for i in f.vertices}
    normals=[]
    for v in mesh.vertices:
        if v.index in outer_ids:
            a,e=polar(v.co)
            bottom_e=np.interp(a,az,low,period=math.tau)
            t=(e-bottom_e)/(math.pi/2-bottom_e)
            normal=resample(normal_field,(a/math.tau+.5)*n,t*(m-1))
            normals.append(tuple(unit(normal)))
        else:
            normals.append(v.normal[:])
    mesh.normals_split_custom_set_from_vertices(normals)
    mesh.update()
    bake_relief(mesh,mat,shader,normal_field,left,right,bottom,top)


def build():
    bpy.ops.wm.open_mainfile(filepath=str(ORIGINAL.with_suffix(".blend")))
    obj=bpy.data.objects["Hair_Sidepart"]
    arm=obj.parent
    obj.modifiers.clear()
    obj.vertex_groups.clear()
    for i in range(len(obj.data.attributes)-1,-1,-1):
        attr=obj.data.attributes[i]
        if attr.name=="sharp_edge":
            obj.data.attributes.remove(attr)
    im=next(n.image for n in obj.active_material.node_tree.nodes if n.type=="TEX_IMAGE" and "basecolor" in n.image.name)
    skin=bob.tree_for(bpy.data.objects["Base_Body"],head_only=True)
    hem=read_hem(bob.tree_for(obj))
    sculpt(obj,skin,hem,im)
    h,n=[obj.vertex_groups.new(name=name) for name in (v1.HEAD,v1.NECK)]
    for vert in obj.data.vertices:
        x,y,z=vert.co
        w=.033*v1.smooth(.002,.09,y)*(1-v1.smooth(.695,.795,z))
        w=w if w>=.0001 else 0
        h.add([vert.index],1-w,"REPLACE")
        if w:
            n.add([vert.index],w,"REPLACE")
    obj.modifiers.new("Master skeleton","ARMATURE").object=arm
    obj.data.name="Combed quiff with continuous rolled hairline"
    active(obj)
    arm.hide_set(False)
    arm.select_set(True)
    obj.parent=None
    bpy.ops.export_scene.gltf(filepath=str(GLB),export_format="GLB",use_selection=True,
                              export_tangents=True,export_animations=False,export_def_bones=False,export_all_influences=False)
    obj.parent=arm
    arm.hide_set(True)
    bpy.data.orphans_purge(do_recursive=True)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(GLB.with_suffix(".blend")),compress=True)
    print("Export",GLB.stat().st_size,digest(GLB),flush=True)


@bpy.app.handlers.persistent
def checker_stills_cpu(scene,*unused):
    if scene.camera and scene.camera.name=="c" and scene.render.engine=="BLENDER_WORKBENCH":
        bob.cpu_studio(scene)


def checker(kind):
    directory=HERE/f"check_{kind}"
    directory.mkdir(exist_ok=True)
    src=HERE/("motion_check.py" if kind=="vertex" else "motion_check_tri.py")
    bpy.app.handlers.frame_change_pre.append(checker_stills_cpu)
    old=sys.argv
    try:
        sys.argv=[str(src),"--",str(v1.MASTER),str(v1.MOTION),str(GLB),str(directory)]
        runpy.run_path(str(src),run_name="__main__")
    finally:
        sys.argv=old
        bpy.app.handlers.frame_change_pre.remove(checker_stills_cpu)
    results=json.loads((directory/"motion_check.json").read_text())
    assert set(results)==set("rest walk run wave jump idle nod dance".split())
    assert all(count==0 and clearance>=.0005 for count,clearance in results.values()),results
    (directory/"asset.sha256").write_text(digest(GLB)+"  "+GLB.name+"\n")


def audit():
    doc,buf=bob.read_glb(GLB)
    ref,refbuf=bob.read_glb(ORIGINAL)
    skin,=doc["skins"]
    def joints(g):
        return [(g["nodes"][j]["name"],[g["nodes"][k]["name"] for k in g["nodes"][j].get("children",[])]) for j in g["skins"][0]["joints"]]
    assert joints(doc)==joints(ref) and len(skin["joints"])==65
    assert np.allclose(bob.accessor(doc,buf,skin["inverseBindMatrices"]),
                       bob.accessor(ref,refbuf,ref["skins"][0]["inverseBindMatrices"]),atol=1e-6,rtol=0)
    mesh,=doc["meshes"]
    prim,=mesh["primitives"]
    triangles=doc["accessors"][prim["indices"]]["count"]//3
    assert triangles<=3000
    attrs=prim["attributes"]
    assert "JOINTS_1" not in attrs and "WEIGHTS_1" not in attrs
    ids=bob.accessor(doc,buf,attrs["JOINTS_0"])
    weights=bob.accessor(doc,buf,attrs["WEIGHTS_0"])
    assert np.allclose(weights.sum(axis=1),1,atol=1e-6)
    names=[name for name,_ in joints(doc)]
    used={names[j] for j in np.unique(ids[weights>0])}
    max_infl=int((weights>0).sum(1).max())
    assert used=={v1.HEAD,v1.NECK} and max_infl<=4
    neck=np.where(ids==names.index(v1.NECK),weights,0).sum(1)
    node,=[n for n in doc["nodes"] if "mesh" in n]
    assert node["skin"]==0 and node["name"]=="Hair_Sidepart"
    sc,obj=load_scene(GLB)
    bm=bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1.e-7)
    bm.normal_update()
    components=len(bob.connected_faces(bm))
    open_edges=sum(not e.is_manifold for e in bm.edges)
    bad_normals=sum(not e.is_contiguous for e in bm.edges)
    assert components==1 and open_edges==bad_normals==0 and bm.calc_volume(signed=True)>0
    bm.faces.ensure_lookup_table()
    tree=BVHTree.FromBMesh(bm)
    self_cross=sum(i<j and set(bm.faces[i].verts).isdisjoint(bm.faces[j].verts)
                   for i,j in tree.overlap(tree))
    assert self_cross==0,self_cross
    # Blender's GLB seam duplicates should carry the same smooth shading
    # normal, even though each side legitimately has a different UV.
    attrs_norm=bob.accessor(doc,buf,attrs["NORMAL"])
    pos=bob.accessor(doc,buf,attrs["POSITION"])
    uniques={}
    normal_error=0.
    for p,n in zip(pos,attrs_norm):
        first=uniques.setdefault(tuple(p),n)
        normal_error=max(normal_error,float(np.linalg.norm(n-first)))
    images=[n.image for n in obj.active_material.node_tree.nodes if n.type=="TEX_IMAGE"]
    assert all(im.packed_file and max(im.size)<=1024 for im in images)
    checks=dict(asset_sha256=digest(GLB),bytes=GLB.stat().st_size,triangles=triangles,joints=len(names),
                max_influences=max_infl,max_neck=float(neck.max()),neck_levels=int(len(np.unique(neck))),
                images=[tuple(im.size) for im in images],components=components,nonadjacent_self_intersections=self_cross,nonmanifold_edges=open_edges,
                inconsistent_edges=bad_normals,minimum_triangle_area=min(f.calc_area() for f in bm.faces),
                maximum_seam_normal_vector_delta=normal_error)
    bm.free()
    js="""const fs=require('fs'),v=require('gltf-validator');const [input,out]=process.argv.slice(1);
    v.validateBytes(new Uint8Array(fs.readFileSync(input)),{uri:require('path').basename(input)}).then(r=>{
    fs.writeFileSync(out,JSON.stringify(r,null,2)); if(r.issues.numErrors||r.issues.numWarnings)process.exitCode=1;
    }).catch(e=>{console.error(e);process.exitCode=1});"""
    subprocess.run(["node","-e",js,str(GLB),str(HERE/"khronos_validation.json")],cwd=v1.REPO,check=True)
    (HERE/"geometry_check.json").write_text(json.dumps(checks,indent=2)+"\n")
    print(checks,flush=True)


if __name__=="__main__":
    stages=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else ["baseline","build","vertex","tri","audit","views","closeups"]
    for stage in stages:
        if stage=="build": build()
        elif stage in ("vertex","tri"): checker(stage)
        elif stage=="audit": audit()
        elif stage in ("baseline","views"): views(stage)
        elif stage=="closeups": closeups()
        else: raise ValueError(stage)
