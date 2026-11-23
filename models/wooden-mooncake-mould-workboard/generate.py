"""Build editable original Mid-Autumn hand-mould still life. Blender 4.3+/5.x."""
import argparse
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

SLUG = "wooden-mooncake-mould-workboard"
N, RINGS = 160, 22
PI, TAU = math.pi, math.tau
random.seed(836)
parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
parser.add_argument("--detail", type=Path)
parser.add_argument("--no-render", action="store_true")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
root = args.output.resolve()
for d in ("exports", "previews"):
    (root / d).mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
asset = bpy.data.collections.new("ASSET | mooncake mould workboard")
scene.collection.children.link(asset)

def linear(t):
    return t / 12.92 if t < .04045 else ((t + .055) / 1.055)**2.4

def material(name, hexc, rough=.49, metal=0):
    rgb = [linear(int(hexc[i:i+2],16)/255) for i in (0,2,4)]
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    p = mat.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = mat.diffuse_color
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    return mat

honey = material("Oiled rubberwood | workboard face", "B88752",.53)
edge = material("Oiled rubberwood | softened end grain", "8A5731",.60)
boardgrain = material("Rubberwood | light honey grain", "AF7C47",.56)
boardgrain2 = material("Rubberwood | darker grain", "9F6F43",.57)
wood = material("Old hardwood | dark crimson brown", "634027",.48)
mouldlip = material("Old hardwood | burnished rim", "75482B",.46)
well = material("Old hardwood | exposed carving", "6B4229",.54)
mouldgrain = material("Old hardwood | fine end grain", "7C5637",.54)
mouldgrain2 = material("Old hardwood | thin grain lines", "66422A",.52)
cake = material("Pastry | honey brown gloss", "BB6E20",.37)
cakeedge = material("Pastry | dark baked fluting", "93521D",.46)
cakebottom = material("Pastry | baked base", "874C23",.52)
cotton = material("Cotton | dusty warm-white", "D9CAAF",.78)
stripe = material("Cotton | woven indigo", "567278",.80)
brush = material("Bamboo | dust brush handle", "D4A466",.53)
band = material("Brushed brass | ferrule", "AD8A52",.42,.48)
fibre = material("Bristles | natural pale strands", "F2D9A3",.76)
fibre2 = material("Bristles | shadow tone", "C5A86D",.77)
cord = material("Cotton | binding cord", "915732",.74)

def in_asset(o):
    for coll in list(o.users_collection):
        coll.objects.unlink(o)
    asset.objects.link(o)
    return o

def group(name, loc=(0,0,0), angle=0):
    o = bpy.data.objects.new(name, None)
    asset.objects.link(o)
    o.location = loc
    o.rotation_euler.z = math.radians(angle)
    o.empty_display_size = .023
    return o

def mesh(name, verts, faces, mats, mids=None, smooth=False, parent=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts,[],faces)
    me.update()
    obj = bpy.data.objects.new(name,me)
    asset.objects.link(obj)
    obj.parent = parent
    for m in mats:
        me.materials.append(m)
    for i, p in enumerate(me.polygons):
        p.material_index = mids[i] if mids is not None else 0
        p.use_smooth = smooth
    return obj

def box(name, loc, dims, radius, mat, parent=None, second=None, angle=0):
    bpy.ops.mesh.primitive_cube_add()
    o = in_asset(bpy.context.object)
    o.name = name
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.parent = parent
    o.location = loc
    o.rotation_euler.z = math.radians(angle)
    o.data.materials.append(mat)
    if second:
        o.data.materials.append(second)
        for p in o.data.polygons:
            if abs(p.normal.z) < .4: p.material_index = 1
    b=o.modifiers.new("Soft finished edges","BEVEL")
    b.width=radius; b.segments=3
    h=o.modifiers.new("Weighted face normals","WEIGHTED_NORMAL")
    h.keep_sharp=True
    return o

