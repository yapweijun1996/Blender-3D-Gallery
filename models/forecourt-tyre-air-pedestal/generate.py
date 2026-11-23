"""An original static tyre-air pedestal. Blender 5.3; dimensions aesthetic only."""
import argparse, math, sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
ID='forecourt-tyre-air-pedestal'; out=a.output.resolve()
for x in ('exports','previews'):(out/x).mkdir(parents=True,exist_ok=True)
if a.review:a.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
C={}
for i,n in enumerate(['Forecourt pedestal castings and recess','Pressure display, static and unnumbered','Continuous hose and compressed-air chuck','Forecourt apron and slab','Studio excluded']):
 c=bpy.data.collections.new(n);S.collection.children.link(c);C[i]=c
def mat(n,h,r=.6,m=0):
 def f(x):v=int(x,16)/255;return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
 o=bpy.data.materials.new(n);o.use_nodes=True;o.diffuse_color=(*[f(h[i:i+2]) for i in (0,2,4)],1)
 b=o.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=o.diffuse_color;b.inputs['Roughness'].default_value=r;b.inputs['Metallic'].default_value=m
 return o
enamel=mat('Deep petrol teal industrial enamel','1A6162',.47,.19)
head=mat('Bluer weatherproof panel','2F7876',.49,.15)
light=mat('Warm ivory generic label','F1DCAA',.57)
satin=mat('Bead blasted stainless steel','85918C',.42,.51)
screw=mat('Dark grey bolts and pedestal boots','515958',.58,.23)
inside=mat('Dark coated reel housing','283C3F',.72,.11)
rubber=mat('Moulded deep charcoal rubber','444A45',.59,.0)
rubber_lt=mat('Subtle grey fabric braid tint','59605A',.63)
glass=mat('Smoked instrument face, not transmissive','223839',.32,.24)
dial=mat('Neutral pale aqua display glyph','B7DDCC',.55)
gold=mat('Muted orange air-chuck shell','E79F50',.45,.16)
brr=mat('Warm metal ferrules','A99B76',.42,.56)
asph=mat('Cool damp-looking concrete','6C7872',.73)
slab=mat('Weathered utility pad concrete','8A8A73',.73)
edge=mat('Old ochre floor dash','B78E53',.70)
studio=mat('Studio background sole material','5A716D',.70)
def put(o,k):
 for c in list(o.users_collection):c.objects.unlink(o)
 C[k].objects.link(o);return o
def mesh(n,k,v,f,m,smooth=False):
 g=bpy.data.meshes.new(n);g.from_pydata(v,[],f);g.update()
 o=bpy.data.objects.new(n,g);C[k].objects.link(o);g.materials.append(m)
 for pp in g.polygons:pp.use_smooth=smooth
 return o
def box(n,k,c,d,m,b=.006,s=1):
 bpy.ops.mesh.primitive_cube_add();o=put(bpy.context.object,k);o.name=n;o.dimensions=d
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.location=c;o.data.materials.append(m)
 if b:
  x=o.modifiers.new('Manufactured edge breaks','BEVEL');x.width=b;x.segments=s
  x=o.modifiers.new('Broad steel panels remain planar','WEIGHTED_NORMAL');x.keep_sharp=True
 return o
def tube(n,k,pts,r,m,sides=8,close=False):
 p=list(map(Vector,pts));v=[];f=[]
 for i,l in enumerate(p):
  q=(p[(i+1)%len(p)] if close or i<len(p)-1 else p[i])-(p[i-1] if close or i else p[0]);q.normalize()
  e=q.cross(Vector((0,1,0)))
  if e.length<.075:e=q.cross(Vector((1,0,0)))
  e.normalize();b=q.cross(e).normalized()
  for j in range(sides):
   t=math.tau*j/sides;v.append(l+r*(e*math.cos(t)+b*math.sin(t)))
 for i in range(len(p) if close else len(p)-1):
  q=(i+1)%len(p)
  for j in range(sides):
   j1=(j+1)%sides;f.append((i*sides+j,i*sides+j1,q*sides+j1,q*sides+j))
 if not close:f.extend([tuple(reversed(range(sides))),tuple(range(len(v)-sides,len(v)))])
 o=mesh(n,k,v,f,m,True)
 if not close:
  for pp in o.data.polygons[-2:]:pp.use_smooth=False
 return o
