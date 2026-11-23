"""Rebuild the round-two twin tails, render the exported skin and run offline QA.

Use Blender in background mode. Stages: build, views, vertex, triangle, motion,
audit. The default runs all stages. The two supplied checker paths are resolved
under MODULAR_CHECKER_DIR (or the original local scratch directory).
"""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import runpy
import subprocess
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
WORK = HERE / '.work'
CHECKS = HERE / 'checks'
CLOSE = HERE / 'closeups'
R2 = HERE.parent / 'round2'
GLB = HERE / 'hair_twintails_v3.glb'
BLEND = HERE / 'hair_twintails_v3.blend'
MASTER = HERE.parents[2] / 'master/GJH_Chibi_Master_rigged.blend'
CLIPS = HERE.parents[2] / 'body-fix/motion_fixed.glb'
CHECKER_DIR = Path(os.environ.get('MODULAR_CHECKER_DIR',
    '/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular'))
spec = importlib.util.spec_from_file_location('original_fit', HERE.parent / 'fit_hair.py')
fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit)
bob = fit.bob
CLIP_NAMES = ('walk', 'run', 'wave', 'jump', 'idle', 'nod', 'dance')
VIEW_NAMES = ('front', 'three_quarter_left', 'three_quarter_right', 'left', 'back', 'right')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def smooth(lo, hi, x):
    t = np.clip((x-lo)/(hi-lo), 0, 1)
    return t*t*(3-2*t)


def active(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def finish_mesh(obj, discard_fragments=False):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
    if discard_fragments:
        components = sorted(bob.connected_faces(bm), key=len, reverse=True)
        print('Volume components', [len(g) for g in components[:15]], flush=True)
        scrap = {v for g in components[1:] for f in g for v in f.verts}
        if scrap:
            bmesh.ops.delete(bm, geom=list(scrap), context='VERTS')
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts)>3])
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    for f in bm.faces:
        f.smooth = True
    print('Mesh', len(bm.faces), 'triangles,', sum(not e.is_manifold for e in bm.edges), 'nonmanifold edges', flush=True)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def modifier(obj, kind, **values):
    m = obj.modifiers.new(kind.title(), kind)
    for k, v in values.items():
        setattr(m, k, v)
    bpy.ops.object.modifier_apply(modifier=m.name)


def lift_tip(x, z):
    # In run frame 4 the curl turns into the moving arm just below z=.622.
    return smooth(.125, .168, abs(x))*(1-smooth(.625, .733, z))


def strand_volume(controls, transform, horizontal=False):
    """Closed, gently fluted cross sections following a Catmull-Rom spine."""
    import openvdb
    controls=np.asarray(controls,float)
    centers=[]
    for j in range(len(controls)-1):
        a,b,c,d=controls[np.clip([j-1,j,j+1,j+2],0,len(controls)-1)]
        for t in np.linspace(0,1,7,endpoint=False):
            centers.append(.5*(2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t**3))
    centers=np.vstack([centers,controls[-1]])
    vertices=[]
    faces=[]
    count=40
    for k, (cx,cy,cz,rx,ry) in enumerate(centers):
        length=centers[min(k+1,len(centers)-1),:3]-centers[max(0,k-1),:3]
        tangent=length/np.linalg.norm(length)
        # A lock of the fringe fans horizontally. A free tail transports
        # its flatter cross-section around the bend, including the upturn.
        if horizontal:
            u=np.array([1,0,0])
            v=np.array([0,1,0])
        else:
            u=np.cross([0,1,0],tangent)
            u/=np.linalg.norm(u)
            v=np.cross(tangent,u)
        for i in range(count):
            ang=2*math.pi*i/count
            flow=1+.05*math.cos(3*ang+1.4*k/len(centers))
            p=[cx,cy,cz]+flow*(max(.00035,rx)*math.cos(ang)*u+max(.00035,ry)*math.sin(ang)*v)
            vertices.append(p)
            if k:
                j=k*count+i
                next_j=k*count+(i+1)%count
                faces.extend([(j-count,next_j-count,next_j),(j-count,next_j,j)])
    for k in (0,len(centers)-1):
        idx=len(vertices)
        vertices.append(centers[k,:3])
        for i in range(count):
            faces.append((idx,k*count+i,k*count+(i+1)%count))
    return openvdb.FloatGrid.createLevelSetFromPolygons(np.array(vertices,'f'),np.array(faces,'I'),
                                                        transform=transform,halfWidth=14)


