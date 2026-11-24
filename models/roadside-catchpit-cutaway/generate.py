"""Original Singapore roadside stormwater catchpit demonstration section."""
import argparse
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector

parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
parser.add_argument('--review',type=Path)
parser.add_argument('--skip-render',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
out=args.output.resolve()
slug='roadside-catchpit-cutaway'
for n in ('exports','previews'):
    (out/n).mkdir(parents=True,exist_ok=True)
if args.review:
    args.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'

def collection(name):
    c=bpy.data.collections.new(name);scene.collection.children.link(c);return c

ground=collection('01 asphalt, pavement and section layers')
inlet=collection('02 road-edge grate and genuinely open stone throat')
pit=collection('03 sectioned solids, taper and sump')
outlet=collection('04 physically apertured side wall, joint and hollow outlet')
cues=collection('05 illustrative solid route cues')
studio=collection('06 studio; omitted from exported asset')
def material(name, hx, r, m=0):
    def linear(c):
        s = int(c, 16)/255
        return s/12.92 if s<=.04045 else ((s+.055)/1.055)**2.4
    col = tuple(linear(hx[i:i+2]) for i in (0,2,4))+(1,)
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = col
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = col
    bsdf.inputs['Roughness'].default_value = r
    bsdf.inputs['Metallic'].default_value = m
    return mat

def assign(o,n,c,p,mat=None):
    o.name=n
    if c not in list(o.users_collection):
        c.objects.link(o)
    for old in list(o.users_collection):
        if old != c:
            old.objects.unlink(o)
    o.parent=p
    if mat:
        o.data.materials.append(mat)
    return o

def empty(n,c,p=None,loc=(0,0,0)):
    o=bpy.data.objects.new(n,None)
    c.objects.link(o)
    o.parent=p
    o.location=loc
    o.empty_display_size=.036
    o.rotation_mode='QUATERNION'
    return o

def box(n,c,p,loc,d,mat,b=.003,seg=1):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o=bpy.context.object
    o.scale=d
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    assign(o,n,c,p,mat)
    o.location=loc
    if b:
        bv=o.modifiers.new('Rounded physical edges','BEVEL')
        bv.width=b
        bv.segments=seg
        wn=o.modifiers.new('Broad flat faces','WEIGHTED_NORMAL')
        wn.keep_sharp=True
    return o

def rod(n,c,p,a,b,r,mat,sides=12):
    a,b=Vector(a),Vector(b)
    d=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=r,depth=d.length)
    o=assign(bpy.context.object,n,c,p,mat)
    o.location=(a+b)/2
    o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    for face in o.data.polygons:
        face.use_smooth=len(face.vertices)==4
    return o

def mesh(n,c,p,v,f,mat):
    data=bpy.data.meshes.new(n)
    data.from_pydata(v,[],f)
    data.update()
    o=bpy.data.objects.new(n,data)
    return assign(o,n,c,p,mat)

def etch(n,c,p,o,text,size,mat):
    data=bpy.data.curves.new(n,'FONT'); data.body=text; data.align_x='CENTER';data.size=size
    ob=bpy.data.objects.new(n,data);assign(ob,n,c,p,mat);ob.location=o
    ob.rotation_euler.x=math.pi/2
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.object.convert(target='MESH')
    return ob

