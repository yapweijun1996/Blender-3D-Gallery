import math
import sys
from collections import defaultdict
import random
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
for sub in ("exports", "previews"):
    (ROOT / sub).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
parts = {}
for key, name in {
    "frame":"01 Structural frame and waist counter",
    "awning":"02 Cloth awning and openings",
    "rail":"03 Display rail and reusable hanger loops",
    "flowers":"04 Jasmine-like and marigold-like retail garlands",
    "service":"05 Coiled stock tray leaf bundles baskets and thread",
    "studio":"06 Studio only",
}.items():
    c=bpy.data.collections.new(name);scene.collection.children.link(c);parts[key]=c


def material(name, color, rough=.45, metal=0, glow=0, alpha=1):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*color, alpha)
    s = m.node_tree.nodes.get("Principled BSDF")
    s.inputs["Base Color"].default_value = (*color, 1)
    s.inputs["Metallic"].default_value = metal
    s.inputs["Roughness"].default_value = rough
    s.inputs["Alpha"].default_value = alpha
    s.inputs["Emission Color"].default_value = (*color, 1)
    s.inputs["Emission Strength"].default_value = glow
    if alpha < 1:
        m.surface_render_method = "BLENDED"
    return m


def attach(o, name, group, mat=None):
    o.name = name
    for coll in list(o.users_collection):
        coll.objects.unlink(o)
    parts[group].objects.link(o)
    if mat:
        o.data.materials.append(mat)
    return o


def cube(name, pos, size, mat, group="case", radius=.008):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    o = attach(bpy.context.object,name,group,mat)
    o.dimensions = size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if radius > .008:
        bevel = o.modifiers.new("Powder-coated edge radius","BEVEL")
        bevel.width = radius
        bevel.segments = 2 if radius >= .025 else 1
        bevel.harden_normals = True
        normal = o.modifiers.new("Weighted corner normals","WEIGHTED_NORMAL")
        normal.keep_sharp = True
    return o


def cylinder(name,pos,radius,depth,mat,group,side=False,n=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n,radius=radius,depth=depth,location=pos)
    o = attach(bpy.context.object,name,group,mat)
    if side:
        o.rotation_euler.x = math.pi/2
    for p in o.data.polygons:
        p.use_smooth = len(p.vertices)==4
    return o


frame=material("Aubergine powder-coated stall frame",(.126,.060,.111),.50,.17)
ink=material("Deep wine frame edge shade",(.064,.031,.063),.62)
wood=material("Warm laminated timber counter",(.391,.205,.101),.56)
wood_light=material("Satin pale oak shelf insert",(.52,.303,.163),.53)
linen=material("Unbleached awning fabric",(.64,.498,.321),.85)
linen_red=material("Dusty rose awning stripe",(.45,.156,.160),.86)
linen_dark=material("Dark bound fold seam",(.36,.129,.121),.80)
metal=material("Warm bronze hanging hardware",(.52,.38,.22),.43,.48)
stone=material("Dusty grey counter mat",(.265,.224,.197),.88)
leaf=material("Deep green leaf backing",(.098,.255,.088),.79)
leaf_light=material("Light jade cut leaf vein",(.21,.36,.105),.79)
bud=material("Ceramic-white waxy jasmine-like buds",(.90,.81,.56),.63)
bud_tip=material("Pearl ivory petal tips",(.98,.91,.69),.57)
gold=material("Marigold-like saffron corollas",(.98,.44,.034),.61)
amber=material("Orange ruffled marigold-like petals",(.89,.232,.026),.61)
inner=material("Golden sunlit petal centres",(1,.64,.067),.57)
rattan=material("Stripped natural rattan",(.47,.277,.106),.73)
rattan_light=material("Pale woven basket rim",(.65,.431,.190),.69)
rope=material("Neutral cotton lacing and spool thread",(.70,.56,.35),.82)

rng=random.Random(863)


def mesh_object(name,verts,faces,mat,group):
    d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update()
    o=bpy.data.objects.new(name,d);parts[group].objects.link(o);o.data.materials.append(mat)
    return o


