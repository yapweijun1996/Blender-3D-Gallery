"""Build the high ponytail from the cached Studio surface and neutral master."""
import bpy
import bmesh
import numpy as np
import math
import sys
import importlib.util
from functools import lru_cache
import json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from pathlib import Path

HERE=Path(__file__).resolve().parent
PARTS=HERE.parents[2]
MASTER=PARTS/'master/GJH_Chibi_Master_rigged.blend'
GLB=HERE/'hair_ponytail_v1.glb'
SRC=Vector((0,-.042,.725))
ROOT=Vector((.001,0,.807))
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('bob_tools',PARTS/'hair-fit-astra/fit_hair.py')
bob=importlib.util.module_from_spec(spec)
spec.loader.exec_module(bob)

def active(o):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active=o

def smooth(a,b,v):
    t=max(0,min(1,(v-a)/(b-a)))
    return t*t*(3-2*t)

def ray(a,e):
    return Vector((math.sin(a)*math.cos(e),-math.cos(a)*math.cos(e),math.sin(e)))

def polar(p,origin):
    d=p-origin
    return math.atan2(d.x,-d.y),math.atan2(d.z,math.hypot(d.x,d.y)),d.length

def interp(x,keys,values):
    return float(np.interp(x,keys,values))

def cut(a):
    # The cut is above all Studio segmentation teeth and below the tie.
    return max(hem(a)+math.radians(13),math.radians(interp(abs(math.degrees(a)),[0,44,62,80,94,109,125,180],[29,29,18,7,5,-20,-31,-31])))

def hem(a):
    # Tangent-flat lock ends and smooth asymmetric arches at their junctions.
    keys=[-180,-156,-127,-110,-96,-86,-77,-70,-63,-57,-49,-43,-37,-28,-20,-13,-7,-2,4,12,18,24,32,42,51,59,66,73,80,91,101,113,130,154,180]
    vals=[-43,-41,-34,-19,-7,-8,-19,-24,-8,-4,-5,-1,-5,4,10,-3,-4,-.3,-4,-4,0,12,1,-4,-5,-5,-14,-25,-15,-7,-10,-23,-36,-42,-43]
    v=math.degrees(a)
    i=max(0,min(len(keys)-2,int(np.searchsorted(keys,v)-1)))
    x0,x1=keys[i:i+2];t=(v-x0)/(x1-x0)
    def slope(j):
        if j==0 or j==len(keys)-1:return 0.
        a=(vals[j]-vals[j-1])/(keys[j]-keys[j-1]);b=(vals[j+1]-vals[j])/(keys[j+1]-keys[j])
        return 2*a*b/(a+b) if a*b>0 else 0.
    e=(2*t**3-3*t*t+1)*vals[i]+(t**3-2*t*t+t)*(x1-x0)*slope(i)+(-2*t**3+3*t*t)*vals[i+1]+(t**3-t*t)*(x1-x0)*slope(i+1)
    return math.radians(e)

def make_tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[p.vertices[:] for p in obj.data.polygons])

def prep_material(obj):
    # Work in stored sRGB bytes for chart-edge cleanup and JPEG export.
    old=obj.active_material
    im=next(n.image for n in old.node_tree.nodes if n.type=='TEX_IMAGE')
    im.colorspace_settings.name='Non-Color'
    w,h=im.size
    c=np.empty((h,w,4),'f');im.pixels.foreach_get(c.ravel())
    rgb=c[:,:,:3];r,g,b=rgb.transpose(2,0,1)
    # Outside charts is black. The ear and face print also leaks into a
    # handful of narrow underside islands. Extend actual chestnut texels.
    ok=(r>.255)&(g>.108)&(g<.66*r)&(b<.51*r)&(g>1.14*b)
    missing=int((~ok).sum())
    for _ in range(40):
        if ok.all():break
        pad=np.pad(ok,1)
        colors=np.pad(rgb,((1,1),(1,1),(0,0)),mode='edge')
        cnt=np.zeros_like(r);sums=np.zeros_like(rgb)
        for dy,dx in [(0,1),(1,0),(2,1),(1,2),(0,0),(2,0),(0,2),(2,2)]:
            vv=pad[dy:dy+h,dx:dx+w]
            cnt+=vv;sums+=colors[dy:dy+h,dx:dx+w]*vv[:,:,None]
        grow=(~ok)&(cnt>0)
        rgb[grow]=sums[grow]/cnt[grow,None];ok|=grow
    rgb[~ok]=np.median(rgb[ok][::35],axis=0)
    return c,missing

