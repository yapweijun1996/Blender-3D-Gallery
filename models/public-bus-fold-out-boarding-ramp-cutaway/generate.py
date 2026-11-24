"""Original static section through a fictional low-floor bus doorway and boarding bridge."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='public-bus-fold-out-boarding-ramp-cutaway'
out=a.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if a.review:a.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
base=collection('01 curb approach and short roadway sample')
bus=collection('02 original cutaway body and open door context')
ramp=collection('03 visible hinge pin lugs ramp and support surfaces')
studio=collection('04 studio only; not exported')
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


asphalt=material('Neutral textured-looking cool roadway sample','515757',.82)
stone=material('Dry light limestone curb','A1A396',.78)
stonecut=material('Pale concrete sectional edges','BFC0A9',.80)
paving=material('Muted broad pavement field','A5A691',.82)
paving_alt=material('Original slightly contrasted paving seams','888A7D',.82)
cream=material('Warm upper bus body, original generic paint','EEE9D6',.41,.15)
petrol=material('Original dusty teal lower bus body','4D7776',.46,.40)
petrolHi=material('Cool body cut edges','7E9F94',.45,.30)
matte=material('Neutral charcoal structure','34464A',.58,.38)
seat=material('Mottled-looking dark interior floor','5A6862',.75)
panel=material('Mid grey ramp deck and matching toe','64777B',.59,.40)
peel=material('Bright satin brushed sill and underside support','B6C0B4',.34,.62)
old=material('Satin darker powder coat under ramp','495C61',.56,.45)
gold=material('Muted warm yellow edging, not a sign','C39346',.53,.36)
lightgold=material('Upper latches witness in amber','D1A95B',.48,.29)
rub=material('Dark flexible-looking threshold joint','394446',.75,.13)
glass=material('Subtle pale blue-green glazed detail','7FA7A5',.21,.12)
glass.diffuse_color=(*glass.diffuse_color[:3],.28)
glass.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value=.28
glass.surface_render_method='DITHERED'
backdrop=material('Neutral ecru editorial shadow surface','C6C8B7',.82)
R=empty('PUBLIC_BUS_BOARDING_SECTION',base)
K=empty('CURB_AND_APPROACH_DATUM',base,R)
V=empty('ORIGINAL_GENERIC_BUS_DOORWAY_CUTAWAY',bus,R)
D=empty('DEPLOYED_BOARDING_BRIDGE_AND_SILL',ramp,R)

def profile_x(name,group,p,section,x0,x1,mats,side_indices=None):
    # For each closed section, state its profile in (Y,Z), stored in order from
    # forward low edge around the solid. Signed orientation is derived, not guessed.
    area=sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(section,section[1:]+section[:1]))
    N=len(section)
    vv=[(x,y,z) for x in (x0,x1) for y,z in section]
    ff=[tuple(reversed(range(N))),tuple(range(N,2*N))]
    ff.extend((i,(i+1)%N,N+(i+1)%N,N+i) for i in range(N))
    if area<0:ff=[tuple(reversed(f)) for f in ff]
    o=mesh(name,group,p,vv,ff,mats[0])
    for mat in mats[1:]:o.data.materials.append(mat)
    if side_indices:
        for face,i in zip(o.data.polygons,[0,0]+side_indices):face.material_index=i
    return o
def slope(y):return .445+.24*(y-.180)
def beam_over(name,group,p,x0,x1,profile,t,mats,side=None):
    return profile_x(name,group,p,profile+[(y,z-t) for y,z in reversed(profile)],x0,x1,mats,side)
def tube(n,group,p,x0,x1,y,z,ri,ro,mat):
    N=32;V0=[];F=[]
    for x,r in ((x0,ri),(x0,ro),(x1,ro),(x1,ri)):
        V0 += [(x,y+r*math.cos(theta*math.tau/N),z+r*math.sin(theta*math.tau/N)) for theta in range(N)]
    for k in range(4):
        for i in range(N):
            q=(i+1)%N;h=(k+1)%4
            F.append((k*N+i,k*N+q,h*N+q,h*N+i))
    o=mesh(n,group,p,V0,F,mat)
    for a in o.data.polygons:a.use_smooth=a.index//N in (1,3)
    return o
# Road and a deliberately cropped sidewalk portion.
box('Flat asphalt street-section base',base,K,(0,-.379,.027),(2.084,1.99,.053),asphalt,.011,2)
# The pavement wraps around the toe seat. A shallow centre notch accepted
# exactly at the end of the thin ramp toe, not a built installation.
zpad=.1906
for x0,x1 in [(-1.044,-.447),(.447,1.044)]:
    profile_x('Side chamfered curb face and walking edge',base,K,
      [(-1.362,.031),(-.880,.031),(-.878,.165),(-.894,zpad),(-1.362,zpad)],x0,x1,[stone,stonecut],[0,0,1,0,0])
center=[(-1.362,.031),(-.880,.031),(-.880,.178),(-.942,.178),(-.942,zpad),(-1.362,zpad)]
profile_x('Center curb segment with actual recessed tongue seat',base,K,center,-.447,.447,[stone,stonecut],[0,0,0,1,0,0])
# Side paving breaks and real chamfered small curbstone lines stay out of the continuous center.
for x in (-.798,.805):
    for y in (-1.300,-1.170,-1.033):
        box('Side inset stone surface patch',base,K,(x,y,.1903),(.352,.113,.003),paving,.004,2)
for X in (-.864,.864):
    box('Low-contrast street joint line section sample',base,K,(X,-.607,.054),(.052,.205,.002),paving_alt,.001,2)
# Shallow receiving floor and visibly open framing, detached from the cropped wheel area.
box('Cabin structural floor tub',bus,V,(0,.391,.384),(1.66,.463,.108),matte,.009,2)
beam_over('Solid continuous interior floor up to sill',bus,V,-.695,.695,[(.190,.445),(.604,.445)],.018,[seat])
box('Short rear inside sectional floor strip',bus,V,(0,.592,.421),(1.59,.035,.041),peel,.005,2)
for x in (-.629,.625):
    box('Independent lower chassis support lug',bus,V,(x,.395,.285),(.171,.261,.158),matte,.015,3)
    box('Sections bearing on dark exhibit foot',bus,V,(x,.410,.130),(.148,.146,.155),rub,.009,2)
    box('Window belt sill inside each flank',bus,V,(x,.256,1.096),(.255,.080,.057),matte,.007,2)
for x0,x1 in [(-.930,-.510),(.510,.930)]:
    profile_x('Rounded bus exterior low skirt section',bus,V,
     [(.15,.329),(.181,.232),(.268,.205),(.293,.211),(.302,.742),(.236,.754),(.198,.715),(.175,.480)],x0,x1,[petrol,petrolHi],[0,0,1,1,1,0,0,0])
    profile_x('Upper cream outer skin framed short module',bus,V,
     [(.174,.732),(.173,1.745),(.215,1.824),(.249,1.840),(.305,1.822),(.321,1.776),(.317,.745)],x0,x1,[cream,petrolHi],[0,0,0,1,1,1,1])
    box('Exterior swaged line below upper body',bus,V,((x0+x1)/2,.159,.733),(x1-x0+.012,.031,.038),petrolHi,.005,2)
    # Open leaves stand parked along the side of the aperture, never blocking it.
    x=(x0+x1)/2
    for xx in (x-.087,x+.085):
        box('Visible open parked door vertical section',bus,V,(xx,.112,1.328),(.033,.047,.804),matte,.005,2)
    for z in (.935,1.718):
        box('Parked door peripheral horizontal rail',bus,V,(x,.112,z),(.202,.045,.034),peel,.006,2)
    box('Recessed transparent door panel, parked away from entry',bus,V,(x,.114,1.359),(.140,.016,.710),glass,.005,2)
    box('Parked leaf rubber footing section',bus,V,(x,.117,.856),(.204,.038,.128),petrol,.007,2)
for x in (-.497,.497):
    box('Carried doorway cut section pillar',bus,V,(x,.213,1.113),(.070,.157,1.337),matte,.010,3)
    box('Bright stainless interior entrance frame insert',bus,V,(x,.157,1.110),(.029,.036,1.255),peel,.006,2)
    rod('Original short visible split interior handhold',bus,V,(x,.364,.650),(x,.364,1.565),.0155,lightgold,16)
    for z in (.703,1.535):
        rod('Short rail bracket into interior side sill',bus,V,(x,.338,z),(x,.390,z),.0095,peel,12)
box('Upper retained lintel across open safe exhibit space',bus,V,(0,.220,1.783),(1.802,.167,.125),petrol,.013,3)
box('Clean cream oblong original bus header',bus,V,(0,.132,1.797),(1.713,.032,.079),cream,.009,3)
etch('Neutral section title no copy of livery',bus,V,(0,.115,1.773),'BUS DOORWAY',.055,matte)
for x in (-.620,.620):
    box('Small inset warm abstract marker shape',bus,V,(x,.108,1.781),(.087,.017,.021),lightgold,.005,2)
# Floor-to-ramp bridge: actual solid profiles share endpoints, not just drawn lines.
# Front is negative Y. The ramp then continues to the curb at the same exact top.
beam_over('Flush elastomer-colored heel transition',ramp,D,-.426,.426,
  [(.150,slope(.150)),(.180,.445),(.190,.445)],.010,[rub])
beam_over('One continuous sloped boarding deck with rolled-off toe end',ramp,D,-.427,.427,
  [(-.880,zpad),(-.862,slope(-.862)),(.150,slope(.150))],.017,[panel])
# Actual feather section is a load-free visual joining the inclined leaf to pavement.
profile_x('Physical toe join, flush cap over center curb rebate',ramp,D,
 [(-.942,.178),(-.880,.178),(-.876,.182),(-.880,zpad),(-.942,zpad)],-.4265,.4265,[panel,peel],[0,1,1,0,0])
# Thin longitudinal edge lips are intentionally different in appearance from tread.
for x0,x1,mat in [(-.450,-.426,gold),(.426,.450,lightgold)]:
    top=[(-.888,zpad+.006),(-.854,slope(-.854)+.024),(.103,slope(.103)+.024),(.125,slope(.125)+.014)]
    beam_over('Continuous raised side guide edge beside the clear path',ramp,D,x0,x1,top,.024,[mat])
    beam_over('Actual lower side structural rail under slope',ramp,D,x0-.003,x1+.003,
     [(-.846,slope(-.846)-.006),(.120,slope(.120)-.006)],.032,[old])
for yy in (-.779,-.655,-.53,-.406,-.282,-.158,-.034,.090):
    z=slope(yy)
    # Below 2 mm of intentionally subtle top texture in the modeled exhibit.
    beam_over('Shallow transverse visual grip stripe on main deck',ramp,D,-.351,.351,
      [(yy-.008,slope(yy-.008)+.0015),(yy+.008,slope(yy+.008)+.0015)],.002,[old])
for x in (-.350,.350):
    for y in (.024,-.296,-.680):
        zz=slope(y)
        rod('Visible ground-flat fastener head captured in the bridge',ramp,D,(x,y,zz-.002),(x,y,zz+.002),.008,peel,12)
# Three alternating fixing lugs and four leaf knuckles, exact coaxial actual pin.
yH,zH=.166,.414
kn=[]
for i,x in enumerate((-.360,-.240,-.120,0,.120,.240,.360)):
    moving=i%2==0
    kind='Leaf' if moving else 'Sill'
    # Hollow annulus kept independent so real pin/bore/end faces can be inspected.
    kn.append(tube(kind+' physical hinge barrel with bore',ramp,D,x-.052,x+.052,yH,zH,.0114,.022,old if moving else peel))
    oy=.137 if moving else .195
    box(kind+' support tang to deck/sill',ramp,D,(x,oy,.414),(.102,.034,.017),old if moving else peel,.0014,2)
rod('HINGE_STEEL_PIN_UNBROKEN_ACROSS_ALL_BARRELS',ramp,D,(-.435,yH,zH),(.435,yH,zH),.0105,peel,24)
for x in (-.435,.435):
    rod('Captured end machined retaining washer',ramp,D,(x-.006,yH,zH),(x+.006,yH,zH),.0144,peel,18)
    rod('Low-profile circular end marker not a button',ramp,D,(x-.004,yH,zH),(x+.004,yH,zH),.0148,lightgold,18)
# Rear sill attached to cabin structure, top is intentionally independent.
box('Upper sill subtub attaches to bus floor',ramp,D,(0,.218,.410),(.912,.067,.041),old,.006,2)
box('Thin fixed end cap inside parked door leaves',ramp,D,(0,.193,.440),(.870,.021,.010),peel,.002,2)
# Make cut view readable in the sectional area without ramps around a complete vehicle.
for x0,x1 in [(-.944,-.917),(.917,.944)]:
    profile_x('Deliberate sectioned edge of left or right vehicle shell',bus,V,
     [(.17,.344),(.169,1.751),(.240,1.841),(.327,1.800),(.329,.665),(.302,.234),(.266,.193),(.197,.226)],x0,x1,
     [petrolHi,cream],[0,1,1,0,1,0,0,1])
box('Studio surface only',studio,None,(0,0,-.026),(200,200,.051),backdrop,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,pos,w,s,col,aim=(0,-.06,.65)):
    d=bpy.data.lights.new(n,'AREA');d.energy=w;d.size=s;d.shape='DISK';d.color=col
    o=bpy.data.objects.new(n,d);studio.objects.link(o);o.location=pos;look(o,aim)
lamp('Warm broad neutral key',(-3.1,-2.95,3.55),420,3.55,(1,.91,.79))
lamp('Cool contrasting sill fill',(3.2,-2.40,2.65),335,2.65,(.80,.92,1))
lamp('Back wall trim sheen',(1.2,1.6,3.14),250,2.60,(1,.93,.82))
world=bpy.data.worlds.new('Soft pale gallery world');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.53,.57,.56,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.47
cd=bpy.data.cameras.new('Editorial camera');cam=bpy.data.objects.new('Editorial camera',cd);studio.objects.link(cam);S.camera=cam
hero=(2.32,-4.16,3.33);target=(.015,-.340,.811)
cd.type='ORTHO';cd.ortho_scale=3.02;cam.location=hero;look(cam,target)
S.render.engine='CYCLES';S.cycles.samples=200;S.cycles.use_denoising=False
S.cycles.adaptive_threshold=.013;S.cycles.adaptive_min_samples=58
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_percentage=100;S.render.resolution_x=S.render.resolution_y=512
S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=92
S.view_settings.view_transform='AgX';S.view_settings.exposure=.10
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True)
for c in (base,bus,ramp):
    for o in c.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/(slug+'.glb')),export_format='GLB',use_selection=True,
                         export_texcoords=False,export_animations=False,export_cameras=False,export_lights=False,export_extras=False)
def still(to,pos,tgt,scale,wh):
    cam.location=pos;look(cam,tgt);cd.ortho_scale=scale
    S.render.resolution_x,S.render.resolution_y=wh;S.render.filepath=str(to)
    bpy.ops.render.render(write_still=True)
if not a.skip_render:still(out/'previews/studio.webp',hero,target,3.02,(512,512))
if a.review:
    S.cycles.samples=75
    still(a.review/'curb-toe-and-deck.webp',(1.14,-1.97,1.18),(.02,-.874,.234),.91,(640,580))
    still(a.review/'doorway-hinge-and-sill.webp',(1.18,-.85,1.16),(.05,.134,.421),.84,(640,580))
    still(a.review/'side-deck-continuity.webp',(2.55,-.60,1.20),(.0,-.485,.331),1.52,(660,590))
