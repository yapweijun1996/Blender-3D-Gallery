"""Original static Wau Bulan workshop display; authored with Blender 5.3."""
import argparse, math, sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon, delaunay_2d_cdt
P=argparse.ArgumentParser()
P.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
P.add_argument('--review',type=Path)
P.add_argument('--skip-render',action='store_true')
A=P.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
ID='wau-bulan-workshop-display'; O=A.output.resolve()
for s in ('exports','previews'):(O/s).mkdir(parents=True,exist_ok=True)
if A.review:A.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
SC=bpy.context.scene;SC.unit_settings.system='METRIC'
C={}
for i,n in enumerate(['Paper sail and crescent','Original layered paper ornament','Bowed spine spars and tied bridle','Workshop display cradle and offcuts','Studio excluded']):
 c=bpy.data.collections.new(n);SC.collection.children.link(c);C[i]=c
def rgb(h):
 def lin(s):
  t=int(s,16)/255
  return t/12.92 if t<=.04045 else ((t+.055)/1.055)**2.4
 return tuple(lin(h[i:i+2]) for i in (0,2,4))
def mat(n,h,rough=.62):
 m=bpy.data.materials.new(n);m.use_nodes=True;m.diffuse_color=(*rgb(h),1)
 p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Roughness'].default_value=rough
 return m
sail=mat('Indigo dyed paper','163454',.73)
back=mat('Blue black reverse paper','2F4557',.78)
seam=mat('Ochre edge piping','C8994E',.68)
rim=mat('Warm ivory applique paper','F6C878',.71)
mint=mat('Pale green cut paper','64CDB0',.69)
pink=mat('Rust coral cut paper','E57654',.75)
cream=mat('Light muted silk paper','FAE0AF',.67)
bamboo=mat('Waxed warm bamboo','B4854D',.62)
joint=mat('Darker bamboo and joint lash','745232',.74)
cord=mat('Twisted ivory cotton cord','DDD2B2',.88)
dark=mat('Old hardwood peg','4B3026',.64)
ground=mat('Stone studio backdrop','758789',.74)
def linked(o,k):
 for c in list(o.users_collection):c.objects.unlink(o)
 C[k].objects.link(o);return o
def mesh(n,k,v,f,mats,mi=None,smooth=False):
 me=bpy.data.meshes.new(n);me.from_pydata(v,[],f);me.update()
 ob=bpy.data.objects.new(n,me);C[k].objects.link(ob)
 for m in mats:me.materials.append(m)
 for i,p in enumerate(me.polygons):p.material_index=mi[i] if mi else 0;p.use_smooth=smooth
 return ob
def curve2(start,segments):
 out=[start]
 for p1,p2,p3,steps in segments:
  p0=out[-1]
  for i in range(1,steps+1):
   t=i/steps;u=1-t
   out.append(tuple(u**3*a+3*u*u*t*b+3*u*t*t*c+t**3*d for a,b,c,d in zip(p0,p1,p2,p3)))
 return out
def mirror(a):return a+[(-x,z) for x,z in list(reversed(a))[1:-1]]
def triangulate(a):
 p=[Vector((x,z,0)) for x,z in a];ids={tuple(q):i for i,q in enumerate(p)}
 return [tuple(q if isinstance(q,int) else ids[tuple(q)] for q in t) for t in tessellate_polygon([p])]
# metres; each wing is swept upward, independent crescent tail dips beneath the inward arch.
body=mirror(curve2((0,1.904),[
 ((.068,1.840),(.155,1.783),(.242,1.758),8),((.467,1.661),(.686,1.682),(.875,1.755),15),
 ((.817,1.626),(.707,1.542),(.598,1.525),10),((.480,1.462),(.345,1.414),(.269,1.322),11),
 ((.175,1.210),(.083,1.177),(0,1.174),11)]))
tail=mirror(curve2((0,1.139),[
 ((.125,1.129),(.279,1.190),(.411,1.298),15),((.421,1.145),(.349,.978),(.236,.931),14),
 ((.177,.892),(.092,.873),(0,.872),11)]))
