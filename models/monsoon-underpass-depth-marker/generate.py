"""Original static roadside monsoon depth gauge, context curb and open grate."""
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
import bpy
from mathutils import Vector

ID="monsoon-underpass-depth-marker"
D=Path(__file__).resolve().parent
for s in ("exports","previews"):(D/s).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system="METRIC"
parts={}
for n in ("01 Cropped underpass roadway and curb","02 Open recessed drain and metal grate",
          "03 Removable ruler housing and mounting","04 Bilingual labels, scale and weathering",
          "05 Studio only"):
    c=bpy.data.collections.new(n);scene.collection.children.link(c);parts[n[:2]]=c

def mat(n,c,r=.48,m=0):
    o=bpy.data.materials.new(n);o.use_nodes=True;o.diffuse_color=(*c,1)
    b=o.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value=(*c,1)
    b.inputs["Roughness"].default_value=r
    b.inputs["Metallic"].default_value=m
    return o
def attach(o,n,k,m=None):
    o.name=n
    for c in list(o.users_collection):c.objects.unlink(o)
    parts[k].objects.link(o)
    if m:o.data.materials.append(m)
    return o
def box(n,p,d,m,k,r=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=attach(bpy.context.object,n,k,m);o.dimensions=d
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if r>=.008:
        l=o.modifiers.new("Worn bevel catches daylight","BEVEL");l.width=r;l.segments=2 if r>=.025 else 1;l.harden_normals=True
        l=o.modifiers.new("Weighted edge normals","WEIGHTED_NORMAL");l.keep_sharp=True
    return o
def cyl(n,p,r,h,m,k,front=False,s=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=s,radius=r,depth=h,location=p)
    o=attach(bpy.context.object,n,k,m)
    if front:o.rotation_euler.x=math.pi/2
    for f in o.data.polygons:f.use_smooth=len(f.vertices)==4
    return o
def mesh(n,v,f,m,k):
    me=bpy.data.meshes.new(n);me.from_pydata(v,[],f);me.update()
    return attach(bpy.data.objects.new(n,me),n,k,m)
def text(n,v,x,z,sz,m,k="04",y=-.030):
    bpy.ops.object.text_add(location=(x,y,z),rotation=(math.pi/2,0,0))
    o=attach(bpy.context.object,n,k,m);o.data.body=v;o.data.align_x="CENTER"
    o.data.align_y="CENTER";o.data.size=sz;o.data.resolution_u=2
    return o

bitumen=mat("Deep blue-gray mottled underpass asphalt",(.061,.085,.093),.78)
tarmac=mat("Wet-weather darker gutter asphalt",(.049,.079,.083),.63)
damp=mat("Slate damp discoloration",(.052,.072,.080),.73)
speck=mat("Muted asphalt aggregate mineral sheen",(.125,.154,.148),.83)
curb=mat("Sand grey cast concrete kerb",(.49,.475,.396),.76)
cement=mat("Pale concrete back and footpath",(.46,.459,.421),.78)
weather=mat("Dry taupe splash and soot marks",(.397,.408,.357),.87)
paint=mat("Old off-white crop road stripe",(.67,.674,.581),.68)
black=mat("Pitch inside unlit drainage chamber",(.034,.047,.046),.75)
steel=mat("Patinated cast grate, graphite with bronze patina",(.17,.225,.207),.47,.45)
silver=mat("Exposed dull stainless grate fasteners",(.42,.45,.407),.41,.46)
blue=mat("Deep muted petrol powder coat",(.027,.133,.157),.51,.20)
cyan=mat("Weathered blue green scale stock",(.060,.254,.278),.53)
cream=mat("Warm pale reflective-look depth marks",(.90,.874,.692),.28,.12)
scuff=mat("Worn pale residual reflective flecks",(.62,.661,.545),.54)

# Physical rectangular opening: the contiguous road is four strips around it.
# Road datum is z=.090 m; 20–100 cm marks are actual geometry offset from datum.
box("Continuous underside road mass",(0,-.181,.013),(2.380,1.364,.026),tarmac,"01",.014)
openX=(-.879,-.137)
openY=(-.285,.138)
def slab(n,x0,x1,y0,y1,z=.090,m=bitumen):
    return box(n,((x0+x1)/2,(y0+y1)/2,(z+.022)/2),(x1-x0,y1-y0,z-.022),m,"01")
slab("Asphalt front roadway crop",-1.190,1.190,-.863,openY[0])
slab("Gutter strip behind open mouth",-1.190,1.190,openY[1],.278,.090,tarmac)
slab("Left road margin beside grate",-1.190,openX[0],openY[0],openY[1],.090)
slab("Right road margin beside grate",openX[1],1.190,openY[0],openY[1],.090)
box("Lane marking on side of scene only",(.846,-.604,.091),(.647,.049,.003),paint,"01")
box("Old lane marking patch",(.300,-.604,.091),(.218,.051,.003),paint,"01")
box("Long underpass cut curb face",(0,.360,.145),(2.380,.275,.225),curb,"01",.023)
box("Floor against sidewall behind curb",(0,.570,.113),(2.380,.331,.183),cement,"01",.015)
for x in (-.91,-.346,.191,.786):
    box("Structural expansion joint in cropped curb",(x,.249,.187),(.011,.008,.112),weather,"01")
box("Low underpass concrete splash-wall crop",(0,.695,.521),(2.380,.122,.783),cement,"01",.037)
box("Lower stronger curb wear course",(0,.626,.296),(2.350,.022,.175),curb,"01",.012)
box("Back-wall cap edge",(0,.697,.916),(2.366,.141,.040),curb,"01",.017)
for x in (-.58,.041,.643):
    box("Vertical formed joint on splash wall",(x,.631,.569),(.010,.008,.588),weather,"01")
# A steel U channel recessed into the asphalt, with genuine open rectangular slots.
gx=-.508; gy=-.0735
box("Recess floor below grate",(gx,gy,.032),(.727,.408,.021),black,"02")
for s in (-1,1):
    box("Deep inner drain edge wall",(gx+s*.355,gy,.055),(.028,.430,.064),black,"02")
    box("Deep inner drain short wall",(gx,gy+s*.193,.055),(.744,.032,.064),black,"02")
    box("Low heavy steel lengthwise perimeter rail",(gx,gy+s*.188,.085),(.728,.040,.020),steel,"02",.008)
    box("Low heavy steel crosswise perimeter rail",(gx+s*.343,gy,.085),(.040,.348,.020),steel,"02",.008)
for i in range(10):
    x=gx-.298+.066*i
    box("Open grate cast round-edged crossbar",(x,gy,.084),(.034,.335,.024),steel,"02",.008)
for x in (gx-.343,gx+.343):
    for y in (gy-.151,gy+.151):
        cyl("Visible low bolt lug",(x,y,.098),.010,.006,silver,"02",False,8)
box("Recessed maintenance pull shallow collar",(gx,.104,.094),(.117,.017,.011),silver,"02",.004)
# Large tilted-phase front face is deliberately vertical and clear of the grate.
cx=.491
for x in (.231,.686):
    box("Galvanized uprights on curb flange",(x,.065,.707),(.040,.061,1.153),blue,"03",.012)
    box("Bolted foundation angle bracket",(x,.141,.221),(.092,.155,.058),blue,"03",.014)
    cyl("Visible bracket deck bolt",(x,.174,.255),.012,.011,silver,"03",False,8)
box("Flush folded powder coated ruler back",(cx,.025,.728),(.565,.077,1.237),blue,"03",.023)
box("Exchangeable slim scale liner",(cx,-.015,.722),(.513,.013,1.182),cyan,"03",.012)
box("Reflective top heading plaque",(cx,-.023,1.203),(.480,.010,.155),cream,"03",.010)
text("Malay heading","ARAS AIR",cx,1.236,.064,blue,y=-.030)
text("English heading","WATER DEPTH",cx,1.175,.040,blue,y=-.030)
for x in (.254,.728):
    for z in (.194,1.279):
        cyl("Visible engraved ruler fastening screw",(x,-.027,z),.011,.006,silver,"03",True,10)

# Tick centres are true z = .090 + cm/100. Alternation is monochrome, no thresholds.
for cm in range(5,101,5):
    z=.090+cm/100
    if z<.19:
        continue
    size=.173 if cm%20==0 else (.119 if cm%10==0 else .078)
    thick=.013 if cm%20==0 else .007
    box("Scale tick %03d cm"%cm,(.349+(size-.173)/2,-.023,z),(size,.009,thick),cream,"04")
    if cm%20==0:
        text("Measured depth label %03d cm"%cm,str(cm),.574,z,.073,cream)
for i in range(5):
    z=.190+i*.202
    box("Fine lightly weathered side motif",(.260,-.022,z),(.013,.006,.078),cream if i%2==0 else scuff,"04")
text("Units centimetres","CM",.576,.197,.042,cream)

# Deterministic, low-count geometry scuffs for asphalt and vertical concrete.
rng=random.Random(15)
for j in range(38):
    x=rng.uniform(-1.113,1.113);y=rng.uniform(-.779,.225)
    if openX[0]-.04 < x < openX[1]+.04 and openY[0]-.02 < y < openY[1]+.02:
        continue
    if abs(y+.604)<.033:
        continue
    radius=rng.uniform(.012,.061)
    v=[(x+radius*math.cos(a*math.tau/5)*rng.uniform(.58,1.15),
        y+radius*.48*math.sin(a*math.tau/5)*rng.uniform(.6,1.4),.0908) for a in range(5)]
    if min(k[0] for k in v)>-1.19 and max(k[0] for k in v)<1.19:
        mesh("Muted irregular surface speckle",v,[(0,1,2,3,4)],speck if j%4==0 else damp,"01")
for i in range(9):
    x=-1.085+i*.255+rng.uniform(-.052,.052);z=rng.uniform(.416,.584)
    w=rng.uniform(.009,.052);h=rng.uniform(.019,.115)
    y=.629-i*.00021
    v=[(x-w,y,z),(x-w*.50,y,z+h*.85),(x+w*.45,y,z+h),
       (x+w,y,z+h*.18),(x+w*.38,y,z-h*.15)]
    mesh("Neutral rain streak on splash wall",v,[(4,3,2,1,0)],weather,"01")
for x,z in ((.265,.375),(.744,.544),(.270,.835),(.731,1.040),(.266,.952)):
    mesh("Tiny wear nick outside the number and tick",[(x-.004,-.027,z),(x+.005,-.027,z+.022),(x+.012,-.027,z+.008)],
         [(0,1,2)],scuff,"04")

def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat("-Z","Y").to_euler()
ground=mat("Muted cool grey studio backdrop",(.108,.127,.139),.75)
box("Studio only shadow ground",(0,0,-.034),(160,160,.058),ground,"05")
bpy.ops.object.camera_add(location=(1.93,-4.47,2.52))
cam=attach(bpy.context.object,"Editorial depth marker camera","05")
aim(cam,(.014,-.004,.60))
cam.data.type="ORTHO";cam.data.ortho_scale=3.02;scene.camera=cam
for n,p,e,c,sz in (
    ("Warm side daylight",(2.5,-3.60,4.3),630,(1,.88,.72),3.0),
    ("Cool broad face fill",(-3.6,-2.55,3.2),435,(.72,.88,1),3.3),
    ("Soft high backdrop",(1.67,2.28,4.2),610,(.86,1,.90),3.1)):
    bpy.ops.object.light_add(type="AREA",location=p)
    l=attach(bpy.context.object,n,"05");l.data.energy=e;l.data.color=c;l.data.shape="DISK";l.data.size=sz
    aim(l,(0,0,.58))
scene.world=bpy.data.worlds.new("Studio contextual soft grey");scene.world.use_nodes=True
bg=scene.world.node_tree.nodes["Background"];bg.inputs[0].default_value=(.47,.53,.60,1);bg.inputs[1].default_value=.38
scene.render.engine="CYCLES";scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.view_settings.view_transform="AgX";scene.render.image_settings.file_format="PNG"
scene.render.filepath=str(D/"previews"/"studio.png")
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.wm.save_as_mainfile(filepath=str(D/(ID+".blend")))
if "--skip-render" not in sys.argv:
    bpy.ops.render.render(write_still=True)
    if "--grate-review" in sys.argv:
        cam.location=(.29,-3.53,2.33);aim(cam,(.039,-.069,.623));cam.data.ortho_scale=2.1
        scene.render.filepath=str(D/"previews"/"grate-review.png")
        bpy.ops.render.render(write_still=True)

selected=[]
for key,coll in parts.items():
    if key=="05":continue
    by=defaultdict(list)
    for o in list(coll.objects):
        if o.modifiers or o.type=="FONT":
            bpy.ops.object.select_all(action="DESELECT");o.select_set(True);bpy.context.view_layer.objects.active=o
            bpy.ops.object.convert(target="MESH");o=bpy.context.view_layer.objects.active
        by[o.data.materials[0].name].append(o)
    for n,obs in sorted(by.items()):
        bpy.ops.object.select_all(action="DESELECT")
        for o in obs:o.select_set(True)
        active=obs[0];bpy.context.view_layer.objects.active=active
        if len(obs)>1:bpy.ops.object.join()
        active.name=coll.name[3:]+" | "+n;selected.append(active)
bpy.ops.object.select_all(action="DESELECT")
for o in selected:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(D/"exports"/(ID+".glb")),export_format="GLB",
   use_selection=True,export_animations=False,export_cameras=False,export_lights=False,export_texcoords=False)
