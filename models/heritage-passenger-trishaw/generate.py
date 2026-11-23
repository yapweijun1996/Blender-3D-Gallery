import math
import sys
from collections import defaultdict
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
    "frame": "01 Cycle frame and rear dropouts", "steering": "02 Fork and steering controls",
    "wheels": "03 Three spoked wheels", "drive": "04 Crank chain and brakes",
    "cab": "05 Passenger sidecar and step", "seat": "06 Seat and stitched upholstery",
    "canopy": "07 Canvas canopy and support hoops", "detail": "08 Trim and equipment",
    "studio": "09 Studio only",
}.items():
    collection = bpy.data.collections.new(name)
    scene.collection.children.link(collection)
    parts[key] = collection


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
    if radius:
        bevel = o.modifiers.new("Powder-coated edge radius","BEVEL")
        bevel.width = radius
        bevel.segments = 2
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


def profile(name, points, left, thickness, mat, group, radius=.006):
    """Extrude a CCW X,Z polygon along Y (cabinet panels and signs)."""
    n=len(points)
    verts=[(x,y,z) for y in (left,left+thickness) for x,z in points]
    faces=[tuple(range(n)),tuple(reversed(range(n,n*2)))]
    faces.extend((i,i+n,(i+1)%n+n,(i+1)%n) for i in range(n))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh)
    parts[group].objects.link(o);o.data.materials.append(mat)
    if radius:
        bevel=o.modifiers.new("Soft molded edge","BEVEL")
        bevel.width=radius;bevel.segments=3;bevel.harden_normals=True
        o.modifiers.new("Weighted facets","WEIGHTED_NORMAL")
    return o


def ball(name,pos,scale,mat,group="plush",tilt=0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=1,location=pos)
    o=attach(bpy.context.object,name,group,mat);o.scale=scale;o.rotation_euler.y=tilt
    for p in o.data.polygons:
        p.use_smooth=True
    return o


def bar(name,a,b,r,mat,group,n=12):
    p,q=Vector(a),Vector(b);d=q-p
    o=cylinder(name,(p+q)*.5,r,d.length,mat,group,n=n)
    o.rotation_euler=d.to_track_quat("Z","Y").to_euler()
    return o



jade = material("Deep bottle green enamel", (.046,.28,.178), .47, .1)
gold = material("Aged warm brass", (.64,.389,.143), .31, .56)
silver = material("Brushed old nickel", (.52,.56,.59), .36, .70)
polish = material("Warm polished zinc", (.55,.50,.39), .28, .64)
rubber = material("Charcoal rubber tire", (.028,.032,.034), .72)
rubber_side = material("Amber cotton tire sidewall", (.44,.271,.119), .79)
tread = material("Raised rubber road tread", (.065,.069,.065), .81)
vinyl = material("Oxblood leather upholstery", (.365,.055,.051), .47)
wine = material("Oxblood screw-mounted wheel skirts", (.49,.075,.048), .45, .12)
stitch = material("Warm pillow piping and stitch thread", (.69,.403,.184), .69)
shadow = material("Lined floor and wheel shadow", (.049,.044,.034), .83)
wood = material("Warm oiled hardwood slats", (.40,.195,.077), .64)
wood_hi = material("Pale oiled hardwood end strip", (.47,.257,.115), .65)
tan = material("Sand woven canvas", (.77,.61,.375), .89)
canvas_green = material("Muted bottle green canvas stripe", (.065,.28,.16), .84)
canvas_edge = material("Dark canvas binding", (.043,.114,.075), .89)
paper = material("Worn cream decoration", (.83,.687,.463), .60)
lampglass = material("Warm opal headlamp lens", (.90,.80,.52), .31, 0, .28)
red = material("Rear red safety lens", (.60,.036,.026), .29)


def mesh_object(name,verts,faces,mat,group,soft=False):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);parts[group].objects.link(o)
    o.data.materials.append(mat)
    if soft:
        for p in mesh.polygons:
            p.use_smooth=True
    return o


