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
    "case": "01 Cabinet and service panels", "display": "02 Product window and shelving",
    "products": "03 Unbranded products", "controls": "04 Selection panel",
    "pickup": "05 Recessed pickup chute", "studio": "06 Studio only",
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


sand = material("Warm ivory powder coat", (.70,.61,.43), .39)
enamel = material("Petrol blue enamel", (.026,.15,.16), .41)
trim = material("Graphite gaskets and controls", (.020,.032,.036), .45)
interior = material("Refrigerated charcoal interior", (.027,.041,.046), .65)
darkness = material("Recess shadow lining", (.006,.009,.010), .8)
metal = material("Brushed stainless", (.53,.57,.61), .32,.65)
white = material("Matte white typography", (.90,.89,.77), .57)
lime = material("Backlit selection and display", (.42,.87,.66), .4, 0, .49)
amber = material("Burnt orange powder coat", (.84,.225,.073), .40)
light = material("Opal LED diffuser", (.70,.90,1), .25, 0, 1.35)
glass = material("Clear protective glazing", (.79,.97,1), .14, 0, 0, .085)
reflection = material("Soft glass edge highlight", (.72,.94,1), .27, 0, 0, .27)

flavors = [
    ("LIME", material("Lime product wrap", (.22,.66,.28)), material("Lime band", (.78,.94,.31))),
    ("PEACH", material("Peach product wrap", (.96,.43,.25)), material("Peach band", (1,.68,.42))),
    ("SODA", material("Soda product wrap", (.09,.53,.85)), material("Soda band", (.46,.87,.99))),
    ("TEA", material("Tea product wrap", (.67,.34,.16)), material("Tea band", (.91,.72,.34))),
    ("BERRY", material("Berry product wrap", (.6,.17,.42)), material("Berry band", (.95,.52,.65))),
]


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


# Main shell uses wall sections rather than a face-covering block; the
# showcase and pickup aperture are actually recessed in the cabinet.
cube("Rear chassis",(0,.332,1.02),(1.19,.103,1.96),enamel)
for x in (-.585,.585):
    cube("Full-height ivory cabinet side",(x,-.001,1.02),(.090,.742,1.96),sand,radius=.014)
cube("Rounded cabinet roof",(0,0,1.996),(1.254,.779,.105),sand,radius=.025)
cube("Recessed steel plinth",(0,.005,.110),(1.18,.735,.185),enamel,radius=.012)
for x in (-.50,.50):
    for y in (-.26,.26):
        cube("Adjustable rubber foot",(x,y,.023),(.12,.13,.046),trim,radius=.008)
cube("Front door broad crossmember",(0,-.352,.534),(1.16,.090,.165),enamel)
cube("Rounded upper marquee",(0,-.376,1.887),(1.165,.106,.139),enamel,radius=.020)
cube("Marquee orange accent",(0,-.432,1.819),(1.119,.010,.010),amber,radius=.002)
label("Main heading","COLD DRINKS",0,1.895,-.432,.083,white,"case")
label("Machine type","CHILLED BEVERAGES",0,1.847,-.436,.020,lime,"case")
for x in (-.56,.24):
    cube("Window seal vertical",(x,-.394,1.218),(.049,.088,1.115),trim,"display")
for z in (.663,1.770):
    cube("Window seal horizontal",(-.16,-.394,z),(.848,.087,.051),trim,"display")
cube("Product bay rear panel",(-.16,.158,1.22),(.786,.028,1.103),interior,"display")
cube("Product bay right wall",(.22,-.087,1.22),(.027,.435,1.105),interior,"display")
cube("Product bay left wall",(-.54,-.087,1.22),(.027,.435,1.105),interior,"display")
cube("Window safety glazing",(-.16,-.413,1.216),(.749,.004,1.051),glass,"display",0)
for x in (-.52,.205):
    cube("Inner vertical LED strip",(x,-.316,1.215),(.010,.014,1.033),light,"display",.001)
for x,w in ((-.518,.008),(.197,.005)):
    cube("Window soft reflection",(x,-.419,1.24),(w,.002,.98),reflection,"display",0)

# Twenty front facings and twenty reserve cans, across four ledged shelves.
for row,z in enumerate((.750,1.000,1.250,1.500)):
    cube(f"Ribbed tray {row+1}",(-.16,-.084,z),(.745,.447,.036),metal,"display")
    cube("Dark shelf label rail",(-.16,-.320,z+.006),(.741,.025,.049),trim,"display",.004)
    for col,x in enumerate((-.445,-.304,-.163,-.022,.119)):
        flavor,wrap,band=flavors[(col+2*row)%len(flavors)]
        base=z+.019
        for behind in (False, True):
            y=-.240 if not behind else -.092
            tag=f"{row+1}{col+1} {flavor}"
            cylinder(tag+" aluminum body",(x,y,base+.080),.045,.154,wrap,"products")
            cylinder(tag+" foot rim",(x,y,base+.008),.046,.009,metal,"products")
            cylinder(tag+" rolled upper rim",(x,y,base+.159),.047,.009,metal,"products")
            cylinder(tag+" product wrap band",(x,y,base+.062),.0455,.027,band,"products")
            cube(tag+" stamped pull tab",(x,y-.011,base+.165),(.020,.030,.004),metal,"products",.001)
            if not behind:
                label(tag+" front label",flavor,x,base+.094,y-.046,.016,white,"products")
        label("Selection marker",f"{chr(65+row)}{col+1}",x,z+.014,-.334,.018,white,"display")
        cube("Tray lane wire divider",(x+.060,-.106,z+.043),(.005,.313,.006),metal,"display",.001)

