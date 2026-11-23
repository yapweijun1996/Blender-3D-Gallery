"""Split the existing face into editable parts while retaining the rest appearance.

Run on a disposable copy of the visitor scene; save only after visual QA. Eyes,
brows and mouth are fitted textured skin-surface patches, not volumetric anatomy.
The base face uses a reconstructed skin-only texture beneath those patches.
Ears and nose are cut from the fused mesh; cut boundaries are capped on the head.
"""
import bpy
import bmesh
import numpy as np
from mathutils import Vector

scene=bpy.data.scenes['GJH Reference Visitor']
bpy.context.window.scene=scene
model=next(c for c in scene.collection.children if c.name.startswith('GJH Visitor Model'))
rig=next(o for o in model.objects if o.type=='ARMATURE')
original=next(o for o in model.objects if o.type=='MESH' and o.name.startswith('Head'))
if original.get('face_modularized'):
    raise RuntimeError('Face is already modularized')
if len(original.data.materials)!=1:
    raise RuntimeError('Expected a single painted face material')

# Freeze reduction on a private copy, retaining armature, vertex weights and UVs.
head=original.copy(); head.data=original.data.copy();model.objects.link(head)
head.name='Head_Skin';head['partSlot']='Head';head['face_modularized']=True
for o in bpy.context.selected_objects:o.select_set(False)
head.select_set(True);bpy.context.view_layer.objects.active=head
for mod in list(head.modifiers):
    if mod.type!='ARMATURE':bpy.ops.object.modifier_apply(modifier=mod.name)
base_mesh=head.data

# Reproduce the skin and blush underpaint, leaving ears and nose colour intact.
original_mat=original.data.materials[0]
tex=next((n for n in original_mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image),None)
if tex is None:raise RuntimeError('Expected packed face texture')
source_image=tex.image;w,h=source_image.size
if (w,h)!=(1024,1024):raise RuntimeError('Unexpected face texture dimensions')
pixels=np.empty(w*h*4,dtype=np.float32);source_image.pixels.foreach_get(pixels)
pixels=pixels.reshape((h,w,4))
axis=(np.arange(w)+.5)*(.48/w);gx,gz=np.meshgrid(axis-.24,axis+.53)
def srgb(value):return np.array([int(value[i:i+2],16)/255 for i in (0,2,4)],dtype=np.float32)
def soft(cx,cz,a,b):return np.exp(-((gx-cx)/a)**2-((gz-cz)/b)**2)
background=np.empty((h,w,3),np.float32);background[:]=srgb('FBD2B2')
def paint(c,a):
    global background
    a=np.clip(a,0,1)[...,None];background[:]=background*(1-a)+c*a
paint(srgb('F59C92'),.55*soft(.118,.632,.036,.026)+.55*soft(-.118,.632,.036,.026))
paint(srgb('E8A688'),.30*soft(0,.6455,.007,.0035))
for side in (-1,1):paint(srgb('EDA688'),.55*soft(side*.187,.650,.009,.022))
# Erase all painted feature pixels beneath selectable patches, leaving the rest unchanged.
feature_masks={}
for side, suffix in ((1,'L'),(-1,'R')):
    feature_masks['Eye.'+suffix]=(np.abs(gx-side*.082)<.055)&(gz>.630)&(gz<.735)
    feature_masks['Brow.'+suffix]=(np.abs(gx-side*.085)<.052)&(gz>=.735)&(gz<.783)
feature_masks['Mouth']=(np.abs(gx)<.043)&(gz>.588)&(gz<.633)
source_pixels=pixels.copy()
def make_image_and_material(name, keep):
    data=source_pixels.copy()
    if keep is None:
        for mask in feature_masks.values():data[mask,:3]=background[mask]
    else:
        # Opaque only where this feature differs from skin. Other facial marks
        # cannot bleed into this patch even where their surface meshes overlap.
        difference=np.max(np.abs(source_pixels[:,:,:3]-background),axis=2)
        data[:,:,3]=np.clip(difference/.025,0,1)*feature_masks[keep]
    image=bpy.data.images.new('Visitor '+name,width=w,height=h,alpha=True)
    image.pixels.foreach_set(data.ravel());image.pack()
    material=original_mat.copy();material.name='Visitor '+name
    node=next(n for n in material.node_tree.nodes if n.type=='TEX_IMAGE' and n.image)
    node.image=image
    if keep is not None:
        material.node_tree.links.new(node.outputs['Alpha'],material.node_tree.nodes.get('Principled BSDF').inputs['Alpha'])
        material.surface_render_method='BLENDED'
    return material
base_mat=make_image_and_material('skin under face',None)
feature_mats={name:make_image_and_material(name,name) for name in feature_masks}

# Partition by source face centroid. The meshes keep original UV, material and weights.
def label(f):
    p=f.calc_center_median();n=f.normal
    if .590<p.z<.712 and p.y>-.04:
        if p.x>.170:return 'Ear.L'
        if p.x<-.170:return 'Ear.R'
    if n.y<.2 and p.y<-.12 and abs(p.x)<.0125 and .641<p.z<.663:return 'Nose'
    if n.y<.2:
        for s,side in ((1,'L'),(-1,'R')):
            if abs(p.x-s*.082)<.059 and .629<p.z<.735:return 'Eye.'+side
            if abs(p.x-s*.085)<.057 and .735<=p.z<.785:return 'Brow.'+side
        if abs(p.x)<.049 and .586<p.z<.635:return 'Mouth'
    return 'Skin'

