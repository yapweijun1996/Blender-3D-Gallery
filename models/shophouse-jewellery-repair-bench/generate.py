"""Original jeweller's service bench, shaped worktop, tools and task lamp; static GLB."""
import math
import sys
from collections import defaultdict
from pathlib import Path
import bmesh
import bpy
from mathutils import Vector

ID="shophouse-jewellery-repair-bench"
P=Path(__file__).resolve().parent
for f in ("exports","previews"):(P/f).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system="METRIC"
C={}
for n in ("01 Shaped worktop, frame and recessed drawers","02 V-notch bench pin and filing tray",
          "03 Mandrels, rings and hand tools","04 Articulated task-light assembly",
          "05 Bilingual repair placard","06 Studio only"):
    c=bpy.data.collections.new(n);scene.collection.children.link(c);C[n[:2]]=c

def mat(n,c,r=.50,m=0):
    o=bpy.data.materials.new(n);o.use_nodes=True;o.diffuse_color=(*c,1)
    p=o.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=(*c,1)
    p.inputs["Roughness"].default_value=r
    p.inputs["Metallic"].default_value=m
    return o
def link(o,n,k,m=None):
    o.name=n
    for c in list(o.users_collection):c.objects.unlink(o)
    C[k].objects.link(o)
    if m:o.data.materials.append(m)
    return o
def bevel(o,r):
    if r>=.007:
        b=o.modifiers.new("Edge rounding on worked surfaces","BEVEL")
        b.width=r;b.segments=2 if r>=.024 else 1;b.harden_normals=True
        b=o.modifiers.new("Weighted polished edge normals","WEIGHTED_NORMAL");b.keep_sharp=True
    return o
