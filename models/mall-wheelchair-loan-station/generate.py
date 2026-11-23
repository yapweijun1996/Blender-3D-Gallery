"""Original static compact mall loan dock with visibly folded transport chair."""
import math
import sys
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

SLUG="mall-wheelchair-loan-station"
D=Path(__file__).resolve().parent
for f in ("exports","previews"):
    (D/f).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system="METRIC"
groups={}
for name in ("01 Low-profile docking bay and curb","02 Bilingual loan and return sign",
             "03 Collapsed chair frame and folding pivots","04 Upholstery and padded grips",
             "05 Main and caster wheels","06 Cup tray and docking bumper",
             "07 Studio only"):
    coll=bpy.data.collections.new(name)
    scene.collection.children.link(coll)
    groups[name[:2]]=coll

def material(name,color,r=.49,metal=0):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    m.diffuse_color=(*color,1)
    p=m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=(*color,1)
    p.inputs["Roughness"].default_value=r
    p.inputs["Metallic"].default_value=metal
    return m

def obj(o,n,key,m=None):
    o.name=n
    for c in list(o.users_collection): c.objects.unlink(o)
    groups[key].objects.link(o)
    if m: o.data.materials.append(m)
    return o

def cube(n,loc,sz,m,key,r=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=obj(bpy.context.object,n,key,m)
    o.dimensions=sz
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if r>=.008:
        bevel=o.modifiers.new("Smooth fabricated edges","BEVEL")
        bevel.width=r
        bevel.segments=2 if r>=.022 else 1
        bevel.harden_normals=True
        normal=o.modifiers.new("Weighted landing normals","WEIGHTED_NORMAL")
        normal.keep_sharp=True
    return o

def mesh(n,v,faces,m,key):
    me=bpy.data.meshes.new(n); me.from_pydata(v,[],faces); me.update()
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    return obj(bpy.data.objects.new(n,me),n,key,m)

def tube(n,points,r,m,key,segs=8):
    p=[Vector(a) for a in points];v=[]
    for k,pt in enumerate(p):
        delta=(p[min(len(p)-1,k+1)]-p[max(0,k-1)]).normalized()
        ref=Vector((1,0,0)) if abs(delta.y)>.975 else Vector((0,1,0))
        a=delta.cross(ref).normalized();b=delta.cross(a)
        for j in range(segs):
            t=j*math.tau/segs;v.append(pt+r*(a*math.cos(t)+b*math.sin(t)))
    fs=[tuple(reversed(range(segs)))]
    for k in range(len(p)-1):
        for j in range(segs):
            i=(j+1)%segs; fs.append((k*segs+j,k*segs+i,(k+1)*segs+i,(k+1)*segs+j))
    fs.append(tuple(range((len(p)-1)*segs,len(p)*segs)))
    o=mesh(n,v,fs,m,key)
    for f in o.data.polygons: f.use_smooth=len(f.vertices)==4
    return o

def cylinder(n,l,r,h,m,key,xx=False,k=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=k,radius=r,depth=h,location=l)
    o=obj(bpy.context.object,n,key,m)
    if xx:o.rotation_euler.y=math.pi/2
    for f in o.data.polygons:f.use_smooth=len(f.vertices)==4
    return o

def wheel(n,x,y,z,profile,m,key="05",segs=24):
    # The profile is an explicit closed section. Real interior voids remain.
    v=[]
    for a,r in profile:
        for k in range(segs):
            theta=math.tau*k/segs
            v.append((x+a,y+r*math.cos(theta),z+r*math.sin(theta)))
    f=[]
    for i in range(len(profile)):
        p=(i+1)%len(profile)
        for j in range(segs):
            k=(j+1)%segs
            f.append((i*segs+j,i*segs+k,p*segs+k,p*segs+j))
    o=mesh(n,v,f,m,key)
    for p in o.data.polygons:p.use_smooth=True
    return o

petrol=material("Petrol green enamel docking accents",(.052,.231,.202),.48,.18)
pine=material("Deep teal writable sign and frame",(.026,.108,.106),.47,.17)
slate=material("Charcoal floor rubber",(.110,.136,.136),.71)
pale=material("Warm neutral ceramic docking surface",(.56,.53,.424),.62)
sand=material("Light limestone wayfinding panel",(.859,.813,.680),.66)
orange=material("Warm amber neutral docking stripes",(.70,.34,.057),.49)
navy=material("Indigo folded textile and storage sling",(.045,.103,.207),.73)
lining=material("Dim blue piping and fold seam",(.123,.223,.366),.64)
steel=material("Brushed aluminium tubing",(.47,.55,.522),.38,.53)
silver=material("Lathed satin push rims",(.62,.65,.60),.36,.56)
tire=material("Graphite tire rubber and push handles",(.025,.033,.039),.69)
hardware=material("Dark graphite hardware",(.045,.067,.072),.56,.26)

# Continuous low docking platform with open straight rollout, restrained stripes.
cube("Independent reusable terracotta-tone platform",(0,0,.040),(1.243,1.139,.080),slate,"01",.032)
cube("Broad neutral docking deck",(0,.013,.075),(1.178,1.067,.024),pale,"01",.017)
cube("Front shallow dark transition edge",(0,-.521,.057),(1.145,.063,.050),slate,"01",.009)
for x in (-.103,.433):
    cube("Thin marked bay boundary line",(x,-.028,.089),(.023,.929,.003),petrol,"01")
    cube("Amber portion of neutral docking stripe",(x,-.399,.091),(.024,.122,.003),orange,"01")
cube("Short open floor threshold marking",(.169,-.471,.089),(.302,.023,.004),petrol,"01")
for x in (.12,.205):
    vs=[(x-.029,-.365,.090),(x,-.320,.090),(x+.029,-.365,.090),(x+.014,-.365,.090),(x+.014,-.405,.090),(x-.014,-.405,.090),(x-.014,-.365,.090)]
    mesh("Simple directional aid on the empty front of the bay",vs,[tuple(range(len(vs)))],petrol,"01")
for x in (-.127,.459):
    cube("Docking bumper floor shoe",(x,.406,.103),(.098,.136,.030),hardware,"06",.009)
tube("Rear docking U-shape side protectors and nested rear bumper",
     [(-.125,.418,.117),(-.125,.449,.347),(-.103,.465,.393),
      (.434,.465,.393),(.459,.448,.350),(.459,.420,.117)],.023,petrol,"06",10)
cube("Replaceable dark contact strip behind rear chair rails",(.169,.438,.393),(.386,.026,.044),tire,"06",.009)
cube("Recessed low rear wheel stop at platform",(.169,.420,.111),(.400,.135,.044),petrol,"06",.012)
for x in (-.033,.367):
    cube("Wheel stop amber cap marker",(x,.397,.131),(.061,.066,.008),orange,"06")
cube("Slender side shelf on dock upright",(-.250,.355,.609),(.173,.155,.027),petrol,"06",.012)
cube("Lip of shallow storage pocket",(-.250,.279,.624),(.179,.019,.029),hardware,"06",.008)

# An independent side-mounted bilingual wayfinding unit with a pictogram.
cube("Side weight plate under loan stand",(-.410,.369,.109),(.249,.229,.038),hardware,"02",.011)
cube("Side post well clear of roll-out path",(-.410,.392,.652),(.064,.068,1.075),petrol,"02",.010)
cube("Rounded placard cover",(-.324,.344,1.131),(.549,.055,.230),pine,"02",.025)
cube("Light inlaid loan placard",(-.324,.310,1.132),(.511,.016,.188),sand,"02",.012)
def text(name,v,x,z,sz,m=pine):
    bpy.ops.object.text_add(location=(x,.3005,z),rotation=(math.pi/2,0,0))
    o=obj(bpy.context.object,name,"02",m)
    o.data.body=v
    o.data.align_x="CENTER"
    o.data.align_y="CENTER"
    o.data.size=sz
    o.data.resolution_u=2
text("Primary Malay wheelchair loan label","PINJAMAN",-.269,1.181,.039)
text("Malay wheelchair name","KERUSI RODA",-.269,1.139,.039)
text("English wheelchair loan label","WHEELCHAIR LOAN",-.269,1.091,.026)
cube("Warm lower editorial accent",(-.269,.299,1.067),(.365,.005,.004),orange,"02")
# Original small geometry wheelchair symbol, not a depiction of a specific installation.
circle=[(-.507+.047*math.cos(k*math.pi/11),.298,1.108+.047*math.sin(k*math.pi/11)) for k in range(3,20)]
tube("Rounded pictogram wheel mark",circle,.0047,pine,"02",6)
head=cylinder("Pictogram person dot",(-.525,.297,1.169),.011,.005,pine,"02",k=10)
head.rotation_euler.x=math.pi/2
tube("Pictogram single seated silhouette",[(-.525,.298,1.152),(-.520,.298,1.114),(-.479,.298,1.114),(-.466,.298,1.084)],.0047,pine,"02",7)

# Folded chair centre is x=.165. Main axle is aft under the narrow real folded seat.
cx=.166
deck=.089
rear_y=.143
rear_z=.374
for s in (-1,1):
    side="Left " if s<0 else "Right "
    x=cx+s*.102
    coords=[(x,.192,1.023),(x,.083,1.024),(x,.064,.941),(x,.072,.787),(x,.115,.561),
            (x,.112,.296),(x,-.246,.259),(x,-.317,.315),(x,-.297,.487)]
    tube(side+"bent continuous side frame handle/rear/caster stays",coords,.0165,steel,"03",9)
    tube(side+"side seat frame member",[(x,.102,.651),(x,-.246,.635),(x,-.284,.579),(x,-.295,.479)],.0155,steel,"03",9)
    tube(side+"rubber attendant push handle",[(x,.171,1.023),(x,.206,1.023),(x,.250,1.022)],.024,tire,"04",9)
    tube(side+"short armrest support",[(x,.080,.645),(x,.054,.745),(x,-.193,.743),(x,-.208,.640)],.015,steel,"03",8)
    cube(side+"short black armrest upholstered pad",(x,-.064,.756),(.052,.266,.043),tire,"04",.015)
    tube(side+"collapsed X brace member",[(cx+s*.092,.035,.344),(cx-s*.081,-.094,.655)],.013,steel,"03",8)
    cylinder(side+"visible folding pivot at lower side frame",(x,.034,.369),.025,.046,hardware,"03",True,12)
    cylinder(side+"seat hinge pin",(x,-.042,.646),.021,.042,steel,"03",True,12)
    tube(side+"swung-up footrest support",[(x,-.276,.503),(x,-.382,.414),(x,-.387,.332)],.012,steel,"03",8)
    footpad=cube(side+"slim stowed foot plate",(x,-.398,.368),(.062,.032,.144),hardware,"03",.011)
    footpad.rotation_euler.x=.19
    for iz in (.321,.354,.392,.421):
        cube(side+"folded footplate ridged groove",(x,-.416,iz),(.054,.006,.007),tire,"03")
    # Real clearance slots and opening in both wheels. Spokes remain separately editable.
    wx=cx+s*.132
    wt=[(-.025,.245),(-.026,.268),(-.019,.282),(-.009,.286),(.009,.286),(.019,.282),(.026,.268),(.025,.245)]
    wheel(side+"spoke wheel multi-radius black tyre",wx,rear_y,rear_z,wt,tire)
    wheel(side+"inner alloy rim",wx,rear_y,rear_z,[(-.021,.242),(-.020,.254),(.020,.254),(.021,.242)],steel)
    wheel(side+"separate bright push rim",wx+s*.051,rear_y,rear_z,[(-.008,.230),(-.007,.242),(.007,.242),(.008,.230)],silver)
    cylinder(side+"real axle wheel hub",(wx,rear_y,rear_z),.039,.085,steel,"05",True,k=16)
    cylinder(side+"outer hub screw-on cap",(wx+s*.047,rear_y,rear_z),.025,.016,hardware,"05",True,k=12)
    for j in range(12):
        a=j*math.tau/12
        b=a+(+.15 if j%2==0 else -.15)
        tube(side+"light crossed spoke",[(wx+s*.019,rear_y+.028*math.cos(b),rear_z+.028*math.sin(b)),
             (wx+s*.010,rear_y+.247*math.cos(a),rear_z+.247*math.sin(a))],.004,steel,"05",5)
    for angle in (0,math.pi/2,math.pi,math.pi*1.5):
        y,z=rear_y+.235*math.cos(angle),rear_z+.235*math.sin(angle)
        tube(side+"push-rim standoff",[(wx+s*.014,y,z),(wx+s*.048,y,z)],.006,steel,"05",6)
    yc=-.309
    zc=.155
    fmx=x+s*.021
    tube(side+"front caster fork from stem",
         [(fmx,yc,.323),(fmx+s*.028,yc,.236),(fmx+s*.028,yc,.168)],.015,steel,"05",8)
    wheel(side+"front caster tread",fmx,yc,zc,
        [(-.017,.041),(-.018,.056),(-.013,.066),(.013,.066),(.018,.056),(.017,.041)],tire,segs=16)
    cylinder(side+"front caster hub", (fmx,yc,zc),.042,.033,steel,"05",True,k=12)

# The textile collapses inward between steel rails. No flat/open usable seat.
def folded_patch(n,lines,m):
    verts=[a for row in lines for a in row]
    L=len(lines[0]);f=[]
    for j in range(len(lines)-1):
        for k in range(L-1):f.append((j*L+k,j*L+k+1,(j+1)*L+k+1,(j+1)*L+k))
    ob=mesh(n,verts,f,m,"04")
    for p in ob.data.polygons:p.use_smooth=True
    mod=ob.modifiers.new("Subtle fabric edge thickness","SOLIDIFY")
    mod.thickness=.0035
folded_patch("Hanging indigo seat sling with central fold",[
    [(cx-.10,-.243,.640),(cx-.055,-.247,.457),(cx,-.257,.423),(cx+.060,-.243,.479),(cx+.10,-.240,.640)],
    [(cx-.10,-.071,.646),(cx-.059,-.07,.470),(cx,-.081,.437),(cx+.060,-.078,.471),(cx+.10,-.065,.646)],
    [(cx-.10,.094,.655),(cx-.06,.089,.493),(cx,.078,.455),(cx+.058,.091,.493),(cx+.10,.095,.655)]],navy)
folded_patch("Folded backrest with inward pleat and uneven fabric",[
    [(cx-.100,.083,.950),(cx-.055,.004,.924),(cx,-.027,.906),(cx+.055,.008,.922),(cx+.100,.083,.950)],
    [(cx-.100,.093,.806),(cx-.049,.002,.799),(cx,-.032,.779),(cx+.047,.013,.805),(cx+.100,.095,.806)],
    [(cx-.100,.111,.662),(cx-.052,.021,.666),(cx,-.007,.651),(cx+.055,.031,.669),(cx+.100,.113,.662)]],navy)
tube("Indigo centre pleat visible in folded backrest",[(cx,-.029,.909),(cx,-.034,.781),(cx,-.009,.650)],.007,lining,"04",7)
tube("Curved sewn upper piping on folded seat",[(cx-.100,-.244,.640),(cx-.055,-.249,.458),(cx,-.259,.425),
     (cx+.058,-.246,.478),(cx+.100,-.239,.641)],.005,lining,"04",7)

def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat("-Z","Y").to_euler()
floor=material("Neutral warm studio ground",(.159,.179,.182),.73)
cube("Studio shadow receiver only",(0,0,-.033),(160,160,.06),floor,"07")
bpy.ops.object.camera_add(location=(1.60,-3.55,1.98))
cam=obj(bpy.context.object,"Editorial studio camera","07")
aim(cam,(-.013,.009,.605))
cam.data.type="ORTHO";cam.data.ortho_scale=1.96
scene.camera=cam
for n,p,e,c,sz in (
    ("Large warm key",(1.8,-3.2,3.7),520,(1,.885,.732),2.6),
    ("Broad cool fill",(-3.6,-2.0,2.8),370,(.74,.89,1),3.3),
    ("Back highlight for titanium",(2.25,2.56,3.7),580,(.92,1,.86),2.65),
):
    bpy.ops.object.light_add(type="AREA",location=p)
    o=obj(bpy.context.object,n,"07")
    o.data.energy=e;o.data.color=c;o.data.shape="DISK";o.data.size=sz
    aim(o,(0,0,.58))
scene.world=bpy.data.worlds.new("Neutral studio ambience")
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes["Background"]
bg.inputs[0].default_value=(.45,.51,.57,1)
bg.inputs[1].default_value=.33
scene.render.engine="CYCLES"
scene.cycles.samples=24
scene.cycles.use_denoising=True
scene.render.resolution_x=720
scene.render.resolution_y=720
scene.render.resolution_percentage=100
scene.view_settings.view_transform="AgX"
scene.render.image_settings.file_format="PNG"
scene.render.filepath=str(D/"previews"/"studio.png")
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.wm.save_as_mainfile(filepath=str(D/(SLUG+".blend")))
if "--skip-render" not in sys.argv:
    bpy.ops.render.render(write_still=True)
    if "--dock-review" in sys.argv:
        cam.location=(2.95,-2.44,1.69)
        aim(cam,(.04,.02,.558))
        cam.data.ortho_scale=1.82
        scene.render.filepath=str(D/"previews"/"dock-review.png")
        bpy.ops.render.render(write_still=True)

selected=[]
for key, group in groups.items():
    if key=="07": continue
    by=defaultdict(list)
    for o in list(group.objects):
        if o.modifiers or o.type=="FONT":
            bpy.ops.object.select_all(action="DESELECT")
            o.select_set(True)
            bpy.context.view_layer.objects.active=o
            bpy.ops.object.convert(target="MESH")
            o=bpy.context.view_layer.objects.active
        by[o.data.materials[0].name].append(o)
    for name, obs in sorted(by.items()):
        bpy.ops.object.select_all(action="DESELECT")
        for o in obs:o.select_set(True)
        active=obs[0]
        bpy.context.view_layer.objects.active=active
        if len(obs)>1:bpy.ops.object.join()
        active.name=group.name[3:]+" | "+name
        selected.append(active)
bpy.ops.object.select_all(action="DESELECT")
for o in selected:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(D/"exports"/(SLUG+".glb")),
    export_format="GLB",use_selection=True,export_animations=False,export_texcoords=False,
    export_cameras=False,export_lights=False)