def tube(name, points, radius, mat, group, sides=10, closed=False):
    points=[Vector(p) for p in points]
    n=len(points)
    verts=[]
    for i,p in enumerate(points):
        tangent=(points[(i+1)%n] if closed or i<n-1 else p)-(points[i-1] if closed or i else p)
        tangent.normalize()
        ref=Vector((1,0,0))
        if abs(ref.dot(tangent))>.95:
            ref=Vector((0,0,1))
        u=(ref-tangent*ref.dot(tangent)).normalized()
        v=tangent.cross(u)
        for j in range(sides):
            angle=j*math.tau/sides
            verts.append(tuple(p+radius*(u*math.cos(angle)+v*math.sin(angle))))
    faces=[]
    for i in range(n if closed else n-1):
        for j in range(sides):
            nxt=(i+1)%n
            faces.append((i*sides+j, i*sides+(j+1)%sides, nxt*sides+(j+1)%sides,nxt*sides+j))
    if not closed:
        faces.extend((tuple(reversed(range(sides))),tuple(range((n-1)*sides,n*sides))))
    return mesh_object(name,verts,faces,mat,group,True)


def ring_x(name,x,y,z,r,minor,mat,group,n=52,sides=9):
    return tube(name,[(x,y+r*math.cos(t*math.tau/n),z+r*math.sin(t*math.tau/n)) for t in range(n)],
                minor,mat,group,sides,True)


def rod_x(name,x,y,z,length,r,mat,group,n=16):
    return bar(name,(x-length/2,y,z),(x+length/2,y,z),r,mat,group,n)


def arch_x(name,x,y,z,r,radius,mat,group,start=31,end=158,axial=0):
    a,b=map(math.radians,(start,end))
    return tube(name,[(x+axial,y+r*math.cos(a+(b-a)*i/21),z+r*math.sin(a+(b-a)*i/21))
                      for i in range(22)],radius,mat,group,8)


def wheel(name,x,y,z,r):
    ring_x(name+" rounded outer tire",x,y,z,r-.035,.033,rubber,"wheels",56,10)
    for sign in (-1,1):
        ring_x(name+" warm sidewall",x+sign*.024,y,z,r-.036,.009,rubber_side,"wheels",48,7)
        ring_x(name+" rim flange",x+sign*.012,y,z,r-.072,.010,silver,"wheels",48,8)
    for i in range(24):
        a=i*math.tau/24
        p=(x+(.011 if i%2 else -.011),y+(r-.055)*math.cos(a),z+(r-.055)*math.sin(a))
        ph=a+(.34 if i%2 else -.34)
        q=(x+(.031 if i%2 else -.031),y+.046*math.cos(ph),z+.046*math.sin(ph))
        bar(name+" cross-laced spoke",q,p,.0031,silver,"wheels",7)
        o=cube(name+" raised tread sipe",(x,y+(r-.004)*math.cos(a),z+(r-.004)*math.sin(a)),(.023,.009,.014),tread,"wheels",.001)
        o.rotation_euler.x=a
    ax=rod_x(name+" barrel hub",x,y,z,.074,.045,silver,"wheels",20)
    for sign in (-1,1):
        rod_x(name+" inner hub cap",x+sign*.043,y,z,.014,.031,polish,"wheels")
        rod_x(name+" axle nut",x+sign*.061,y,z,.027,.019,polish,"wheels",8)
    return ax


# A sidecar layout: two inline bicycle wheels, plus an outboard passenger wheel.
bx=.378
front_y, rear_y, side_y = -.770, .690, .485
wheel("Front bicycle wheel",bx,front_y,.350,.350)
wheel("Rear bicycle wheel",bx,rear_y,.350,.350)
wheel("Outboard passenger wheel",-.974,side_y,.303,.303)

# The conventional frame's load paths meet the bottom bracket and head tube.
bottom=(bx,.110,.355); seat_joint=(bx,.335,.915)
head_low=(bx,-.559,.757); head_high=(bx,-.503,1.025)
drop_y=(bx,rear_y,.350)
bar("Brazed down tube",head_low,bottom,.040,jade,"frame",16)
bar("Brazed curved top rail",head_high,seat_joint,.035,jade,"frame",16)
bar("Seat tube",bottom,seat_joint,.036,jade,"frame",16)
bar("Head tube bearings",head_low,head_high,.054,jade,"frame",18)
for sign in (-1,1):
    x=bx+sign*.074
    tube("Rear chainstay",[(bx+sign*.030,.11,.355),(x,.315,.373),(x,.532,.364),(x,rear_y,.350)],.021,jade,"frame")
    tube("Rear seatstay",[(bx+sign*.025,.336,.914),(x,.466,.737),(x,.590,.479),(x,rear_y,.35)],.018,jade,"frame")
    rod_x("Rear bronze dropout plate",x,rear_y,.350,.030,.047,jade,"frame",14)