def shape_ends(obj):
    """Sculpt new tapered fringe and S-curl ends into the fused R2 envelope."""
    import openvdb
    h=.0017
    transform=openvdb.createLinearTransform(voxelSize=h)
    mesh=obj.data
    points=np.array([v.co[:] for v in mesh.vertices],'f')
    indices=np.array([p.vertices[:] for p in mesh.polygons],'I')
    grid=openvdb.FloatGrid.createLevelSetFromPolygons(points,indices,transform=transform,halfWidth=14)
    fringe=[
        [(.013,-.181,.951,.045,.022),(.016,-.201,.927,.050,.026),
         (.015,-.210,.906,.054,.024),(.009,-.212,.884,.052,.023),
         (-.001,-.211,.864,.044,.017),(-.014,-.211,.847,.032,.012),
         (-.026,-.208,.833,.022,.009),(-.035,-.204,.824,.013,.005),
         (-.047,-.201,.817,.00045,.00045)],
        [(.050,-.180,.940,.031,.024),(.059,-.195,.913,.035,.023),
         (.061,-.201,.892,.036,.022),(.058,-.198,.872,.031,.018),
         (.052,-.196,.854,.025,.014),(.044,-.196,.839,.018,.009),
         (.034,-.197,.828,.010,.005),(.021,-.196,.819,.00045,.00045)]]
    pony=[
        [(.225,.054,.814,.031,.059),(.224,.048,.785,.032,.060),
         (.216,.037,.754,.036,.060),(.221,.025,.730,.038,.061),
         (.239,.022,.707,.036,.058),(.249,.032,.682,.031,.050),
         (.245,.051,.659,.025,.038),(.230,.072,.644,.019,.029),
         (.208,.093,.638,.013,.021),(.185,.116,.644,.007,.011),
         (.162,.139,.660,.00045,.00045)],
        [(.225,.069,.804,.021,.032),(.229,.068,.778,.020,.030),
         (.242,.075,.753,.019,.025),(.263,.087,.732,.017,.021),
         (.280,.099,.714,.014,.016),(.289,.110,.698,.010,.012),
         (.290,.119,.686,.006,.007),(.284,.126,.676,.0004,.0004)]]
    body=bpy.context.scene.objects['Base_Body']
    body.data.calc_loop_triangles()
    skin=openvdb.FloatGrid.createLevelSetFromPolygons(
        np.array([body.matrix_world@v.co for v in body.data.vertices],'f'),
        np.array([f.vertices[:] for f in body.data.loop_triangles],'I'),transform=transform,halfWidth=14)
    def patch(lo,hi,controls,side=0):
        begin=np.floor(np.array(lo)/h).astype(int)
        end=np.ceil(np.array(hi)/h).astype(int)
        shape=tuple(end-begin+1)
        ijk=tuple(int(x) for x in begin)
        old=np.empty(shape,'f')
        grid.copyToArray(old,ijk=ijk)
        new=np.full(shape,grid.background,'f')
        for strand in controls:
            pts=np.array(strand)
            if side:
                ear=smooth(.665,.707,pts[:,2])*(1-smooth(.755,.810,pts[:,2]))
                pts[:,0]=(pts[:,0]+.020*ear)*side
                pts[:,1]+=.009*ear
            else:
                pts[:,1]-=.004
            component=strand_volume(pts,transform,horizontal=not side)
            sdf=np.empty(shape,'f')
            component.copyToArray(sdf,ijk=ijk)
            # Rounded union at the shared root. Beyond the split the two
            # tapered tips retain their own normals and negative space.
            radius=.003
            delta=np.maximum(radius-np.abs(new-sdf),0)/radius
            new=np.minimum(new,sdf)-.25*radius*delta**2
        x,y,z=[a*h for a in np.ogrid[begin[0]:end[0]+1,begin[1]:end[1]+1,begin[2]:end[2]+1]]
        if side:
            lateral=np.maximum(smooth(.155,.182,abs(x)),(1-smooth(.67,.71,z))*smooth(.12,.152,abs(x)))
            mask=lateral*smooth(-.065,-.035,y)*(1-smooth(.122,.155,y))*(1-smooth(.738,.801,z))
        else:
            left=-.078+.027*smooth(.843,.877,z)
            mask=smooth(left,left+.022,x)*(1-smooth(.085,.104,x))*smooth(.145,.177,-y)*(1-smooth(.885,.926,z))
        # Ensure room for the pinnae and forehead along the inward-facing
        # walls before blending the new swept locks into the original shell.
        body_distance=np.empty(shape,'f')
        skin.copyToArray(body_distance,ijk=ijk)
        new=np.maximum(new,.0085-body_distance)
        grid.copyFromArray(np.ascontiguousarray(old+mask*(new-old),dtype='f'),ijk=ijk)
    patch((-.09,-.264,.790),(.120,-.122,.945),fringe)
    for side in (-1,1):
        bounds=sorted([.11*side,.322*side])
        patch((bounds[0],-.078,.580),(bounds[1],.17,.821),pony,side)
    # Roll the two corners of the rear hem into an uninterrupted arc.
    start=np.floor(np.array([-.192,.032,.670])/h).astype(int)
    end=np.ceil(np.array([.192,.255,.770])/h).astype(int)
    region=np.empty(tuple(end-start+1),'f')
    ijk=tuple(int(x) for x in start)
    grid.copyToArray(region,ijk=ijk)
    x,y,z=[a*h for a in np.ogrid[start[0]:end[0]+1,start[1]:end[1]+1,start[2]:end[2]+1]]
    floor=.680+.034*(np.abs(x)/.167)**4
    cut=floor-z
    rounding=.010
    radius=np.maximum(rounding-np.abs(region-cut),0)/rounding
    rolled=np.maximum(region,cut)+.25*rounding*radius*radius
    w=smooth(.04,.090,y)*(1-smooth(.166,.189,abs(x)))*smooth(.670,.683,z)
    grid.copyFromArray(np.ascontiguousarray(region+w*(rolled-region),dtype='f'),ijk=ijk)
    verts,tri,quad=grid.convertToPolygons(isovalue=0,adaptivity=.06)
    replacement=bpy.data.meshes.new('Fused and tapered locks')
    replacement.from_pydata(verts.tolist(),[],tri.tolist()+quad.tolist())
    obj.data=replacement
    bpy.data.meshes.remove(mesh)
    finish_mesh(obj,True)


