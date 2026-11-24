"""Original shophouse awning with one native, physically articulated demonstration."""
import argparse, math, sys
from pathlib import Path
import bpy
from mathutils import Vector,Quaternion
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
ID='shophouse-retractable-fabric-awning'
CLIP='AWNING_FOLD_IN'
out=a.output.resolve()
for x in ('exports','previews'):(out/x).mkdir(parents=True,exist_ok=True)
if a.review:a.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC';S.render.fps=30;S.frame_start=0;S.frame_end=72
C={}
for i,n in enumerate(['Small wall mounting context','Stationary cassette and hardware','Bilateral rigid link motion','Fixed-width textile and moving bar','Studio excluded']):
 c=bpy.data.collections.new(n);S.collection.children.link(c);C[i]=c
def mat(n,h,r=.6,m=0):
 def f(x):v=int(x,16)/255;return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
 o=bpy.data.materials.new(n);o.use_nodes=True;o.diffuse_color=(*[f(h[i:i+2]) for i in (0,2,4)],1)
 b=o.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=o.diffuse_color
 b.inputs['Roughness'].default_value=r;b.inputs['Metallic'].default_value=m
 return o
cream=mat('Old warm lime wash','C4AD8C',.74)
pl=mat('Sandstone footing','9E956E',.71)
shade=mat('Shadowed window opening','515F53',.61)
moss=mat('Sage ceramic skirting','5F7767',.54)
paint=mat('Grey bronze cassette enclosure','6C7565',.51,.23)
cast=mat('Warm pale powder-coated links','B9A98B',.51,.26)
dark=mat('Blank black green brackets','394B43',.57,.28)
steel=mat('Tarnished zinc hinge detail','9D9A7D',.44,.5)
clothA=mat('Matte dark sea-green textile','317269',.78)
clothB=mat('Undyed straw textile','E8C28D',.79)
clothC=mat('Thin rust accent stripe','AC6843',.81)
rollmat=mat('Slate green rolled textile edges','566E60',.79)
concrete=mat('Low-key studio concrete','74887E',.72)
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
def poly(n,k,v,f,mats,indices,flat=True):
 o=mesh(n,k,v,f,mats[0],not flat)
 for m in mats[1:]:o.data.materials.append(m)
 for i,p in enumerate(o.data.polygons):p.material_index=indices[i]
 return o
def join(k,n,obs):
 if len(obs)==1:obs[0].name=n;return obs[0]
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.select_set(True)
 bpy.context.view_layer.objects.active=obs[0]
 bpy.ops.object.join();o=bpy.context.object;o.name=n
 return o
# Tightly cropped, fictional mounting bay: a low wall elevation fragment, not a complete shop.
box('Feet of shophouse display fragment',0,(0,.064,.046),(2.25,.810,.092),pl,.025,2)
box('Left plaster ledge pier',0,(-.961,.088,.648),(.293,.326,1.138),cream,.014,2)
box('Right plaster ledge pier',0,(.961,.088,.648),(.293,.326,1.138),cream,.014,2)
box('Lintel supporting the two cartridge brackets',0,(0,.091,1.213),(2.215,.319,.277),cream,.016,2)
box('Recessed grille backing, not a doorway',0,(0,.193,.633),(1.657,.133,1.029),shade,.013)
box('Plain sill below the recessed bay',0,(0,-.003,.209),(1.647,.292,.086),pl,.015)
for x in (-.908,.908):
 for y in (.19,.31):
  box('Short sage skirt segment',0,(x,-.084,y),(.165,.038,.092),moss,.004)
for i in range(12):box('Vertical simplified closed timber shutter rib',0,(-.746+i*.135,.109,.579),(.082,.026,.604),moss,.004)
# Physical centre axis and exact inclined linkage plane. D is real in-plane projection.
theta=math.radians(8.5);co,si=math.cos(theta),math.sin(theta)
H=1.115;Y=-.254
L=.437;D0=.777;D1=.102;W=1.825;armX=.821
def P(x,d=0,h=0):return Vector((x,Y-d*co-h*si,H-d*si+h*co))
def cyl(n,k,a0,a1,r,m,s=12):return tube(n,k,[a0,a1],r,m,s)
def xcyl(n,k,x0,x1,y,z,r,m,s=12):
 return cyl(n,k,(x0,y,z),(x1,y,z),r,m,s)
