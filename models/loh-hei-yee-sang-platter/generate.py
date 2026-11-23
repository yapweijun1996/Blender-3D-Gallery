"""Create an original tabletop model and one authored ingredient-toss clip."""
from math import cos, sin, pi, tau, radians
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector

root=Path(__file__).resolve().parent
slug="loh-hei-yee-sang-platter"
for p in ("exports","previews"):
    (root/p).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system="METRIC"
scene.render.fps=24
scene.frame_start=0
scene.frame_end=50
rng=random.Random(20261123)
groups={}
for section,name in [
    ("table","01 Tabletop and lacquer placemat"),("plate","02 Serving porcelain"),
    ("dishes","03 Sauce dishes and utensil rests"),("food","04 Animated ingredient parcels"),
    ("sticks","05 Animated chopstick pairs"),("studio","06 Studio (not exported)")
]:
    coll=bpy.data.collections.new(name);scene.collection.children.link(coll);groups[section]=coll


def material(name,rgb,rough=.6,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*rgb,1)
    p=m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=(*rgb,1)
    p.inputs["Roughness"].default_value=rough;p.inputs["Metallic"].default_value=metal
    return m


rosewood=material("Smoked rosewood lacquer",(.165,.049,.036),.40)
wood_edge=material("Caramel lacquer edge",(.32,.125,.072),.46)
lacquer=material("Festive vermilion lacquer",(.48,.043,.032),.48)
deep_red=material("Dark red lacquer inlay",(.29,.028,.032),.52)
ceramic=material("Warm stoneware porcelain glaze",(.68,.61,.46),.33)
cobalt=material("Indigo slip decoration",(.050,.120,.312),.41)
gold=material("Soft brass lip detailing",(.67,.47,.17),.40,.42)
ginger=material("Pomegranate pickled-ginger strips",(.54,.028,.099),.57)
ginger_tip=material("Bright ginger cut edge",(.94,.213,.36),.53)
carrot=material("Tangerine carrot ribbons",(.89,.157,.015),.57)
carrot_tip=material("Sunlit carrot cut edge",(1,.47,.090),.53)
cream=material("Ivory radish shreds",(.80,.81,.63),.66)
cream_tip=material("Radish palest cut edge",(1,.94,.76),.61)
cucumber=material("Light jade cucumber ribbons",(.228,.445,.071),.57)
cucumber_tip=material("Cucumber dark green rind",(.084,.34,.086),.59)
pomelo=material("Champagne citrus arils",(.95,.592,.251),.63)
pomelo_tip=material("Pale citrus vesicles",(1,.74,.425),.66)
cracker=material("Golden pillow crackers",(.73,.361,.086),.68)
cracker_tip=material("Toasted cracker edges",(.92,.547,.168),.66)
salmon=material("Coral fish slice",(.75,.155,.096),.47)
salmon_tip=material("Warm cream marbling",(.95,.61,.44),.52)
sauce=material("Dark glossy fruit dressing",(.285,.073,.025),.29)
oil=material("Amber dressing surface",(.61,.283,.038),.32)
seed=material("Toasted sesame accent",(.43,.262,.101),.67)
sticks=material("Ebony stained bamboo",(.17,.061,.031),.38)


