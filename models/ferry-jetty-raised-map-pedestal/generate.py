"""A fictional ferry-jetty model with two genuine raised-relief map insets."""
import math
import sys
from collections import defaultdict
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

ID="ferry-jetty-raised-map-pedestal"
D=Path(__file__).resolve().parent
for f in ("exports","previews"):(D/f).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system="METRIC"
C={}
for n in ("01 Pedestal base and fixed bracket spine","02 Diagonal boxed map insets",
          "03 Raised imaginary overview and jetty detail","04 Bilingual sample labels",
          "05 Studio only"):
    c=bpy.data.collections.new(n);scene.collection.children.link(c);C[n[:2]]=c

def mat(n,c,r=.52,m=0):
    o=bpy.data.materials.new(n);o.use_nodes=True;o.diffuse_color=(*c,1)
    p=o.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=(*c,1)
    p.inputs["Roughness"].default_value=r
    p.inputs["Metallic"].default_value=m
    return o
def put(o,n,k,m=None):
    o.name=n
    for c in list(o.users_collection):c.objects.unlink(o)
    C[k].objects.link(o)
    if m:o.data.materials.append(m)
    return o
def bevel(o,r):
    if r>=.007:
        b=o.modifiers.new("Folded soft edge radius","BEVEL");b.width=r;b.segments=2 if r>=.021 else 1;b.harden_normals=True
        b=o.modifiers.new("Weighted molded corner normals","WEIGHTED_NORMAL");b.keep_sharp=True
    return o
def cube(n,p,d,m,k,r=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p)
    o=put(bpy.context.object,n,k,m);o.dimensions=d;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return bevel(o,r)
def mesh(n,v,f,m,k):
    x=bpy.data.meshes.new(n);x.from_pydata(v,[],f);x.update()
    b=bmesh.new();b.from_mesh(x);bmesh.ops.recalc_face_normals(b,faces=list(b.faces));b.to_mesh(x);b.free()
    return put(bpy.data.objects.new(n,x),n,k,m)
def cyl(n,p,r,h,m,k,segments=14):
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments,radius=r,depth=h,location=p)
    o=put(bpy.context.object,n,k,m)
    for v in o.data.polygons:v.use_smooth=len(v.vertices)==4
    return o
def bar(n,a,b,w,h,m,k,r=0):
    a,b=Vector(a),Vector(b)
    o=cube(n,(a+b)/2,(w,h,(b-a).length),m,k,r)
    o.rotation_euler=(b-a).to_track_quat("Z","Y").to_euler()
    return o

navy=mat("Midnight maritime blue powder coat",(.029,.086,.137),.47,.21)
petrol=mat("Dark marine teal frame lining",(.046,.221,.230),.50,.18)
water=mat("Fictional deep teal blue printed water",(.055,.275,.365),.58)
land=mat("Map warm limestone raised islands",(.801,.743,.585),.65)
pale=mat("Ivory paint label and neutral surface",(.90,.86,.709),.63)
sand=mat("Old pale golden drainboard floor",(.443,.397,.277),.69)
dark=mat("Charcoal rubberised base and join shadows",(.05,.072,.072),.66)
silver=mat("Brushed marine grey fasteners",(.422,.491,.487),.42,.42)
gold=mat("Orange raised route and contact symbols",(.942,.385,.052),.49)
rust=mat("Warm red ochre landmark counterpoint",(.568,.158,.064),.55)
wave=mat("Muted reef blue low-relief wave symbol",(.13,.44,.50),.68)
grass=mat("Neutral abstract coastal green interior",(.442,.55,.37),.72)

# An independent small deck footing rather than a full terminal or navigation aid.
cube("Rounded slab non-slip illustration footprint",(0,.005,.036),(1.154,.766,.072),dark,"01",.024)
cube("Inset light warm platform deck",(0,.005,.071),(1.090,.709,.021),sand,"01",.015)
for x in (-.428,-.283,-.142,0,.142,.283,.428):
    cube("Notched deck parallel join seam",(x,.005,.0835),(.009,.676,.003),dark,"01")