def bow(x,z):return .048*(x/.875)**2+.057*((z-1.371)/.533)**2-.062+.045*(1.904-z)
def xyz(x,z,w=0):return (x,bow(x,z)+w,z)
# A constrained, near-uniform lattice preserves the bow and avoids coplanar-looking slim ears.
def panel(n,a):
 pts=list(reversed(a))  # CCW in the paper plane (Blender -Y outward).
 boundary=len(pts)
 def contained(x,z):
  odd=False;distance=100
  for j,(x0,z0) in enumerate(pts[:boundary]):
   x1,z1=pts[(j+1)%boundary]
   if (z0>z)!=(z1>z) and x < x0+(z-z0)*(x1-x0)/(z1-z0):odd=not odd
   X,Z=x1-x0,z1-z0
   t=max(0,min(1,((x-x0)*X+(z-z0)*Z)/(X*X+Z*Z)))
   distance=min(distance,math.hypot(x-x0-t*X,z-z0-t*Z))
  return odd and distance>.023
 for row in range(22):
  z=.879+row*.05
  for j in range(-17,18):
   x=.052*(j+(row%2)*.5)
   if contained(x,z):pts.append((x,z))
 v,e,t,refs,_,_=delaunay_2d_cdt([Vector(q) for q in pts],[],[tuple(range(boundary))],1,1e-6)
 target={p[0]:j for j,p in enumerate(refs) if len(p)==1}
 ring=[target[j] for j in reversed(range(boundary))]
 # Sharp cut front/reverse edge, analytically smooth normals across each bowed cap.
 f=[]
 for i,j,k in t:
  ax,az=v[i]; bx,bz=v[j]; cx,cz=v[k]
  f.append((i,j,k) if (bx-ax)*(cz-az)-(bz-az)*(cx-ax)>0 else (i,k,j))
 vv=[xyz(x,z,.003*d) for d in (0,1) for x,z in v];nn=len(v)
 fs=f+[tuple(i+nn for i in reversed(m)) for m in f]; matid=[0]*len(f)+[1]*len(f)
 rims=set()
 for j,i in enumerate(ring):
  q=ring[(j+1)%len(ring)];fs.append((i,q,q+nn,i+nn));matid.append(2)
  rims.add(tuple(sorted((i,q))));rims.add(tuple(sorted((i+nn,q+nn))))
 ob=mesh(n,0,vv,fs,[sail,back,seam],matid)
 for p in ob.data.polygons:p.use_smooth=p.material_index!=2
 for e in ob.data.edges:e.use_edge_sharp=tuple(sorted(e.vertices)) in rims
 return ob
panel('WAU_BOWED_PAPER_SAIL',body)
panel('WAU_CRESCENT_PAPER_TAIL',tail)
def tube(n,k,pts,r,m,sides=7,closed=False):
 p=list(map(Vector,pts));vs=[];f=[]
 for i,l in enumerate(p):
  q=(p[(i+1)%len(p)] if closed or i<len(p)-1 else p[i])-(p[i-1] if closed or i else p[0]);q.normalize()
  a=q.cross(Vector((0,1,0)))
  if a.length<.001:a=q.cross(Vector((0,0,1)))
  a.normalize();b=q.cross(a).normalized()
  for j in range(sides):
   w=math.tau*j/sides;vs.append(l+r*(a*math.cos(w)+b*math.sin(w)))
 for i in range(len(p) if closed else len(p)-1):
  q=(i+1)%len(p)
  for j in range(sides):
   k1=(j+1)%sides;f.append((i*sides+j,i*sides+k1,q*sides+k1,q*sides+j))
 if not closed:f.extend((tuple(reversed(range(sides))),tuple(range(len(vs)-sides,len(vs)))))
 return mesh(n,k,vs,f,[m],smooth=True)
def decor_line(n,points,m,r=.007):
 return tube(n,1,[xyz(x,z,-.0037) for x,z in points],r,m,6)
def solid_decor(n,outline,m,w=-.006):
 vv=[xyz(x,z,w) for x,z in outline]
 f=triangulate(outline)
 # use paper offset that remains in front of interpolated faceted sail on all sections.
 fixed=[]
 for i,j,k in f:
  x,y=outline[i];p,q=outline[j];r,s=outline[k];fixed.append((i,j,k) if (p-x)*(s-y)-(q-y)*(r-x)>0 else (i,k,j))
 return mesh(n,1,vv,fixed,[m])
# Rim caulks at true paper boundary and repeats 20 mm inboard.
for name,arr,c0,ratio in [('wing',body,1.54,.954),('crescent',tail,1.092,.917)]:
 tube(name+' visible taper edge',0,[xyz(x,z,.001) for x,z in arr],.0061,seam,6,True)
 tube(name+' inset warm cut border',1,[xyz(x*ratio,c0+(z-c0)*ratio,-.009) for x,z in arr],.0066,rim,6,True)
def petal(cx,cz,dx,dz,width,m):
 leng=math.hypot(dx,dz);ax=-dz/leng;az=dx/leng
 return curve2((cx,cz),[
  ((cx+dx*.1+ax*width,cz+dz*.1+az*width),(cx+dx*.62+ax*width,cz+dz*.62+az*width),(cx+dx,cz+dz),7),
  ((cx+dx*.72-ax*width,cz+dz*.72-az*width),(cx+dx*.15-ax*width,cz+dz*.15-az*width),(cx,cz),7)])[:-1]
