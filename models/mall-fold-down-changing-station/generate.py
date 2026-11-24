"""Native original family-room fold-down fixture; empty model animation, not equipment instructions."""
import argparse, math, sys
from pathlib import Path
import bpy
from mathutils import Vector, Quaternion
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='mall-fold-down-changing-station'
out=a.output.resolve()
for k in ('previews','exports'): (out/k).mkdir(parents=True,exist_ok=True)
if a.review:a.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene
S.unit_settings.system='METRIC'
S.render.fps=30
S.frame_start=0
S.frame_end=66

def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c

context=collection('01 sectional wall and family-room plaque')
body=collection('02 fixed mounting shell, bearing cheeks and pins')
deck=collection('03 moving padded deck with fascia, grip and captured barrel')
studio=collection('04 studio only, never exported')
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


# Scene coordinates: front points -Y and floor datum Z=0. The rotation is solely
# about one world-X directed hinge. Presentation proportions are original artwork.
room=empty('FAMILY_ROOM_DISPLAY_CONTEXT',context)
fixed=empty('CHANGING_STATION_HOUSING',body)
hinge=empty('CHANGING_DECK_HINGE',deck,loc=(0,-.124,.851))
wall=material('Glazed cool-grey wall tiles','D7DDD9',.45)
wallalt=material('Two soft tile tones','E1E7E0',.43)
mortar=material('Recessed slim grout','A2B3AF',.72)
powder=material('Sea-green satin main shell','2F706C',.34,.11)
powder_l=material('Muted lighter teal polypropylene','58998D',.4)
powder_dark=material('Dark deep forest moulding','254845',.50)
sand=material('Warm ivory deck pad','EFF1D9',.55)
rim=material('Ivory softly molded perimeter','DEE5CB',.38)
oak=material('Honey ochre detail polymer','EFB779',.41)
steel=material('Satin stainless hardware','A7BCB4',.31,.62)
light_steel=material('Polished pin caps','CAD9CC',.27,.72)
grip=material('Charcoal inset grip pocket','243D3B',.66)
ink=material('Soft cream type','F4E1BD',.58)
warm=material('Warm brushed base trim','A39071',.47,.28)
ground=material('Warm stone studio backdrop','979789',.69)

# A cropped sample wall, not a full washroom. The slab and tile gaps remain physical.
box('Wall section solid substrate',context,room,(0,.030,.769),(1.090,.057,1.538),mortar,.021,3)
for col in range(4):
    for row in range(6):
        incr=.247
        x=(col-1.5)*.266
        z=.136+row*incr
        box('Glazed wall section tile %d %d'%(col,row),context,room,(x,-.004,z),(.263,.022,.244),wallalt if (row+col*3)%5==0 else wall,.003,2)
box('Brushed toe trim at cropped cutaway',context,room,(0,-.023,.030),(1.082,.034,.059),warm,.007,3)
box('Wall sample slab foot',context,room,(0,.025,.012),(1.10,.133,.023),mortar,.010,2)
box('Textured narrow plaque backing',context,room,(0,-.028,1.433),(.630,.028,.108),powder_dark,.018,4)
box('Ochre decorative plaque line',context,room,(0,-.045,1.397),(.468,.005,.005),oak,.002,2)

def front_text(n,group,parent,word,x,y,z,size,mat):
    curve=bpy.data.curves.new(n,'FONT');curve.body=word;curve.align_x='CENTER'
    curve.size=size;curve.space_character=1.10
    o=bpy.data.objects.new(n,curve);assign(o,n,group,parent,mat)
    o.location=(x,y,z);o.rotation_euler.x=math.pi/2
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    bpy.ops.object.convert(target='MESH')
    return o
front_text('Original generic FAMILY CARE sign',context,room,'FAMILY CARE',0,-.043,1.430,.040,ink)
front_text('Small generic sign subtitle',context,room,'F O L D - D O W N   D E C K',0,-.043,1.411,.0105,ink)

# Fixed shell: separate simple parts produce a genuine receiving recess instead
# of a large self-intersecting solid on the tray's side of the hinge.
box('Recessed wall mounting plate',body,fixed,(0,-.034,1.088),(.810,.037,.554),powder,.031,6)
box('Inset lightly pebbled inner back',body,fixed,(0,-.055,1.090),(.736,.013,.488),powder_l,.022,5)
box('Shell closed upper brow',body,fixed,(0,-.111,1.351),(.826,.133,.053),powder,.024,5)
for side in (-1,1):
    end='left' if side<0 else 'right'
    xx=side*.403
    box(end+' molded narrow hinge cheek',body,fixed,(xx,-.093,1.098),(.057,.106,.481),powder,.016,4)
    box(end+' dark trim beneath bearing',body,fixed,(xx,-.108,.847),(.058,.126,.098),powder_dark,.018,4)
    rod(end+' fixed outward bearing pin',body,fixed,(side*.373,-.124,.851),(side*.443,-.124,.851),.031,steel,26)
    rod(end+' round polished retaining face',body,fixed,(side*.439,-.124,.851),(side*.447,-.124,.851),.022,light_steel,24)
    rod(end+' pin axial recess',body,fixed,(side*.446,-.124,.851),(side*.448,-.124,.851),.008,grip,18)
    for zz in (.976,1.235):
        rod(end+' visual mounting hardware',body,fixed,(side*.383,-.151,zz),(side*.383,-.148,zz),.0085,steel,18)
        box(end+' screw impression',body,fixed,(side*.383,-.152,zz),(.010,.001,.0017),grip,.0004,2)