def unwrap(obj):
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(58),island_margin=.016,
                             area_weight=.3,correct_aspect=False,scale_to_bounds=True)
    bpy.ops.uv.seams_from_islands(mark_seams=True,mark_sharp=False)
    bpy.ops.uv.unwrap(method='ANGLE_BASED',margin=.009)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(margin_method='FRACTION',margin=.0095,shape_method='CONCAVE')
    bpy.ops.object.mode_set(mode='OBJECT')

    # Leave a dedicated strip for occasional folded triangles. Repacking a
    # whole atlas after each fix can move a different overlap onto a texel.
    mesh=obj.data
    uv=mesh.uv_layers.active.data
    for loop in uv:
        loop.uv.y=.135+.865*loop.uv.y
    owner=np.full((1024,1024),-1,int)
    busy=np.zeros((1024,1024),bool)
    bad=set()
    for f in mesh.polygons:
        st=np.asarray([uv[idx].uv[:] for idx in f.loop_indices])
        y,x,w=raster(st,1024)
        if w is None:
            bad.add(f.index)
            continue
        busy[y,x]=True
        inside=w.min(1)>1e-6
        ids=owner[y[inside],x[inside]]
        if np.any(ids>=0):
            bad.add(f.index)
            bad.update(ids[ids>=0].tolist())
        owner[y[inside],x[inside]]=f.index
    for i in sorted(bad):
        f=mesh.polygons[i]
        p=np.array([mesh.vertices[j].co[:] for j in f.vertices])
        e=p[1]-p[0]
        e/=np.linalg.norm(e)
        n=np.cross(e,p[2]-p[0])
        n/=np.linalg.norm(n)
        xy=(p-p[0])@np.array([e,np.cross(n,e)]).T
        xy-=xy.min(0)
        # Guarantee usable texel width even on a physical sliver.
        xy*=np.maximum(950.,2.8/np.maximum(1e-9,xy.max(0)))
        integral=np.pad(busy,((1,0),(1,0))).cumsum(0,dtype='i4').cumsum(1,dtype='i4')
        pad=17
        width,height=np.ceil(xy.max(0)).astype(int)+1+2*pad
        free=integral[height:,width:]-integral[:-height,width:]-integral[height:,:-width]+integral[:-height,:-width]
        slots=np.flatnonzero(free==0)
        if not len(slots):
            raise RuntimeError(f'No padded space for face {i}')
        y,x=np.unravel_index(slots[0],free.shape)
        for idx,st in zip(f.loop_indices,(xy+[x+pad+.5,y+pad+.5])/1024):
            uv[idx].uv=st
        busy[y:y+height,x:x+width]=True


def fair_budget_mesh(obj, high):
    """Redistribute decimator slivers along the original rounded surface."""
    surface=BVHTree.FromPolygons([v.co.copy() for v in high.vertices],
                                 [f.vertices[:] for f in high.polygons],all_triangles=True)
    bm=bmesh.new()
    bm.from_mesh(obj.data)
    # Limit redistribution to the convex tail crests. The fine cut edge
    # of a cheek lock must never be snapped to its opposite wall.
    def weight(v):
        x,y,z=v.co
        return (bob.smooth(.156,.194,abs(x))*bob.smooth(.076,.132,y)*
                bob.smooth(.894,.954,z))
    for k in range(7):
        zone=[f for f in bm.faces if all(weight(v)>.01 for v in f.verts)]
        zset=set(zone)
        edges=[e for e in bm.edges if e.link_faces and all(f in zset for f in e.link_faces)]
        bmesh.ops.beautify_fill(bm,faces=zone,edges=edges,method='AREA')
        bm.normal_update()
        next_points={}
        for v in bm.verts:
            amount=weight(v)
            if not amount:
                continue
            adjacent=[e.other_vert(v).co for e in v.link_edges]
            avg=sum(adjacent,Vector())/len(adjacent)
            delta=avg-v.co
            delta-=.70*delta.dot(v.normal)*v.normal
            if delta.length>.010:
                delta*=.010/delta.length
            trial=v.co+.48*delta
            hit=surface.find_nearest(trial)
            if hit[1].dot(v.normal)<.05:
                candidates=surface.find_nearest_range(trial,max(.004,hit[3]+.002))
                if candidates:
                    hit=min(candidates,key=lambda q:q[3]+.004*max(0.,.4-q[1].dot(v.normal)))
            next_points[v]=v.co.lerp(hit[0],.80*amount)
        for v,q in next_points.items():
            v.co=q
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def support_liner(obj):
    # The straight chords of a low-poly liner need clearance over the
    # convex skull between their vertices. Move thin outer sections with it.
    scalp=bob.tree_for(bpy.context.scene.objects['Base_Body'],True)
    for v in obj.data.vertices:
        p=v.co
        gap=scalp.find_nearest(p)[3]
        posterior=bob.smooth(-.018,.075,p.y)
        crown=bob.smooth(.870,.975,p.z)
        w=(1-bob.smooth(.011,.038,gap))*max(posterior,.50*crown)
        outward=(p-bob.ROOT).normalized()
        p+=outward*(.0068*w)
    obj.data.update()


