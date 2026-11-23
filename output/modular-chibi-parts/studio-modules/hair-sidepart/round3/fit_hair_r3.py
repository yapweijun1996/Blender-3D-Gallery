"""Rebuild and check the boy's side-part. Run with Blender 5; see NOTES.md."""
from pathlib import Path
import hashlib
import json
import math
import os
import subprocess
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
R2 = HERE.parent / "round2"
SOURCE = R2 / "hair_sidepart_v2.blend"
ORIGINAL = R2 / "hair_sidepart_v2.glb"
GLB = HERE / "hair_sidepart_v3.glb"
CACHE = HERE / ".runtime"
CACHE.mkdir(exist_ok=True)
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE.parent))
import fit_hair as v1
from fit_hair import ROOT, bob

MOTION = v1.PARTS / "body-fix/motion_fixed.glb"
SCRATCH = Path(os.environ.get("HAIR_CHECKER_DIR",
    "/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular"))
VIEWS = [(0,-1,0), (.6,-1,.08), (-.6,-1,.08), (1,0,.03), (0,1,.06), (-1,0,.03)]
LABELS = ["front", "three_quarter_left", "three_quarter_right", "left", "back", "right"]
ANGLES = np.arange(360) * math.pi / 180
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



def interpolate_curve(keys, samples):
    """Catmull-Rom interpolation through the combing guides."""
    keys = np.asarray(keys, dtype=float)
    u = np.linspace(0, len(keys)-1, samples)
    idx = np.minimum(u.astype(int), len(keys)-2)
    t = (u-idx)[:,None]
    p0,p1 = keys[np.maximum(0,idx-1)],keys[idx]
    p2,p3 = keys[idx+1],keys[np.minimum(len(keys)-1,idx+2)]
    return .5*((2*p1) + (-p0+p2)*t + (2*p0-5*p1+4*p2-p3)*t*t
               + (-p0+3*p1-3*p2+p3)*t*t*t)


def hair_ridge(directions, guide, top_width, depth):
    """A soft, tapered relief following a hand-combed spherical spline."""
    points = interpolate_curve(guide, 136)
    a,e = np.radians(points).T
    centers = np.column_stack((np.sin(a)*np.cos(e), -np.cos(a)*np.cos(e), np.sin(e)))
    # Smoothly tapered amplitudes avoid a round bump at the end of a lock.
    s = np.linspace(0,1,len(points))
    taper = ramp(0,.19,s)*(1-ramp(.755,1,s))
    width = np.radians(top_width*(.45+.55*taper)*(1-.29*ramp(.63,1,s)))
    taper *= 1-.29*ramp(.49,.82,s)
    result = np.zeros(directions.shape[:2],dtype="f")
    for point, strength, sigma in zip(centers,taper,width):
        chord_sq = np.maximum(0,2-2*(directions @ point))
        height = strength*np.exp(-.5*chord_sq/(sigma*sigma))
        result = np.maximum(result,height)
    return result * depth