for x in (-.240,-.120,0,.120,.240):
    box('Quiet interior horizontal panel accent',body,fixed,(x,-.064,1.286),(.057,.005,.003),powder_dark,.0014,2)
rod('Stationary continuous captured steel axle',body,fixed,(-.392,-.124,.851),(.392,-.124,.851),.0135,steel,28)
for side in (-1,1):
    box('Stationary continuous bearing stop shoulder '+str(side),body,fixed,(side*.391,-.1315,.800),(.076,.029,.0234),powder_dark,.003,3)
box('Molded fixed lower lip beneath hinge',body,fixed,(0,-.049,.823),(.756,.075,.023),powder,.010,3)

# Empty deck. Its 3D pads and broad edge blend from closed fascia into one
# horizontal pad. Front corners and interior shallow edging are original.
def rounded_outline(w,d,r,center,n=9):
    ox,oy=center; pts=[]
    for cx,cy,start in ((w/2-r,d/2-r,0),(-w/2+r,d/2-r,90),(-w/2+r,-d/2+r,180),(w/2-r,-d/2+r,270)):
        for i in range(n):
            t=math.radians(start+i*90/(n-1))
            pts.append((ox+cx+r*math.cos(t),oy+cy+r*math.sin(t)))
    return pts

def round_profile(n,levels,mats,mids):
    v=[(x,y,z) for w,d,r,cy,z in levels for x,y in rounded_outline(w,d,r,(0,cy))]
    N=len(v)//len(levels);faces=[];ids=[]
    faces.append(tuple(reversed(range(N))));ids.append(mids[0])
    for j in range(len(levels)-1):
        for i in range(N):
            k=(i+1)%N
            faces.append((j*N+i,j*N+k,(j+1)*N+k,(j+1)*N+i));ids.append(mids[j+1])
    faces.append(tuple(range((len(levels)-1)*N,len(v))));ids.append(mids[-1])
    o=mesh(n,deck,hinge,v,faces,mats[0])
    for m in mats[1:]:o.data.materials.append(m)
    for f,i in zip(o.data.polygons,ids):
        f.material_index=i;f.use_smooth=len(f.vertices)==4
    return o

round_profile('Broad movable molded tray shell',[
    (.657,.389,.040,-.225,-.048),(.696,.418,.045,-.225,-.042),
    (.721,.425,.053,-.225,-.026),(.725,.427,.056,-.226,-.009),
    (.714,.416,.055,-.227,.006),(.681,.390,.045,-.226,.018),
    ],[powder_l,powder,powder_dark],[1,2,1,0,0,0,0])
round_profile('Contoured ivory pad with solid smooth sitting surface',[
    (.647,.359,.054,-.228,.015),(.660,.370,.059,-.228,.018),
    (.666,.375,.062,-.229,.025),(.654,.365,.059,-.229,.035),
    (.643,.352,.055,-.228,.038),
    ],[rim,sand],[0,0,0,0,1,1])
# Top side rails are integrated fixed-width trim on the moving pan, no strap
# or other action prop. On the folded model they nest into the fixed recess.
for side in (-1,1):
    box('Deck raised soft lateral edging '+str(side),deck,hinge,(side*.320,-.229,.035),(.028,.245,.032),rim,.012,4)
box('Deck back rounded edge',deck,hinge,(0,-.057,.030),(.592,.034,.031),rim,.014,4)
box('Deck front convex shoulder',deck,hinge,(0,-.393,.028),(.590,.028,.025),rim,.010,4)
def sleeve(n,x0,x1,r,bore=.0145):
    # The small axial opening is actual topology, not a dark appearance.
    N=28; v=[]; f=[]
    for x,rr in ((x0,r),(x1,r),(x1,bore),(x0,bore)):
        for j in range(N):
            t=math.tau*j/N
            v.append((x,rr*math.cos(t),rr*math.sin(t)))
    for k in range(4):
        for j in range(N):
            m=(j+1)%N
            f.append((k*N+j,k*N+m,((k+1)%4)*N+m,((k+1)%4)*N+j))
    o=mesh(n,deck,hinge,v,f,steel if 'central' in n else powder_dark)
    for q in o.data.polygons:q.use_smooth=q.index//N in (0,2)
    return o
