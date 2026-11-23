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
    "site": "01 Asphalt and pedestrian island",
    "mark": "02 Bay paint and inset tactile cue",
    "frame": "03 Cantilever steel frame",
    "roof": "04 Folded canopy water path",
    "sign": "05 Numbered pickup marker",
    "amenity": "06 Bench and edge protection",
    "studio": "07 Studio only",
}.items():
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    parts[key] = c


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


# Shared plain PBR materials; there are no texture dependencies or logos.
asphalt = material("Charcoal street asphalt", (.040,.048,.059), .91)
bay = material("Cool dark lay-by pavement", (.075,.115,.132), .91)
substrate = material("Onyx cutaway plinth", (.030,.038,.047), .73)
slab = material("Matte light cement paver", (.41,.45,.46), .84)
slab_alt = material("Cool mid-grey cement paver", (.32,.36,.38), .84)
grout = material("Dark paver and drain joints", (.087,.112,.118), .82)
curb = material("Warm precast concrete curb", (.57,.55,.50), .83)
amber = material("Amber cast tactile tile", (.91,.49,.077), .79)
line = material("Buff yellow roadway paint", (.95,.68,.22), .76)
chalk = material("Warm white sign and paint field", (.86,.86,.73), .69)
teal = material("Petrol matte structural steel", (.038,.191,.207), .44, .22)
roofmat = material("Pale zinc standing seam sheets", (.36,.57,.58), .47, .23)
accent = material("Seafoam edge aluminum", (.143,.58,.51), .39, .24)
dark = material("Blue black sign and powder coat", (.022,.075,.104), .48)
metal = material("Satin stainless hardware", (.41,.49,.50), .40, .64)
diffusion = material("Neutral frosted ceiling light", (.76,.91,.94), .34, 0, .43)
teak = material("Pale outdoor hardwood bench", (.46,.26,.115), .63)


def mesh_object(name,verts,faces,mat,group):
    d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update()
    o=bpy.data.objects.new(name,d);parts[group].objects.link(o)
    o.data.materials.append(mat)
    return o


def strip(name, path, width, mat, group, radius=.008):
    """Square-section segment sweep with positively connected elbow plates."""
    for i,(a,b) in enumerate(zip(path,path[1:])):
        p,q=Vector(a),Vector(b);d=q-p
        box=cube(f"{name} span {i+1}",(p+q)/2,(width,width,d.length+.003),mat,group,radius)
        box.rotation_mode="QUATERNION";box.rotation_quaternion=d.to_track_quat("Z","Y")