def rod(name,a,b,r,mat,group,n=9):
    p,q=Vector(a),Vector(b);d=q-p
    o=cylinder(name,(p+q)*.5,r,d.length,mat,group,n=n)
    o.rotation_euler=d.to_track_quat("Z","Y").to_euler()
    return o


def cord(name,points,r,mat,group):
    points=[Vector(p) for p in points]
    verts=[];faces=[];k=5
    for i,p in enumerate(points):
        t=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
        u=Vector((0,1,0)) if abs(t.y)<.94 else Vector((1,0,0));u=(u-t*u.dot(t)).normalized()
        v=t.cross(u)
        for j in range(k):
            theta=j*math.tau/k
            verts.append(tuple(p+r*(u*math.cos(theta)+v*math.sin(theta))))
    for i in range(len(points)-1):
        for j in range(k):
            a=i*k+j;b=i*k+(j+1)%k
            faces.append((a,b,b+k,a+k))
    faces.extend((tuple(reversed(range(k))),tuple(range((len(points)-1)*k,len(verts)))))
    return mesh_object(name,verts,faces,mat,group)


# Low stock-and-display cabinet, not a generic empty tent shell.
for x in (-.967,.967):
    for y in (-.297,.325):
        cube("Squared replaceable floor shoe",(x,y,.058),(.137,.138,.116),ink,"frame",.013)
        cube("Modular vertical square-tube stall leg",(x,y,.498),(.070,.072,.912),frame,"frame",.009)
cube("Dark toe-kick strip",(0,-.326,.151),(1.953,.029,.061),ink,"frame",.008)
cube("Inner cabinet base shelf",(0,.029,.198),(1.906,.617,.052),wood,"frame",.011)
cube("Back-of-counter cross stretcher",(0,.342,.502),(1.938,.067,.067),frame,"frame",.010)
for x in (-.962,.957):
    cube("Side mullion bin guard",(x,.022,.555),(.074,.642,.066),frame,"frame",.009)
for x in (-.950,.105):
    cube("Carpenter-fitted low vertical storage divider",(x,.029,.470),(.063,.578,.525),wood,"frame",.012)
cube("Partial fluted left retail face",(-.417,-.307,.445),(1.038,.052,.503),wood,"frame",.013)
for i in range(8):
    x=-.860+i*.122
    cube("Raised linear front relief board",(x,-.338,.446),(.071,.020,.472),wood_light if i%4==0 else wood,"frame",.004)
cube("Pale oak worktop and sales ledge",(0,-.014,.861),(2.116,.737,.080),wood_light,"frame",.024)
cube("Thin worktop apron band",(0,-.369,.835),(2.071,.059,.048),ink,"frame",.009)
cube("Small counter mat just beneath stock tray",(.124,-.093,.903),(1.057,.477,.009),stone,"service",.007)
for x in (-.967,.974):
    cube("Slender rear canopy upright", (x,.323,1.437),(.076,.079,1.304),frame,"awning",.010)
    rod("Awning side angled support brace",(x,.319,1.758),(x,-.431,1.947),.025,frame,"awning")
rod("Front long awning ring rail",(-1.021,-.432,1.947),(1.022,-.432,1.947),.028,frame,"awning",12)
rod("Back longer awning roll",(-1.021,.452,2.078),(1.022,.452,2.078),.023,frame,"awning",12)


def awning_z(x,y):
    return 2.004 + .113*(y+.435)/.895 + .011*math.cos((x+1.075)*math.tau/.268)

# Eight wide bands in a repeating restrained palette, with sewn scallops (not a brand pattern).
for i in range(8):
    x0=-1.064+i*.266;x1=x0+.266
    xs=[x0+(x1-x0)*j/6 for j in range(7)]
    ys=[-.468,-.218,.055,.298,.468]
    v=[(x,y,awning_z(x,y)) for y in ys for x in xs]
    f=[(j*7+i,j*7+i+1,(j+1)*7+i+1,(j+1)*7+i) for j in range(4) for i in range(6)]
    top=mesh_object("Tensioned awning cloth panel",v,f,linen_red if i%3==1 else linen,"awning")
    top.modifiers.new("Canvas physical thickness","SOLIDIFY").thickness=.004
    upper=[]
    for j,x in enumerate(xs):
        z=awning_z(x,-.470)
        upper.extend(((x,-.473,z-.004),(x,-.479,z-.060-.033*math.sin(j*math.pi/6))))
    faces=[(2*j,2*j+2,2*j+3,2*j+1) for j in range(6)]
    flap=mesh_object("Scalloped awning valance",upper,faces,linen_red if i%3==1 else linen,"awning")
    flap.modifiers.new("Discrete bound cloth hem thickness","SOLIDIFY").thickness=.005
    cord("Awning sewn scalloped lower binding",upper[1::2],.004,linen_dark,"awning")
