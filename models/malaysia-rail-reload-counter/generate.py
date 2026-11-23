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
    "shell":"01 Modular station counter and customer shelf",
    "sign":"02 Bilingual unbranded signage",
    "window":"03 Glazed opening and receipt slot",
    "staff":"04 Staff-side blank terminal and joinery",
    "reader":"05 Fictional static reader and sample tray",
    "motion":"06 Animated sample card and reader acknowledgement",
    "studio":"07 Studio only",
}.items():
    c=bpy.data.collections.new(name);scene.collection.children.link(c);parts[key]=c
scene.render.fps=24
scene.frame_start=0
scene.frame_end=48


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
    if radius > .006:
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



green=material("Petrol green baked enamel",(.038,.219,.181),.47,.14)
ink=material("Dark evergreen frame and gaskets",(.024,.065,.059),.55,.11)
jade=material("Mineral sage facade tile",(.26,.42,.35),.55)
cream=material("Warm polished limestone and sign insert",(.80,.72,.57),.47)
grey=material("Neutral stone lower slab",(.43,.45,.41),.69)
silver=material("Brushed bronze-grey counter hardware",(.50,.46,.40),.36,.56)
dark=material("Graphite dark monitor and slot recess",(.024,.036,.043),.54)
window=material("Low-reflectance window acrylic",(.64,.84,.83),.15,0,0,.078)
cedar=material("Dull copper accent face",(.52,.238,.12),.46,.24)
paper=material("Blank stock paper and faux card print",(.90,.84,.65),.64)
sample=material("Illustrative amber sample card",(.95,.55,.068),.49)
screen=material("Unlit staff monitor face",(.028,.059,.062),.36)
lit=material("Fictional mint acknowledgement bar",(.10,1.0,.37),.27,0,1.45)


def writing(name,data,pos,size,mat,group,flat=False):
    bpy.ops.object.text_add(location=pos,rotation=(0,0,0) if flat else (math.pi/2,0,0))
    o=attach(bpy.context.object,name,group,mat)
    o.data.body=data;o.data.align_x="CENTER";o.data.align_y="CENTER"
    o.data.size=size;o.data.resolution_u=2;o.data.space_character=1.02
    return o


# A single station bay rather than a rail gate, kiosk or separate payments machine.
cube("Continuous customer-service floor mounting plinth",(0,.031,.062),(2.274,1.064,.124),ink,"shell",.022)
cube("Base stone wear edge",(0,-.487,.108),(2.198,.056,.047),grey,"shell",.007)
cube("Left removable side enclosure",(-1.06,.059,.556),(.129,.973,.940),green,"shell",.018)
cube("Right removable side enclosure",(1.061,.066,.561),(.128,.981,.942),green,"shell",.018)
cube("Stiff full width valance base",(0,-.285,.507),(2.012,.145,.748),jade,"shell",.017)
cube("Inset architectural lower facade",(0,-.361,.470),(1.860,.021,.533),cream,"shell",.012)
for x in (-.74,-.29,.15,.60):
    cube("Segmentation seam in facade stone",(x,-.376,.459),(.009,.007,.458),silver,"shell",0)
cube("Bottom plinth ventilation rail",(0,-.371,.203),(1.982,.030,.133),green,"shell",.009)
for i in range(13):
    cube("Shallow perforation slot emboss",(-.911+i*.152,-.388,.198),(.094,.006,.021),ink,"shell",0)
cube("Waist-high service ledge",(0,-.008,.864),(2.195,.971,.067),grey,"shell",.025)
cube("Low projecting traveler shelf",(0,-.400,.883),(2.155,.460,.050),cream,"shell",.016)
cube("Narrow copper front shelf inlay",(0,-.607,.866),(2.115,.025,.029),cedar,"shell",.006)
cube("Staff-side underside rack shelf",(-.451,.267,.451),(.952,.412,.041),green,"staff",.008)
cube("Rear staff storage flat cupboard",(1.02,.286,.428),(.137,.401,.646),jade,"staff",.015)
for x in (-.760,-.304):
    cube("Staff pull-out plain supply drawer face",(x,.484,.675),(.379,.044,.149),cream,"staff",.012)
    cube("Brushed drawer finger grip",(x,.509,.688),(.142,.018,.022),silver,"staff",.005)
cube("Between zones sensible service desk partition",(-.015,.279,.503),(.069,.392,.699),green,"staff",.008)

# Customer-facing continuous window trim and a true low handover opening.
for x in (-1.063,1.063):
    cube("Staffed window vertical powder-coated jamb",(x,-.038,1.455),(.128,.115,1.233),green,"window",.016)
    cube("Narrow rear station frame upright",(x,.514,1.388),(.079,.081,1.121),ink,"staff",.007)
    cube("Continuous clear side return glazing",(x,-.012+.259,1.382),(.010,.459,.750),window,"window",0)
