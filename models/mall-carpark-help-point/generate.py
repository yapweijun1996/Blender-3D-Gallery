"""Original mall car park assistance pedestal and local-only authored sample press."""
import math
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector

SLUG="mall-carpark-help-point"
D=Path(__file__).resolve().parent
for folder in ("exports","previews"):
    (D/folder).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system="METRIC"
scene.render.fps=24
scene.frame_start=0
scene.frame_end=36
parts={}
for name in ("01 Curb island and anchored plinth",
             "02 Pedestal serviceable housing",
             "03 Bilingual assistance hardware",
             "04 Moving demo button and acknowledgment lens",
             "05 Studio only"):
    c=bpy.data.collections.new(name)
    scene.collection.children.link(c)
    parts[name[:2]]=c

def mat(name,rgb,r=.48,metal=0,glow=0):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    m.diffuse_color=(*rgb,1)
    b=m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value=(*rgb,1)
    b.inputs["Roughness"].default_value=r
    b.inputs["Metallic"].default_value=metal
    b.inputs["Emission Color"].default_value=(*rgb,1)
    b.inputs["Emission Strength"].default_value=glow
    return m

def attach(o,name,key,m=None):
    o.name=name
    for c in list(o.users_collection):
        c.objects.unlink(o)
    parts[key].objects.link(o)
    if m: o.data.materials.append(m)
    return o

def cube(name,center,size,m,key,r=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center)
    o=attach(bpy.context.object,name,key,m)
    o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if r>=.007:
        b=o.modifiers.new("Manufactured radius","BEVEL")
        b.width=r
        b.segments=2 if r>.022 else 1
        b.harden_normals=True
        b=o.modifiers.new("Weighted corner normals","WEIGHTED_NORMAL")
        b.keep_sharp=True
    return o

def cyl(name,center,r,h,m,key,n=16,front=False):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n,radius=r,depth=h,location=center)
    o=attach(bpy.context.object,name,key,m)
    if front: o.rotation_euler.x=math.pi/2
    for p in o.data.polygons: p.use_smooth=len(p.vertices)==4
    return o

def bar(name,a,b,w,h,m,key,r=0):
    aa,bb=Vector(a),Vector(b)
    o=cube(name,(aa+bb)/2,(w,h,(bb-aa).length),m,key,r)
    o.rotation_euler=(bb-aa).to_track_quat("Z","Y").to_euler()
    return o

def text(name,data,p,size,m,key,align="CENTER"):
    bpy.ops.object.text_add(location=p,rotation=(math.pi/2,0,0))
    o=attach(bpy.context.object,name,key,m)
    o.data.body=data
    o.data.align_x=align
    o.data.align_y="CENTER"
    o.data.size=size
    o.data.resolution_u=2
    return o

curb=mat("Warm charcoal terrazzo",(.209,.231,.221),.79)
stone=mat("Finely textured light grey island top",(.412,.425,.394),.70)
mustard=mat("Golden weather-resistant powder coat",(.79,.414,.063),.52,.12)
faded=mat("Muted safety yellow curb cue",(.80,.65,.24),.71)
ink=mat("Deep blue spruce enclosure",(.035,.105,.127),.50,.19)
rubber=mat("Night grey gasket and recesses",(.028,.041,.047),.55)
grey=mat("Brushed nickel service detailing",(.41,.46,.441),.39,.43)
ivory=mat("Enamel off-white front labels",(.85,.87,.77),.54)
amber=mat("Amber ready lens",(.91,.360,.047),.34,.07,.45)
green=mat("Mint green fictional acknowledgment only",(.045,.98,.44),.29,.03,2.0)

# Small neutral modular island. No surveyed or safety-engineered layout claim.
cube("Floor-level continuous curb island",(.037,.003,.076),(.93,.627,.152),curb,"01",.045)
cube("Broad island flat paver inset",(.048,.021,.143),(.826,.539,.029),stone,"01",.018)
for x in (-.144,.190):
    cube("Shallow top expansion line",(x,.020,.157),(.008,.505,.003),curb,"01")
for x in (-.211,.016,.242):
    o=cube("Neutral short yellow cue painted at island edge",(x,-.263,.139),(.122,.046,.009),faded,"01")
    o.rotation_euler.y=.12