def cz(n,k,x,y,z0,z1,r,m,segments=10):return tube(n,k,[(x,y,z0),(x,y,z1)],r,m,segments)
def cy(n,k,x,z,y0,y1,r,m,segments=10):return tube(n,k,[(x,y0,z),(x,y1,z)],r,m,segments)
def cubic(A,B,D,E,n):
 return [tuple((1-t)**3*x+3*(1-t)**2*t*y+3*(1-t)*t*t*z+t**3*w for x,y,z,w in zip(A,B,D,E)) for t in (i/n for i in range(n+1))]
# The apron is a bounded bit of fictional space, not the standardized location of anything.
box('Cut utility forecourt slab',3,(0,.025,.048),(1.167,.910,.096),asph,.028,2)
box('Raised pad under equipment feet',3,(-.028,.026,.117),(.775,.539,.054),slab,.020,2)
for x in (-.313,-.201,-.089,.023):
 box('Small interrupted apron stripe',3,(x,-.327,.098),(.072,.036,.004),edge,.001)
box('Powder-coated pedestal base',0,(-.026,.024,.155),(.623,.415,.048),screw,.012,2)
for x in (-.282,.229):
 for y in (-.136,.185):cz('Visible hex pad bolt',0,x,y,.177,.188,.018,satin,6)
# Individually closed cast walls form a genuinely open, recessed front.
box('Lower cabinet body',0,(-.026,.026,.253),(.625,.365,.168),enamel,.015,2)
box('Left structural cheek',0,(-.303,.019,.710),(.071,.395,.754),enamel,.008,2)
box('Right structural cheek',0,(.251,.019,.710),(.071,.395,.754),enamel,.008,2)
box('Recess deep back wall',0,(-.026,.134,.708),(.544,.132,.738),inside,.014,2)
box('Recess side return left',0,(-.260,-.012,.711),(.014,.299,.730),inside,.004)
box('Recess side return right',0,(.208,-.012,.711),(.014,.299,.730),inside,.004)
box('Open reel lower floor',0,(-.024,-.015,.340),(.52,.341,.031),inside,.005)
box('Open reel upper lip',0,(-.027,-.020,1.073),(.624,.408,.042),enamel,.011)
for x in (-.294,.240):
 box('Slim lighter upright wear strip',0,(x,-.185,.705),(.017,.021,.663),head,.004)
 for z in (.382,1.024):cy('Front access cover fastener',0,x,z,-.20,-.196,.009,satin,6)
box('Rear hinged access lid',0,(-.032,.218,.736),(.47,.039,.573),head,.015,2)
for x in (-.206,.138):
 for z in (.503,.958):cy('Rear access captive screw',0,x,z,.237,.243,.012,satin,6)
for z in (.574,.622,.670,.718):
 box('Rear moulded cooling slot shadow',0,(-.028,.241,z),(.343,.008,.013),inside,.004)
box('Kickplate protects lower panel',0,(-.027,-.164,.234),(.580,.026,.091),satin,.007)
for x in (-.252,.201):cy('Kickplate screw',0,x,.234,-.181,-.177,.010,screw,6)
# The display frame is a slanted, closed electronics head. UV-free graphics are authored geometry.
def F(x,z,offset=0):return (x,-.228+(z-1.078)*.227-offset,z)
def plate(n,k,x,z,w,h,off,th,m,bev=0):
 b=[(x-w/2,z-h/2),(x+w/2,z-h/2),(x+w/2,z+h/2),(x-w/2,z+h/2)]
 v=[F(q,r,t) for t in (off,off-th) for q,r in b]
 o=mesh(n,k,v,[(0,1,2,3),(7,6,5,4),(4,5,1,0),(5,6,2,1),(6,7,3,2),(7,4,0,3)],m)
 if bev:
  x=o.modifiers.new('Rolled edge radius','BEVEL');x.width=bev;x.segments=2
  x=o.modifiers.new('Hand finished planar front','WEIGHTED_NORMAL');x.keep_sharp=True
 return o
