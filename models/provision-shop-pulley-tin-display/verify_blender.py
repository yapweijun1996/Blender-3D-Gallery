"""Read-only native and reimport checks of the empty heritage-inspired exhibit."""
import bpy,sys,math,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
id='provision-shop-pulley-tin-display'
root=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else Path(__file__).resolve().parent
result={}
for lane in ('native','GLB'):
    if lane=='native':bpy.ops.wm.open_mainfile(filepath=str(root/(id+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(root/'exports'/(id+'.glb')))
    bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get()
    def leaf(n):return [o for o in bpy.data.objects[n].children_recursive if o.type=='MESH']
    def starts(n,l):return [o for o in l if o.name.startswith(n)]
    def choose(n,l):
        a=starts(n,l);assert len(a)==1,(lane,n,[o.name for o in a]);return a[0]
    vdata={}
    def g(o):
        if o.name not in vdata:
            e=o.evaluated_get(dg); mesh=e.to_mesh()
            vdata[o.name]=([e.matrix_world@q.co for q in mesh.vertices],[tuple(q.vertices) for q in mesh.polygons]);e.to_mesh_clear()
        return vdata[o.name]
    def bvh(o):return BVHTree.FromPolygons(*g(o))
    def hits(t,p,d,s):return t.ray_cast(Vector(p),Vector(d),s)
    def hit(t,p,d,s):
        q,*_=hits(t,p,d,s);assert q is not None,(lane,p,d,s);return q
    def bb(o,k):
        p,_=g(o);return (min(v[k] for v in p),max(v[k] for v in p))
    def near(a,b,eps):
        assert abs(a-b)<eps,(lane,a,b,eps)
    def center(o,k):return sum(bb(o,k))/2
    z0=1.152;y0=-.012
    scope=leaf('OVERHEAD_TIMBER_AND_ONE_AUTHORED_PULLEY')
    body=choose('Single sheave with real recessed cord groove',scope);bodyb=bvh(body)
    cable=choose('Single continuous cord over groove between vessels',scope);cb=bvh(cable)
    shaft=choose('Continuous pulley shaft through both cheeks',scope);shaftb=bvh(shaft)
    timber=choose('Cropped overhead old timber',scope);timberb=bvh(timber)
    cheeks=starts('Actual mounting cheek',scope);pads=starts('Visible bracket pad seated in timber',scope)
    assert len(cheeks)==len(pads)==2 and bodyb.overlap(shaftb)
    for cheek,pad in zip(sorted(cheeks,key=lambda o:center(o,1)),sorted(pads,key=lambda o:center(o,1))):
        c=bvh(cheek);t=bvh(pad)
        assert c.overlap(shaftb) and c.overlap(t) and t.overlap(timberb),(lane,cheek.name)
    samples=[]
    for i in range(0,49,2):
        a=i*math.pi/48
        d=Vector((math.cos(a),0,math.sin(a)));mid=Vector((0,y0,z0))
        cc=hit(cb,mid,d,.201);floor=hit(bodyb,mid+.22*d,-d,.055)
        dist=(cc-floor).dot(d)
        assert -.00015 < dist < .00045,(lane,i,dist,cc,floor)
        near((floor-mid).length,.171,.00043)
        for s in [-1,1]:
            rail=hit(bodyb,mid+.22*d+Vector((0,s*.019,0)),-d,.045)
            assert (rail-mid).dot(d)>(cc-mid).dot(d)+.013,(lane,i,cc,rail)
        samples.append(dist*1000)
    # Check actual connected cable continuity by triangulated geometry;
    # glTF may split vertices across seams, so use coordinate welding.
    nodes,faces=g(cable)
    keys=[tuple(round(x,5) for x in p) for p in nodes]
    ed={}
    for face in faces:
        for i,k in enumerate(face):
            a,b=keys[k],keys[face[(i+1)%len(face)]]
            ed.setdefault(a,set()).add(b);ed.setdefault(b,set()).add(a)
    todo=[keys[0]]; seen=set(todo)
    while todo:
        for p in ed[todo.pop()]:
            if p not in seen:seen.add(p);todo.append(p)
    assert len(seen)==len(ed)
    tin_scope=leaf('PAIR_OPEN_EMPTY_PROVISION_TINS')
    report=[]
    for s,z,label in [(-1,.720,'HIGH'),(1,.430,'LOW')]:
        x=s*.178
        tin_ob=choose('Bored empty rolled enamel tub '+str(s),tin_scope)
        tin=bvh(tin_ob)
        bail_ob=choose('Continuous ear-to-ear formed bail '+str(s),tin_scope)
        bail=bvh(bail_ob)
        knot_ob=choose('Seated cord lashing at bail crown '+str(s),tin_scope)
        knot=bvh(knot_ob)
        # True empty interior at the lip, wall and sealed floor.
        for dx,dy in [(0,0),(.037,-.032),(-.058,.028),(0,-.074)]:
            floor=hit(tin,(x+dx,y0+dy,z+.204),(0,0,-1),.200)
            near(floor.z,z+.012,1.2e-5)
        for ds in [-1,1]:
            for dz in [.04,.10,.154]:
                wall=hit(tin,(x,y0,z+dz),(ds,0,0),.120)
                near(wall.x,x+ds*.1065,.00013)
        assert not bodyb.overlap(bail) and not bodyb.overlap(tin),(lane,label,'unplanned sheave contact')
        margins=[]
        for o in starts('True bored eye secured outside tin',tin_scope):
            xx=center(o,0); zz=center(o,2)
            if abs(zz-z-.16)>.003:continue
            bore=bvh(o)
            assert tin.overlap(bore),(lane,o.name,'unseated ear on wall')
            wall_clearance=min(abs(v.x-x) for v in g(o)[0])-.1065
            assert wall_clearance>.002,(lane,o.name,wall_clearance)
            margins.append(wall_clearance*1000)
            rivets=[r for r in starts('Mated ear shelf rivet',tin_scope)
                    if abs(center(r,2)-z-.143)<.002 and (center(r,0)-x)*(xx-x)>0]
            assert len(rivets)==1 and tin.overlap(bvh(rivets[0]))
            assert min(abs(v.x-x) for v in g(rivets[0])[0])-.1065>.004
            # Open bore at depth, off-axis rays independent of the wire.
            assert not hits(bore,(xx+.0064,y0-.026,zz),(0,1,0),.052)[0],(lane,o.name,'blocked ear')
            q=hit(bail,(xx,y0+.006,zz),(1,0,0),.0062)
            near(q.x,xx+.0048,.00045)
        kx,ky,kz=(center(knot_ob,i) for i in range(3))
        near(kx,x,1e-5); near(ky,y0,1e-5); near(kz,z+.302,.00025)
        kb=knot.overlap(bail); kc=knot.overlap(cb); assert kb and kc,(lane,label,'bail/lashing/cord connection',len(kb),len(kc))
        assert bb(tin_ob,2)[0]>.4 and len(margins)==2
        report.append({'tin':label,'open_mouth_to_sealed_floor_rays':4,'hollow_side_rays':6,'bail_bore_checks':2,'ear_intrusion_min_clearance_mm':min(margins),
             'bail_wrap_surface_pairs':len(kb),'wrap_matches_continuous_rope_triangles':len(kc),
             'floor_z':z+.012})
    assert all(not o.animation_data for o in bpy.data.objects)
    result[lane]={'one_connected_cord':True,'groove_symmetric_samples':len(samples),'min_max_groove_tangent_error_mm':[min(samples),max(samples)],
                 'continuous_axle_pads_to_timber':True,'empty_vessels':report}
print('M50_PHYSICAL='+json.dumps(result,separators=(',',':')))