def combined_atlas(c,missing,source,original,upper):
    h,w=c.shape[:2]
    # Reserve a band above the original charts. U is unchanged and V scales
    # uniformly. The band samples the original UV texture in fitted directions.
    retained=864
    atlas=np.ones_like(c)
    row=(np.arange(retained)+.5)*h/retained-.5
    lo=np.floor(row).astype(int);frac=(row-lo)[:,None,None]
    atlas[:retained]=(1-frac)*c[lo]+frac*c[np.minimum(lo+1,h-1)]
    atlas[retained:retained+3]=atlas[retained-1]
    data=source.data;uv=data.uv_layers.active
    # Reconcile corresponding Studio texels across UV seams on the surface
    # before filtering them. Collapsing 765k triangles to the module budget
    # otherwise exposes single triangles spanning differently lit chart edges.
    vi=np.array([tuple(p.vertices) for p in data.polygons])
    face_uv=np.array([[uv.data[i].uv[:] for i in f.loop_indices] for f in data.polygons])
    def texels(st):
        ix=np.clip((st[...,0]*w).astype(int),0,w-1)
        iy=np.clip((st[...,1]*h).astype(int),0,h-1)
        return c[iy,ix,:3]
    centre=face_uv.mean(1)
    rgb=texels(.54*face_uv+.46*centre[:,None,:])
    # Segmentation sometimes bakes a light skin streak on the bangs. Limit
    # those outliers to the observed range of the broad chestnut surfaces.
    lower,upper_rgb=np.quantile(rgb.reshape(-1,3),[.06,.90],axis=0)
    rgb=np.clip(rgb,lower,upper_rgb)
    source_color=np.zeros((len(data.vertices),3))
    counts=np.bincount(vi.ravel(),minlength=len(source_color)).clip(1)
    np.add.at(source_color,vi.ravel(),rgb.reshape(-1,3));source_color/=counts[:,None]
    edges=np.array([e.vertices[:] for e in data.edges]);i,j=edges.T
    neighbors=np.bincount(edges.ravel(),minlength=len(source_color)).clip(1)[:,None]
    for _ in range(16):
        acc=np.zeros_like(source_color)
        np.add.at(acc,i,source_color[j]);np.add.at(acc,j,source_color[i])
        source_color=(source_color+acc/neighbors)*.5
    def field(p,face):
        tri=triangles[face]
        weights=barycentric_transform(p,*tri,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
        return np.array(weights)@source_color[vi[face]]

    from mathutils.geometry import barycentric_transform
    triangles=[tuple(Vector(x) for x in [data.vertices[i].co for i in face.vertices]) for face in data.polygons]
    def surface_color(p):
        q,_,f,_=original.find_nearest(p)
        return field(q,f)
    # Correct low-frequency chart mismatches on the actual decimated UV
    # triangles. Retain fine differences of the source texture within them.
    actual=upper.data
    source_tint=np.array([surface_color(v.co) for v in actual.vertices])
    owned=np.zeros((retained,w),bool)
    for p in actual.polygons:
        uvtri=np.array([actual.uv_layers.active.data[i].uv[:] for i in p.loop_indices])*[w,retained]-.5
        mi=np.maximum(0,np.floor(uvtri.min(0)).astype(int));ma=np.minimum([w-1,retained-1],np.ceil(uvtri.max(0)).astype(int))
        if np.any(ma<mi):continue
        dx,dy=uvtri[1:]-uvtri[0];den=dx[0]*dy[1]-dx[1]*dy[0]
        if abs(den)<1e-8:continue
        Y,X=np.mgrid[mi[1]:ma[1]+1,mi[0]:ma[0]+1];xx=X-uvtri[0,0];yy=Y-uvtri[0,1]
        a=(xx*dy[1]-yy*dy[0])/den;b=(dx[0]*yy-dx[1]*xx)/den;inside=(a>=0)&(b>=0)&(a+b<=1)
        if not inside.any():continue
        x=X[inside];y=Y[inside];a=a[inside,None];b=b[inside,None]
        v0,v1,v2=source_tint[list(p.vertices)]
        target=(1-a-b)*v0+a*v1+b*v2
        # Only a bounded high-frequency residual passes through at a UV seam.
        atlas[y,x,:3]=target+np.clip(atlas[y,x,:3]-target,-.022,.022)*.22
        owned[y,x]=True
    for _ in range(12):
        acc=np.zeros((retained,w,3),'f');n=np.zeros((retained,w),'f')
        for dy,dx in [(1,0),(-1,0),(0,1),(0,-1)]:
            neighbors=np.roll(owned,(dy,dx),(0,1))
            col=np.roll(atlas[:retained,:,:3],(dy,dx),(0,1))
            n+=neighbors;acc+=col*neighbors[:,:,None]
        edge=(~owned)&(n>0);atlas[:retained,:,:3][edge]=acc[edge]/n[edge,None];owned|=edge
    atlas[retained:retained+3]=atlas[retained-1]

    def sample(a,e):
        d=ray(a,e);p,n,f,_=original.ray_cast(SRC,d,.198)
        if p is None:
            p,n,f,_=original.find_nearest(SRC+.166*d)
        return (*field(p,f),1.0)
    aw,ah=510,76
    tile=np.empty((ah,aw,4),'f')
    for j in range(ah):
        e=math.radians(-60+150*j/(ah-1))
        for i in range(aw):
            a=-math.pi+math.tau*i/(aw-1)
            # Below the Studio hem continue the nearest lock colour, avoiding
            # the skin-colored cut face printed into the raw segmentation.
            tile[j,i]=sample(a,max(e,hem(a)+math.radians(3)))
    for _ in range(2):
        tile=(4*tile+np.roll(tile,1,1)+np.roll(tile,-1,1)+np.concatenate([tile[:1],tile[:-1]])+np.concatenate([tile[1:],tile[-1:]]))/8
    xs=np.clip((np.arange(w)-2)/2,0,aw-1);ys=np.clip((np.arange(h-retained-4)-2)/2,0,ah-1)
    i,j=xs.astype(int),ys.astype(int);s,t=(xs-i)[None,:,None],(ys-j)[:,None,None]
    v=tile[:,i]*(1-s)+tile[:,np.minimum(i+1,aw-1)]*s
    atlas[retained+4:]=v[j]*(1-t)+v[np.minimum(j+1,ah-1)]*t
    atlas[retained+3]=atlas[retained+4]
    image=bpy.data.images.new('Studio chestnut | padded base colour',w,h,alpha=False)
    image.colorspace_settings.name='Non-Color';image.pixels.foreach_set(atlas.ravel())
    image.file_format='PNG';image.filepath_raw=str(HERE/'.runtime/chestnut.png');image.save()
    bpy.data.images.remove(image)
    image=bpy.data.images.load(str(HERE/'.runtime/chestnut.png'))
    image.colorspace_settings.name='sRGB';image.pack()
    mat=bpy.data.materials.new('Chestnut | Studio base colour')
    mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Roughness'].default_value=.56
    bs.inputs['Specular IOR Level'].default_value=.32
    tx=mat.node_tree.nodes.new('ShaderNodeTexImage');tx.image=image
    mat.node_tree.links.new(tx.outputs['Color'],bs.inputs['Base Color'])
    print('Atlas',w,h,'padded texels',missing,flush=True)
    return mat

def clip_upper(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    values={}
    for v in bm.verts:
        a,e,r=polar(v.co,SRC)
        values[v]=max(e-cut(a),(r-.198)*22 if 1.6<a<3.05 else -1)
    bob.trim_field(bm,values)
    islands=bob.connected_faces(bm)
    for comp in islands[1:]:bmesh.ops.delete(bm,geom=comp,context='FACES')
    bm.to_mesh(obj.data);bm.free()
    active(obj)
    dec=obj.modifiers.new('Outer clump detail budget','DECIMATE')
    dec.ratio=1200/len(obj.data.polygons)
    bpy.ops.object.modifier_apply(modifier=dec.name)
    bm=bmesh.new();bm.from_mesh(obj.data)
    boundary={e for e in bm.edges if e.is_boundary}
    loops=[]
    while boundary:
        first=boundary.pop();u,v=first.verts;row=[u,v]
        while v!=u:
            opts=[e for e in v.link_edges if e in boundary]
            if not opts:break
            ed=opts[0];boundary.remove(ed);v=ed.other_vert(v)
            if v!=u:row.append(v)
        loops.append(row)
    loops.sort(key=len,reverse=True)
    print('Clipped boundaries',[(len(q),tuple(round(k,3) for k in q[0].co)) for q in loops[:12]],flush=True)
    for small in loops[1:]:
        group=set(small)
        bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary and set(e.verts)<=group])
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
    bm.verts.index_update()
    border=[v.index for v in loops[0]]
    bm.to_mesh(obj.data);bm.free()
    return border