cube("Stand anchored mounting foot",(0,.031,.177),(.466,.401,.051),ink,"01",.021)
for x in (-.175,.175):
    for y in (-.104,.158):
        cyl("Recessed mounting anchor head",(x,y,.205),.014,.008,grey,"01",8)

# A serviceable head and narrow welded leg, not a ticket, card reader or crossing.
cube("Raised anti-splash welded pedestal leg",(0,.039,.551),(.247,.220,.712),ink,"02",.024)
cube("Golden stainless leg front cover",(0,-.070,.507),(.219,.019,.461),mustard,"02",.009)
cube("Pedestal foot resilient collar",(0,.039,.231),(.285,.251,.087),rubber,"02",.014)
cube("Pedestal back recessed maintenance hatch",(0,.155,.556),(.206,.019,.431),mustard,"02",.012)
for z in (.369,.735):
    cyl("Back-only maintenance fastener",(.074,.170,z),.011,.010,grey,"02",8,True)
for side in (-1,1):
    cube("Gold side-shell side wall",(side*.183,.035,.975),(.044,.298,.508),mustard,"02",.019)
    cube("Dark edge gasket on side service door",(side*.205,.052,.975),(.007,.211,.419),rubber,"02",.011)
    cube("Soft side cover inset",(side*.209,.057,.980),(.012,.186,.397),mustard,"02",.011)
    for z in (.794,1.122):
        cube("Exposed short inset enclosure hinge",(side*.213,.138,z),(.020,.047,.032),grey,"02",.008)
cube("Sealed removable weather cap back",(0,.147,.971),(.365,.077,.513),ink,"02",.029)
cube("Deep gold rainfall overhang",(0,.009,1.238),(.441,.401,.075),mustard,"02",.023)
o=cube("Slanted top roof rain drip characteristic",(0,.020,1.281),(.406,.365,.027),mustard,"02",.011)
o.rotation_euler.x=.063
cube("Under-roof dark trim",(0,-.166,1.205),(.399,.064,.039),ink,"02",.008)
cube("Deep facade and front glass-free service panel",(0,-.112,.984),(.364,.080,.451),ink,"03",.018)
cube("Rounded ivory bilingual upper label",(0,-.159,1.155),(.337,.017,.085),ivory,"03",.010)
text("Malay header","BANTUAN",(0,-.169,1.174),.035,ink,"03")
text("English header","HELP POINT",(0,-.169,1.138),.024,ink,"03")

# Actual visual speaker gaps alternate with stiff grille bars backed by a recessed diaphragm.
cube("Speaker and microphone dark diaphragm recess",(0,-.154,1.050),(.302,.020,.097),rubber,"03",.008)
for x in (-.146,.146):
    cube("Speaker grill side raised trim",(x,-.175,1.050),(.024,.025,.091),grey,"03",.007)
for z in (1.024,1.040,1.056,1.072):
    cube("Vented speaker horizontal face bar",(0,-.176,z),(.273,.023,.007),grey,"03")
for x in (-.108,-.053,0,.053,.108):
    cyl("Illustrative mic perforation cap",(x,-.161,.994),.006,.012,grey,"03",9,True)
cube("Recessed capsule readiness display trim",(0,-.166,.963),(.263,.029,.040),rubber,"03",.009)
cube("Visible low-power amber ready status bar",(0,-.185,.963),(.173,.013,.014),amber,"03",.007)
text("Fictional demo small marker","CONTOH / DEMO",(0,-.159,.925),.015,ivory,"03")

# One physically movable push face and separate concealed green emitter.
cube("Metal push control raised bezel",(0,-.176,.841),(.177,.060,.116),grey,"03",.018)
cube("Push control dark gasket",(0,-.207,.841),(.150,.014,.094),rubber,"03",.010)
cube("Lower offset panel reinforcement label",(0,-.151,.763),(.205,.014,.021),mustard,"03",.005)
button=cube("CARPARK_HELP_BUTTON",(0,-.223,.841),(.133,.027,.079),mustard,"04",.013)
def keep_parent(o,p):
    # Convert explicit world transform to local, keeping genuinely mobile descendants.
    bpy.context.view_layer.update()
    before=o.matrix_world.copy()
    o.parent=p
    o.matrix_world=before
for name,value,z,sz in (("Malay key print","TEKAN",.855,.018),("English key print","PRESS",.826,.012)):
    keep_parent(text(name,value,(0,-.237,z),sz,ink,"04"),button)
