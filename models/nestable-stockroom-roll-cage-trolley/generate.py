"""Original static nested stockroom roll-cage display; not installation or handling guidance."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
opts=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='nestable-stockroom-roll-cage-trolley'
out=opts.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if opts.review:opts.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
base=collection('01 independent retail exhibit ground')
last=collection('02 shared original cage unit source')
loose=collection('03 same cage model physically nested')
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
baseM=vmat('Original aggregate flooring in soft green grey',.82)
mark=material('Quiet off-white fictional floor accents','BABDA8',.73)
shadow=material('Slate original exhibit label','405356',.65)
face=material('Caption lettering warm contrast','E0D4AE',.67)
paint=material('Satin green-blue finish on tubular common frame','3F7776',.55,.40)
edge=material('Darker protection sleeves and cutaway caps','364E54',.58,.46)
grid=material('Slight warm zinc finish on genuine open grilles','A9B3A5',.47,.65)
hingeM=material('Dull bright deck hinge galvanized steel','A6AEAB',.49,.70)
handle=material('Generic muted orange grips and stowed edge rail','D59840',.55,.27)
rubber=material('Charcoal stockroom wheel tires','303636',.89,.03)
hub=material('Cool grey caster hub faces','6F7C78',.56,.47)
axleM=material('Cast dark silver wheel hardware','899594',.44,.64)
wireM=material('Warm grey parked deck support wire','8F9691',.49,.62)
studioMat=material('Matte muted neutral stand background','536464',.84)
R=empty('NESTABLE_STOCKROOM_ROLL_CAGE_DISPLAY',base)
ground=empty('INDEPENDENT_EXHIBIT_PLINTH',base,R)
unit=empty('RECEIVER_CAGE_SAME_SKU',last,R,(0,.274,0))
nest=empty('NESTED_CAGE_SAME_SKU',loose,R,(0,-.111,0))
# Original exhibit proportions. The tapered side envelopes leave real
# lateral clearance over the shared footprint. The front opening has no gate.
Y0=-.398;Y1=.388;zFoot=.068;zBase=.221;zTop=1.514
half=lambda y:.237-.19*y
pl=colored_board('Quiet textured stockroom exhibit plinth',base,ground,(0,.075,.033),(1.13,1.71,.066),baseM,[103,121,110])
for s in (-1,1):
    for y in [-.472,.320,.660]:
        box('Quiet dashed lines on the accompanying floor',base,ground,(s*.483,y,.0668),(.018,.14,.0022),mark,.001)
box('Small generic label at outside display front',base,ground,(.062,-.789,.048),(.403,.021,.037),shadow,.004)
etch('Original nested stockroom cage exhibit label',base,ground,(.062,-.801,.045),'ROLL CAGES  /  NESTED',.020,face)
def uv_side(y,z,s,inset=0):
    return (s*(half(y)-inset),y,z)
def rail(n,a,b,r,m=paint,ns=12):
    return rod(n,last,unit,a,b,r,m,ns)
for s,d in [(-1,'LEFT'),(1,'RIGHT')]:
    rail('Solid tapered bottom outside tube '+d, uv_side(Y0,zBase,s), uv_side(Y1,zBase,s),.018)
    rail('Tall front side tubular upright '+d,uv_side(Y0,zBase,s),uv_side(Y0,1.460,s),.0145)
    rail('Tall rear narrow structural tube '+d,uv_side(Y1,zBase,s),uv_side(Y1,zTop,s),.0145)
    q=[uv_side(y,z,s) for y,z in [(Y0,1.449),(Y0+.002,1.468),(Y0+.018,1.492),(Y0+.042,1.509),(Y0+.065,1.514),(Y1,zTop)]]
    sweep('Curved capped top side tube '+d,last,unit,q,.0145,paint,12)
    rail('Low side rail above open plinth '+d,uv_side(Y0,.283,s),uv_side(Y1,.283,s),.0105)
    rail('Attached mid-height horizontal stiffener '+d,uv_side(Y0,.867,s),uv_side(Y1,.867,s),.0095)
    # Side infill uses true round welded wires; the three-dimensional openings
    # are not transparent materials or a surface.
    for i in range(11):
        y=Y0+(i+1)*(Y1-Y0)/12
        rail('Open side grid vertical wire '+d,uv_side(y,.285,s,.0008),uv_side(y,zTop-.013,s,.0008),.0034,grid,8)
    for j in range(14):
        z=.282+(j+1)*1.218/15
        rail('Open side grid horizontal wire '+d,uv_side(Y0,z,s,-.001),uv_side(Y1,z,s,-.001),.0036,grid,8)
    box('Satin narrow front corner scuff cap '+d,last,unit,uv_side(Y0+.009,.287,s),(.038,.060,.091),edge,.008,2)
    rail('Short color-contrast upright rounded model grab detail '+d,uv_side(Y0,1.250,s),uv_side(Y0,1.397,s),.018,handle)
    rail('Upper grip quiet dark cap '+d,uv_side(Y0,1.394,s),uv_side(Y0,1.413,s),.018,edge)
# Narrow rear open grid, no sheet. The nested unit inserts from the wider
# front only in this static illustration; there is no modeled operation.
backWidth=half(Y1)
for z in [zBase,.287,.867,1.510]:
    rail('Rear structural narrow brace',(-backWidth,Y1,z),(backWidth,Y1,z),.011 if z>.23 else .015)
for i in range(6):
    x=-backWidth+(i+1)*(2*backWidth)/7
    rail('True rear grille vertical wire',(x,Y1,.286),(x,Y1,1.512),.0034,grid,8)
for j in range(14):
    z=.285+(j+1)*1.217/15
    rail('True rear grille horizontal wire',(-backWidth,Y1,z),(backWidth,Y1,z),.0036,grid,8)
# Recognizable separately parked mesh pad. It is held by real pinned lower
# mounts and a supported upper keeper, not hovering or crossing the other cage.
deck=empty('STOWED_UPRIGHT_MESH_PLATFORM',last,unit,(0,.354,.239))
for s in [-1,1]:
    rod('Tall amber-deck edge',(last),deck,(s*.125,0,.047),(s*.125,0,.745),.0098,handle,10)
for z in [.046,.747]:
    rod('Wide amber parked deck cross-rail',last,deck,(-.126,0,z),(.126,0,z),.0097,handle,10)
for i in range(5):
    x=-.125+(i+1)*.25/6
    rod('Parked deck genuine grid vertical wire',last,deck,(x,0,.045),(x,0,.746),.0035,wireM,8)
for j in range(9):
    z=.046+(j+1)*.699/10
    rod('Parked deck genuine grid horizontal wire',last,deck,(-.124,0,z),(.124,0,z),.0035,wireM,8)
def bore_x(n,c,parent,xa,xb,cy,cz,rin,rout,m):
    N=22;vv=[];ff=[]
    for x,r in [(xa,rin),(xa,rout),(xb,rout),(xb,rin)]:
        for j in range(N):
            t=j*math.tau/N;vv.append((x,cy+math.cos(t)*r,cz+math.sin(t)*r))
    for i in range(4):
        for j in range(N):
            a=i*N+j;b=((i+1)%4)*N+j;c0=((i+1)%4)*N+(j+1)%N;d=i*N+(j+1)%N
            ff.append((a,b,c0,d))
    o=mesh(n,c,parent,vv,ff,m)
    for i,q in enumerate(o.data.polygons):q.use_smooth=i//N in (1,3)
    return o
hingeY=.359;hingeZ=.254
for s,d in [(-1,'LEFT'),(1,'RIGHT')]:
    # Stand-side collar segments and a separately attached platform collar.
    a,b=sorted((s*.086,s*.116))
    bore_x('Rested platform inner eye '+d, last,unit,a,b,hingeY,hingeZ,.0081,.0165,handle)
    a,b=sorted((s*.124,s*.159))
    bore_x('Cage mounted outer eye '+d, last,unit,a,b,hingeY,hingeZ,.0081,.0171,hingeM)
    box('Recessed weld-tab into rear cage '+d,last,unit,(s*.146,.381,.249),(.030,.048,.029),hingeM,.003,2)
    box('Parked platform spar-foot to hanger '+d,last,deck,(s*.110,.001,.033),(.031,.023,.050),handle,.003,2)
    box('Upper deck keeper '+d,last,unit,(s*.129,.369,.986),(.026,.055,.032),edge,.004,2)
    rail('Rear keeper bracket '+d,(s*.129,Y1,.867),(s*.129,Y1,1.010),.008,hingeM)
    rod('Small actual keeper fastening axis '+d,last,unit,(s*.130,.333,.986),(s*.130,.401,.986),.006,hingeM,10)
rod('Continuous fixed common pin for stowed platform',last,unit,(-.164,hingeY,hingeZ),(.164,hingeY,hingeZ),.0068,hingeM,14)
# Four stable casters. Floors and casters are separate meshes.
for y in [-.342,.329]:
    for s,d in [(-1,'LEFT'),(1,'RIGHT')]:
        x=s*half(y)
        wz=.123
        # Rounded stepped sidewall and broad palm-sized tire profile.
        profile=[(-.027,0.027),(-.027,.049),(-.022,.056),(-.015,.057),(.015,.057),(.022,.056),(.027,.049),(.027,.027)]
        vv=[];ff=[];Q=24
        for xx,rr in profile:
            for j in range(Q):
                a=j*math.tau/Q;vv.append((x+xx,y+rr*math.cos(a),wz+rr*math.sin(a)))
        for i in range(len(profile)):
            for j in range(Q):
                nxt=(i+1)%len(profile);k=(j+1)%Q;f=i*Q;g=nxt*Q
                ff.append((f+j,g+j,g+k,f+k))
        o=mesh('Seated black tire on independent caster '+d,last,unit,vv,ff,rubber)
        for q in o.data.polygons:q.use_smooth=True
        rod('Pressed caster hub with visible lip '+d,last,unit,(x-.029,y,wz),(x+.029,y,wz),.029,hub,18)
        rod('Independent horizontal caster axle '+d,last,unit,(x-.040,y,wz),(x+.040,y,wz),.0077,axleM,14)
        for slide in [-.035,.035]:
            box('Shaped steel caster fork cheek '+d,last,unit,(x+slide,y+.015,.163),(.010,.056,.091),axleM,.007,2)
        box('Capped caster fork crown '+d,last,unit,(x,y+.016,.200),(.090,.066,.016),hingeM,.005,2)
        rod('Caster stem effector with no simulation '+d,last,unit,(x,y+.016,.201),(x,y+.016,.225),.026,edge,12)
        if y>0:
            box('Compact dark parked rear caster tab '+d,last,unit,(x,y+.045,.171),(.060,.027,.014),handle,.005,2)
# Linked mesh repeats one SKU exactly; both complete module roots and the
# parked-deck child hierarchy remain independently selectable in the .blend.
def linked_repeat(s,d):
    for child in list(s.children):
        n=child.copy();loose.objects.link(n);n.name='NESTED COPY '+child.name;n.parent=d
        n.matrix_basis=child.matrix_basis.copy()
        linked_repeat(child,n)
linked_repeat(unit,nest)
box('Studio matte shadow only excluded',studio,None,(0,0,-.027),(100,100,.053),studioMat,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def light(n,where,w,sz,col,aim=(0,0,.79)):
    l=bpy.data.lights.new(n,'AREA');l.energy=w;l.size=sz;l.shape='DISK';l.color=col
    o=bpy.data.objects.new(n,l);studio.objects.link(o);o.location=where;look(o,aim)
light('Warm key highlights real fine steel grid',(-2.75,-3.1,3.66),675,2.48,(1,.91,.80))
light('Cool quiet fill shapes old ground plinth',(2.9,-2.13,2.74),475,2.3,(.83,.94,1))
light('Upper reflected rim on upper cage line',(.91,2.3,2.75),355,1.85,(1,.92,.78))
world=bpy.data.worlds.new('Warm natural exhibit fill');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.54,.55,.52,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.38
cd=bpy.data.cameras.new('Editorial cutaway camera');cam=bpy.data.objects.new('Editorial cutaway camera',cd);studio.objects.link(cam);S.camera=cam
hero=(2.54,-3.49,2.67);target=(0,.086,.759)
cd.type='ORTHO';cd.ortho_scale=2.22;cam.location=hero;look(cam,target)
S.render.engine='CYCLES';S.cycles.samples=216;S.cycles.use_denoising=False
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
if not opts.skip_render:still(out/'previews/studio.webp',hero,target,2.22,(512,512))
if opts.review:
    S.cycles.samples=145
    still(opts.review/'top-view-of-true-nested-footprints.webp',(1.36,-1.72,3.39),(0,.10,.725),1.96,(680,660))
    still(opts.review/'tapered-lower-chassis-and-grounded-castors.webp',(2.37,-1.41,1.13),(0,.096,.226),1.63,(690,620))
    still(opts.review/'upright-stowed-platform-and-retainer.webp',(.28,-2.68,1.41),(0,.337,.683),1.11,(655,660))
