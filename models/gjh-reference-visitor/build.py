import bpy, math, os
from mathutils import Vector
BASE='/Users/yapweijun/Documents/GitHub/Blender-3D-Gallery'
OUT=os.path.join(BASE,'models/gjh-reference-visitor')
SOURCE=os.path.join(BASE,'models/chibi-visitor-v4/sources/chibi-visitor-v4.blend')
scene=bpy.data.scenes.new('GJH Reference Visitor')
bpy.context.window.scene=scene
with bpy.data.libraries.load(SOURCE,link=False) as (src,dst):
    dst.collections=['CV4 Model']
model=dst.collections[0]
model.name='GJH Visitor Model'
scene.collection.children.link(model)
objs={o.name.split('.')[0]:o for o in model.objects}
for obj in list(model.objects):
    if obj.name.split('.')[0] in ('Bag','Watch'):
        bpy.data.objects.remove(obj,do_unlink=True)
root=next(o for o in model.objects if o.type=='EMPTY')
root.name='GJH_Visitor'

def color(hex):
    rgb=[int(hex[i:i+2],16)/255 for i in (0,2,4)]
    return tuple((v/12.92 if v<0.04045 else ((v+0.055)/1.055)**2.4) for v in rgb)+(1,)
def setmat(mat,h):
    mat.diffuse_color=color(h)
    if mat.use_nodes:
        n=mat.node_tree.nodes.get('Principled BSDF')
        if n:n.inputs['Base Color'].default_value=color(h)
def material(name,h):
    m=bpy.data.materials.new(name);m.diffuse_color=color(h);m.use_nodes=True
    n=m.node_tree.nodes.get('Principled BSDF');n.inputs['Base Color'].default_value=color(h);n.inputs['Roughness'].default_value=.64
    return m
hoodie=objs['Hoodie']
for mat in hoodie.data.materials:
    name=mat.name.split('.')[0]
    if name in ('Hoodie','Hoodie seam'):setmat(mat,'EDE8F5')
    elif name=='Hoodie rib':setmat(mat,'7335BE')
    elif name=='Drawstring':setmat(mat,'783DC1')
    elif name=='Tee':setmat(mat,'EDE8F5')
# The inherited short-sleeve cuff is covered by the long sleeve.
for poly in hoodie.data.polygons:
    c=poly.center
    if poly.material_index == 1 and abs(c.x) > .10 and .42 < c.z < .47:
        poly.material_index = 0
for mat in objs['Shorts'].data.materials:
    if mat.name.startswith('Shorts'):setmat(mat,'34323B')
for obj in model.objects:
    if obj.name.startswith('Shoe'):
        for mat in obj.data.materials:
            if mat.name.startswith('Shoe') and not mat.name.startswith('Shoe rubber'):setmat(mat,'7037B3')
purple=material('GJH Purple','7136B7'); light=material('GJH Hoodie Ivory','EDE8F5'); dark=material('Backpack Charcoal','282530'); packface=material('Backpack Pocket','3C3647'); white=material('Logo White','FAF8FF'); seam=material('Cargo Pocket','403D46')

def relink(obj):
    for c in list(obj.users_collection):c.objects.unlink(obj)
    model.objects.link(obj);obj.parent=root
    return obj
def uvball(name,loc,scale,mat,segments=24,rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=loc)
    o=relink(bpy.context.object);o.name=name;o.scale=scale;o.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for p in o.data.polygons:p.use_smooth=True
    return o
def box(name,loc,scale,mat,bevel=.01):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=relink(bpy.context.object);o.name=name;o.dimensions=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat)
    if bevel:
        mod=o.modifiers.new('Rounded edges','BEVEL');mod.width=bevel;mod.segments=3
        o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    return o
def tube(name,points,radius,mat):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=2;cu.bevel_depth=radius;cu.bevel_resolution=2
    s=cu.splines.new('POLY');s.points.add(len(points)-1)
    for p,co in zip(s.points,points):p.co=(*co,1)
    ob=bpy.data.objects.new(name,cu);model.objects.link(ob);ob.parent=root;ob.data.materials.append(mat);return ob
# Long sleeves overlay the exposed forearms; cuffs end above the fists.
for s in (-1,1):
    a=Vector((s*.115,.003,.455));b=Vector((s*.166,-.001,.339));mid=(a+b)/2
    o=uvball('Long sleeve',mid,(.054,.055,(b-a).length/2+.029),light)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    o=uvball('Purple cuff',(s*.169,-.002,.339),(.038,.042,.018),purple)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
# Shoulder straps follow the front of the torso.
for s in (-1,1):
    tube('Backpack shoulder strap',[(s*.069,-.030,.547),(s*.081,-.068,.518),(s*.091,-.082,.472),(s*.096,-.086,.431)],.009,dark)