def sculpt(obj):
    active(obj)
    for m in list(obj.modifiers):
        obj.modifiers.remove(m)
    obj.vertex_groups.clear()
    mesh = obj.data
    if mesh.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    while mesh.uv_layers:
        mesh.uv_layers.remove(mesh.uv_layers[0])
    # Give the thin exterior/lining sandwich enough thickness to sample it
    # as a volume. The thin top of the head stays inside the fitted liner.
    for v in mesh.vertices:
        p = v.co
        w = smooth(.72, .93, p.z)
        outward = Vector((p.x-.001, p.y, p.z-.807)).normalized()
        p += outward * (.0028*w*max(0., v.normal.dot(outward)))
    # Subdivision of the welded original softens the planar facets at each
    # ponytail crest and rounds the two ends of the posterior hem.
    finish_mesh(obj)
    modifier(obj,'SUBSURF',subdivision_type='CATMULL_CLARK',levels=1)
    # Offset isosurfaces close the interlocking slits while retaining the
    # open underside of the wig. Re-distance between expansion and return.
    group=bpy.data.node_groups.new('Close and fair the hair envelope','GeometryNodeTree')
    for io in ('INPUT','OUTPUT'):
        group.interface.new_socket(name='Geometry',in_out=io,socket_type='NodeSocketGeometry')
    incoming=group.nodes.new('NodeGroupInput').outputs['Geometry']
    def stage(kind, prior, **inputs):
        node=group.nodes.new('GeometryNode'+kind)
        group.links.new(prior,node.inputs[0])
        for key,value in inputs.items():
            node.inputs[key].default_value=value
        return node.outputs[0]
    expanded=stage('MeshToSDFGrid',incoming,**{'Voxel Size':.0019,'Band Width':8})
    surface=stage('GridToMesh',expanded,Threshold=.0074,Adaptivity=.025)
    grid=stage('MeshToSDFGrid',surface,**{'Voxel Size':.0019,'Band Width':9})
    grid=stage('SDFGridMean',grid,Width=3,Iterations=3)
    surface=stage('GridToMesh',grid,Threshold=-.0051,Adaptivity=.075)
    group.links.new(surface,group.nodes.new('NodeGroupOutput').inputs[0])
    mod=obj.modifiers.new('Weld and fair folds','NODES')
    mod.node_group=group
    bpy.ops.object.modifier_apply(modifier=mod.name)
    finish_mesh(obj, True)
    # The budget mesh is redistributed on the high-resolution envelope.
    shape_ends(obj)
    high=obj.data.copy()
    modifier(obj, 'DECIMATE', ratio=min(1., 2984/len(obj.data.polygons)), use_collapse_triangulate=True)
    fair_budget_mesh(obj, high)
    support_liner(obj)
    finish_mesh(obj)
    for v in obj.data.vertices:
        p = v.co
        w = lift_tip(p.x, p.z)
        p.z += .012*w
        p.x += math.copysign(.005*w, p.x)
    obj.data.update()
    bpy.data.meshes.remove(high)