cube("Main header longitudinal welded crossmember",(0,-.027,1.841),(2.185,.139,.141),green,"window",.015)
cube("Amber bronze edge on under-header fascia",(0,-.106,1.773),(2.025,.026,.041),cedar,"window",.008)
cube("Low hold-back metal glazing sill",(0,-.029,1.142),(1.992,.083,.047),silver,"window",.008)
for x in (-.948,.947):
    cube("Outer vertical dark window gasket",(x,-.027,1.485),(.019,.035,.675),ink,"window",0)
for x in (-.495,.498):
    cube("Upper lapped translucent service glazing",(x,-.019,1.478),(.960,.011,.657),window,"window",0)
cube("Subtle center glazing mullion",(0,-.018,1.470),(.045,.043,.711),green,"window",.007)
for x,w in ((-.765,.403),(.747,.425)):
    cube("Under-glass fixed kick panel",(x,-.031,1.030),(w,.046,.223),jade,"window",.008)
# Front and rear openings are actually unobstructed through the center.
cube("Wide transaction transfer tray floor",(-.159,-.194,.927),(.385,.239,.027),silver,"window",.009)
cube("Low transfer tray dark liner",(-.159,-.195,.942),(.326,.198,.006),dark,"window",0)
for x in (-.339,.021):
    cube("Raised tray side retainer",(x,-.193,.948),(.027,.218,.036),silver,"window",.006)
cube("Brittle receipt opening outer metallic bevel",(-.443,-.407,.751),(.382,.063,.087),silver,"window",.012)
cube("Wide recessed receipt mouth",(-.443,-.444,.749),(.318,.019,.033),dark,"window",.006)
cube("Small unprinted document tongue",(-.444,-.460,.747),(.200,.041,.003),paper,"window",0)

# Neutral bilingual wording; no agency signing system, fare or route.
cube("Rear-bolted bilingual header plaque",(0,-.047,1.991),(2.038,.154,.294),ink,"sign",.024)
cube("Warm white insert for header lettering",(0,-.130,1.995),(1.916,.032,.227),cream,"sign",.012)
cube("Bottom accent strip on bilingual sign",(0,-.149,1.899),(1.839,.013,.023),cedar,"sign",.005)
writing("Malay customer service title","KHIDMAT PELANGGAN",(0,-.150,2.040),.108,green,"sign")
writing("English customer service subheading","CUSTOMER SERVICE",(0,-.151,1.943),.064,green,"sign")
cube("Reader plaque block mounted to fascia",(.638,-.433,.710),(.366,.130,.070),ink,"sign",.010)
cube("Reader bilingual wall-facing plaque",(.638,-.499,.703),(.476,.030,.137),green,"sign",.011)
writing("Malay reload title","TAMBAH NILAI",(.638,-.516,.731),.047,cream,"sign")
writing("English reload subheading","RELOAD",(.637,-.516,.677),.038,cream,"sign")
# Staff terminal has a deliberately blank screen and unlabeled soft keyboard.
cube("Staff terminal nonslip foot",(-.560,.303,.925),(.247,.166,.041),dark,"staff",.013)
cube("Monitor upright stand",(-.557,.306,1.020),(.072,.071,.170),green,"staff",.009)
m=cube("Blank staff monitor monitor case",(-.555,.300,1.199),(.435,.081,.296),dark,"staff",.019)
m.rotation_euler.x=.14
m=cube("Unilluminated staff display glass",(-.555,.344,1.198),(.386,.017,.250),screen,"staff",.007)
m.rotation_euler.x=.14
cube("Rear terminal vertical cable outlet",(-.554,.261,1.048),(.042,.017,.099),dark,"staff",.003)
cube("Low staff keyboard blank chassis",(-.619,.436,.920),(.305,.140,.047),ink,"staff",.010)
for i in range(4):
    cube("Blank keyboard horizontal emboss",(-.622,.393+i*.027,.946),(.261,.016,.004),grey,"staff",0)
cube("Staff station dark receipt-printer box",(.155,.339,.982),(.219,.207,.155),dark,"staff",.011)
cube("Unmarked printer lid lip",(.155,.236,1.038),(.178,.023,.025),silver,"staff",.004)


# Fictional local model only. It has no NFC, data, fare or payment logic.
cube("Passenger reader lower wedge model",(.571,-.407,.925),(.383,.297,.067),green,"reader",.017)
cube("Passenger reader upper dark contact surround",(.566,-.413,.962),(.370,.286,.032),dark,"reader",.021)
cube("Flat sample tap surface",(.522,-.434,.981),(.213,.200,.009),jade,"reader",.008)
for dx in (-1,1):
    cube("Sample pad geometrical texture line",(.522+dx*.086,-.433,.986),(.005,.145,.002),grey,"reader",0)
