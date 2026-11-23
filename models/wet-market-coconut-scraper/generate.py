"""Original guarded illustrative wet-market coconut scraper; no operating model."""
import math
import sys
from collections import defaultdict
from pathlib import Path
import bmesh
import bpy
from mathutils import Vector

ID="wet-market-coconut-scraper"
R=Path(__file__).resolve().parent
for f in ("exports","previews"):(R/f).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system="METRIC"
scene.render.fps=24;scene.frame_start=0;scene.frame_end=48
g={}
for n in ("01 Merchant workboard and clamped casting","02 Shielded housings and stationary bearings",
          "03 Staged coconut shells and open receiver bowl","04 Bilingual illustration label",
          "05 Captive rotating crank and scraper group","06 Studio only"):
    c=bpy.data.collections.new(n);scene.collection.children.link(c);g[n[:2]]=c

def mat(n,c,r=.47,m=0,a=1):
    o=bpy.data.materials.new(n);o.use_nodes=True;o.diffuse_color=(*c,a)
    s=o.node_tree.nodes.get("Principled BSDF");s.inputs["Base Color"].default_value=(*c,1)
    s.inputs["Roughness"].default_value=r;s.inputs["Metallic"].default_value=m;s.inputs["Alpha"].default_value=a
    if a<1:o.surface_render_method="BLENDED"
    return o
def att(o,n,k,m=None):
    o.name=n
    for c in list(o.users_collection):c.objects.unlink(o)
    g[k].objects.link(o)
    if m:o.data.materials.append(m)
    return o