# Control box, display, selection membrane, and inert reader-shaped details.
cube("Right door panel",(.409,-.373,1.208),(.297,.106,1.13),enamel,"controls",.018)
cube("Display rubber inset",(.406,-.434,1.632),(.232,.025,.126),trim,"controls",.011)
cube("LCD smoked glass",(.406,-.449,1.634),(.200,.008,.082),interior,"controls",.008)
label("Idle screen","SELECT ITEM",.407,1.637,-.455,.026,lime)
label("Panel serial label","A—D / 1—5",.407,1.577,-.449,.019,white)
for row,line in enumerate(("ABC","D12","345","×✓")):
    for col,char in enumerate(line):
        x=.342+col*.062; z=1.497-row*.057
        cube("Selection key "+char,(x,-.446,z),(.044,.023,.042),sand if char not in "×✓" else amber,"controls",.006)
        # Built-in Blender font has wider Latin coverage than symbolic glyphs.
        label("Key legend",{"×":"X","✓":"OK"}.get(char,char),x,z,-.460,.019,trim)
cube("Generic reader bezel",(.404,-.435,1.154),(.224,.032,.138),trim,"controls",.012)
cube("Inert contact pad",(.401,-.453,1.162),(.147,.011,.077),interior,"controls",.008)
for ix in range(3):
    cube("Reader etched bar",(.401,-.460,1.158+ix*.011),(.028+ix*.012,.003,.003),metal,"controls",.001)
cylinder("Reader green status light",(.481,-.459,1.181),.009,.004,lime,"controls",True)
cube("Mechanical return slot surround",(.412,-.434,.986),(.169,.023,.071),trim,"controls",.006)
cube("Return slot brush shadow",(.400,-.447,.985),(.121,.006,.021),darkness,"controls",.003)
label("Return legend","RETURN",.407,1.034,-.435,.019,white)
cylinder("Recessed service cylinder",(.415,-.432,.803),.031,.012,metal,"controls",True)
cube("Lock keyway",(.415,-.439,.803),(.015,.003,.004),darkness,"controls",.001)

# Real aperture and set-back flap; the front lip surrounds rather than covers it.
for x in (-.512,.500):
    cube("Pickup side upright",(x,-.341,.344),(.148,.111,.286),enamel,"pickup",.012)
for z in (.189,.491):
    cube("Pickup surround beam",(0,-.380,z),(1.105,.087,.050),enamel,"pickup",.008)
cube("Pickup back wall",(0,-.153,.343),(.909,.019,.285),darkness,"pickup",.004)
cube("Pickup floor plate",(0,-.256,.210),(.904,.237,.021),metal,"pickup",.009)
cube("Set-back chute flap",(0,-.197,.351),(.869,.026,.200),trim,"pickup",.012)
for x in (-.42,.42):
    cube("Pickup recess bright side",(x,-.272,.344),(.043,.190,.239),interior,"pickup",.009)
cube("Grip bar",(0,-.233,.302),(.327,.029,.016),metal,"pickup",.005)
label("Pickup instruction","PICK UP HERE",0,.522,-.426,.029,white,"pickup")

# The visible service side is detailed rather than flat.
cube("Service cover",(.631,.058,.694),(.010,.528,.936),enamel,radius=.006)
for z in (.403,.445,.487,.529,.571,.613,.655,.697,.739):
    cube("Recessed condenser louver",(.638,.049,z),(.007,.349,.018),trim,radius=.003)
for z in (.283,1.092):
    for y in (-.181,.292):
        cube("Service panel fastener",(.642,y,z),(.010,.015,.015),metal,radius=.002)
for j in range(3):
    cube("Painted side stripe",(.632,.015,1.505-j*.054),(.009,.552,.032),amber if j==0 else enamel,radius=.006)
cube("Rear cooling panel",(0,.392,.571),(.939,.014,.522),trim,radius=.008)
for j in range(9):
    cube("Rear cooler vent",(0,.402,.405+j*.040),(.737,.006,.015),metal,radius=.002)


def aim(o, target):
    o.rotation_euler=(Vector(target)-o.location).to_track_quat("-Z","Y").to_euler()


cube("Studio floor",(0,0,-.029),(200,200,.045),material("Studio charcoal",(.033,.046,.058),.66),"studio")
bpy.ops.object.camera_add(location=(3.45,-6.70,2.92))
camera=attach(bpy.context.object,"Frontal three-quarter studio camera","studio")
aim(camera,(0,-.02,1.04))
camera.data.type="ORTHO";camera.data.ortho_scale=2.57
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
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"street-beverage-vending-machine.blend"))
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
bpy.ops.export_scene.gltf(filepath=str(ROOT/"exports"/"street-beverage-vending-machine.glb"),
                         export_format="GLB",use_selection=True,export_animations=False,
                         export_cameras=False,export_lights=False,export_texcoords=False)