plate('Cast slanted head around instruments',1,-.027,1.259,.618,.362,0,.385,head,.015)
plate('Thin dark replaceable instrument panel',1,-.027,1.245,.544,.296,.011,.021,enamel,.010)
plate('Panel bottom narrow anodized trim',1,-.027,1.113,.517,.017,.027,.008,satin,.0035)
plate('Display acrylic recess with round corners',1,-.023,1.218,.325,.163,.023,.019,inside,.012)
plate('Smoked acrylic instrument face',1,-.023,1.219,.289,.134,.040,.012,glass,.009)
plate('Deflected visor with shallow lip',1,-.027,1.424,.633,.031,.052,.414,enamel,.009)
# A descriptive generic bilingual label with own monoline alphabet. No grades, units or numbers.
glyph={'A':[[(0,0),(.5,1),(1,0)],[(.21,.39),(.79,.39)]],
 'I':[[ (.5,0),(.5,1)]], 'R':[[(0,0),(0,1),(.80,1),(1,.80),(.80,.49),(0,.49)],[(.47,.49),(1,0)]],
 'N':[[(0,0),(0,1),(1,0),(1,1)]], 'G':[[(.99,.84),(.76,1),(.20,1),(0,.78),(0,.22),(.19,0),(.80,0),(1,.20),(1,.50),(.57,.50)]],
 '/':[[(.22,0),(.80,1)]], ' ':[]}
def text(n,chars,x,z,s,r,off,m):
 for i,ch in enumerate(chars):
  for j,seq in enumerate(glyph[ch]):
   tube(n+' '+str(i)+' '+str(j),1,[F(x+(i*.86+u*.55)*s,z+v*s,off) for u,v in seq],r,m,6)
text('Generic AIR / ANGIN lettermark','AIR / ANGIN',-.235,1.337,.050,.0048,.029,light)
# Abstract instrument dial with broad arc and indicator. Geometry carries no pressure scale.
cx=-.024;cz0=1.198
def cp(r,theta,off=.0425):return F(cx+r*math.cos(theta),cz0+r*math.sin(theta),off)
tube('Static unnumbered display arc',1,[cp(.047,math.radians(13+i*154/25)) for i in range(26)],.0042,dial,7)
tube('Fixed ivory pointer in decorative dial',1,[cp(.003,0,.047),cp(.034,math.radians(62),.047)],.0038,light,7)
for X in (-.241,.192):
 plate('Inset matte control housing',1,X,1.216,.042,.047,.027,.014,screw,.007)
 plate('Blank nonfunctional rubber control',1,X,1.216,.027,.014,.041,.011,dial,.005)
# One continuous bounded coil, openly visible in the dark front recess.
start=(-.143,-.065,1.028)
angles=math.tau*1.75
points=[]
for i in range(93):
 t=i/92;th=math.pi/2+t*angles
 # Slack is routed over two rounded span guides around a visible retainer.
 points.append((-.038+(.180+.026*t)*math.cos(th),-.108-.038*t,.681+(.233+.029*t)*math.sin(th)))
A=points[0];B=points[-1]
middle=(.185,-.223,.789); exit1=(.267,-.254,.835); end=(.348,-.206,.913)
route=cubic(start,(-.132,-.102,.994),(.026,-.107,A[2]+.010),A,12)[:-1]+points
route+=cubic(B,(.171,-.174,.724),(.173,-.215,.753),middle,10)[1:]
route+=cubic(middle,(.192,-.236,.836),(.229,-.254,.806),exit1,10)[1:]
route+=cubic(exit1,(.324,-.247,.873),(.347,-.206,.866),end,11)[1:]
hose=tube('AIR_CONTINUOUS_COIL_AND_LEAD',2,route,.0122,rubber,9)
hose['curve_rings']=len(route);hose['radial_vertices']=9
hose['wound_turns']=1.75
# Physical separate inlet collar and spool flange behind the tubing.
cy('Rear fixed reel hub',2,-.038,.679,.065,-.060,.112,screw,26)
cy('Outer reel plate and recessed spindle',2,-.038,.679,-.058,-.091,.103,inside,24)
cy('Capped spindle and hex centre',2,-.038,.679,-.088,-.107,.031,satin,10)
for X,z in ((-.199,.727),(.130,.742),(-.015,.484),(-.031,.882)):
 cy('Rounded coil spacer from rear wall',2,X,z,.050,-.104,.023,inside,12)