class CombedSurface:
    def __init__(self, obj, skin):
        old = bob.tree_for(obj)
        hem = read_hem(old)
        hem = blur(hem[None,:], 1.8, 0)[0]
        # Fair the nape in angular space; the old decimated rim printed flat
        # segments into both the contour and the interpolated vertex normals.
        for i,a in enumerate(ANGLES):
            az = abs((a+math.pi)%math.tau-math.pi)
            if az <= math.radians(100):
                continue
            target_z = .7148 + .049*(1+math.cos(a))**1.25
            elevation = float(hem[i])
            for _ in range(5):
                d = direction(a,elevation)
                radius = (v1.get_surface(skin,d,.0045)-ROOT).length+.0014
                elevation = math.asin((target_z-ROOT.z)/radius)
            hem[i] += (elevation-hem[i])*ramp(100,127,math.degrees(az))
        az_deg=np.abs((np.degrees(ANGLES)+180)%360-180)
        # Bring the sideburn onto the forward-facing temple. At grazing
        # angles the old point trapped a dark line of skin behind the hem.
        signed=(np.degrees(ANGLES)+180)%360-180
        canonical_hem=hem.copy()
        forward=10*np.exp(-.5*((az_deg-59)/16)**2)
        hem=at_angle(hem,np.radians(signed+np.sign(signed)*forward))
        hem+=np.radians(2.8)*np.exp(-.5*((az_deg-57)/9)**2)
        self.hem = hem
        cols, rows = 384, 209
        self.cols,self.rows = cols,rows
        a = np.linspace(-math.pi,math.pi,cols,endpoint=False)
        lo = at_angle(hem,a)
        t = np.linspace(0,1,rows)[:,None]
        e = lo+t*(math.pi/2-lo)
        old_lo=at_angle(canonical_hem,a)
        old_e=old_lo+t*(math.pi/2-old_lo)
        self.lo = lo
        dirs = np.stack(np.broadcast_arrays(np.sin(a)*np.cos(e),-np.cos(a)*np.cos(e),np.sin(e)),axis=-1)
        envelope,skull = np.empty(e.shape),np.empty(e.shape)
        for j,i in np.ndindex(e.shape):
            d = Vector(dirs[j,i])
            old_d=direction(a[i],old_e[j,i])
            start=ROOT+.55*old_d
            _,_,_,dh=old.ray_cast(start,-old_d,.55)
            p = v1.get_surface(skin,d,.0045)
            skull[j,i] = (p-ROOT).length
            envelope[j,i] = .55-dh if dh is not None else (v1.get_surface(skin,old_d,.0045)-ROOT).length+.006
        # Keep R2's overall volume. A broad filter removes its individual
        # folded locks before the new lower-frequency sweep is laid in.
        dome = resample(blur(envelope,12,14),np.arange(cols)[None,:],
                        (e-old_lo)/(math.pi/2-old_lo)*(rows-1))
        front = .5+.5*np.cos(a)
        above = np.degrees(e-lo)
        crown = ramp(2,21,above)
        dome -= .0060*front*crown
        # Guide order follows the natural flow away from the offset part.
        # The three banks on the long side lift at the far temple. Two shorter
        # banks return toward the opposite ear. All live in the same radius field.
        guides = [
            ([(35,26),(26,35),(11,34),(-4,24),(-21,13),(-43,9),(-66,17)],6.3,.0177),
            ([(42,36),(29,49),(7,52),(-16,42),(-37,30),(-59,26),(-81,33)],8.7,.0188),
            ([(52,48),(40,63),(12,71),(-24,65),(-52,53),(-77,46),(-99,52)],9.2,.0150),
            ([(29,25),(41,29),(54,24),(65,12),(73,1),(78,-5)],5.6,.0125),
            ([(39,38),(53,44),(69,37),(79,23),(88,11),(98,6)],6.6,.0150),
            ([(55,54),(75,57),(92,45),(104,29),(114,19)],8.2,.0110),
        ]
        banks = [hair_ridge(dirs, guide, width*.61, depth) for guide,width,depth in guides]
        # A smooth union keeps the crease between neighbouring broad banks;
        # adding overlapping Gaussian profiles would erase the side part.
        relief = np.power(sum(bank**4 for bank in banks),.25)
        part = hair_ridge(dirs, [(28,19),(32,26),(37,34),(43,44),(52,55),(67,66),(95,74)], 3.5,.0027)
        # Roll under to a narrow contact edge. Rapidly increasing thickness at
        # the front made a dark ledge over the brow on the previous haircut.
        blend = ramp(0,15+8*(1-front),above)
        foundation = np.maximum(dome,skull+.003)
        rear = ramp(90,140,np.abs(np.degrees(a)))
        r = np.clip(above/(15+8*(1-front)),0,1)
        blend += ((1-(1-r)**2)-blend)*rear
        radius = (skull+.0014)*(1-blend)+foundation*blend
        # An inset, skin-following return at the temples closes the narrow
        # line of sight under the sideburn while preserving motion clearance.
        tight=np.array([(v1.get_surface(skin,direction(az,el),.00125)-ROOT).length
                        for az,el in zip(a,lo)])+.00048
        fit=ramp(25,49,np.abs(np.degrees(a)))*(1-ramp(75,97,np.abs(np.degrees(a))))*(1-ramp(0,10,above))
        radius+=(tight[None,:]-(skull[0]+.0014)[None,:])*fit
        radius += (relief-part)*ramp(.3,8,above)
        temple = np.exp(-.5*((np.abs(np.degrees(a))-68)/7)**2)
        radius += .0032*temple*ramp(.8,6,above)*(1-ramp(10,24,above))
        # Fair the distal crest where a grazing profile ray formerly caught
        # a single triangular glint on the left crown.
        fade=np.exp(-.5*((np.degrees(a)+66)/12)**2-.5*((np.degrees(e)-50)/6.0)**2)
        radius+=(blur(radius,4.4,6)-radius)*fade*.3
        pole = ramp(82,90,np.degrees(e))
        radius += pole*(radius.mean(axis=1,keepdims=True)-radius)
        self.radius = radius
        self.relief = relief
        p = dirs*radius[:,:,None]
        du = np.roll(p,-1,axis=1)-np.roll(p,1,axis=1)
        dv = np.gradient(p,axis=0)
        field = np.cross(du,dv)
        field /= np.maximum(1.e-12,np.linalg.norm(field,axis=-1,keepdims=True))
        field[-1,:] = (0,0,1)
        self.normals = blur(field,1.65,1.9)

    def level(self,a):
        return at_angle(self.hem,a)

    def sample(self,field,a,t):
        return resample(field,(a/math.tau+.5)*self.cols,np.asarray(t)*(self.rows-1))

    def point(self,a,t):
        lo = self.level(a)
        e = lo+t*(math.pi/2-lo)
        return ROOT+direction(a,e)*self.sample(self.radius,a,t)


