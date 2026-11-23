"""Original shophouse parcel hatch. Blender 5.3, procedural only."""
import argparse
from collections import defaultdict
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ID = "shophouse-parcel-drop-hatch"
PIVOT = (0.0, -0.175, .853)
CLIP = "PARCEL_HATCH_OPEN"
OPEN = math.radians(70)
parser=argparse.ArgumentParser()
parser.add_argument("--output",type=Path,default=Path(__file__).resolve().parent)
parser.add_argument("--review",type=Path)
parser.add_argument("--skip-render",action="store_true")
a=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
R=a.output.resolve()
for f in ("exports","previews"): (R/f).mkdir(parents=True,exist_ok=True)
if a.review: a.review.mkdir(parents=True,exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system="METRIC"
scene.render.fps=30
scene.frame_start=0
scene.frame_end=54
groups={}
for n in ("01 Plaster bay and tile foot","02 Handset-free metal hatch surround",
          "03 Safe stationary sample parcel and tray","04 Local bilingual signage",
          "05 Captive pivoted panel", "06 Native studio only"):
    c=bpy.data.collections.new(n);scene.collection.children.link(c);groups[n[:2]]=c

def lin(x):
    return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4
def mat(n,hexcol,rough=.52,metal=0):
    rgb=[lin(int(hexcol[i:i+2],16)/255) for i in (0,2,4)]
    m=bpy.data.materials.new(n); m.diffuse_color=(*rgb,1); m.use_nodes=True
    p=m.node_tree.nodes.get("Principled BSDF");p.inputs["Base Color"].default_value=m.diffuse_color
    p.inputs["Roughness"].default_value=rough;p.inputs["Metallic"].default_value=metal
    return m
plaster=mat("Aged warm limewash","CCB28C",.82)
shadow=mat("Plaster inset umber","AF9677",.81)
terracotta=mat("Powdery terracotta border","9A5A43",.70)
tile=mat("Sea-green ceramic skirting","527A71",.52)
tile_shade=mat("Faded jade skirting variation","608576",.60)
grout=mat("Cement joints","9F9479",.80)
paving=mat("Rain-worn grey cement floor","718178",.83)
paving_light=mat("Rain-worn swatch variation","819086",.81)
teal=mat("Deep petrol enamel","22595B",.50,.21)
teal_light=mat("Lighter sea-green enamel","347975",.48,.21)
teal_dark=mat("Rear painted aperture steel","1B4345",.60,.20)
steel=mat("Dull brushed warm-grey steel","81796C",.43,.60)
dark=mat("Rubber damp edge and cavity","27302E",.68)
gold=mat("Antique brass accent","A97643",.49,.54)
beige=mat("Illustration letters warm ivory","E8D7B0",.51)
ink=mat("Illustration ink","272D2D",.68)
kraft=mat("Fluted kraft paper","A97544",.74)
kraft_dark=mat("Folded exposed kraft","805432",.75)
tape=mat("Matte kraft sealing tape","C89658",.64)
paper=mat("Sample label pale paper","EAD5AA",.72)
ochre=mat("Amber enamel small sample cue","D99E59",.54)
land=mat("Neutral studio background","5B6264",.74)

def into(o,k):
    for c in list(o.users_collection): c.objects.unlink(o)
    groups[k].objects.link(o);return o
def empty(n, xyz,k):
    o=bpy.data.objects.new(n,None);groups[k].objects.link(o);o.location=xyz;o.empty_display_size=.051
    return o
def box(n,xyz,dim,m,k,bevel=.006,parent=None,rz=0):
    bpy.ops.mesh.primitive_cube_add()
    o=into(bpy.context.object,k);o.name=n;o.dimensions=dim
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.parent=parent; o.location=xyz; o.rotation_euler.z=rz;o.data.materials.append(m)
    if bevel:
        b=o.modifiers.new("Rounded manufactured edges","BEVEL");b.width=bevel;b.segments=2
        w=o.modifiers.new("Weighted planar normals","WEIGHTED_NORMAL");w.keep_sharp=True
    return o
def cyl(n,xyz,r,dep,m,k,axis="z",parent=None,seg=14):
    bpy.ops.mesh.primitive_cylinder_add(vertices=seg,radius=r,depth=dep)
    o=into(bpy.context.object,k);o.name=n;o.parent=parent;o.location=xyz;o.data.materials.append(m)
    if axis=="x":o.rotation_euler.y=math.pi/2
    if axis=="y":o.rotation_euler.x=math.pi/2
    for p in o.data.polygons:
        p.use_smooth=len(p.vertices)==4
    b=o.modifiers.new("Rounded pin edge","BEVEL");b.width=min(.0015,r/5);b.segments=2
    return o
def txt(n, words, xyz, width, nominal, m, k, parent=None):
    curve=bpy.data.curves.new(n,"FONT");curve.body=words;curve.align_x="CENTER"
    curve.size=nominal;curve.resolution_u=4;curve.extrude=.00045
    o=bpy.data.objects.new(n,curve);groups[k].objects.link(o)
    o.parent=parent;o.location=xyz;o.rotation_euler.x=math.pi/2
    curve.materials.append(m)
    bpy.context.view_layer.update()
    if o.dimensions.x>width:
        size=width/o.dimensions.x
        o.scale=(size,size,size)
    return o
# Fictional streetside bay: one partial wall, discrete ledge, grout and worn tile apron.
box("Segment of shallow terrazzo stoop", (0,.018,.047),(1.18,.72,.094),paving,"01",.018)
for i in range(8):
    for j in range(3):
        x=-.506+i*.144
        y=-.270+.147*j
        box("Paving setts", (x,y,.097),(.136,.139,.014),paving_light if (i*3+j*5)%7 in (0,1) else paving,"01",.002)
box("Limewash left pier",(-.432,.097,.889),(.244,.37,1.588),plaster,"01",.018)
box("Limewash right pier",(.432,.097,.889),(.244,.37,1.588),plaster,"01",.018)
box("Plastered lintel above wall aperture",(0,.097,1.501),(.635,.370,.363),plaster,"01",.011)
box("Lower plaster spandrel",(0,.097,.459),(.624,.370,.719),plaster,"01",.01)
box("Limewash top lintel cap",(0,.095,1.690),(1.122,.390,.075),shadow,"01",.010)
box("Narrow terracotta shadow line",(0,-.093,1.606),(1.096,.016,.028),terracotta,"01",.002)
box("Cement skirting backing",(0,-.103,.265),(1.110,.026,.268),grout,"01",.006)
for i in range(8):
    for j in range(2):
        x=-.483+i*.138; z=.195+j*.126
        box("Plain glazed shophouse tile",(x,-.124,z),(.13,.025,.118),tile_shade if (i+2*j)%5==0 else tile,"01",.003)
box("Small decorative skirting cap",(0,-.139,.398),(1.112,.039,.033),tile_shade,"01",.004)
# Small vertical warm accents are decorative (not a historic tile reconstruction).
for x in [-.483,.483]:
    box("Slender recessed warm side seam",(x,-.091,.949),(.061,.028,.906),shadow,"01",.006)
    for z in [.596,.826,1.056,1.286]:
        box("Stamp of terracotta colour", (x,-.111,z),(.048,.017,.123),terracotta,"01",.006)
        box("Original geometric cartouche", (x,-.124,z),(.010,.004,.040),beige,"01",.001)
box("Apron narrow cement nosing",(0,-.307,.110),(1.11,.034,.025),grout,"01",.005)

# Surround is genuinely open; no wall face, illusion, or fixed slab closes the aperture.
box("Compartment inner lower tray",(0,.104,.864),(.662,.410,.068),teal_dark,"02",.007)
box("Compartment inner back",(0,.311,1.075),(.650,.035,.468),teal_dark,"02",.009)
box("Compartment inner roof",(0,.064,1.297),(.664,.49,.062),teal_dark,"02",.006)
for x in [-.330,.330]:
    box("Compartment side leaf",(x,.069,1.072),(.068,.482,.443),teal_dark,"02",.009)
for x in [-.327,.327]:
    box("Enamel foreplate upright",(x,-.135,1.071),(.078,.071,.536),teal,"02",.007)
    box("Soft jamb profile",(x- .035 if x<0 else x+.035,-.178,1.085),(.014,.016,.472),dark,"02",.002)
box("Enamel face header",(0,-.135,1.329),(.732,.076,.087),teal,"02",.011)
box("Drip edge over recessed frame",(0,-.193,1.358),(.754,.073,.039),teal_light,"02",.008)
box("Enamel bottom threshold",(0,-.115,.813),(.730,.117,.081),teal,"02",.008)
box("Stationary front sill rib",(0,-.145,.851),(.612,.032,.023),steel,"02",.003)
for x in [-.316,.316]:
    box("Hinge saddle mounting ears",(x,-.171,.841),(.066,.063,.086),teal,"02",.004)
    cyl("Fixed end bearing",(x,PIVOT[1],PIVOT[2]),.028,.057,steel,"02","x")
    for z in [.922,1.234]:
        cyl("Rounded neutral housing stud",(x,-.175,z),.009,.009,steel,"02","y",seg=12)
# Mock parcel stands on an inner rest, deliberately not attached to the swinging panel.
box("Stationary folded parcel rest",(0,.130,.916),(.494,.334,.044),steel,"03",.006)
for i in range(9):
    box("Inner stationary non-slip ribs",(-.203+i*.051,.128,.940),(.013,.286,.004),dark,"03",.001)
sample=empty("PARCEL_DROP_SAMPLE",(.011,.116,.942),"03")
sample.rotation_euler.z=math.radians(3)
box("Sealed no-carrier sample parcel",(0,0,.095),(.306,.220,.190),kraft,"03",.008,sample)
box("Fold seam strip on front",(0,-.1105,.135),(.279,.004,.004),kraft_dark,"03",.001,sample)
box("Fold seam across top",(0,0,.191),(.289,.007,.004),kraft_dark,"03",.001,sample)
box("Matte longitudinal paper tape",(0,.003,.193),(.048,.213,.004),tape,"03",.002,sample)
box("Tape edge on front",(.077,-.111,.157),(.032,.004,.060),tape,"03",.001,sample)
box("Uncoded SAMPLE face label",(-.038,-.113,.105),(.159,.004,.073),paper,"03",.005,sample)
txt("SAMPLE lettering","SAMPLE",(-.038,-.116,.099),.124,.027,ink,"03",sample)
box("Small non-data line on paper label",(-.038,-.116,.092),(.091,.002,.003),ink,"03",.001,sample)
# Bilingual purpose plate, no carrier, real service instruction or claimed security.
box("Upper navy signage plate", (0,-.108,1.485),(.616,.045,.164),teal_dark,"04",.010)
box("Inset warm accent rule", (0,-.134,1.459),(.506,.009,.007),ochre,"04",.0016)
txt("EN parcel label","PARCEL DROP", (0,-.136,1.484),.486,.072,beige,"04")
txt("MS parcel label","SERAHAN BUNGKUSAN", (0,-.136,1.413),.470,.041,beige,"04")
# Pivot and all descendants share a physically plausible horizontal bottom axis.
flap=empty("PARCEL_DROP_FLAP",PIVOT,"05")
box("Slightly rounded movable hatch sheet",(0,-.025,.219),(.556,.058,.427),teal_light,"05",.010,flap)
box("Stamped closed-face inset",(0,-.055,.223),(.511,.016,.375),teal,"05",.008,flap)
box("Solid visible inner face",(0,.009,.219),(.512,.015,.377),teal_dark,"05",.009,flap)
for x in [-.204,.204]:
    box("Inner stiffener", (x,.019,.207),(.049,.017,.316),teal_light,"05",.006,flap)
for x in [-.094,.094]:
    box("Handle stand-off",(x,-.081,.350),(.035,.064,.035),gold,"05",.006,flap)
box("Rounded empty pull handle",(0,-.114,.350),(.227,.037,.037),gold,"05",.009,flap)
for x in [-.216,.216]:
    cyl("Moving hinge knuckle",(x,0,0),.019,.115,steel,"05","x",flap)
cyl("Moving central hinge sleeve",(0,0,0),.013,.322,steel,"05","x",flap)
# Single authored curve; panel opens only outward (+X rotation), then holds.
for f,pct in [(0,0),(5,0),(12,.102),(20,.396),(28,.764),(36,1),(54,1)]:
    flap.rotation_euler.x=OPEN*pct
    flap.keyframe_insert(data_path="rotation_euler",index=0,frame=f,group="Fictional one-motion reveal")
motion=flap.animation_data.action;motion.name="Hand-authored outward hatch reveal"
track=flap.animation_data.nla_tracks.new();track.name=CLIP
track.strips.new("Demo open and hold",0,motion)
flap.animation_data.action=None

# Photographer's independent backdrop + lights, never part of the exported asset.
box("Studio floor, not exported",(0,0,-.037),(200,200,.065),land,"06",0)

def aim(o,d):
    o.rotation_euler=(Vector(d)-o.location).to_track_quat("-Z","Y").to_euler()
def lamp(name,xyz,power,scale,color,target=(0,-.01,.91)):
    d=bpy.data.lights.new(name,"AREA"); d.energy=power;d.shape="DISK";d.size=scale;d.color=color
    o=bpy.data.objects.new(name,d);groups["06"].objects.link(o);o.location=xyz;aim(o,target)
lamp("Cloudy key",(-1.9,-2.65,3.72),182,2.28,(1,.89,.77))
lamp("Soft front fill",(1.62,-2.12,2.29),104,1.75,(.85,.95,1))
lamp("Recess and SAMPLE visibility",(.09,-1.78,1.99),62,1.10,(1,.96,.84),(0,.14,1.025))
lamp("Pale wall skim",(1.5,1.25,2.3),126,1.8,(.84,.93,1))
wl=bpy.data.worlds.new("Overcast daylight");scene.world=wl;wl.use_nodes=True
world=wl.node_tree.nodes["Background"];world.inputs[0].default_value=(.51,.58,.61,1)
world.inputs[1].default_value=.46
camera=bpy.data.cameras.new("Retained orthographic studio")
cam=bpy.data.objects.new("Retained orthographic studio",camera)
groups["06"].objects.link(cam);scene.camera=cam
cam.location=(1.68,-3.36,2.35);aim(cam,(0,-.056,.857))
camera.type="ORTHO";camera.ortho_scale=2.20;camera.lens=48
scene.render.engine="CYCLES"; scene.cycles.samples=48
scene.cycles.use_denoising=(sys.platform=="darwin")
scene.render.threads_mode="FIXED";scene.render.threads=6
scene.view_settings.view_transform="AgX"
scene.view_settings.exposure=-.12
scene.render.resolution_x=512;scene.render.resolution_y=512;scene.render.resolution_percentage=100
scene.render.image_settings.file_format="WEBP";scene.render.image_settings.quality=93
scene.render.filepath="//previews/studio.webp"
scene.frame_set(0)
bpy.ops.object.select_all(action="DESELECT")
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(R/(ID+".blend")),compress=True)
def render_path(dest,f):
    scene.frame_set(f);scene.render.filepath=str(dest);bpy.ops.render.render(write_still=True)