cy('Upper cabinet inlet sleeve',2,start[0],start[2],-.040,-.069,.022,brr,12)
# Roller bridge sits outside the front lip, while the stowed hose enters a small metal chuck.
tube('Bent outside fairlead bracket lower',2,[(.243,-.173,.807),(.248,-.228,.823),(.281,-.256,.804),(.307,-.222,.818)],.017,satin,8)
box('Side nozzle stay mounting flange',2,(.292,-.092,1.036),(.042,.195,.148),inside,.009)
box('Nozzle cradle horizontal bridge',2,(.336,-.189,.999),(.112,.095,.042),inside,.012,2)
tube('NOZZLE_CRADLE_FORK',2,[(.312,-.220,.994),(.315,-.254,.990),(.358,-.271,.990),(.391,-.250,.990),(.396,-.216,.994)],.014,satin,9)
cz('Chuck cable flex strain relief',2,end[0],end[1],.901,.954,.018,rubber_lt,12)
for zz in (.914,.925,.936):cz('Strain-relief rib',2,end[0],end[1],zz,zz+.005,.021,rubber,12)
cz('Small nickel nozzle coupling',2,end[0],end[1],.943,.993,.023,brr,12)
body=box('AIR_CHUCK_SMALL_STOWED_HANDLE',2,(.348,-.206,1.020),(.060,.056,.102),gold,.012,2)
tube('Short solid air-chuck jaw',2,[(.349,-.207,1.047),(.349,-.231,1.089),(.350,-.269,1.109)],.0165,satin,11)
tube('Short movable-looking but static thumb latch',2,[(.356,-.185,1.050),(.356,-.160,1.072),(.355,-.167,1.100)],.0089,gold,8)
tube('Dark sleeve at chuck tip',2,[(.35,-.266,1.107),(.35,-.282,1.115)],.0187,screw,10)
# Consolidate only grouped details, retaining named assets and material separation for authoring.
def join(k,n,fn):
 v=[o for o in C[k].objects if o.type=='MESH' and fn(o.name)]
 if len(v)<2:return
 bpy.ops.object.select_all(action='DESELECT')
 for ob in v:ob.select_set(True)
 bpy.context.view_layer.objects.active=v[0];bpy.ops.object.join();bpy.context.object.name=n
for k,n,pre in [(1,'FORCOURT_BILINGUAL_GEOMETRY','Generic AIR'),(0,'CABINET_REAR_COOLING_SLOTS','Rear moulded'),
 (3,'APRON_WORN_DASHES','Small interrupted'),(2,'REEL_GUIDES','Rounded coil spacer'),
 (2,'CHUCK_RIBS','Strain-relief')]:join(k,n,lambda q,p=pre:q.startswith(p))
box('Studio floor (excluded)',4,(0,0,-.026),(200,200,.046),studio,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,loc,power,size,col):
 d=bpy.data.lights.new(n,'AREA');d.energy=power;d.size=size;d.shape='DISK';d.color=col
 o=bpy.data.objects.new(n,d);C[4].objects.link(o);o.location=loc;look(o,(0,0,.92))
lamp('Open forecourt key',(-1.61,-2.22,3.12),298,2.0,(1,.90,.79))
lamp('Wide subdued reflection',(2.22,-1.09,2.24),155,2.18,(.84,.99,1))
lamp('Back separation',(1.07,1.34,2.73),187,1.46,(.83,.96,1))
w=bpy.data.worlds.new('Soft outdoor studio');w.use_nodes=True
S.world=w;w.node_tree.nodes['Background'].inputs[0].default_value=(.48,.61,.58,1);w.node_tree.nodes['Background'].inputs[1].default_value=.50
m=bpy.data.cameras.new('Studio camera');cam=bpy.data.objects.new('Studio camera',m);C[4].objects.link(cam);S.camera=cam;m.type='ORTHO';m.ortho_scale=1.71
cam.location=(1.68,-3.88,2.27);look(cam,(.007,-.017,.761))
S.render.engine='CYCLES';S.cycles.samples=48;S.cycles.use_denoising=sys.platform=='darwin'
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_x=S.render.resolution_y=512;S.render.resolution_percentage=100
S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=92
S.view_settings.view_transform='AgX';S.view_settings.exposure=.08
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(ID+'.blend')),compress=True)
def render(to,pos,t,ortho,n):
 cam.location=pos;look(cam,t);m.ortho_scale=ortho
 S.render.resolution_x,S.render.resolution_y=n;S.render.filepath=str(to);bpy.ops.render.render(write_still=True)
if not a.skip_render:render(out/'previews/studio.webp',(1.68,-3.88,2.27),(.007,-.017,.761),1.71,(512,512))
if a.review:
 render(a.review/'hose-and-chuck.webp',(1.45,-3.5,1.33),(.039,-.117,.765),.840,(720,650))
 render(a.review/'face.webp',(.491,-3.24,2.15),(-.018,-.108,1.246),.746,(720,480))
bpy.ops.object.select_all(action='DESELECT')
for k in range(4):
 for ob in C[k].objects:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/f'{ID}.glb'),export_format='GLB',use_selection=True,export_texcoords=False,export_animations=False)