def box(n,p,d,m,k,r=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=att(bpy.context.object,n,k,m)
    o.dimensions=d;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if r>=.008:
        b=o.modifiers.new("Cast edge radius","BEVEL");b.width=r;b.segments=2 if r>=.027 else 1;b.harden_normals=True
        b=o.modifiers.new("Weighted corner normals","WEIGHTED_NORMAL");b.keep_sharp=True
    return o
def mesh(n,v,f,m,k):
    me=bpy.data.meshes.new(n);me.from_pydata(v,[],f);me.update()
    b=bmesh.new();b.from_mesh(me);bmesh.ops.recalc_face_normals(b,faces=list(b.faces));b.to_mesh(me);b.free()
    return att(bpy.data.objects.new(n,me),n,k,m)
def cyl(n,p,r,d,m,k,axis="z",s=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=s,radius=r,depth=d,location=p)
    o=att(bpy.context.object,n,k,m)
    if axis=="x":o.rotation_euler.y=math.pi/2
    if axis=="y":o.rotation_euler.x=math.pi/2
    for f in o.data.polygons:f.use_smooth=len(f.vertices)==4
    return o
def turns(n,p,path,m,k,N=24,axis="z"):
    verts=[]
    for r,z in path:
        for i in range(N):
            a=math.tau*i/N;x=r*math.cos(a);y=r*math.sin(a)
            verts.append((z,x,y) if axis=="x" else (x,y,z))
    fs=[]
    for i in range(len(path)):
        j=(i+1)%len(path)
        for a in range(N):
            b=(a+1)%N;fs.append((i*N+a,i*N+b,j*N+b,j*N+a))
    o=mesh(n,verts,fs,m,k);o.location=p
    for f in o.data.polygons:f.use_smooth=True
    return o
def bar(n,a,b,w,h,m,k,r=0):
    a,b=Vector(a),Vector(b);o=box(n,(a+b)/2,(w,h,(b-a).length),m,k,r)
    o.rotation_euler=(b-a).to_track_quat("Z","Y").to_euler();return o
def text(n,t,p,s,m):
    bpy.ops.object.text_add(location=p,rotation=(math.pi/2,0,0));o=att(bpy.context.object,n,"04",m)
    o.data.body=t;o.data.align_x="CENTER";o.data.align_y="CENTER";o.data.size=s;o.data.resolution_u=2
    return o
def parent(o,p):
    bpy.context.view_layer.update();w=o.matrix_world.copy();o.parent=p;o.matrix_world=w;return o

oak=mat("Used rich meranti wood bench",(.31,.143,.067),.72)
board=mat("Honey marked reusable preparation board",(.455,.265,.125),.67)
deep=mat("Deep rough wood seam and carbon rubber",(.060,.047,.038),.72)
green=mat("Weathered deep jade cast body",(.040,.190,.131),.51,.22)
ink=mat("Dull evergreen structural casing",(.037,.101,.085),.54,.23)
metal=mat("Worn satin stainless",(.37,.45,.413),.42,.51)
brass=mat("Warm matte aged gear and bowl alloy",(.64,.354,.102),.46,.52)
yellow=mat("Contrasting warm amber demonstration crank grip",(.95,.342,.032),.49)
ivory=mat("Ivory coconut flesh and fiducial",(.857,.792,.585),.64)
tan=mat("Mid brown clean coconut shell",(.265,.120,.043),.83)
fiber=mat("Pale tan shell fibers",(.438,.237,.097),.84)
cover=mat("Marked clear protective demo shield",(.68,.84,.80),.22,0,.10)
paper=mat("Warm pale bilingual marker",(.87,.809,.662),.61)

# Footprint and an independent compact working/preparation surface.
box("Single heavy rounded timber workboard",(.027,0,.034),(1.274,.796,.068),oak,"01",.032)
for x in (-.552,-.160,.256,.553):
    box("Broad abrasion board seams",(x,-.012,.068),(.006,.718,.0035),deep,"01")
box("Small raised service preparation inset",(-.350,-.142,.090),(.424,.388,.045),board,"01",.023)
box("Inset top ridge worn pale",(-.349,-.311,.108),(.355,.010,.008),fiber,"01")
for y in (-.091,.245):
    box("Cast base anchoring dovetail",(-.034,y,.090),(.369,.091,.049),green,"01",.017)
    for x in (-.164,.096):cyl("Recessed mounting head",(x,y,.118),.015,.010,metal,"01",s=10)
box("Smoothed cast-down main mounting plinth",(-.056,.064,.144),(.309,.210,.084),green,"01",.024)
box("Distinct vertical bearing-casting support",(-.091,.065,.254),(.173,.181,.249),green,"01",.028)
for y in (-.007,.130):
    bar("Diagonal triangular form at bearing foot",(-.170,y,.130),(-.131,y,.358),.040,.032,ink,"01")
box("Clamp fixed outer bench jaw",(-.073,.325,.093),(.152,.132,.083),ink,"01",.019)
cyl("Robust context clamp stud",(-.072,.336,.058),.019,.069,metal,"01",s=12)
bar("Clamp cross-grip under rear edge",(-.148,.337,.033),(.005,.337,.033),.018,.018,metal,"01")
box("Plate backing on bench front",(.057,-.365,.095),(.426,.028,.057),ink,"04",.008)
box("Bilingual plate face",(.057,-.381,.096),(.404,.012,.047),paper,"04",.010)
text("Malay primary equipment label","KUKUR KELAPA",(.057,-.388,.105),.022,ink)
text("English secondary equipment label","COCONUT SCRAPER",(.057,-.388,.085),.014,ink)

# Two distinct parallel shafts, 20 and 10 teeth at a conceptual opposite ratio.
ay=.074; cz=.235; rz=.373
for name,z,r in (("Input",cz,.049),("Rotor",rz,.048)):
    cyl(name+" fixed green bearing shell",(-.038,ay,z),r,.188,green,"02","x",20)
    cyl(name+" bolted stationary sleeve",(.025,ay,z),r*.82,.032,metal,"02","x",20)
# Guard perimeter around the gear faces plus a separate transparent top rotor visor.
def arc(shx,y,z,w,h,m,k):
    for a,(p,q) in enumerate(zip(shx,shx[1:])):
        aa,bb=p*math.tau,q*math.tau
        bar("Rounded guard perimeter member",(y[0],y[1]+w*math.cos(aa),z+h*math.sin(aa)),
            (y[0],y[1]+w*math.cos(bb),z+h*math.sin(bb)),.025,.025,m,k)
arc([i/16 for i in range(17)],(.162,ay),.291,.125,.183,ink,"02")
guard=cyl("Colorless full clear mechanical gear shield",(.153,ay,.291),.124,.013,cover,"02","x",32)
guard.scale.x=1.48
for y in (ay-.109,ay+.109):
    for z in (.192,.389):cyl("Clear gear shield fixing cap",(.165,y,z),.012,.019,metal,"02","x",10)
# A semi-circular clear visor physically spans above the rounded display rotor.
rv=[]; rf=[]
for i in range(11):
    a=i*math.pi/10
    y=ay+.086*math.cos(a);z=rz+.086*math.sin(a)
    rv.extend(((.187,y,z),(.328,y,z)))
for i in range(10):rf.append((2*i,2*i+1,2*i+3,2*i+2))
visor=mesh("Arched local rotor visor",rv,rf,cover,"02")
sol=visor.modifiers.new("Clear guard wall","SOLIDIFY");sol.thickness=.008
for x in (.187,.326):
    arc([i/20 for i in range(11)],(x,ay),rz,.088,.088,green,"02")
for y in (ay-.09,ay+.09):
    box("Fixed casing cheek below visor",( .200,y,.344),(.078,.032,.060),green,"02",.008)

crank=att(bpy.data.objects.new("KELAPA_CRANK_HANDLE",None),"KELAPA_CRANK_HANDLE","05")
crank.location=(.214,ay,cz)
rotor=att(bpy.data.objects.new("KELAPA_SCRAPER_ROTOR",None),"KELAPA_SCRAPER_ROTOR","05")
rotor.location=(.097,ay,rz)
parent(cyl("Input rotating axle through bearing and guard",(.123,ay,cz),.020,.251,metal,"05","x",16),crank)
parent(cyl("Opposing captive rotor drive shaft",(.157,ay,rz),.021,.216,metal,"05","x",16),rotor)

def gear(n,x,y,z,pitch,teeth,m,around,phase):
    v=[]
    for xx in (x-.012,x+.012):
        for j in range(teeth):
            for k,f in enumerate((.10,.27,.63,.80)):
                a=math.tau*(j+f)/teeth+phase
                rr=pitch+(.005 if k in (1,2) else -.006)
                v.append((xx,y+rr*math.cos(a),z+rr*math.sin(a)))
    N=teeth*4
    f=[tuple(range(N-1,-1,-1)),tuple(range(N,2*N))]
    for j in range(N):
        nn=(j+1)%N;f.append((j,nn,nn+N,j+N))
    parent(mesh(n,v,f,m,"05"),around)
    parent(cyl(n+" central steel boss",(x+.017,y,z),pitch*.26,.019,metal,"05","x",14),around)
gear("Captive twenty-tooth driver visible through guard",.102,ay,cz,.092,20,brass,crank,0)
gear("Captive ten-tooth follower visible through guard",.102,ay,rz,.046,10,brass,rotor,math.tau/20)
# Crank throw starts up/front, then integrates 270 degrees to a visibly different pose.
tip=(.242,ay-.111,cz+.070)
parent(bar("One round-edged contrasting crank arm",(.241,ay,cz),tip,.033,.033,ink,"05",.010),crank)
parent(cyl("Large amber hand-crank fiducial grip",(.295,tip[1],tip[2]),.026,.098,yellow,"05","x",20),crank)
parent(cyl("Small silver end cap on knob",(.347,tip[1],tip[2]),.014,.011,metal,"05","x",14),crank)
parent(turns("Rounded non-cutting demonstration scraper rotor",(.219,ay,rz),
    [(.006,0),(.041,0),(.054,.020),(.057,.055),(.051,.083),(.032,.108),(.006,.115)],metal,"05",24,"x"),rotor)
for i in range(9):
    a=i*math.tau/9
    y=ay+.039*math.cos(a);z=rz+.039*math.sin(a)
    parent(cyl("Rounded visual rotor nub",(.306,y,z),.006,.010,metal,"05","x",10),rotor)
parent(box("Ivory rotor visual index stripe",(.330,ay-.020,rz+.016),(.011,.047,.009),ivory,"05"),rotor)
parent(cyl("Amber rotor fiducial dot",(.334,ay+.028,rz+.019),.010,.008,yellow,"05","x",14),rotor)
# Smooth fractional rotations with a preserved 2:1 relative signed phase.
def anim(o,a):
    for f,u in ((0,0),(5,0),(13,.15),(23,.45),(33,.75),(43,1),(48,1)):
        o.rotation_euler.x=a*u
        o.keyframe_insert(data_path="rotation_euler",frame=f,group="Fictional crank demonstration")
    action=o.animation_data.action;action.name=o.name+"_source_turn"
    track=o.animation_data.nla_tracks.new();track.name="KELAPA_CRANK_TURN"
    track.strips.new("Single staged rotation",0,action);o.animation_data.action=None
anim(crank,math.pi*1.5)
anim(rotor,-math.pi*3)

# Dry context only: staged halves with a real cavity and an empty receiving bowl.
for x,y,a in ((-.398,-.160,.13),(-.275,-.186,-.15)):
    o=turns("Open brown coconut half shell",(x,y,.116),
         [(.008,0),(.037,.005),(.067,.023),(.083,.052),(.089,.083),(.081,.085),(.058,.069),(.033,.042),(.008,.025)],tan,"03",22)
    i=turns("Ivory hollow interior coconut layer",(x,y,.118),
         [(.010,.022),(.033,.040),(.057,.066),(.082,.083),(.075,.083),(.056,.072),(.032,.053),(.01,.035)],ivory,"03",22)
    o.rotation_euler.x=a;i.rotation_euler.x=a
    lip=turns("Fine weathered fibre shell lip",(x,y,.117),
         [(.081,.080),(.089,.080),(.087,.083),(.079,.083)],fiber,"03",22)
    lip.rotation_euler.x=a
turns("Empty satin bowl with true open concave interior",(.512,-.026,.070),
      [(.006,0),(.073,0),(.105,.019),(.134,.057),(.149,.100),(.145,.105),
       (.137,.099),(.123,.057),(.096,.025),(.065,.010),(.006,.010)],brass,"03",32)
turns("Raised bright lip on empty collecting bowl",(.512,-.026,.070),
      [(.140,.095),(.148,.096),(.149,.102),(.145,.105),(.139,.102)],metal,"03",32)

def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat("-Z","Y").to_euler()
floor=mat("Soft neutral studio floor",(.134,.167,.151),.79)
box("Studio only shadow floor",(0,0,-.035),(150,150,.061),floor,"06")
bpy.ops.object.camera_add(location=(2.57,-3.13,2.45))
cam=att(bpy.context.object,"Orthographic hardware editorial camera","06")
aim(cam,(.019,-.007,.220));cam.data.type="ORTHO";cam.data.ortho_scale=1.64;scene.camera=cam
for n,p,e,c,s in (
    ("Large warm overhead key",(1.84,-2.79,3.49),467,(1,.866,.699),2.2),
    ("Cool local detail fill",(-2,-1.88,2.09),301,(.71,.89,1),2.2),
    ("Warm side gear rim",(2.07,1.57,2.29),380,(.99,1,.78),2.0)):
    bpy.ops.object.light_add(type="AREA",location=p);o=att(bpy.context.object,n,"06")
    o.data.energy=e;o.data.color=c;o.data.shape="DISK";o.data.size=s;aim(o,(0,0,.29))
scene.world=bpy.data.worlds.new("Neutral studio ambient");scene.world.use_nodes=True
bg=scene.world.node_tree.nodes["Background"];bg.inputs[0].default_value=(.45,.54,.62,1);bg.inputs[1].default_value=.38
scene.render.engine="CYCLES";scene.cycles.samples=26;scene.cycles.use_denoising=True
scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.view_settings.view_transform="AgX";scene.view_settings.exposure=-.25;scene.render.image_settings.file_format="PNG"
scene.render.filepath=str(R/"previews"/"studio.png")
scene.frame_set(0);bpy.ops.object.select_all(action="DESELECT")
bpy.ops.wm.save_as_mainfile(filepath=str(R/(ID+".blend")))
if "--skip-render" not in sys.argv:
    bpy.ops.render.render(write_still=True)
    if "--turn-review" in sys.argv:
        cam.location=(2.74,-1.23,1.31);aim(cam,(.154,.048,.282));cam.data.ortho_scale=.76
        for label,f in (("ready",0),("mid-turn",23),("turned",48)):
            scene.frame_set(f);scene.render.filepath=str(R/"previews"/(label+".png"));bpy.ops.render.render(write_still=True)
        scene.frame_set(0)

selected=[]
for k,c in g.items():
    if k=="06":continue
    if k=="05":
        # Batch like-material moving descendants without changing their parents.
        movers=defaultdict(list)
        for o in list(c.objects):
            if o.type=="EMPTY":selected.append(o);continue
            movers[(o.parent.name,o.data.materials[0].name)].append(o)
        for (axis,style), objects in sorted(movers.items()):
            bpy.ops.object.select_all(action="DESELECT")
            for ob in objects:ob.select_set(True)
            h=objects[0];bpy.context.view_layer.objects.active=h
            if len(objects)>1:
                # Apply any modifiers before joining so the authored edge
                # radii still match the Blender preview.
                for ob in objects:
                    bpy.ops.object.select_all(action="DESELECT")
                    ob.select_set(True);bpy.context.view_layer.objects.active=ob
                    if ob.modifiers:bpy.ops.object.convert(target="MESH")
                bpy.ops.object.select_all(action="DESELECT")
                for ob in objects:ob.select_set(True)
                bpy.context.view_layer.objects.active=h
                bpy.ops.object.join()
            h.name=axis+" assembly | "+style;selected.append(h)
        continue
    by=defaultdict(list)
    for o in list(c.objects):
        if o.modifiers or o.type=="FONT":
            bpy.ops.object.select_all(action="DESELECT")
            o.select_set(True);bpy.context.view_layer.objects.active=o
            bpy.ops.object.convert(target="MESH");o=bpy.context.view_layer.objects.active
        if o.data.materials[0].diffuse_color[3]<1:selected.append(o)
        else:by[o.data.materials[0].name].append(o)
    for m,a in sorted(by.items()):
        bpy.ops.object.select_all(action="DESELECT")
        for o in a:o.select_set(True)
        h=a[0];bpy.context.view_layer.objects.active=h
        if len(a)>1:bpy.ops.object.join()
        h.name=c.name[3:]+" | "+m;selected.append(h)
bpy.ops.object.select_all(action="DESELECT")
for o in selected:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(R/"exports"/(ID+".glb")),export_format="GLB",
    use_selection=True,export_animations=True,export_animation_mode="NLA_TRACKS",
    export_force_sampling=True,export_cameras=False,export_lights=False,export_texcoords=False)
