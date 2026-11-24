"""Cast last, fitted saddle and true sole relief: verify native and production GLB readback."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
slug='five-foot-way-cobbler-repair-stand'
arg=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=Path(arg[0]) if arg else Path(__file__).resolve().parent
out={}
for v in ('source','reimport'):
    if v=='source':bpy.ops.wm.open_mainfile(filepath=str(p/(slug+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(p/'exports'/(slug+'.glb')))
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    def many(p):return [o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(p)]
    def one(p):
        m=many(p);assert len(m)==1,(p,[o.name for o in m]);return m[0]
    def get(o):
        e=o.evaluated_get(dg);m=e.to_mesh()
        vs=[e.matrix_world@q.co for q in m.vertices];ff=[tuple(f.vertices) for f in m.polygons]
        e.to_mesh_clear()
        return vs,ff
    def bounds(o,j):
        vs,_=get(o)
        return min(x[j] for x in vs),max(x[j] for x in vs)
    def tree(objs):
        if not isinstance(objs,list):objs=[objs]
        verts=[];faces=[]
        for o in objs:
            vs,ff=get(o);n=len(verts);verts+=vs;faces.extend(tuple(n+i for i in f) for f in ff)
        return BVHTree.FromPolygons(verts,faces)
    def ray(b,p,d=(0,0,-1),m=3):
        return b.ray_cast(Vector(p),Vector(d),m)[0]
    last=one('Sculpted closed asymmetric toe heel cast shoe last')
    lid=tree(last)
    bbw=bounds(last,0);assert abs((bbw[1]-bbw[0])-.288)<.00015
    breadth={}
    for word,x in [('heel',-.106),('waist',-.055),('toe',.042)]:
        xx=x-.129
        top=ray(lid,(xx,-.051,.80))
        low=ray(lid,(xx,-.051,.44),(0,0,1))
        q=ray(lid,(xx,-.23,(top.z+low.z)/2),(0,1,0))
        h=ray(lid,(xx,.12,(top.z+low.z)/2),(0,-1,0))
        assert top and low and h and q
        breadth[word]=dict(width=h.y-q.y,height=top.z-low.z)
    assert breadth['toe']['width']>.090 and breadth['waist']['width']<.064
    assert breadth['heel']['width']>breadth['waist']['width']*1.16
    assert max(r['height'] for r in breadth.values())>.038
    # Solid load path observed with axial rays to each independently modeled part.
    axis=(-.224,-.051)
    chain=[
        one('Sanded hardwood last mount foot block'),
        one('Independent cast iron footprint flange'),
        one('Tapered mounted iron stem fixed into'),
        one('Continuous heel tenon visible'),
        last
    ]
    levels=[]
    for part in chain:
        model=tree(part); a=ray(model,(*axis,.91));b=ray(model,(*axis,.315),(0,0,1))
        assert a and b and a.z>b.z
        levels.append([b.z,a.z])
    joins=[]
    for (_,a),(b,_) in zip(levels,levels[1:]):
        joins.append(a-b);assert 0.00039<a-b<.013,(v,levels,joins)
    saddle=tree(one('True open square saddle socket'))
    gap=[]
    passRays=0
    for xx in (-.014,0,.014):
        for yy in (-.014,0,.014):
            assert ray(saddle,(axis[0]+xx,axis[1]+yy,.559),m=.076) is None
            passRays+=1
    for pz in (.509,.514,.521):
        for di in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0)]:
            take=ray(saddle,(*axis,pz),di,.027)
            pin=ray(tree(chain[3]),(*axis,pz),di,.025)
            assert take and pin
            delta=(take-Vector((*axis,pz))).length-(pin-Vector((*axis,pz))).length
            assert .0017<delta<.0023,(v,pz,di,delta)
            gap.append(delta)
    allr=tree(many('Actual raised forefoot tread')+many('Actual raised heel tread')+many('Dark full continuous recessed tread field'))
    assert len(many('Actual raised forefoot tread'))==16 and len(many('Actual raised heel tread'))==8
    trans=bpy.context.scene.objects['LOOSE_SHOE_FORM_SOLE'].matrix_world
    def sole_at(x,y):
        origin=trans@Vector((x,y,.11)); hit=ray(allr,origin)
        assert hit,(v,x,y)
        return (trans.inverted()@hit).z
    tread=[]
    for x in [.010+j*.0142 for j in range(8)]:
        for y in (-.019,.019):
            lower=sole_at(x,0)
            raised=sole_at(x,y)
            assert .00335<raised-lower<.00345,(v,x,y,lower,raised)
            tread.append(raised-lower)
    for x in [-.117+j*.013 for j in range(4)]:
        for y in (-.014,.014):
            lower=sole_at(x,0)
            raised=sole_at(x,y)
            assert .00305<raised-lower<.00315,(v,x,y,lower,raised)
            tread.append(raised-lower)
    bench=tree(many('Independent worn flat workbench plank'))
    lowS=tree(one('Full distinct shoe sole sidewall'))
    seats=[]
    for xy in ((-.075,.016),(-.02,0),(.02,-.01),(.062,.008),(.091,0)):
        pos=trans@Vector((*xy,0))
        uk=ray(bench,(pos.x,pos.y,.64))
        lo=ray(lowS,(pos.x,pos.y,.32),(0,0,1))
        assert uk and lo and abs(uk.z-lo.z)<.00015,(v,pos,uk,lo)
        seats.append(uk.z-lo.z)
    mh=one('Mallet low aged retaining center collar');mT=one('Mallet broad rounded tail supports')
    ref=.356
    malletContacts=[bounds(mh,2)[0]-ref,bounds(mT,2)[0]-ref]
    assert all(-.00065<z<.00045 for z in malletContacts)
    out[v]=dict(breadth_m=breadth,mOUNT_levels_m=levels,physical_join_overlaps_m=joins,saddle_clear_through_rays=passRays,
                square_socket_pin_clearance_probe_count=len(gap),socket_min_gap_m=min(gap),tread_positions=len(tread),
                tread_relief_mm=[min(tread)*1000,max(tread)*1000],sole_physical_plank_seat_rays=len(seats),
                parked_mallet_seat_m=malletContacts)
print(json.dumps(out,indent=2))