# Each duplicate starts from the same frozen topology so borders share coordinates.
def clone_part(name,wanted,offset=0.0):
    obj=head.copy();obj.data=base_mesh.copy();model.objects.link(obj);obj.name=name;obj['partSlot']=name
    bm=bmesh.new();bm.from_mesh(obj.data);bm.normal_update()
    def include(f):
        p=f.calc_center_median()
        if wanted in ('Ear.L','Ear.R','Nose'):return label(f)==wanted
        if f.normal.y >= .2:return False
        if wanted.startswith('Eye.'):
            side=1 if wanted.endswith('L') else -1
            return abs(p.x-side*.082)<.070 and .615<p.z<.755
        if wanted.startswith('Brow.'):
            side=1 if wanted.endswith('L') else -1
            return abs(p.x-side*.085)<.070 and .715<p.z<.800
        if wanted=='Mouth':return abs(p.x)<.060 and .575<p.z<.650
        return label(f)==wanted
    doomed=[f for f in bm.faces if not include(f)]
    bmesh.ops.delete(bm,geom=doomed,context='FACES')
    if offset:
        for v in bm.verts:v.co+=v.normal*offset
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    if not obj.data.polygons:raise RuntimeError('No polygons for '+name)
    return obj

parts=[]
for name in ('Eye.L','Eye.R','Brow.L','Brow.R','Mouth'):
    part=clone_part(name,name,.00030 if name.startswith('Brow.') else .00015)
    part.data.materials.clear();part.data.materials.append(feature_mats[name]);parts.append(part)
for name in ('Ear.L','Ear.R','Nose'):
    parts.append(clone_part(name,name))

# Remove the physically separated ears and nose. Cap each freshly cut boundary
# so hiding a part doesn't expose an open mesh; capped area uses plain skin.
bm=bmesh.new();bm.from_mesh(head.data);bm.normal_update()
cut_layers=bm.edges.layers.int.new('face_cut')
original_boundary=bm.edges.layers.int.new('original_boundary')
for edge in bm.edges:
    edge[original_boundary]=int(edge.is_boundary)
for edge in bm.edges:
    labs={label(f) for f in edge.link_faces}
    if 'Skin' in labs or any(x.startswith(('Eye.','Brow.')) or x=='Mouth' for x in labs):
        if any(x in ('Ear.L','Ear.R','Nose') for x in labs):edge[cut_layers]=1
doomed=[f for f in bm.faces if label(f) in ('Ear.L','Ear.R','Nose')]
bmesh.ops.delete(bm,geom=doomed,context='FACES')
boundary=[e for e in bm.edges if e.is_boundary]
cap_faces=bmesh.ops.holes_fill(bm,edges=boundary,sides=0).get('faces',[])
for face in cap_faces:face.material_index=1
bm.to_mesh(head.data);bm.free();head.data.update()
head.data.materials.clear();head.data.materials.append(base_mat)
cap_mat=bpy.data.materials.new('Visitor skin cap');cap_mat.diffuse_color=base_mat.diffuse_color;cap_mat.use_nodes=True
cap_mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=base_mat.diffuse_color
head.data.materials.append(cap_mat)
# Shallow skin underlays hide the original hair cutout when the ear is removed.
# Their residual side silhouette is a known limitation of the fused source.
root=next(o for o in model.objects if o.name=='GJH_Visitor')
for side in (-1,1):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,location=(side*.171,.032,.651))
    plug=bpy.context.object
    for collection in list(plug.users_collection):collection.objects.unlink(plug)
    model.objects.link(plug);plug.parent=root;plug.name='Ear_Underlay.'+('L' if side>0 else 'R')
    plug.scale=(.013,.031,.041)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    plug.data.materials.append(cap_mat);plug['partSlot']='Head'
    for poly in plug.data.polygons:poly.use_smooth=True
    group=plug.vertex_groups.new(name='Head');group.add(list(range(len(plug.data.vertices))),1.,'REPLACE')
    modifier=plug.modifiers.new('Visitor armature','ARMATURE');modifier.object=rig
# Keep the untouched source outside the runtime collection so collection-based
# exports cannot accidentally include the original painted face as a duplicate.
source_collection=bpy.data.collections.get('GJH Face Source')
if source_collection is None:
    source_collection=bpy.data.collections.new('GJH Face Source')
    scene.collection.children.link(source_collection)
source_collection.objects.link(original)
for collection in list(original.users_collection):
    if collection!=source_collection:collection.objects.unlink(original)
source_collection.hide_viewport=True;source_collection.hide_render=True
original.hide_render=True;original['face_source_only']=True
result={'base':head.name,'features':[(o.name,len(o.data.polygons)) for o in parts],'cap_faces':len(cap_faces),'warning':'The brows, eyes and mouth are surface patches; nose and ears are split fused geometry. Visual and swap QA required.'}