cube("Raised fictional reader indicator island",(.696,-.433,.981),(.065,.139,.010),ink,"reader",.008)
cube("Indicator physical cream surround",(.696,-.433,.988),(.040,.073,.005),silver,"reader",.002)
cube("Idle dark nonfunctional indicator",(.696,-.433,.991),(.028,.061,.006),dark,"reader",.002)
cube("Shelf card rest shallow bottom",(.197,-.451,.911),(.152,.113,.011),ink,"reader",.006)
cube("Shelf card rest outline left",(.120,-.451,.918),(.010,.101,.011),silver,"reader",0)
cube("Shelf card rest front locator",(.197,-.505,.917),(.127,.011,.008),silver,"reader",0)

body=cube("Unbranded amber sample card blank",(0,0,0),(.115,.074,.0044),sample,"motion",.005)
stripe=cube("Plain optical lane on sample card",(0,-.025,.0024),(.110,.013,.001),cream,"motion",0)
marker=cube("Sample card short non-electronic print",(-.031,.017,.0028),(.013,.006,.001),green,"motion",0)
label=writing("Visible sample-only label","DEMO",(.007,.008,.0028),.020,dark,"motion",flat=True)
bpy.ops.object.select_all(action="DESELECT");label.select_set(True)
bpy.context.view_layer.objects.active=label
bpy.ops.object.convert(target="MESH")
label=bpy.context.view_layer.objects.active
bpy.ops.object.select_all(action="DESELECT")
for o in (body,stripe,marker,label):o.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.object.join()
card=bpy.context.view_layer.objects.active;card.name="RAIL_DEMO_CARD"
indicator=cube("RAIL_READER_INDICATOR",(0,0,0),(.025,.054,.003),lit,"motion",.003)


def schedule(obj,keyset):
    for f,xyz,rot in keyset:
        obj.location=xyz;obj.rotation_euler=rot
        obj.keyframe_insert(data_path="location",frame=f,group="Fictional sample interaction")
        obj.keyframe_insert(data_path="rotation_euler",frame=f,group="Fictional sample interaction")
    a=obj.animation_data.action;a.name=obj.name+"_source_animation"
    n=obj.animation_data.nla_tracks.new();n.name="RAIL_CARD_TAP"
    n.strips.new("Authored 2 second sample motion",0,a)
    obj.animation_data.action=None


rest=(.198,-.450,.921);rest_rot=(0,0,.071)
end=(.522,-.437,.993);end_rot=(0,0,-.037)
schedule(card,[
    (0,rest,rest_rot),(6,rest,rest_rot),
    (13,(.258,-.494,1.019),(.176,-.195,.014)),
    (21,(.405,-.445,1.083),(.114,-.108,-.017)),
    (29,(.511,-.433,1.035),(.069,.003,-.032)),
    (34,end,end_rot),(48,end,end_rot),
])
hidden=(.696,-.433,.983);visible=(.696,-.433,.9965)
schedule(indicator,[(0,hidden,(0,0,0)),(33,hidden,(0,0,0)),(36,visible,(0,0,0)),(48,visible,(0,0,0))])
def aim(o, target):
    o.rotation_euler=(Vector(target)-o.location).to_track_quat("-Z","Y").to_euler()


cube("Studio floor",(0,0,-.029),(200,200,.045),material("Studio charcoal",(.042,.052,.053),.66),"studio")
bpy.ops.object.camera_add(location=(2.65,-5.68,3.23))
camera=attach(bpy.context.object,"Frontal three-quarter studio camera","studio")
aim(camera,(0,-.08,1.04))
camera.data.type="ORTHO";camera.data.ortho_scale=3.07
scene.camera=camera
for name,pos,energy,color,size in (
    ("Warm key",(2.9,-3.7,5.1),395,(1,.89,.73),3.0),
    ("Cool window fill",(-3.5,-4.0,2.7),270,(.70,.87,1),3.0),
    ("Top perimeter rim",(3,2.7,4.2),408,(.77,.93,1),2.8),
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

scene.frame_set(0)
# Every authoring part remains separate and editable in the saved project.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"malaysia-rail-reload-counter.blend"))
if "--skip-render" not in sys.argv:
    bpy.ops.render.render(write_still=True)
    if "--tap-review" in sys.argv:
        camera.location=(1.18,-2.7,1.92)
        aim(camera,(.48,-.399,.980))
        camera.data.ortho_scale=.58
        scene.render.filepath=str(ROOT/"previews"/"reader-ready.png")
        bpy.ops.render.render(write_still=True)
        scene.frame_set(48)
        scene.render.filepath=str(ROOT/"previews"/"reader-acknowledged.png")
        bpy.ops.render.render(write_still=True)
        scene.frame_set(0)

# Batch exported meshes by functional group and material. Keep glass separate
# so an engine can sort its transparency independently of the cabinet.
model_objects=[]
for name, coll in parts.items():
    if name=="studio":
        continue
    if name=="motion":
        model_objects.extend(coll.objects)
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
bpy.ops.export_scene.gltf(filepath=str(ROOT/"exports"/"malaysia-rail-reload-counter.glb"),
                         export_format="GLB",use_selection=True,export_animations=True,
                         export_animation_mode="NLA_TRACKS",export_force_sampling=True,
                         export_cameras=False,export_lights=False,export_texcoords=False)