# Cast cradle, exposed roller, static crowned roof cap and shoulders with bolted ends.
box('Visible cassette back rail',1,(0,-.086,1.125),(1.994,.092,.128),paint,.014,2)
box('Protective cap over roller, front exposed',1,(0,-.124,1.209),(1.976,.224,.040),paint,.010,2)
for side in (-1,1):
 x=side*.932
 box('Stationary flanged wall mounting plate',1,(x,-.084,1.124),(.121,.032,.174),dark,.011)
 for z in (1.072,1.179):
  cyl('Visible recessed hex bolt',1,(x,-.107,z),(x,-.129,z),.016,steel,6)
 box('Supporting cartridge cheek and bearing',1,(x,-.202,1.131),(.053,.242,.171),paint,.013,2)
 xcyl('Fixed axle side bushing',1,x-.020,x+.020,*P(0,0,0)[1:],.057,steel,18)
 joint=P(side*armX,0,-.004)
 box('Broad side shoulder mounting pad',1,(joint.x+.016*side,joint.y+.027,joint.z-.031),(.112,.137,.064),dark,.008)
 cyl('Stationary shoulder hinge pin',1,joint+Vector((0,0,-.025)),joint+Vector((0,0,.027)),.021,steel,12)
# Cylinder's central axis is world X. Local spindle assembly is animated without changing station.
roller=xcyl('Turning textile roller',3,-.920,.920,0,0,.047,rollmat,30)
rparts=[roller,xcyl('Left solid end flange',3,-.925,-.887,0,0,.053,dark,20),xcyl('Right solid end flange',3,.887,.925,0,0,.053,dark,20),
        xcyl('Narrow raised roll seam not a measuring index',3,-.882,.882,-.046,.004,.0042,clothC,8)]
roller=join(3,'AWNING_ROLLER',rparts);roller.location=P(0,0,0);roller.rotation_mode='QUATERNION'
# One striped, lightly bowed fixed-width closed textile laminate; Y compresses as more goes onto roller.
breaks=[0,.112,.152,.280,.319,.450,.489,.510,.549,.679,.718,.848,.889,1.]
zones=[0,2,1,2,0,2,1,2,0,2,1,2,0]
part=15;ncol=len(breaks)
verts=[(-W/2+W*f,-D0*t,.0035-.005*math.sin(math.pi*t)+side*.0025)
       for side in (0,1) for f in breaks for i in range(part+1) for t in (i/part,)]
r=part+1;nn=ncol*r;faces=[];mi=[]
for j in range(ncol-1):
 for i in range(part):
  a0=j*r+i;b=(j+1)*r+i;ids=(a0,a0+1,b+1,b)
  faces.extend([tuple(reversed(ids)),tuple(k+nn for k in ids)]);mi.extend([zones[j]]*2)
ring=[i*r for i in range(ncol)]+list(range((ncol-1)*r+1,ncol*r))+[i*r+part for i in range(ncol-2,-1,-1)]+list(range(part-1,0,-1))
for i,j in zip(ring,ring[1:]+ring[:1]):
 faces.append((j,i,i+nn,j+nn));mi.append(2)
cloth=poly('AWNING_FABRIC',3,verts,faces,[clothA,clothB,clothC],mi)
cloth.location=P(0,0,.0445);cloth.rotation_euler=(theta,0,0)
# Front header and stitched scalloped strip move as one. Keep clear pocket at fully parked D1.
parts=[box('Folded metal front extruded carrier',3,(0,0,0),(W+.067,.062,.047),paint,.010,2),
       box('Metal front visible face inset',3,(0,-.035,-.001),(W+.033,.015,.023),dark,.005)]
for x in (-.893,.893):
 parts.append(box('Front end cap',3,(x,0,0),(.052,.067,.055),cast,.006))
for j,c in enumerate(zones):
 U=-W/2+W*breaks[j];V=-W/2+W*breaks[j+1]
 v=[(U,-.036,-.02),(V,-.036,-.02)]+[(V+(U-V)*i/9,-.039,-.062-.025*abs(math.sin(7*math.pi*((V+(U-V)*i/9+W/2)/W)))) for i in range(10)]
 # Thin sewn valance: the 3 mm return stays with the bar.
 v+=[(x,y-.003,z) for x,y,z in v]
 n=len(v)//2
 f=[tuple(range(n)),tuple(reversed(range(n,n*2)))]+[((i+1)%n,i,n+i,n+(i+1)%n) for i in range(n)]
 parts.append(mesh('Stitched apron interval',3,v,f,[clothA,clothB,clothC][c]))
bar=join(3,'AWNING_FRONT_BAR',parts)
# Four rigid equal-length links, with distinct shoulder, elbow and carrier pivots.
def link(n,skin):
 p0=box(n,2,(0,0,0),(.038,1,.028),skin,.007,2)
 # Build against one live local datum: the second pin remains exactly L from origin.
 for v in p0.data.vertices:
  v.co.y*=L-.019;v.co.y+=L/2
 # The pin geometry is combined on the actual hinge axis, not simulated by stretching the bar.
 p1=cyl('Rigid inner bearing ring',2,(0,0,-.015),(0,0,.019),.022,steel,12)
 p2=cyl('Rigid outer bearing ring',2,(0,L,-.016),(0,L,.019),.020,steel,12)
 o=join(2,n,[p0,p1,p2]);o.rotation_mode='QUATERNION'
 return o
