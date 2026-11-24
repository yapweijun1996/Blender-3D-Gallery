"""Read-only geometry evidence for independent display assemblies, not use instructions."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
slug='penang-heritage-kopi-roasting-station'
arg=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=Path(arg[0]) if arg else Path(__file__).resolve().parent
result={}
for lane in ('native','GLB'):
    if lane=='native':bpy.ops.wm.open_mainfile(filepath=str(p/(slug+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(p/'exports'/(slug+'.glb')))
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    def many(prefix):
        return sorted((o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(prefix)),key=lambda o:o.name)
    def one(prefix):
        found=many(prefix)
        assert len(found)==1,(lane,prefix,[o.name for o in found]);return found[0]
    def geom(o):
        e=o.evaluated_get(dg);m=e.to_mesh()
        vs=[e.matrix_world@q.co for q in m.vertices];fs=[tuple(q.vertices) for q in m.polygons];e.to_mesh_clear()
        return vs,fs
    def bv(o):return BVHTree.FromPolygons(*geom(o))
    def bulk(os):
        vs=[];fs=[]
        for o in os:
            va,fa=geom(o);j=len(vs);vs+=va;fs+= [tuple(j+i for i in f) for f in fa]
        return BVHTree.FromPolygons(vs,fs)
    def shot(b,x,d,lim=1):return b.ray_cast(Vector(x),Vector(d),lim)[0]
    def updown(b,x,y,zlo,zhi):
        lo=shot(b,(x,y,zlo),(0,0,1),zhi-zlo);hi=shot(b,(x,y,zhi),(0,0,-1),zhi-zlo)
        assert lo and hi,(lane,x,y,zlo,zhi)
        return (lo.z,hi.z)
    def overlap(a,b):return min(a[1],b[1])-max(a[0],b[0])
    def nearest(a,b):return min(b.find_nearest(v)[3] for v in geom(a)[0])
    cx,cy=-.23,.038
    pot=bv(one('Genuinely hollow'))
    depths=[]
    for r in [0,.062,.120,.196,.241,.273]:
        for az in [0,math.pi/3,math.pi/2,math.pi,3*math.pi/2]:
            h=shot(pot,(cx+r*math.cos(az),cy+r*math.sin(az),.78),(0,0,-1),1)
            assert h and .218<h.z<.554,(lane,r,az,h)
            if r<.196:assert h.z<.27,(lane,r,az,h)
            depths.append((.608-h.z)*1000)
    centralBottom,centralInside=updown(pot,cx,cy,.161,.63)
    assert .039<centralInside-centralBottom<.042,(lane,centralBottom,centralInside)
    brick=many('Individual original curved brick joint')
    assert len(brick)>85
    allBrick=bulk(brick)
    seat=bv(one('Independent forged ring'))
    collar=bv(one('Cast pot seating collar'))
    shellProbe=[]
    for a in [.11,.38,1.31,2.56,3.98,4.65,5.55,5.97]:
        def toward(r):return (cx+r*math.cos(a),cy+r*math.sin(a))
        r=.306
        p0=updown(allBrick,*toward(r),.485,.569)
        p1=updown(seat,*toward(r),.529,.578)
        p2=updown(collar,*toward(r),.545,.579)
        off=tuple(overlap(a,b) for a,b in ((p0,p1),(p1,p2)))
        assert all(.007<x<.030 for x in off),(lane,a,off)
        shellProbe.append([v*1000 for v in off])
    for x in [-.060,0,.060]:
        for z in [.133,.168,.208]:
            origin=(cx+x,cy-.50,z)
            assert not shot(allBrick,origin,(0,1,0),.49),(lane,'false/obstructed mouth',x,z)
            assert any(shot(allBrick,(origin[0]+eps,origin[1],origin[2]),(0,1,0),1.01) for eps in (-.002,0,.002)),(lane,'missing rear cavity wall',x,z)
    upperMesh=bv(one('Low unconnected paddles rack crossbar'))
    shelf=bv(one('Second timber saddle on paddle rack'))
    faces=many('Paired rounded parked hardwood paddle blade')
    arms=many('Separate long wooden parked paddle shaft')
    assert len(faces)==len(arms)==2
    paddleContacts=[]
    for i,(face,arm) in enumerate(zip(faces,arms)):
        x=.338+(.070 if i else -.070)
        faceTree=bv(face)
        support=updown(upperMesh,x,.241,.175,.29)
        foot=shot(faceTree,(x,.242,.230),(0,0,1),.05);assert foot
        seatDepth=support[1]-foot.z
        backRail=nearest(face,shelf)
        neck=nearest(arm,faceTree)
        assert .0002<seatDepth<.0015 and backRail<.007 and neck<.009,(lane,i,seatDepth,backRail,neck)
        paddleContacts.append([seatDepth*1000,backRail*1000,neck*1000])
    spoke=one('Deep open rope groove')
    spoolTree=bv(spoke); rope=one('One genuine stationary rope')
    cord=bv(rope); clip=bv(one('Small independent cord parking cleat'))
    # Open radial profiles into depression in both independently modeled solids.
    rr=[]
    x,y,z=.649,.305,.930
    for j in range(1,24):
        a=j*math.pi/24
        direct=(0,-math.cos(a),-math.sin(a))
        orig=(x,y+.098*math.cos(a),z+.098*math.sin(a))
        outer=shot(cord,orig,direct,.075)
        core=shot(spoolTree,orig,direct,.095)
        assert outer and core,(lane,j)
        ro=(outer-Vector((x,y,z))).length; rs=(core-Vector((x,y,z))).length
        assert .0545<ro<.0577 and .0465<rs<.04715,(lane,j,ro,rs)
        rr.append([rs*1000,ro*1000])
    endpoint=shot(cord,(x,.205,.136),(0,0,1),.040);assert endpoint
    cp=updown(clip,x,.205,.115,.173)
    cc=cp[1]-endpoint.z
    assert .003<cc<.012,(lane,'unseated cord end',cc)
    shaft=bv(one('Continuous axle through spool'))
    for sig in [-1,1]:
        x1=x+sig*.083
        ray=shot(shaft,(x1,y,z+.045),(0,0,-1),.09)
        assert ray and ray.z>z+.01
    result[lane]=dict(pot_cavity_depth_mm=[min(depths),max(depths)],pot_base_thickness_mm=(centralInside-centralBottom)*1000,
                      pot_bearing_probes=len(shellProbe),actual_arch_through_rays=9,actual_bricks=len(brick),
                      paired_paddle_foot_back_and_shaft_measurements_mm=paddleContacts,
                      actual_independent_rope_arc_rays=len(rr),rope_park_clip_embed_mm=cc*1000)
print(json.dumps(result,indent=2))