class Shape:
    def __init__(self):
        self.vertices=[];self.faces=[];self.materials=[];self.surfaces=[];self.smooth=[]
    def add(self,verts,faces,mat,soft=False):
        k=len(self.vertices);self.vertices.extend(verts)
        if mat not in self.materials:
            self.materials.append(mat)
        ix=self.materials.index(mat)
        for face in faces:
            self.faces.append(tuple(k+i for i in face));self.surfaces.append(ix);self.smooth.append(soft)
    def lathe(self,profile,mat,x=0,y=0,n=56,caps=True):
        verts=[(x+r*cos(t*tau/n),y+r*sin(t*tau/n),z) for r,z in profile for t in range(n)]
        faces=[tuple(reversed(range(n)))] if caps else []
        for i in range(len(profile)-1):
            for t in range(n):
                u=(t+1)%n;faces.append((i*n+t,i*n+u,(i+1)*n+u,(i+1)*n+t))
        if caps: faces.append(tuple(range((len(profile)-1)*n,len(verts))))
        self.add(verts,faces,mat,True)
    def extrude(self,profile,base,top,mat):
        n=len(profile)
        v=[(x,y,z) for z in (base,top) for x,y in profile]
        f=[tuple(reversed(range(n))),tuple(range(n,n*2))]
        f.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
        self.add(v,f,mat)
    def ribbon(self,x,y,z,angle,length,width,mat,bend=.006,height=.004):
        n=4;verts=[]
        for k in range(n):
            t=k/(n-1);xx=(t-.5)*length; yy=bend*sin(t*pi)
            half=width*(.38+.12*sin(t*pi));zz=z+height*sin(pi*t)+.002*sin(2*pi*t)
            for side,dz in ((-1,0),(1,0),(1,-.0010),(-1,-.0010)):
                offset=yy+side*half
                verts.append((x+cos(angle)*xx-sin(angle)*offset,y+sin(angle)*xx+cos(angle)*offset,zz+dz))
        f=[]
        for j in range(n-1):
            for k in range(4):
                q=(k+1)%4;f.append((4*j+k,4*(j+1)+k,4*(j+1)+q,4*j+q))
        f.extend(((3,2,1,0),(4*n-4,4*n-3,4*n-2,4*n-1)))
        self.add(verts,f,mat)
    def box(self,center,dims,mat,angle=0):
        x,y,z=center;u,v,h=(a/2 for a in dims)
        xy=[(-u,-v),(u,-v),(u,v),(-u,v)]
        self.extrude([(x+cos(angle)*a-sin(angle)*b,y+sin(angle)*a+cos(angle)*b) for a,b in xy],z-h,z+h,mat)
    def make(self,name,group,origin=(0,0,0)):
        mesh=bpy.data.meshes.new(name)
        mesh.from_pydata(self.vertices,[],self.faces);mesh.update()
        for m in self.materials: mesh.materials.append(m)
        for p,ix,smooth in zip(mesh.polygons,self.surfaces,self.smooth):p.material_index=ix;p.use_smooth=smooth
        o=bpy.data.objects.new(name,mesh);groups[group].objects.link(o);o.location=origin
        return o


# Warm low tabletop tile, cropped as a diorama rather than a full table.
table=Shape()
table.lathe([(.478,0),(.527,.007),(.546,.019),(.546,.033),(.536,.041)],rosewood,x=-.015,y=.005,n=56)
table.lathe([(.533,.018),(.547,.020),(.548,.024),(.536,.026)],wood_edge,x=-.015,y=.005,n=56,caps=False)
table.lathe([(.376,.041),(.397,.042),(.402,.045)],lacquer,n=48)
table.lathe([(.389,.047),(.394,.0471),(.396,.049),(.390,.0491)],deep_red,n=48,caps=False)
table.make("Tabletop_lacquer", "table")

plate=Shape()
plate.lathe([(.211,.046),(.222,.048),(.239,.057),(.267,.068),(.291,.085),
             (.299,.097),(.2995,.103),(.294,.111),(.275,.112),(.261,.103),
             (.238,.081),(.211,.069),(.009,.069)],ceramic,n=56)
plate.lathe([(.280,.108),(.283,.108),(.285,.113),(.283,.114),(.280,.114)],cobalt,n=56,caps=False)
plate.lathe([(.289,.110),(.291,.110),(.2915,.113),(.290,.114)],gold,n=56,caps=False)
plate.lathe([(.204,.070),(.206,.070),(.207,.071),(.205,.072)],cobalt,n=48,caps=False)
plate.make("Serving_platter_unchanged","plate")

dishes=Shape()
for x,y,surf in [(-.286,.268,sauce),(.281,.277,oil)]:
    dishes.lathe([(.032,.041),(.051,.044),(.061,.057),(.063,.073),(.058,.081),
                 (.051,.078),(.041,.061),(.009,.061)],ceramic,x,y,n=40)
    dishes.lathe([(.049,.077),(.057,.078),(.059,.080),(.057,.081),(.055,.081)],cobalt,x,y,n=40,caps=False)
    dishes.lathe([(.032,.061),(.044,.066),(.044,.069),(.009,.0695)],surf,x,y,n=36)
for x,y,theta in [(-.432,-.112,.31),(.430,.105,-.25)]:
    dishes.box((x,y,.052),(.063,.054,.019),ceramic,theta)
    dishes.box((x,y-.024,.062),(.048,.008,.005),gold,theta)
dishes.make("Two_sauce_dishes_and_rests_unchanged","dishes")


def polygon(x,y,rx,ry,n,rot=0):
    return [(x+rx*cos(t*tau/n)*cos(rot)-ry*sin(t*tau/n)*sin(rot),
             y+rx*cos(t*tau/n)*sin(rot)+ry*sin(t*tau/n)*cos(rot)) for t in range(n)]