def raster(st, size):
    xy = st*size-.5
    lo = np.maximum(0, np.ceil(xy.min(0)).astype(int))
    hi = np.minimum(size-1, np.floor(xy.max(0)).astype(int))
    y, x = np.mgrid[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
    basis = (xy[1:]-xy[0]).T
    if not x.size or abs(np.linalg.det(basis))<1e-12:
        return [], [], None
    uv = (np.stack((x,y),axis=-1)-xy[0]) @ np.linalg.inv(basis).T
    w = np.dstack((1-uv.sum(-1), uv))
    valid = w.min(-1)>=-1e-7
    return y[valid], x[valid], w[valid]


def png_pixels(path):
    im = bpy.data.images.load(str(path), check_existing=False)
    im.colorspace_settings.name = 'Non-Color'
    data = np.empty(4*im.size[0]*im.size[1], 'f')
    im.pixels.foreach_get(data)
    data = data.reshape(im.size[1], im.size[0], 4)
    bpy.data.images.remove(im)
    return data


def write_png(path, data):
    h,w,channels = data.shape
    im = bpy.data.images.new(path.stem, w, h, alpha=channels==4)
    im.colorspace_settings.name = 'Non-Color'
    if channels==3:
        data = np.dstack((data,np.ones((h,w), 'f')))
    im.pixels.foreach_set(np.ascontiguousarray(data, dtype='f').ravel())
    im.file_format = 'PNG'
    im.filepath_raw = str(path)
    im.save()
    bpy.data.images.remove(im)


def ribbon_planes(donor):
    # Fit a band to each original violet attachment in mesh space. A single
    # continuous plane per side avoids inheriting jagged atlas transitions.
    pos, _, _, _, uv=fit.mesh_arrays(donor)
    im=next(n.image for n in donor.materials[0].node_tree.nodes
            if n.type=='TEX_IMAGE' and 'basecolor' in n.image.name)
    im.colorspace_settings.name='Non-Color'
    px=np.empty(1024*1024*4,'f')
    im.pixels.foreach_get(px)
    px=px.reshape(1024,1024,4)
    samples=[]
    for i,st in enumerate(uv):
        if st[:,1].min()<.03:
            continue
        y,x,w=raster(st,1024)
        if w is None:
            continue
        q=w@pos[i]
        rgb=px[y,x,:3]
        valid=(rgb[:,2]-rgb[:,1]>.11)&(q[:,2]>.92)&(abs(q[:,0])>.065)
        if valid.any():
            samples.append(q[valid])
    points=np.vstack(samples)
    result=[]
    for side in (-1,1):
        q=points[side*points[:,0]>0]
        center=q.mean(0)
        _,vectors=np.linalg.eigh(np.cov(q.T))
        result.append((center,vectors[:,0]))
    return result


def surface_color(obj, donor):
    planes=ribbon_planes(donor)
    active(obj)
    unwrap(obj)
    dst = fit.mesh_arrays(obj.data)
    atlas = np.zeros((1024,1024,3),'f')
    normal_atlas=np.zeros_like(atlas)
    mask = np.zeros((1024,1024),bool)
    for i, st in enumerate(dst[4]):
        y,x,w = raster(st,1024)
        if w is None or not len(x):
            continue
        p = w@dst[0][i]
        # Invert the local curl lift to sample the original colour field.
        original = p.copy()
        for _ in range(4):
            lift = lift_tip(original[:,0],original[:,2])
            original[:,2] = p[:,2]-.012*lift
            original[:,0] = p[:,0]-np.sign(p[:,0])*.005*lift
        n=fit.normalize(w@dst[1][i])
        t=w@dst[2][i]
        t=fit.normalize(t-n*(t*n).sum(1,keepdims=True))
        bt=np.cross(n,t)*np.sign(w@dst[3][i])
        surf=n
        sx,sy,sz=original.T
        # On the back, use uninterrupted swept channels with a level tangent
        # at the centre. Fade them before the rounded hem turns underneath.
        rear=(smooth(.044,.125,sy)*(1-smooth(.143,.202,np.abs(sx)))*
              smooth(.68,.73,sz)*(1-smooth(.994,1.025,sz))*smooth(.0,.28,surf[:,1]))
        def phase(points):
            a,b,c=points.T
            polar=np.arctan2(c-.807,np.maximum(.02,np.hypot(a,b)))
            return 30*(polar-.27*(a/.16)**2)+.42*np.sin(3*polar+2*a)
        phi=phase(original)
        grad=np.column_stack([(phase(original+off)-phase(original-off))/.0002
                              for off in .0001*np.eye(3)])
        grad-=surf*(grad*surf).sum(1,keepdims=True)
        # A broad strand flank and a narrow trough; the physical pigment
        # varies a few percent across the same smooth course.
        perturb=fit.normalize(grad)*(.14*np.sin(phi)+.074*np.sin(2*phi))[:,None]
        tail=(smooth(.145,.198,np.abs(sx))*smooth(-.064,-.014,sy)*(1-smooth(.765,.846,sz)))
        bang=(smooth(-.078,-.047,sx)*(1-smooth(.082,.119,sx))*
              smooth(.154,.19,-sy)*(1-smooth(.887,.958,sz)))
        # The rebuilt locks have their own flow. Nearest paint from an old
        # overlapping tip would project fragmentary marks across the curl.
        def tail_phase(q):
            xx,yy,zz=q.T
            xx=np.abs(xx)
            cx=np.interp(zz,[.62,.65,.68,.705,.735,.765,.80,.86,.93,1.04],
                            [.194,.231,.249,.260,.25,.233,.234,.246,.251,.198])
            cy=np.interp(zz,[.62,.65,.68,.705,.735,.765,.80,.86,.93,1.04],
                            [.099,.07,.042,.032,.035,.052,.055,.065,.08,.065])
            return 3*np.arctan2((yy-cy)*.68,xx-cx)+.8*np.sin((zz-.63)*10)
        def bang_phase(q):
            xx,yy,zz=q.T
            return 94*(xx-.020*np.sin((zz-.84)*20)-.55*(zz-.875))
        def flow(phase_fn):
            ph=phase_fn(original)
            # A cyclic phase may wrap at pi: differentiate its periodic relief.
            grad=np.column_stack([(np.cos(phase_fn(original+offset))-np.cos(phase_fn(original-offset)))/.0002
                                  for offset in .0001*np.eye(3)])
            grad-=n*(n*grad).sum(1,keepdims=True)
            return ph,grad/np.maximum(90.,np.linalg.norm(grad,axis=1,keepdims=True))
        tail_ph,tail_grad=flow(tail_phase)
        bang_ph,bang_grad=flow(bang_phase)
        # Use one continuous chestnut field on the whole wig. Only the
        # violet tie placement comes from the old UV data.
        tie=np.zeros(len(x))
        bead=np.zeros_like(n)
        for center,axis in planes:
            delta=p-center
            along=delta@axis
            across=np.linalg.norm(delta-along[:,None]*axis,axis=1)
            zone=(1-smooth(.064,.083,across))*smooth(-.034,-.019,sy)
            band=(1-smooth(.010,.0128,np.abs(along)))*zone
            tie=np.maximum(tie,band)
            tangent_axis=axis-n*(n@axis)[:,None]
            bead+=tangent_axis*(np.sign(along)*.23*np.exp(-((np.abs(along)-.0097)/.0037)**2)*zone)[:,None]
        def front_phase(q):
            a,b,c=q.T
            az=np.arctan2(a,-b)
            el=np.arctan2(c-.807,np.maximum(.015,np.hypot(a,b)))
            return 13*az+2.4*el+.7*np.sin(2*el+az)
        front_ph,front_grad=flow(front_phase)
        front=(smooth(.044,.16,-sy)*(1-smooth(1.01,1.035,sz)))
        outer=smooth(.180,.235,np.abs(sx))*smooth(-.066,-.018,sy)*(1-smooth(.976,1.026,sz))
        fringe=front*(1-bang)
        curl=np.maximum(tail,outer)
        absolute=fit.normalize(n+bead+.87*rear[:,None]*perturb-.12*curl[:,None]*tail_grad-
                               .12*bang[:,None]*bang_grad-.105*fringe[:,None]*front_grad)
        pigment_variation=(.052*(curl*np.cos(tail_ph)+bang*np.cos(bang_ph)+fringe*np.cos(front_ph))+
               rear*(.048*np.cos(phi)+.012*np.cos(2*phi)))
        base=np.array([.455,.247,.187])+(np.array([.053,.045,.036])*
             smooth(.638,.994,sz)[:,None])
        hair=base*(1+pigment_variation)[:,None]
        ribbons=np.array([.49,.138,.642])+.065*smooth(.930,1.015,sz)[:,None]
        atlas[y,x]=hair*(1-tie[:,None])+ribbons*tie[:,None]
        local=fit.normalize(np.column_stack(((absolute*t).sum(1),(absolute*bt).sum(1),
                                             np.maximum(.28,(absolute*n).sum(1)))))
        normal_atlas[y,x]=.5+.5*local
        mask[y,x] = True
    # Nearest-front dilation for eight full texels and a chestnut fill
    # beyond them. A mip sample outside a chart never reads black.
    for _ in range(8):
        old = mask.copy()
        for dy,dx in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
            dst_s = (slice(max(0,dy),min(1024,1024+dy)),slice(max(0,dx),min(1024,1024+dx)))
            src_s = (slice(max(0,-dy),min(1024,1024-dy)),slice(max(0,-dx),min(1024,1024-dx)))
            grow = old[src_s] & ~mask[dst_s]
            atlas[dst_s][grow] = atlas[src_s][grow]
            normal_atlas[dst_s][grow] = normal_atlas[src_s][grow]
            mask[dst_s] |= grow
    atlas[~mask]=(.45,.256,.204)
    normal_atlas[~mask]=(.5,.5,1)
    path = WORK/'Chestnut.png'
    write_png(path, atlas)
    im = bpy.data.images.load(str(path), check_existing=False)
    im.pack()
    im.filepath = '//Chestnut.png'
    mat = bpy.data.materials.new('Chestnut hair and violet ribbons')
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Roughness'].default_value = .52
    bs.inputs['Metallic'].default_value = 0
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = im
    mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    normal_path=WORK/'Strand relief.png'
    write_png(normal_path,normal_atlas)
    im=bpy.data.images.load(str(normal_path),check_existing=False)
    im.colorspace_settings.name='Non-Color'
    im.pack()
    im.filepath='//Strand relief.png'
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image=im
    normal_node=mat.node_tree.nodes.new('ShaderNodeNormalMap')
    mat.node_tree.links.new(tex.outputs['Color'],normal_node.inputs['Color'])
    mat.node_tree.links.new(normal_node.outputs['Normal'],bs.inputs['Normal'])
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def build():
    bpy.ops.wm.open_mainfile(filepath=str(R2/'hair_twintails_v2.blend'))
    sc = bpy.context.scene
    obj, arm = sc.objects['Hair_Twintails'], sc.objects['Armature']
    donor = obj.data.copy()
    sculpt(obj)
    surface_color(obj, donor)
    bpy.data.meshes.remove(donor)
    heads, necks = [obj.vertex_groups.new(name=name) for name in (bob.HEAD,bob.NECK)]
    for v in obj.data.vertices:
        x,y,z = v.co
        w = .105*bob.smooth(-.008,.095,y)*(1-bob.smooth(.652,.760,z))
        heads.add([v.index],1-w,'REPLACE')
        if w>0:
            necks.add([v.index],w,'REPLACE')
    active(obj)
    arm.hide_set(False)
    arm.select_set(True)
    obj.parent=None
    skin=obj.modifiers.new('Master skin','ARMATURE')
    skin.object=arm
    obj.data.name='Chestnut twin tails'
    bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,
                              export_tangents=True,export_animations=False,export_all_influences=False,export_def_bones=False)
    obj.parent=arm
    arm.hide_set(True)
    bpy.data.orphans_purge(do_recursive=True)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print('Exported',sha(GLB),flush=True)


