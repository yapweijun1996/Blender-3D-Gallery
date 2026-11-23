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
  "body":"01 Modular body and service shelf",
  "separate":"02 Divider and sign",
  "inspect":"03 Parcel inspection tray and sample carton",
  "equipment":"04 Flat scale and compact inspection scanner",
  "bins":"05 Separate intake and checked-return bins",
  "staff":"06 Staff aisle storage and hardware",
  "studio":"07 Studio only",
}.items():
    c=bpy.data.collections.new(name)
    scene.collection.children.link(c)
    parts[key]=c


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



indigo=material("Midnight blue powder-coated steel",(.045,.091,.218),.45,.12)
midblue=material("Casement cobalt blue",(.073,.169,.375),.44)
chalk=material("Ivory laminate and signage",(.78,.73,.57),.48)
sand=material("Warm stone-effect counter surround",(.57,.501,.369),.57)
charcoal=material("Blue black rubber and shadow coat",(.037,.054,.082),.59)
light=material("Muted warm white lettering",(.92,.86,.71),.58)
silver=material("Brushed inspection stainless",(.47,.51,.54),.35,.64)
peach=material("Burnt tangerine intake crate",(.68,.173,.055),.54)
teal=material("Desaturated jade checked-return crate",(.048,.36,.28),.54)
paper=material("Unprinted pale stock and tape",(.70,.581,.389),.64)
kraft=material("Kraft corrugated carton",(.37,.203,.094),.78)
crease=material("Carton seam shade",(.227,.112,.051),.81)
display=material("Smoked inactive scale window",(.019,.040,.049),.37)
green=material("Cold glass scanner window",(.065,.31,.25),.28,.18)
panel=material("Neutral transparent acrylic divider",(.72,.89,.98),.17,0,0,.100)


def text(name,body,pos,size,mat,group,flip=False,horizontal=False):
    rotation=(0,0,0) if horizontal else (math.pi/2,0,math.pi if flip else 0)
    bpy.ops.object.text_add(location=pos,rotation=rotation)
    o=attach(bpy.context.object,name,group,mat)
    o.data.body=body;o.data.align_x="CENTER";o.data.align_y="CENTER";o.data.size=size
    o.data.space_character=1.03;o.data.resolution_u=2
    return o


# Front faces Blender -Y. The service and inspection modules have separate
# carcasses and staggered heights. The open portal is merchandise, not payment.
cube("Recessed structural kick plinth",(-.032,.054,.081),(2.324,.693,.162),charcoal,"body",.021)
cube("High service block left side panel",(-1.115,.037,.465),(.111,.751,.808),indigo,"body",.017)
cube("Left shell extra face thickness",(-1.053,.029,.457),(.041,.747,.730),midblue,"body",.013)
cube("Customer approach infill",(-.624,-.327,.473),(.893,.094,.783),chalk,"body",.015)
cube("Customer skeleton centre structural divider",(-.169,.040,.388),(.108,.737,.677),indigo,"body",.018)
cube("Customer panel lower rich indigo skirt",(-.622,-.382,.178),(.873,.039,.107),midblue,"body",.014)
cube("Fine fascia break with a soft return",(-.613,-.382,.555),(.897,.018,.021),silver,"body",.004)
cube("Customer ledge main solid laminate",(-.643,-.012,.869),(1.055,.818,.102),sand,"body",.028)
cube("Overhanging customer document shelf",(-.648,-.233,.927),(1.10,.397,.068),chalk,"body",.019)
cube("Customer shelf top charcoal underside band",(-.654,-.410,.897),(1.037,.041,.027),midblue,"body",.008)
cube("Change-of-level transition end block",(-.089,.033,.821),(.102,.771,.105),indigo,"body",.014)
cube("Inspection worktop mass",(.527,.041,.791),(1.211,.845,.091),chalk,"body",.027)
cube("Inspection top matte skirting",(.520,-.382,.781),(1.210,.045,.087),midblue,"body",.011)
cube("Right vertical end panel", (1.076,.037,.407),(.112,.777,.693),indigo,"body",.019)
cube("Staff rear frame rail",(.506,.363,.648),(1.042,.057,.099),indigo,"body",.014)
cube("Open-sorting framed cubby deck",(.511,-.002,.229),(1.176,.746,.064),indigo,"body",.013)
cube("Portal vertical bin separator",(.492,.044,.448),(.062,.735,.429),charcoal,"body",.009)
cube("Right front top signage stripe",(.512,-.410,.763),(1.139,.030,.030),silver,"body",.004)