tube("Top brace arc",[(bx,-.505,.981),(bx,-.207,.887),(bx,.113,.844),(bx,.310,.840)],.019,jade,"frame")
bar("Tall nickel saddle post",seat_joint,(bx,.391,1.077),.022,silver,"frame")
saddle=cube("Historic sprung saddle nose",(bx,.346,1.081),(.112,.208,.041),vinyl,"seat",.025)
ball("Wide rider sprung saddle shoulder",(bx,.455,1.098),(.143,.124,.039),vinyl,"seat")
for x in (bx-.091,bx+.091):
    center=Vector((x,.492,1.046))
    tube("Rider saddle exposed coil spring", [tuple(center+Vector((.018*math.cos(t*.76),.018*math.sin(t*.76),-.034+t*.0024))) for t in range(29)],.004,polish,"seat",7)
bar("Head bearing bottom cup",(bx,-.570,.751),(bx,-.556,.787),.054,gold,"steering")
bar("Head bearing top cup",(bx,-.506,1.010),(bx,-.493,1.049),.054,gold,"steering")
tube("Steering stem quill",[(bx,-.505,1.021),(bx,-.462,1.148),(bx,-.516,1.186)],.025,silver,"steering")
for sign in (-1,1):
    x=bx+sign*.067
    tube("Curved fork blade",[(bx+sign*.035,-.551,.771),(x,-.612,.682),(x,-.683,.529),
                             (x,-.746,.407),(x,-.770,.350)],.026,silver,"steering")
    rod_x("Front dropout lug",x,front_y,.350,.018,.040,jade,"steering",12)
    tube("Swept nickel handlebar",[(bx,-.518,1.188),(bx+sign*.105,-.525,1.186),(bx+sign*.233,-.485,1.193),
                                  (bx+sign*.287,-.383,1.206),(bx+sign*.291,-.288,1.212)],.018,silver,"steering")
    bar("Sculpted brown handlebar grip",(bx+sign*.291,-.388,1.206),(bx+sign*.292,-.267,1.214),.028,wood,"steering",14)
    for j in range(6):
        y=-.372+j*.016
        bar("Handlebar grip knurl ridge",(bx+sign*.291,y,1.209),(bx+sign*.291,y+.004,1.209),.029,shadow,"steering",10)
    tube("Brake hand lever",[(bx+sign*.239,-.475,1.181),(bx+sign*.290,-.448,1.167),
                            (bx+sign*.335,-.366,1.173)],.011,silver,"steering",8)
cylinder("Round handlebar bell",(bx-.186,-.519,1.222),.032,.028,gold,"steering",n=18)
ball("Bell crown",(bx-.186,-.519,1.235),(.032,.032,.015),gold,"steering")
for x,y,z,r,side in ((bx,front_y,.350,.375,1),(bx,rear_y,.350,.375,-1),(-.974,side_y,.303,.329,1)):
    for offset in (-.039,0,.039):
        arch_x("Rolled mudguard longitudinal rib",x,y,z,r,.025 if offset==0 else .014,wine,"detail",
               start=18 if side>0 else 5,end=165 if side>0 else 150,axial=offset)
    for sign in (-1,1):
        tube("Mudguard support wire",[(x+sign*.05,y,.350),(x+sign*.064,y+r*.66,.350+r*.74)],.006,silver,"detail",7)
for profile_coords in ([(bx+.064,-.382,1.197),(bx+.023,-.633,1.11),(bx,-.646,.971),(bx,-.625,.733)],
                       [(bx-.066,-.434,1.182),(bx-.031,-.405,1.045),(bx-.076,.046,.876),(bx-.086,.56,.782),(bx,.646,.691)]):
    tube("Brake Bowden housing",profile_coords,.0065,shadow,"drive",7)
