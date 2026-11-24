"""Original museum-inspired rubber-sheet roller display. Blender 5.3."""
import argparse, math, sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path);p.add_argument('--skip-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
ID='heritage-rubber-sheet-roller'; out=a.output.resolve()
for x in ('exports','previews'):(out/x).mkdir(parents=True,exist_ok=True)
if a.review:a.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
C={}
for i,n in enumerate(['Weathered workshop frame','Two in-line roller drums and crank','Mock sheet and support tables','Studio excluded']):
 c=bpy.data.collections.new(n);S.collection.children.link(c);C[i]=c
def mat(n,h,r=.6,m=0):
 def f(x):v=int(x,16)/255;return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
 o=bpy.data.materials.new(n);o.use_nodes=True;o.diffuse_color=(*[f(h[i:i+2]) for i in (0,2,4)],1)
 b=o.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=o.diffuse_color
 b.inputs['Roughness'].default_value=r;b.inputs['Metallic'].default_value=m
 return o
cast=mat('Oxidised grey-green cast frame','5D6656',.53,.27)
black=mat('Darkening iron on cast feet','4B5145',.58,.32)
steel=mat('Worn satin roller and cap steel','929587',.51,.53)
darksteel=mat('Patinated roller ridges','727D72',.59,.41)
gear=mat('Tarnished umber gearing','7A6750',.58,.39)
bolts=mat('Softly bright flattened iron bolts','A49A79',.48,.51)
wood=mat('Dark rubberwood support','886548',.72)
woodlight=mat('Worn warm rubberwood end','A7865D',.69)
woodedge=mat('Dark edge band and wheel','594A39',.66)
sheet=mat('Matte wheat-coloured mock sheet','D4A355',.65)
sheetside=mat('Warm umber sheet edge','BE8948',.74)
sheetother=mat('Unmarked lighter face of sheet','DCAC63',.71)
whole=mat('Dusty olive studio floor','758071',.76)
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
def pol(n,k,v,f,ml,idx=None,smooth=False):
 ob=mesh(n,k,v,f,ml[0],smooth)
 for m in ml[1:]:ob.data.materials.append(m)
 if idx:
  for i,pp in enumerate(ob.data.polygons):pp.material_index=idx[i]
 return ob
def cyl(n,k,A,B,r,m,s=12):return tube(n,k,[A,B],r,m,s)
def xc(n,k,x0,x1,z,r,m,s=16,y=0):return cyl(n,k,(x0,y,z),(x1,y,z),r,m,s)
def yz_prism(n,k,xctr,width,outline,m):
 # CCW in YZ is outward +X.
 area=sum(y*q-z*p for (y,z),(p,q) in zip(outline,outline[1:]+outline[:1]))
 if area<0:outline=list(reversed(outline))
 vs=[(xctr+d*width/2,y,z) for d in (-1,1) for y,z in outline]
 L=len(outline)
 fs=[tuple(reversed(range(L))),tuple(range(L,2*L))]+[(i,(i+1)%L,(i+1)%L+L,i+L) for i in range(L)]
 ob=mesh(n,k,vs,fs,m)
 bevel=ob.modifiers.new('Casting breaks','BEVEL');bevel.width=.006;bevel.segments=2
 wn=ob.modifiers.new('Flat cheeks','WEIGHTED_NORMAL');wn.keep_sharp=True
 return ob
def grouped(n,obs):
 if len(obs)<2:return obs[0]
 bpy.ops.object.select_all(action='DESELECT')
 bpy.context.view_layer.objects.active=obs[0]
 for o in obs:o.select_set(True)
 bpy.ops.object.join();ob=bpy.context.object;ob.name=n
 return ob
# Rectangular partly-open stand, with real crossbars and recognizable cast side cheeks.
box('Low narrow workshop display base',0,(0,.018,.045),(1.105,.865,.090),woodedge,.019,2)
for i,y in enumerate((-.276,-.127,.022,.171,.320)):
 box('Separate old wood display board',0,(0,y,.100),(1.065,.143,.028),woodlight if i%3==1 else wood,.006,2)
for x in (-.320,.320):
 box('Welded low frame rail',0,(x,0,.157),(.069,.653,.081),black,.008,2)
 for y in (-.257,.258):
  box('Wide flange at foot',0,(x,y,.124),(.132,.126,.041),cast,.008)
  for X in (x-.043,x+.043):
   cyl('Visible rounded hex cast-foot bolt',0,(X,y,.142),(X,y,.155),.014,bolts,6)
 for y in (-1,1):
  yz_prism('Splayed tapered frame leg',0,x,.061,[(y*.244,.178),(y*.160,.206),(y*.086,.598),(y*.113,.648),(y*.174,.631),(y*.228,.324)],cast)
 yz_prism('Bifurcated vertical roller bearing housing',0,x,.079,[(-.146,.605),(-.147,.914),(-.100,.957),(.075,.963),(.122,.924),(.141,.641),(.089,.607)],cast)
for y in (-.137,.142):
 box('Long frame lower braces',0,(0,y,.377),(.655,.041,.033),black,.003)
box('Rigid cast top bridge',0,(0,.016,.964),(.733,.071,.061),cast,.010,2)
for x in (-.336,.336):
 box('Cast top bearing cap',0,(x,.016,1.005),(.105,.110,.039),black,.007)
 cyl('Short capped top adjusting post (fixed)',0,(x,.016,1.009),(x,.016,1.060),.013,bolts,10)
 cyl('Original rounded top adjuster',0,(x,.016,1.056),(x,.016,1.079),.032,gear,10)
# Two separately editable x-axis rollers. Actual groove radius changes; not a decal, pattern or image.
LO=.691;HI=.865;RR=.083;ROW=.294
smooth=xc('RUBBER_ROLLER_SMOOTH_LOWER',1,-ROW,ROW,LO,RR,steel,48)
def roller(n,z,s,section,mats):
 v=[]; f=[]; mi=[]
 for x in (-ROW,ROW):
  for i in range(s):
   t=math.tau*i/s; r=section[i%len(section)];v.append((x,r*math.cos(t),z+r*math.sin(t)))
 # Clockwise from positive X at x=-ROW, counterclockwise at x=+ROW.
 f=[tuple(reversed(range(s))),tuple(range(s,2*s))];mi=[1,1]
 for i in range(s):
  j=(i+1)%s;f.append((i,j,j+s,i+s));mi.append(0 if section[i%len(section)]>=.081 else 1)
 ob=pol(n,1,v,f,mats,mi)
 for pp in ob.data.polygons[2:]:pp.use_smooth=False
 return ob
# 24 visibly ridged profile breaks running along the full drum span.
rib=roller('RUBBER_ROLLER_RIBBED_UPPER',HI,96,[.0782,.083,.083,.0782],[steel,darksteel])
for Z in (LO,HI):
 for x in (-1,1):
  xc('Raised bearing race flange',1,x*.286,x*.332,Z,.069,black,20)
  xc('Axle hub in each cassette',1,x*.315,x*.379,Z,.036,bolts,14)
  for y in (-.089,.087):
   xc('Rivet in fixed frame cheek',1,x*.350,x*.369,Z,.013,bolts,7,y)
def gear_ring(n,x0,x1,z,teeth,low,hi,phase):
 nseg=4*teeth
 rs=[low,hi,hi,low]
 v=[]
 for x in (x0,x1):
  for i in range(nseg):
   t=phase+i*math.tau/nseg;r=rs[i%4];v.append((x,r*math.cos(t),z+r*math.sin(t)))
 f=[tuple(reversed(range(nseg))),tuple(range(nseg,2*nseg))]
 for i in range(nseg):
  k=(i+1)%nseg;f.append((i,k,k+nseg,i+nseg))
 return mesh(n,1,v,f,gear)
gear_ring('Exposed lower fictional gear silhouette',-.410,-.381,LO,16,.077,.088,math.pi/320)
gear_ring('Exposed upper fictional gear silhouette',-.410,-.381,HI,16,.077,.088,math.pi/16)
for Z in (LO,HI):
 xc('Capped gear axle visible inboard',1,-.434,-.405,Z,.031,steel,14)
xc('Crank attaches to upper roller axle',1,.347,.441,HI,.028,bolts,14)
cyl('RUBBER_FIXED_HAND_CRANK',1,(.427,0,HI),(.463,-.136,.980),.019,black,10)
cyl('Crank handle elbow',1,(.462,-.134,.976),(.568,-.134,.976),.016,bolts,12)
cyl('Warm hand grip, static',1,(.491,-.134,.976),(.563,-.134,.976),.026,woodlight,16)
for xx in (.498,.556):xc('Thin turned grip end bead',1,xx-.004,xx+.004,.976,.028,woodedge,14,-.134)
# Staged mock sheet travels across the virtual nip, then curls forward over one wood tray ledge.
for i in range(4):
 box('Stationary inlet table softwood slat',2,(0,.176+.063*i,.745+.007*i-(.004 if i==3 else 0)),(.638,.056,.044),woodlight if i==1 else wood,.006)
for x in (-.312,.312):box('Inlet tray side support',2,(x,.259,.716),(.046,.304,.045),black,.008)
for i in range(4):
 Z=.714-.011*i-(.009 if i==3 else 0)
 box('Stationary outfeed tray board',2,(0,-.170-.053*i,Z),(.636,.048,.043),woodlight if i==1 else wood,.005)
for x in (-.300,.300):
 yz_prism('Small tray ledge side stay',2,x,.043,[(-.378,.674),(-.151,.718),(-.151,.694),(-.327,.624)],black)
# Sheet edge shape and ribbed channels are explicit physical surfaces.
NX=8; NY=82
sf=[]
def sheet_row(u,t,d):
 y=.430-1.012*t
 x=(.261*(1-.017*math.cos(math.pi*t)+.011*math.sin(6*math.pi*t+.6)))*(2*u-1)
 z=.7794+.015*max(0,(y-.157)/.273)**2
 if y<-.091:
  k=min(1,(-y-.091)/.491)
  z-=.171*k**1.20
  z+=min(1,(-y-.091)/.078)*.0032*math.sin(math.tau*(23*k)+.15*math.sin(math.pi*u))
 return (x,y,z+d)
for side in range(2):
 for i in range(NY+1):
  for j in range(NX+1):sf.append(sheet_row(j/NX,i/NY,(-.001 if side==0 else .0041)))
N=(NY+1)*(NX+1);Q=NX+1;faces=[];mid=[]
for i in range(NY):
 for j in range(NX):
  h=i*Q+j;k=h+Q
  ids=(h,h+1,k+1,k) # Downward normal on bottom.
  faces.extend([ids,tuple(x+N for x in reversed(ids))]);mid.extend([2,0])
ring=[j for j in range(Q)]+[i*Q+(Q-1) for i in range(1,NY+1)]+[NY*Q+j for j in range(Q-2,-1,-1)]+[i*Q for i in range(NY-1,0,-1)]
for x,y in zip(ring,ring[1:]+ring[:1]):faces.append((y,x,x+N,y+N));mid.append(1)
skin=pol('RUBBER_MOCK_SHEET_RIBBED_OUTFEED',2,sf,faces,[sheet,sheetside,sheetother],mid,True)
for p in skin.data.polygons[-len(ring):]:p.use_smooth=False
# Keep distinct named pieces while batching repeated cast bolts and slats.
for k,name,p in [(0,'CAST_FOOT_FASTENERS','Visible rounded'),(0,'WOODEN_DISPLAY_BOARD_SURFACE','Separate old'),
                 (1,'ROLLER_BEARING_RACES','Raised bearing'),(1,'ROLLER_HUBS','Axle hub'),(1,'CAST_CHEEK_RIVETS','Rivet'),
                 (2,'INLET_WORKTRAY_SLATS','Stationary inlet'),(2,'OUTFEED_WORKTRAY_SLATS','Stationary outfeed')]:
 obs=[o for o in C[k].objects if o.name.startswith(p)]
 if obs:grouped(name,obs)
box('Studio floor ignored',3,(0,0,-.029),(200,200,.05),whole,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,c,power,size,color):
 l=bpy.data.lights.new(n,'AREA');l.energy=power;l.size=size;l.shape='DISK';l.color=color
 o=bpy.data.objects.new(n,l);C[3].objects.link(o);o.location=c;look(o,(0,0,.75))
lamp('Soft museum key',(-1.58,-2.16,3.12),263,1.85,(1,.87,.70))
lamp('Clean roller sheen',(2.44,-1.38,1.93),136,1.98,(.84,.96,1))
lamp('Edge reflection',(1.04,1.88,2.85),192,1.63,(.85,1,.95))
w=bpy.data.worlds.new('Neutral museum skylight');S.world=w;w.use_nodes=True
w.node_tree.nodes['Background'].inputs[0].default_value=(.48,.56,.49,1);w.node_tree.nodes['Background'].inputs[1].default_value=.49
m=bpy.data.cameras.new('Studio camera');cam=bpy.data.objects.new('Studio camera',m);C[3].objects.link(cam);S.camera=cam;m.type='ORTHO';m.ortho_scale=1.44
cam.location=(1.64,-3.10,2.05);look(cam,(.004,-.037,.535))
S.render.engine='CYCLES';S.cycles.samples=44;S.cycles.use_denoising=sys.platform=='darwin'
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
if not a.skip_render:render(out/'previews/studio.webp',(1.64,-3.10,2.05),(.004,-.037,.535),1.44,(512,512))
if a.review:
 render(a.review/'sheet-and-roller.webp',(1.18,-2.74,1.63),(.034,-.203,.791),1.13,(760,560))
 render(a.review/'rear-gears.webp',(-1.38,2.65,1.79),(-.095,.065,.760),1.32,(720,560))
bpy.ops.object.select_all(action='DESELECT')
for k in range(3):
 for ob in C[k].objects:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/f'{ID}.glb'),export_format='GLB',use_selection=True,export_texcoords=False,export_animations=False)
