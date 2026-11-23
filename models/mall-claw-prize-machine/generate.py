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
    "case": "01 Shell and service hardware", "glass": "02 Glazing and light bars",
    "gantry": "03 X-Y gantry and cable reel", "claw": "04 Claw links and pivot hardware",
    "plush": "05 Original toy sculptures", "controls": "06 Joystick and buttons",
    "chute": "07 Prize drop and collection tunnel", "studio": "08 Studio only",
}.items():
    coll = bpy.data.collections.new(name)
    scene.collection.children.link(coll)
    parts[key] = coll

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


iris = material("Indigo violet structural enamel", (.14,.058,.43), .40)
ink = material("Deep amethyst shadow lining", (.029,.018,.075), .62)
lavender = material("Lilac molded fascias", (.50,.32,.82), .38)
cream = material("Vanilla powder coat", (.91,.76,.55), .46)
white = material("Warm paper legends", (.93,.87,.73), .58)
aqua = material("Seafoam accents", (.05,.66,.60), .44)
pink = material("Warm pink powder coat", (.85,.19,.39), .43)
opal = material("Frosted lilac light cores", (.69,.52,1), .28, 0, .9)
light = material("Cool white showcase diffusers", (.66,.91,1), .28, 0, 1.2)
glass = material("Anti-reflective clear acrylic", (.73,.89,1), .17, 0, 0, .052)
metal = material("Satin cast aluminum", (.61,.64,.71), .31, .68)
hardware = material("Graphite bolts and gaskets", (.045,.049,.073), .52, .15)
plum = material("Berry plush", (.66,.16,.39), .82)
sea = material("Lagoon plush", (.052,.44,.36), .88)
butter = material("Butter plush", (.94,.58,.15), .86)
snow = material("Cream plush", (.83,.72,.55), .86)
mauve = material("Heather plush", (.41,.23,.59), .86)
eyes = material("Charcoal embroidery", (.036,.021,.049), .88)
blush = material("Peach embroidery", (.98,.37,.31), .80)
felt = material("Lilac prize bed felt", (.28,.14,.46), .91)
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


def label(name,txt,x,z,y,size,mat=white,group="controls"):
    bpy.ops.object.text_add(location=(x,y,z),rotation=(math.pi/2,0,0))
    o = attach(bpy.context.object,name,group,mat)
    o.data.body=txt
    o.data.size=size
    o.data.align_x="CENTER"
    o.data.align_y="CENTER"
    o.data.resolution_u=3
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


def badge(name,x,z,y,r,mat,group="case"):
    ring=[(x+(r if i%2==0 else r*.46)*math.cos(i*math.pi/5+math.pi/2),
           z+(r if i%2==0 else r*.46)*math.sin(i*math.pi/5+math.pi/2)) for i in range(10)]
    profile(name,ring,y,.008,mat,group,.002)


def marquee_outline(x,z,w,h):
    return [(x+w*u,z+h*v) for u,v in
            [(-.5,-.31),(-.39,-.50),(.39,-.50),(.50,-.31),
             (.50,.21),(.36,.43),(.18,.50),(-.18,.50),(-.36,.43),(-.50,.21)]]


# Forward is -Y; the prize window is a volume, never a flat graphic.
cube("Molded pedestal",(0,-.014,.063),(1.14,.94,.126),iris,radius=.036)
for x in (-.47,.47):
    for y in (-.36,.34):
        cylinder("Recessed leveling foot",(x,y,.026),.049,.052,hardware,"case")