sleeve('One moving central hinge sleeve',-.351,.351,.023)
for side in (-1,1):
    sleeve('Thin moving bushing end '+str(side),*sorted((side*.351,side*.366)),.026)
    box('Actual molded arm meets its moving barrel '+str(side),deck,hinge,(side*.328,-.0375,-.007),(.054,.046,.044),powder,.009,3)
    box('Moving open-limit contact lug '+str(side),deck,hinge,(side*.357,-.018,-.029),(.024,.014,.020),powder,.0025,3)

# Outside reveals a useful original grip/fascia, not branded instruction.
round_profile('Inset edge stripe fascia on outer face',[
    (.513,.238,.035,-.226,-.051),(.535,.255,.042,-.226,-.048),
    (.537,.257,.043,-.226,-.045),
    ],[powder_dark,powder],[0,0,1,1])
box('Dark recessed finger grip panel',deck,hinge,(0,-.384,-.043),(.217,.030,.026),grip,.011,4)
for s in (-1,1):
    box('Grip mounting end '+str(s),deck,hinge,(s*.089,-.385,-.056),(.035,.023,.029),oak,.006,3)
rod('Floating ochre pull grip',deck,hinge,(-.097,-.393,-.068),(.097,-.393,-.068),.009,oak,22)
for x in (-.146,-.073,0,.073,.146):
    box('Small neutral fascia motif',deck,hinge,(x,-.252,-.0515),(.034,.003,.0025),powder_l,.0013,2)

# Thirty-one explicit easing keys followed by a held end pose. Standard X
# quaternion only: Blender -90° folded --> 0° level. No other object is keyed.
for f in (1,4,7,*range(9,57,2),57,58,61,64,67):
    t=max(0,min(1,(f-4)/52));e=t*t*(3-2*t)
    hinge.rotation_quaternion=Quaternion((1,0,0),-math.pi/2*(1-e))
    hinge.keyframe_insert(data_path='rotation_quaternion',frame=f-1,group='Single authored hinge motion')
action=hinge.animation_data.action; action.name='CHANGING_STATION_UNFOLD'
# In new Blender the active action belongs to an action slot.
if hasattr(action,'layers'):
    curves=action.layers[0].strips[0].channelbag(hinge.animation_data.action_slot).fcurves
else:
    curves=action.fcurves
for fcurve in curves:
    for key in fcurve.keyframe_points:key.interpolation='LINEAR'
S.frame_set(0)

box('Studio ground only',studio,None,(0,0,-.030),(200,200,.055),ground,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,c,power,size,color,aim=(0,0,.95)):
    m=bpy.data.lights.new(n,'AREA');m.energy=power;m.size=size;m.shape='DISK';m.color=color
    o=bpy.data.objects.new(n,m);studio.objects.link(o);o.location=c;look(o,aim)
lamp('Broad warm softbox',(-2.4,-3.0,3.44),375,3.0,(1,.91,.81))
lamp('Cool broad detail fill',(2.5,-1.40,2.12),260,2.6,(.83,.95,1))
lamp('Back wall tile broad rim',(.62,1.50,2.88),235,2.0,(1,.92,.77))
world=bpy.data.worlds.new('Warm editorial studio');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.52,.59,.61,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.46
lens=bpy.data.cameras.new('Studio camera');cam=bpy.data.objects.new('Studio camera',lens);studio.objects.link(cam)
S.camera=cam;lens.type='ORTHO';lens.ortho_scale=1.90
cam.location=(2.15,-4.3,2.76);look(cam,(-.012,-.075,.775))
S.render.engine='CYCLES';S.cycles.samples=48;S.cycles.use_denoising=sys.platform=='darwin'
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_x=S.render.resolution_y=512
S.render.resolution_percentage=100;S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=92
S.view_settings.view_transform='AgX';S.view_settings.exposure=.10
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True)
for c in (context,body,deck):
    for o in c.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/f'{slug}.glb'),export_format='GLB',use_selection=True,
                         export_texcoords=False,export_animations=True,export_animation_mode='ACTIONS',
                         export_cameras=False,export_lights=False,export_extras=False)
def still(to,frame,pos,target,scale,res):
    S.frame_set(frame);cam.location=pos;look(cam,target);lens.ortho_scale=scale
    S.render.resolution_x,S.render.resolution_y=res;S.render.filepath=str(to)
    bpy.ops.render.render(write_still=True)
if not a.skip_render:
    still(out/'previews/studio.webp',66,(2.15,-4.3,2.76),(-.012,-.075,.775),1.87,(512,512))
if a.review:
    still(a.review/'closed-fascia.webp',0,(2.15,-4.3,2.76),(-.012,-.075,.775),1.87,(800,800))
    still(a.review/'mid-unfold.webp',30,(2.15,-4.3,2.76),(-.012,-.075,.775),1.87,(800,800))
    still(a.review/'open-level-deck.webp',66,(2.15,-4.3,2.76),(-.012,-.075,.775),1.87,(800,800))
    still(a.review/'hinge-and-open-deck-detail.webp',66,(1.20,-1.34,1.28),(.273,-.123,.865),.53,(720,640))