def upper_shell(obj,surface,cut,budget):
    verts,faces = [],[]
    count = 192
    for t in np.linspace(cut,1,91)[:-1]:
        for i in range(count):
            a = math.tau*i/count-math.pi
            verts.append(surface.point(a,t))
        if len(verts)>count:
            row = len(verts)-2*count
            for i in range(count):
                k=(i+1)%count
                faces.extend([(row+i,row+k,row+count+i),(row+k,row+count+k,row+count+i)])
    pole = len(verts)
    verts.append(surface.point(0,1))
    for i in range(count):
        faces.append((pole-count+i,pole-count+(i+1)%count,pole))
    mesh=bpy.data.meshes.new("Exterior sculpt")
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    obj.data = mesh
    active(obj)
    v1.decimate(obj,budget)
    bm=bmesh.new()
    bm.from_mesh(obj.data)
    # A boundary on the editable sculpt is kept only until the continuous
    # turned-under lip and inner crown have been stitched to it.
    for edge in [e for e in bm.edges if e.is_boundary]:
        x,y=edge.verts
        delta=(polar(y.co)[0]-polar(x.co)[0]+math.pi)%math.tau-math.pi
        pieces=int(math.ceil(abs(delta)/math.radians(4.0)))
        tail=x
        for piece in range(1,pieces):
            _,tail=bmesh.utils.edge_split(bm.edges.get((tail,y)),tail,1/(pieces-piece+1))
    boundary,=v1.rim_loops(bm)
    for v in boundary:
        v.co=surface.point(polar(v.co)[0],cut)
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
    bm.verts.index_update()
    bm.to_mesh(obj.data)
    verts=[v.co.copy() for v in obj.data.vertices]
    faces=[tuple(f.vertices) for f in obj.data.polygons]
    border=sorted([v.index for v in boundary],key=lambda i: polar(verts[i])[0])
    edges={tuple(sorted(ed.vertices[:])) for ed in obj.data.edges}
    assert all(tuple(sorted(pair)) in edges for pair in zip(border,border[1:]+border[:1]))
    bm.free()
    return verts,faces,border


