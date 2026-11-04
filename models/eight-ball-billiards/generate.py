"""Create an original, unbranded 8-ball asset pack. Blender 5.1.2; meters.
Run: blender --background --factory-startup --python models/eight-ball-billiards/generate.py
"""
import bpy
import bmesh
import math
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'exports'
OUT.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world.color = (0.18, 0.18, 0.18)


def material(name, color, roughness=.4, metallic=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Metallic'].default_value = metallic
    return m

wood = material('Walnut | satin', (.13, .045, .018), .3)
wood_edge = material('Rail wood | warm walnut', (.21, .075, .025), .28)
cloth = material('Wool cloth | tournament green', (.025, .19, .105), .88)
rubber = material('Cushion rubber | green', (.018, .12, .065), .76)
black = material('Pocket leather | charcoal', (.014, .012, .012), .53)
white = material('Ivory resin', (.92, .90, .82), .24)
ink = material('Number ink', (.005, .006, .008), .29)
metal = material('Brushed steel', (.34, .37, .39), .3, .8)
chalkblue = material('Chalk | blue', (.035, .12, .35), .95)
chalkpaper = material('Chalk wrapper | dark blue', (.025, .045, .13), .6)
shaftmat = material('Cue shaft | maple', (.67, .47, .25), .34)
colors = [(0.92,.56,.012),(.015,.09,.55),(.61,.018,.025),(.22,.035,.37),(.88,.23,.015),(.012,.30,.105),(.31,.035,.025)]
ballmats = [material('Resin | '+str(i+1), c, .23) for i,c in enumerate(colors)]
ball8 = material('Resin | eight black', (.009,.01,.013), .22)


def root(name, loc=(0,0,0)):
    obj = bpy.data.objects.new(name, None)
    scene.collection.objects.link(obj)
    obj.location = loc
    return obj


def adopt(obj, parent):
    bpy.context.view_layer.update()
    matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = matrix
    return obj


def assign(obj, mat):
    obj.data.materials.append(mat)
    return obj


def bevel(obj, amount=.006, segments=2):
    mod = obj.modifiers.new('Small rounded edges', 'BEVEL')
    mod.width = amount
    mod.segments = segments
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


def cube(name, loc, dims, mat, parent=None, bevel_size=.003):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob=bpy.context.object; ob.name=name
    ob.dimensions=dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel_size: bevel(ob, bevel_size)
    assign(ob, mat)
    if parent: adopt(ob,parent)
    return ob


def cylinder(name, loc, radius, depth, mat, parent=None, vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    ob=bpy.context.object; ob.name=name
    assign(ob,mat)
    if parent: adopt(ob,parent)
    return ob


def rod(name, start, end, radius1, radius2, mat, parent, vertices=20):
    a,b=Vector(start),Vector(end)
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius1, radius2=radius2, depth=(b-a).length, location=(a+b)/2)
    ob=bpy.context.object; ob.name=name
    ob.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    assign(ob,mat); adopt(ob,parent)
    for poly in ob.data.polygons: poly.use_smooth=True
    return ob


def export_uv(ob):
    if ob.type != 'MESH' or ob.data.uv_layers: return
    uv=ob.data.uv_layers.new(name='UVMap')
    for poly in ob.data.polygons:
        for li in poly.loop_indices:
            v=ob.data.vertices[ob.data.loops[li].vertex_index].co
            uv.data[li].uv=(v.x, v.y)

# Table dimensions: 2.54 x 1.40 m outside, 2.24 x 1.12 m playing surface.
table=root('ASSET_Table')
base=cube('Table | solid walnut cabinet',(0,0,.67),(2.54,1.40,.16),wood,table,.015)
felt=cube('Table | slate and green cloth',(0,0,.766),(2.30,1.18,.025),cloth,table,.002)
pockets=[(x,y) for x in (-1.12,0,1.12) for y in (-.56,.56)]
# Cut actual openings through the slate and cabinet. Keep cutters temporary.
for i,(x,y) in enumerate(pockets):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=.055 if x else .052, depth=.5, location=(x,y,.72))
    cutter=bpy.context.object; cutter.name='temporary cutter'
    for target in (base,felt):
        bpy.context.view_layer.objects.active=target
        mod=target.modifiers.new('Pocket cut','BOOLEAN'); mod.operation='DIFFERENCE'; mod.solver='EXACT'; mod.object=cutter
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
    cylinder('Pocket %d | recessed liner'%(i+1),(x,y,.689),.049,.115,black,table)
# Side rails have a break at each middle pocket.
for y in (-.636,.636):
    for x in (-.60,.60):
        cube('Long rail',(x,y,.811),(1.05,.125,.085),wood_edge,table,.009)
        cube('Cushion',(x,y*.86,.796),(1.03,.052,.052),rubber,table,.006)
for x in (-1.215,1.215):
    cube('End rail',(x,0,.811),(.11,1.02,.085),wood_edge,table,.009)
    cube('Cushion',(x*.93,0,.796),(.05,.99,.052),rubber,table,.006)
for x in (-.97,.97):
    for y in (-.48,.48):
        cube('Table leg',(x,y,.305),(.17,.17,.61),wood,table,.012)
        cube('Leg foot',(x,y,.025),(.19,.19,.05),black,table,.004)
# Decorative sight markers on long rails.
for y in (-.636,.636):
    for x in (-.93,-.62,-.31,.31,.62,.93):
        cylinder('Rail sight',(x,y,.856),.008,.002,white,table,16)

