"""Original Sabah sompoton inspired exhibit; no acoustics or manufacturing guidance."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
opts=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='sabah-sompoton-display'
out=opts.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if opts.review:opts.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
base=collection('01 original low museum support and identification plaque')
gourd=collection('02 hollow dried gourd and visible dark setting collar')
bamboo=collection('03 two groups of four bamboo components and binding')
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
    x=x/255
    return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4
def vertmat(name,rough):
    m=material(name,'FFFFFF',rough)
    node=m.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name='Display grain'
    m.node_tree.links.new(node.outputs['Color'],m.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    return m
skin=vertmat('Sun-cured gourd mottled surface',.57)
inside=material('Matte dark inner dried gourd shell','68462D',.8)
rim=material('Naturally scuffed warm gourd rim','A27243',.65)
bamb=vertmat('Natural longitudinal bamboo colour',.62)
bamb_cut=material('Pale cut-end bamboo fibres','CCAC76',.63)
bamb_dark=material('Matte inner bamboo cavity','8E6C41',.77)
blockmat=material('Soft wood-coloured closed ends','A88254',.71)
bindA=material('Main tan woven-fibre raft binding','94704D',.74)
bindB=material('Alternating accented fibre strand','B18F60',.75)
wax=material('Dark aged sealing bead framing raft throat','4D3926',.67)
wood=vertmat('Deep warm oiled exhibit plinth',.57)
pad=material('Charcoal felt plinth cradle contacts','3A3E3B',.85)
steel=material('Neutral blackened bronze display hardware','4A5351',.61,.39)
cream=material('Muted tan modern exhibit lettering','DEC898',.60)
panel=material('Restrained dark-teal label panel','3C5E58',.63,.19)
accent=material('Satin narrow bronze label frame','8A7049',.49,.39)
stage=material('Soft pale neutral exhibition studio','CACAAE',.80)
R=empty('SABAH_SOMPOTON_EXHIBIT_ROOT',base)
G=empty('KOROBU_HOLLOW_DRIED_GOURD',gourd,R)
Q=empty('EIGHT_TUBES_IN_TWO_RAFTS',bamboo,R)
F=empty('STAND_AND_PLAQUE',base,R)

def colors(o,fn):
    c=o.data.color_attributes.new(name='Display grain',type='FLOAT_COLOR',domain='POINT')
    for v,col in zip(o.data.vertices,c.data):
        t=fn(v.co)
        col.color=tuple(linear(max(0,min(255,x))) for x in t)+(1,)
def mesh_m(n,col,parent,v,f,mats,ids):
    o=mesh(n,col,parent,v,f,mats[0])
    for m in mats[1:]:o.data.materials.append(m)
    for p,i in zip(o.data.polygons,ids):
        p.material_index=i
        p.use_smooth=len(p.vertices)==4
    return o
def addrings(vertices,faces,ids,rings,ns,fn):
    for j,ring in enumerate(rings):
        if j:
            for k in range(ns):
                a=(j-1)*ns+k;b=(j-1)*ns+(k+1)%ns
                faces.append((a,b,b+ns,a+ns));ids.append(fn(j-1,k))
        vertices.extend(ring)
    return vertices,faces,ids
def solid_bound(n,xspan,yspan,z,dy):
    a=box(n,base,F,(xspan,yspan,z),dy,wood,.010,3)
    bpy.context.view_layer.update()
    for other in bpy.context.selected_objects:other.select_set(False)
    a.select_set(True);bpy.context.view_layer.objects.active=a
    for mod in list(a.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    colors(a,lambda q:(61+9*math.sin(52*q.z+36*q.y)+5*math.cos(140*q.y+9*q.x),48+5*math.sin(50*q.y+30*q.z),37+5*math.cos(95*q.y+q.x)))
    return a
# Low wooden presentation base; the instrument is above it, not part of its geometry.
solid_bound('Long thin oiled timber pedestal',-.028,0,.024,(.512,.301,.046))
solid_bound('Lighter stepped upper plinth band',-.028,0,.053,(.484,.278,.019))
for x in (-.236,.180):
    for y in (-.108,.108):
        box('Protective foot under original display stand',base,F,(x,y,.004),(.049,.052,.009),pad,.004,2)
box('Modern small dark-teal information panel',base,F,(-.034,-.143,.042),(.230,.019,.039),panel,.006,3)
box('Small metallic title accent strip',base,F,(-.034,-.153,.0275),(.211,.004,.004),accent,.001,2)
etch('Original exhibit text no maker attribution',base,F,(-.034,-.153,.041),'SOMPOTON  /  SABAH',.0176,cream)
for x in (-.139,.071):
    rod('Plaque round drafted attachment',base,F,(x,-.155,.040),(x,-.157,.040),.0030,accent,12)
# Skin topology: bulb-shaped oval organic chamber, with integral bent mouth neck.
# Both surface skins modeled. The flared mouth stays genuinely open.
# x, cross-section radii y/z, center lateral y, height z.
outer=[
 (-.238,.012,.010,-.021,.241),(-.232,.014,.011,-.020,.239),(-.219,.015,.013,-.018,.232),
 (-.201,.017,.016,-.014,.218),(-.180,.021,.021,-.009,.203),(-.158,.026,.027,-.006,.188),
 (-.133,.036,.039,-.003,.175),(-.111,.049,.054,-.001,.168),(-.088,.068,.068,0,.163),
 (-.063,.085,.082,0,.159),(-.032,.097,.090,0,.156),(.002,.103,.097,0,.157),
 (.034,.101,.096,0,.159),(.066,.092,.090,0,.163),(.096,.080,.078,0,.169),(.117,.063,.065,0,.173),
 (.139,.042,.045,0,.174),(.154,.026,.030,0,.171),(.162,.010,.015,0,.170),(.166,.004,.005,0,.169),
]
inner=[(x,ry-(.003 if x<-.15 else .0048),rz-(.003 if x<-.15 else .0048),cy,cz) for x,ry,rz,cy,cz in outer[:-2]]
inner+=[(.158,.011,.014,0,.170),(.161,.0045,.0055,0,.1698)]
Ns=72
def gpoint(a,k,inner=False):
    x,ry,rz,y,z=a
    t=k*math.tau/Ns
    w=1+.020*math.cos(t*5+x*9)+.010*math.sin(t*3-x*17)
    return (x,y+math.cos(t)*ry*w,z+math.sin(t)*rz*w)
def surface(n,rows):
    return [[gpoint(a,k) for k in range(Ns)] for a in rows]
vv,ff,mi=addrings([],[],[],surface('outside',outer),Ns,lambda j,k:0)
N=len(vv);shape=surface('inside',inner)
iv,iff,imi=addrings([],[],[],shape,Ns,lambda j,k:1)
vv+=iv
ff+= [tuple(N+u for u in reversed(q)) for q in iff];mi+=imi
for k in range(Ns):
    q=(k+1)%Ns
    ff.append((k,N+k,N+q,q));mi.append(2)
ff.extend([tuple(range((len(outer)-1)*Ns,len(outer)*Ns)),tuple(reversed(range(N+(len(inner)-1)*Ns,N+len(inner)*Ns)))]);mi.extend([0,1])
shell=mesh_m('Hollow organic gourd shell and bent mouth opening',gourd,G,vv,ff,[skin,inside,rim],mi)
# A genuine 3D Boolean aperture accepts both rows. This is only a native visual
# demarcation under the sealing rim, not a reed/fitting fabrication diagram.
cut=box('Temporary Boolean aperture only',gourd,None,(.052,0,.272),(.130,.071,.127),None,0)
bpy.ops.object.select_all(action='DESELECT');shell.select_set(True);bpy.context.view_layer.objects.active=shell
boolean=shell.modifiers.new('Open to interior for visible two-raft fit','BOOLEAN')
boolean.operation='DIFFERENCE';boolean.object=cut;boolean.solver='EXACT'
bpy.ops.object.modifier_apply(modifier=boolean.name)
bpy.data.objects.remove(cut,do_unlink=True)
def gourd_color(p):
    x,y,z=p
    n=.13*math.sin(31*x+7*z)+.11*math.sin(18*y-33*z+23*x)+.055*math.cos(105*y+25*z+63*x)+.032*math.sin(210*x+102*y+71*z)
    neck=(.19 if x<-.175 else 0)
    return (146*(1+n)+14*neck,99*(1+n)+7*neck,55*(1+n)+4*neck)
colors(shell,gourd_color)
# Thick impression of a real imperfect shell opening and binding collar.
# Contour follows the real gourd profile height along the raft entry.
collar=[(-.016,-.035,.252),(.010,-.039,.252),(.050,-.039,.250),(.091,-.037,.243),(.115,-.033,.226),
        (.122,-.022,.224),(.122,.021,.225),(.115,.034,.227),(.091,.039,.245),(.050,.040,.253),
        (.010,.039,.254),(-.019,.036,.253),(-.021,.024,.251),(-.021,-.022,.251)]
sweep('Open dark gourd and raft seam bead, not a filled decal',gourd,G,collar,.0052,wax,10,True)
# Upper pipe tips stay visibly hollow only where represented as open.
# All bases are closed in the exhibit; long raft finish is an illustration,
# not a mapping to finger position, sounding role, or tuning.
locs=[.000,.034,.068,.102]
count=32
def pipe(i,x,y,ztop,rad,mode,z0):
    p=empty(('SHORT_RAFT_' if mode=='open' else 'LONG_RAFT_')+str(i+1),bamboo,Q,(x,y,0))
    ro=rad;ri=rad-(.0027+.00025*(i%3));dv=.001
    profile=[(ro*.83,z0,0),(ro*.97,z0+.009,0),(ro,z0+.050,0),(ro*.986,ztop-.074,0),
       (ro*.992,ztop-.027,0),(ro*.982,ztop-.004,0),(ro*.956,ztop,0),(ri,ztop,1)]
    if mode=='open':
        profile.extend([(ri,ztop-.011,2),(ri*.93,z0+.045,2),(ri*.91,z0+.009,2),(.001,z0+.009,2)])
    elif mode=='seated':
        profile.extend([(ri,ztop-.012,2),(.001,ztop-.014,3)])
    else:
        profile.extend([(ri,ztop-.001,1),(.001,ztop-.001,3)])
    N=count
    rings=[]
    for j,(r,z,m) in enumerate(profile):
        rings.append([(r*(1+.016*math.sin(th*5*math.tau/N+i*.19))*math.cos(th*math.tau/N),
          r*(1+.015*math.cos(th*3*math.tau/N-i*.16))*math.sin(th*math.tau/N),
          z+(0.00045*math.sin(th*math.tau/N+i*.33) if j in (6,7,8) else 0)) for th in range(N)])
    V,Fr,C=addrings([],[],[],rings,N,lambda j,k:profile[j][2])
    V.extend([(0,0,z0),(0,0,profile[-1][1])])
    last=(len(profile)-1)*N
    for k in range(N):
        k1=(k+1)%N
        Fr.append((len(V)-2,k1,k));C.append(0)
        Fr.append((len(V)-1,last+k,last+k1));C.append(2 if mode=='open' else 3)
    ob=mesh_m('Hollow bamboo stalk '+p.name,bamboo,p,V,Fr,[bamb,bamb_cut,bamb_dark,blockmat],C)
    def tint(v):
        x,y,z=v; th=math.atan2(y,x)
        modulation=(.06*math.cos(th*4+i*.51)+.04*math.sin(th*10+i*.74)+.028*math.sin(75*z+3*th+i*.69))
        tone=(.975+(.074 if i%2 else 0))*(1+modulation)
        return (176*tone,137*tone,83*tone)
    colors(ob,tint)
    rz=ztop-(.073 if i%2 else .042)
    bumpV=[]
    bumpF=[]
    for j,(r,h) in enumerate([(ro*.98,rz-.003),(ro*1.036,rz-.0015),(ro*1.043,rz+.001),(ro*.98,rz+.0028)]):
        bumpV.extend((r*math.cos(theta*math.tau/24),r*math.sin(theta*math.tau/24),h) for theta in range(24))
        if j:
            bumpF.extend((k,k1,k1+24,k+24) for k,k1 in (((j-1)*24+t,(j-1)*24+(t+1)%24) for t in range(24)))
    ridge=mesh('Narrow independent bamboo joint witness '+p.name,bamboo,p,bumpV,bumpF,bamb_cut)
    for f in ridge.data.polygons:f.use_smooth=True
    return p
for i,x in enumerate(locs):
    baseH=(.218,.220,.222,.220)[i]
    pipe(i,x,-.016,.568,(.0152,.0145,.0148,.0152)[i],'open',baseH)
    mode=('seated','flat','seated','flat')[i]
    heights=(.782,.690,.782,.628)
    pipe(i,x,.016,heights[i],(.0155,.0149,.0151,.0148)[i],mode,baseH)
# Four slightly imperfect bands and overlapping independent seam crosses.
def outline(z,coords):
    xmin,xmax,ymin,ymax=coords
    r=.020;q=[]
    for cx,cy,offset in [(xmax-r,ymax-r,0),(xmin+r,ymax-r,math.pi/2),(xmin+r,ymin+r,math.pi),(xmax-r,ymin+r,1.5*math.pi)]:
        for i in range(8):
            a=offset+i*math.pi/14
            q.append((cx+r*math.cos(a),cy+r*math.sin(a),z+.001*math.sin(a*2)))
    return q
for center in (.329,.467):
    for i in range(4):
        z=center+.0038*i
        sweep('Individually modeled woven raft binding band',bamboo,Q,outline(z,(-.0175,.1195,-.0345,.0345)),.00275,bindA if i%2 else bindB,8,True)
    for i,x in enumerate((-.006,.022,.041,.067,.089,.108)):
        y=-.0331
        rod('Original tied binding cross stitch',bamboo,Q,(x-.005,y,center-.0006),(x+.003,y-.001,center+.0128),.0015,bindB if i%2 else bindA,8)
# Independent modest cradle with observable support geometry below the broad gourd.
for x,z in [(-.061,.080),(.058,.076)]:
    for s in (-1,1):
        rear_fit=.004 if (x>.05 and s>0) else 0
        a=(x,s*.052,.060); b=(x,s*.046,z+.011-rear_fit); c=(x,s*.037,z-.004-rear_fit)
        sweep('Bent display hardware supporting the dried body',base,F,[a,b,c],.0068,steel,10)
        # Extra axial sections let the existing felt pad follow the curved underside.
        N=16
        spec=[(-.012,.0073),(-.009,.009),(-.006,.009),(-.003,.009),(0,.009),(.003,.009),(.006,.009),(.009,.009),(.012,.0073)]
        rows=[[(xx,r*math.cos(k*math.tau/N),r*math.sin(k*math.tau/N)) for k in range(N)] for xx,r in spec]
        vs,fs,_=addrings([],[],[],rows,N,lambda j,k:0)
        fs.extend([tuple(reversed(range(N))),tuple(range((len(rows)-1)*N,len(rows)*N))])
        padObj=mesh('Felt pinched-contact cradle pad',base,F,vs,fs,pad)
        padObj.location=(x,s*.037,z-.004-rear_fit)
        for poly in padObj.data.polygons:poly.use_smooth=len(poly.vertices)==4
        box('Fastening tab fixed into the timber support',base,F,(x,s*.053,.065),(.038,.027,.009),steel,.004,2)
# Conform only the highest contact tips to the actual exterior shell at
# their own coordinates. Keep the measured felt seat, never enter the interior.
bpy.context.view_layer.update()
gverts=[shell.matrix_world@v.co for v in shell.data.vertices]
gfaces=[tuple(q.vertices) for q in shell.data.polygons]
outside=BVHTree.FromPolygons(gverts,gfaces)
for o in base.objects:
    if not (o.name.startswith('Bent display hardware') or o.name.startswith('Felt pinched-contact')):continue
    m=o.matrix_world.copy(); inv=m.inverted()
    for v in o.data.vertices:
        xyz=m@v.co
        loc,n,_,_=outside.ray_cast(Vector((xyz.x,xyz.y,.030)),Vector((0,0,1)),.100)
        assert loc is not None
        if xyz.z>loc.z+.0008:
            xyz.z=loc.z+.0008
            v.co=inv@xyz
    o.data.update()
# Very subtle rear upright with protective rail, no attachment to the gourd neck.
for x in (.119,):
    rod('Slim dark back stabiliser of display only',base,F,(x,.076,.063),(x,.076,.344),.0068,steel,12)
    rod('Padded rear binder stop arm',base,F,(x,.076,.343),(x,.036,.343),.0081,pad,12)
    box('Lower rear support plate seated on display wood',base,F,(x,.077,.068),(.037,.035,.013),steel,.004,2)
box('Studio ground only',studio,None,(0,0,-.027),(200,200,.053),stage,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,pos,w,s,col,aim=(0,0,.36)):
    d=bpy.data.lights.new(n,'AREA');d.energy=w;d.size=s;d.shape='DISK';d.color=col
    o=bpy.data.objects.new(n,d);studio.objects.link(o);o.location=pos;look(o,aim)
lamp('Warm wood tonal key',(-1.50,-1.72,1.72),162,1.55,(1,.89,.75))
lamp('Pale fill aimed at contrasting rows',(1.19,-1.27,1.45),117,1.20,(.84,.94,1))
lamp('High gradual rim on bamboo top',(.38,.82,1.62),100,.88,(1,.92,.80))
world=bpy.data.worlds.new('Pale gallery studio fill');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.52,.55,.54,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.39
cd=bpy.data.cameras.new('Editorial cutaway camera');cam=bpy.data.objects.new('Editorial cutaway camera',cd);studio.objects.link(cam);S.camera=cam
hero=(.74,-1.51,1.02);target=(-.037,.0,.385)
cd.type='ORTHO';cd.ortho_scale=.96;cam.location=hero;look(cam,target)
S.render.engine='CYCLES';S.cycles.samples=184;S.cycles.use_denoising=False
S.cycles.adaptive_threshold=.012;S.cycles.adaptive_min_samples=55
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_percentage=100;S.render.resolution_x=S.render.resolution_y=512
S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=92
S.view_settings.view_transform='AgX';S.view_settings.exposure=.03
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True)
for c in (base,gourd,bamboo):
    for o in c.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/(slug+'.glb')),export_format='GLB',use_selection=True,
                         export_texcoords=False,export_animations=False,export_cameras=False,
                         export_lights=False,export_extras=False)
def still(to,pos,tgt,scale,wh):
    cam.location=pos;look(cam,tgt);cd.ortho_scale=scale
    S.render.resolution_x,S.render.resolution_y=wh;S.render.filepath=str(to)
    bpy.ops.render.render(write_still=True)
if not opts.skip_render:still(out/'previews/studio.webp',hero,target,.96,(512,512))
if opts.review:
    S.cycles.samples=68
    still(opts.review/'mouth-opening-and-raft-junction.webp',(-.66,-.70,.54),(-.079,-.003,.202),.40,(645,595))
    still(opts.review/'true-short-mouths-and-closed-long-ends.webp',(.62,-.61,1.25),(.048,0,.652),.30,(650,590))
    still(opts.review/'back-lit-stand-and-binding.webp',(.52,.78,.69),(.029,0,.271),.64,(620,580))