def join_courses(verts,faces,upper,lower):
    def angles(row):
        values=[polar(verts[i])[0] for i in row]
        values=np.unwrap(values)
        values-=math.tau*round((values[0]+math.pi)/math.tau)
        return np.append(values,values[0]+math.tau)
    a,b=angles(upper),angles(lower)
    i=j=0
    while i<len(upper) or j<len(lower):
        x,y=upper[i%len(upper)],lower[j%len(lower)]
        if j==len(lower) or (i<len(upper) and a[i+1]<=b[j+1]):
            faces.append((x,y,upper[(i+1)%len(upper)]))
            i+=1
        else:
            faces.append((x,y,lower[(j+1)%len(lower)]))
            j+=1


def support_lining(mesh,skin,inner_start):
    # A vertex can clear the skull while the chord to its neighbour cuts
    # through it. Test triangle interiors as well as edge subdivisions.
    for _ in range(8):
        offsets=np.zeros(len(mesh.vertices))
        for face in mesh.polygons:
            ids=tuple(face.vertices)
            if min(ids)<inner_start:
                continue
            a,b,c=[mesh.vertices[i].co for i in ids]
            probes=[(a+b+c)/3]
            for p,q in ((a,b),(b,c),(c,a)):
                probes.extend(p.lerp(q,t) for t in (.25,.5,.75))
            for p in probes:
                hit,normal,_,_=skin.find_nearest(p)
                az=abs(math.degrees(polar(p)[0]))
                goal=.0010+.0015*ramp(50,100,az)
                deficit=goal-(p-hit).dot(normal)
                if deficit>0:
                    ray=(p-ROOT).normalized()
                    amount=(deficit+.00018)/max(.40,normal.dot(ray))
                    for i in ids:
                        offsets[i]=max(offsets[i],amount)
        if not np.any(offsets):
            break
        for i in np.flatnonzero(offsets):
            v=mesh.vertices[int(i)]
            v.co+=(v.co-ROOT).normalized()*min(.006,offsets[i])
    mesh.update()


def support_margin(mesh,skin,surface,inner_start):
    # Preserve the whole lip's thickness. Pushing just one of two close
    # layers can put the lining through the exterior on the ear cutouts.
    angles=np.array([polar(v.co)[0] for v in mesh.vertices])
    elevations=np.array([polar(v.co)[1] for v in mesh.vertices])
    hem=surface.level(angles)
    levels=(elevations-hem)/(math.pi/2-hem)
    edge_faces=[f for f in mesh.polygons if min(f.vertices)<inner_start
                and max(levels[list(f.vertices)])<.105]
    for _ in range(5):
        sector=np.zeros(360)
        for face in edge_faces:
            ids=list(face.vertices)
            a,b,c=[mesh.vertices[i].co for i in ids]
            probes=[(a+b+c)/3]
            for p,q in ((a,b),(b,c),(c,a)):
                probes.extend(p.lerp(q,f) for f in (.15,.33,.5,.67,.85))
            correction=0
            for p in probes:
                hit,normal,_,_=skin.find_nearest(p)
                deficit=.00065-(p-hit).dot(normal)
                if deficit>0:
                    correction=max(correction,(deficit+.0001)/max(.38,normal.dot((p-ROOT).normalized())))
            if correction:
                for idx in ids:
                    angle=math.degrees(angles[idx])
                    for j in range(round(angle)-5,round(angle)+6):
                        sector[j%360]=max(sector[j%360],correction)
        if not np.any(sector):
            break
        shift=at_angle(blur(sector[None,:],1,0)[0],angles)*(1-ramp(.083,.16,levels))
        for i in np.flatnonzero(shift):
            v=mesh.vertices[int(i)]
            v.co+=(v.co-ROOT).normalized()*shift[i]
        mesh.update()


