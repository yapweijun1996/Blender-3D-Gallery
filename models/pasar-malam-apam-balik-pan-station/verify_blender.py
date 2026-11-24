"""Verify hollow pans and lid, seated contact, rack openings and folded sample in native and GLB."""
import bpy,json,math,sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from pathlib import Path
slug='pasar-malam-apam-balik-pan-station'
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=Path(args[0]) if args else Path(__file__).resolve().parent
report={}
for typ in ('native','glb'):
    if typ=='native':bpy.ops.wm.open_mainfile(filepath=str(p/(slug+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(p/'exports'/(slug+'.glb')))
    bpy.context.view_layer.update()
    def find(prefix):
        return [o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(prefix)]
    def one(p):
        found=find(p);assert len(found)==1,(p,[x.name for x in found]);return found[0]
    dg=bpy.context.evaluated_depsgraph_get()
    def geometry(o):
        e=o.evaluated_get(dg);m=e.to_mesh()
        pts=[e.matrix_world@v.co for v in m.vertices]
        faces=[tuple(poly.vertices) for poly in m.polygons]
        e.to_mesh_clear()
        return pts,faces
    def bvh(obs):
        pts=[];faces=[]
        for o in obs:
            v,f=geometry(o);n=len(pts)
            faces.extend(tuple(n+i for i in a) for a in f);pts.extend(v)
        return BVHTree.FromPolygons(pts,faces)
    def axis_surface(obj,xy,z,step):
        return bvh([obj]).ray_cast(Vector((*xy,z)),Vector((0,0,step)))[0]
    def delta(t):return max(t)-min(t)
    pan_metrics=[]
    for side,xc in [('LEFT',-.448),('RIGHT',-.025)]:
        pan=one('Walled concave radial pan basin '+side); stand=one('Short passive annular iron trivet '+side)
        ph,sh=bvh([pan]),bvh([stand])
        low=[]; rims=[]
        for i in range(24):
            ang=math.tau*i/24
            for r in (.012,.105,.152):
                pt=(xc+r*math.cos(ang),-.078+r*math.sin(ang))
                hit,n,_,d=ph.ray_cast(Vector((*pt,.76)),Vector((0,0,-1)))
                assert hit and n.z>.3,(typ,side,r,hit,n)
                (rims if r>.15 else low).append(hit.z)
        assert min(rims)-max(low)>.036
        support=[]
        for i in range(48):
            ang=math.tau*i/48
            pt=(xc+.121*math.cos(ang),-.078+.121*math.sin(ang))
            under,n,_,_=ph.ray_cast(Vector((*pt,.565)),Vector((0,0,1)))
            rest,_,_,_=sh.ray_cast(Vector((*pt,.62)),Vector((0,0,-1)))
            gap=under.z-rest.z
            assert n.z<-.98 and abs(gap)<.00008,(typ,side,gap)
            support.append(gap)
        center=(xc,-.078)
        deep=axis_surface(pan,center,.765,-1).z
        bottom=axis_surface(pan,center,.545,1).z
        assert .00595<(deep-bottom)<.00605
        pan_metrics.append(dict(side=side,upper_open_cavity_samples=len(low)+len(rims),minimum_cavity_depth_m=min(rims)-max(low),
                                structural_gauge_m=deep-bottom,plateau_contact_samples=len(support),maximum_plateau_contact_error_m=max(map(abs,support))))
    lid=one('True hollow thin removable domed lid');tr=bpy.context.scene.objects['REMOVABLE_DOMED_LID'].matrix_world
    lith=bvh([lid]);normal=tr.to_3x3()@Vector((0,0,1))
    shell=[]
    for radi in (.015,.048,.093,.124):
        for k in range(18):
            a=math.tau*k/18;q=Vector((radi*math.cos(a),radi*math.sin(a),0))
            lo,nlo,_,_=lith.ray_cast(tr@(q-Vector((0,0,.050))),normal)
            hi,nhi,_,_=lith.ray_cast(tr@(q+Vector((0,0,.180))),-normal)
            assert lo and hi and nhi.dot(normal)>.23 and nlo.dot(normal)<-.23,(typ,radi)
            assert .002<(hi-lo).length<.015
            shell.append((hi-lo).length)
    pads=find('Formed padded contact on dome stand');assert len(pads)==4
    left=[];right=[]
    for pad in pads:
        pts,_=geometry(pad)
        x=sum(v.x for v in pts)/len(pts)
        group=left if x<.073 else right
        group.append(min(lith.find_nearest(v)[3] for v in pts))
    rack=[*find('Independent cooling rack wire'),*find('Rack spacing support lower longitudinal wire'),
          *find('Open cooling frame short span'),*find('Long stainless cooling frame')]
    assert len(rack)==22
    grid=bvh(rack); opened=[];hits=[]
    for x in (.290,.366,.449,.535):
        for j in range(15):
            yy=-.055-.175+.023*j
            hit=grid.ray_cast(Vector((x,yy,.688)),Vector((0,0,-1)),.089)[0]
            gap=grid.ray_cast(Vector((x,yy+.0115,.688)),Vector((0,0,-1)),.089)[0]
            assert hit is not None and gap is None,(typ,x,j)
            hits.append(hit.z);opened.append(yy+.0115)
    sample=one('Pancake true baked lower folded shell')
    up=one('Pancake upper turned-over shell and irregular edge')
    lowerz=min(v.z for v in geometry(sample)[0])
    upperz=max(v.z for v in geometry(up)[0])
    assert upperz-lowerz>.030
    topR=max(hits)
    assert abs(lowerz-topR)<.0002,(typ,lowerz,topR)
    report[typ]=dict(pans=pan_metrics,shell_samples=len(shell),shell_gauge_range_m=[min(shell),max(shell)],
                     separated_lid_support_vertex_nearness_m=[min(left),min(right)],rack_clear_apertures=len(opened),rack_wire_hits=len(hits),
                     folded_sample_thickness_m=upperz-lowerz,folded_sample_rack_gap_m=lowerz-topR)
    assert min(left)<.006 and min(right)<.006,(typ,left,right)
print(json.dumps(report,indent=2))