stone=material('Warm grey cast concrete', '989686', .77)
section=material('Pale concrete on exposed section', 'BFB39A', .81)
kerb=material('Grey-green weathered precast kerb', '92988B', .73)
mortar=material('Cool stamped concrete seam', '727B70', .82)
asphalt=material('Warm black slate asphalt', '484E4F', .88)
gutter=material('Cool dark asphalt at wall lip', '4D6063', .91)
grit1=material('Gravel quartz pale bits', 'B6AA8D', .91)
grit2=material('Gravel green grey pebbles', '757368', .93)
soil=material('Ochre sectioned fill', '9B7658', .92)
sub=material('Grey compacted sub-base', '6A6A61', .93)
paving=material('Pavement concrete', 'B3A88F', .86)
metal=material('Grey-green machined bar slot frame', '404A4A', .48, .43)
metal_light=material('Pale subtly worn galvanised bar edges', '77827E', .45, .42)
pipe=material('Warm grey precast outlet sleeve', 'A69E87', .73)
pipe_dark=material('Slate outlet inner wall material', '5E6B6A', .84)
stroke=material('Muted turquoise illustrative route arrows', '63AEB0', .58)
wet=material('Flat-teal illustrative sump water', '3C7479', .35)
white=material('Near white road-mark remainder', 'CFC5A6', .77)
plinth=material('Deep desaturated teal display base', '304844', .58)
shadow=material('Studio-only matte stone', '8D9A95', .84)
root=empty('ASSET_RoadsideCatchpitCutaway',ground)

def block(n,c,x0,x1,y0,y1,z0,z1,mat,b=.004,seg=1):
    return box(n,c,root,((x0+x1)*.5,(y0+y1)*.5,(z0+z1)*.5),(x1-x0,y1-y0,z1-z0),mat,b,seg)

def solid(n,c,v,f,materials,ids=None):
    g=mesh(n,c,root,v,f,materials[0])
    for mat in materials[1:]:
        g.data.materials.append(mat)
    if ids:
        for face,i in zip(g.data.polygons,ids):
            face.material_index=i
    return g