def build():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    obj=bpy.data.objects["Hair_Sidepart"]
    arm=obj.parent
    obj.modifiers.clear()
    obj.vertex_groups.clear()
    skin=bob.tree_for(bpy.data.objects["Base_Body"],head_only=True)
    surface=CombedSurface(obj,skin)
    cut=.029
    verts,faces,border=upper_shell(obj,surface,cut,1410)
    upper_ids=set(range(len(verts)))
    # The lip is a smooth semicircle in radial/elevation cross-section.
    # Angle-dependent clearance follows the forehead closely and preserves
    # extra room behind the ears for animated neck motion.
    courses=[("roll",0,96),("roll",math.pi*.36,96),
             ("roll",math.pi*.70,96),("roll",math.pi,96),
             ("lining",.075,72),("lining",.14,48),("lining",.215,48),("lining",.30,40),("lining",.40,36),
             ("lining",.59,32),("lining",.77,24),("lining",.91,16)]
    inner_start=None
    for zone,t,count in courses:
        if zone=="lining" and inner_start is None:
            inner_start=len(verts)
        row=[]
        # Spend more angular samples where the temple curve turns sharply.
        angles=np.linspace(-math.pi,math.pi,721)
        density=1+1.15*np.exp(-.5*((np.abs(np.degrees(angles))-64)/9)**2)
        arc=np.r_[0,np.cumsum((density[1:]+density[:-1])*.5)]
        for a in np.interp(np.arange(count)/count,arc/arc[-1],angles):
            lo=surface.level(a)
            if zone=="roll":
                d=direction(a,lo)
                inner_clear=.00165-.00074*ramp(25,49,abs(math.degrees(a)))+.00354*ramp(75,97,abs(math.degrees(a)))
                outside=(surface.point(a,0)-ROOT).length
                inside=(v1.get_surface(skin,d,inner_clear)-ROOT).length
                outer=max(outside,inside+.00075+.0007*ramp(75,97,abs(math.degrees(a))))
                r=(outer+inside+(outer-inside)*math.cos(t))*.5
                e=lo-.5*(outer-inside)/r*math.sin(t)
                p=ROOT+direction(a,e)*r
            else:
                # Level out the inner courses above the ear so neighbouring
                # columns do not produce long skewed chords through the head.
                e=lo+(math.pi/2-lo)*t
                common=math.radians(90*t)
                e+=(common-e)*ramp(.09,.40,t)
                clr=.0075 if t>=.215 else .0020+.0024*ramp(75,97,abs(math.degrees(a)))
                p=v1.get_surface(skin,direction(a,e),clr)
            row.append(len(verts))
            verts.append(p)
        join_courses(verts,faces,border,row)
        border=row
    pole=len(verts)
    verts.append(v1.get_surface(skin,Vector((0,0,1)),.0055))
    for i,x in enumerate(border):
        faces.append((border[(i+1)%len(border)],x,pole))
    mesh=bpy.data.meshes.new("Combed side part with rolled hairline")
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    bm=bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    assert all(e.is_manifold and e.is_contiguous for e in bm.edges)
    assert bm.calc_volume(signed=True)>0 and len(bm.verts)==len(verts)
    bm.to_mesh(mesh)
    bm.free()
    obj.data=mesh
    assert all((v.co-verts[v.index]).length<.000001 for v in mesh.vertices)
    support_lining(mesh,skin,inner_start)
    support_margin(mesh,skin,surface,inner_start)
    for f in mesh.polygons:
        f.use_smooth=True
    mesh.update()
    # Use the continuous sculpt derivative on the upper dome and the true
    # rolled geometry normal on the rim. The transition is above the hem.
    normals=[]
    colors=mesh.color_attributes.new(name="Chestnut",type="FLOAT_COLOR",domain="POINT")
    for v in mesh.vertices:
        a,e=polar(v.co)
        lo=surface.level(a)
        t=np.clip((e-lo)/(math.pi/2-lo),0,1)
        n=v.normal.copy()
        if v.index in upper_ids:
            target=Vector(surface.sample(surface.normals,a,t)).normalized()
            n=n.lerp(target,float(ramp(.018,.075,t))).normalized()
        normals.append(tuple(n))
        # Linear-light chestnut. There is a single continuous colour for
        # every shared position, including the rim and both sides of the part.
        copper=.72+.19*ramp(0,.85,t)+.42*surface.sample(surface.relief,a,t)/.022
        colors.data[v.index].color=(.170*copper,.043*copper,.026*copper,1)
    mesh.normals_split_custom_set_from_vertices(normals)
    mat=bpy.data.materials.new("Chestnut satin")
    mat.use_nodes=True
    shader=mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Roughness"].default_value=.47
    shader.inputs["Metallic"].default_value=.08
    attr=mat.node_tree.nodes.new("ShaderNodeVertexColor")
    attr.layer_name=colors.name
    mat.node_tree.links.new(attr.outputs["Color"],shader.inputs["Base Color"])
    mesh.materials.append(mat)
    h,n=[obj.vertex_groups.new(name=name) for name in (v1.HEAD,v1.NECK)]
    for v in mesh.vertices:
        x,y,z=v.co
        w=.033*v1.smooth(.002,.09,y)*(1-v1.smooth(.695,.795,z))
        w=w if w>=.0001 else 0
        h.add([v.index],1-w,"REPLACE")
        if w:
            n.add([v.index],w,"REPLACE")
    obj.modifiers.new("Master skeleton","ARMATURE").object=arm
    active(obj)
    arm.hide_set(False)
    arm.select_set(True)
    obj.parent=None
    bpy.ops.export_scene.gltf(filepath=str(GLB),export_format="GLB",use_selection=True,
                              export_animations=False,export_def_bones=False,export_all_influences=False)
    obj.parent=arm
    arm.hide_set(True)
    bpy.data.orphans_purge(do_recursive=True)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(GLB.with_suffix(".blend")),compress=True)
    print("FINAL MESH",len(mesh.vertices),len(mesh.polygons),digest(GLB),flush=True)