cube("Thick dark raised plinth connection",(0,.169,.118),(.526,.415,.072),navy,"01",.019)
for x in (-.198,.198):
    for y in (.004,.301):
        cyl("Round deck platform anchor foot",(x,y,.158),.024,.016,silver,"01",12)
cube("Marine finished central fixed pedestal spine",(0,.188,.599),(.304,.198,.935),navy,"01",.025)
cube("Slim inset pedestal material strip",(0,.083,.555),(.229,.024,.648),petrol,"01",.014)
for x in (-.136,.136):
    bar("Fitted diagonal bracket supporting front map",(x,.157,.474),(x,-.240,.797),.040,.051,navy,"01",.009)
    bar("Fitted short bracket supporting upper map",(x,.206,.882),(x,.015,1.193),.045,.051,navy,"01",.009)
cube("Wrapped upper central collar",(0,.172,1.035),(.328,.212,.081),petrol,"01",.014)

# The surface-space helpers put all graphics on each sloping plane by construction.
upper=((0,.130,1.202),math.radians(23))
lower=((0,-.177,.823),math.radians(24))
def world(s,x,y,z):
    o,a=s
    return Vector(o)+Matrix.Rotation(a,3,"X")@Vector((x,y,z))
def tile(n,s,x,y,z,w,h,d,m,k,r=0):
    o=cube(n,world(s,x,y,z),(w,h,d),m,k,r)
    o.rotation_euler.x=s[1]
    return o
def patch(n,s,polygon,z0,z1,m,k="03"):
    N=len(polygon)
    v=[world(s,x,y,z) for z in (z0,z1) for x,y in polygon]
    f=[tuple(range(N-1,-1,-1)),tuple(range(N,N*2))]
    f.extend((i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N))
    return mesh(n,v,f,m,k)
def disk(n,s,x,y,z,r,d,m,k="03",segments=14):
    o=cyl(n,world(s,x,y,z),r,d,m,k,segments)
    o.rotation_euler.x=s[1]
    return o
def label(n,s,v,x,y,z,size,m=pale):
    bpy.ops.object.text_add(location=world(s,x,y,z),rotation=(s[1],0,0))
    o=put(bpy.context.object,n,"04",m)
    o.data.body=v;o.data.size=size;o.data.align_x="CENTER";o.data.align_y="CENTER";o.data.resolution_u=2
    return o
def track(n,s,path,z,w,m,d=.010,with_joints=True):
    for k,((x,y),(u,v)) in enumerate(zip(path,path[1:])):
        a,b=world(s,x,y,z),world(s,u,v,z)
        direction=Vector((u-x,v-y)).length
        o=tile(n+" raised polyline segment",s,(x+u)/2,(y+v)/2,z,direction+w*.12,w,d,m,"03")
        o.rotation_euler=(Matrix.Rotation(s[1],3,"X")@Matrix.Rotation(math.atan2(v-y,u-x),3,"Z")).to_euler()
    if with_joints:
        for x,y in path:disk(n+" rounded joins",s,x,y,z,w*.51,d,m,"03",10)

for n,s,w,h in (("Upper overview",upper,1.053,.556),("Lower boarding inset",lower,.851,.422)):
    tile(n+" separate full sloping metal housing",s,0,0,0,w,h,.068,navy,"02",.023)
    tile(n+" petrol lining bezel",s,0,0,.038,w-.036,h-.041,.024,petrol,"02",.012)
    tile(n+" recessed water field",s,0,0,.052,w-.080,h-.086,.010,water,"02",.008)
    for x in (-w*.468,w*.468):
        for y in (-h*.415,h*.415):
            disk(n+" small inset panel corner fastener",s,x,y,.051,.008,.005,silver,"02",10)
    tile(n+" slate edge protective grab rim",s,0,-h*.458,.053,w-.029,.024,.019,navy,"02",.008)