def points_mesh(name, points, z0, z1, mat, group):
    # Counter-clockwise plan polygon extruded upward.
    n=len(points)
    verts=[(x,y,z) for z in (z0,z1) for x,y in points]
    faces=[tuple(reversed(range(n))),tuple(range(n,n*2))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    return mesh_object(name, verts, faces, mat, group)


def writing(name, text, xyz, size, mat, group, angle=(math.pi/2,0,0)):
    bpy.ops.object.text_add(location=xyz,rotation=angle)
    o=attach(bpy.context.object,name,group,mat)
    o.data.body=text;o.data.size=size;o.data.align_x="CENTER";o.data.align_y="CENTER"
    o.data.resolution_u=2;o.data.space_character=1.08
    return o


def squared_pictogram(x,y,z):
    # Generic motorcar pictogram in the sign face, not a logo.
    profile("Pickup car windshield",[(-.048+x,.010+z),(.048+x,.010+z),(.035+x,.047+z),
                                     (-.032+x,.047+z)],y,.003,chalk,"sign",0)
    cube("Pickup pictogram body",(x,y-.003,z-.010),(.139,.007,.041),chalk,"sign",.005)
    for dx in (-.044,.044):
        cube("Pickup pictogram tire",(x+dx,y-.004,z-.038),(.025,.006,.029),chalk,"sign",.003)


# One self-contained road-edge module, not a whole roadway or a real survey.
deck=[(-3.13,-2.38),(-2.99,-2.52),(3.01,-2.52),(3.14,-2.38),
      (3.14,1.64),(2.99,1.79),(-2.99,1.79),(-3.13,1.63)]
points_mesh("Chamfered modular display substrate",deck,0,.142,substrate,"site")
road=[(-3.11,-2.36),(-2.98,-2.49),(2.98,-2.49),(3.12,-2.37),
      (3.12,-.04),(-3.11,-.04)]
points_mesh("Continuous asphalt road deck",road,.137,.175,asphalt,"site")
inset=[(-2.63,-.25),(-2.34,-2.29),(2.25,-2.29),(2.59,-.25)]
points_mesh("Inlaid darker single pickup berth",inset,.175,.177,bay,"site")

# Pedestrian island is uninterrupted except for the deliberate ramp aperture.
ramp_l,ramp_r=.72,1.80
for i in range(13):
    x0=-3.102+i*.476;x1=x0+.468
    for j,(y0,y1) in enumerate(((.685,1.031),(1.041,1.386),(1.396,1.632))):
        if i in (0,12) and j==2:
            continue
        cube("Scored island pavement plate",((x0+x1)/2,(y0+y1)/2,.290),
             (x1-x0,y1-y0,.025),slab if (i+j)%5 else slab_alt,"site",.003)
cube("Left main island slab",((-3.105+ramp_l)/2,.269,.277),(ramp_l+3.105,.801,.047),slab,"site",.008)
cube("Right main island slab",((3.102+ramp_r)/2,.269,.277),(3.102-ramp_r,.801,.047),slab,"site",.008)
for x0,x1 in ((-3.097,ramp_l),(ramp_r,3.079)):
    for i in range(math.ceil((x1-x0)/.40)):
        a=x0+i*.40;b=min(x1,a+.39)
        if b-a>.009:
            cube("Rounded precast kerb unit",((a+b)/2,-.059,.229),(b-a,.152,.137),curb,"site",.012)
# Ensure that the ramp skin rises from roadway to deck without a curb piece crossing it.
v=[(x,y,z) for z in (.174,) for x,y in ((ramp_l,-.135),(ramp_r,-.135),(ramp_r,.463),(ramp_l,.463))]
v.extend((x,y,z) for x,y,z in ((ramp_l,-.135,.18),(ramp_r,-.135,.18),(ramp_r,.463,.302),(ramp_l,.463,.302)))
ramp=mesh_object("Continuous cast curb-cut ramp",v,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],curb,"site")
# Lower the underlay only in the ramp slice: two separate road-edge pieces keep the sloped face visible.
cube("Left continuous island underlay",((-3.105+ramp_l)/2,.850,.210),(ramp_l+3.105,1.82,.14),grout,"site",.004)
cube("Right continuous island underlay",((3.10+ramp_r)/2,.850,.210),(3.10-ramp_r,1.82,.14),grout,"site",.004)
cube("Pedestrian ramp top landing",(1.26,.567,.265),(1.08,.211,.074),slab,"site",.005)
cube("Tactile tile backing inset",(1.26,.537,.307),(.908,.161,.015),amber,"mark",.005)
for i in range(13):
    for j in range(3):
        cylinder("Truncated tactile stud",(.861+i*.066,.488+j*.047,.320),.012,.012,amber,"mark",n=8)
# Terminate the front and rear floor as a coherent single diorama tile.
cube("Rear grey island border strip",(0,1.683,.262),(5.87,.115,.091),curb,"site",.013)
for x in (-1.78,2.43):
    cube("Kerb drain grille frame",(x,-.172,.186),(.289,.232,.023),grout,"site",.008)
    for i in range(8):
        cube("Drain slot bridge",(x-.112+i*.032,-.172,.199),(.013,.166,.009),metal,"site",.001)

# Contrasting dual-colour paint does not imply any signed traffic regulation.
for a,b in (((-2.62,-.25),(-2.34,-2.29)),((-2.34,-2.29),(2.26,-2.29)),((2.26,-2.29),(2.58,-.25))):
    dx=b[0]-a[0];dy=b[1]-a[1]
    o=cube("Dedicated bay painted perimeter",((a[0]+b[0])/2,(a[1]+b[1])/2,.178),
           (math.hypot(dx,dy)+.014,.045,.002),line,"mark",0)
    o.rotation_euler.z=math.atan2(dy,dx)
writing("Large painted pickup berth legend","PICKUP",(-.48,-1.45,.180),.34,chalk,"mark",(0,0,0))
writing("Matching berth number on pavement","08",(1.58,-1.44,.180),.35,line,"mark",(0,0,0))
for x in (-.79,.79):
    a=[(x-.040,-.773),(x+.040,-.773),(x+.040,-.545),(x+.105,-.545),
       (x,-.412),(x-.105,-.545),(x-.040,-.545)]
    points_mesh("Painted pedestrian directional cue",a,.177,.179,chalk,"mark")