uvball('Purple hood back',(0,.092,.533),(.104,.055,.050),purple)
for s in (-1,1):
    uvball('Purple collar',(s*.048,-.038,.540),(.054,.035,.020),purple)
box('Backpack',(0,.143,.425),(.172,.085,.200),dark,.023)
box('Backpack front pocket',(0,.192,.405),(.131,.022,.107),packface,.017)
# Shopping-bag emblems, drawn in contrasting raised linework.
def icon(name,y,z,mat,sign=-1,scale=1):
    x=.023*scale;h=.031*scale
    tube(name+' outline',[(-x,y,z),(-x*.82,y,z+h),(x*.82,y,z+h),(x,y,z),(-x,y,z)],.0028*scale,mat)
    points=[]
    for i in range(15):
        a=math.pi*i/14;points.append((.011*scale*math.cos(a),y,z+h+.001*scale+.014*scale*math.sin(a)))
    tube(name+' handle',points,.0028*scale,mat)
icon('Chest bag logo',-.125,.416,purple,scale=1.0)
# Project the chest emblem onto the sweatshirt so it follows its curved surface.
from mathutils.bvhtree import BVHTree
bpy.context.view_layer.update()
surface=BVHTree.FromObject(hoodie,bpy.context.evaluated_depsgraph_get())
for obj in model.objects:
    if obj.name.startswith('Chest bag logo'):
        for spline in obj.data.splines:
            for point in spline.points:
                hit, normal, face, distance=surface.ray_cast(Vector((point.co.x,-1,point.co.z)),Vector((0,1,0)))
                if hit is None: raise RuntimeError('Chest emblem projection missed the hoodie')
                point.co.y=hit.y-.002

icon('Backpack bag logo',.206,.401,white,scale=1.0)
# Replace the rolled layered shorts with simpler loose cargo legs.
bpy.data.objects.remove(objs['Shorts'], do_unlink=True)
box('Shorts waist',(0,0,.301),(.225,.158,.073),seam,.016)
for s in (-1,1):
    box('Shorts leg',(s*.064,0,.258),(.126,.166,.105),seam,.012)
for s in (-1,1):
    box('Cargo side pocket',(s*.124,.002,.251),(.024,.092,.060),seam,.006)
# Reduce mesh density while retaining the sculpted facial texture and silhouette.
for o in model.objects:
    if o.type=='MESH':
        if o.name.startswith('Hair'):ratio=.22
        elif o.name.startswith('Head'):ratio=.55
        elif o.name.startswith('Arm.'):ratio=.45
        else:continue
        mod=o.modifiers.new('Game mesh reduction','DECIMATE');mod.ratio=ratio
root.scale=(1.297,)*3
# Refine the shorts profile after creating the initial wardrobe.
exec(compile(open(os.path.join(OUT, 'shorts.py')).read(), 'shorts.py', 'exec'))
for o in model.objects:
    if o.name.startswith('Hair'):
        for hair_mat in o.data.materials:
            if hair_mat.use_nodes:
                hair_mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.62
# Studio is intentionally outside export collection.
studio=bpy.data.collections.new('GJH Studio');scene.collection.children.link(studio)
def link_studio(obj):
    for c in list(obj.users_collection):c.objects.unlink(obj)
    studio.objects.link(obj)
world=bpy.data.worlds.new('GJH Studio World');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.76,.72,.84,1);world.node_tree.nodes['Background'].inputs[1].default_value=.7;scene.world=world
for name,loc,power,size in [('Key',(-3,-4,5),450,4),('Fill',(4,-2,3),250,4),('Rim',(1,3,4),380,3)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    o=bpy.data.objects.new(name,data);studio.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,.68))-o.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('Turnaround Camera');cam=bpy.data.objects.new('Turnaround Camera',camdata);studio.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=1.47
scene.render.engine='CYCLES';scene.cycles.samples=32
scene.render.resolution_x=750;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX'
for name,angle in [('front',0),('three-quarter',32),('side',90),('back',180)]:
    a=math.radians(angle);target=Vector((0,0,.65));cam.location=target+Vector((4*math.sin(a),-4*math.cos(a),0));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=os.path.join(OUT,'previews',name+'.png');bpy.ops.render.render(write_still=True,scene=scene.name)
# Set the open scene to a useful three-quarter camera and preserve the original startup scene.
a=math.radians(32);target=Vector((0,0,.65));cam.location=target+Vector((4*math.sin(a),-4*math.cos(a),0));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'sources','gjh-reference-visitor.blend'))
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,'exports','gjh-reference-visitor.glb'),export_format='GLB',collection=model.name,export_yup=True,export_apply=True,export_vertex_color='MATERIAL',export_animations=False)
result={'blend':bpy.data.filepath,'objects':len(model.objects),'export':os.path.join(OUT,'exports','gjh-reference-visitor.glb')}
