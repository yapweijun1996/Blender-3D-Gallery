"""Original metric glass railing kit. Blender 4.0.2; no downloaded content.
Rebuild: blender -b --python generate.py
Preserve manual edits: blender -b --python generate.py -- --export-source
"""
from pathlib import Path
import bpy, math, sys
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SPECS=[('post','ASSET_MallGlassPost',None),('1m','ASSET_MallGlass1m',1),('2m','ASSET_MallGlass2m',2)]

def material(name, rgb, roughness=.4, metallic=0, alpha=1):
    m=bpy.data.materials.new(name); m.use_nodes=True
    def linear(v):
        v=v/255
        return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    rgba=(*[linear(v) for v in rgb],alpha)
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=rgba
    bs.inputs['Alpha'].default_value=alpha
    bs.inputs['Metallic'].default_value=metallic
    bs.inputs['Roughness'].default_value=roughness
    m.diffuse_color=rgba
    if alpha<1:
        m.blend_method='BLEND'; m.use_screen_refraction=False
        m.use_backface_culling=False
        m.show_transparent_back=False
    return m

def box(name,loc,dims,mat,bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object; o.name=name; o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat)
    if bevel:
        b=o.modifiers.new('Manufactured edge radius','BEVEL'); b.width=bevel; b.segments=3
        n=o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    return o

def group_since(before,module,origin):
    for o in set(bpy.context.scene.objects)-before:
        o['module']=module; o['module_origin']=origin

def palette():
    return dict(metal=material('Satin graphite aluminium',(66,83,85),.32,.65),
      brass=material('Warm champagne end caps',(183,161,112),.3,.65),
      dark=material('Recessed gasket',(28,43,43),.7),
      glass=material('GLASS sea-green transparent alpha 0.28',(124,191,181),.16,0,.28),
      edge=material('Glass polished edge tint',(78,143,132),.24,0,.7))

def post(x,p,name):
    before=set(bpy.context.scene.objects)
    box('Base rubber isolator',(x,0,.003),(.152,.152,.006),p['dark'],.002)
    box('Square fixing plate',(x,0,.017),(.16,.16,.028),p['metal'],.008)
    box('Post upright',(x,0,.564),(.052,.052,1.07),p['metal'],.004)
    box('Champagne post cap',(x,0,1.109),(.052,.052,.022),p['brass'],.003)
    for dx in (-.052,.052):
        for dy in (-.052,.052):
            bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.006,depth=.002,location=(x+dx,dy,.032))
            o=bpy.context.object; o.name='Flush fixing head'; o.data.materials.append(p['brass'])
    # Four-direction flush receiver details support perpendicular infills.
    for a in range(4):
        for z in (.22,.94):
            o=box('Flush receiver gasket',(x+.026*math.cos(a*math.pi/2),.026*math.sin(a*math.pi/2),z),
                  (.001,.025,.04),p['dark'],0)
            o.rotation_euler.z=a*math.pi/2
    group_since(before,name,[x,0,0])

def infill(length,p):
    before=set(bpy.context.scene.objects)
    # Connector faces at +/- (centre spacing/2 - .026), touching only post side faces.
    span=length-.052
    box('Continuous top handrail',(0,0,1.095),(span,.044,.05),p['metal'],.003)
    box('Top handrail champagne inlay',(0,0,1.1205),(span,.022,.001),p['brass'],0)
    box('Lower glass shoe',(0,0,.127),(span,.028,.024),p['metal'],.002)
    width=length-.084
    box('GLASS editable panel',(0,0,.605),(width,.012,.92),p['glass'],0)
    # Thin visible edge surfaces, not opaque replacement panels.
    for sx in (-1,1):
        box('Polished glass vertical edge',(sx*(width/2-.00075),0,.605),(.0015,.013,.92),p['edge'],0)
    box('Polished glass lower edge',(0,0,.14575),(width,.013,.0015),p['edge'],0)
    for sx in (-1,1):
        for z in (.22,.94):
            box('Glass clamp',(sx*(length/2-.037),0,z),(.022,.026,.038),p['brass'],.002)
    group_since(before,'MODULE_Infill',[0,0,0])