for x in (-1.048,1.048):
    cord("Awning sealed folded side bead",[(x,y,awning_z(x,y)+.005) for y in [-.46,-.18,.12,.43]],.009,linen_dark,"awning")

rod("Customer-visible front garland rail",(-.980,-.190,1.772),(.980,-.190,1.772),.019,metal,"rail",12)
for x in (-.958,.956):
    rod("Hanging rail outer extension bracket",(x,.332,1.774),(x,-.213,1.774),.023,frame,"rail",10)
    rod("Rail keeper vertical strap",(x,-.192,1.768),(x,-.192,1.964),.010,metal,"rail",8)


class BlossomMesh:
    def __init__(self):
        self.v=[];self.f=[];self.mats=[];self.assign=[]
    def add(self,verts,faces,mats):
        base=len(self.v);self.v.extend(verts)
        for face,mat in zip(faces,mats):
            self.f.append(tuple(base+i for i in face))
            if mat not in self.mats:self.mats.append(mat)
            self.assign.append(self.mats.index(mat))
    def head(self,center,r,kind,orient=0,table=False,accent=False):
        x,y,z=center;verts=[];n=8
        # The pale wax-star silhouette is tighter and angular; warm flower
        # heads have a scalloped domed skirt and differently faceted centre.
        # Use one material per head to avoid splitting the same surface
        # at tiny material seams. Alternate colour between adjacent heads.
        if kind=="pale":
            petal=bud_tip if accent else bud
            pattern=(1.0,.52,1.0,.55,1.0,.57,1.0,.53)
            rings=((.60,.012),(1,-.005))
        else:
            petal=inner if accent else (gold if kind=="gold" else amber)
            pattern=(1.0,.69,1.0,.66,.98,.70,1.0,.76)
            rings=((.64,.016),(1,-.009))
        for radial,depth in rings:
            for j in range(n):
                a=(j/n)*math.tau+orient
                dx=r*radial*pattern[j]*math.cos(a)
                offset=r*radial*pattern[j]*math.sin(a)
                verts.append((x+dx,y+offset,z-depth) if table else (x+dx,y+depth,z+offset))
        verts.append((x,y,z+.020) if table else (x,y-.022,z))
        faces=[tuple(reversed(range(n)))]
        for j in range(n):
            k=(j+1)%n
            faces.extend(((j,k,n+k,n+j),(n+j,n+k,2*n)))
        self.add(verts,faces,[petal]*len(faces))
    def finish(self,name):
        m=bpy.data.meshes.new(name);m.from_pydata(self.v,[],self.f);m.update()
        o=bpy.data.objects.new(name,m);parts["flowers"].objects.link(o)
        for mat in self.mats:m.materials.append(mat)
        for p,index in zip(m.polygons,self.assign):p.material_index=index;p.use_smooth=True
        return o


def shaped_hoop(x,t,width,drop,y=-.194):
    # More vertical sides than a half-disc; round heel so it reads as a strung garland.
    return (x + width*(t-.5), y+.014*math.sin(math.tau*t),1.682-drop*(math.sin(math.pi*t)**.78))


def resample_hoop(x,width,drop,n):
    points=[Vector(shaped_hoop(x,j/80,width,drop)) for j in range(81)]
    dist=[0.]
    for a,b in zip(points,points[1:]):dist.append(dist[-1]+(b-a).length)
    output=[];i=0
    for j in range(n):
        t=dist[-1]*j/(n-1)
        while i<len(dist)-2 and dist[i+1]<t:i+=1
        u=(t-dist[i])/(dist[i+1]-dist[i])
        output.append(tuple(points[i].lerp(points[i+1],u)))
    return output


