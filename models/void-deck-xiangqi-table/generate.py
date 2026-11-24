"""Original Singapore void-deck Xiangqi table still life; Blender 5.3."""
import argparse, math, random, sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path);p.add_argument('--skip-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
ID='void-deck-xiangqi-table'; out=a.output.resolve()
for x in ('exports','previews'):(out/x).mkdir(parents=True,exist_ok=True)
if a.review:a.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
C={}
for i,n in enumerate(['Public floor display pad','Cast terrazzo table and four stools','Integral Xiangqi board and river','Ten individual static demonstration pieces','Studio excluded']):
 c=bpy.data.collections.new(n);S.collection.children.link(c);C[i]=c
def mat(n,h,r=.6,m=0):
 def f(x):v=int(x,16)/255;return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
 o=bpy.data.materials.new(n);o.use_nodes=True;o.diffuse_color=(*[f(h[i:i+2]) for i in (0,2,4)],1)
 b=o.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=o.diffuse_color
 b.inputs['Roughness'].default_value=r;b.inputs['Metallic'].default_value=m
 return o
fert=mat('Cool warm-grey precast aggregate','9C9D86',.70)
topp=mat('Ivory pale terrazzo skim','C4B495',.65)
green=mat('Faded sage banding on seat collars','687E6B',.66)
shadow=mat('Dark worn edge underside','818D77',.73)
grid=mat('Dark muted khaki inset grid','39473B',.65)
river=mat('Soft jade river hint','A8B099',.68)
warm=mat('Soft ochre cast aggregate chips','A78C69',.67)
chalk=mat('Pale quartz chips','E4D9B5',.63)
sage=mat('Sage aggregate chips','82947E',.66)
plinth=mat('Sheltered cool concrete pad','737A72',.84)
floor=mat('Mix of old light shelter paving','A1A385',.82)
floor2=mat('Mute dusty shelter paving','929880',.83)
redWood=mat('Quiet ivory boxwood red side','E6BB85',.54)
darkWood=mat('Cool brown-stained boxwood dark side','A38258',.55)
red=mat('Brick-red counters and engraved letter fill','AB4639',.51)
black=mat('Dark charcoal letter fill, not pitch black','343B35',.55)
studio=mat('Muted atelier backdrop','688376',.77)
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
def multi(n,k,v,f,mats,mi,smooth=False):
 o=mesh(n,k,v,f,mats[0],smooth)
 for m in mats[1:]:o.data.materials.append(m)
 for i,p in enumerate(o.data.polygons):p.material_index=mi[i]
 return o
def join(n,obs):
 if len(obs)<2:return obs[0]
 bpy.ops.object.select_all(action='DESELECT');bpy.context.view_layer.objects.active=obs[0]
 for o in obs:o.select_set(True)
 bpy.ops.object.join();o=bpy.context.object;o.name=n;return o
def lathe(n,k,x,y,p,ml,sides=24):
 v=[];f=[];ms=[]
 for r,z,m in p:
  for i in range(sides):
   t=math.tau*i/sides
   v.append((x+r*math.cos(t),y+r*math.sin(t),z))
 for j in range(len(p)-1):
  for i in range(sides):
   f.append((j*sides+i,j*sides+(i+1)%sides,(j+1)*sides+(i+1)%sides,(j+1)*sides+i));ms.append(p[j][2])
 f.append(tuple(reversed(range(sides))));ms.append(p[0][2])
 f.append(tuple(range((len(p)-1)*sides,len(p)*sides)));ms.append(p[-1][2])
 o=multi(n,k,v,f,ml,ms,True)
 for p in o.data.polygons[-2:]:p.use_smooth=False
 return o
# Sparse cast slab context, not a whole block/standard drawing.
box('Cloud-grey paving display base',0,(0,0,.033),(2.212,2.188,.066),plinth,.022,2)
for r in range(3):
 for c in range(3):
  box('Sheltered paving tile',0,((c-1)*.714,(r-1)*.714,.077),(.704,.704,.027),floor2 if (r+c*2)%5==4 else floor,.006)
T=.800
table=box('TABLE_ROUNDED_CAST_TERRAZZO_TOP',1,(0,0,.741),(1.118,1.129,.118),topp,.028,3)
box('Sage toned structural ring below tabletop',1,(0,0,.685),(.965,.969,.037),green,.014,2)
lathe('TABLE_SOLID_CAST_TAPER_AND_FOOT',1,0,0,[(.272,.085,1),(.272,.109,1),(.239,.154,0),(.175,.204,0),
  (.145,.588,0),(.196,.657,0),(.230,.672,0),(.230,.688,0)],[fert,shadow],20)
seats=[('front',0,-.862),('back',0,.862),('left',-.860,0),('right',.860,0)]
for n,x,y in seats:
 lathe('STOOL_'+n.upper()+'_SOLID_CAST_SEAT',1,x,y,[(.145,.088,1),(.150,.118,1),(.118,.160,0),(.096,.353,0),
 (.129,.382,0),(.156,.400,2),(.164,.415,2),(.164,.443,3),(.151,.457,3)],[fert,shadow,green,topp],24)
# Original irregular terrazzo flecks use low, coplanar inset color patches (no stock raster or texture).
rnd=random.Random(271994)
v=[];f=[];mi=[]
def chip(x,y,z,mag,j):
 base=len(v);k=rnd.choice([4,5,6]);a=rnd.random()*math.tau
 for i in range(k):
  t=a+math.tau*i/k;r=mag*(.55+rnd.random()*.50)
  v.append((x+r*math.cos(t),y+r*math.sin(t),z))
 f.append(tuple(range(base,len(v))));mi.append(j%3)
for j in range(148):
 x=rnd.uniform(-.521,.521);y=rnd.uniform(-.540,.540)
 if abs(x)<.400 and abs(y)<.446:continue
 chip(x,y,T+.00010,rnd.uniform(.003,.0102),j)
for n,x,y in seats:
 for j in range(30):
  t=rnd.random()*math.tau;r=.139*math.sqrt(rnd.random())
  chip(x+math.cos(t)*r,y+math.sin(t)*r,.45715,rnd.uniform(.0027,.0065),j)
chips=multi('TERRAZZO_RESTRAINED_ORIGINAL_AGGREGATE',1,v,f,[chalk,warm,sage],mi)
# Intersection board, nine FILES x ten RANKS. The two exterior files bridge the river; all seven inner files do not.
sp=.092; X=[(i-4)*sp for i in range(9)]; Y=[(j-4.5)*sp for j in range(10)]
tile=box('BOARD_FIXED_INTEGRAL_INSET',2,(0,0,T-.00055),(.801,.892,.0034),topp,.00042)
xb=.368
vr=[];fr=[];mi=[]
def strip(a,b,width,idx,z=T+.00175):
 ax,ay=a;bx,by=b;L=math.hypot(bx-ax,by-ay);ux=-(by-ay)*width/(2*L);uy=(bx-ax)*width/(2*L)
 n=len(vr)
 vr.extend([(ax+ux,ay+uy,z),(ax-ux,ay-uy,z),(bx-ux,by-uy,z),(bx+ux,by+uy,z)])
 fr.append(tuple(range(n,n+4)));mi.append(idx)
def rect(x1,y1,x2,y2,idx,z):
 n=len(vr);vr.extend([(x1,y1,z),(x2,y1,z),(x2,y2,z),(x1,y2,z)]);fr.append(tuple(range(n,n+4)));mi.append(idx)
rect(-xb,-.046,+xb,.046,1,T+.00146)
for j,y in enumerate(Y):
 strip((-xb-.0017,y),(xb+.0017,y),.0044,0)
for i,x in enumerate(X):
 for j in range(9):
  if j==4 and i not in (0,8):continue
  strip((x,Y[j]+.0022),(x,Y[j+1]-.0022),.0034,0)
for low,high in ((0,2),(7,9)):
 strip((X[3],Y[low]),(X[5],Y[high]),.0033,0,T+.00179)
 strip((X[5],Y[low]),(X[3],Y[high]),.0033,0,T+.00180)
for i in (0,2,4,6,8):
 for j in (3,6):
  if i not in (0,8): sx=(-1,1)
  else:sx=(1,) if i==0 else (-1,)
  for xg in sx:
   for yg in (-1,1):
    x=X[i]+xg*.0102;y=Y[j]+yg*.0102
    strip((x+xg*.0107,y),(x,y),.0016,0)
    strip((x,y),(x,y+yg*.0097),.0016,0)
board=multi('XIANGQI_INTEGRAL_GRID_RIVER_PALACES',2,vr,fr,[grid,river],mi)
board['files']=9;board['ranks']=10;board['inner_river_breaks']=7;board['fixed_display']=True
# Small original monoline engraving glyphs (no font or outside artwork).
# These are sign-legibility abstractions, not copied typeface outlines.
glyph={
 '帅':[[(.15,.84),(.15,.26),(.10,.15)],[(.28,.95),(.28,.34),(.23,.18),(.08,.06)],
       [(.43,.28),(.43,.74),(.90,.74),(.90,.28),(.83,.24)],[(.66,.96),(.66,.08)]],
 '将':[[(.13,.78),(.27,.66)],[(.08,.39),(.27,.49)],[(.28,.96),(.28,.08)],
       [(.57,.96),(.45,.72),(.77,.72),(.68,.60),(.48,.50)],[(.54,.69),(.64,.63)],
       [(.43,.43),(.92,.43)],[(.72,.57),(.72,.10),(.60,.08),(.53,.17)],[(.48,.35),(.58,.25)]],
 '车':[[(.16,.79),(.89,.79)],[(.48,.95),(.26,.59),(.85,.59)],
        [(.16,.36),(.90,.36)],[(.59,.69),(.59,.09)]],
 '马':[[(.19,.88),(.82,.88),(.75,.53)],[(.31,.87),(.27,.54),(.86,.54),(.82,.16),(.72,.08),(.59,.16)],[(.15,.31),(.72,.31)]],
 '炮':[[(.08,.59),(.18,.73)],[(.27,.92),(.27,.47),(.20,.24),(.09,.12)],[(.37,.67),(.28,.53)],[(.28,.40),(.40,.24)],
       [(.60,.94),(.45,.70),(.88,.70),(.84,.33),(.74,.33)],[(.54,.55),(.71,.55),(.71,.41),(.56,.41),(.56,.17),(.84,.17),(.90,.26)]],
 '兵':[[(.29,.69),(.75,.90)],[(.32,.73),(.32,.41)],[(.32,.66),(.81,.66)],[(.66,.66),(.66,.41)],[(.14,.41),(.90,.41)],
       [(.44,.27),(.20,.12)],[(.62,.27),(.83,.10)]],
 '卒':[[(.51,.93),(.60,.81)],[(.14,.75),(.88,.75)],[(.38,.68),(.21,.47)],[(.34,.58),(.46,.48)],
       [(.68,.68),(.54,.48)],[(.66,.57),(.79,.48)],[(.13,.38),(.90,.38)],[(.52,.42),(.52,.09)]],
}
pieces=[('red','general','帅',4,0),('red','chariot','车',8,2),('red','horse','马',2,2),
 ('red','cannon','炮',7,4),('red','soldier','兵',4,4),('dark','general','将',4,9),
 ('dark','chariot','车',0,7),('dark','horse','马',6,7),('dark','cannon','炮',1,5),('dark','soldier','卒',6,6)]
rest=T+.00227
for side,role,letter,ix,iy in pieces:
 x=X[ix];y=Y[iy];n='XIANGQI_'+side.upper()+'_'+role.upper()
 ob=lathe(n,3,x,y,[(.0300,rest,0),(.0342,rest+.002,0),(.0352,rest+.0068,0),
  (.0347,rest+.0130,0),(.0322,rest+.0170,0),(.0312,rest+.0183,0)],
  [redWood if side=='red' else darkWood],20)
 ob['file']=ix;ob['rank']=iy;ob['side']=side;ob['role']=role
 ink=red if side=='red' else black
 d=1 if side=='red' else -1
 decorative=[]
 decorative.append(tube('Ink border rim',3,[(x+.0254*math.cos(i*math.tau/22),y+.0254*math.sin(i*math.tau/22),rest+.0184) for i in range(22)],.0010,ink,5,True))
 for k,line in enumerate(glyph[letter]):
  coords=[(x+d*(u-.5)*.033,y+d*(v-.50)*.033,rest+.01855) for u,v in line]
  decorative.append(tube('Individually drawn character stroke',3,coords,.00108,ink,5))
 letters=join(n+'_ENGRAVING',decorative)
 if len(decorative)==1:letters.name=n+'_ENGRAVING'
# Native proof framing.
box('Studio floor ignored',4,(0,0,-.029),(200,200,.05),studio,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,c,power,size,color):
 l=bpy.data.lights.new(n,'AREA');l.energy=power;l.size=size;l.shape='DISK';l.color=color
 o=bpy.data.objects.new(n,l);C[4].objects.link(o);o.location=c;look(o,(0,0,.40))
lamp('Sheltered morning daylight',(-2.0,-3.09,3.46),339,2.35,(1,.91,.76))
lamp('Opens paving shadows',(2.33,-1.66,2.20),164,2.37,(.83,.97,1))
lamp('Gentle raised-aggregate rim',(-1.02,2.19,3.18),174,1.65,(.88,1,.92))
w=bpy.data.worlds.new('Neutral void-deck gallery set');S.world=w;w.use_nodes=True
w.node_tree.nodes['Background'].inputs[0].default_value=(.51,.62,.54,1);w.node_tree.nodes['Background'].inputs[1].default_value=.49
m=bpy.data.cameras.new('Studio camera');cam=bpy.data.objects.new('Studio camera',m);C[4].objects.link(cam);S.camera=cam;m.type='ORTHO';m.ortho_scale=2.93
cam.location=(2.38,-3.59,2.72);look(cam,(.006,.017,.42))
S.render.engine='CYCLES';S.cycles.samples=48;S.cycles.use_denoising=sys.platform=='darwin'
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_x=S.render.resolution_y=512;S.render.resolution_percentage=100
S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=92
S.view_settings.view_transform='AgX';S.view_settings.exposure=.082
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(ID+'.blend')),compress=True)
def render(to,pos,t,ortho,n):
 cam.location=pos;look(cam,t);m.ortho_scale=ortho
 S.render.resolution_x,S.render.resolution_y=n;S.render.filepath=str(to);bpy.ops.render.render(write_still=True)
if not a.skip_render:render(out/'previews/studio.webp',(2.38,-3.59,2.72),(.006,.017,.42),2.93,(512,512))
if a.review:
 render(a.review/'integral-board.webp',(.035,-.162,3.47),(0,0,T),1.12,(660,700))
 render(a.review/'cast-pedestal.webp',(2.46,-2.96,1.36),(0,-.03,.41),2.64,(720,530))
bpy.ops.object.select_all(action='DESELECT')
for k in range(4):
 for ob in C[k].objects:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/f'{ID}.glb'),export_format='GLB',use_selection=True,export_texcoords=False,export_animations=False)
