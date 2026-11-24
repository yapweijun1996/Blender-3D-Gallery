"""Native and independently reimported GLB topology and corresponding powder proof."""
import bpy, math, sys, json, itertools
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from collections import defaultdict, Counter
argv=sys.argv[sys.argv.index('--')+1:]
def inspect(imported):
    D=bpy.context.evaluated_depsgraph_get()
    O=bpy.data.objects
    plate=O['PATTERN_SIEVE_TRUE_PERFORATED_PLATE']
    holder=O['PERFORATED_SIEVE_HOLDER']
    swatch=O['MATCHED_POWDER_SWATCH']
    base=O['PRESENTATION_BASE']
    def geom(o,root):
        ev=o.evaluated_get(D);me=ev.to_mesh();T=root.matrix_world.inverted()@ev.matrix_world
        V=[T@p.co for p in me.vertices]
        F=[tuple(p.vertices) for p in me.polygons]
        mats=[ev.material_slots[f.material_index].material.name for f in me.polygons]
        ev.to_mesh_clear()
        return V,F,mats
    def shape(o,root):
        V,F,_=geom(o,root)
        return BVHTree.FromPolygons(V,F,all_triangles=all(len(x)==3 for x in F))
    def hull(blobs,root):
        return [shape(o,root) for o in blobs if o.type=='MESH']
    v,f,m=geom(plate,holder)
    def key(p):return tuple(round(u,6) for u in p)
    def xy(p):return tuple(round(u,6) for u in p[:2])
    weld={key(p) for p in v}
    face=[tuple(key(v[i]) for i in x) for x in f]
    inc=Counter(tuple(sorted((a,b))) for p in face for a,b in zip(p,p[1:]+p[:1]))
    assert set(inc.values())=={2},Counter(inc.values())
    # Include only top boundary edges of actual vertical bare-metal sidewalls.
    adj=defaultdict(set)
    for fs,ma in zip(f,m):
        if not ma.startswith('Bare cut surfaces'):continue
        for a,b in zip(fs,fs[1:]+fs[:1]):
            if v[a].z>.0016 and v[b].z>.0016:
                u,w=xy(v[a]),xy(v[b]); assert u!=w
                adj[u].add(w);adj[w].add(u)
    assert set(map(len,adj.values()))=={2},Counter(map(len,adj.values()))
    keyset=set(adj);loops=[]
    while keyset:
        a=min(keyset);q=[a];f0=a;b=min(adj[a])
        while b!=a:
            q.append(b)
            c,=adj[b]-{f0};f0,b=b,c
        keyset-=set(q);loops.append(q)
    assert len(loops)==30,len(loops)
    def area(q):
        return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(q,q[1:]+q[:1])))/2
    loops=sorted(loops,key=area,reverse=True);outer,*holes=loops
    assert area(outer)>.030 and max(map(area,holes))<.001
    whole=defaultdict(set)
    for a,b in inc:whole[a].add(b);whole[b].add(a)
    stack=[next(iter(weld))];seen=set()
    while stack:
        a=stack.pop()
        if a not in seen:
            seen.add(a);stack.extend(whole[a]-seen)
    assert seen==weld
    chi=len(weld)-len(inc)+len(face)
    assert chi==2-2*29,(len(weld),len(inc),len(face),chi)
    z0,z1=min(v0.z for v0 in v),max(v0.z for v0 in v)
    assert abs(z1-z0-.0034)<.000005
    sill=shape(plate,holder)
    solid=hull(holder.children_recursive+base.children_recursive,holder)
    swobjs=[o for o in swatch.children_recursive if o.type=='MESH' and o.name.startswith('MATCHED_POWDER_TRANSFER_')]
    assert len(swobjs)==4,len(swobjs)
    sw=hull(swobjs,swatch)
    def is_in(q,L):
        a,b=q;flag=False
        for (x,y),(u,w) in zip(L,L[1:]+L[:1]):
            if (y>b)!=(w>b) and a<(u-x)*(b-y)/(w-y)+x:flag=not flag
        return flag
    def distance(q,a,b):
        x,y=q;u,v=a;dx=b[0]-u;dy=b[1]-v
        t=max(0,min(1,((x-u)*dx+(y-v)*dy)/(dx*dx+dy*dy)))
        return math.hypot(x-u-t*dx,y-v-t*dy)
    rz=Vector((0,0,1))
    holesCount=0;powderCount=0;wallCount=0;transferHeight=[]
    for h in holes:
        a,b=min(x[0] for x in h),max(x[0] for x in h)
        c,d=min(x[1] for x in h),max(x[1] for x in h)
        tests=[]
        for i,j in itertools.product(range(1,16),range(1,16)):
            q=(a+(b-a)*i/16,c+(d-c)*j/16)
            if not is_in(q,h):continue
            sep=min(distance(q,p,w) for p,w in zip(h,h[1:]+h[:1]))
            if sep>.00085:tests.append((sep,q))
        assert len(tests)>=9,len(tests)
        _,ctr=max(tests); ctr=Vector((*ctr,0))
        for sep,q in sorted(tests,reverse=True)[::max(1,len(tests)//9)][:9]:
            for s in (-1,1):
                pos=Vector((*q,s*.017));dr=rz*(-s)
                assert all(t.ray_cast(pos,dr,.034)[0] is None for t in solid),(q,s,min(tests), 'blocked complete aperture')
                holesCount+=1
            pos=Vector((*q,.018))
            hits=[r.ray_cast(pos,-rz,.016)[0] for r in sw]
            hits=[h1 for h1 in hits if h1 is not None]
            assert len(hits)==1,(q,len(hits))
            height=hits[0].z
            assert .0067<height<.0101,height
            transferHeight.append(height)
            powderCount+=1
        for p in (-1,1):
            loc,_,_,dt=sill.ray_cast(ctr,Vector((p,0,0)),.028)
            assert loc is not None and abs(loc.z)<.00001 and .0007<dt<.017,(ctr,loc,dt)
            wallCount+=1
    webCount=0
    for i in range(-13,14):
        for j in range(-13,14):
            q=(i*.0062,j*.0062)
            if math.hypot(*q)>.095 or any(is_in(q,h) for h in holes):continue
            if min(distance(q,a,b) for h in holes for a,b in zip(h,h[1:]+h[:1]))<.0003:continue
            p=Vector((*q,.016));hit=sill.ray_cast(p,-rz,.03)[0]
            assert hit is not None and abs(hit.z-z1)<1e-5,(p,hit)
            webCount+=1
    # The physical dust sample must sit on its matte ceramic substrate:
    # at least one coated base vertex per color intersects the tiny top skin.
    ceramic=O['Dark matte sample tile under separate powder print']
    c,vf,m=geom(ceramic,swatch);tile_top=max(q.z for q in c)
    for ob in swobjs:
        v,f,_=geom(ob,swatch)
        assert .00000<tile_top-min(q.z for q in v)<.00015
    rim=shape(O['Continuous dark aubergine rim shell'],holder)
    joins=0
    for side in (-1,1):
        for name in ('Small opposed patterned hand grip ','External soft cradle tab mount ','Set-in forked support post '):
            assert rim.overlap(shape(O[name+str(side)],holder)),name
            joins+=1
    return dict(physicalRimJoins=joins,imported=imported,realHoles=len(holes),oneWeldedSolid=True,topologyEuler=chi,genuineThicknessMm=(z1-z0)*1000,
       frontAndReverseUnobstructedRays=holesCount,correspondingPowderRays=powderCount,
       interiorWallHits=wallCount,solidWebProbes=webCount,minPowderHeightMm=min(transferHeight)*1000,maxPowderHeightMm=max(transferHeight)*1000)
bpy.ops.wm.open_mainfile(filepath=argv[0]);a=inspect(False)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=argv[1]);b=inspect(True)
print('M35_GEOMETRY='+json.dumps([a,b]))