cube("Perimeter base bead",(0,-.012,.122),(1.148,.944,.035),lavender,radius=.014)
cube("Rear cabinet panel",(0,.377,.692),(1.10,.127,1.28),iris,radius=.04)
for x in (-.526,.526):
    cube("Lower molded side cheek",(x,-.035,.360),(.109,.841,.50),lavender,radius=.040)
    for y in (-.35,.328):
        cube("Window structural corner post",(x,y,1.288),(.091,.097,1.386),iris,radius=.036)
        cube("Color-matched post face bead",(x,y-.052,1.300),(.04,.022,1.25),lavender,radius=.012)
    cube("Side sill",(x,-.037,.701),(.10,.783,.102),iris,radius=.023)
    cube("Side head rail",(x,-.025,1.807),(.093,.804,.088),iris,radius=.027)
    # Keep both wings transparent so side inspection opens onto the gantry.
    cube("Side acrylic sheet",(x,-.016,1.265),(.009,.651,1.030),glass,"glass",0)
cube("Rear lilac interior liner",(0,.345,1.269),(1.01,.052,1.08),felt,"glass",.009)
for z in (.791,1.524):
    cube("Rear liner color break",(0,.309,z),(.94,.012,.013),lavender,"glass",.003)
for x in (-.38, .38):
    for z in (1.07,1.42,1.65):
        badge("Embossed rear star",x,z,.300,.052,lavender,"glass")
cube("Front window top header",(0,-.380,1.815),(1.04,.114,.146),cream,radius=.028)
cube("Front window base seal",(0,-.389,.713),(1.05,.082,.106),iris,radius=.024)
cube("Front acrylic viewing door",(0,-.387,1.272),(1.007,.011,1.04),glass,"glass",0)
for x in (-.506,.506):
    cube("Thin acrylic pillar gasket",(x,-.397,1.269),(.019,.012,1.054),hardware,"glass",.003)
for n in range(3):
    cube("Window door swing hinge",(.510,-.413,.846+n*.354),(.054,.035,.087),cream,"glass",.011)
cylinder("Showcase service lock",(-.491,-.415,.931),.022,.031,metal,"glass",side=True)
cube("Showcase head shelf",(0,-.028,1.858),(1.15,.874,.104),iris,radius=.035)
cube("Crown lightbox",(0,-.026,1.932),(1.079,.810,.123),lavender,radius=.040)
profile("Arched prize marquee housing",marquee_outline(0,1.968,1.053,.278),-.465,.128,iris,"case",.014)
profile("Marquee translucent face",marquee_outline(0,1.969,.959,.205),-.476,.02,cream,"case",.009)
for x in (-.40,.40):
    badge("Marquee star",x,1.976,-.490,.046,pink)
label("Top marquee sign","PRIZE   PAVILION",0,1.988,-.493,.084,iris,"case")
label("Small marquee legend","C L A W   S T U D I O",0,1.917,-.494,.023,iris,"case")

for x in (-.430,.430):
    cube("Tall side interior light diffuser",(x,-.332,1.276),(.018,.025,.971),light,"glass",.008)
cube("Front overhead light diffuser",(0,-.279,1.748),(.88,.031,.018),light,"glass",.007)
# Visible right-side molded inspection cover and real inset ventilation slats.
cube("Marquee lower shadow seam bead",(0,-.447,1.831),(.747,.033,.037),lavender,radius=.013)
for sign in (-1,1):
    surf=sign*.586
    cube("Lower side inspection panel",(surf,.097,.381),(.025,.433,.356),iris,radius=.026)
    cube("Lower inset side inspection panel",(surf+sign*.015,.103,.387),(.010,.365,.285),lavender,radius=.016)
    for y in (-.061,.263):
        for z in (.266,.505):
            bar("Inspection panel mounting screw",(surf+sign*.017,y,z),(surf+sign*.031,y,z),.011,metal,"case")
    for j in range(5):
        cube("Inspection panel recessed vent line",(surf+sign*.022,.107,.316+j*.029),(.012,.198,.012),ink,radius=.005)
    cube("Inspection panel asymmetrical color plate",(surf+sign*.023,.107,.466),(.011,.188,.022),aqua,radius=.005)
for x in (-.323,.323):
    for z in (.29,.33,.37,.41):
        cube("Rear service louver",(x,.452,z),(.248,.024,.016),ink,radius=.008)