# Signs sit behind the check-in shelf; acrylic divider has metal base clips.
for x in (-1.000,-.272):
    cube("Sign rail upright",(x,.354,1.249),(.045,.049,.713),indigo,"separate",.009)
    cube("Bolt-on sign rail stake foot",(x,.353,.925),(.089,.083,.027),silver,"separate",.007)
cube("Raised directional sign board",(-.637,.319,1.437),(.960,.097,.265),indigo,"separate",.024)
cube("Inset ivory returns sign face",(-.637,.264,1.443),(.904,.027,.213),chalk,"separate",.015)
cube("Tangerine service band",(-.638,.246,1.376),(.844,.010,.038),peach,"separate",.005)
text("Primary service sign","RETURNS & EXCHANGES",(-.638,.246,1.466),.071,indigo,"separate")
text("Secondary service sign","01  HANDOVER",(-.637,.239,1.377),.030,light,"separate")
cube("Slim acrylic divider sheet",(-.115,.032,1.075),(.015,.562,.373),panel,"separate",0)
for y in (-.222,.268):
    cube("Top divider edge mounting rail",(-.115,y,1.076),(.026,.023,.368),silver,"separate",.005)
    cube("Divider foot socket",(-.115,y,.903),(.072,.071,.027),silver,"separate",.007)

# Open intake paper tray on high shelf and one anonymous sample carton.
cube("Document tray insert",(-.714,-.153,.977),(.286,.207,.028),charcoal,"inspect",.013)
for x in (-.848,-.580):
    cube("Document tray recessed wing",(x,-.145,.997),(.021,.203,.051),silver,"inspect",.007)
cube("Document tray rear retainer",(-.714,-.052,1.000),(.267,.023,.051),charcoal,"inspect",.007)
sheet=cube("Unmarked return slip blank",(-.720,-.157,1.001),(.190,.118,.002),paper,"inspect",0)
sheet.rotation_euler.z=.07
cube("Blank sample parcel tray base",(.648,-.118,.853),(.681,.425,.037),silver,"inspect",.013)
cube("Inspection tray anti-slip liner",(.648,-.118,.881),(.595,.358,.014),charcoal,"inspect",.010)
for x in (.332,.965):
    cube("Raised inspection tray side-wall",(x,-.117,.903),(.035,.393,.066),silver,"inspect",.008)
cube("Raised rear inspection tray retainer",(.648,.075,.903),(.616,.038,.066),silver,"inspect",.008)
cube("Inspection tray front inset handle",(.646,-.333,.866),(.247,.018,.025),indigo,"inspect",.005)
cube("Blank kraft sample carton",(.699,-.143,.988),(.318,.235,.196),kraft,"inspect",.010)
cube("Carton top center flap seam",(.698,-.143,1.087),(.294,.013,.003),crease,"inspect",0)
cube("Sample carton plain neutral packing tape",(.699,-.143,1.090),(.312,.051,.005),paper,"inspect",.002)
for x in (.540,.858):
    cube("Folded packing tape end tab",(x,-.142,1.048),(.006,.052,.091),paper,"inspect",.002)
cube("Plain paper sample tag, no data",(.725,-.262,1.006),(.123,.004,.049),paper,"inspect",.002)

# Low surface equipment: simple open scanning aperture and a physical
# scale platform. No POS touchscreen, keyboard, card reader or money drawer.
cube("Flat scale base housing",(.180,.179,.863),(.386,.292,.058),charcoal,"equipment",.013)
cube("Brushed low scale weigh plate",(.180,.179,.902),(.350,.256,.031),silver,"equipment",.015)
for x in (.059,.302):
    cube("Scale platform orientation nib",(x,.168,.922),(.006,.126,.004),charcoal,"equipment",0)
cube("Small inactive weighing readout",(.179,.029,.858),(.123,.015,.041),display,"equipment",.008)
cube("Unnumbered off-indicator bar",(.179,.021,.860),(.031,.004,.004),green,"equipment",0)
cube("Inspection scanner base foot",(.764,.290,.856),(.308,.132,.045),silver,"equipment",.014)
cube("Scanner balanced swivel stand",(.764,.303,.924),(.122,.086,.148),indigo,"equipment",.014)
scanner=cube("Scanner short chamfered head",(.762,.264,1.016),(.296,.124,.087),charcoal,"equipment",.019)
scanner.rotation_euler.x=.117
lens=cube("Scanner tilted green aperture",(.762,.201,1.017),(.211,.012,.037),green,"equipment",.007)
lens.rotation_euler.x=.117
for x in (.621,.902):
    cube("Scanner bumper pole endcap",(x,.269,1.019),(.024,.110,.077),midblue,"equipment",.009)