def schedule(obj,frames):
    for frame,location,rotation in frames:
        obj.location=location;obj.rotation_euler=rotation
        obj.keyframe_insert(data_path="location",frame=frame-1,group="Authored toss")
        obj.keyframe_insert(data_path="rotation_euler",frame=frame-1,group="Authored toss")
    action=obj.animation_data.action
    action.name=obj.name+"_toss_channels"
    # The Blender glTF exporter merges equal track names across moving objects.
    track=obj.animation_data.nla_tracks.new()
    track.name="LOH_HEI_TOSS"
    track.strips.new("Authored motion",0,action)
    obj.animation_data.action=None


def pad(x,y,z,angle,r):
    return (x+cos(angle)*r,y+sin(angle)*r,z)


for k,(ingredient,theta,form,base,light) in enumerate([
    ("Carrot",-106,"ribbon",carrot,carrot_tip),
    ("Cucumber",-52,"ribbon",cucumber,cucumber_tip),
    ("White_radish",6,"ribbon",cream,cream_tip),
    ("Pickled_ginger",73,"ribbon",ginger,ginger_tip),
    ("Pomelo",133,"citrus",pomelo,pomelo_tip),
    ("Pillow_cracker",194,"cracker",cracker,cracker_tip),
    ("Fish_slices",0,"fish",salmon,salmon_tip),
]):
    for j in range(3):
        a=radians(theta)
        if form=="fish":
            early=(.035-j*.035,.008+j*.016,.073+j*.005)
        else:
            early=pad(.159*cos(a),.159*sin(a),.072+.004*j,a+pi/2,(j-1)*.035)
        p=Shape()
        if form=="ribbon":
            for i in range(16):
                px=rng.uniform(-.033,.033);py=rng.uniform(-.025,.025)
                z=rng.uniform(.006,.030)*(1-max(abs(px),abs(py))*7)+.005
                p.ribbon(px,py,z,rng.uniform(-pi,pi),rng.uniform(.043,.073),rng.uniform(.0061,.0098),
                         light if i%4==0 else base,rng.uniform(.003,.015),rng.uniform(.003,.009))
        elif form=="citrus":
            for i in range(19):
                x,y=rng.uniform(-.035,.035),rng.uniform(-.022,.022)
                z=rng.uniform(.002,.012)
                p.extrude(polygon(x,y,rng.uniform(.004,.012),rng.uniform(.004,.009),6,rng.random()*pi),z,z+rng.uniform(.006,.011),light if i%4==0 else base)
        elif form=="cracker":
            for i in range(8):
                x,y=rng.uniform(-.032,.032),rng.uniform(-.025,.025)
                z=rng.uniform(.005,.021)
                rad=rng.uniform(.010,.015);spin=rng.random()*pi
                p.extrude(polygon(x,y,rad,rad*.75,4,spin),z,z+.010,base)
                p.extrude(polygon(x,y,rad*.75,rad*.57,4,spin),z+.010,z+.012,light)
        else:
            for i in range(3):
                x,y=(i-1)*.017,-i*.012
                poly=[(x-.036,y-.013),(x-.013,y-.022),(x+.027,y-.013),
                      (x+.037,y+.002),(x+.017,y+.013),(x-.026,y+.010)]
                p.extrude(poly,.004+i*.006,.010+i*.006,base)
                for rib in range(3):
                    p.ribbon(x-.02+rib*.017,y-.004,.0105+i*.006,1.08,.021,.0027,light,bend=.002,height=.0002)
        o=p.make(f"{ingredient}_parcel_{j+1}","food",early)
        end_a=(12+(k*3+j)*137.50776)*pi/180
        distance=.050+((k*11+j*13)%15)*.0083
        if (Vector((distance*cos(end_a),distance*sin(end_a))) - Vector(early[:2])).length < .034:
            end_a += .67
        end=(distance*cos(end_a),distance*sin(end_a),.072+(j%2)*.005)
        angle=rng.uniform(-pi,pi)
        loft=.094+((k*7+j*3)%8)*.010
        choose=3 if form=="fish" else 0
        delay=(k*3+j*4)%5+choose
        # Small parcels rise independently and land within the serving well.
        schedule(o,[
            (1,early,(0,0,0)),
            (8+delay,early,(0,0,0)),
            (18+delay,(early[0]*.69+end[0]*.31,early[1]*.69+end[1]*.31,.078+loft),(.36,-.30,angle*.36)),
            (26+delay,(early[0]*.30+end[0]*.70,early[1]*.30+end[1]*.70,.076+loft*.57),(.21,-.11,angle*.69)),
            (36+delay,end,(0,0,angle)),
            (51,end,(0,0,angle)),
        ])