# Physical headlamp, rear reflector and fascia plaques; no electronics.
cylinder("Bicycle headlamp shell",(bx,-.638,.789),.055,.112,gold,"detail",side=True,n=26)
cylinder("Bicycle headlamp lens",(bx,-.700,.789),.049,.013,lampglass,"detail",side=True,n=26)
cylinder("Rear bicycle safety lens",(bx,.984,.482),.031,.026,red,"detail",side=True,n=18)


# Crank, pedal cage and closed chain path in the same outboard drive plane.
d_x=bx+.099; c_y=.110; c_z=.355; r_y=rear_y; r_z=.350
for x in (bx-.05,bx+.05):
    rod_x("Bottom bracket bearing",x,c_y,c_z,.036,.047,polish,"drive")
rod_x("Through crank shaft",bx,c_y,c_z,.285,.022,silver,"drive")
for yc,zc,r,n,label in ((c_y,c_z,.111,32,"Crank chainring"),(r_y,r_z,.054,16,"Rear freewheel sprocket")):
    rod_x(label+" backing plate",d_x,yc,zc,.017,r-.007,silver,"drive",n)
    for i in range(n):
        a=i*math.tau/n
        y=yc+r*math.cos(a);z=zc+r*math.sin(a)
        o=cube(label+" tooth",(d_x,y,z),(.022,.017,.014),polish,"drive",.003)
        o.rotation_euler.x=a
    for i in range(5):
        a=i*math.tau/5
        rod_x(label+" fastener",d_x+.015,yc+(r*.63)*math.cos(a),zc+(r*.63)*math.sin(a),.014,.010,gold,"drive",10)
path=[]
d=math.hypot(r_y-c_y,r_z-c_z);heading=math.atan2(r_z-c_z,r_y-c_y)
limit=math.acos((.113-.056)/d);a=heading+limit;b=heading-limit
for yc,zc,r,start,end in ((c_y,c_z,.113,a,b+math.tau),(r_y,r_z,.056,b,a)):
    for i in range(18):
        t=start+(end-start)*i/17
        path.append((d_x,yc+r*math.cos(t),zc+r*math.sin(t)))
tube("Closed roller-chain core",path,.009,shadow,"drive",8,True)
for p,q in zip(path,path[1:]+path[:1]):
    p,q=Vector(p),Vector(q);length=(q-p).length
    for i in range(max(1,round(length/.020))):
        pivot=p.lerp(q,i/max(1,round(length/.020)))
        rod_x("Exposed nickel chain pin",pivot.x,pivot.y,pivot.z,.024,.005,silver,"drive",7)
for sign in (-1,1):
    x=bx+sign*.113
    # Keep the down pedal above the road and stagger the paired crank throw by 180 degrees.
    y=c_y+sign*.130;z=c_z+sign*.090
    bar("Forged crank arm",(x,c_y,c_z),(x,y,z),.023,silver,"drive")
    rod_x("Pedal spindle",x+sign*.064,y,z,.127,.015,silver,"drive")
    for o in (-1,1):
        cube("Pedal rubber grip bar",(x+sign*.067,y+o*.038,z),(.114,.025,.025),shadow,"drive",.005)
    for o in (-1,1):
        cube("Pedal end cap",(x+sign*.067+o*.050,y,z),(.017,.094,.022),polish,"drive",.006)
for yc,zc in ((-.635,.721),(.644,.671)):
    for sign in (-1,1):
        bar("Rim brake caliper arm",(bx+sign*.011,yc,zc),(bx+sign*.046,yc-.008,zc-.051),.014,polish,"drive",8)
        cube("Rim brake shoe",(bx+sign*.032,yc-.010,zc-.055),(.021,.045,.021),shadow,"drive",.003)

# Welded sidecar subframe and low step housing sit clear of the third wheel.
for yc in (-.308,.524):
    x=-.482
    bar("Sidecar longitudinal lower flange",(x,yc,.263),(x,yc,.401),.025,jade,"cab")
    bar("Sidecar transverse attachment outrigger",(-.930,yc,.254),(bx-.023,yc,.318),.034,jade,"cab",16)
    rod_x("Sidecar attachment clamp",-.029,yc,.290,.094,.051,gold,"cab")
