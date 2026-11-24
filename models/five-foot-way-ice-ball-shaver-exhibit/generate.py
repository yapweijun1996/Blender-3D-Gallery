"""Original static Singapore five-foot-way ice-ball shaver exhibit, no operative blade or process."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
opts=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='five-foot-way-ice-ball-shaver-exhibit'
out=opts.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if opts.review:opts.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
base=collection('01 independent retail exhibit ground')
last=collection('02 original non-operational timber shaver')
loose=collection('03 independent staged ice and empty catch bowl')
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

def etch(n,c,p,o,text,size,mat):
    data=bpy.data.curves.new(n,'FONT'); data.body=text; data.align_x='CENTER';data.size=size
    ob=bpy.data.objects.new(n,data);assign(ob,n,c,p,mat);ob.location=o
    ob.rotation_euler.x=math.pi/2
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.object.convert(target='MESH')
    return ob


def multi(n,c,r,v,f,m,ids,smooth=False):
    o=mesh(n,c,r,v,f,m[0])
    for mat in m[1:]:o.data.materials.append(mat)
    for p,k in zip(o.data.polygons,ids):p.material_index=k;p.use_smooth=smooth and len(p.vertices)==4
    return o
slate=material('Deep petrol museum slab','283F43',.60,.18)
satin=material('Muted unpainted exhibition marker','D1C5A8',.52,.18)
wood=material('Golden brown satin original timber','92623E',.56)
darkwood=material('Side endgrain and old uprights','765135',.57)
warm=material('Slight longitudinal sanded wood fleck','977353',.61)
darkmetal=material('Plain sealed smooth slot surround','64726F',.46,.48)
bright=material('Age-polished rounded fitting','8D9D98',.37,.52)
black=material('Matte historic dark hardware','414340',.61,.35)
bowlMat=material('Cream and green-gray enamel bowl body','6E9690',.46,.24)
bowlInside=material('Neutral quiet enamel bowl interior','CFD4BF',.46,.16)
iceMat=material('Frosted pale exhibit ice prop','C0D9DA',.70,.04)
iceFace=material('Frosted uneven facet highlights','DAE7E1',.58,.01)
iceBlue=material('Pale translucent-looking facet, opaque','9FC6C9',.60,.03)
studioMat=material('Studio slate matte','344952',.83)
ped=empty('SEPARATE_MODERN_MUSEUM_SUPPORT',base)
frame=empty('ORIGINAL_WOODEN_SHAVER_EXHIBIT',last)
stilllife=empty('EMPTY_BOWL_AND_SEPARATE_STAGED_ICE',loose)
box('Modern dark exhibit plinth',base,ped,(0,0,.021),(.535,.833,.042),slate,.018,3)
box('Front inset museum label plate',base,ped,(0,-.416,.021),(.358,.006,.032),slate,.004,1)
etch('Original exhibit caption',base,ped,(0,-.420,.015),'FIVE-FOOT WAY   /   ICE-BALL SHAVER',.0149,satin)
for x in (-.13,.13):
    for y in (-.21,.224):
        box('Seated tapered square timber leg',last,frame,(x,y,.111),(.056,.055,.142),darkwood,.008,2)
        box('Steel cap seated on timber leg',last,frame,(x,y,.045),(.047,.046,.007),black,.003,2)
        rod('Seated round dark joint rivet',last,frame,(x,y-.028,.143),(x,y-.031,.143),.007,bright,9)
    box('Long physical under-frame apron',last,frame,(x,0,.146),(.047,.50,.055),darkwood,.006,2)
for y in (-.208,.224):
    box('Inboard transverse apron; supported',last,frame,(0,y,.150),(.248,.043,.045),wood,.006,2)
# Main original top is a single manifold solid with a true, fully open slot.
top=box('Continuous bench deck with true through slot',last,frame,(0,0,.195),(.348,.664,.043),wood,.010,3)
top.data.materials.append(darkwood)
bpy.ops.object.select_all(action='DESELECT');top.select_set(True);bpy.context.view_layer.objects.active=top
for m in list(top.modifiers):bpy.ops.object.modifier_apply(modifier=m.name)
# Cutting tool is deleted from the scripted artwork before save/export.
tool=box('Temporary negative space',last,None,(0,-.103,.195),(.156,.048,.130),darkwood,.007,3)
for m in list(tool.modifiers):bpy.ops.object.modifier_apply(modifier=m.name)
bpy.context.view_layer.objects.active=top;top.select_set(True);tool.select_set(False)
mod=top.modifiers.new('Actual through-opening clear of all mechanisms','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=tool
bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(tool,do_unlink=True)
# Two neutral rounded edges related to the opening, deliberately no sharp
# or detachable edge, real-world specifications, force or moving mechanism.
for side in (-1,1):
    box('Rounded nonoperative slot side trim',last,frame,(side*.087,-.102,.219),(.014,.066,.014),darkmetal,.006,3)
    for y in (-.127,-.074):
        rod('Plain retained end screw',last,frame,(side*.089,y,.225),(side*.089,y,.227),.004,bright,10)
for y in (-.140,-.066):
    box('Fixed blunt slot reveal lip',last,frame,(0,y,.220),(.173,.009,.017),bright,.004,3)
for x in (-.158,.158):
    box('Raised longitudinal rounded exhibit side rail',last,frame,(x,-.020,.226),(.019,.535,.035),wood,.008,2)
    for y in (-.253,.212):
        rod('Side rail fixed flush fastener head',last,frame,(x,y,.237),(x,y,.244),.0056,bright,12)
# A small muted long-grain accent in real mesh, without mapped texture or
# distracting color triangles around the opening.
import random
rng=random.Random(925); vv=[];ff=[]
for side in (-1,1):
    for i in range(15):
        x=side*(.104+i*.0026); y=rng.uniform(-.29,.03); y2=min(y+rng.uniform(.10,.25),.287); j=len(vv)
        vv += [(x,y,.21657),(x+.00038,y+.028,.21657),(x,y2,.21657),(x-.00030,y+.025,.21657)]
        ff.append((j,j+1,j+2,j+3))
mesh('Fine subtle lengthwise timber flecks',last,frame,vv,ff,warm)
# Empty formed display bowl, a genuine continuous thin shell with bottom.
def bowl():
    x,y,z=0,-.103,.042
    rows=[(.052,0,0),(.062,.003,0),(.076,.012,0),(.087,.026,0),(.102,.046,0),(.105,.053,0),
        (.104,.057,0),(.100,.058,1),(.096,.054,1),(.095,.047,1),(.081,.027,1),(.066,.014,1),(.050,.007,1)]
    N=32;v=[];f=[];ia=[]
    for r,h,k in rows:
        for i in range(N):
            a=math.tau*i/N;v.append((x+r*math.cos(a),y+r*math.sin(a),z+h))
    for j in range(len(rows)-1):
        for i in range(N):
            k=(i+1)%N;f.append((j*N+i,j*N+k,(j+1)*N+k,(j+1)*N+i));ia.append(rows[j][2])
    f+=[tuple(reversed(range(N))),tuple(range((len(rows)-1)*N,len(rows)*N))];ia += [0,1]
    return multi('Closed thin enamel catch bowl with open cavity',loose,stilllife,v,f,[bowlMat,bowlInside],ia,True)
bowl()
ice=box('Frosty sculpted demonstration ice block, stationary',loose,stilllife,(.003,.154,.260),(.164,.173,.087),iceMat,.015,3)
ice.data.materials.append(iceFace);ice.data.materials.append(iceBlue)
for i,f in enumerate(ice.data.polygons):
    if f.normal.z<.5 and f.normal.y<-.5:f.material_index=2
    if f.normal.z>.5:f.material_index=1
for y in (.232,.254):
    box('Stationary blank rear display stop',last,frame,(.001,y,.224),(.152,.012,.017),darkwood,.003,2)
box("Studio matte shadow only excluded",studio,None,(0,0,-.027),(100,100,.053),studioMat,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def light(n,where,w,sz,col,aim=(0,0,.79)):
    l=bpy.data.lights.new(n,'AREA');l.energy=w;l.size=sz;l.shape='DISK';l.color=col
    o=bpy.data.objects.new(n,l);studio.objects.link(o);o.location=where;look(o,aim)
light('Warm key highlights steel wheels and cut concrete',(-2.75,-3.1,3.66),420,2.35,(1,.91,.80))
light('Cool quiet fill shapes model plinth',(2.9,-2.13,2.74),280,2.0,(.83,.94,1))
light('Upper reflected rim on upper steel bracket',(.91,2.3,2.75),240,1.70,(1,.92,.78))
world=bpy.data.worlds.new('Warm natural exhibit fill');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.54,.55,.52,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.38
cd=bpy.data.cameras.new('Editorial cutaway camera');cam=bpy.data.objects.new('Editorial cutaway camera',cd);studio.objects.link(cam);S.camera=cam
hero=(1.37,-1.24,.84);target=(0,-.007,.153)
cd.type='ORTHO';cd.ortho_scale=1.020;cam.location=hero;look(cam,target)
S.render.engine='CYCLES';S.cycles.samples=145;S.cycles.use_denoising=False
S.cycles.adaptive_threshold=.012;S.cycles.adaptive_min_samples=38
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
if not opts.skip_render:still(out/'previews/studio.webp',hero,target,1.020,(512,512))



if opts.review:
    S.cycles.samples=93
    still(opts.review/'true-open-slot-and-rounded-trim.webp',(.42,-.52,1.19),(0,-.080,.211),.512,(640,560))
    still(opts.review/'empty-catch-bowl-under-wood-frame.webp',(.53,-.68,.346),(0,-.103,.126),.52,(630,540))