for x,col,title in ((.209,peach,"INTAKE"),(.790,teal,"CHECKED")):
    # Separate open basins with physically distinct colours and bottom panels.
    cube(f"{title} open tote floor",(x,-.023,.282),(.413,.602,.044),col,"bins",.013)
    cube(f"{title} taller rear tote wall",(x,.270,.411),(.415,.037,.239),col,"bins",.009)
    cube(f"{title} low front tote face",(x,-.309,.356),(.413,.045,.134),col,"bins",.012)
    for dx in (-.191,.191):
        cube(f"{title} independent tote side wall",(x+dx,-.022,.399),(.039,.575,.219),col,"bins",.012)
        cube(f"{title} reinforcement lip",(x+dx,-.020,.512),(.053,.556,.023),col,"bins",.006)
    cube(f"{title} upper back lip",(x,.268,.530),(.415,.043,.024),col,"bins",.005)
    cube(f"{title} front handhold slot",(x,-.334,.395),(.135,.009,.023),charcoal,"bins",.007)
    cube(f"{title} frontal cream tag holder",(x,-.335,.336),(.165,.010,.040),chalk,"bins",.005)
    text(f"{title} physical tag",title,(x,-.341,.335),.029,indigo,"bins")
    for j in (-.111,.111):
        cube(f"{title} pressed tote rib",(x+j,-.335,.351),(.015,.014,.090),col,"bins",.003)
        cube(f"{title} floor slide roller",(x+j,-.010,.260),(.022,.525,.016),charcoal,"bins",.003)
cube("Returned item low plain insert",(.832,-.072,.319),(.196,.201,.028),paper,"bins",.006)
cube("Returned item folded edge",(.826,-.169,.335),(.182,.009,.025),kraft,"bins",.002)
cube("Intake tray angled empty insert",(.196,.018,.298),(.236,.305,.017),charcoal,"bins",.007)

# Additional rear access is entirely physical, no receipt or payment fittings.
cube("Staff side left cabinet bottom shelf",(-.618,.104,.203),(.802,.532,.044),midblue,"staff",.009)
cube("Staff side left cabinet mid shelf",(-.618,.104,.526),(.802,.532,.044),indigo,"staff",.009)
for x in (-.962,-.291):
    cube("Open staff niche interior runner",(x,.030,.365),(.037,.470,.356),midblue,"staff",.007)
for z in (.646,.748):
    cube("Staff procedure drawer face",(-.637,.364,z),(.787,.044,.084),chalk,"staff",.008)
    cube("Shallow drawer finger grip",(-.637,.391,z),(.188,.020,.023),silver,"staff",.006)
cube("Rear removable far end access panel",(1.095,.137,.433),(.016,.462,.482),midblue,"staff",.009)
for y in (-.055,.310):
    for z in (.222,.641):
        bolt=cylinder("Panel inset fastener",(1.105,y,z),.010,.008,silver,"staff",n=8)
        bolt.rotation_euler.y=math.pi/2
for x in (.435,.552,.665,.780,.900):
    cube("Cable tray under return station slit",(x,.366,.673),(.071,.020,.019),charcoal,"staff",.004)
def aim(o, target):
    o.rotation_euler=(Vector(target)-o.location).to_track_quat("-Z","Y").to_euler()


cube("Studio floor",(0,0,-.029),(200,200,.045),material("Studio charcoal",(.042,.052,.053),.66),"studio")
bpy.ops.object.camera_add(location=(3.20,-5.56,3.19))
camera=attach(bpy.context.object,"Frontal three-quarter studio camera","studio")
aim(camera,(0,0,.76))
camera.data.type="ORTHO";camera.data.ortho_scale=3.02
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

# Every authoring part remains separate and editable in the saved project.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"mall-returns-exchange-counter.blend"))
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
bpy.ops.export_scene.gltf(filepath=str(ROOT/"exports"/"mall-returns-exchange-counter.glb"),
                         export_format="GLB",use_selection=True,export_animations=False,
                         export_cameras=False,export_lights=False,export_texcoords=False)