# Custom bilateral botanical imagery; no coat of arms, crest, archival art or religious symbols.
for side in (-1,1):
 for dx,dz,n,m in [(.083,.233,'cream',rim),(.186,.122,'green',mint),(.221,.002,'coral',pink),(.147,-.085,'ivory',cream)]:
  solid_decor('Central bloom '+n,petal(0,1.477,dx*side,dz,.032,m),m)
 wing=curve2((.10,1.465),[
  ((.198,1.495),(.289,1.554),(.371,1.583),11),((.480,1.62),(.615,1.575),(.741,1.672),15)])
 decor_line('Hand layered main vine',[(x*side,z) for x,z in wing],rim,.007)
 leafs=[(.227,1.52,.086,.087,.023),(.330,1.568,.108,-.037,.020),(.425,1.597,.100,.063,.019),(.53,1.598,.091,-.042,.016),(.62,1.615,.106,.047,.017)]
 for i,(x,z,dx,dz,w) in enumerate(leafs):
  m=(mint,cream,pink,mint,cream)[i];solid_decor('Wing frond cut paper',petal(side*x,z,side*dx,dz,w,m),m)
 low=curve2((.036,.958),[((.109,.954),(.228,.989),(.291,1.055),12),((.337,1.095),(.359,1.142),(.366,1.185),7)])
 decor_line('Independent crescent ornament sweep',[(x*side,z) for x,z in low],rim,.0068)
 for i,(x,z,dx,dz) in enumerate([(.090,.974,.058,.071),(.181,.998,.047,.071),(.253,1.033,.048,.084)]):
  m=(mint,pink,mint)[i];solid_decor('Crescent paper frond',petal(side*x,z,side*dx,dz,.0145,m),m)
# raised centre rosette ring and structured bamboo framework on the reverse.
for rad,col in ((.041,cream),(.020,pink)):
 solid_decor('Central original petal pin',[(math.sin(i*math.tau/16)*rad,1.477+math.cos(i*math.tau/16)*rad) for i in range(16)],col,-.010-rad/20)
S=[xyz(0,.892+(1.899-.892)*i/20,.014) for i in range(21)]
tube('WAU_LONGITUDINAL_BAMBOO_SPINE',2,S,.0115,bamboo,9)
def bowpath(name,h,off,r):
 half=curve2((0,h[0]),h[1]);p=[(-x,z) for x,z in reversed(half[1:])]+half
 pts=[xyz(x,z,off) for x,z in p];tube(name,2,pts,r,bamboo,8)
 return pts
main=bowpath('WAU_CONTINUOUS_BOWED_CROSS_SPAR',(1.501,[((.344,1.469),(.576,1.511),(.862,1.746),24)]),.016,.009)
cres=bowpath('WAU_CRESCENT_BOW_SPAR',(0.932,[((.168,.924),(.318,1.008),(.409,1.288),18)]),.014,.008)
# Long diagonals are short reinforcing reeds, visibly joined at the centre and swept tip.
for side in (-1,1):
 path=curve2((0,1.233),[((.26,1.340),(.496,1.547),(.665,1.598),20)])
 tube('Split bamboo wing brace',2,[xyz(x*side,z,.013) for x,z in path],.0059,bamboo,7)
for z in (.93,1.232,1.505,1.77):
 for j in range(3):
  zz=z+(j-1)*.006
  tube('Tied sinew lash around bamboo',2,[(.014*math.cos(i*math.tau/12),bow(0,zz)+.020+.017*math.sin(i*math.tau/12),zz) for i in range(12)],.0026,joint,6,True)
# A paired visible continuous cotton bridle. Knot sits in front; on reverse its lashing ties remain legible.
K=(.099,-.198,1.332)
for n,a in [('upper',xyz(.009,1.690,.017)),('lower',xyz(.007,1.184,.017))]:
 M=((a[0]+K[0])*.50,(a[1]+K[1])*.50-.012,(a[2]+K[2])*.50-.009)
 tube('WAU_BRIDLE_'+n.upper(),2,[a, (a[0]+.010,a[1]-.022,a[2]+.007),M,K],.0031,cord,7)
tube('Bridle open cotton tag',2,[K,(.114,-.202,1.31),(.121,-.176,1.291),(.134,-.162,1.296)],.0031,cord,7)
# Three-point tabletop-style bamboo display cradle, with visibly joined diagonal rear supports.
for side in (-1,1):
 x=side*.226
 tube('Bamboo resting foot',3,[(x,-.241,.034),(x,.392,.034)],.034,bamboo,12)
 tube('Upright display tripod rail',3,[(x,.104,.061),(x*.79,.017,1.036)],.023,bamboo,10)
 tube('Rear kickstand securely joins rail',3,[(x,.350,.063),(x*.82,.051,.776)],.019,bamboo,10)
 tube('Padded T-seat under crescent',3,[(x*.72,-.066,.891),(x*.79,.030,.897)],.024,joint,10)
 tube('Small wooden stopper at tip',3,[(x*.72,-.071,.882),(x*.72,-.071,.962)],.018,dark,9)