bar("Outboard sidecar axle bridge",(-.973,side_y,.303),(-.600,side_y,.303),.041,silver,"cab",14)
for x in (-.793,-.131):
    tube("Sidecar parallel chassis runner",[(x,-.556,.289),(x,-.367,.247),(x,.351,.236),
                                           (x,.632,.273),(x,.706,.319)],.027,jade,"cab")
cube("Elevated sidecar passenger floor",(-.470,.160,.394),(.750,.940,.095),shadow,"cab",.042)
cube("Rolled front external footrest step",(-.471,-.502,.294),(.624,.406,.071),jade,"cab",.033)
for i in range(8):
    x=-.735+i*.075
    cube("Front footrest anti-skid hardwood slat",(x,-.510,.335),(.056,.331,.026),wood if i%2 else wood_hi,"cab",.007)
for x in (-.790,-.153):
    profile("Front stepped steel skirt",
            [(x-.035,.296),(x+.035,.296),(x+.035,.421),(x-.035,.450)],-.327,.139,jade,"cab",.009)

# Panel shoulders are curved in profile, with a wave-shaped top around the side aperture.
outline=[(-.402,.402),(-.365,.468),(-.155,.536),(.025,.635),(.258,.698),
         (.570,.703),(.677,.619),(.683,.412),(.587,.337),(-.309,.348)]
for x in (-.848,-.091):
    verts=[(x+offset,y,z) for offset in (-.028,.028) for y,z in outline]
    n=len(outline)
    faces=[tuple(range(n)),tuple(reversed(range(n,n*2)))]
    faces.extend((i,i+n,n+(i+1)%n,(i+1)%n) for i in range(n))
    panel=mesh_object("Rolled sidecar side skin",verts,faces,jade,"cab")
    normal=panel.modifiers.new("Face-weighted normals","WEIGHTED_NORMAL")
    lip=[(x,y,z+.01) for y,z in outline[:8]]
    tube("Sidecar upper curled rim",lip,.020,gold,"cab",10)
    for offset in (0,.048):
        tube("Painted curved side pinline",[(x+(-.031 if x<-.4 else .031),y,z-.096-offset) for y,z in outline[1:8]],.006,paper,"detail",8)
    for y in (-.211,.032,.313,.548):
        rod_x("Body brass rivet",x+(-.035 if x<-.4 else .035),y,.449,.016,.010,gold,"detail",9)
cube("Raised bolted rear wall",(-.474,.639,.585),(.780,.139,.504),jade,"cab",.057)
cube("Rear protective rub rail",(-.474,.713,.454),(.785,.051,.056),polish,"cab",.021)
cube("Sidecar rear red lens mount",(-.713,.722,.641),(.099,.026,.055),gold,"detail",.010)
cube("Sidecar rear safety reflector",(-.713,.737,.642),(.075,.015,.039),red,"detail",.009)
for x in (-.760,-.186):
    tube("Passenger curved entry grab rail",[(x,-.316,.494),(x,-.323,.563),(x,-.280,.670),
                                           (x,-.196,.742),(x,-.127,.727)],.019,polish,"cab")
    cube("Seat mounting bracket",(x,.319,.493),(.058,.407,.101),jade,"seat",.011)

# The cushion and separate curved back have real padded seams and stitch impressions.
cube("Bench seat cushion thick roll",(-.471,.310,.562),(.684,.433,.147),vinyl,"seat",.051)
cube("Bench front leather bolster",(-.471,.102,.580),(.690,.071,.086),vinyl,"seat",.028)
for x in (-.635,-.306):
    tube("Seat cushion parallel quilt seam",[(x,.115,.601),(x,.178,.636),(x,.300,.640),(x,.444,.642)],.006,stitch,"seat",7)
tube("Bench perimeter lower piping",[(-.793,.133,.592),(-.724,.093,.597),(-.217,.093,.596),(-.156,.153,.591),
                                    (-.148,.453,.589),(-.214,.504,.598),(-.725,.504,.598),(-.790,.456,.590)],
     .011,stitch,"seat",8,True)