# Broad raised islands and a clearly fictional orange ferry routing in the water.
tile("Overview navy header inset",upper,0,.188,.059,.932,.073,.012,navy,"04",.008)
label("Malay upper title",upper,"PETA JETI",-.247,.190,.067,.039)
label("English upper title",upper,"JETTY MAP",.034,.190,.067,.034)
label("Upper model-only marker",upper,"CONTOH / SAMPLE",.317,.184,.067,.017)
patch("Raised upper left imaginary coastline",upper,[(-.464,.138),(-.242,.137),(-.193,.092),(-.225,.047),
    (-.157,.006),(-.178,-.043),(-.257,-.051),(-.294,-.124),(-.372,-.174),(-.464,-.173)],.056,.073,land)
patch("Raised upper right abstract shore",upper,[(.461,.124),(.343,.121),(.266,.088),(.248,.031),(.283,-.013),
    (.202,-.055),(.236,-.097),(.310,-.151),(.461,-.158)],.056,.074,land)
patch("Soft relief hinterland west",upper,[(-.451,.110),(-.296,.111),(-.264,.078),(-.300,.025),
    (-.281,-.015),(-.349,-.054),(-.451,-.076)],.071,.078,grass)
patch("Soft relief hinterland east",upper,[(.451,.087),(.394,.096),(.315,.052),(.330,.004),(.398,-.014),(.451,-.008)],.072,.078,grass)
track("Raised ferry path across fictional bay",upper,[(-.194,-.019),(-.116,-.042),(-.050,-.060),(.034,-.044),(.126,-.067),(.231,-.069)],.078,.015,gold,.015)
track("Raised footpath on imaginary left land",upper,[(-.426,.062),(-.341,.047),(-.312,.004),(-.251,-.018),(-.196,-.020)],.081,.013,navy,.011)
track("Raised footpath on imaginary right land",upper,[(.457,-.091),(.377,-.095),(.334,-.057),(.294,-.077),(.234,-.069)],.081,.013,navy,.011)
for x,y,v in ((-.199,-.018,"A"),(.231,-.071,"B")):
    disk("Raised fictional terminal node "+v,upper,x,y,.086,.023,.017,pale,"03",16)
    disk("Contrasting inset landmark cap "+v,upper,x,y,.096,.012,.006,rust,"03",12)
    label("Fictional abstract terminal letter "+v,upper,v,x,y+.034,.086,.022,navy)
for x,y in ((-.08,.077),(.058,.093),(.130,.049),(-.095,-.139),(.015,-.118),(.115,-.14)):
    track("Abstract blue water markings",upper,[(x-.017,y),(x-.006,y+.004),(x+.009,y),(x+.022,y+.003)],.061,.006,wave,.004,False)
tile("Small legend base across overview bottom",upper,.011,-.204,.060,.545,.043,.012,navy,"04",.007)
label("Concept only footer caption",upper,"LALUAN REKAAN   /   IMAGINARY ROUTE",.008,-.204,.068,.014)

# Lower detail has its own deck shape, boarding spur, and open water patches.
tile("Detail slate label stripe",lower,0,.139,.061,.741,.054,.010,navy,"04",.007)
label("Lower Malay and English detail title",lower,"DEK JETI   /   JETTY DECK",-.128,.139,.068,.024)
label("Lower model-only indicator",lower,"CONTOH / SAMPLE",.252,.139,.068,.014)
patch("Raised detail abstract boarding deck",lower,[(-.364,-.025),(-.144,-.025),(-.144,.071),(-.091,.071),(-.091,-.025),
    (.079,-.025),(.079,.035),(.156,.035),(.156,-.015),(.340,-.015),(.340,-.093),
    (.089,-.094),(.057,-.145),(-.364,-.145)],.055,.075,land)
for x in (-.293,-.246,-.199,-.151,-.104,-.058,-.012,.035):
    tile("Raised lower deck board seam",lower,x,-.105,.079,.006,.060,.008,navy,"03")
