"""Verify the 16 real cavities and seated display counters, native and GLB reimport."""
import bpy,sys,math,json,collections
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
slug='traditional-congkak-board-display'
path=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else Path(__file__).resolve().parent
data={}
for lane in ('native','GLB'):
    if lane=='native':bpy.ops.wm.open_mainfile(filepath=str(path/(slug+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(path/'exports'/(slug+'.glb')))
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    d={}
    def leaf(n):
        return [o for o in bpy.data.objects[n].children_recursive if o.type=='MESH']
    def geometry(o):
        if o.name not in d:
            e=o.evaluated_get(dg);m=e.to_mesh()
            d[o.name]=([e.matrix_world@v.co for v in m.vertices],[tuple(p.vertices) for p in m.polygons]);e.to_mesh_clear()
        return d[o.name]
    def bv(o):return BVHTree.FromPolygons(*geometry(o))
    def bound(o,k):
        a,_=geometry(o);return (min(x[k] for x in a),max(x[k] for x in a))
    board=leaf('CONGKAK_ORIGINAL_SOLID_BOARD');assert len(board)==1
    woody=board[0];v,f=geometry(woody)
    # Geometric mesh welding handles valid glTF material/normal seam duplicates
    # without counting them as gaps in the solid.
    keys=[tuple(round(q,6) for q in a) for a in v]
    neighbor={}; sides=collections.Counter()
    for p in f:
        for i,j in enumerate(p):
            a,b=keys[j],keys[p[(i+1)%len(p)]]
            if a!=b:
                neighbor.setdefault(a,set()).add(b);neighbor.setdefault(b,set()).add(a)
                sides[tuple(sorted((a,b)))]+=1
    assert len(sides)>1000 and all(n==2 for n in sides.values()),(lane,collections.Counter(sides.values()))
    q=[keys[0]];done=set(q)
    while q:
        for k in neighbor[q.pop()]:
            if k not in done:done.add(k);q.append(k)
    assert len(done)==len(neighbor)==len(set(keys))
    native=bv(woody)
    def ray(px,py,pz=.188,d=(0,0,-1),close=.155):
        a,n,_,_=native.ray_cast(Vector((px,py,pz)),Vector(d),close)
        assert a is not None,(lane,px,py,pz)
        return a,n
    pits=[]
    for tag,px,py,R,sink in ([('village',x,y,.0355,.042) for x in (-.046,.046)
                            for y in (-.276,-.184,-.092,0,.092,.184,.276)]
                            +[('house',0,y,.068,.059) for y in (-.404,.404)]):
        values=[ray(px,py)[0].z]
        assert abs(values[0]-(.168-sink))<2e-6,(lane,tag,px,py,values[0])
        radii=2 if tag=='village' else 3
        for angle in range(12):
            a=angle*math.tau/12;x,y=math.cos(a)*R,math.sin(a)*R
            for scale in (.43,.75,.94)[:radii]:
                h,n=ray(px+x*scale,py+y*scale)
                assert values[0]<h.z<.1678 and n.z>-.02,(lane,tag,px,py,angle,scale,h,n)
                values.append(h.z)
        bottom,normal=ray(px,py,.062,(0,0,1),.020)
        assert abs(bottom.z-.074)<2e-6 and normal.z<-.95
        assert values[0]-bottom.z>.03
        pits.append({'kind':tag,'gridCoord':[px,py],'depthMm':(.168-values[0])*1000,
                     'wallSamples':len(values)-1,'toSolidUndersideMm':(values[0]-bottom.z)*1000})
    # The medial ridge, all longitudinal bridges and the body beyond the end
    # wells remain one continuous surface at the intended height.
    for y in (-.330,-.230,-.138,-.046,.046,.138,.230,.330):
        for x in (-.053,0,.053):assert abs(ray(x,y)[0].z-.168)<2e-6,(lane,x,y)
    seeds=leaf('STAGED_SPARSE_COUNTERS');assert len(seeds)==9
    db=[]
    for i,o in enumerate(seeds):
        s=bv(o);bb=[bound(o,k) for k in range(3)]
        sx,sy=[sum(b0)/2 for b0 in bb[:2]]
        near=min(pits,key=lambda row:math.hypot(sx-row['gridCoord'][0],sy-row['gridCoord'][1]))
        assert math.hypot(sx-near['gridCoord'][0],sy-near['gridCoord'][1])<.019
        if i:
            for prior in seeds[:i]:assert not s.overlap(bv(prior)),(lane,o.name,prior.name)
        assert len(s.overlap(native))>0,(lane,o.name,'unsupported seed')
        # Actual lower quarter seats on cavity; above-quarter core must be clear.
        verts,_=geometry(o);minz,maxz=bb[2]
        pen=[]
        for vert in verts:
            h,_=ray(vert.x,vert.y)
            pen.append(h.z-vert.z)
            if vert.z>minz+.25*(maxz-minz):assert pen[-1]<0,(lane,o.name,'overly buried')
        db.append(max(pen)*1000)
        assert .025<db[-1]<1.7,(lane,o.name,db[-1])
    cradles=[o for o in leaf('SEPARATE_INTERPRETIVE_EXHIBIT_PLINTH') if o.name.startswith('Independent padded cradle')]
    assert len(cradles)==2
    assert all(.0002<bound(o,2)[1]-bound(woody,2)[0]<.0013 for o in cradles)
    assert all(not o.animation_data for o in bpy.data.objects)
    data[lane]={'watertightShellEdges':len(sides),'cavities':pits,'seatedCounters':len(seeds),
        'counterSeatingContactMmMinMax':[min(db),max(db)],'additionalBottomIntegrityRays':16,'intactDeckBridgeRays':24}
print('M51_PHYSICAL='+json.dumps(data,separators=(',',':')))