def build():
    sys.path.insert(0,str(HERE))
    from bake_clearance import cache_poses,apply_offsets
    cache_poses()
    bpy.ops.wm.open_mainfile(filepath=str(MASTER),use_scripts=False)
    bpy.context.preferences.filepaths.save_version=0
    bpy.context.preferences.filepaths.file_preview_type='NONE'
    sc=bpy.context.scene
    body,arm=sc.objects['Base_Body'],sc.objects['Armature']
    with bpy.data.libraries.load(str(HERE/'source_working.blend'),link=False) as (src,dst):
        dst.objects=['tripo_part_0']
    obj=dst.objects[0];sc.collection.objects.link(obj)
    original=make_tree(obj);skin=make_tree(body)
    colors,missing=prep_material(obj)
    donor=obj.copy();donor.data=obj.data.copy()
    border=clip_upper(obj)
    mat=combined_atlas(colors,missing,donor,original,obj)
    bpy.data.objects.remove(donor,do_unlink=True)
    mesh=obj.data
    sourceverts=[v.co.copy() for v in mesh.vertices]
    faces=[tuple(f.vertices) for f in mesh.polygons]
    oldfacecount=len(faces)
    uv=mesh.uv_layers.active
    charts=[[tuple(uv.data[j].uv) for j in f.loop_indices] for f in mesh.polygons]
    # A smooth field prevents low-poly skull triangles printing through the cap.
    # Retain the small local support step on the hidden lining separately.
    na,ne=180,77
    field=np.zeros((na,ne))
    for i in range(na):
        for j in range(ne):
            d=ray(i*math.tau/na,math.radians(-62+2*j))
            hit=skin.ray_cast(ROOT+d*.48,-d,.48)[0]
            field[i,j]=(hit-ROOT).length if hit is not None else .168
    for _ in range(10):
        field=(4*field+np.roll(field,1,0)+np.roll(field,-1,0)+np.c_[field[:,0],field[:,:-1]]+np.c_[field[:,1:],field[:,-1]])/8
    def body_r(a,e):
        u=((a%math.tau)*na/math.tau)%na;v=np.clip((math.degrees(e)+62)/2,0,ne-1.00001)
        i,j=int(u),int(v);s,t=u-i,v-j
        return (1-s)*((1-t)*field[i,j]+t*field[i,j+1])+s*((1-t)*field[(i+1)%na,j]+t*field[(i+1)%na,j+1])
    def src_base(a,e):
        d=ray(a,e)
        # Ellipsoid fitted to the smooth Studio cap (crown .894, rear .146).
        radii=np.array((.171,.167,.170));off=np.array((.001,-.020,.002));n=np.array(d)
        aa=np.sum((n/radii)**2);bb=np.sum(n*off/radii**2)
        return (-bb+math.sqrt(bb*bb-aa*(np.sum((off/radii)**2)-1)))/aa
    def support(d,pad):
        hit,n,_,_=skin.ray_cast(ROOT+d*.48,-d,.48)
        if hit is None:return .17
        r=(hit-ROOT).length+pad/max(.45,d.dot(n))
        for _ in range(5):
            p=ROOT+d*r;q,n,_,_=skin.find_nearest(p)
            deficit=pad-(p-q).dot(n)
            if deficit<.00001:break
            r+=deficit/max(.35,d.dot(n))
        return r
    def upper_r(a,e,r):
        delta=r-src_base(a,e)
        base=body_r(a,e)+.017
        # Broad convex locks sweep from the upper forehead to distinct ends.
        ad=math.degrees(a);ed=math.degrees(e)
        comb=ad-4*math.sin(e)*math.sin(a)
        lobes=sum(amp*math.exp(-.5*((comb-mid)/width)**2) for mid,width,amp in
                  [(-54,6,.004),(-37,8,.007),(-11,8,.008),(6,8,.009),(41,13,.009),(68,6,.004)])
        relief=lobes*(1-smooth(15,60,ed))
        return base+relief+delta*(.62+.53*smooth(.008,.06,delta))
    verts=[]
    for p in sourceverts:
        a,e,r=polar(p,SRC)
        verts.append(ROOT+ray(a,e)*upper_r(a,e,r))
    angles=[polar(sourceverts[i],SRC)[0] for i in border]
    moves=np.angle(np.exp(1j*np.diff(angles+[angles[0]])))
    print('border azimuth',len(border),np.degrees(moves).min(),np.degrees(moves).max(),np.degrees(sum(moves)),flush=True)
    if sum(moves)<0:border.reverse()
    k=min(range(len(border)),key=lambda k:polar(sourceverts[border[k]],SRC)[0]);border=border[k:]+border[:k]
    def angle(idx):return polar(verts[idx],ROOT)[0]
    def join(top,bottom):
        # Associate each ring by a common seam and cyclic order. The Studio
        # cut has slight backtracking, which is retained on its first row.
        def seq(row):
            a=np.unwrap([angle(i) for i in row]);a-=math.tau*round((a[0]+math.pi)/math.tau);return list(a)+[a[0]+math.tau]
        u,v=seq(top),seq(bottom);i=j=0
        while i<len(top) or j<len(bottom):
            p,q=top[i%len(top)],bottom[j%len(bottom)]
            if j==len(bottom) or (i<len(top) and u[i+1]<=v[j+1]):
                faces.append((p,q,top[(i+1)%len(top)]));i+=1
            else:
                faces.append((p,q,bottom[(j+1)%len(bottom)]));j+=1
    samples=np.linspace(-math.pi,math.pi,1441)
    rim_profile=np.array([hem(x) for x in samples])
    curvature=np.abs(np.gradient(np.gradient(rim_profile,samples),samples))
    density=1+.65*np.exp(-(samples/1.45)**4)+.11*np.minimum(19,curvature)*np.exp(-(samples/1.9)**6)
    mass=np.r_[0,np.cumsum((density[1:]+density[:-1])*.5)]
    def roundrow(count,fn):
        row=[]
        angles=np.interp(np.arange(count)*mass[-1]/count,mass,samples) if count>60 else np.linspace(-math.pi,math.pi,count,endpoint=False)
        for a in angles:
            row.append(len(verts));verts.append(fn(a))
        return row
    def shell(a,e):
        d=ray(a,e)
        hit=original.ray_cast(SRC,d,.195)[0]
        r=(hit-SRC).length if hit is not None else src_base(a,e)
        return max(body_r(a,e)+.011,upper_r(a,e,r))
    @lru_cache(maxsize=None)
    def rim(a):
        e=hem(a)
        rear=smooth(104,128,abs(math.degrees(a)))
        if rear:
            world_z=.674+.081*((math.pi-abs(a))/math.radians(80))**2
            trial=e
            for _ in range(5):
                trial=math.asin(np.clip((world_z-ROOT.z)/shell(a,trial),-.96,.96))
            e+=rear*(trial-e)
        d=ray(a,e)
        inside=support(d,.00175+.0006*smooth(64,110,abs(math.degrees(a))))
        # Rounding folds the skirt into a thin, seated edge under the clumps.
        outer=max(inside+.0036,shell(a,e)+.001)
        return e,inside,outer
    for frac,n in [(.36,69),(.73,82)]:
        def course(a):
            low,rin,rout=rim(a);e=(1-frac)*cut(a)+frac*low
            r=shell(a,e)
            r=r*(1-frac**3)+rout*frac**3
            return ROOT+ray(a,e)*r
        row=roundrow(n,course);join(border,row);border=row
    for phase,n in [(0,144),(math.pi*.53,150),(math.pi,133)]:
        def roll(a):
            e,rin,rout=rim(a);r=(rin+rout+(rout-rin)*math.cos(phase))/2
            return ROOT+ray(a,e-min(.004,(rout-rin)*.5)*math.sin(phase)/r)*r
        row=roundrow(n,roll);join(border,row);border=row
    for t,n in [(.075,70),(.16,52),(.29,42),(.42,33),(.55,29),(.69,24),(.81,17),(.92,12)]:
        def lining(a):
            e=rim(a)[0]*(1-t)+math.pi*.5*t
            d=ray(a,e);return ROOT+d*support(d,.0030+.004*t)
        row=roundrow(n,lining);join(border,row);border=row
    pole=len(verts);d=Vector((0,0,1));verts.append(ROOT+d*support(d,.009))
    for i,p in enumerate(border):faces.append((p,border[(i+1)%len(border)],pole))
    from repair_upper import relax_fold
    relax_fold(verts,faces,oldfacecount)
    apply_offsets(verts,faces,ROOT,skin)
    new=bpy.data.meshes.new('Studio ponytail with rolled hairline')
    new.from_pydata(verts,[],faces);new.update()
    layer=new.uv_layers.new(name='UVMap')
    # The original charts remain on the upper surface and the entire tail.
    # The added geometry samples a continuous band baked from the same atlas.
    for f in new.polygons:
        angles=np.unwrap([polar(verts[i],ROOT)[0] for i in f.vertices]);angles-=math.tau*round(float(np.mean(angles))/math.tau)
        for k,li in enumerate(f.loop_indices):
            if f.index<oldfacecount:
                u,v=charts[f.index][k];xy=(u,v*864/1024)
            else:
                p=verts[f.vertices[k]];a,e,_=polar(p,ROOT)
                u=np.clip((angles[k]+math.pi)/math.tau,0,1);v=np.clip((math.degrees(e)+60)/150,0,1)
                xy=((2.5+1018*u)/1024,(870.5+150*v)/1024)
            layer.data[li].uv=xy
        f.use_smooth=True
    bm=bmesh.new();bm.from_mesh(new)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    print('Mesh',len(bm.faces),'bad edges',sum(not e.is_manifold for e in bm.edges),'volume',bm.calc_volume(signed=True),flush=True)
    bm.to_mesh(new);bm.free()
    obj.data=new;new.materials.append(mat);obj.name='Hair_High_Ponytail'
    head=obj.vertex_groups.new(name='mixamorig:Head');head.add(list(range(len(verts))),1,'REPLACE')
    obj.modifiers.new('Neutral master skeleton','ARMATURE').object=arm
    active(obj);arm.hide_set(False);arm.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,export_animations=False,export_def_bones=False,export_all_influences=False)
    obj.parent=arm
    arm.hide_set(True)
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(GLB.with_suffix('.blend')),compress=True)

if __name__=='__main__':build()