for x in (-.46,.46):
    for z in (.202,.533):
        cylinder("Rear quarter turn screw",(x,.459,z),.015,.012,metal,"case",side=True)


# Gantry: independent front/back linear rails, lateral bridge, cable trolley.
for y in (-.240,.244):
    for z in (1.704,1.735):
        bar("Horizontal brushed gantry rail",(-.428,y,z),(.428,y,z),.011,metal,"gantry")
    for x in (-.435,.435):
        cube("Gantry fixed nylon mount",(x,y,1.721),(.059,.052,.066),hardware,"gantry",.010)
for x in (-.168,-.104):
    bar("Fore-aft carriage rail",(x,-.236,1.713),(x,.238,1.713),.011,metal,"gantry")
for y in (-.221,.226):
    cube("Bridge sliding bearing",(-.136,y,1.715),(.118,.065,.068),iris,"gantry",.011)
cx,cy=-.136,-.118
cube("Moving trolley housing",(cx,cy,1.699),(.149,.113,.072),hardware,"gantry",.012)
cube("Trolley safety label plate",(cx,cy-.058,1.699),(.114,.012,.024),cream,"gantry",.004)
bar("Cable reel axle",(cx-.046,cy,1.651),(cx+.046,cy,1.651),.023,metal,"gantry")
for x in (cx-.041,cx+.041):
    bar("Cable reel end flange",(x-.004,cy,1.651),(x+.004,cy,1.651),.034,iris,"gantry")
bar("Suspended cable braid",(cx,cy,1.643),(cx,cy,1.494),.008,hardware,"gantry")
cylinder("Cable strain relief",(cx,cy,1.496),.022,.041,metal,"gantry")
cylinder("Claw actuator cup",(cx,cy,1.446),.066,.091,iris,"claw",n=24)
cylinder("Claw lower sliding collar",(cx,cy,1.387),.052,.037,metal,"claw",n=24)
cylinder("Internal claw plunger end",(cx,cy,1.357),.038,.029,hardware,"claw",n=20)
for i in range(3):
    angle=math.pi/2+i*math.tau/3
    # Each finger has its own shoulder fork, link, tip, linkage and pivot hardware.
    radial=Vector((math.cos(angle),math.sin(angle),0))
    tangent=Vector((-math.sin(angle),math.cos(angle),0))
    def radial_point(radius,z):
        return Vector((cx,cy,z))+radial*radius
    def link(name,a,b,width,mat,bevel=.006):
        p,q=Vector(a),Vector(b);d=q-p
        o=cube(f"Finger {i+1} {name}",(p+q)*.5,(width,width,d.length+.011),mat,"claw",bevel)
        o.rotation_mode="QUATERNION";o.rotation_quaternion=d.to_track_quat("Z","Y")
    shoulder=radial_point(.070,1.405)
    elbow=radial_point(.141,1.321)
    knee=radial_point(.158,1.250)
    tip=radial_point(.100,1.193)
    link("fixed socket",radial_point(.036,1.415),shoulder,.047,iris)
    link("stamped upper link",shoulder,elbow,.032,metal)
    link("angled lower link",elbow,knee,.026,metal)
    link("rounded inward tip",knee,tip,.027,metal)
    link("rubber gripping pad",radial_point(.124,1.214),tip,.030,pink)
    p=radial_point(.039,1.361)
    bar(f"Finger {i+1} actuation strut",p,elbow,.009,hardware,"claw")
    for n, pivot in enumerate((shoulder,elbow)):
        bar(f"Finger {i+1} exposed pivot pin {n}",pivot-tangent*.026,pivot+tangent*.026,.014,hardware,"claw")
        for sign in (-1,1):
            cap=pivot+tangent*(sign*.029)
            bar(f"Finger {i+1} pivot cap {n}",cap-tangent*.003,cap+tangent*.003,.011,metal,"claw")