# Open front with posts behind waiting line: no support inside the road berth.
for x in (-1.94,1.98):
    cube("Raised steel foundation pad",(x,1.267,.333),(.361,.322,.076),curb,"frame",.015)
    cube("Post base powder-coated mounting plate",(x,1.267,.380),(.292,.260,.029),dark,"frame",.008)
    for dx,dy in ((-.099,-.086),(.099,-.086),(.099,.086),(-.099,.086)):
        cylinder("Visible foundation anchor head",(x+dx,1.267+dy,.402),.016,.020,metal,"frame",n=6)
    strip("Tapered-position steel upright",[(x,1.267,.393),(x,1.259,1.650),(x,1.190,2.508)],.147,teal,"frame",.012)
    strip("Diagonal cantilever tension brace",[(x,1.251,1.838),(x,.977,2.191),(x,.414,2.450)],.088,teal,"frame",.009)
    strip("Underside cantilever boom",[(x,1.502,2.416),(x,.660,2.480),(x,-.530,2.543)],.131,teal,"frame",.010)
    cube("Beam cap on projecting end",(x,-.544,2.540),(.147,.021,.123),accent,"frame",.009)
for y,z in ((-.568,2.570),(1.466,2.450)):
    cube("Shared spanning structural beam",(0,y,z),(4.744,.107,.106),teal,"frame",.010)

# Each canopy sheet slopes to a slotted rear gutter. The front fascia is higher.
for i in range(9):
    x=-2.43+i*.540
    w=.541
    yf,yr=-.658,1.555
    front,rear=2.658,2.532
    vertices=[(x,yf,front-.027),(x+w,yf,front-.027),(x+w,yr,rear-.027),(x,yr,rear-.027),
              (x,yf,front),(x+w,yf,front),(x+w,yr,rear),(x,yr,rear)]
    mesh_object("Folded standing seam canopy roof sheet",vertices,
                [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],roofmat,"roof")
    strip("Rolled standing seam enclosure",[(x,yf+.036,front+.008),(x,yr-.018,rear+.008)],.020,accent,"roof",.004)
cube("Thin high front aluminum fascia",(0,-.640,2.617),(4.880,.093,.118),accent,"roof",.016)
cube("Powder-coated fascia edge lower trim",(0,-.686,2.572),(4.841,.026,.026),teal,"roof",.007)
for x in (-2.415,2.423):
    strip("Sloped edge weather cap",[(x,-.630,2.650),(x,1.550,2.524)],.048,dark,"roof",.009)
cube("Rain gutter continuous trough base",(0,1.570,2.466),(4.846,.184,.026),dark,"roof",.006)
for y in (1.491,1.646):
    cube("Rain gutter rolled vertical lip",(0,y,2.501),(4.854,.020,.085),accent,"roof",.007)
for x in (-2.422,2.422):
    cube("Gutter end closure",(x,1.569,2.500),(.022,.170,.091),dark,"roof",.008)
strip("Connected rear downspout",[(1.966,1.592,2.454),(1.966,1.576,2.294),
           (1.966,1.356,2.074),(1.966,1.356,.577),(1.966,1.517,.391)],.057,accent,"roof",.010)
for z in (.655,1.442,2.005):
    cube("Downspout saddle strap",(1.967,1.338,z),(.084,.081,.024),metal,"roof",.006)
cube("Rear drain shoe catch plate",(1.967,1.513,.315),(.225,.176,.017),grout,"roof",.008)
for x in (-1.225,.005,1.235):
    cube("Underside luminaires channel housing",(x,.011,2.533),(.958,.112,.042),dark,"roof",.007)
    cube("Under-canopy continuous frosted lens",(x,.008,2.509),(.886,.062,.013),diffusion,"roof",.005)