def point_at(o,target):
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()

def export(root,path):
    scene=bpy.context.scene
    authored=list(root.children); duplicates=[]
    for module in sorted({o['module'] for o in authored}):
        bpy.ops.object.select_all(action='DESELECT'); copies=[]
        for o in authored:
            if o['module']!=module: continue
            copy=o.copy(); copy.data=o.data.copy(); scene.collection.objects.link(copy)
            copy.select_set(True); copies.append(copy)
        bpy.context.view_layer.objects.active=copies[0]
        bpy.ops.object.convert(target='MESH'); bpy.ops.object.join(); merged=bpy.context.object
        merged.name=module
        scene.cursor.location=next(o['module_origin'] for o in authored if o['module']==module)
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        merged['module']=module; duplicates.append(merged)
    bpy.ops.object.select_all(action='DESELECT')
    for o in duplicates: o.select_set(True)
    root.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_apply=True,
      export_yup=True,export_animations=False,export_texcoords=False,export_extras=True,export_cameras=False,export_lights=False)
    for o in duplicates: bpy.data.objects.remove(o,do_unlink=True)

def studio(length):
    scene=bpy.context.scene
    ground=material('Studio backdrop only',(225,222,211),.95)
    box('Studio floor NOT EXPORTED',(0,0,-.055),(200,200,.1),ground,0)
    target=(0,0,.55)
    for name,loc,energy,size in [('Key',(3,4,6),650,5),('Fill',(-4,1,3),450,4),('Rim',(1,-4,5),750,3)]:
        bpy.ops.object.light_add(type='AREA',location=loc); o=bpy.context.object
        o.name=name; o.data.energy=energy; o.data.shape='DISK'; o.data.size=size; point_at(o,target)
    bpy.ops.object.camera_add(location=(2.5,5,2.4)); scene.camera=bpy.context.object
    scene.camera.data.type='ORTHO'; scene.camera.data.ortho_scale=1.55 if length is None else length+1
    point_at(scene.camera,target)
    world=bpy.data.worlds.new('Studio environment'); world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.32,.36,.35,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5; scene.world=world
    scene.render.engine='CYCLES'; scene.cycles.samples=32; scene.cycles.use_denoising=False
    scene.render.resolution_x=scene.render.resolution_y=768; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'; scene.view_settings.view_transform='AgX'

def main():
    for folder in ('sources','exports','previews','reports'): (HERE/folder).mkdir(exist_ok=True)
    preserve='--export-source' in sys.argv
    for suffix,root_name,length in SPECS:
        slug='mall-glass-railing-'+suffix
        if preserve:
            bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(slug+'.blend')))
            root=bpy.data.objects[root_name]
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.context.scene.unit_settings.system='METRIC'; bpy.context.scene.unit_settings.scale_length=1
            p=palette()
            if length is None: post(0,p,'MODULE_Post')
            else:
                post(-length/2,p,'MODULE_Post_Left'); post(length/2,p,'MODULE_Post_Right'); infill(length,p)
            objects=list(bpy.context.scene.objects)
            root=bpy.data.objects.new(root_name,None); bpy.context.scene.collection.objects.link(root)
            for o in objects: o.parent=root
            root['units']='metres'; root['origin']='floor centre'; root['centre_spacing_m']=length or 0
            root['purpose']='Decorative static concept; not a safety or building-code specification'
            studio(length)
        export(root,HERE/'exports'/(slug+'.glb'))
        bpy.context.scene.render.filepath=str(HERE/'previews'/(slug+'.png'))
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(slug+'.blend')),compress=True)
        bpy.ops.render.render(write_still=True)

if __name__=='__main__': main()