def box(n,p,d,m,k,r=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=link(bpy.context.object,n,k,m)
    o.dimensions=d;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return bevel(o,r)
def mesh(n,v,f,m,k):
    me=bpy.data.meshes.new(n);me.from_pydata(v,[],f);me.update()
    b=bmesh.new();b.from_mesh(me);bmesh.ops.recalc_face_normals(b,faces=list(b.faces));b.to_mesh(me);b.free()
    return link(bpy.data.objects.new(n,me),n,k,m)
def prism(n,xy,z0,z1,m,k,r=0):
    N=len(xy);v=[(x,y,z) for z in (z0,z1) for x,y in xy]
    f=[tuple(range(N-1,-1,-1)),tuple(range(N,2*N))]
    f += [(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)]
    return bevel(mesh(n,v,f,m,k),r)
def cyl(n,p,r,h,m,k,axis="z",N=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=N,radius=r,depth=h,location=p)
    o=link(bpy.context.object,n,k,m)
    if axis=="x":o.rotation_euler.y=math.pi/2
    if axis=="y":o.rotation_euler.x=math.pi/2
    for q in o.data.polygons:q.use_smooth=len(q.vertices)==4
    return o
def lathe(n,p,profile,m,k,N=24,axis="Z"):
    v=[]
    for r,z in profile:
        for j in range(N):
            a=math.tau*j/N;x=r*math.cos(a);y=r*math.sin(a)
            v.append((z,x,y) if axis=="X" else (x,y,z))
    f=[]
    for i in range(len(profile)):
        b=(i+1)%len(profile)
        for j in range(N):
            t=(j+1)%N;f.append((i*N+j,i*N+t,b*N+t,b*N+j))
    o=mesh(n,v,f,m,k);o.location=p
    for q in o.data.polygons:q.use_smooth=True
    return o
def bar(n,p,q,w,h,m,k,r=0):
    a,b=Vector(p),Vector(q);o=box(n,(a+b)/2,(w,h,(b-a).length),m,k,r)
    o.rotation_euler=(b-a).to_track_quat("Z","Y").to_euler();return o
def text(n,t,p,s,m):
    bpy.ops.object.text_add(location=p,rotation=(math.pi/2,0,0));o=link(bpy.context.object,n,"05",m)
    o.data.body=t;o.data.align_x="CENTER";o.data.align_y="CENTER";o.data.size=s;o.data.resolution_u=2
    return o

wood=mat("Used warm walnut worktop",(.33,.157,.073),.64)
edge=mat("Polished endgrain border",(.235,.106,.054),.62)
woodLite=mat("Honey ash bench-pin replaceable block",(.57,.344,.142),.66)
draw=mat("Old sage-green painted drawer fronts",(.095,.247,.190),.51)
deep=mat("Evergreen painted steel frame",(.026,.100,.084),.48,.22)
black=mat("Charcoal felt liner and grip",(.039,.055,.048),.84)
metal=mat("Cool brushed tool-grade steel",(.46,.54,.512),.43,.59)
brass=mat("Aged brass lamp and hardware",(.64,.386,.117),.41,.52)
light=mat("Warm lamp enamel diffuser",(.84,.81,.68),.49)
rings=mat("Neutral sample ring blanks, brass finish",(.73,.423,.116),.40,.51)
linen=mat("Ecru label stock and unmarked repair paper",(.87,.802,.674),.65)
blue=mat("Dusty indigo blue strip pad",(.071,.159,.180),.69)

# A true straight-back/crescent-front jeweller work surface, with open leg space.
curved=[]
for i in range(17):
    a=math.pi*i/16
    curved.append((-.361*math.cos(a),-.387+.226*math.sin(a)))
profile=[(-.720,-.387),*curved,(.720,-.387),(.720,.354),(-.720,.354)]
prism("Dark thick apron following exact bench recess",profile,.844,.896,edge,"01",.010)
prism("Crescent recess main solid working top",profile,.892,.953,wood,"01",.012)
for x in (-.658,.658):
    for y in (-.298,.285):
        box("Round-corner vertical wooden leg",(x,y,.424),(.070,.072,.810),edge,"01",.012)
        box("Brass foot ferrule on rubber foot",(x,y,.029),(.075,.079,.058),brass,"01",.009)
    box("Deep green side apron leg rail",(x,-.013,.668),(.065,.534,.061),deep,"01",.010)
box("Rear leg support continuous horizontal body",(0,.294,.510),(1.271,.067,.089),edge,"01",.013)
box("Rear shallow raised tool-retaining lip",(0,.331,.971),(1.420,.034,.042),edge,"01",.008)
for side in (-1,1):
    x=side*.534
    box("Compact solid independent drawer upper case",(x,.037,.733),(.261,.544,.215),edge,"01",.016)
    for z in (.696,.803):
        box("Green front of shallow service drawer",(x,-.246,z),(.246,.027,.087),draw,"01",.013)
        box("Wide aged brass label-frame drawer pull",(x,-.271,z),(.095,.029,.030),brass,"01",.009)
        box("Dark rectangular pull centre",(x,-.290,z),(.056,.007,.012),deep,"01",0)

# Rounded replaceable bench pin with a true through V-notch from the worker end.
pin=[(-.101,-.131),(-.101,-.421),(-.060,-.433),(0,-.301),(.060,-.433),(.101,-.421),(.101,-.131)]
prism("Replaceable timber working pin with through V-notch",pin,.909,.946,woodLite,"02",.008)
box("Dark metal mount underneath replaceable bench pin",(0,-.166,.891),(.187,.143,.045),deep,"02",.012)
for x in (-.077,.077):
    cyl("Recessed bench pin fixing head",(x,-.181,.948),.009,.006,metal,"02","z",10)
# Visibly hollow collector tray, front extended below and away from the V-notch.
box("Filing tray bottom: stained contained sweep surface",(0,-.323,.732),(.533,.410,.022),deep,"02",.008)
box("Small inset charcoal cloth inside filing tray",(0,-.327,.746),(.495,.360,.004),black,"02")
for x in (-.266,.266):
    box("Independent raised filing tray sides",(x,-.323,.767),(.021,.412,.064),brass,"02",.008)
for y in (-.528,-.121):
    box("Raised tray shallow front and rear stop",(0,y,.766),(.543,.020,.061),brass,"02",.010)
for x in (-.286,.286):
    box("Fixed dark tray slide above lip",(x,-.242,.775),(.028,.531,.035),deep,"02",.007)
box("Small curved-look central tray pull",(0,-.557,.779),(.128,.044,.031),brass,"02",.011)
for x,y in ((-.104,-.300),(-.127,-.346),(.124,-.388),(.09,-.352),(.149,-.311)):
    cyl("Subtle blank metal offcut on felt",(x,y,.749),.004,.004,brass,"02","z",7)

# Very small tapered metal mandrels on felt rests, and ring blanks at true prop scale.
box("Compact dark felt for stock and mandrels",(-.485,.025,.960),(.333,.212,.014),black,"03",.010)
for y in (-.029,.069):
    box("Single green mandrel rest cradle",(-.481,y,.970),(.164,.052,.021),deep,"03",.008)
def mandrel(n,x,y,z,L,r):
    profile=[(.001,0),(r*.84,0),(r,.020),(r,L*.17),(r*.76,L*.22),(r*.37,L*.93),(r*.29,L),(.001,L)]
    return lathe(n,(x,y,z),profile,metal,"03",18,"X")
mandrel("Long tapered ring mandrel with plain shaft",-.637,-.028,.994,.249,.023)
mandrel("Short tapered ring-forming mandrel",-.609,.069,.990,.190,.019)
for y,x,z in ((-.028,-.496,.994),(.069,-.518,.989)):
    lathe("Loose brass ring around illustrative tapered shaft",(x,y,z),
          [(.012,-.004),(.016,-.004),(.017,.005),(.012,.007)],rings,"03",22,"X")
box("Small velvet inspection pad for sample rings",(.374,-.217,.962),(.209,.204,.018),blue,"03",.010)
sampleProfile=[(.009,-.003),(.014,-.003),(.015,.001),(.015,.004),(.014,.006),(.009,.006)]
for x,y,rz in ((.341,-.250,.14),(.400,-.214,-.07),(.360,-.157,.09)):
    o=lathe("Unmarked metal ring blank on velvet pad",(x,y,.977),sampleProfile,rings,"03",22)
    o.rotation_euler.y=rz
for j in range(2):
    y=.031+j*.053
    bar("Plain smooth filing shaft",(.264,y,.970),(.446,y,.970),.013,.010,metal,"03",.004)
    bar("Short ochre wood file grip",(.446,y,.970),(.570,y,.970),.027,.027,woodLite,"03",.010)
box("Plain box for anonymous repair slips",(-.544,.229,.981),(.254,.142,.053),draw,"03",.012)
for j in range(3):
    v=box("Blank small envelope of repair slips",(-.553,.219,.995+j*.005),(.162,.101,.004),linen,"03")
    v.rotation_euler.z=(-.15+.14*j)
box("Small capped repair residue jar",(.600,.229,1.015),(.106,.105,.105),draw,"03",.024)
cyl("Jar top cap",(.600,.229,1.079),.048,.023,brass,"03","z",18)

# Task lamp has two visibly articulated-link pairs, fixed in this GLB.
base=(.561,.128,.959)
low=(.558,.125,1.069)
join=(.461,.141,1.384)
top=(.320,-.014,1.471)
tip=(.196,-.137,1.409)
cyl("Counterweighted circular lamp clamp foot",base,.065,.032,deep,"04","z",22)
cyl("Lamp post emerges from plate",(.561,.128,1.018),.027,.096,brass,"04","z",18)
for dy in (-.020,.020):
    a=(low[0],low[1]+dy,low[2]);b=(join[0],join[1]+dy,join[2]);c=(top[0],top[1]+dy,top[2])
    bar("Lower parallel task-lamp arm",a,b,.021,.019,brass,"04",.006)
    bar("Upper parallel task-lamp shoulder arm",b,c,.019,.019,brass,"04",.006)
for i,(x,y,z) in enumerate((low,join,top)):
    cyl("Represented articulated hinge pivot "+str(i),(x,y,z),.022,.064,deep,"04","y",14)
    cyl("Visible bronze hinge screw "+str(i),(x,y-.038,z),.013,.016,brass,"04","y",12)
bar("Short end elbow on lamp shoulder",top,tip,.028,.022,brass,"04")
shade=lathe("Domed hollow task lamp shade opening downward",tip,
   [(.027,.028),(.049,.020),(.057,-.004),(.078,-.036),(.078,-.045),(.072,-.045),(.073,-.036),(.053,-.005),(.047,.023),(.027,.025)],brass,"04",24)
shade.rotation_euler=(.097,.17,0)
diff=cyl("Unlit light cream inset lamp face",(tip[0]-.006,tip[1]+.003,tip[2]-.033),.058,.008,light,"04","z",20)
diff.rotation_euler=shade.rotation_euler

# Freestanding neutral signs reference use, not a real retail shop, name or prices.
box("Slim enamel rear placard lower foot",(-.137,.261,.966),(.499,.092,.023),deep,"05",.009)
box("Neutral framed repair placard",(-.148,.269,1.075),(.496,.041,.196),deep,"05",.020)
box("Inset warm cream bilingual writing surface",(-.148,.244,1.075),(.459,.014,.159),linen,"05",.010)
text("Generic Malay repair heading first line","BAIK PULIH",(-.148,.235,1.117),.036,deep)
text("Generic Malay jewellery heading","BARANG KEMAS",(-.148,.235,1.075),.035,deep)
text("Generic English service","JEWELLERY REPAIR",(-.148,.235,1.031),.023,deep)

def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat("-Z","Y").to_euler()
floor=mat("Dark neutral editorial studio background",(.095,.129,.123),.79)
box("Only studio shadow floor",(0,0,-.033),(150,150,.057),floor,"06")
bpy.ops.object.camera_add(location=(1.63,-3.32,2.43))
cam=link(bpy.context.object,"Editorial jeweller bench view","06")
aim(cam,(.002,-.013,.728));cam.data.type="ORTHO";cam.data.ortho_scale=2.06;scene.camera=cam
for n,p,e,c,s in (
    ("Large warm soft key",(2.4,-3.02,4.2),475,(1,.86,.68),2.4),
    ("Cool shop-window fill",(-2.8,-1.95,2.46),380,(.68,.86,1),2.85),
    ("Satin brass edge light",(2.33,1.77,3.27),430,(.88,1,.78),2.4)):
    bpy.ops.object.light_add(type="AREA",location=p);o=link(bpy.context.object,n,"06")
    o.data.energy=e;o.data.color=c;o.data.shape="DISK";o.data.size=s;aim(o,(0,0,.72))
scene.world=bpy.data.worlds.new("Studio diffuse background");scene.world.use_nodes=True
bg=scene.world.node_tree.nodes["Background"]
bg.inputs[0].default_value=(.42,.51,.60,1);bg.inputs[1].default_value=.34
scene.render.engine="CYCLES";scene.cycles.samples=26;scene.cycles.use_denoising=True
scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.view_settings.view_transform="AgX";scene.view_settings.exposure=-.18
scene.render.image_settings.file_format="PNG";scene.render.filepath=str(P/"previews"/"studio.png")
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.wm.save_as_mainfile(filepath=str(P/(ID+".blend")))
if "--skip-render" not in sys.argv:
    bpy.ops.render.render(write_still=True)
    if "--bench-review" in sys.argv:
        cam.location=(.81,-2.59,2.48);aim(cam,(.006,-.101,.874));cam.data.ortho_scale=1.55
        scene.render.filepath=str(P/"previews"/"tools.png");bpy.ops.render.render(write_still=True)

selected=[]
for k,c in C.items():
    if k=="06":continue
    group=defaultdict(list)
    for o in list(c.objects):
        if o.modifiers or o.type=="FONT":
            bpy.ops.object.select_all(action="DESELECT");o.select_set(True);bpy.context.view_layer.objects.active=o
            bpy.ops.object.convert(target="MESH");o=bpy.context.view_layer.objects.active
        group[o.data.materials[0].name].append(o)
    for m,obs in sorted(group.items()):
        bpy.ops.object.select_all(action="DESELECT")
        for ob in obs:ob.select_set(True)
        a=obs[0];bpy.context.view_layer.objects.active=a
        if len(obs)>1:bpy.ops.object.join()
        a.name=c.name[3:]+" | "+m;selected.append(a)
bpy.ops.object.select_all(action="DESELECT")
for ob in selected:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(P/"exports"/(ID+".glb")),export_format="GLB",
    use_selection=True,export_animations=False,export_cameras=False,export_lights=False,export_texcoords=False)