# Low felt bed has a real drop opening on the front right, clear of toys.
cube("Prize bed left section",(-.158,-.001,.698),(.714,.677,.042),felt,"chute",.015)
cube("Prize bed rear right section",(.361,.143,.698),(.307,.388,.042),felt,"chute",.015)
cube("Prize drop aperture left rim",(.213,-.215,.718),(.033,.308,.046),cream,"chute",.009)
cube("Prize drop aperture right rim",(.480,-.215,.718),(.033,.308,.046),cream,"chute",.009)
cube("Prize drop aperture rear rim",(.346,-.059,.718),(.268,.035,.046),cream,"chute",.009)
cube("Prize chute right interior",(.473,-.277,.476),(.044,.206,.459),ink,"chute",.010)
cube("Prize chute left interior",(.217,-.278,.476),(.044,.206,.459),ink,"chute",.010)
cube("Prize chute rear interior",(.345,-.145,.455),(.268,.059,.484),ink,"chute",.010)
cube("Prize chute padded floor",(.345,-.322,.276),(.276,.215,.058),felt,"chute",.015)
cube("Lower front service access panel",(-.165,-.397,.401),(.653,.087,.503),iris,radius=.035)
cube("Recessed service insert",(-.175,-.447,.387),(.552,.026,.320),lavender,radius=.032)
for x in (-.33,-.24,-.15):
    badge("Raised service medallion",x,.397,-.471,.033,cream)
profile("Cabinet lower decorative sweep",[(-.46,.258),(.093,.258),(.093,.286),(-.25,.314),(-.46,.352)],-.466,.012,aqua,"case",.006)
cylinder("Coin box service lock",(.035,-.467,.376),.021,.027,metal,"case",side=True)
cube("Collection opening top surround",(.348,-.419,.536),(.376,.088,.080),cream,"chute",.026)
cube("Collection opening threshold",(.348,-.432,.240),(.371,.107,.086),cream,"chute",.025)
for x in (.173,.523):
    cube("Collection opening upright",(x,-.420,.389),(.073,.083,.278),cream,"chute",.023)
flap=cube("Static inward swung bump flap",(.348,-.363,.487),(.288,.019,.137),iris,"chute",.012)
flap.rotation_euler.x=-.56
cube("Collection pull lip",(.348,-.493,.278),(.251,.030,.034),aqua,"chute",.010)
label("Pickup legend","PRIZE PICKUP",.348,.536,-.468,.029,ink,"chute")

# Controls are a projecting deck, above route-independent faux coin hardware.
deck=cube("Rounded joystick desk",(0,-.475,.672),(1.053,.248,.092),cream,"controls",.035)
deck.rotation_euler.x=.105
cube("Soft-purple front bumper",(0,-.591,.643),(1.014,.068,.092),lavender,"controls",.031)
cube("Joystick socket",(-.307,-.484,.722),(.195,.142,.025),iris,"controls",.021)
cylinder("Joystick black boot",(-.307,-.484,.747),.045,.037,hardware,"controls")
bar("Joystick shaft",(-.306,-.484,.749),(-.336,-.515,.817),.012,metal,"controls")
ball("Joystick sphere",(-.338,-.518,.831),(.046,.046,.046),pink,"controls")
for x,y in ((.318,-.491),(.149,-.505)):
    cylinder("Brushed pushbutton collar",(x,y,.724),.054,.022,metal,"controls",n=24)
    cylinder("Tinted deactivated pushbutton",(x,y,.742),.040,.026,aqua if x>.2 else pink,"controls",n=24)
cube("Opaque idle display face",(-.038,-.606,.655),(.153,.026,.052),ink,"controls",.011)
label("Idle panel lettering","READY",-.038,.655,-.622,.028,opal)
cube("Faux coin acceptor mount",(.035,-.461,.452),(.106,.04,.058),hardware,"controls",.010)
cube("Inert slot seam",(.036,-.486,.454),(.069,.009,.011),metal,"controls",.003)

