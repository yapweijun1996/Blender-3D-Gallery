"""Original outdoor Malaysian air balang counter with one authored illustrative pour."""
import math
import sys
from collections import defaultdict
from pathlib import Path
import bmesh
import bpy
from mathutils import Vector

SLUG="ramadan-bazaar-air-balang-stall"
D=Path(__file__).resolve().parent
for f in ("exports","previews"):(D/f).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system="METRIC"
scene.render.fps=24
scene.frame_start=0;scene.frame_end=54
col={}
for n in ("01 Awning and folding outdoor frame","02 Retail counter and cold storage",
          "03 Three air balang vessels and taps","04 Cups, signs and service preparation",
          "05 One animated sample pour","06 Studio only"):
    c=bpy.data.collections.new(n);scene.collection.children.link(c);col[n[:2]]=c

def material(n,c,rough=.49,metal=0,alpha=1):
    m=bpy.data.materials.new(n);m.use_nodes=True;m.diffuse_color=(*c,alpha)
    p=m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=(*c,1)
    p.inputs["Roughness"].default_value=rough
    p.inputs["Metallic"].default_value=metal
    p.inputs["Alpha"].default_value=alpha
    if alpha<1:m.surface_render_method="BLENDED"
    return m
def attach(o,n,k,m=None):
    o.name=n
    for c in list(o.users_collection):c.objects.unlink(o)
    col[k].objects.link(o)
    if m:o.data.materials.append(m)
    return o
