"""Original static Sarawak Iban backstrap loom display; not a named artifact or instruction."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
opts=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='sarawak-iban-backstrap-loom-display'
out=opts.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if opts.review:opts.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
base=collection('01 contrasting museum exhibit supports')
last=collection('02 independent tension loom beams and heddle')
loose=collection('03 genuine yarn lanes and resting backstrap')
studio=collection('04 studio only; excluded from export')
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

def sweep(n,c,p,coords,r,mat,sides=7,closed=False):
    points=[Vector(k) for k in coords]
    v=[]; f=[]; L=len(points)
    for i,q in enumerate(points):
        t=(points[(i+1)%L] if i<L-1 or closed else q)-(points[i-1] if i or closed else q)
        t.normalize()
        u=t.cross(Vector((0,1,0))).normalized()
        if not u.length:
            u=t.cross(Vector((1,0,0))).normalized()
        w=t.cross(u)
        for k in range(sides):
            theta=k*math.tau/sides
            v.append(q+r*(u*math.cos(theta)+w*math.sin(theta)))
    for i in range(L if closed else L-1):
        j=(i+1)%L
        for k in range(sides):
            l=(k+1)%sides
            f.append((i*sides+k,i*sides+l,j*sides+l,j*sides+k))
    if not closed:
        f.extend([tuple(reversed(range(sides))),tuple(range((L-1)*sides,L*sides))])
    o=mesh(n,c,p,v,f,mat)
    for face in o.data.polygons:
        face.use_smooth=len(face.vertices)==4
    return o

def etch(n,c,p,o,text,size,mat):
    data=bpy.data.curves.new(n,'FONT'); data.body=text; data.align_x='CENTER';data.size=size
    ob=bpy.data.objects.new(n,data);assign(ob,n,c,p,mat);ob.location=o
    ob.rotation_euler.x=math.pi/2
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.object.convert(target='MESH')
    return ob


def linear(x):
    x=max(0,min(255,x))/255
    return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4
def vmat(n,rough,metal=0):
    m=material(n,'FFFFFF',rough,metal)
    v=m.node_tree.nodes.new('ShaderNodeVertexColor');v.layer_name='Procedural surface grain'
    m.node_tree.links.new(v.outputs['Color'],m.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    return m
def apply_color(o,fn):
    c=o.data.color_attributes.new(name='Procedural surface grain',type='FLOAT_COLOR',domain='POINT')
    for v,x in zip(o.data.vertices,c.data):x.color=tuple(linear(k) for k in fn(v.co))+(1,)
def multi(n,c,r,v,f,m,ids,smooth=False):
    o=mesh(n,c,r,v,f,m[0])
    for mat in m[1:]:o.data.materials.append(mat)
    for p,k in zip(o.data.polygons,ids):p.material_index=k;p.use_smooth=smooth and len(p.vertices)==4
    return o
def colored_board(n,c,r,p,d,mat,hue):
    o=box(n,c,r,p,d,mat,.0068,3)
    bpy.context.view_layer.update();bpy.context.view_layer.objects.active=o
    for mod in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
    apply_color(o,lambda v: tuple(k*(1+.065*math.sin(v.y*99+v.x*9)+.045*math.sin(v.y*186+v.z*5)+.042*math.cos(v.x*21+v.y*50)) for k in hue))
    return o
wood=vmat('Mellow tropical hardwood, original grain',.61)
woodLight=vmat('Worn lighter wooden battens',.54)
stone=material('Museum base warm slate','3F5150',.74)
grey=material('Contemporary muted blue steel supports','557276',.56,.30)
pads=material('Neutral soft saddles for display only','87928B',.77)
metal=material('Modern dark-blue fitting ends','3A5055',.45,.44)
warm=material('Quiet natural webbing edge','BB9D5F',.86)
strapM=material('Chestnut open display strap','80563D',.83)
stitch=material('Short muted backstrap thread tack','D6AC71',.83)
yarn=[
 material('Natural cream warp yarn','D2BB8D',.83),
 material('Original brick warp yarn','A24E3F',.83),
 material('Original muted plum yarn','573942',.83),
 material('Original dark indigo warp yarn','394556',.83),
 material('Soft warm grey shading yarn','9C8B76',.83)]
cord=material('Natural off-white heddle and breast ties','DACEA5',.80)
etchM=material('Museum caption lettering','DBD4B7',.85)

root=empty('SARAWAK_IBAN_BACKSTRAP_LOOM_EXHIBIT',base)
supports=empty('INDEPENDENT_CONTEMPORARY_EXHIBITION_SUPPORTS',base,root)
beamGroup=empty('TRADITIONAL_TYPE_WOODEN_BEAMS_AND_BARS',last,root)
woven=empty('INDIVIDUALLY_MODELED_INTERLACED_WARP_AND_WEFT',loose,root)
ties=empty('HEDDLE_LOOPS_AND_BREAST_BEAM_BACKSTRAP_TIES',loose,root)
strapGroup=empty('INDEPENDENT_RESTING_OPEN_BACKSTRAP',loose,root)
def wood_timber(n,loc,d,col):
    return colored_board(n,last,beamGroup,loc,d,wood,col)
def crossbar(n,y,z,radius,span,hue):
    o=rod(n,last,beamGroup,(-span/2,y,z),(span/2,y,z),radius,woodLight,24)
    apply_color(o,lambda v:tuple(k*(1+.035*math.sin(v.z*112+v.x*25)+.028*math.cos(v.z*62+v.y*21)) for k in hue))
    return o

box('Textured display plinth, clearly not a loom frame',base,supports,(0,-.021,.032),(.91,1.26,.064),stone,.014,3)
# Exhibition rests are deliberately freestanding, blue-grey at the four corners.
near=-.368;far=.368; zh=.306;zf=.330
for side in (-1,1):
    for y,z,rad,word in [(near,zh,.027,'front'),(far,zf,.027,'rear')]:
        x=side*.323
        box('Independent '+word+' display foot',base,supports,(x,y,.076),(.095,.100,.026),grey,.009,2)
        box('Independent '+word+' exhibit upright',base,supports,(x,y,(z+.045)/2),(.032,.035,z-.129),grey,.005,2)
        box('Compliant '+word+' support saddle under beam',base,supports,(x,y,z-rad-.008),(.053,.081,.017),pads,.005,3)
        for q in [-1,1]:
            box('Short upward side keeper, separate from loom',base,supports,(x,y+q*(rad+.007),z-rad+.003),(.053,.013,.024),grey,.004,2)
for x in [-.236,.236]:
    box('Low independent strap rest stop',base,supports,(x,-.536,.112),(.048,.075,.096),grey,.007,2)
    box('Strap rest foot pad',base,supports,(x,-.536,.075),(.082,.103,.022),grey,.008,2)
seat=box('Independent lower padded display strap rest',base,supports,(0,-.541,.14997),(.54,.091,.031),pads,.012,3)
seat.rotation_euler.x=math.atan(.006/.034)

rb=.027
crossbar('Wood breast beam with individually rounded edges',near,zh,rb,.704,[153,105,59])
crossbar('Wood warp beam, rear anchor',far,zf,rb,.704,[137,90,49])
crossbar('Raised hardwood heddle rod',.033,.411,.010,.574,[169,114,65])
crossbar('First slender wooden crosspiece',.169,.344,.008,.580,[177,127,73])
crossbar('Second slender wooden crosspiece',.220,.346,.008,.580,[172,121,70])
o=wood_timber('Distinct bevel-edged beater resting beside swatch',(.321,-.117,.070),(.036,.243,.012),[157,104,59])
o.rotation_euler.z=.14
for x in [.295,-.292]:
    box('Narrow side holder for raised heddle exhibit',base,supports,(x,.033,.371),(.027,.036,.071),grey,.005,2)
    box('Display pedestal for heddle side holder',base,supports,(x,.034,.201),(.021,.023,.280),grey,.004,2)

# Unambiguously separate warp and weft meshes. Alternate surfaces at each real
# intersection with space between the solids and preserve each continuous strand.
nx=36; ny=21
xs=[-.221+(i+.5)*(.442/nx) for i in range(nx)]
ys=[-.321+i*.0105 for i in range(ny)]
rwarp=.00185; rweft=.00185; sep=.0028
h=lambda y:.338+(y-near)*(.020/(far-near))
parity=lambda j,i: 1 if (j+i)%2==0 else -1
kWarp=lambda i: 0 if i in (0,1,34,35,8,9,26,27) else 3 if i in (2,3,32,33,16,17,18,19) else 1 if i in (4,5,6,7,28,29,30,31,12,13,22,23) else 2
kWeft=lambda j: 0 if j in (0,1,19,20) else 1 if j in (6,7,8,14,15) else 4
def arc_x(x,y,z,deg0,deg1,rr,n=7):
    ang=[math.radians(deg0+(deg1-deg0)*i/n) for i in range(n+1)]
    return [(x,y+rr*math.cos(a),z+rr*math.sin(a)) for a in ang]
def warpPath(i):
    x=xs[i]
    wovenPath=[(x,y,h(y)+sep*parity(j,i)) for j,y in enumerate(ys)]
    row=1 if i%2==0 else -1
    shed=[(x,-.070,h(-.070)+row*.009),(x,.033,.357+row*.021),(x,.126,.351+row*.013),
          (x,.156,.344+row*.01025),(x,.169,.344+row*.01025),(x,.182,.344+row*.01025),
          (x,.207,.346-row*.01025),(x,.220,.346-row*.01025),(x,.233,.346-row*.01025),
          (x,.283,.354+row*.012),(x,far-.036,zf+rb+rwarp+.001)]
    return arc_x(x,near,zh,255,90,rb+rwarp+.00072)+wovenPath+shed+arc_x(x,far,zf,90,-75,rb+rwarp+.00072)
def weftPath(j):
    y=ys[j]
    pts=[(x,y,h(y)-sep*parity(j,i)) for i,x in enumerate(xs)]
    return [(-.226,y,h(y)-sep*parity(j,0))]+pts+[(.226,y,h(y)-sep*parity(j,nx-1))]
# Keep each continuous strand as its own node for editable proof; use modest
# radial segmentation and no embedded texture to retain real browser geometry.
for i in range(nx):
    sweep(f'Continuous warp thread {i+1:02d}',loose,woven,warpPath(i),rwarp,yarn[kWarp(i)],6)
for j in range(ny):
    sweep(f'Alternating solid weft course {j+1:02d}',loose,woven,weftPath(j),rweft,yarn[kWeft(j)],6)
for i in range(0,nx,2):
    x=xs[i]
    yy=.033
    points=[(x-.0037,yy,.381),(x-.0037,yy-.008,.392),(x-.0027,yy-.0116,.408)]
    points+=arc_x(x,yy,.411,180,0,.0116,8)
    points += [(x+.0027,yy+.0116,.408),(x+.0037,yy+.008,.392),(x+.0037,yy,.381),
               (x+.0025,yy,.3760),(x,yy,.37465),(x-.0025,yy,.3760)]
    sweep(f'Closed cord loop wrapping heddle and upper warp {i+1:02d}',loose,ties,points,.00112,cord,6,True)

# Actual open U-shaped textile strip with two folded tongue locations and corbels on the separate rest.
def strapMesh():
    v=[]; f=[]
    for i in range(23):
        u=-1+i/11
        for j in range(7):
            w=-1+j/3
            v.append((u*.221,-.540-.022*(1-u*u)+w*.034,.165+.043*(abs(u)**3.2)+w*.006))
    for i in range(22):
        for j in range(6):
            q=i*7+j;f.append((q,q+7,q+8,q+1))
    n=len(v)
    rim=[*range(0,7), *range(13,n,7), *range(n-2,n-8,-1), *range(n-14,0,-7)]
    vertices=[(x,y,z+q*.003) for q in [1,-1] for x,y,z in v]
    shell=f+[tuple(reversed([n+x for x in face])) for face in f]
    for a,b in zip(rim,rim[1:]+rim[:1]):shell.append((a,b,b+n,a+n))
    o=mesh('Wide curved open backstrap with structural thickness',loose,strapGroup,vertices,shell,strapM)
    for side in [-1,1]:
        edge=[(u*.221,-.540-.022*(1-u*u)+side*.034,.165+.043*(abs(u)**3.2)+side*.006) for u in [-1+i/11 for i in range(23)]]
        sweep('Contrasted real stitched edge border',loose,strapGroup,edge,.0020,stitch,6)
strapMesh()
for side in [-1,1]:
    x=side*.261
    points=arc_x(x,near,zh,155,-155,rb+.0041,15)
    points += [(side*.258,-.405,.271),(side*.235,-.465,.217),(side*.217,-.528,.205),
               (side*.210,-.535,.207),(side*.216,-.550,.209),(side*.227,-.537,.215),(side*.237,-.471,.224),
               (side*.250,-.421,.276),(side*.261,-.419,.322)]
    sweep('Continuous bound strap tie '+str(side),loose,ties,points,.00265,cord,8,True)
box('Separate low exhibit label',base,supports,(.0,-.643,.059),(.372,.020,.046),metal,.005,2)
etch('Original museum context plaque',base,supports,(0,-.654,.051),'SARAWAK  /  BACKSTRAP LOOM',.015,etchM)

box('Studio matte shadow only excluded',studio,None,(0,0,-.027),(100,100,.053),stone,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def light(n,where,w,sz,col,aim=(0,0,.29)):
    l=bpy.data.lights.new(n,'AREA');l.energy=w;l.size=sz;l.shape='DISK';l.color=col
    o=bpy.data.objects.new(n,l);studio.objects.link(o);o.location=where;look(o,aim)
light('Warm key reveals loom yarn',(-1.54,-1.68,1.72),135,1.42,(1,.91,.80))
light('Cool quiet fill shapes old tiled perimeter',(1.29,-1.31,1.54),98,1.30,(.83,.94,1))
light('Upper reflected rim on loom yarn',(.66,.95,1.65),78,.94,(1,.92,.78))
world=bpy.data.worlds.new('Warm natural exhibit fill');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.54,.55,.52,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.38
cd=bpy.data.cameras.new('Editorial cutaway camera');cam=bpy.data.objects.new('Editorial cutaway camera',cd);studio.objects.link(cam);S.camera=cam
hero=(1.07,-1.54,1.49);target=(.003,-.020,.215)
cd.type='ORTHO';cd.ortho_scale=1.58;cam.location=hero;look(cam,target)
S.render.engine='CYCLES';S.cycles.samples=210;S.cycles.use_denoising=False
S.cycles.adaptive_threshold=.012;S.cycles.adaptive_min_samples=52
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_percentage=100;S.render.resolution_x=S.render.resolution_y=512
S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=93
S.view_settings.view_transform='AgX';S.view_settings.exposure=.05
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True)
for c in (base,last,loose):
    for o in c.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/(slug+'.glb')),export_format='GLB',use_selection=True,
                         export_texcoords=False,export_animations=False,export_cameras=False,
                         export_lights=False,export_extras=False)
def still(to,pos,tgt,scale,wh):
    cam.location=pos;look(cam,tgt);cd.ortho_scale=scale
    S.render.resolution_x,S.render.resolution_y=wh;S.render.filepath=str(to)
    bpy.ops.render.render(write_still=True)
if not opts.skip_render:still(out/'previews/studio.webp',hero,target,1.58,(512,512))
if opts.review:
    S.cycles.samples=135
    still(opts.review/'raised-heddle-threads.webp',(.66,-.34,.76),(.0,.076,.365),.61,(640,600))
    still(opts.review/'physical-warp-weft-crossings.webp',(.15,-.49,.69),(.01,-.239,.334),.46,(650,600))
    still(opts.review/'open-backstrap-and-ties.webp',(-.65,-.96,.69),(.0,-.43,.221),.83,(640,600))