if not a.skip_render:
    render_path(R/"previews"/"studio.webp",54)
if a.review:
    render_path(a.review/"closed.webp",0)
    cam.location=(.88,-2.54,1.91);aim(cam,(0,.025,1.115))
    camera.ortho_scale=1.25
    scene.render.resolution_x=740;scene.render.resolution_y=620
    render_path(a.review/"opened-detail.webp",54)
scene.frame_set(0)
# Native source remains editable. Use a material-and-parent join only in the export copy.
chosen=[]
def one(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True);bpy.context.view_layer.objects.active=ob
for k,c in sorted(groups.items()):
    if k=="06": continue
    parts=defaultdict(list)
    for ob in list(c.objects):
        if ob.type=="EMPTY":
            chosen.append(ob); continue
        if ob.type!="MESH" or ob.modifiers:
            one(ob);bpy.ops.object.convert(target="MESH");ob=bpy.context.view_layer.objects.active
        parts[(ob.parent.name if ob.parent else None,ob.data.materials[0].name)].append(ob)
    for (parent,key),items in sorted(parts.items(),key=lambda pair: (pair[0][0] or "",pair[0][1])):
        bpy.ops.object.select_all(action="DESELECT")
        for ob in items: ob.select_set(True)
        obj=items[0];bpy.context.view_layer.objects.active=obj
        if len(items)>1:bpy.ops.object.join()
        obj.name=(parent or c.name[3:])+" | "+key
        chosen.append(obj)
bpy.ops.object.select_all(action="DESELECT")
for o in chosen: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(R/"exports"/(ID+".glb")),export_format="GLB",
 use_selection=True,export_animation_mode="NLA_TRACKS",export_animations=True,export_force_sampling=True,
 export_cameras=False,export_lights=False,export_texcoords=False,export_extras=False)
