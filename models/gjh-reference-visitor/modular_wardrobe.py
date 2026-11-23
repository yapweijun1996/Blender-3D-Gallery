"""Split socks, label existing wardrobe parts and add optional fitted garments.

Run on the working GJH Reference Visitor scene. Existing source is backed up
by the caller before execution. Optional garments are hidden in the default
scene and retain the visitor's armature weights for export as variants.
"""
import bpy, bmesh, math
from mathutils import Vector
sc=bpy.data.scenes['GJH Reference Visitor']; bpy.context.window.scene=sc
model=next(c for c in sc.collection.children if c.name.startswith('GJH Visitor Model'))
rig=next(o for o in model.objects if o.type=='ARMATURE');root=next(o for o in model.objects if o.name=='GJH_Visitor')

# Existing leg meshes have separate skin/sock geometry but share one object.
# Split along the authored material boundary; existing deform groups survive.
for side in ('L','R'):
    leg=next(o for o in model.objects if o.name.startswith('Leg.'+side))
    sock=leg.copy();sock.data=leg.data.copy();model.objects.link(sock);sock.name='Sock.'+side
    sock_mats=[i for i,m in enumerate(leg.data.materials) if m and m.name.startswith('Sock')]
    if len(sock_mats)!=1: raise RuntimeError('Expected one sock material in '+leg.name)
    idx=sock_mats[0]
    def retain(obj,keep_sock):
        bm=bmesh.new();bm.from_mesh(obj.data)
        remove=[f for f in bm.faces if (f.material_index==idx)!=keep_sock]
        bmesh.ops.delete(bm,geom=remove,context='FACES')
        orphans=[v for v in bm.verts if not v.link_faces]
        if orphans:bmesh.ops.delete(bm,geom=orphans,context='VERTS')
        bm.to_mesh(obj.data);bm.free();obj.data.update()
        if not obj.data.polygons:raise RuntimeError('Empty split '+obj.name)
    retain(leg,False);retain(sock,True)
    leg['partSlot']='Leg.'+side;sock['partSlot']='Sock.'+side

# Logical slots can contain several meshes and distinct bone bindings.
for o in model.objects:
    n=o.name
    if o.type!='MESH':continue
    if n.startswith('Head'): slot='Head'
    elif n.startswith('Hair'):slot='Hair'
    elif n.startswith('Hoodie') or n.startswith(('Long sleeve','Purple cuff','Purple collar','Purple hood back','Chest bag logo')):slot='Hoodie'
    elif n.startswith('Backpack'):slot='Backpack'
    elif n.startswith(('Shorts','Cargo side pocket')):slot='Shorts'
    elif n.startswith('Shoe.L'):slot='Shoe.L'
    elif n.startswith('Shoe.R'):slot='Shoe.R'
    elif n.startswith('Arm.L'):slot='Arm.L'
    elif n.startswith('Arm.R'):slot='Arm.R'
    else:continue
    o['partSlot']=slot

opts=bpy.data.collections.new('GJH Optional Wardrobe');sc.collection.children.link(opts)
def mat(name,rgba):
    m=bpy.data.materials.new(name);m.diffuse_color=(*rgba,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*rgba,1);bs.inputs['Roughness'].default_value=.65
    return m
denim=mat('Optional denim',(0.045,.11,.27));stitch=mat('Optional denim seam',(.18,.27,.43)); capmat=mat('Optional cap lavender',(.26,.12,.48));capband=mat('Optional cap brim',(.13,.06,.25));cappanel=mat('Optional cap front panel',(.72,.72,.82))
def mesh_obj(name,verts,faces,material,slot):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();me.materials.append(material)
    o=bpy.data.objects.new(name,me);opts.objects.link(o);o.parent=root;o['partSlot']=slot;o['optional']=True
    for p in me.polygons:p.use_smooth=True
    return o
def bind(o, weights):
    groups={name:o.vertex_groups.new(name=name) for name in weights}
    for name,indices in weights.items():
        for i,w in indices:
            if w>0:groups[name].add([i],w,'REPLACE')
    mod=o.modifiers.new('Visitor armature','ARMATURE');mod.object=rig
# Fitted cap dome; the open lower ring sits over the scalp and leaves face visible.
N=32;verts=[];faces=[]
for j in range(11):
    theta=(math.pi/2)*(j/10)
    rr=math.sin(theta);z=.875+.120*math.cos(theta)
    for k in range(N):
        a=2*math.pi*k/N;verts.append((.215*rr*math.cos(a),.032+.245*rr*math.sin(a),z))
for j in range(10):
    for k in range(N):
        a=j*N+k;b=j*N+(k+1)%N;faces.append((a,b,b+N,a+N))
cap=mesh_obj('Hat_Crown',verts,faces,capmat,'Hat');cap.data.materials.append(cappanel)
for poly in cap.data.polygons:
    if (poly.index % N) in range(21,28):poly.material_index=1
bind(cap,{'Head':[(i,1.) for i in range(len(verts))]})
# Bill is a shallow, rounded ellipsoid, partly embedded into the forehead edge.
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=10,location=(0,-.205,.875))
bill=bpy.context.object
for c in list(bill.users_collection):c.objects.unlink(bill)
opts.objects.link(bill);bill.name='Hat_Bill';bill.parent=root;bill.scale=(.146,.120,.015);bill.rotation_euler.x=.12
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);bill.data.materials.append(capband);bill['partSlot']='Hat';bill['optional']=True
for p in bill.data.polygons:p.use_smooth=True
bind(bill,{'Head':[(i,1.) for i in range(len(bill.data.vertices))]})
# Straight trousers: hip and two leg shells; leg weights blend around the knee.
verts=[];faces=[];boneweights={'Root':[],'UpperLeg.L':[],'UpperLeg.R':[],'LowerLeg.L':[],'LowerLeg.R':[]}
def jeans_loft(rings,side=None,n=24):
    start=len(verts)
    for z,rx,ry,cx in rings:
        for k in range(n):
            a=2*math.pi*k/n;sp=lambda v:math.copysign(abs(v)**.8,v)
            idx=len(verts);verts.append((cx+rx*sp(math.cos(a)),.006+ry*sp(math.sin(a)),z))
            if side is None:boneweights['Root'].append((idx,1))
            else:
                lower=max(0,min(1,(.18-z)/.05));boneweights['UpperLeg.'+side].append((idx,1-lower));boneweights['LowerLeg.'+side].append((idx,lower))
    for j in range(len(rings)-1):
        for k in range(n):
            a=start+j*n+k;b=start+j*n+(k+1)%n;faces.append((a,b,b+n,a+n))
    faces.append(tuple(start+k for k in reversed(range(n))));end=start+(len(rings)-1)*n;faces.append(tuple(end+k for k in range(n)))
jeans_loft([(.28,.105,.061,0),(.31,.108,.061,0),(.332,.101,.061,0)])
for sign,side in ((1,'L'),(-1,'R')):
    jeans_loft([(.072,.048,.060,sign*.068),(.13,.050,.061,sign*.068),(.19,.054,.065,sign*.068),(.26,.060,.076,sign*.065),(.28,.059,.075,sign*.065)],side)
jeans=mesh_obj('Jeans',verts,faces,denim,'Jeans');bind(jeans,boneweights)
for o in opts.objects:o.hide_render=True;o.hide_set(True)
bpy.context.view_layer.update()
result={'optional_parts':[o.name for o in opts.objects],'slots':sorted({o.get('partSlot') for o in model.objects if o.get('partSlot')}),'sock_split':True}