indicator=cube("CARPARK_HELP_INDICATOR",(0,-.171,.963),(.170,.009,.0135),green,"04",.006)
# Active group channels express exactly two translations. World-facing positive
# glTF Z is Blender −Y. Button travels 12 mm inward, then releases.
def track(obj, yframes):
    for f,y in yframes:
        obj.location.y=y
        obj.keyframe_insert(data_path="location",frame=f,group="Illustrative local-only press")
    a=obj.animation_data.action
    a.name=obj.name+"_source_motion"
    track=obj.animation_data.nla_tracks.new()
    track.name="CARPARK_HELP_PRESS"
    track.strips.new("One illustrative press",0,a)
    obj.animation_data.action=None
track(button,[(0,-.223),(5,-.223),(12,-.211),(16,-.211),(22,-.223),(36,-.223)])
track(indicator,[(0,-.171),(15,-.171),(20,-.197),(36,-.197)])

def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()
floor=mat("Neutral dark concrete in studio only",(.103,.124,.127),.71)
cube("Studio floor",(0,0,-.03),(140,140,.055),floor,"05")
bpy.ops.object.camera_add(location=(1.75,-3.65,1.88))
c=attach(bpy.context.object,"Front editorial studio camera","05")
aim(c,(.011,-.013,.633))
c.data.type="ORTHO"
c.data.ortho_scale=1.73
scene.camera=c
for name,p,energy,col,size in (
    ("Warm softbox front",(1.57,-3.3,3.15),405,(1,.873,.71),2.9),
    ("Cool softbox left",(-2.65,-1.96,2.1),280,(.68,.89,1),2.4),
    ("Soft island backlight",(2.36,1.64,3.1),360,(.77,.94,1),2.15),
):
    bpy.ops.object.light_add(type="AREA",location=p)
    o=attach(bpy.context.object,name,"05")
    o.data.energy=energy
    o.data.color=col
    o.data.shape="DISK"
    o.data.size=size
    aim(o,(0,0,.67))
scene.world=bpy.data.worlds.new("Studio diffuse ambience")
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes["Background"]
bg.inputs[0].default_value=(.45,.51,.59,1)
bg.inputs[1].default_value=.36
scene.render.engine="CYCLES"
scene.cycles.samples=24
scene.cycles.use_denoising=True
scene.render.resolution_x=720
scene.render.resolution_y=720
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.view_settings.view_transform="AgX"
scene.render.filepath=str(D/"previews"/"studio.png")
scene.frame_set(0)
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.wm.save_as_mainfile(filepath=str(D/(SLUG+".blend")))
if "--skip-render" not in sys.argv:
    bpy.ops.render.render(write_still=True)
    if "--press-review" in sys.argv:
        c.location=(.79,-2.84,1.4)
        aim(c,(0,-.176,1.036))
        c.data.ortho_scale=.57
        for tag,f in (("ready",0),("down",14),("ack",36)):
            scene.frame_set(f)
            scene.render.filepath=str(D/"previews"/(tag+".png"))
            bpy.ops.render.render(write_still=True)
        scene.frame_set(0)

def convert(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.convert(target="MESH")
    return bpy.context.view_layer.objects.active

selected=[]
for key, col in parts.items():
    if key=="05": continue
    if key=="04":
        # The tracked push surface, attached labels and green emitter stay
        # distinct named glTF objects; the animation tracks are preserved.
        for o in list(col.objects):
            selected.append(convert(o) if o.type=="FONT" else o)
        continue
    by=defaultdict(list)
    for o in list(col.objects):
        if o.modifiers or o.type=="FONT": o=convert(o)
        by[o.data.materials[0].name].append(o)
    for name, objects in sorted(by.items()):
        bpy.ops.object.select_all(action="DESELECT")
        for o in objects: o.select_set(True)
        a=objects[0]
        bpy.context.view_layer.objects.active=a
        if len(objects)>1: bpy.ops.object.join()
        a.name=col.name[3:]+" | "+name
        selected.append(a)
bpy.ops.object.select_all(action="DESELECT")
for o in selected: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(D/"exports"/(SLUG+".glb")),
    export_format="GLB", use_selection=True, export_animations=True,
    export_animation_mode="NLA_TRACKS", export_force_sampling=True,
    export_cameras=False, export_lights=False, export_texcoords=False)