track("Detail amber walking path",lower,[(-.288,-.065),(-.173,-.065),(-.113,-.062),(.079,-.059),(.148,-.048),(.264,-.049)],.083,.016,gold,.014)
for x,y in ((-.287,-.065),(-.112,-.063),(.257,-.048)):
    disk("Distinct raised lower map node",lower,x,y,.092,.019,.015,pale,"03",14)
for x,y in ((-.042,.040),(.251,.073),(.302,-.126)):
    track("Short lower water edge motif",lower,[(x-.023,y),(x-.004,y+.006),(x+.017,y)],.063,.008,wave,.004,False)
patch("Lower geometric fictional boat mark",lower,[(.266,.052),(.337,.052),(.322,.041),(.279,.041)],.064,.080,pale)
tile("Boat single raised cabin mark",lower,.301,.058,.076,.036,.011,.013,rust,"03")

def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat("-Z","Y").to_euler()
floor=mat("Dark slate studio ground",(.109,.142,.151),.77)
cube("Separate studio shadow floor",(0,0,-.031),(150,150,.056),floor,"05")
bpy.ops.object.camera_add(location=(1.40,-3.29,2.67))
cam=put(bpy.context.object,"Raised line product camera","05")
aim(cam,(0,-.008,.682));cam.data.type="ORTHO";cam.data.ortho_scale=1.89;scene.camera=cam
for n,p,e,c,s in (
    ("Warm coastal key light",(2.05,-2.93,3.22),473,(1,.89,.71),2.43),
    ("Cool board fill",(-2.62,-1.83,2.79),365,(.70,.89,1),2.50),
    ("Rim light for raised coastlines",(1.35,2.18,3.22),521,(.91,1,.85),2.30)):
    bpy.ops.object.light_add(type="AREA",location=p);o=put(bpy.context.object,n,"05")
    o.data.energy=e;o.data.color=c;o.data.shape="DISK";o.data.size=s;aim(o,(0,0,.74))
scene.world=bpy.data.worlds.new("Neutral ambient studio");scene.world.use_nodes=True
bg=scene.world.node_tree.nodes["Background"];bg.inputs[0].default_value=(.45,.56,.63,1);bg.inputs[1].default_value=.35
scene.render.engine="CYCLES";scene.cycles.samples=26;scene.cycles.use_denoising=True
scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.view_settings.view_transform="AgX";scene.view_settings.exposure=-.23
scene.render.image_settings.file_format="PNG";scene.render.filepath=str(D/"previews"/"studio.png")
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.wm.save_as_mainfile(filepath=str(D/(ID+".blend")))
if "--skip-render" not in sys.argv:
    bpy.ops.render.render(write_still=True)
    if "--map-review" in sys.argv:
        cam.location=(.55,-2.81,3.55);aim(cam,(0,-.063,1.022));cam.data.ortho_scale=1.275
        scene.render.filepath=str(D/"previews"/"relief.png");bpy.ops.render.render(write_still=True)
selected=[]
for k,c in C.items():
    if k=="05":continue
    by=defaultdict(list)
    for o in list(c.objects):
        if o.modifiers or o.type=="FONT":
            bpy.ops.object.select_all(action="DESELECT");o.select_set(True);bpy.context.view_layer.objects.active=o
            bpy.ops.object.convert(target="MESH");o=bpy.context.view_layer.objects.active
        by[o.data.materials[0].name].append(o)
    for m,obs in sorted(by.items()):
        bpy.ops.object.select_all(action="DESELECT")
        for o in obs:o.select_set(True)
        a=obs[0];bpy.context.view_layer.objects.active=a
        if len(obs)>1:bpy.ops.object.join()
        a.name=c.name[3:]+" | "+m;selected.append(a)
bpy.ops.object.select_all(action="DESELECT")
for o in selected:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(D/"exports"/(ID+".glb")),export_format="GLB",
 use_selection=True,export_animations=False,export_cameras=False,export_lights=False,export_texcoords=False)