arms=[(link('AWNING_'+s+'_PROXIMAL',cast),link('AWNING_'+s+'_DISTAL',paint)) for s in ('L','R')]
def seat(o,a,b):
 o.location=a;o.rotation_quaternion=(b-a).to_track_quat('Y','Z')
def positions(D):
 # Both linkage endpoint solutions are isosceles on the same inclined plane. No arm is resized.
 off=math.sqrt(L*L-(D/2)**2)
 return [(P(side*armX,0,-.004),P(side*(armX-off),D/2,-.004),P(side*armX,D,-.004))
         for side in (-1,1)]
FRAMES=72
def step(f):
 t=max(0,min(1,(f-4)/64));q=t*t*(3-2*t)
 return D0+(D1-D0)*q
def frame(f):
 D=step(f)
 bar.location=P(0,D,.020)
 cloth.scale=(1,D/D0,1)
 roller.rotation_quaternion=Quaternion((1,0,0),(D0-D)/.047)
 for (o1,o2),(u,v,w) in zip(arms,positions(D)):seat(o1,u,v);seat(o2,v,w)
 return D
animated=[(bar,('location',)),(cloth,('scale',)),(roller,('rotation_quaternion',))]
animated.extend((i,('location','rotation_quaternion')) for g in arms for i in g)
prev={}
for f in range(FRAMES+1):
 frame(f)
 for o,props in animated:
  if 'rotation_quaternion' in props:
   q=o.rotation_quaternion
   if o in prev and q.dot(prev[o])<0:o.rotation_quaternion=-q
   prev[o]=o.rotation_quaternion.copy()
  for prop in props:o.keyframe_insert(data_path=prop,frame=f,group='One retract cycle')
for o,props in animated:
 act=o.animation_data.action;act.name=o.name+' authored retract cycle'
 # Each object has one track with the exact same name; the exporter merges to one clip.
 t=o.animation_data.nla_tracks.new();t.name=CLIP
 t.strips.new('Fabric and linked arms retract together',0,act);o.animation_data.action=None
S.frame_set(0)
# Stills are directly rendered poses of the exact scene and never enter the GLB.
box('Studio matte floor',4,(0,0,-.027),(200,200,.046),concrete,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,c,power,size,color):
 l=bpy.data.lights.new(n,'AREA');l.energy=power;l.size=size;l.shape='DISK';l.color=color
 o=bpy.data.objects.new(n,l);C[4].objects.link(o);o.location=c;look(o,(0,-.22,.91))
lamp('Warm courtyard skylight',(-2.26,-3.38,3.2),404,2.9,(1,.91,.78))
lamp('Wide overcast underawning fill',(1.9,-2.5,1.91),140,2.64,(.82,.97,1))
lamp('Daylight high separation',(.07,1.52,3.46),228,2.0,(.82,.97,1))
w=bpy.data.worlds.new('Open street daylight');w.use_nodes=True;S.world=w
w.node_tree.nodes['Background'].inputs[0].default_value=(.52,.66,.61,1);w.node_tree.nodes['Background'].inputs[1].default_value=.46
m=bpy.data.cameras.new('Studio camera');cam=bpy.data.objects.new('Studio camera',m);C[4].objects.link(cam);S.camera=cam;m.type='ORTHO';m.ortho_scale=2.65
cam.location=(2.35,-4.72,2.79);look(cam,(0,-.298,.756))
S.render.engine='CYCLES';S.cycles.samples=40;S.cycles.use_denoising=sys.platform=='darwin'
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_x=S.render.resolution_y=512;S.render.resolution_percentage=100
S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=92
S.view_settings.view_transform='AgX';S.view_settings.exposure=.10
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(ID+'.blend')),compress=True)
def render(to,f,pos,t,ortho,n):
 S.frame_set(f);cam.location=pos;look(cam,t);m.ortho_scale=ortho
 S.render.resolution_x,S.render.resolution_y=n;S.render.filepath=str(to);bpy.ops.render.render(write_still=True)
if not a.skip_render:render(out/'previews/studio.webp',0,(2.35,-4.72,2.79),(0,-.298,.756),2.65,(512,512))
if a.review:
 for f,n in ((0,'extended-links'),(36,'midway-links'),(72,'parked-links')):
  render(a.review/(n+'.webp'),f,(1.412,-4.83,1.72),(0,-.37,1.015),2.16,(760,500))
S.frame_set(0)
bpy.ops.object.select_all(action='DESELECT')
for k in range(4):
 for ob in C[k].objects:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/f'{ID}.glb'),export_format='GLB',use_selection=True,export_texcoords=False,
 export_animations=True,export_animation_mode='NLA_TRACKS',export_force_sampling=True,export_cameras=False,export_lights=False,export_extras=False)