for z,y,w in ((.329,.086,.235),(.854,.03,.189)):
 tube('Horizontal pegged display stretcher',3,[(-w,y,z),(w,y,z)],.021,bamboo,10)
for z,y in ((.335,.086),(.853,.030)):
 for x in (-.194,.194):
  tube('Dark fastening peg',3,[(x,y-.024,z),(x,y+.021,z)],.008,joint,8)
# Small wound thread reel next to the stand.
for aa,bb,rad,col in ((.062,.157,.037,cord),(.051,.061,.050,joint),(.157,.169,.050,joint)):
 tube('Reel cotton or wooden flange',3,[(.339,aa,.052),(.339,bb,.052)],rad,col,14)
for y in (.073,.085,.097,.109,.121,.133,.145):
 tube('Cotton winding detail',3,[(.339+.039*math.cos(i*math.tau/14),y,.052+.039*math.sin(i*math.tau/14)) for i in range(14)],.0027,cord,5,True)
# Consolidate only stationery ornamental parts/edge/stand sub-components for draw-call and GLB budgets.
def join(k,name,sel):
 o=[x for x in C[k].objects if x.type=='MESH' and sel(x)]
 if len(o)<2:return
 bpy.ops.object.select_all(action='DESELECT')
 for x in o:x.select_set(True)
 bpy.context.view_layer.objects.active=o[0];bpy.ops.object.join();bpy.context.object.name=name
join(1,'WAU_ORIGINAL_LAYERED_APPLIQUE',lambda o:True)
join(3,'WORKSHOP_BAMBOO_STAND',lambda o:not any(x in o.name for x in ('Reel','winding')))
join(3,'WORKSHOP_COTTON_REEL',lambda o:any(x in o.name for x in ('Reel','winding')))
join(2,'WAU_BAMBOO_JOINERY_LASHING',lambda o:o.name.startswith('Tied'))
join(0,'WAU_PAPER_EDGE_PIPING',lambda o:o.name.endswith('edge'))
# Large floor is exact thumbnail-only; export selects asset collections exclusively.
mesh('Studio floor',4,[(-200,-200,-.002),(200,-200,-.002),(200,200,-.002),(-200,200,-.002)],[(0,1,2,3)],[ground])
def look(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,pos,power,size,color):
 d=bpy.data.lights.new(n,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color
 o=bpy.data.objects.new(n,d);C[4].objects.link(o);o.location=pos;look(o,(0,0,1.166))
lamp('Wide atelier daylight',(-2.4,-3.25,4.0),320,2.6,(1,.91,.76))
lamp('Quiet neutral fill',(2.24,-1.87,2.76),125,2.1,(.80,.93,1))
lamp('Back spars light',(1.68,2.79,3.44),275,2.65,(.91,1,1))
w=bpy.data.worlds.new('Neutral workshop lighting');SC.world=w;w.use_nodes=True
w.node_tree.nodes['Background'].inputs[0].default_value=(.61,.69,.72,1);w.node_tree.nodes['Background'].inputs[1].default_value=.36
c=bpy.data.cameras.new('Studio only');cam=bpy.data.objects.new('Studio only',c);C[4].objects.link(cam);SC.camera=cam
c.type='ORTHO';c.ortho_scale=2.24;cam.location=(1.14,-5.66,2.38);look(cam,(0,.01,.991))
SC.render.engine='CYCLES';SC.cycles.samples=36;SC.cycles.use_denoising=sys.platform=='darwin'
SC.render.threads_mode='FIXED';SC.render.threads=5
SC.render.resolution_x=512;SC.render.resolution_y=512;SC.render.resolution_percentage=100
SC.render.image_settings.file_format='WEBP';SC.render.image_settings.quality=92
SC.view_settings.view_transform='AgX';SC.view_settings.exposure=.075
SC.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/(ID+'.blend')),compress=True)
def render(p,pos,target,ortho,pixels):
 cam.location=pos;look(cam,target);c.ortho_scale=ortho
 SC.render.resolution_x,SC.render.resolution_y=pixels;SC.render.filepath=str(p);bpy.ops.render.render(write_still=True)
if not A.skip_render:render(O/'previews/studio.webp',(1.14,-5.66,2.38),(0,.01,.991),2.24,(512,512))
if A.review:
 render(A.review/'rear-spars.webp',(-1.89,4.4,2.47),(0,0,1.142),2.06,(720,720))
 render(A.review/'front-crescent.webp',(.524,-4.02,1.69),(0,-.025,1.399),1.86,(780,560))
bpy.ops.object.select_all(action='DESELECT')
for k in range(4):
 for ob in C[k].objects:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'exports'/f'{ID}.glb'),export_format='GLB',use_selection=True,export_texcoords=False,export_animations=False)
