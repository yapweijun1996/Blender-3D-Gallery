"""Actual slat voids, downward slot, and two transverse hollow cages."""
import bpy,math,sys,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from collections import defaultdict
args=sys.argv[sys.argv.index('--')+1:]
X,Y,Z=(Vector(v) for v in ((1,0,0),(0,1,0),(0,0,1)))
def verify(imported):
    D=bpy.context.evaluated_depsgraph_get()
    O=bpy.data.objects
    def shape(ob):
        eo=ob.evaluated_get(D);me=eo.to_mesh();T=eo.matrix_world
        v=[T@p.co for p in me.vertices];f=[tuple(q.vertices) for q in me.polygons]
        eo.to_mesh_clear()
        b=BVHTree.FromPolygons(v,f,all_triangles=all(len(x)==3 for x in f))
        lo,hi=(tuple(fun(q[i] for q in v) for i in range(3)) for fun in (min,max))
        return b,(lo,hi),v,f
    mains=('SAMPLE_ENTRANCE_HEADER','AIR_CURTAIN_SECTIONED_HOUSING','PAIR_OF_STATIC_CROSS_FLOW_BLOWERS')
    all_obs=[o for n in mains for o in O[n].children_recursive if o.type=='MESH']
    s={o.name:shape(o) for o in all_obs}
    def t(name):return s[name][0]
    def clear(orig,dir,d,objects):
        for name in objects:
            assert t(name).ray_cast(orig,dir,d)[0] is None,(tuple(orig),tuple(dir),name)
    names=list(s)
    slit=0;lip=0
    for i in range(-18,19):
        x=i*.032
        for y in (-.030,-.018,0,.019,.031):
            clear(Vector((x,y,.202)),Z,.129,names)
            clear(Vector((x,y,.331)),-Z,.129,names)
            slit+=2
        for y, obj in ((-.058,'Continuous front outlet lip with no texture stand-in'),(.058,'Connected rear curved plenum and rear outlet lip')):
            h,n,_,_=t(obj).ray_cast(Vector((x,y,.223)),Z,.090)
            assert h is not None and .245<h.z<.267,(x,y,h,obj)
            lip+=1
    grille=0;material=0
    for j in range(10):
        z=.335+(j+.50)*.0184
        for i in range(7):
            x=-.610+.081*i
            clear(Vector((x,-.197,z)),Y,.088,names)
            clear(Vector((x,-.109,z)),-Y,.088,names)
            grille+=2
    for j in range(11):
        for i in range(7):
            x=-.61+.081*i
            h,_,_,_=t('Genuinely separated front intake slat '+str(j)).ray_cast(Vector((x,-.197,.335+j*.0184)),Y,.089)
            assert h is not None,(j,i,x)
            material+=1
    inside=0;bladeHits=0;annularAttachments=0;shafts=0;noIntersections=0
    housing=[o.name for k in mains[:2] for o in O[k].children_recursive if o.type=='MESH']
    def bbox_inter(a,b):
        return all(max(a[0][i],b[0][i])<=min(a[1][i],b[1][i]) for i in range(3))
    for idx,(side,x0) in enumerate((('LEFT',-.336),('RIGHT',.336))):
        pivot=O['OPEN_BLOWER_CAGE_'+side].matrix_world.translation
        assert (pivot-Vector((x0,-.018,.425))).length<1e-6
        vn='Actual separate curved blade surfaces '+side
        v,f=s[vn][2:]
        def key(z):return tuple(round(q,6) for q in z)
        a=defaultdict(set)
        for p in f:
            for u,w in zip(p,p[1:]+p[:1]):
                a[key(v[u])].add(key(v[w]));a[key(v[w])].add(key(v[u]))
        allv=set(a);cc=0
        while allv:
            stack=[allv.pop()];cc+=1
            while stack:
                u=stack.pop()
                for w in a[u]&allv:allv.remove(w);stack.append(w)
        assert cc==22,(side,cc)
        cages=[vn,'Captured outer annular end ring '+side,'Matching true bored sleeve end ring '+side,'Sparse center annular support band '+side]
        for q in cages:
            for m in housing:
                if bbox_inter(s[q][1],s[m][1]):
                    assert not t(q).overlap(t(m)),(side,q,m)
                    noIntersections+=1
        for q in cages[1:]:
            assert t(vn).overlap(t(q)),(side,q)
            annularAttachments+=1
        for u in (-.207,-.146,-.039,.048,.112,.207):
            for i in range(22):
                alpha=math.tau*(i+.5)/22
                R=Vector((0,math.cos(alpha),math.sin(alpha)))
                clear(pivot+u*X+.097*R,-R,.079,cages)
                clear(pivot+u*X+.019*R,R,.077,cages)
                inside+=2
                beta=math.tau*i/22
                R=Vector((0,math.cos(beta),math.sin(beta)))
                pt,_,_,d=t(vn).ray_cast(pivot+u*X+.105*R,-R,.06)
                assert pt is not None and .070<(pt-pivot-u*X).length<.085,(side,u,i,pt)
                bladeHits+=1
        ax='Light straight original stationary axle '+side
        for j in range(idx*2,idx*2+2):
            p='Visible brushed bearing collar cap '+str(j)
            assert t(ax).overlap(t(p)),(side,j)
            shafts+=1
    return dict(imported=imported, continuousOutletRaysTwoDirections=slit, solidOutletBoundaryRays=lip,
      trueIntakeOpeningRaysTwoDirections=grille, solidSlatHits=material,
      openCageRaysTwoDirections=inside, physicalBladeHits=bladeHits, nativeGroupedBladesPerCage=22,
      supportedCageJoinCount=annularAttachments, shaftBearingJoins=shafts,
      casingCageBroadPhaseWithNoIntersection=noIntersections)
bpy.ops.wm.open_mainfile(filepath=args[0]);native=verify(False)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=args[1]);imp=verify(True)
print('M36_GEOMETRY='+json.dumps([native,imp]))
