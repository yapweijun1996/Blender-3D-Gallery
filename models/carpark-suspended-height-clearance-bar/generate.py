"""Original static carpark clearance bar exhibit, not an engineering or driving reference."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
opts=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='carpark-suspended-height-clearance-bar'
out=opts.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if opts.review:opts.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
base=collection('01 original concrete entrance slice')
last=collection('02 bar, roof plates and welded attachment stems')
loose=collection('03 two modeled interlinked short chain groups')
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
concrete=vmat('Natural warm formed mineral aggregate',.77)
shade=vmat('Cross-section interior grey concrete',.81)
asphalt=vmat('Muted original graphite and charcoal aggregate',.91)
roadMat=material('Flat off-white original approach marking','BDC0AD',.78)
edge=material('Dark slate column skirting and entrance trim','394F53',.70)
matte=material('Original warm blue structural mounting plates','4A5859',.53,.64)
hardware=material('Galvanized metallic eyelet and hex hardware','A6ACAA',.42,.73)
linksA=material('Forged steel chain bright side','ADAAA0',.37,.79)
linksB=material('Forged steel chain dark side','878A87',.43,.69)
barTint=vmat('Ocher coated aluminium panel with restrained speckle',.55,.26)
endCap=material('Deep slate end inserts and return lip','293E43',.57,.36)
stripe=material('Dark blue hazard accent panels, nonregulatory','273C3E',.56,.19)
letter=material('Muted beige lettering and short floor cue','F0E0B9',.49)
orange=material('Soft ocher low corner marking','C49B62',.57)
glass=material('Opal ceiling lamp not emissive','DDD4AA',.53)
R=empty('CARPARK_SUSPENDED_HEIGHT_CLEARANCE_BAR_EXHIBIT',base)
B=empty('INDEPENDENT_CONCRETE_ENTRANCE_CROSS_SECTION',base,R)
H=empty('BAR_AND_SEPARATE_ANCHOR_PLATE_ASSEMBLIES',last,R)
C=empty('TWO_GENUINELY_INTERLOCKED_CHAINS',loose,R)
def grain(n,c,p,loc,d,mat,hue,rounding=.012,amp=1.):
    o=box(n,c,p,loc,d,mat,rounding,2)
    bpy.context.view_layer.update();bpy.context.view_layer.objects.active=o
    for m in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=m.name)
    apply_color(o,lambda v:tuple(k*(1+amp*(.047*math.sin(v.x*27+v.y*61+v.z*77)+.024*math.cos(v.y*83+v.z*46)+.025*math.sin(v.z*33-v.x*21))) for k in hue))
    return o
def face(n,c,r,outline,z,mat):
    v=[(x,y,z) for x,y in outline]
    return mesh(n,c,r,v,[tuple(range(len(v)))],mat)
def wall_sheet(n,x,z,dx,dz,y,mat):
    v=[(x-dx/2,y,z-dz/2),(x+dx/2,y,z-dz/2),(x+dx/2,y,z+dz/2),(x-dx/2,y,z+dz/2)]
    return mesh(n,last,H,v,[tuple(range(4))],mat)
# Standalone cleanly cut entrance, no regulatory sign heights or named location.
grain('Exhibit slab section with pale sawn side',base,B,(0,0,.09),(4.22,2.51,.18),shade,[135,130,113],.035)
grain('Continuous original asphalt roadway texture',base,B,(0,0,.184),(3.56,2.48,.027),asphalt,[69,77,74],.006,1.3)
for side in (-1,1):
    x=side*1.91
    grain('Raised boundary threshold curb',base,B,(x,0,.225),(.364,2.46,.090),concrete,[168,160,140],.013)
    grain('One solid entrance pier',base,B,(side*1.783,.106,1.292),(.328,.690,2.078),concrete,[171,164,145],.024)
    box('Near-visible slate pier plinth band',base,B,(side*1.783,.106,.401),(.342,.704,.308),edge,.012,2)
    box('Vertical inset amber trim on pier face',base,B,(side*1.783,-.245,.64),(.100,.024,.240),orange,.007,2)
    coords=[(side*1.45,-1.21),(side*1.52,-1.21),(side*1.52,.72),(side*1.45,.72)]
    face('Simple unnumbered edge cue on original floor',base,B,coords if side>0 else list(reversed(coords)),.198,roadMat)
# A single light-cast lintel with a dark relief near front, rather than an entire building.
grain('Real overhead concrete anchorage lintel',base,B,(0,-.020,2.486),(3.88,1.134,.322),concrete,[174,167,148],.025)
grain('Narrow pressed fascia overlay above and behind fixture',base,B,(0,-.589,2.507),(3.849,.054,.161),shade,[144,141,126],.012)
box('Small roof join horizontal reveal',base,B,(0,-.622,2.468),(3.74,.010,.009),edge,.001)
for x in (-1.34,1.34):
    box('Independent small ceiling luminaire chassis',base,B,(x,.210,2.298),(.295,.101,.037),edge,.011,2)
    box('Inset off-white ceiling lamp lens',base,B,(x,.211,2.275),(.253,.080,.014),glass,.006,2)
# Broken generic lane orientation cue, not an official marking copy.
face('Short original entry approach shaft',base,B,[(-.069,-1.16),(.069,-1.16),(.069,-.81),(-.069,-.81)],.198,roadMat)
face('Separate simple triangular approach cue',base,B,[(-.169,-.835),(.169,-.835),(0,-.626)],.1981,roadMat)
sideNote=etch('Fictional generic MSCP exhibit caption',base,B,(-1.19,-.6225,2.520),'CAR PARK / ENTRY',.082,letter)
# The exact artistic proportions express hierarchy, not a safe clearance.
Z=.0
barZ=1.540;barY=-.467;eyex=1.135;eyez=1.695;pitch=.10590
grain('Closed suspended warning bar core',last,H,(0,barY,barZ),(2.905,.118,.150),barTint,[204,154,63],.024,1.15)
for s in (-1,1):
    box('Inset moulded end cap',last,H,(s*1.446,barY,barZ),(.067,.129,.133),endCap,.021,3)
    box('Small separate edge flange seat ring',last,H,(s*1.393,barY,barZ),(.025,.126,.146),endCap,.006,2)
box('Lower rolled lip of actual solid bar section',last,H,(0,barY,1.470),(2.788,.120,.015),endCap,.005,2)
# Individual diagonal patches set in front of the existing bar skin.
for side in (-1,1):
    for j in range(3):
        x=side*(.935+j*.143); y=barY-.062
        vv=[(x-.048,y,barZ-.055),(x+.012,y,barZ-.055),(x+.048,y,barZ+.055),(x-.012,y,barZ+.055)]
        if side<0:vv=[(2*x-X,Y,z) for X,Y,z in reversed(vv)]
        mesh('Independent diagonal visual caution inset',last,H,vv,[(0,1,2,3)],stripe)
plate=wall_sheet('Fictional unnumbered warning plate',0,barZ,1.337,.115,barY-.062,stripe)
etch('Original LOW CLEARANCE words, no numeric value',last,H,(0,barY-.064,barZ-.025),'LOW CLEARANCE',.089,letter)
# A true closed elliptical tube in alternating vertical planes. Each neighbor
# crosses the disk of the next once without shared material or mesh overlap.
hr=.065;br=.039;tr=.012
def ring(n,pos,orient,mat):
    X,Y,Z=pos; nsz=40; nring=10;v=[];f=[]
    for i in range(nsz):
        m=i*math.tau/nsz
        u=br*math.sin(m); z=hr*math.cos(m)
        normal=Vector((hr*math.sin(m),br*math.cos(m))).normalized()
        for j in range(nring):
            a=j*math.tau/nring
            d=u+normal.x*tr*math.cos(a);e=tr*math.sin(a)
            v.append((X+(d if orient==0 else -e),Y+(e if orient==0 else d),Z+z+normal.y*tr*math.cos(a)))
    for i in range(nsz):
        for k in range(nring):
            j=(i+1)%nsz;l=(k+1)%nring
            f.append((i*nring+k,j*nring+k,j*nring+l,i*nring+l))
    # The winding above gives an outward tube as traversed from each outer side.
    o=mesh(n,loose,C,v,f,mat)
    for pol in o.data.polygons:pol.use_smooth=True
    return o
for side,word in [(-1,'LEFT'),(1,'RIGHT')]:
    x=side*eyex;top=eyez+pitch*5
    box('Roof bolted anchor plate '+word,last,H,(x,barY,2.314),(.219,.189,.031),matte,.007,2)
    box('Bar bolted eye seat plate '+word,last,H,(x,barY,1.620),(.155,.121,.021),matte,.005,2)
    # Physical threaded collars touch the respective closed eyes as visible fixtures.
    rod('Anchor eye stem anchored to roof plate '+word,last,H,(x,barY,top+.057),(x,barY,2.319),.018,hardware,14)
    rod('Bar eye stem anchored to seat and warning core '+word,last,H,(x,barY,1.606),(x,barY,eyez-.052),.017,hardware,14)
    for sx in (-1,1):
        for sy in (-1,1):
            px=x+sx*.075;py=barY+sy*.056
            rod('Visible hex anchor head '+word,last,H,(px,py,2.289),(px,py,2.305),.013,hardware,6)
            px=x+sx*.049;py=barY+sy*.034
            rod('Visible hex eye plate head '+word,last,H,(px,py,1.622),(px,py,1.636),.009,hardware,6)
    for idx in range(6):
        if idx==0: st='CLOSED_BAR_EYE'
        elif idx==5: st='CLOSED_OVERHEAD_EYE'
        else: st='CLOSED_CHAIN_LINK'
        ring(f'{word}_{idx}_{st}',(x,barY,eyez+pitch*idx),idx%2,(hardware if idx in (0,5) else linksA if idx%2==1 else linksB))
box('Studio matte shadow only excluded',studio,None,(0,0,-.027),(100,100,.053),shade,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def light(n,where,w,sz,col,aim=(0,0,1.30)):
    l=bpy.data.lights.new(n,'AREA');l.energy=w;l.size=sz;l.shape='DISK';l.color=col
    o=bpy.data.objects.new(n,l);studio.objects.link(o);o.location=where;look(o,aim)
light('Warm key highlights chain links and matte bar',(-4.5,-5.8,6.9),2400,4.9,(1,.91,.80))
light('Cool quiet fill shapes old concrete entrance',(6.2,-2.6,5.0),1650,4.5,(.83,.94,1))
light('Upper reflected rim on panel hardware',(1.9,4.1,5.7),2080,3.8,(1,.92,.78))
world=bpy.data.worlds.new('Warm natural exhibit fill');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.54,.55,.52,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.38
cd=bpy.data.cameras.new('Editorial cutaway camera');cam=bpy.data.objects.new('Editorial cutaway camera',cd);studio.objects.link(cam);S.camera=cam
hero=(3.76,-7.9,3.54);target=(.0,-.1,1.30)
cd.type='ORTHO';cd.ortho_scale=5.54;cam.location=hero;look(cam,target)
S.render.engine='CYCLES';S.cycles.samples=220;S.cycles.use_denoising=False
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
if not opts.skip_render:still(out/'previews/studio.webp',hero,target,5.54,(512,512))
if opts.review:
    S.cycles.samples=150
    still(opts.review/'chain-assembly-front.webp',(2.58,-4.45,2.11),(1.135,-.467,1.971),1.08,(630,640))
    still(opts.review/'slab-anchor-and-eye-underside.webp',(.33,-2.24,1.19),(1.135,-.467,2.203),.797,(630,600))
    still(opts.review/'bar-mount-and-unnumbered-insert.webp',(2.49,-4.36,1.87),(.58,-.467,1.608),2.36,(675,540))