def cube(n,p,s,m,k,r=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=attach(bpy.context.object,n,k,m);o.dimensions=s
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if r>=.008:
        b=o.modifiers.new("Formed edge radius","BEVEL");b.width=r;b.segments=2 if r>=.028 else 1;b.harden_normals=True
        b=o.modifiers.new("Weighted corner normals","WEIGHTED_NORMAL");b.keep_sharp=True
    return o
def mesh(n,v,f,m,k):
    me=bpy.data.meshes.new(n);me.from_pydata(v,[],f);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    return attach(bpy.data.objects.new(n,me),n,k,m)
def turns(n,p,path,m,k,nseg=24,close=True,smooth=True):
    # Spiral-free closed cross-section or one un-capped transparent wall.
    vv=[(r*math.cos(a*math.tau/nseg),r*math.sin(a*math.tau/nseg),z) for r,z in path for a in range(nseg)]
    ff=[]
    for j in range(len(path) if close else len(path)-1):
        nxt=(j+1)%len(path)
        for a in range(nseg):
            b=(a+1)%nseg;ff.append((j*nseg+a,j*nseg+b,nxt*nseg+b,nxt*nseg+a))
    o=mesh(n,vv,ff,m,k)
    o.location=p
    if smooth:
        for f in o.data.polygons:f.use_smooth=True
    return o
def cylinder(n,p,r,h,m,k,nseg=20,front=False):
    bpy.ops.mesh.primitive_cylinder_add(vertices=nseg,radius=r,depth=h,location=p);o=attach(bpy.context.object,n,k,m)
    if front:o.rotation_euler.x=math.pi/2
    for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
    return o
def bar(n,a,b,sx,sy,m,k,r=0):
    a,b=Vector(a),Vector(b);o=cube(n,(a+b)/2,(sx,sy,(b-a).length),m,k,r)
    o.rotation_euler=(b-a).to_track_quat("Z","Y").to_euler();return o
def text(n,t,p,size,m,k):
    bpy.ops.object.text_add(location=p,rotation=(math.pi/2,0,0));o=attach(bpy.context.object,n,k,m)
    o.data.body=t;o.data.align_x="CENTER";o.data.align_y="CENTER";o.data.size=size;o.data.resolution_u=2
    return o

plum=material("Mulberry night-market canvas",(.203,.042,.107),.78)
shade=material("Dark eggplant awning underside",(.095,.029,.067),.73)
cream=material("Warm oat cotton canvas and sign stock",(.85,.76,.56),.65)
metal=material("Dull silver contact rack and fittings",(.40,.46,.44),.38,.50)
black=material("Graphite collapsible frame and tap bodies",(.034,.046,.044),.58)
wood=material("Warm sawn counter boards",(.455,.247,.115),.69)
darkWood=material("Recessed dark cutting-board seams",(.24,.117,.060),.75)
gold=material("Muted golden ties and fastenings",(.73,.39,.072),.54)
glass=material("Clear balang outer shell",(.68,.91,.90),.18,0,.13)
glassGem=material("Soft rim and clear vessel base",(.64,.83,.78),.21,0,.49)
cupM=material("Plain translucent serving cup",(.86,.96,.92),.20,0,.27)
ice=material("Mini milky clear ice edges",(.82,.95,.95),.29,0,.62)
green=material("Illustrative yellow-green lime drink",(.40,.62,.034),.29)
amber=material("Illustrative reddish amber tea",(.57,.155,.029),.28)
rose=material("Illustrative rose-red drink",(.57,.036,.104),.30)
limeSkin=material("Lime slice and rind",(.156,.34,.042),.48)
limeFlesh=material("Pale cut lime flesh",(.73,.77,.255),.50)
flow=material("Bright fictional lime pour liquid",(.55,.77,.100),.29)

# Portable street tent: taut four-panel roof, structural braces and straight hem.
for x in (-1.119,1.119):
    for y in (-.659,.612):
        cube("Flat interlocking tent foot",(x,y,.025),(.119,.112,.050),black,"01",.010)
        cube("Light four-post telescopic frame",(x,y,1.092),(.052,.052,2.118),metal,"01",.010)
        cube("Temporary dry clamp lock",(x,y,.687),(.076,.072,.074),black,"01",.011)
        cube("Upper canopy sleeve",(x,y,2.129),(.083,.083,.095),shade,"01",.008)
    bar("Tension side cross brace",(x,-.637,1.695),(x,.612,2.149),.027,.043,metal,"01")
for y in (-.659,.612):
    for s in (-1,1):
        bar("Angled structural roof strut",(s*1.119,y,2.149),(0,y,2.465),.036,.040,metal,"01")
    cube("Front and rear frame stretcher",(0,y,2.122),(2.260,.053,.043),black,"01",.009)
cube("Continuous ridge", (0,-.023,2.458),(.046,1.296,.039),metal,"01")
for j in range(8):
    a=-1.18+j*.295;b=a+.295
    def Z(x):return 2.485-abs(x)*.282
    cv=[(a,-.747,Z(a)),(b,-.747,Z(b)),(b,.696,Z(b)),(a,.696,Z(a))]
    panel=mesh("Tensioned matte canvas stripe",cv,[(0,1,2,3)],plum if j%2==0 else cream,"01")
    mod=panel.modifiers.new("Opaque sewn canvas thickness","SOLIDIFY");mod.thickness=.010
    cube("Straight stitched short front valance",((a+b)/2,-.740,2.099),(b-a,.034,.147),plum if j%2==0 else cream,"01",.008)
cube("Deep mulberry sign face backing",(0,-.749,2.120),(1.48,.044,.222),shade,"01",.012)
cube("Thin hem record line",(0,-.775,2.043),(1.423,.009,.011),gold,"01")
text("Malay header","AIR BALANG",(0,-.775,2.155),.105,cream,"01")
text("English subtitle","ICED DRINKS",(0,-.775,2.071),.041,cream,"01")

# Mobile folding service counter, distinctly open rear ice supply and cup table.
for x in (-.865,.865):
    for y in (-.322,.369):
        cube("Load bearing counter leg",(x,y,.472),(.068,.061,.912),black,"02",.013)
        cube("Counter foot tip",(x,y,.019),(.086,.080,.038),black,"02",.007)
    bar("Rear-grounded diagonal table supports",(x,-.321,.174),(x,.366,.777),.038,.043,metal,"02")
cube("Counter table planks",(0,.021,.921),(2.034,.819,.071),wood,"02",.022)
for x in (-.665,-.332,0,.332,.665):
    cube("Shallow tabletop board seam",(x,.039,.958),(.009,.733,.003),darkWood,"02")
cube("Mulberry taut textile front market apron",(0,-.378,.604),(1.802,.023,.563),plum,"02",.008)
cube("Simple front apron hem stitching",(0,-.394,.340),(1.767,.006,.013),gold,"02")
for x in (-.781,.781):
    cube("End apron hem",(x,-.392,.612),(.012,.007,.501),shade,"02")
cube("Upper cool supplies lower shelf",(0,.210,.258),(1.762,.428,.042),darkWood,"02",.012)
cube("Closed plain cooler chest",(.505,.184,.467),(.643,.394,.401),cream,"02",.026)
cube("Cooler lid split and carry ridge",(.505,.184,.680),(.681,.412,.064),shade,"02",.022)
cube("Cooler front cold retention latch",(.505,-.029,.557),(.119,.043,.081),gold,"02",.010)
cube("Shallow reusable cup supply crate",(-.493,.137,.387),(.590,.355,.211),shade,"02",.020)
for x in (-.721,-.590,-.464,-.332,-.221):
    cube("Long side crate embossed rib",(x,-.043,.390),(.016,.022,.168),plum,"02")

# Each vessel keeps open space above differently colored stock and visible ice.
balangs=[(-.600,green,"AIS LIMAU","ICED LIME",1.658),
        (.014,amber,"TEH AIS","ICED TEA",1.619),
        (.604,rose,"SIRAP","ROSE DRINK",1.667)]
for idx,(x,c,title,sub,zfill) in enumerate(balangs):
    y=.016; r=.186
    cube("Raised compact jar rack reinforced side",(x,.053,1.042),(.440,.444,.163),black,"03",.018)
    cube("Warm front rail colour label",(x,-.177,1.046),(.408,.023,.103),cream,"03",.014)
    text(title+" flavor name",title,(x,-.190,1.069),.036,shade,"03")
    text(title+" secondary label",sub,(x,-.190,1.030),.024,shade,"03")
    cylinder("Skid-proof base coaster",(x,y,1.135),.199,.045,shade,"03",24)
    turns("Rounded transparent open-top vessel body", (x,y,1.15),[(r-.010,0),(r,.014),(r+.010,.031),(r+.010,.535),(r+.004,.557)],glass,"03",28,False)
    turns("Lower clear structural ring",(x,y,1.15),[(.163,-.007),(.194,-.007),(.195,.013),(.185,.021),(.168,.021)],glassGem,"03",24)
    dr=zfill-1.153
    liquid=cylinder("Visible coloured stock with distinct fill height",(x,y,1.153+dr/2),.176,dr,c,"03",26)
    cylinder("Textured deep refill lid seating rim",(x,y,1.719),.204,.043,shade,"03",26)
    cylinder("Moulded flat dispenser lid colour",(x,y,1.747),.194,.017,cream if idx==1 else plum,"03",26)
    cube("Raised rib on screw-cap top handle",(x,y,1.775),(.143,.071,.063),shade,"03",.018)
    for j in range(4):
        ang=j*math.tau/4+.38*idx
        ic=cube("Individually tilted pale drink ice cube",(x+.110*math.cos(ang),y+.098*math.sin(ang),zfill+.008),(.066,.061,.047),ice,"03",.009)
        ic.rotation_euler=(.15+.09*j,.14-.05*j,.4+.56*j)
    if idx==0:
        for j in range(2):
            o=cylinder("Original fresh lime disk rind",(x+(.086 if j==1 else -.075),y-.066,zfill+.022),.054,.013,limeSkin,"03",16)
            o.rotation_euler.x=.23-.39*j
            o=cylinder("Visible lime center face",(x+(.086 if j==1 else -.075),y-.068,zfill+.031),.044,.009,limeFlesh,"03",16)
            o.rotation_euler.x=.23-.39*j
    cylinder("Tap bulkhead black seal",(x,-.182,1.243),.044,.035,black,"03",16,True)
    cylinder("Plain metal spigot horizontal feed pipe",(x,-.245,1.248),.025,.151,metal,"03",14,True)
    cube("Rounded graphite tap body",(x,-.303,1.246),(.096,.093,.075),black,"03",.018)
    cylinder("Downward functional form spout neck",(x,-.329,1.200),.022,.062,metal,"03",16)
    cylinder("Nozzle small black tip",(x,-.329,1.166),.017,.013,black,"03",16)
    cylinder("Lever pivot silver cap",(x,-.303,1.270),.021,.102,metal,"03",14,True)
    if idx:
        cube("Raised stationary graphite tap flag",(x,-.306,1.323),(.049,.044,.112),black,"03",.009)

# Stacks, neat floor-counter drips and the featured cup physically under a single tap.
for x in (-.600,.014,.604):
    cube("Raised near-edge metal cup drip tray",(x,-.332,.970),(.264,.146,.023),metal,"04",.010)
    for xoff in (-.074,-.036,0,.036,.074):
        cube("End of tray punched recess inset",(x+xoff,-.334,.985),(.013,.109,.003),black,"04")
def cup(n,p,r=.052,h=.127):
    wall=turns(n,p,[(r*.64,0),(r*.69,.007),(r,h-.007),(r*1.026,h),(r*.94,h)],cupM,"04",20,False)
    cylinder(n+" bottom disc",(p[0],p[1],p[2]+.004),r*.68,.008,cupM,"04",20)
    return wall
x0=-.600; y0=-.329
cup("Featured demonstration empty cup", (x0,y0,.986),.057,.132)
cup("Unfilled cool cup by rose drink", (.638,-.329,.986),.054,.127)
for count, x, y in ((4,.937,.034),(3,-.927,.110)):
    for j in range(count):
        cup("Nested unbranded cup stock",(x,y,.958+j*.021),.048,.111)
cube("Dark shallow preparation board",(-.405,.282,.971),(.235,.158,.028),darkWood,"04",.008)
for j in range(3):
    cylinder("Small uncut lime by preparation board",(-.464+j*.055,.281,.994),.030,.019,limeSkin,"04",12)

# Y-up glTF: lever local +X rotates, stream and liquid column use only Y scale.
# Anchor positions match the nozzle, vessel side and cup center in the saved source.
lever=attach(bpy.data.objects.new("AIR_BALANG_TAP_LEVER",None),"AIR_BALANG_TAP_LEVER","05")
lever.location=(x0,-.303,1.270)
horn=cube("Featured amber lever paddle",(x0,-.311,1.321),(.057,.047,.115),gold,"05",.012)
bpy.context.view_layer.update()
ww=horn.matrix_world.copy();horn.parent=lever;horn.matrix_world=ww
stream=turns("AIR_BALANG_STREAM",(x0,y0,1.159),[(.001,-.167),(.0085,-.151),(.009,-.025),(.011,0),(.002,0)],flow,"05",14)
# A radial cup vessel and matching shallow fill, making a narrow gap safe at top.
fill=turns("AIR_BALANG_CUP_FILL",(x0,y0,.996),[(.001,0),(.032,0),(.050,.095),(.001,.095)],flow,"05",20)
def animate(o,curves):
    for path,series in curves.items():
        for f,val in series:
            setattr(o,path,val)
            o.keyframe_insert(data_path=path,frame=f,group="Illustrative drink pour")
    a=o.animation_data.action;a.name=o.name+"_authored_motion"
    t=o.animation_data.nla_tracks.new();t.name="AIR_BALANG_POUR"
    t.strips.new("One featured local-only pour",0,a)
    o.animation_data.action=None
def V(t):
    return [(f,(a,0,0)) for f,a in t]
def SZ(t):return [(f,(1,1,v)) for f,v in t]
animate(lever,{"rotation_euler":V([(0,0),(5,0),(12,.87),(39,.87),(47,0),(54,0)])})
animate(stream,{"scale":SZ([(0,.001),(10,.001),(16,1),(37,1),(42,.001),(54,.001)])})
animate(fill,{"scale":SZ([(0,.010),(15,.010),(21,.22),(30,.57),(40,.96),(54,.96)])})

def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat("-Z","Y").to_euler()
floor=material("Deep neutral market studio floor",(.134,.158,.154),.72)
cube("Studio ground only",(0,0,-.032),(180,180,.062),floor,"06")
bpy.ops.object.camera_add(location=(2.45,-6.02,2.82))
cam=attach(bpy.context.object,"Editorial stall camera","06")
aim(cam,(-.015,-.020,1.235))
cam.data.type="ORTHO";cam.data.ortho_scale=3.40
scene.camera=cam
for n,p,e,c,sz in (
    ("Warm wide softbox",(2.7,-3.7,4.7),710,(1,.862,.686),4.2),
    ("Cool window rim",(-3.9,-3.0,3.2),640,(.68,.87,1),4.3),
    ("Rear market light",(3.15,2.43,4.4),810,(.91,1,.80),3.4),
):
    bpy.ops.object.light_add(type="AREA",location=p)
    o=attach(bpy.context.object,n,"06");o.data.energy=e;o.data.color=c;o.data.shape="DISK";o.data.size=sz
    aim(o,(0,0,1.14))
scene.world=bpy.data.worlds.new("Studio soft ambient");scene.world.use_nodes=True
bg=scene.world.node_tree.nodes["Background"];bg.inputs[0].default_value=(.44,.51,.60,1);bg.inputs[1].default_value=.42
scene.render.engine="CYCLES";scene.cycles.samples=26;scene.cycles.use_denoising=True
scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.view_settings.view_transform="AgX";scene.render.image_settings.file_format="PNG"
scene.render.filepath=str(D/"previews"/"studio.png")
scene.frame_set(0)
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.wm.save_as_mainfile(filepath=str(D/(SLUG+".blend")))
if "--skip-render" not in sys.argv:
    bpy.ops.render.render(write_still=True)
    if "--pour-review" in sys.argv:
        cam.location=(.44,-3.70,1.83)
        aim(cam,(x0,-.30,1.178));cam.data.ortho_scale=.61
        for label,f in (("ready",0),("pour",30),("filled",54)):
            scene.frame_set(f);scene.render.filepath=str(D/"previews"/(label+".png"))
            bpy.ops.render.render(write_still=True)
        scene.frame_set(0)

chosen=[]
for key,c in col.items():
    if key=="06":continue
    if key=="05":
        chosen.extend(c.objects);continue
    by=defaultdict(list)
    for o in list(c.objects):
        if o.modifiers or o.type=="FONT":
            bpy.ops.object.select_all(action="DESELECT");o.select_set(True);bpy.context.view_layer.objects.active=o
            bpy.ops.object.convert(target="MESH");o=bpy.context.view_layer.objects.active
        # Transparent vessels and cup shells are independently sorted on export;
        # combine each remaining material group to limit draw calls.
        if o.data.materials[0].diffuse_color[3]<1:
            chosen.append(o)
        else:by[o.data.materials[0].name].append(o)
    for m,obs in sorted(by.items()):
        bpy.ops.object.select_all(action="DESELECT")
        for o in obs:o.select_set(True)
        a=obs[0];bpy.context.view_layer.objects.active=a
        if len(obs)>1:bpy.ops.object.join()
        a.name=c.name[3:]+" | "+m;chosen.append(a)
bpy.ops.object.select_all(action="DESELECT")
for o in chosen:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(D/"exports"/(SLUG+".glb")),export_format="GLB",use_selection=True,export_animations=True,
    export_animation_mode="NLA_TRACKS",export_force_sampling=True,export_cameras=False,export_lights=False,export_texcoords=False)