def tube(name, points, bevel, mat, parent=None, resolution=2):
    cu = bpy.data.curves.new(name,"CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = bevel
    cu.bevel_resolution = resolution
    cu.use_fill_caps = True
    s=cu.splines.new("POLY"); s.points.add(len(points)-1)
    for p, v in zip(s.points,points):
        p.co = (*v,1)
    obj=bpy.data.objects.new(name,cu);asset.objects.link(obj)
    obj.parent=parent;cu.materials.append(mat)
    return obj

def quads_loop(faces, mids, a, b, count, mat):
    for j in range(count):
        k=(j+1)%count
        faces.append((a+j,a+k,b+k,b+j))
        mids.append(mat)

def grain(name, items, materials, parent):
    vs, fs, m = [], [], []
    for points, w, index in items:
        start=len(vs)
        for x,y,z in points:
            vs.extend(((x,y-w/2,z),(x,y+w/2,z)))
        for i in range(len(points)-1):
            j=start+2*i
            fs.append((j,j+2,j+3,j+1));m.append(index)
    return mesh(name,vs,fs,materials,m,parent=parent)

board = group("WORKBOARD | oiled timber")
box("Rounded workboard, long grain", (0,0,.018),(.660,.430,.028),.011,honey,board,edge)
lines=[]
for i in range(53):
    x0=random.uniform(-.31,.12)
    length=random.uniform(.028,.48)
    end=min(.315,x0+length)
    y0=random.uniform(-.195,.195)
    w=random.uniform(.00025,.00115)
    phase=random.uniform(0,7)
    points=[]
    for j in range(16):
        u=j/15; x=x0+(end-x0)*u
        y=y0+.0015*math.sin(x*26+phase)+.0008*math.sin(x*57+phase)
        points.append((x,y,.03216+.00004*(i%3)))
    lines.append((points,w,int(i%7==0)))
grain("Timber streaks, lengthwise",lines,[boardgrain,boardgrain2],board)

outline=[(.095,0),(.093,.032),(.085,.055),(.070,.075),(.052,.089),(.027,.096),(-.001,.097),(-.031,.094),
         (-.055,.083),(-.074,.067),(-.087,.046),(-.105,.032),(-.128,.024),(-.164,.021),
         (-.198,.022),(-.231,.027),(-.253,.028),(-.267,.022),(-.273,.011),(-.275,0)]
outline+= [(x,-y) for x,y in reversed(outline[1:-1])]
def cross(a,b):
    return a[0]*b[1]-a[1]*b[0]
def rim(t):
    u=math.cos(t),math.sin(t)
    for a,b in zip(outline,outline[1:]+outline[:1]):
        v=b[0]-a[0],b[1]-a[1]
        cv=cross(u,v)
        if abs(cv)<1e-9: continue
        scale,h=cross(a,v)/cv,cross(a,u)/cv
        if scale>0 and -1e-8<=h<=1+1e-8: return scale
    raise ValueError(t)

def hrad(t):
    return .0648 + .00205*math.cos(20*t)

def peaked(distance,width):
    t=max(0,1-min(distance/width,1)**2)
    return t*t

def sdseg(x,y,ax,ay,bx,by):
    vx,vy=bx-ax,by-ay
    u=max(0,min(1,((x-ax)*vx+(y-ay)*vy)/(vx*vx+vy*vy)))
    return math.hypot(x-(ax+u*vx),y-(ay+u*vy))

# The asymmetric crescent and two seeds make the X mirror measurable.
# The rose is original: not a replica, character, or licensed maker's emblem.
def relief(x,y):
    r=math.hypot(x,y)
    a=math.atan2(y,x)
    ring=.71*peaked(abs(r-.803),.052)
    petals=.92*peaked(abs(r-(.455+.179*math.cos(8*a))),.076)
    petals*=min(1,max(0,(r-.20)/.09))
    outer=.181-math.hypot(x+.073,y-.005)
    cut=math.hypot(x-.033,y-.062)-.158
    weight=min(1,max(0,min(outer,cut)/.043))
    cres=.93*(weight*weight*(3-2*weight))
    seed1=.77*peaked(math.hypot(x-.132,y-.055),.067)
    seed2=.57*peaked(math.hypot(x-.172,y+.067),.059)
    return max(ring,petals,cres,seed1,seed2)

angles=[TAU*i/N for i in range(N)]
mould = group("HAND MOULD | carved negative",(-.052,.057,.034),22)
dough = group("STAMPED CAKE | mirrored positive",(.166,-.080,.033),-9)

def tool():
    vs,fs,mids=[],[],[]
    def add(fn):
        vs.extend(fn(t) for t in angles)
    # Rings progress CCW, bottom-centre -> exterior -> lip -> actual well.
    # Surface bands and anti-clockwise top have outward winding across the closed solid.
    for z,inset in [(0,.0022),(.0018,.0008),(.0053,0),(.037,0),(.0416,.0008),(.0431,.0024)]:
        add(lambda a,z=z,i=inset: ((rim(a)-i)*math.cos(a),(rim(a)-i)*math.sin(a),z))
    for mix,zi in [(0.31,.0454),(.68,.0448),(.88,.0440),(.96,.0438),(1,.0424)]:
        add(lambda a,m=mix,z=zi: ((m*hrad(a)+(1-m)*(rim(a)-.0024))*math.cos(a),(m*hrad(a)+(1-m)*(rim(a)-.0024))*math.sin(a),z))
    for factor,zi in [(.999,.0398),(.987,.033),(.964,.0204),(.934,.0183)]:
        add(lambda a,k=factor,z=zi: (k*hrad(a)*math.cos(a),k*hrad(a)*math.sin(a),z))
    # Sculpt the bottom as negative relief, not an overlay or painted recess.
    for j in range(RINGS,0,-1):
        u=(j-1)/RINGS + 0.014
        add(lambda a,u=u: (.931*hrad(a)*u*math.cos(a),.931*hrad(a)*u*math.sin(a),
                             .01815-.00445*relief(u*math.cos(a),u*math.sin(a))))
    cy=len(vs);vs.append((0,0,.01815-.00445*relief(0,0)))
    fs.append(tuple(reversed(range(N))));mids.append(0)
    for j in range((len(vs)-1)//N-1):
        m=0 if j<5 else 1 if j<10 else 2
        quads_loop(fs,mids,j*N,(j+1)*N,N,m)
    last=cy-N
    for k in range(N):
        fs.append((last+k,last+(k+1)%N,cy));mids.append(2)
    return mesh("Hardwood body with scalloped wall and carved motif",vs,fs,[wood,mouldlip,well],mids,True,mould)

def baked():
    vs,fs,mids=[],[],[]
    def add(fn):
        vs.extend(fn(t) for t in angles)
    # Piece stands outside mould; all sample coords map across X in the top ring.
    for s,z in [(.87,0),(.939,.002),(.986,.006),(.99,.023),(.98,.028),(.948,.0307),(.934,.0314)]:
        add(lambda a,k=s,z=z: (k*hrad(a)*math.cos(a),k*hrad(a)*math.sin(a),z))
    for j in range(RINGS,0,-1):
        u=(j-1)/RINGS+0.014
        add(lambda a,u=u: (.931*hrad(a)*u*math.cos(a),.931*hrad(a)*u*math.sin(a),
                            .03155+.00445*relief(-u*math.cos(a),u*math.sin(a))))
    cy=len(vs);vs.append((0,0,.03155+.00445*relief(0,0)))
    fs.append(tuple(reversed(range(N))));mids.append(2)
    for j in range((len(vs)-1)//N-1):
        m=1 if j<4 else 0
        quads_loop(fs,mids,j*N,(j+1)*N,N,m)
    last=cy-N
    for k in range(N):
        fs.append((last+k,last+(k+1)%N,cy));mids.append(0)
    return mesh("Fluted pastry with X-mirrored raised blossom and crescent",vs,fs,[cake,cakeedge,cakebottom],mids,True,dough)

negative=tool()
positive=baked()
negative["carving_depth_m"]=.00445
positive["mirrors_original_mould_about"]="local X"
# Use grain strips just above the wood lip only where the left handle is flat and safe.
lines=[]
for j in range(15):
    y0=random.uniform(-.013,.013)
    x0=random.uniform(-.246,-.186)
    x1=random.uniform(-.183,-.122)
    pts=[]
    for i in range(13):
        t=i/12
        x=x0+t*(x1-x0)
        y=y0+.0009*math.sin(x*77+j)
        a=math.atan2(y,x); rr=math.hypot(x,y)
        m=(rim(a)-.0024-rr)/(rim(a)-.0024-hrad(a))
        zz=.0431+min(max(m,0),.31)*(.0454-.0431)/.31
        if m>.31: zz=.0454+min((m-.31)/.37,1)*(.0448-.0454)
        pts.append((x,y,zz+.00028))
    lines.append((pts,random.uniform(.00023,.00058),j%2))
grain("Burnished handle, short open grain",lines,[mouldgrain,mouldgrain2],mould)

def simple_lathe(name,parent,pairs,mats,theta=24):
    # Sweep circular sections along custom local +X longitudinal handle axis.
    verts,faces,mi=[],[],[]
    for x,r,tag in pairs:
        verts.extend((x,r*math.cos(TAU*i/theta),r*math.sin(TAU*i/theta)) for i in range(theta))
    faces.append(tuple(range(theta)));mi.append(pairs[0][2])
    for j in range(len(pairs)-1):
        quads_loop(faces,mi,(j+1)*theta,j*theta,theta,pairs[j][2])
    last=(len(pairs)-1)*theta
    faces.append(tuple(reversed(range(last,last+theta))));mi.append(pairs[-1][2])
    return mesh(name,verts,faces,mats,mi,True,parent)

wrap=group("COTTON | folded work cloth",(.177,.121,.033),-11)
def cloth_z(x,y):
    return .007 + .0022*math.cos((x+.02)*73+y*19)+.0011*math.sin(y*49-x*7)
vw=[];fw=[];mw=[]
nx,ny=20,16
for layer in range(2):
    for i in range(nx+1):
        u=i/nx; x=(u-.5)*.154
        for j in range(ny+1):
            v=j/ny; y=(v-.5)*.104 + .0020*math.sin(u*PI*3)*(2*v-1)
            vw.append((x,y,cloth_z(x,y)-layer*.005))
s=(nx+1)*(ny+1)
for layer in range(2):
    for i in range(nx):
        for j in range(ny):
            k=layer*s+i*(ny+1)+j
            f=(k,k+ny+1,k+ny+2,k+1)
            fw.append(f if not layer else f[::-1]);mw.append(int(j in {2,4,ny-3}))
loop=list(range(ny+1))+[i*(ny+1)+ny for i in range(1,nx+1)]+[nx*(ny+1)+j for j in range(ny-1,-1,-1)]+[i*(ny+1) for i in range(nx-1,0,-1)]
for a,b in zip(loop,loop[1:]+loop[:1]):
    fw.append((b,a,a+s,b+s));mw.append(0)
mesh("Layered cotton with indigo woven bands",vw,fw,[cotton,stripe],mw,True,wrap)
brushgroup=group("DUST BRUSH | bamboo and straw",(.191,.120,.053),-24)
simple_lathe("Turned bamboo shaft and brass binding",brushgroup,
              [(-.097,.004,0),(-.093,.007,0),(-.081,.0075,0),(-.059,.0071,0),
               (-.025,.0059,0),(.005,.0050,0),(.024,.0063,0),(.031,.0074,2),
               (.033,.0080,1),(.045,.0098,1),(.047,.0098,1),(.048,.0094,1)], [brush,band,cord])
# Flat bundle comprises separately tinted physical tapered fibres, grouped into one mesh.
vs=[];fs=[];mi=[]
for j in range(31):
    y=random.uniform(-.011,.011); z=random.uniform(-.005,.005)
    extent=random.uniform(.028,.038)
    lateral=random.uniform(-.002,.002)
    start=len(vs)
    levels=[(.047,y*.62,z*.79,.00148),(.052,y*.84,z*.94,.00150),
            (.047+extent*.64,y+lateral*.65,z*.74,.00107),
            (.047+extent,y+lateral,z*.60-.002,.00043)]
    for xx,yy,zz,r in levels:
        vs.extend((xx,yy+r*math.cos(TAU*k/5),zz+r*math.sin(TAU*k/5)) for k in range(5))
    for k in range(3):
        quads_loop(fs,mi,start+(k+1)*5,start+k*5,5,int(j%6==0))
    fs.append(tuple(start+15+k for k in range(5)));mi.append(int(j%6==0))
mesh("Thirty-one tapered pale brush fibres",vs,fs,[fibre,fibre2],mi,True,brushgroup)

# Export the asset collection only; removable camera, lights and floor stay in .blend.
stage = bpy.data.collections.new("STUDIO | lights and floor (not exported)")
scene.collection.children.link(stage)
def in_studio(o):
    for c in list(o.users_collection): c.objects.unlink(o)
    stage.objects.link(o);return o

def point(o, target):
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()

floor=material("Studio | muted slate floor","405557",.78)
bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,.002))
ground=in_studio(bpy.context.object);ground.name="Studio contact-shadow floor; outside export"
ground.data.materials.append(floor)
world=bpy.data.worlds.new("Diffuse daylight");scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.43,.49,.53,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.31

def area(name,loc,dest,power,size,color):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color
    o=bpy.data.objects.new(name,d);stage.objects.link(o);o.location=loc;point(o,dest)
area('Soft main',(-.42,-.88,1.12),(-.08,.02,.04),16,.64,(1,.86,.70))
area('Raking light to read relief',(.62,-.21,.36),(-.05,.05,.06),8,.37,(.88,.94,1))
area('Overhead warm bounce',(.03,.69,.88),(.08,.05,.05),11,.52,(1,.91,.72))
area('Low cool fill',(-.69,.53,.40),(-.05,.045,.04),3,.50,(.75,.88,1))

camera=bpy.data.cameras.new('Studio camera')
o=bpy.data.objects.new('Studio camera',camera);stage.objects.link(o);scene.camera=o
o.location=(.55,-.76,1.04);point(o,(0,.0,.030))
camera.type='ORTHO';camera.ortho_scale=.825
camera.lens=55
scene.render.engine='CYCLES'
scene.cycles.samples=64
scene.cycles.use_denoising=(sys.platform == 'darwin')
scene.view_settings.view_transform='AgX'
scene.render.resolution_x=512;scene.render.resolution_y=512;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='WEBP'
scene.render.image_settings.quality=92
scene.render.filepath='//previews/studio.webp'
scene.render.film_transparent=False
scene.render.threads_mode='FIXED';scene.render.threads=6

bpy.ops.object.select_all(action="DESELECT")
for obj in asset.objects: obj.select_set(True)
bpy.context.view_layer.objects.active=negative
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(root/(SLUG+".blend")),compress=True)
bpy.ops.export_scene.gltf(
    filepath=str(root/"exports"/(SLUG+".glb")),
    export_format='GLB',use_selection=True,export_extras=False,export_yup=True,
    export_animations=False,export_apply=True,export_texcoords=False)
if not args.no_render:
    scene.render.filepath=str(root/"previews"/"studio.webp")
    bpy.ops.render.render(write_still=True)
if args.detail:
    scene.render.resolution_x=840;scene.render.resolution_y=640
    camera.ortho_scale=.484
    o.location=(.05,-.44,1.11);point(o,(.025,.024,.062))
    scene.render.filepath=str(args.detail.resolve())
    bpy.ops.render.render(write_still=True)
