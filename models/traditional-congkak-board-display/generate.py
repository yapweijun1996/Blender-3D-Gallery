"""Original static Malaysian congkak game-board exhibit, no playable interaction."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
opts=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='traditional-congkak-board-display'
out=opts.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if opts.review:opts.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
base=collection('01 independent retail exhibit ground')
last=collection('02 one continuous carved congkak board')
loose=collection('03 sparse original seed-like exhibit counters')
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

def etch(n,c,p,o,text,size,mat):
    data=bpy.data.curves.new(n,'FONT'); data.body=text; data.align_x='CENTER';data.size=size
    ob=bpy.data.objects.new(n,data);assign(ob,n,c,p,mat);ob.location=o
    ob.rotation_euler.x=math.pi/2
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.object.convert(target='MESH')
    return ob


def multi(n,c,r,v,f,m,ids,smooth=False):
    o=mesh(n,c,r,v,f,m[0])
    for mat in m[1:]:o.data.materials.append(mat)
    for p,k in zip(o.data.polygons,ids):p.material_index=k;p.use_smooth=smooth and len(p.vertices)==4
    return o
slate=material('Carbon blue low museum plinth','2D3A42',.64,.18)
liner=material('Slate tan thin support felt','A0896C',.82)
alloy=material('Small satin shallow caption','D6C5A5',.53,.18)
timber=material('Warm individually cut wood with grain','92552E',.53)
cut=material('Soft hand-finished inner wood bowls','9A6541',.58)
seedA=material('Plain counters in buff wood grain','BE925E',.69)
seedB=material('Plain counters in dark shell color','6C4638',.66)
seedEdge=material('Small ivory seed seam','DDC19B',.70)
studioMat=material('Quiet blue gray backdrop','344754',.86)
ped=empty('SEPARATE_INTERPRETIVE_EXHIBIT_PLINTH',base)
boardRoot=empty('CONGKAK_ORIGINAL_SOLID_BOARD',last)
parts=empty('STAGED_SPARSE_COUNTERS',loose)
box('Low museum exhibit slab',base,ped,(0,0,.025),(.405,1.123,.05),slate,.019,3)
box('Recessed top museum center plane',base,ped,(0,0,.048),(.379,1.077,.008),slate,.009,2)
for y in (-.288,.288):
    box('Independent padded cradle',base,ped,(0,y,.061),(.209,.083,.028),liner,.005,2)
    for x in [-.104,.104]:
        rod('Cradle mount boot',base,ped,(x,y,.050),(x,y,.067),.009,slate,12)
etch('Original simple plinth caption',base,ped,(0,-.562,.016),'CONGKAK   /   MALAYSIA',.019,alloy)
# One actual closed carved board, flaring at its shoulder and tapering toward its
# rounded end stores. The native result remains a single watertight editable solid.
N=88
v=[];f=[]
for zz,sc in [(.074,.924),(.079,.954),(.093,.980),(.140,1.0),(.157,1.0),(.166,.985),(.168,.955)]:
    for i in range(N):
        a=math.tau*i/N; cx=math.cos(a);cy=math.sin(a)
        Y=math.copysign(abs(cy)**.33,cy)*.492
        # Very modest length-dependent taper, original and non-figurative.
        X=math.copysign(abs(cx)**.27,cx)*(.124-(abs(Y)/.492)**2*.008)
        v.append((sc*X,sc*Y,zz))
for j in range(6):
    for i in range(N):
        a=j*N+i;b=j*N+(i+1)%N
        f.append((a,b,b+N,a+N))
f+= [tuple(reversed(range(N))),tuple(range(6*N,7*N))]
board=mesh('Single carved solid board with integral 16 wells',last,boardRoot,v,f,timber)
board.data.materials.append(cut)
patterns=[(x,y,.0355,.042,'Village '+str(row)+'-'+str(k+1)) for row,x in enumerate((-.046,.046),1)
          for k,y in enumerate((-.276,-.184,-.092,0,.092,.184,.276))]
patterns.extend([(0,y,.068,.059,'House end '+k) for k,y in [('front',-.404),('back',.404)]])
def stage_solid_carve(x,y,r,dep,name):
    vv=[];ff=[];num=48 if r>.06 else 32
    # Fine radius at the rolled rim, strong shoulder, evidently concave interior.
    prof=[(-dep,.092),(-dep+.001,.285),(-dep+.003,.455),(-dep+.008,.638),
          (-dep+.015,.796),(-dep+.024,.902),(-.010,.938),(-.005,.965),(-.001,1.0),(.004,1.04),(.013,1.04)]
    for z,rr in prof:
        for i in range(num):
            a=i*math.tau/num
            vv.append((x+r*rr*math.cos(a),y+r*rr*math.sin(a),.168+z))
    for j in range(len(prof)-1):
        for i in range(num):
            a=j*num+i;b=j*num+(i+1)%num
            ff.append((a,b,b+num,a+num))
    ff.append(tuple(reversed(range(num))));ff.append(tuple(range((len(prof)-1)*num,len(prof)*num)))
    tool=mesh('Temporary bowl cutting volume '+name,last,None,vv,ff,timber)
    tool.data.materials.append(cut)
    for face in tool.data.polygons:face.material_index=1
    bpy.ops.object.select_all(action='DESELECT');board.select_set(True);bpy.context.view_layer.objects.active=board
    mod=board.modifiers.new('Integral bowl '+name,'BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=tool
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(tool,do_unlink=True)
for x,y,r,d,n in patterns:stage_solid_carve(x,y,r,d,n)
for face in board.data.polygons:
    face.use_smooth=abs(face.normal.z)<.985
# Color detail authored per point without external bitmap assets. The long
# grain follows the billet, including curved recesses and the rounded side.
def lin(x):
    return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4
for mat in (timber,cut):
    vc=mat.node_tree.nodes.new('ShaderNodeVertexColor');vc.layer_name='AUTHORED_WOOD_GRAIN'
    mat.node_tree.links.new(vc.outputs['Color'],mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
colors=board.data.color_attributes.new(name='AUTHORED_WOOD_GRAIN',type='FLOAT_COLOR',domain='POINT')
for vtx,vc in zip(board.data.vertices,colors.data):
    x,y,z=vtx.co
    g=math.sin(x*220+1.7*math.sin(y*9)+.77*math.sin(y*18+x*9)+z*95)
    fine=math.sin(x*410+.5*math.sin(y*14)+z*146)*.32
    wide=math.sin(x*90-.8*math.sin(y*13)+z*20)*.36
    stain=math.exp(-((y-.155)/.14)**2)*math.sin(x*156-.3+z*22)*.32
    # Large top triangles share one quiet finish; visible grain is kept
    # only at much lower amplitude on the rounded sides and interior.
    reach=max(0.,min(1.,(.167-z)/.025))
    shade=7*reach*(g+.48*fine+.50*wide+.45*stain)
    lift=8 if z>.157 else 6
    rgb=(147+shade+lift,89+.72*shade+lift,51+.46*shade+lift)
    vc.color=tuple(lin(max(0,min(255,c))/255) for c in rgb)+(1,)
# Small number of original seed-like shapes, some wells are intentionally empty.
# Seat each piece on a ray-cast from the actual solid, not assumed floor height.
from mathutils.bvhtree import BVHTree
tree=BVHTree.FromPolygons([q.co.copy() for q in board.data.vertices],
                         [tuple(q.vertices) for q in board.data.polygons])
seedstaging=[
(-.046,-.276,-.002,.002,-.36,0),(-.046,-.184,.002,-.002,.32,1),
(.046,-.184,-.003,.002,.95,0),(.046,.0,.000,-.003,-.4,1),
(-.046,.184,.004,.003,.64,0),(0,-.404,-.011,.006,.43,1),
(0,-.404,.009,.005,-.38,0),(0,-.404,-.002,-.013,.14,1),
(0,.404,.002,-.004,-.43,0)]
for i,(x,y,ox,oy,rot,k) in enumerate(seedstaging,1):
    px=x+ox;py=y+oy
    hit,n,_,_=tree.ray_cast(Vector((px,py,.184)),Vector((0,0,-1)),.100)
    assert hit
    # Slightly flattened tapered ovoid, length and color variation within a
    # tiny staged handful. Each has finite material seam, not letters or marks.
    uu=[]; ff=[]; inds=[]; M=12; rings=7
    sx=.0065+(.0005 if i%2 else .0000);sy=.0089+(.0008 if i%3 else 0); sz=.0049
    lo=(0,0,-sz);hi=(0,0,sz)
    for a in range(1,rings):
        p=math.pi*a/rings
        for q in range(M):
            u=math.tau*q/M
            xx=sx*math.sin(p)*math.cos(u)*(1-.16*math.sin(u))
            yy=sy*math.sin(p)*math.sin(u)
            zz=-sz*math.cos(p)+.00056*math.sin(u)*math.sin(p)
            uu.append((xx,yy,zz))
    ii=len(uu);uu.extend([lo,hi])
    for q in range(M):
        q2=(q+1)%M
        ff.append((ii,q2,q));inds.append(0)
        ff.append((ii+1,ii-M+q,ii-M+q2));inds.append(0)
        for j in range(rings-2):
            ff.append((j*M+q,j*M+q2,(j+1)*M+q2,(j+1)*M+q))
            inds.append(1 if j==2 and q==4 else 0)
    s=multi('Staged original seated seed '+str(i),loose,parts,uu,ff,[seedA if k==0 else seedB,seedEdge],inds,True)
    s.rotation_euler.z=rot
    # Sample the whole transformed solid for stable contact with the
    # bottom of the well, rather than dropping the centermost vertex.
    sn,cs=math.sin(rot),math.cos(rot)
    required=[]
    for xx,yy,zz in uu:
        p,n,_,_=tree.ray_cast(Vector((px+cs*xx-sn*yy,py+sn*xx+cs*yy,.184)),Vector((0,0,-1)),.100)
        assert p is not None
        required.append(p.z-zz)
    s.location=(px,py,max(required)-.00015)
box("Studio matte shadow only excluded",studio,None,(0,0,-.027),(100,100,.053),studioMat,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def light(n,where,w,sz,col,aim=(0,0,.79)):
    l=bpy.data.lights.new(n,'AREA');l.energy=w;l.size=sz;l.shape='DISK';l.color=col
    o=bpy.data.objects.new(n,l);studio.objects.link(o);o.location=where;look(o,aim)
light('Warm key highlights steel wheels and cut concrete',(-2.75,-3.1,3.66),420,2.35,(1,.91,.80))
light('Cool quiet fill shapes model plinth',(2.9,-2.13,2.74),280,2.0,(.83,.94,1))
light('Upper reflected rim on upper steel bracket',(.91,2.3,2.75),240,1.70,(1,.92,.78))
world=bpy.data.worlds.new('Warm natural exhibit fill');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.54,.55,.52,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.38
cd=bpy.data.cameras.new('Editorial cutaway camera');cam=bpy.data.objects.new('Editorial cutaway camera',cd);studio.objects.link(cam);S.camera=cam
hero=(1.23,-1.04,1.81);target=(0,0,.080)
cd.type='ORTHO';cd.ortho_scale=1.215;cam.location=hero;look(cam,target)
S.render.engine='CYCLES';S.cycles.samples=190;S.cycles.use_denoising=False
S.cycles.adaptive_threshold=.012;S.cycles.adaptive_min_samples=38
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
if not opts.skip_render:still(out/'previews/studio.webp',hero,target,1.215,(512,512))


if opts.review:
    S.cycles.samples=118
    still(opts.review/'top-view-of-fourteen-cups-and-two-houses.webp',(.035,-.054,2.11),(0,0,.087),1.17,(650,720))
    still(opts.review/'one-continuous-recess-and-seated-counters.webp',(.74,-.67,.79),(0,-.207,.139),.416,(690,620))
    still(opts.review/'depth-and-rounded-end-store-detail.webp',(.51,-.92,.69),(0,-.337,.122),.426,(656,633))