for i,(x,width,drop,kind) in enumerate([
    (-.787,.247,.43,"pale"),(-.474,.247,.52,"gold"),(-.159,.242,.46,"pale"),
    (.153,.253,.51,"amber"),(.466,.235,.45,"pale"),(.779,.250,.515,"gold"),
]):
    garland=BlossomMesh()
    n=24 if drop>.48 else 22
    pts=[shaped_hoop(x,j/(2*n),width,drop) for j in range(2*n+1)]
    cord("Reusable cotton garland loop",pts[::4]+[pts[-1]] if n%2 else pts[::4],.005,rope,"rail")
    for sign,t in ((-1,0),(1,1)):
        a=shaped_hoop(x,t,width,drop)
        cord("Over-rail garland stock hanger",[(a[0],-.195,1.674),(a[0],-.205,1.731),(a[0],-.211,1.775),
             (a[0],-.187,1.795),(a[0],-.169,1.773),(a[0],-.174,1.742)],.006,rope,"rail")
        cylinder("Small brass hanger clip", (a[0],-.192,1.759),.012,.019,metal,"rail",n=8)
    for j,(a,b,c) in enumerate(resample_hoop(x,width,drop,n)):
        center=(a+rng.uniform(-.004,.004),b+rng.uniform(-.005,.005),c+rng.uniform(-.004,.004))
        radius=rng.uniform(.029,.036) if kind=="pale" else rng.uniform(.033,.041)
        garland.head(center,radius,kind,rng.random()*math.tau,accent=(j%3==0))
        if kind=="pale" and j%3==0:
            garland.head((a+.011,b+.003,c+.005),radius*.63,kind,rng.random()*math.tau)
    garland.finish(("Ivory jasmine-like" if kind=="pale" else "Ochre marigold-like")+f" retail garland {i+1}")


# Split on-counter work and stock areas, featuring physical bottoms and lips.
def tray(name,x,y,wide,deep,mat):
    cube(name+" base",(x,y,.918),(wide,deep,.025),mat,"service",.010)
    for side in (-1,1):
        cube(name+" side rim",(x+side*(wide/2-.017),y,.949),(.025,deep,.050),mat,"service",.007)
    for side in (-1,1):
        cube(name+" shallow end rim",(x,y+side*(deep/2-.017),.942),(wide,.026,.039),mat,"service",.006)

tray("Low open garland wrapping tray",-.568,-.124,.674,.370,rattan_light)
tray("Perforation-free square leaf and supply tray",.254,-.062,.372,.382,wood)
roll=BlossomMesh()
for i in range(16):
    a=math.tau*i/16
    roll.head((-.566+.184*math.cos(a),-.118+.094*math.sin(a),.946),
              rng.uniform(.016,.021),"pale" if i<8 else "amber",a,table=True,accent=not (i%2))
roll.finish("Two folded retail specimen strands in wrapping tray")
for j in range(7):
    x=.156+j*.035;y=-.125+(j%3)*.012
    x2=x+.044;y2=y+.138
    m=mesh_object("Loose leaf backing blade",
                  [(x,y,.938),(x-.032,y+.068,.946),(x2,y2,.957),(x+.052,y+.082,.950),(x+.016,y+.075,.969)],
                  [(0,1,4),(1,2,4),(2,3,4),(3,0,4)],leaf,"service")
    cord("Raised small leaf vein",[(x,y+.011,.939),(x+.017,y+.076,.970),(x2,y2-.001,.958)],.003,leaf_light,"service")
for x,r,c in ((.669,.054,rope),(.809,.058,linen_red),(.920,.039,rope)):
    cylinder("Thread reel wooden base", (x,-.161,.923),r,.029,wood_light,"service",n=14)
    cylinder("Rolled spool thread band", (x,-.161,.956),r*.772,.057,c,"service",n=14)
    cylinder("Thread reel wooden upper flange",(x,-.161,.991),r,.017,wood_light,"service",n=14)
    cylinder("Visible centre spool eye",(x,-.161,1.001),r*.283,.008,ink,"service",n=10)
    for q in range(3):
        cylinder("Wound thread roll relief ring",(x,-.161,.935+q*.014),r*.802,.005,c,"service",n=12)