seat= cube("Reclined padded passenger back",(-.471,.562,.790),(.681,.131,.491),vinyl,"seat",.061)
seat.rotation_euler.x=-.112
for x in (-.704,-.475,-.244):
    tube("Upholstered backrest stitched seam",[(x,.509,.616),(x,.497,.770),(x,.514,.895),(x,.547,.994)],.006,stitch,"seat",7)
    for j in range(4):
        z=.68+j*.078
        cylinder("Backrest inset traditional tuft",(x,.491,z),.016,.011,vinyl,"seat",side=True,n=12)

# A lightly crowned stretched striped fabric canopy. The rear hoop is taller than
# the entry lip and each rail meets a visible articulated mounting bracket.
def roof(x,y):
    t=(x+.481)/.433
    h=1.776-.267*t*t
    q=(y-.094)/.622
    return h-.100*q*q+.015*q

xs=[-.925+i*(.889/15) for i in range(16)]
ys=[-.489+i*(1.199/12) for i in range(13)]
for i in range(len(xs)-1):
    x0,x1=xs[i:i+2]
    verts=[(x,y,roof(x,y)) for y in ys for x in (x0,x1)]
    faces=[(2*j,2*j+1,2*j+3,2*j+2) for j in range(len(ys)-1)]
    cover=mesh_object("Stretched canvas roof stripe",verts,faces,canvas_green if i%3==1 else tan,"canopy",True)
    sol=cover.modifiers.new("Canvas thickness","SOLIDIFY");sol.thickness=.004
for y in (ys[0]+.004,ys[-1]-.004):
    tube("Canopy shaped upper binding",[(x,y,roof(x,y)+.002) for x in xs],.012,canvas_edge,"canopy",8)
    verts=[(x,y,roof(x,y)-drop) for x in xs for drop in (0,.067)]
    faces=[(2*i,2*i+2,2*i+3,2*i+1) for i in range(len(xs)-1)]
    skirt=mesh_object("Canvas front and rear drop valance",verts,faces,tan,"canopy")
    sol=skirt.modifiers.new("Canvas thickness","SOLIDIFY");sol.thickness=.005
    tube("Bound valance hem",[(x,y,roof(x,y)-.067) for x in xs],.007,canvas_edge,"canopy",8)
for x in (xs[0],xs[-1]):
    tube("Canopy longitudinal reinforced seam",[(x,y,roof(x,y)-.003) for y in ys],.011,canvas_edge,"canopy",8)
    for y,base in ((-.376,.322),(.568,.597)):
        z0=.570 if y<0 else .725
        tube("Canopy sprung upright mounting arm",[(x+(0.064 if x<-.4 else -.062),base,z0),
              (x+(0.02 if x<-.4 else -.021),base-.002,1.185),(x,y,roof(x,y)-.032)],.020,silver,"canopy")
        rod_x("Folding canopy support rivet",x+(0.063 if x<-.4 else -.059),base,z0,.029,.023,gold,"canopy",14)
for y in (-.377,.133,.566):
    tube("Three continuous bowed canopy ribs",[(x,y,roof(x,y)-.029) for x in xs],.017,polish,"canopy",8)
def aim(o, target):
    o.rotation_euler=(Vector(target)-o.location).to_track_quat("-Z","Y").to_euler()


cube("Studio floor",(0,0,-.029),(200,200,.045),material("Studio charcoal",(.042,.052,.053),.66),"studio")
bpy.ops.object.camera_add(location=(-4.55,-6.70,3.14))
camera=attach(bpy.context.object,"Frontal three-quarter studio camera","studio")
aim(camera,(-.12,-.01,.91))
camera.data.type="ORTHO";camera.data.ortho_scale=3.00
scene.camera=camera
for name,pos,energy,color,size in (
    ("Warm key",(2.9,-3.7,5.1),480,(1,.89,.73),3.0),
    ("Cool window fill",(-3.5,-4.0,2.7),334,(.70,.87,1),3.2),
    ("Top perimeter rim",(3,2.7,4.2),520,(.77,.93,1),2.1),
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
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"heritage-passenger-trishaw.blend"))
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
bpy.ops.export_scene.gltf(filepath=str(ROOT/"exports"/"heritage-passenger-trishaw.glb"),
                         export_format="GLB",use_selection=True,export_animations=False,
                         export_cameras=False,export_lights=False,export_texcoords=False)