def wedge(n,c,x0,x1,y0,y1,z0,x0out,x1out,y0out,y1out,z1,mat):
    vs=[(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
        (x0out,y0out,z1),(x1out,y0out,z1),(x1out,y1out,z1),(x0out,y1out,z1)]
    fs=[(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
    return solid(n,c,vs,fs,[mat])

block('Presentation-section supporting slate base',ground,-1.116,1.113,-.614,.674,.006,.097,plinth,.024,3)
block('Dark plaque on cut edge',cues,-.958,-.438,-.616,-.607,.028,.075,metal,.004)
etch('Original cutaway plate title',cues,root,(-.697,-.617,.038),'STORMWATER  /  CUTAWAY',.022,white)

# Compact soil wings and granular layer, never blocking the sliced central chamber.
block('Left exposed earth section',ground,-1.045,-.820,-.437,.609,.099,.735,soil,.016,2)
block('Left compacted road aggregate',ground,-1.045,-.790,-.439,.620,.730,.874,sub,.008)
block('Far backed soil',ground,-.830,.506,.520,.617,.100,.786,soil,.014,2)
block('Far concrete backfill cap',ground,-.830,.506,.498,.633,.776,.889,sub,.007)
block('Right short warm soil section at pipe exit',ground,.250,.620,.250,.620,.101,.691,soil,.015,2)
block('Right short compacted fill layer',ground,.251,.622,.243,.625,.676,.869,sub,.010)
block('Right curb block substrate',ground,.233,.620,-.435,-.130,.560,.866,sub,.011)

# Split asphalt slabs form a real full-width apron opening toward the grated drop.
block('Roadway sliced to left of inlet',ground,-1.058,-.623,-.441,-.066,.868,.926,asphalt,.007,2)
block('Roadway sliced to right of inlet',ground,-.015,.724,-.442,-.067,.869,.926,asphalt,.007,2)
block('Asphalt cut lip ahead of grate',ground,-.623,-.015,-.441,-.321,.871,.923,asphalt,.006,2)
block('Dark left gutter shoulder',ground,-1.049,-.624,-.320,-.071,.924,.930,gutter,.002)
block('Dark right gutter shoulder',ground,-.018,.718,-.320,-.072,.924,.930,gutter,.002)
block('Subtle clipped road stripe remnant',ground,-1.039,-.829,-.416,-.390,.926,.928,white,.001)
# Raised pedestrian paving across the back; shallow chips split off the curb side.
for i,(x0,x1) in enumerate([(-1.048,-.659),(-.654,-.236),(-.230,.183),(.189,.622)]):
    block('Separated raised rear paver slab',ground,x0,x1,.265,.628,.969,1.036,paving,.008,2)
block('Raised rear footpath support shelf',ground,-1.047,.622,.269,.627,.887,.972,stone,.005)

# Real kerb opening: separated wings and lentil, open through Y toward the cut chamber.
block('Kerb inlet left cheek',inlet,-1.051,-.623,-.068,.092,.917,1.059,kerb,.011,3)
block('Kerb inlet right cheek',inlet,-.015,.621,-.068,.092,.918,1.059,kerb,.011,3)
block('Kerb lintel above the open throat',inlet,-.623,-.015,-.068,.103,1.012,1.059,kerb,.008,2)
block('Small rim collar at rear of throat',inlet,-.623,-.015,.246,.268,.916,1.038,mortar,.005)
block('Throat rear shelf',inlet,-.623,-.015,.104,.247,1.015,1.048,stone,.006)
# Left and right cheek edging enclose the narrow throat but its interior stays open.
block('Left open-throat lining',pit,-.659,-.623,.096,.265,.768,1.018,section,.004)
block('Right open-throat lining',pit,-.016,.018,.096,.265,.767,1.018,section,.004)

# The grate seats on a real metal perimeter. Nine bars transverse to roadway axis X.
for x in (-.607,-.031):
    block('Grate perimeter bearing end',inlet,x-.017,x+.017,-.326,-.066,.897,.930,metal,.003)
for y in (-.316,-.077):
    block('Grate perimeter bearing long rail',inlet,-.602,-.036,y-.013,y+.013,.895,.928,metal,.003)
for i in range(9):
    x=-.565+i*.0615
    block('Open grate crossbar',inlet,x-.0105,x+.0105,-.304,-.088,.908,.935,metal,.0033,2)
    block('Distinct crossbar soft top edge',inlet,x-.0078,x+.0078,-.281,-.109,.9348,.936,metal_light,.0006)
for x in (-.602,-.035):
    for y in (-.313,-.078):
        rod('Recessed grate frame pin',inlet,root,(x,y,.926),(x,y,.930),.006,metal_light,10)
# Cast inner wall and the two taper cheeks; chamber roof edges leave connected interior air.
block('Lower cast sump floor',pit,-.821,.260,-.431,.526,.101,.168,section,.011,2)
block('Left full-height cast retaining wall',pit,-.833,-.727,-.429,.491,.157,.824,stone,.009,2)
block('Rear chamber backing wall',pit,-.823,.254,.437,.525,.154,.893,stone,.010,2)
wedge('Left taper toward throat',pit,-.735,-.716,-.428,.452,.655,-.735,-.627,-.430,.444,.898,section)
wedge('Rear taper toward throat',pit,-.722,.224,.415,.447,.644,-.721,.231,.286,.449,.887,section)
wedge('Right taper over pipe chamber side',pit,.108,.245,-.426,.440,.680,-.011,.245,-.424,.435,.896,section)
block('Right sawn front edge',pit,.127,.249,-.433,-.393,.156,.687,section,.005)
block('Left sawn front edge',pit,-.827,-.721,-.435,-.398,.154,.664,section,.005)
block('Recessed pale rim below roadway front',pit,-.620,-.019,-.432,-.352,.833,.890,stone,.005)
block('Raised seam in left chamber',pit,-.727,-.722,-.363,.413,.417,.422,mortar,.001)
block('Raised seam in rear chamber',pit,-.718,.121,.435,.438,.411,.415,mortar,.001)

# Emphasize the lower collection bowl without obscuring the actual bore or throat.
block('Thin illustrative sump layer, below outlet invert',cues,-.709,.108,-.369,.413,.169,.175,wet,.012,3)
block('Section apex subtle submerged band',pit,-.708,.120,-.392,-.368,.168,.177,stone,.003)
for n,x,y in ((0,-.38,-.34),(1,-.19,-.34),(2,.00,-.34)):
    # Tiny blue flow guide marks in the demonstration, not visible from roads at scale.
    o=box('Route cue in sump pointing toward outlet',cues,root,(x,y-.029,.174),(.062,.010,.004),stroke,.001)
    o.rotation_euler.z=math.pi/4
    o=box('Route cue in sump pointing toward outlet',cues,root,(x,y+.009,.174),(.062,.010,.004),stroke,.001)
    o.rotation_euler.z=-math.pi/4
for x in (-.829,.439):
    box('Shallow runoff cue toward grate',cues,root,(x-.013,-.370,.930),(.042,.009,.003),stroke,.001).rotation_euler.z=(.62 if x<0 else -.62)
    box('Shallow runoff cue toward grate',cues,root,(x-.013,-.339,.930),(.042,.009,.003),stroke,.001).rotation_euler.z=(-.62 if x<0 else .62)
# A short engraved diagram on the non-functional cut face.
etch('Original inlet label on front cut edge',cues,root,(-.312,-.435,.844),'INLET',.025,white)

# Solid rectangular end wall with a genuinely open circular pass-through.
# Samples include every rectangle corner direction so the outer face is planar and complete.
cy,cz,ri=.063,.385,.126
Y0,Y1,Z0,Z1=-.415,.438,.165,.713
corner_angles=[math.atan2(z-cz,y-cy)%math.tau for y in (Y0,Y1) for z in (Z0,Z1)]
angles=sorted(set([round(math.tau*i/36,12) for i in range(36)]+[round(a,12) for a in corner_angles]))
l=len(angles)

def circle(x,r):
    return [(x,cy+r*math.cos(t),cz+r*math.sin(t)) for t in angles]

def rectangle(x):
    result=[]
    for t in angles:
        y,z=math.cos(t),math.sin(t)
        ys=((Y1 if y>0 else Y0)-cy)/y if abs(y)>1e-10 else math.inf
        zs=((Z1 if z>0 else Z0)-cz)/z if abs(z)>1e-10 else math.inf
        scale=min(ys,zs)
        result.append((x,cy+y*scale,cz+z*scale))
    return result

def ring_shell(n,c,v,materials):
    f=[];sel=[]
    for k in range(len(v)//l):
        q=(k+1)%(len(v)//l)
        for i in range(l):
            j=(i+1)%l
            f.append((k*l+i,k*l+j,q*l+j,q*l+i));sel.append(k%len(materials))
    return solid(n,c,v,f,materials,sel)

w=ring_shell('OUTLET_PASS_THROUGH_WALL',outlet,
           rectangle(.108)+rectangle(.238)+circle(.238,ri)+circle(.108,ri),[section,stone,pipe_dark,section])
pipe_obj=ring_shell('OUTLET_HOLLOW_PIPE',outlet,
                    circle(.238,.163)+circle(.765,.163)+circle(.806,.151)+circle(.806,ri)+circle(.238,ri),
                    [pipe,pipe,section,pipe_dark,pipe])
for f in pipe_obj.data.polygons:
    if f.material_index in (0,1,3):
        f.use_smooth=True
ring_shell('Visible outer compression joint collar',outlet,
           circle(.251,.174)+circle(.323,.174)+circle(.323,.163)+circle(.251,.163),[pipe,kerb,pipe_dark,mortar])
# Simple exposed cut edge shadows; no end plate across the pipe bore.
ring_shell('Outlet terminal edge band with open centre',outlet,
           circle(.771,.158)+circle(.806,.152)+circle(.806,ri+.0004)+circle(.771,ri+.0004),
           [mortar,section,pipe_dark,pipe])
block('Pipe saddle display support below bore',outlet,.366,.626,-.072,.201,.101,.227,stone,.008,2)
etch('Outlet label on separate showpiece soil ledge',cues,root,(.468,-.438,.564),'OUTLET',.026,white)
# Sparse surface aggregate is original geometry, only on the sawn earth face.
rng=random.Random(733)
for k,sector in enumerate([(-1.002,-.856,-.435,.158,.692),(.267,.578,-.436,.589,.802)]):
    x0,x1,y,z0,z1=sector
    v=[];f=[];ids=[]
    for _ in range(66 if k==0 else 36):
        x=rng.uniform(x0,x1);z=rng.uniform(z0,z1);rad=rng.uniform(.0025,.008)
        y0=y-rng.uniform(.001,.004)
        sides=rng.choice((3,4,5));start=len(v); angle=rng.uniform(0,math.tau)
        for j in range(sides):
            t=angle+j*math.tau/sides;scale=rng.uniform(.78,1.2)
            v.append((x+rad*scale*math.cos(t),y0,z+rad*scale*.71*math.sin(t)))
        f.append(tuple(range(start,start+sides)));ids.append(rng.randint(0,1))
    solid('Original mineral flecks on cut soil face',ground,v,f,[grit1,grit2],ids)
# Two restrained leaf-bottom shapes on intact exterior road, safely away from the grate.
for x,y,theta in ((.612,-.387,.8),(-.906,-.310,-.5)):
    q=[(-.016,0),(-.005,-.008),(.014,-.004),(.027,.002),(.009,.009),(-.005,.007)]
    v=[(x+a*math.cos(theta)-b*math.sin(theta),y+a*math.sin(theta)+b*math.cos(theta),.9306) for a,b in q]
    v.append((x+.004,y,.933))
    solid('Dry roadside leaf portion',ground,v,[(i,(i+1)%6,6) for i in range(6)],[soil,grit1],[0,0,0,1,1,1])

box('Studio shadow surface',studio,None,(0,0,-.025),(200,200,.048),shadow,0)
def look(o,t):
    o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,c,power,size,color):
    m=bpy.data.lights.new(n,'AREA');m.energy=power;m.size=size;m.shape='DISK';m.color=color
    o=bpy.data.objects.new(n,m);studio.objects.link(o);o.location=c;look(o,(0,0,.59))
lamp('Broad warm daylight key',(-2.2,-3.6,4.1),448,3.15,(1,.91,.79))
lamp('Soft section interior fill',(2.6,-3.2,1.83),194,2.3,(.86,.97,1))
lamp('Pale upper plane separation',(.50,1.86,3.65),258,2.2,(.88,.97,1))
world=bpy.data.worlds.new('Neutral overcast daylight');world.use_nodes=True
scene.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.57,.68,.66,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.50
lens=bpy.data.cameras.new('Asset studio');cam=bpy.data.objects.new('Asset studio',lens);studio.objects.link(cam)
scene.camera=cam;lens.type='ORTHO';lens.ortho_scale=2.66
cam.location=(3.50,-6.5,3.18);look(cam,(-.075,.042,.535))
scene.render.engine='CYCLES';scene.cycles.samples=40;scene.cycles.use_denoising=sys.platform=='darwin'
scene.render.threads_mode='FIXED';scene.render.threads=5
scene.render.resolution_x=scene.render.resolution_y=512
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='WEBP';scene.render.image_settings.quality=92
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.12
scene.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True)

# Export before optional renders: camera, lights and studio surface are never in the GLB.
for c in (ground,inlet,pit,outlet,cues):
    for o in c.objects:
        o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/f'{slug}.glb'),export_format='GLB',use_selection=True,
                         export_texcoords=False,export_animations=False,export_cameras=False,export_lights=False,export_extras=False)
def still(to,pos,target,scale,res):
    cam.location=pos; look(cam,target); lens.ortho_scale=scale
    scene.render.resolution_x,scene.render.resolution_y=res;scene.render.filepath=str(to)
    bpy.ops.render.render(write_still=True)
if not args.skip_render:
    still(out/'previews/studio.webp',(3.50,-6.5,3.18),(-.075,.042,.535),2.66,(512,512))
if args.review:
    still(args.review/'inlet-and-open-grate.webp',(.5,-4.72,4.03),(-.279,-.043,.869),1.57,(792,540))
    still(args.review/'outlet-and-sump-section.webp',(4.35,-4.85,1.93),(-.038,-.048,.522),2.42,(820,520))
    still(args.review/'right-bank-bore.webp',(4.82,-2.50,1.61),(.516,.065,.539),1.38,(748,530))
