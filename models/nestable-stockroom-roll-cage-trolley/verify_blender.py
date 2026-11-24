"""Read-only fit, lattice, hinge and contact checks for both static cage copies."""
import bpy,sys,math,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
slug='nestable-stockroom-roll-cage-trolley'
path=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else Path(__file__).resolve().parent
out={}
for lane in ('native','GLB'):
    if lane=='native':bpy.ops.wm.open_mainfile(filepath=str(path/(slug+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(path/'exports'/(slug+'.glb')))
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    def leaf(root):
        return [o for o in bpy.data.objects[root].children_recursive if o.type=='MESH']
    def geo(o):
        e=o.evaluated_get(dg);m=e.to_mesh()
        v=[e.matrix_world@q.co for q in m.vertices]
        f=[tuple(q.vertices) for q in m.polygons];e.to_mesh_clear();return v,f
    def join(os):
        v=[];f=[]
        for o in os:
            v1,f1=geo(o);n=len(v);v+=v1;f.extend(tuple(i+n for i in x) for x in f1)
        return v,f
    def allBV(a):return BVHTree.FromPolygons(*join(a))
    def bvh(o):return BVHTree.FromPolygons(*geo(o))
    def ray(t,p,d,span):return t.ray_cast(Vector(p),Vector(d),span)[0]
    def cell(name,os):
        return [o for o in os if o.name.removeprefix('NESTED COPY ').startswith(name)]
    def one(name,os):
        a=cell(name,os);assert len(a)==1,(lane,name,a);return a[0]
    def closest(t,g):
        return min(t.find_nearest(v)[3] for v in g)
    def overlap(a,b):
        return min(a[1],b[1])-max(a[0],b[0])
    def bounds(v,axis):return (min(q[axis] for q in v),max(q[axis] for q in v))
    a=leaf('RECEIVER_CAGE_SAME_SKU');b=leaf('NESTED_CAGE_SAME_SKU')
    assert len(a)==len(b) and len(a)>125,(lane,len(a),len(b))
    av,af=join(a);bw,bf=join(b)
    aty,bty=bounds(av,1),bounds(bw,1)
    offset=bpy.data.objects['NESTED_CAGE_SAME_SKU'].matrix_world.translation.y-bpy.data.objects['RECEIVER_CAGE_SAME_SKU'].matrix_world.translation.y
    assert abs(offset+.385)<2e-6
    assert abs((aty[1]-aty[0])-(bty[1]-bty[0]))<1e-6
    assert .40<overlap(aty,bty)<.50,(lane,aty,bty)
    def near(v,off=0):
        return sorted(tuple(round(c,5) for c in (p.x,p.y+off,p.z)) for p in v)
    va,vb=near(av),near(bw,-offset)
    assert len(va)==len(vb)
    # Shared linked source data survives serialization independently of exact
    # glTF seam duplication; compare geometric coordinates allowing tiny
    # export rounding on equivalent repeated native meshes.
    if lane=='native':
        bdata={o.data.as_pointer() for o in b}
        assert all(o.data.as_pointer() in bdata for o in a)
    key=lambda p:tuple(round(c,4) for c in p)
    sa,sb={key(p) for p in va},{key(p) for p in vb}
    assert len(sa ^ sb)/len(sa | sb)<.002,(lane,len(sa ^ sb),len(sa))
    r=BVHTree.FromPolygons(av,af);m=BVHTree.FromPolygons(bw,bf)
    assert not r.overlap(m),(lane,'nested station interpenetration')
    d=min(closest(r,bw),closest(m,av))
    # This finite sweep validates the empty artwork placement, not a real
    # installation technique, product or loaded cart.
    for i in range(41):
        q=-.53+.53*i/40
        u=BVHTree.FromPolygons([v+Vector((0,q,0)) for v in bw],bf)
        assert not r.overlap(u),(lane,i,q,'illustrative alignment obstruction')
    floor=bvh(one('Quiet textured stockroom exhibit plinth',leaf('INDEPENDENT_EXHIBIT_PLINTH')))
    casterGaps=[];holes=0;hingeRays=0;seat=[]
    for os,off in [(a,.274),(b,-.111)]:
        tires=cell('Seated black tire on independent caster',os);assert len(tires)==4
        for o in tires:
            v,_=geo(o);x=(bounds(v,0)[0]+bounds(v,0)[1])/2;y=(bounds(v,1)[0]+bounds(v,1)[1])/2
            f=ray(floor,(x,y,.099),(0,0,-1),.09)
            lowest=min(p.z for p in v)
            assert f and abs(f.z-lowest)<.000025,(lane,os[0].name,x,y,lowest,f)
            casterGaps.append((lowest-f.z)*1000)
        openSide=allBV(cell('Open side grid',os))
        for i in [1,3,5,8,10]:
            for j in [2,5,8,11]:
                y0=-.398+(i+.5)*(.388+.398)/12
                zz=.282+(j+.5)*1.218/15
                for sign in [-1,1]:
                    x=sign*(.237-.19*y0+.038)
                    assert ray(openSide,(x,y0+off,zz),(-sign,0,0),.087) is None,(lane,i,j,sign,'blocked true grid cell')
                    holes+=1
        pin=bvh(one('Continuous fixed common pin',os))
        for side in ['LEFT','RIGHT']:
            inner=one('Rested platform inner eye '+side,os)
            outer=one('Cage mounted outer eye '+side,os)
            a1=bvh(inner);a2=bvh(outer)
            assert a1.overlap(bvh(one('Parked platform spar-foot to hanger '+side,os))),(lane,side,'floating deck base')
            assert a2.overlap(bvh(one('Recessed weld-tab into rear cage '+side,os))),(lane,side,'eye not tied to cage')
            for piece,mesh in [(inner,a1),(outer,a2)]:
                assert not mesh.overlap(pin),(lane,side,'blocked pin')
                ba=bounds(geo(piece)[0],0);xx=(ba[0]+ba[1])/2
                for i in range(12):
                    ang=i*math.tau/12
                    direction=(0,math.cos(ang),math.sin(ang));p0=(xx,.359+off,.254)
                    r1=ray(mesh,p0,direction,.018);r2=ray(pin,p0,direction,.018)
                    assert r1 and r2 and .0010<(r1-r2).length<.0017,(lane,side,i,r1,r2)
                    hingeRays+=1
            keeper=bvh(one('Upper deck keeper '+side,os))
            guard=bvh(one('Small actual keeper fastening axis '+side,os))
            top=bvh([x for x in cell('Wide amber parked deck cross-rail',os) if bounds(geo(x)[0],2)[0]>.90][0])
            link=bvh(one('Rear keeper bracket '+side,os))
            assert keeper.overlap(top) and keeper.overlap(guard) and keeper.overlap(link),(lane,side,'parked panel retainer not seated')
            seat.append(side)
    out[lane]={'cage_mesh_instances':len(a)+len(b),'geometry_same_on_both':True,
               'nested_footprint_overlap_m':overlap(aty,bty),'nested_pair_nearest_surface_mm':d*1000,
               'visual_alignment_disjoint_samples':41,'lattice_open_rays':holes,'grounded_wheel_residuals_mm':casterGaps,
               'actual_open_bored_hinge_rays':hingeRays,'seated_upper_keepers':len(seat)}
print(json.dumps(out,indent=2))