def hair_mask(axis, hair, body):
    rot=(-axis).to_track_quat('-Z','Y')
    dx=rot@Vector((1,0,0))
    dy=rot@Vector((0,1,0))
    pitch=fit.FRAMING/fit.PIXELS
    start=fit.CAMERA_TARGET+2*axis-(dx+dy)*(.5*(fit.PIXELS-1)*pitch)
    dx*=pitch
    dy*=pitch
    mask=np.zeros((fit.PIXELS,fit.PIXELS),bool)
    for y in range(fit.PIXELS):
        row=start+dy*y
        for x in range(fit.PIXELS):
            origin=row+dx*x
            h=hair.ray_cast(origin,-axis,3)
            if h[0] is not None:
                mask[y,x]=body.ray_cast(origin,-axis,h[3])[0] is None
    return mask


def render_scene(asset):
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    bpy.ops.import_scene.gltf(filepath=str(asset))
    sc=bpy.context.scene
    bob.cpu_studio(sc)
    cam=bpy.data.objects.new('Orthographic fit',bpy.data.cameras.new('Orthographic fit'))
    sc.collection.objects.link(cam)
    sc.camera=cam
    cam.data.type='ORTHO'
    cam.data.ortho_scale=fit.FRAMING
    return sc,cam


def aim(cam,axis):
    cam.location=fit.CAMERA_TARGET+2*axis
    cam.rotation_euler=(-axis).to_track_quat('-Z','Y').to_euler()


def views():
    sc,cam=render_scene(GLB)
    size=fit.PIXELS
    panels=[]
    boxes={0:('front_hairline', (105,117,464,333)),
           3:('side',(104,107,458,449)),4:('nape',(91,111,481,426))}
    for i,direction in enumerate(fit.VIEWS):
        aim(cam,Vector(direction).normalized())
        sc.render.resolution_x=sc.render.resolution_y=size
        sc.render.use_border=False
        path=WORK/'panel.png'
        sc.render.filepath=str(path)
        bpy.ops.render.render(write_still=True)
        panels.append(png_pixels(path))
        if i in boxes:
            name,(l,t,r,b)=boxes[i]
            sc.render.resolution_x=sc.render.resolution_y=3*size
            sc.render.use_border=sc.render.use_crop_to_border=True
            sc.render.border_min_x,sc.render.border_max_x=l/size,r/size
            sc.render.border_min_y,sc.render.border_max_y=1-b/size,1-t/size
            sc.render.filepath=str(CLOSE/(name+'.png'))
            bpy.ops.render.render(write_still=True)
    write_png(HERE/'fit_views_v3.png', np.vstack((np.hstack(panels[3:]),np.hstack(panels[:3]))))
    pixels()


