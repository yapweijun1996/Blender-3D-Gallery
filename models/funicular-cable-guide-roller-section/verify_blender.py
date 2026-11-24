"""Physical debug for native Blender and independent GLB import."""
import bpy,math,sys,json
from collections import defaultdict,Counter
from mathutils import Vector
from mathutils.bvhtree import BVHTree
p=sys.argv[sys.argv.index('--')+1:]
Y=(-.605,0,.605); ZAX=.216; ZLINE=.35111
def read(imported=False):
    O=bpy.data.objects; D=bpy.context.evaluated_depsgraph_get()
    P=O['INCLINED_SECTION_ORIGIN']
    inv=P.matrix_world.inverted()
    def shape(obj):
        eo=obj.evaluated_get(D);me=eo.to_mesh();M=inv@eo.matrix_world
        v=[M@x.co for x in me.vertices];f=[tuple(q.vertices) for q in me.polygons]
        eo.to_mesh_clear()
        bb=[tuple(fn(vv[i] for vv in v) for i in range(3)) for fn in (min,max)]
        return (BVHTree.FromPolygons(v,f,all_triangles=all(len(q)==3 for q in f)),v,f,bb)
    S={o.name:shape(o) for o in P.children_recursive if o.type=='MESH'}
    def t(k):return S[k][0]
    def fire(k,l,r,maxi=.2):
        return t(k).ray_cast(Vector(l),Vector(r),maxi)[0]
    cloth='One unbroken sculpted centre haul rope'
    v,f=S[cloth][1:3]
    def key(v):return tuple(round(x,5) for x in v)
    C=Counter();A=defaultdict(set)
    for q in f:
        for i,j in zip(q,q[1:]+q[:1]):
            a,b=key(v[i]),key(v[j])
            assert a!=b
            C[tuple(sorted((a,b)))]+=1
            A[a].add(b);A[b].add(a)
    assert set(C.values())=={2} and len(A)-len(C)+len(f)==2,(len(A),len(C),len(f))
    remaining=set(A);front=[remaining.pop()]
    while front:
        q=front.pop()
        for x in A[q]&remaining:remaining.remove(x);front.append(x)
    assert not remaining
    assert abs(S[cloth][3][1][1]-S[cloth][3][0][1]-1.786)<.00002
    lineProbes=0;railProbes=0
    grade=P.matrix_world.to_3x3()@Vector((0,1,0))
    grade=math.degrees(math.atan2(grade.z,grade.y))
    assert 12.9999<grade<13.0001,grade
    below=Vector((0,0,-1))
    support=0;seatProbes=0;cageFit=0;bear=0;boreClear=0;caps=0
    center=[];centerToShoulder=[];gaps=[]
    for yi in range(-43,44):
        u=yi*.0202
        for x in (-.011,0,.011):
            h=fire(cloth,(x,u,.395),below,.070)
            assert h is not None and .367<h.z<.3741,(x,u,h)
            lineProbes+=1
        for x,name in ((-.472,'Continuous left section rail head web and foot'),(.472,'Continuous right section rail head web and foot')):
            hit=fire(name,(x,u,.434),below,.09)
            assert hit is not None and abs(hit.z-.395)<.000003,(u,hit)
            railProbes+=1
    for i,y in enumerate(Y,1):
        sh='CONCAVE_GUIDE_ROLLER_'+str(i)
        assert not t(cloth).overlap(t(sh)),(i,'cloth intersects roller')
        for dy in (-.012,0,.012):
            for j in range(-10,11):
                x=j*.00195
                l0=(x,y+dy,ZLINE)
                p1=fire(cloth,l0,below,.056);p2=fire(sh,l0,below,.056)
                assert p1 is not None and p2 is not None,(i,j,dy,p1,p2)
                g=(p1.z-p2.z)*1000
                assert .05<g<3.1,(i,dy,j,g)
                gaps.append(g);seatProbes+=1
                if j==0 and dy==0:center.append(g)
        at=fire(sh,(0,y,.41),below)
        for x in (-.046,.046):
            shld=fire(sh,(x,y,.41),below)
            assert shld is not None and at is not None and shld.z-at.z>.032
            centerToShoulder.append((shld.z-at.z)*1000)
        axis='One physically sustained transverse axle '+str(i)
        assert not t(axis).overlap(t(sh)),(i,'axle clips machined roller bore')
        for dy in (-.013,0,.013):
            for dz in (-.013,0,.013):
                for u in (-1,1):
                    assert fire(sh,(u*.071,y+dy,ZAX+dz),(-u,0,0),.143) is None
                    boreClear+=1
        for s in (-1,1):
            lock='Original hex anti-rotation hub cap '+str((i,s))
            p=fire(lock,(s*.189,y,ZAX),(-s,0,0),.06)
            assert p is not None and abs(p.x-s*.160)<.000003
            caps+=1
            for n in ('Surface kingpin anticorrosion collar ','Outer machined retaining seat ','Original hex anti-rotation hub cap '):
                assert t(axis).overlap(t(n+str((i,s)))),(i,s,n)
                bear+=1
            foot='Seat base of installed guide fork '+str((i,s))
            riser='Short raised pedestal joined to bridge and fork '+str((i,s))
            bridge='Actual central mounting sleeper bridge '+str(i)
            assert t(riser).overlap(t(foot)) and t(riser).overlap(t(bridge))
            support+=2
            for n in (foot,riser,bridge,'Sculpted upright rectangular bearing cheek '+str((i,s))):
                assert not t(sh).overlap(t(n)),(i,s,n)
                cageFit+=1
    return dict(imported=imported,closedRopeOneShell=True,straightLineRays=lineProbes,matchedRailProfileRays=railProbes,cableTouches=[
       dict(y=Y[i],nearTangentGapMm=x) for i,x in enumerate(center)], cableTroughTestRays=seatProbes,
       groovedSideShoulderMm=(min(centerToShoulder),max(centerToShoulder)),minMaxSampledGapMm=(min(gaps),max(gaps)),
       axleOpenBoreRays=boreClear,coaxialCapHits=caps,physicalAxleSeatJoins=bear,pedestalSupportJoins=support,
       noRollerSupportOverlapChecks=cageFit)
bpy.ops.wm.open_mainfile(filepath=p[0]);a=read()
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=p[1]);b=read(True)
print('M37_GEOMETRY='+json.dumps([a,b]))