bed=Shape()
# Low scattered accents remain on the serving surface throughout.
for i in range(22):
    ang=rng.random()*tau
    r=rng.uniform(.027,.199)
    x,y=r*cos(ang),r*sin(ang)
    bed.extrude(polygon(x,y,.0038,.0019,6,ang),.071,.0732,seed)
bed.make("Sesame_scatter_unchanged","plate")


def tapered_stick(shape, y, mat):
    # The +X end is the narrow inward tip.
    verts = [(x,y+s*w,z) for x,w in ((-.108,.0067),(.113,.0028)) for s,z in
             ((-1,-w),(-1,w),(1,w),(1,-w))]
    shape.add(verts,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],mat)


for side,rest in [("Left",(-.419,-.113,.068)),("Right",(.419,.111,.068))]:
    s=Shape();sign=1 if side=="Left" else -1;yaw=.31 if sign==1 else pi-.25
    for y in (-.012,.012):
        tapered_stick(s,y,sticks)
        s.box((-.088,y,0),(.015,.0138,.014),gold)
        s.box((-.098,y,0),(.008,.014,.014),lacquer)
    o=s.make(side+"_paired_chopsticks","sticks",rest)
    schedule(o,[
        (1,rest,(0,0,yaw)),
        (8,(-sign*.293,rest[1],.116),(0,.16,yaw)),
        (15,(-sign*.235,rest[1]*.86,.153),(0,.35,yaw+sign*.10)),
        (23,(-sign*.219,rest[1]*.61,.231),(0,-.38,yaw-sign*.11)),
        (31,(-sign*.244,rest[1]*.75,.194),(0,-.14,yaw-sign*.018)),
        (44,rest,(0,0,yaw)),(51,rest,(0,0,yaw)),
    ])

def aim(o,target):
    o.rotation_euler=(Vector(target)-o.location).to_track_quat("-Z","Y").to_euler()

floor=Shape()
floor.box((0,0,-.037),(200,200,.054),material("Studio spruce shadow floor",(.047,.059,.054),.72))
floor.make("Studio floor","studio")
bpy.ops.object.camera_add(location=(.88,-1.38,1.44))
camera=bpy.context.object
for c in list(camera.users_collection): c.objects.unlink(camera)
groups["studio"].objects.link(camera)
aim(camera,(-.018,.009,.045));camera.data.type="ORTHO";camera.data.ortho_scale=1.22;scene.camera=camera
for name,pos,energy,color,size in [
    ("Large warm window",(-.76,-.85,1.86),61,(1,.88,.72),1.14),
    ("Cool overhead fill",(1.10,.19,1.67),37,(.78,.89,1),1.35),
    ("Soft rear reflector",(-.43,.99,1.44),38,(1,.93,.77),.86),
]:
    bpy.ops.object.light_add(type="AREA",location=pos)
    o=bpy.context.object
    for c in list(o.users_collection): c.objects.unlink(o)
    groups["studio"].objects.link(o)
    o.name=name;o.data.energy=energy;o.data.color=color;o.data.shape="DISK";o.data.size=size
    aim(o,(0,0,.06))
scene.world=bpy.data.worlds.new("Soft room ambient")
scene.world.use_nodes=True
scene.world.node_tree.nodes["Background"].inputs[0].default_value=(.36,.40,.47,1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value=.27
scene.render.engine="CYCLES";scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.filepath=str(root/"previews"/"studio.png")
scene.view_settings.view_transform="AgX"
scene.view_settings.exposure=-.43
scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(root/(slug+".blend")))
if "--skip-render" not in sys.argv:
    bpy.ops.render.render(write_still=True)
    if "--mixed-review" in sys.argv:
        scene.frame_set(50)
        scene.render.filepath=str(root/"previews"/"mixed-review.png")
        bpy.ops.render.render(write_still=True)
        scene.frame_set(0)
bpy.ops.object.select_all(action="DESELECT")
for group,coll in groups.items():
    if group=="studio": continue
    for obj in coll.objects: obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(root/"exports"/(slug+".glb")),export_format="GLB",
                         use_selection=True,export_animations=True,export_animation_mode="NLA_TRACKS",
                         export_force_sampling=True,export_cameras=False,export_lights=False,export_texcoords=False)