def pixels():
    result={}
    size=fit.PIXELS
    for tag,folder in [('v2',R2),('v3',HERE)]:
        asset=folder/('hair_twintails_'+tag+'.glb')
        sc,cam=render_scene(asset)
        hair=bob.tree_for(sc.objects['Hair_Twintails'])
        body=bob.tree_for(sc.objects['Base_Body'])
        path=folder/('fit_views_'+tag+'.png')
        sheet=png_pixels(path)
        rows={}
        for i,(name,direction) in enumerate(zip(VIEW_NAMES,fit.VIEWS)):
            mask=hair_mask(Vector(direction).normalized(),hair,body)
            y,x=(1-i//3)*size,(i%3)*size
            rgb=sheet[y:y+size,x:x+size,:3][mask].astype(np.float64)
            linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
            weights=[.2126,.7152,.0722]
            rows[name]=dict(hair_pixels=int(mask.sum()),dark=int((rgb@weights<.12).sum()),
                            linear_dark=int((linear@weights<.12).sum()))
        result[tag]=dict(asset_sha256=sha(asset),sheet_sha256=sha(path),views=rows,
                         total={k:sum(row[k] for row in rows.values()) for k in rows['front']})
    result['closeup_sha256']={p.name:sha(p) for p in CLOSE.glob('*.png')}
    report(CHECKS/'pixels_v3.json', result)
    print('Pixel totals:',result['v2']['total'],result['v3']['total'],flush=True)
    recorded=json.loads((R2/'visual_check.json').read_text())['v2']
    assert sha(R2/'hair_twintails_v2.glb')==recorded['sha256']
    for old in recorded['views']:
        before=result['v2']['views'][old['view']]
        after=result['v3']['views'][old['view']]
        assert (before['hair_pixels'],before['dark'],before['linear_dark'])==(
            old['hair_pixels'],old['near_black_srgb'],old['relative_luminance_lt_12pct'])
        assert after['dark']<before['dark'] and after['linear_dark']<before['linear_dark']


def checker(kind):
    script=CHECKER_DIR/('motion_check_dense.py' if kind=='vertex' else 'motion_check_tri.py')
    out=CHECKS/kind
    out.mkdir(exist_ok=True)

    @bpy.app.handlers.persistent
    def cpu(scene,*unused):
        if scene.camera and scene.camera.name=='c' and scene.render.engine=='BLENDER_WORKBENCH':
            bob.cpu_studio(scene)

    old=sys.argv
    bpy.app.handlers.frame_change_pre.append(cpu)
    try:
        sys.argv=[str(script),'--',str(MASTER),str(CLIPS),str(GLB),str(out)]
        runpy.run_path(str(script),run_name='__main__')
    finally:
        bpy.app.handlers.frame_change_pre.remove(cpu)
        sys.argv=old
    report(out/'provenance.json',dict(asset_sha256=sha(GLB),master_sha256=sha(MASTER),
           corrected_clips_sha256=sha(CLIPS),checker=script.name,checker_sha256=sha(script),
           raw_result_sha256=sha(out/'motion_check.json')))
    rows=json.loads((out/'motion_check.json').read_text())
    assert set(rows)=={'rest',*CLIP_NAMES}
    assert all(n==0 and d>=.0005 for n,d in rows.values()),rows


def motion():
    # Match the supplied checkers' master rebinding and signed vertex
    # convention. The additional sweep measures both gates on every half-step.
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    sc=bpy.context.scene
    arm,body=sc.objects['Armature'],sc.objects['Base_Body']
    before=set(sc.objects)
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    added=set(sc.objects)-before
    g,=[o for o in added if o.name=='Hair_Twintails']
    g.parent=None
    for o in added:
        if o.type=='ARMATURE':
            bpy.data.objects.remove(o)
    for m in list(g.modifiers):
        g.modifiers.remove(m)
    g.parent=arm
    g.modifiers.new('Master skin','ARMATURE').object=arm
    bpy.ops.import_scene.gltf(filepath=str(CLIPS))
    for obj in sc.objects:
        if obj not in (arm,body,g):
            obj.hide_viewport=obj.hide_render=True
    anim=arm.animation_data_create()
    rows={}
    for name in ('rest',*CLIP_NAMES):
        a=None if name=='rest' else bpy.data.actions[name]
        anim.action=a
        if a:
            anim.action_slot=a.slots[0]
            f0,f1=map(int,a.frame_range)
        else:
            f0=f1=1
        worst_v=worst_t=0
        min_d=math.inf
        for tick in range(2*f0,2*f1+1):
            sc.frame_set(tick//2,subframe=(tick%2)*.5)
            dg=bpy.context.evaluated_depsgraph_get()
            be,ge=body.evaluated_get(dg),g.evaluated_get(dg)
            bm,gm=be.to_mesh(),ge.to_mesh()
            xyz=[ge.matrix_world@v.co for v in gm.vertices]
            skin=BVHTree.FromPolygons([be.matrix_world@v.co for v in bm.vertices],[p.vertices[:] for p in bm.polygons])
            shell=BVHTree.FromPolygons(xyz,[p.vertices[:] for p in gm.polygons])
            distances=[]
            for p in xyz:
                q,n,_,_=skin.find_nearest(p)
                distances.append((p-q).dot(n))
            overlaps=len(skin.overlap(shell))
            worst_v=max(worst_v,sum(d<0 for d in distances))
            worst_t=max(worst_t,overlaps)
            if min(distances)<min_d:
                min_d=min(distances)
                min_frame=tick/2
                vertex=distances.index(min_d)
            be.to_mesh_clear()
            ge.to_mesh_clear()
        rows[name]=dict(start=f0,end=f1,samples=2*(f1-f0)+1,max_vertices_inside=worst_v,
                        max_triangle_pairs=worst_t,min_signed_m=min_d,min_frame=min_frame,vertex=vertex)
        print(name,rows[name],flush=True)
    report(CHECKS/'motion_integer_half.json',dict(asset_sha256=sha(GLB),master_sha256=sha(MASTER),
           corrected_clips_sha256=sha(CLIPS),samples=sum(r['samples'] for r in rows.values()),clips=rows))
    assert all(r['max_vertices_inside']==r['max_triangle_pairs']==0 and r['min_signed_m']>=.0005
               for r in rows.values()),rows


def audit_source(doc,blob,prim):
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    hair=bpy.context.scene.objects['Hair_Twintails']
    assert hair.parent.name=='Armature' and len(hair.parent.data.bones)==65
    assert any(m.type=='ARMATURE' and m.object==hair.parent for m in hair.modifiers)
    assert bpy.context.scene.objects.get('Base_Body')
    images={n.image.name:dict(size=list(n.image.size),packed=bool(n.image.packed_file))
            for n in hair.active_material.node_tree.nodes if n.type=='TEX_IMAGE'}
    assert all(v['packed'] and max(v['size'])<=1024 for v in images.values())
    positions={tuple(v.co) for v in hair.data.vertices}
    xyz=bob.accessor(doc,blob,prim['attributes']['POSITION'])
    assert positions==set(map(tuple,np.column_stack((xyz[:,0],-xyz[:,2],xyz[:,1]))))
    occupied=np.zeros((1024,1024),bool)
    overlap=0
    for st in fit.mesh_arrays(hair.data)[4]:
        y,x,w=raster(st,1024)
        if w is not None:
            inside=w.min(1)>1e-6
            y,x=y[inside],x[inside]
            overlap+=int(occupied[y,x].sum())
            occupied[y,x]=True
    assert overlap==0 and all(face.use_smooth for face in hair.data.polygons)
    report(CHECKS/'source.json',dict(blend_sha256=sha(BLEND),asset_sha256=sha(GLB),
           fit_script_sha256=sha(Path(__file__).resolve()),matching_unique_positions=len(positions),
           packed_hair_images=images,overlapping_uv_interior_texels=overlap,color_padding_px=8,
           blend_triangles=len(hair.data.polygons),all_faces_smooth=True))


def audit():
    js="""const fs=require('fs'),v=require('gltf-validator');
    v.validateBytes(new Uint8Array(fs.readFileSync(process.argv[1])),{writeTimestamp:false}).then(
      r=>console.log(JSON.stringify({version:v.version(),...r})),e=>{console.error(e);process.exitCode=1;});"""
    result=json.loads(subprocess.check_output(['node','-e',js,str(GLB)],cwd=bob.REPO,text=True))
    result['asset_sha256']=sha(GLB)
    report(CHECKS/'gltf_validator.json',result)
    assert result['issues']['numErrors']==result['issues']['numWarnings']==0
    doc,blob=bob.read_glb(GLB)
    ref,rblob=bob.read_glb(MASTER.with_name('base_body.glb'))
    def skeleton(doc):
        s,=doc['skins']
        return [(doc['nodes'][i]['name'],[doc['nodes'][j]['name'] for j in doc['nodes'][i].get('children',[])]) for i in s['joints']]
    assert skeleton(doc)==skeleton(ref) and len(skeleton(doc))==65
    assert np.allclose(bob.accessor(doc,blob,doc['skins'][0]['inverseBindMatrices']),
                       bob.accessor(ref,rblob,ref['skins'][0]['inverseBindMatrices']),atol=1e-6,rtol=0)
    mesh,=doc['meshes']
    prim,=mesh['primitives']
    assert not doc.get('animations') and not doc.get('cameras') and not doc.get('extensions',{}).get('KHR_lights_punctual')
    assert sum('mesh' in n for n in doc['nodes'])==1 and 'WEIGHTS_1' not in prim['attributes']
    weights=bob.accessor(doc,blob,prim['attributes']['WEIGHTS_0'])
    tris=doc['accessors'][prim['indices']]['count']//3
    assert np.allclose(weights.sum(1),1,atol=1e-6) and 1000<=tris<=3000
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    obj=bpy.context.scene.objects['Hair_Twintails']
    tex={n.image.name:list(n.image.size) for n in obj.active_material.node_tree.nodes if n.type=='TEX_IMAGE'}
    assert all(max(wh)<=1024 for wh in tex.values()) and all('bufferView' in im for im in doc.get('images',[]))
    bm=bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bm.faces.ensure_lookup_table()
    tree=BVHTree.FromBMesh(bm)
    pairs=sum(i<j and set(bm.faces[i].verts).isdisjoint(bm.faces[j].verts) for i,j in tree.overlap(tree))
    geo=dict(asset_sha256=sha(GLB),triangles=tris,mesh_nodes=1,skins=1,joints=len(skeleton(doc)),
             max_influences=int((weights>0).sum(1).max()),textures=tex,animations=0,
             components=len(bob.connected_faces(bm)),open_edges=sum(e.is_boundary for e in bm.edges),
             non_manifold_edges=sum(not e.is_manifold for e in bm.edges),
             inconsistent_winding_edges=sum(not e.is_contiguous for e in bm.edges),
             self_intersecting_nonadjacent_triangle_pairs=pairs,
             euler_characteristic=len(bm.verts)-len(bm.edges)+len(bm.faces))
    report(CHECKS/'geometry.json',geo)
    print('GEOMETRY',geo,flush=True)
    assert geo['open_edges']==geo['non_manifold_edges']==geo['inconsistent_winding_edges']==0 and geo['max_influences']<=4
    assert geo['components']==1 and pairs==0
    bm.free()
    audit_source(doc,blob,prim)


if __name__=='__main__':
    for folder in (WORK,CHECKS,CLOSE):
        folder.mkdir(exist_ok=True)
    for stage in sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ('build','audit','views','vertex','triangle','motion'):
        if stage in ('vertex','triangle'):
            checker(stage)
        else:
            globals()[stage]()