# Large open basket visible under the right half of the counter.
cube("Basket low structural board",(.538,-.024,.246),(.653,.465,.044),rattan,"service",.014)
for side in (-1,1):
    cube("Basket woven light open side wall",(.538+side*.314,-.024,.355),(.041,.445,.214),rattan,"service",.009)
for j in range(5):
    for side in (-1,1):
        z=.271+j*.032
        cube("Basket separated horizontal fibre band",(.538,-.024+side*.211,z),(.627,.026,.020),rattan_light if j%3==1 else rattan,"service",.003)
for j in range(13):
    x=.247+j*.047
    cube("Basket weave vertical front stitch",(x,-.242,.358),(.019,.021,.206),rattan_light if j%3==0 else rattan,"service",.003)
cube("Basket reinforced front rolled rim",(.538,-.239,.466),(.669,.037,.049),rattan_light,"service",.014)
cube("Basket reinforced rear rolled rim",(.538,.193,.466),(.669,.037,.049),rattan_light,"service",.014)
for x in (.206,.869):
    cube("Basket rolled side rim",(x,-.021,.465),(.039,.452,.044),rattan_light,"service",.013)
def aim(o, target):
    o.rotation_euler=(Vector(target)-o.location).to_track_quat("-Z","Y").to_euler()


cube("Studio floor",(0,0,-.029),(200,200,.045),material("Studio charcoal",(.042,.052,.053),.66),"studio")
bpy.ops.object.camera_add(location=(2.57,-6.10,2.78))
camera=attach(bpy.context.object,"Frontal three-quarter studio camera","studio")
aim(camera,(0,-.02,1.06))
camera.data.type="ORTHO";camera.data.ortho_scale=2.84
scene.camera=camera
for name,pos,energy,color,size in (
    ("Warm key",(2.9,-3.7,5.1),264,(1,.89,.73),2.45),
    ("Cool window fill",(-3.5,-4.0,2.7),175,(.70,.87,1),2.2),
    ("Top perimeter rim",(3,2.7,4.2),275,(.77,.93,1),2.5),
):
    bpy.ops.object.light_add(type="AREA",location=pos)
    o=attach(bpy.context.object,name,"studio")
    o.data.energy=energy;o.data.color=color;o.data.shape="DISK";o.data.size=size
    aim(o,(0,0,.94))
scene.world=bpy.data.worlds.new("Ambient studio")
scene.world.use_nodes=True
scene.world.node_tree.nodes["Background"].inputs[0].default_value=(.32,.38,.47,1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value=.32
scene.render.engine="CYCLES"
scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=720;scene.render.resolution_y=720
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.filepath=str(ROOT/"previews"/"studio.png")
scene.view_settings.view_transform="AgX"

# Every authoring part remains separate and editable in the saved project.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"festival-flower-garland-stall.blend"))
if "--skip-render" not in sys.argv:
    bpy.ops.render.render(write_still=True)

# Batch exported meshes by functional group and material. Keep glass separate
# so an engine can sort its transparency independently of the cabinet.
model_objects=[]
for name, coll in parts.items():
    if name=="studio":
        continue
    by=defaultdict(list)
    for o in list(coll.objects):
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active=o
        if o.type=="FONT" or o.modifiers:
            bpy.ops.object.convert(target="MESH")
            o=bpy.context.view_layer.objects.active
        if len(o.data.materials)>1:
            model_objects.append(o)
            continue
        by[o.data.materials[0].name].append(o)
    for mat, objects in sorted(by.items()):
        bpy.ops.object.select_all(action="DESELECT")
        for o in objects:
            o.select_set(True)
        active=objects[0]
        bpy.context.view_layer.objects.active=active
        if len(objects)>1:
            bpy.ops.object.join()
        active.name=coll.name[3:]+" | "+mat
        model_objects.append(active)
bpy.ops.object.select_all(action="DESELECT")
for o in model_objects:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/"exports"/"festival-flower-garland-stall.glb"),
                         export_format="GLB",use_selection=True,export_animations=False,
                         export_cameras=False,export_lights=False,export_texcoords=False)