def views():
    sc,hair=load_scene(GLB)
    cam=set_camera(sc)
    body_tree=bob.tree_for(sc.objects["Base_Body"])
    hair_tree=bob.tree_for(hair)
    sheet=np.empty((1040,1560,4),"f")
    stats={}
    for i,d in enumerate(VIEWS):
        aim(cam,d)
        sc.render.filepath=str(CACHE/"tile.png")
        bpy.ops.render.render(write_still=True)
        tile=image_array(sc.render.filepath)
        y,x=(1-i//3)*520,(i%3)*520
        sheet[y:y+520,x:x+520]=tile
        mask=visible_mask(cam,body_tree,hair_tree)
        rgb=tile[:,:,:3][mask]
        linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
        stats[LABELS[i]]=dict(hair_pixels=int(mask.sum()),dark=int((rgb@[.2126,.7152,.0722]<.12).sum()),
                              linear_dark=int((linear@[.2126,.7152,.0722]<.12).sum()))
    save_pixels(HERE/"fit_views_v3.png",sheet)
    info=dict(asset_sha256=digest(GLB),views=stats)
    (HERE/"pixels_v3.json").write_text(json.dumps(info,indent=2)+"\n")


def closeups():
    sc,_=load_scene(GLB)
    cam=set_camera(sc)
    sc.render.resolution_x=sc.render.resolution_y=1040
    sc.render.use_border=sc.render.use_crop_to_border=True
    for name,idx,box in [("front_hairline",0,(52,69,465,363)),("side",5,(43,39,490,371)),
                         ("nape",4,(48,274,472,397))]:
        aim(cam,VIEWS[idx])
        x0,y0,x1,y1=box
        sc.render.border_min_x,sc.render.border_max_x=x0/520,x1/520
        sc.render.border_min_y,sc.render.border_max_y=1-y1/520,1-y0/520
        sc.render.filepath=str(HERE/f"closeup_{name}.png")
        bpy.ops.render.render(write_still=True)
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
    assert 1000<=triangles<=3000
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
    assert not doc.get("animations") and not doc.get("cameras")
    assert not doc.get("extensions",{}).get("KHR_lights_punctual")
    assert len(doc["materials"])==1
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
    bpy.ops.wm.open_mainfile(filepath=str(GLB.with_suffix(".blend")))
    editable=bpy.data.objects["Hair_Sidepart"]
    rig=editable.parent
    editable.data.calc_loop_triangles()
    assert len(editable.data.loop_triangles)==triangles
    assert rig.type=="ARMATURE" and len(rig.data.bones)==65
    assert any(mod.type=="ARMATURE" and mod.object==rig for mod in editable.modifiers)
    assert all(poly.use_smooth for poly in editable.data.polygons)
    assert all(n.image.packed_file for n in editable.active_material.node_tree.nodes if n.type=="TEX_IMAGE")
    checks.update(editable_blend_reopened=True,mesh_nodes=1,animation_clips_in_export=0)
    js="""const fs=require('fs'),v=require('gltf-validator');const [input,out]=process.argv.slice(1);
    v.validateBytes(new Uint8Array(fs.readFileSync(input)),{uri:require('path').basename(input)}).then(r=>{
    fs.writeFileSync(out,JSON.stringify(r,null,2)); if(r.issues.numErrors||r.issues.numWarnings)process.exitCode=1;
    }).catch(e=>{console.error(e);process.exitCode=1});"""
    subprocess.run(["node","-e",js,str(GLB),str(HERE/"khronos_validation.json")],cwd=v1.REPO,check=True)
    (HERE/"geometry_check.json").write_text(json.dumps(checks,indent=2)+"\n")
    print(checks,flush=True)



def motion(kind):
    # Run supplied setup and measurement code verbatim. The supplied drivers
    # skip subframes, round clearance and use a sparse stride for overlaps.
    # Drive their original measure() at all requested poses instead.
    filename={"vertex":"motion_check_dense.py","tri":"motion_check_tri.py"}[kind]
    source=SCRATCH/filename
    checker_source=source.read_text()
    setup,driver=checker_source.split("arm.animation_data_create();res={}",1)
    assert "def measure():" in setup and "for name in('walk'" in driver
    scope={"__name__":"checker","__file__":str(source)}
    out=HERE/f"check_{kind}"
    out.mkdir(exist_ok=True)
    old_args=sys.argv
    sys.argv=[str(source),"--",str(v1.MASTER),str(MOTION),str(GLB),str(out)]
    try:
        exec(compile(setup,str(source),"exec"),scope)
    finally:
        sys.argv=old_args
    arm,sc=scope["arm"],scope["sc"]
    imported=scope["src"]
    imported_slots={strip.action.name:strip.action for track in imported.animation_data.nla_tracks
                    for strip in track.strips if strip.action}
    if imported.animation_data.action:
        a=imported.animation_data.action
        imported_slots[a.name]=a
    clips=("walk","run","wave","jump","idle","nod","dance")
    assert all(name in imported_slots for name in clips),list(imported_slots)
    arm.animation_data_create()
    # A master with pre-existing animation would invalidate an isolated clip.
    assert not list(arm.animation_data.nla_tracks)
    meta=dict(asset_sha256=digest(GLB),master_sha256=digest(v1.MASTER),clips_sha256=digest(MOTION),
              checker=filename,checker_sha256=digest(source),step_frames=.5,results={})
    for name in ("rest",*clips):
        action=imported_slots.get(name)
        arm.animation_data.action=action
        if action:
            arm.animation_data.action_slot=action.slots[0]
            f0,f1=action.frame_range
            assert float(f0).is_integer() and float(f1).is_integer()
            steps=range(int(f0)*2,int(f1)*2+1)
        else:
            steps=[2]
        peak,minimum,worst_frame=0,float("inf"),None
        for step in steps:
            sc.frame_set(step//2,subframe=(step%2)*.5)
            count,clearance=scope["measure"]()
            peak=max(peak,count)
            if clearance<minimum:
                minimum,worst_frame=clearance,step/2
        meta["results"][name]=dict(samples=len(steps),first=steps[0]/2,last=steps[-1]/2,
                                  max_count=peak,min_signed_m=minimum,min_frame=worst_frame)
        print(kind,name,meta["results"][name],flush=True)
    (out/"motion_check.json").write_text(json.dumps(meta,indent=2)+"\n")
    assert all(r["max_count"]==0 and r["min_signed_m"]>=.0005 for r in meta["results"].values()),meta


if __name__=="__main__":
    steps=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else ["build","audit","vertex","tri","views","closeups"]
    for step in steps:
        if step in ("vertex","tri"):
            motion(step)
        else:
            {"build":build,"audit":audit,"views":views,"closeups":closeups}[step]()