def critter(label,x,y,floor,s,kind,mat):
    def ell(name,delta,scale,color=mat,tilt=0):
        dp=(x+delta[0]*s,y+delta[1]*s,floor+delta[2]*s)
        return ball(label+" "+name,dp,tuple(v*s for v in scale),color,"plush",tilt)
    ell("body",(0,0,.83),(.74,.58,.76))
    ell("cream belly",(0,-.505,.754),(.44,.118,.35),snow)
    for sign in (-1,1):
        ell("rounded foot",(sign*.44,-.20,.244),(.31,.43,.23))
        ell("small side arm",(sign*.67,-.045,.91),(.26,.40,.27),mat,-sign*.38)
    ell("head",(0,0,1.70),(.82,.68,.63))
    if kind=="rabbit":
        for sign in (-1,1):
            ell("long ear",(sign*.48,.073,2.36),(.19,.17,.56),mat,sign*.29)
            ell("long ear lining",(sign*.51,-.067,2.36),(.108,.062,.39),blush,sign*.29)
    elif kind=="cat":
        for sign in (-1,1):
            apex=x+s*sign*.61
            profile(label+" pointed ear",[(apex-.22*s,floor+s*2.03),(apex+.22*s,floor+s*2.03),(apex+s*sign*.16,floor+s*2.60)],y-.15*s,.37*s,mat,"plush",s*.09)
    elif kind=="bear":
        for sign in (-1,1):
            ell("rounded ear",(sign*.59,0,2.14),(.258,.21,.267))
            ell("round ear inset",(sign*.60,-.163,2.15),(.152,.071,.17),snow)
    else:
        ell("leaf sprout",(0,.015,2.31),(.16,.15,.29),sea,.50)
        ell("duck bill",(0,-.69,1.57),(.36,.18,.15),blush)
    for sign in (-1,1):
        ell("embroidered eye",(sign*.25,-.612,1.81),(.077,.056,.084),eyes)
        if kind!="duck":
            ell("cheek embroidery",(sign*.42,-.577,1.61),(.111,.045,.071),blush)
    if kind!="duck":
        ell("stitched nose",(0,-.665,1.628),(.083,.053,.060),eyes)

critter("Front mint rabbit",-.365,-.190,.712,.107,"rabbit",sea)
critter("Front peach cat",-.096,-.229,.712,.092,"cat",plum)
critter("Mid golden duck",.106,-.037,.712,.102,"duck",butter)
critter("Rear oatmeal bear",-.270,.059,.712,.114,"bear",snow)
critter("Rear lavender rabbit",-.027,.159,.712,.104,"rabbit",mauve)
critter("Rear yellow duck",.260,.204,.712,.112,"duck",butter)
for x,y,z in ((-.42,.133,.767),(.432,.117,.763),(.358,.270,.762),(-.145,.018,.756)):
    ball("Loose novelty capsule",(x,y,z),(.056,.056,.056),pink,"plush")
    edge=cylinder("Capsule seam",(x,y,z),.057,.012,cream,"plush")
    edge.rotation_euler.y=.35
def aim(o, target):
    o.rotation_euler=(Vector(target)-o.location).to_track_quat("-Z","Y").to_euler()


cube("Studio floor",(0,0,-.029),(200,200,.045),material("Studio charcoal",(.051,.044,.078),.66),"studio")
bpy.ops.object.camera_add(location=(3.16,-6.95,2.75))
camera=attach(bpy.context.object,"Frontal three-quarter studio camera","studio")
aim(camera,(0,-.07,1.06))
camera.data.type="ORTHO";camera.data.ortho_scale=2.52
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
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"mall-claw-prize-machine.blend"))
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
bpy.ops.export_scene.gltf(filepath=str(ROOT/"exports"/"mall-claw-prize-machine.glb"),
                         export_format="GLB",use_selection=True,export_animations=False,
                         export_cameras=False,export_lights=False,export_texcoords=False)
