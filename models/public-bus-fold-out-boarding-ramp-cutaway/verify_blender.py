"""Observe the connected art surface and captured hinge on source and exact GLB readback."""
import json,math,sys,bpy
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
slug='public-bus-fold-out-boarding-ramp-cutaway'
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
artifact=Path(args[0]) if args else Path(__file__).resolve().parent
r={}
for kind in ('source','reimport'):
    if kind=='source':bpy.ops.wm.open_mainfile(filepath=str(artifact/(slug+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(artifact/'exports'/(slug+'.glb')))
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    def all(p):return [ob for ob in bpy.context.scene.objects if ob.type=='MESH' and ob.name.startswith(p)]
    def one(p):
        hits=all(p);assert len(hits)==1,(p,[o.name for o in hits]);return hits[0]
    def resolved(ob):
        e=ob.evaluated_get(dg);m=e.to_mesh()
        pts=[e.matrix_world@v.co for v in m.vertices]
        ff=[tuple(v.vertices) for v in m.polygons]
        e.to_mesh_clear()
        return pts,ff
    def bvh(objs):
        pt=[];s=[]
        for o in objs:
            p,f=resolved(o);q=len(pt);pt.extend(p);s.extend(tuple(k+q for k in a) for a in f)
        return BVHTree.FromPolygons(pt,s)
    def limit(ob,j):
        vs=resolved(ob)[0]
        return min(v[j] for v in vs),max(v[j] for v in vs)
    floor=one('Solid continuous interior floor up to sill')
    heel=one('Flush elastomer-colored heel transition')
    leaf=one('One continuous sloped boarding deck')
    lip=one('Physical toe join')
    curb=one('Center curb segment')
    track=bvh([floor,heel,leaf,lip,curb])
    def expected(y):
        if y<=-.880:return .1906
        if y>=.180:return .445
        return .445+.24*(y-.180)
    rows=sorted(set([-1.32+i*.0048 for i in range(398)]+[s+d for s in (-.942,-.880,.15,.18,.19) for d in [-.00045,-.00008,.00008,.00045]]))
    # Rays rather than only bounding boxes. The 11 lanes stay clear of side edging.
    rays=[]
    for x in (-.417,-.387,-.297,-.187,-.084,0,.081,.174,.284,.387,.417):
        for y in rows:
            pos,normal,_,_=track.ray_cast(Vector((x,y,.73)),Vector((0,0,-1)),1)
            assert pos and normal.z>.85,(kind,x,y,pos,normal)
            err=abs(pos.z-expected(y))
            assert err<2e-6,(kind,x,y,pos.z,expected(y),err)
            rays.append(err)
    xe=[-.417,-.230,0,.232,.417]
    joins=[]
    for seam in (-.942,-.880,.150,.190):
        for x in xe:
            low=track.ray_cast(Vector((x,seam-.0001,.74)),Vector((0,0,-1)))[0]
            high=track.ray_cast(Vector((x,seam+.0001,.74)),Vector((0,0,-1)))[0]
            assert low and high and 0<=high.z-low.z+1e-7<.00006,(kind,seam,low,high)
            joins.append(abs(high.z-low.z))
    side=all('Continuous raised side guide edge');assert len(side)==2
    sideb=bvh(side)
    edging=[]
    for x in (-.437,.437):
        for i in range(13):
            y=-.82+i*.0695
            p=sideb.ray_cast(Vector((x,y,.70)),Vector((0,0,-1)))[0]
            assert p and p.z-expected(y)>.012,(kind,x,y)
            edging.append(p.z-expected(y))
    hinges=sorted([*all('Leaf physical hinge barrel'),*all('Sill physical hinge barrel')],key=lambda o:limit(o,0)[0])
    assert len(hinges)==7
    assert ['Leaf' if p.name.startswith('Leaf') else 'Sill' for p in hinges]==['Leaf','Sill']*3+['Leaf']
    pin=one('HINGE_STEEL_PIN_UNBROKEN_ACROSS_ALL_BARRELS')
    pb=bvh([pin]);center=(.166,.414)
    assert abs(limit(pin,0)[0]+.435)<1e-6 and abs(limit(pin,0)[1]-.435)<1e-6
    rad_errors=[];barrel_radial_gaps=[];hinge_axial_gaps=[]
    supports=all('Leaf support tang')+all('Sill support tang');joined=[bvh([t]) for t in supports]
    assert len(supports)==7
    for i,h in enumerate(hinges):
        hbox=limit(h,0); hx=sum(hbox)*.5; hb=bvh([h])
        # Look outward from the empty center to the inner cylindrical surface.
        for j in range(24):
            a=7*math.pi/96+j*math.tau/24; out=Vector((0,math.cos(a),math.sin(a)))
            bore=hb.ray_cast(Vector((hx,*center)),out,.020)[0]
            pinSurf=pb.ray_cast(Vector((hx,*center)),out,.014)[0]
            assert bore and pinSurf,(kind,i,j)
            d=(bore-Vector((hx,*center))).length
            dp=(pinSurf-Vector((hx,*center))).length
            assert .01130<d<.01150 and .01035<dp<.01060 and (d-dp)>.00076,(kind,i,j,d,dp)
            barrel_radial_gaps.append(d-dp);rad_errors.append(abs(d-.0114))
        hl,hr=hbox
        if i:
            gap=hl-limit(hinges[i-1],0)[1]
            assert abs(gap-.016)<1e-6,(kind,i,gap)
            hinge_axial_gaps.append(gap)
        sw=next(j for j,s in enumerate(supports) if limit(s,0)[0]<hx<limit(s,0)[1])
        # Point is safely inside the annulus and the connecting support tang;
        # nearest opposing skin still leaves the modeled pin/bore open.
        direction=-1 if i%2==0 else 1
        yy=.166+direction*.018
        tri=hb.ray_cast(Vector((hx,yy,.457)),Vector((0,0,-1)))[0]
        tang=joined[sw].ray_cast(Vector((hx,yy,.457)),Vector((0,0,-1)))[0]
        assert tri and tang and abs(tri.z-tang.z)<.008,(kind,i,tri,tang)
        tangent_bounds=limit(supports[sw],1)
        assert (center[0]-tangent_bounds[1] if direction<0 else tangent_bounds[0]-center[0])>.0115
    road=one('Flat asphalt street-section base');ground=limit(road,2)[1]
    pads=all('Sections bearing on dark exhibit foot'); chassis=all('Independent lower chassis support lug')
    assert len(pads)==len(chassis)==2
    for pad,lug in zip(sorted(pads,key=lambda p:limit(p,0)[0]),sorted(chassis,key=lambda p:limit(p,0)[0])):
        assert -.0013<limit(pad,2)[0]-ground<.0001
        assert 0<limit(pad,2)[1]-limit(lug,2)[0]<.0020
    r[kind]=dict(path_rays=len(rays),path_max_error_m=max(rays),join_pairs=len(joins),max_near_join_height_change_m=max(joins),
                 edging_probe_hits=len(edging),edge_minimum_raise_m=min(edging),actual_hinge_knuckles=len(hinges),
                 bore_radial_probes=len(barrel_radial_gaps),pin_to_bore_min_m=min(barrel_radial_gaps),knuckle_gaps_m=hinge_axial_gaps)
print(json.dumps(r,indent=2))