# A single readable numbered pickup marker, not a taxi-specific signpost.
sx,sy=-2.60,.295
cube("Bay marker pedestal foot",(sx,sy,.330),(.386,.304,.059),curb,"sign",.015)
cube("Square marker post",(sx,sy,1.242),(.100,.108,1.806),dark,"sign",.018)
cube("Slim marker projecting panel",(sx,sy-.065,1.821),(.432,.105,.875),dark,"sign",.041)
cube("Seamed teal front sign insert",(sx,sy-.124,1.823),(.370,.029,.811),teal,"sign",.028)
cube("Seafoam lower sign insert",(sx,sy-.141,1.533),(.312,.018,.132),accent,"sign",.016)
squared_pictogram(sx,sy-.144,2.129)
writing("Pickup sign bay label","BAY", (sx,sy-.148,2.001),.076,chalk,"sign")
writing("Large numbered bay marker","08", (sx,sy-.149,1.855),.228,chalk,"sign")
writing("Generic place descriptor on sign","PICKUP", (sx,sy-.148,1.676),.070,chalk,"sign")
writing("Waiting direction sign symbol",">", (sx,sy-.155,1.535),.108,dark,"sign")
cube("Marker short side reflective stripe",(sx+.218,sy-.061,1.503),(.012,.049,.151),chalk,"sign",.005)
for z in (1.514,2.109):
    cube("Plate back strap clamp",(sx,sy+.009,z),(.149,.040,.043),metal,"sign",.006)

# One low seating rail and three protective posts clear of the ramp and path.
for x in (-.990,.334):
    cube("Bench floor mounting shoe",(x,1.149,.320),(.168,.260,.030),metal,"amenity",.006)
    strip("Bench pedestal support",[(x,1.153,.333),(x,1.154,.736),(x,1.273,.830)],.075,teal,"amenity",.007)
    strip("Backrest structural rail",[(x,1.306,.727),(x,1.363,1.070)],.052,teal,"amenity",.007)
for i in range(4):
    cube("Replaceable timber seat slat",(-.324,.979+i*.097,.755),(1.779,.081,.062),teak,"amenity",.012)
for i in range(3):
    cube("Replaceable timber back slat",(-.324,1.339,.859+i*.082),(1.776,.052,.070),teak,"amenity",.011)
for x in (-2.10,-.572,2.092):
    cylinder("Edge protection post foot",(x,.064,.317),.074,.041,metal,"amenity",n=12)
    cylinder("Mist teal edge protection post",(x,.064,.573),.056,.498,teal,"amenity",n=12)
    cylinder("Contrasting protection marker ring",(x,.064,.741),.058,.039,line,"amenity",n=12)
    cylinder("Rounded top post cap",(x,.064,.829),.057,.024,accent,"amenity",n=12)
def aim(o, target):
    o.rotation_euler=(Vector(target)-o.location).to_track_quat("-Z","Y").to_euler()


cube("Studio floor",(0,0,-.029),(200,200,.045),material("Studio charcoal",(.042,.052,.053),.66),"studio")
bpy.ops.object.camera_add(location=(-6.75,-8.40,5.95))
camera=attach(bpy.context.object,"Frontal three-quarter studio camera","studio")
aim(camera,(0,-.28,1.02))
camera.data.type="ORTHO";camera.data.ortho_scale=8.45
scene.camera=camera
for name,pos,energy,color,size in (
    ("Warm key",(2.9,-3.7,5.1),880,(1,.89,.73),4.0),
    ("Cool window fill",(-3.5,-4.0,2.7),510,(.70,.87,1),4.0),
    ("Top perimeter rim",(3,2.7,4.2),745,(.77,.93,1),4.5),
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

# Non-rendering, named model-local interaction anchors for Gallery consumers.
# The GLB exporter converts Blender (X,Y,Z) into glTF (X,Z,-Y).
anchors=[]
anchor_collection=bpy.data.collections.new("08 Authored interaction anchors")
scene.collection.children.link(anchor_collection)
for name, xyz in [
    ("ANCHOR_PICKUP_B08", (-2.60,.146,1.855)),
    ("ANCHOR_VEHICLE_STOP", (0,-1.26,.177)),
    ("ANCHOR_BOARDING_POINT", (1.26,-.255,.177)),
]:
    o=bpy.data.objects.new(name,None)
    o.empty_display_type="PLAIN_AXES";o.empty_display_size=.13
    o.location=xyz
    anchor_collection.objects.link(o)
    anchors.append(o)

# Every authoring part remains separate and editable in the saved project.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"mall-ride-hail-pickup-bay.blend"))
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
for o in model_objects+anchors:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/"exports"/"mall-ride-hail-pickup-bay.glb"),
                         export_format="GLB",use_selection=True,export_animations=False,
                         export_cameras=False,export_lights=False,export_texcoords=False)