# 57.15 mm diameter resin balls, with a white number medallion and black numeral.
R=.028575
balls=[]
# Familiar colors, original unbranded ball design. Spread for a readable showcase.
positions=[(-.70,-.12)] + [(.20+(i%5)*.078,-.20+(i//5)*.105) for i in range(15)]
for n,(x,y) in enumerate(positions):
    z=.7785+R
    b=root('ASSET_Ball_%02d'%n,(x,y,z)); balls.append(b)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=R, location=(x,y,z))
    sphere=bpy.context.object; sphere.name='Ball %02d | resin'%n
    base_mat=white if n==0 or n>=9 else (ball8 if n==8 else ballmats[n-1])
    assign(sphere,base_mat)
    if n>=9:
        sphere.data.materials.append(ballmats[n-9])
        for p in sphere.data.polygons:
            # center stripe defined in ball local space
            if abs(p.center.z) < R*.43: p.material_index=1
    for p in sphere.data.polygons: p.use_smooth=True
    adopt(sphere,b)
    if n:
        # Raised, non-textured mesh marks remain legible in glTF and move with their ball.
        cylinder('Ball %02d | number medallion'%n,(x,y,z+R+.00030),.0113,.00055,white,b,32)
        bpy.ops.object.text_add(location=(x,y,z+R+.00065))
        t=bpy.context.object; t.name='Ball %02d | numeral %d'%(n,n)
        t.data.body=str(n); t.data.align_x='CENTER'; t.data.align_y='CENTER'; t.data.size=.015 if n<10 else .012
        t.data.extrude=.00008; t.data.resolution_u=3
        assign(t,ink)
        bpy.context.view_layer.objects.active=t
        bpy.ops.object.convert(target='MESH')
        bm = bmesh.new(); bm.from_mesh(t.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.000001)
        bm.to_mesh(t.data); bm.free(); t.data.update()
        adopt(t,b)

# Two separate tapered sticks, each 1.47 m long, positioned alongside the table.
cues=[]
for k,y in enumerate((-.94,-1.02),1):
    cue=root('ASSET_Cue_%02d'%k,(0,y,.06)); cues.append(cue)
    rod('Cue %d | butt'%k,(-.735,y,.06),(-.22,y,.06),.017,.011,wood,cue)
    rod('Cue %d | shaft'%k,(-.22,y,.06),(.70,y,.06),.011,.006,shaftmat,cue)
    rod('Cue %d | ferrule'%k,(.70,y,.06),(.728,y,.06),.006,.006,white,cue,16)
    rod('Cue %d | tip'%k,(.728,y,.06),(.735,y,.06),.006,.005,black,cue,16)
# Equilateral open wooden triangle rack, suitably sized for 57.15 mm balls.
rack=root('ASSET_Triangle_Rack',(.65,.27,.80))
vertices=[(.48,.27,.80),(.78,.435,.80),(.78,.105,.80)]
for a,b in zip(vertices,vertices[1:]+vertices[:1]): rod('Rack | wooden side',a,b,.009,.009,wood_edge,rack,12)
chalk=root('ASSET_Chalk',(-.83,.636,.88))
cube('Chalk | paper sleeve',(-.83,.636,.866),(.025,.025,.022),chalkpaper,chalk,.001)
cube('Chalk | blue top',(-.83,.636,.879),(.023,.023,.006),chalkblue,chalk,.001)
assets=[table,*balls,*cues,rack,chalk]
for ob in bpy.data.objects: export_uv(ob)

# Studio objects are kept separate from every export.
studio=root('STUDIO | not exported')
cube('Studio floor',(0,0,-.035),(200,200,.05),material('Studio floor | slate',(.055,.065,.075),.8),studio,.0)
def area(name,loc,power,size):
    bpy.ops.object.light_add(type='AREA', location=loc)
    ob=bpy.context.object; ob.name=name; ob.data.energy=power; ob.data.shape='DISK'; ob.data.size=size
    ob.rotation_euler=(Vector((0,0,.5))-ob.location).to_track_quat('-Z','Y').to_euler(); adopt(ob,studio)
area('Studio | key',(-2,-2,4),750,4)
area('Studio | fill',(2,1,3.5),500,3)
bpy.ops.object.camera_add(location=(3.5,-4.8,4.2))
cam=bpy.context.object; cam.name='Studio | camera'; cam.rotation_euler=(Vector((0,0,.52))-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.type='ORTHO'; cam.data.ortho_scale=4.05
adopt(cam,studio); scene.camera=cam
scene.render.image_settings.color_mode='RGBA'
scene.render.filepath=str(ROOT/'preview.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'scene.blend'))
bpy.ops.render.render(write_still=True)

# Export only asset roots and descendants, never camera, lights or studio floor.
def export(path,roots,origin=False):
    old=[o.location.copy() for o in roots]
    if origin:
        for o in roots: o.location=(0,0,0)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in bpy.data.objects:
        cur=ob
        while cur:
            if cur in roots: ob.select_set(True); break
            cur=cur.parent
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_apply=True)
    for o,loc in zip(roots,old): o.location=loc
export(OUT/'billiards-scene.glb',assets)
for ob in assets:
    export(OUT/(ob.name.replace('ASSET_','').lower()+'.glb'),[ob],True)
print('ASSET_GENERATION_COMPLETE',len(assets),'individual exports')
