"""Original deterministic Blender 4.0.2 public corridor drinking fixture."""
from pathlib import Path
import bpy, math, sys
from mathutils import Vector

HERE=Path(__file__).resolve().parent
SLUG='mall-water-dispenser'; ROOT='ASSET_MallWaterDispenser'; TARGET=(0,0,0.72); SCALE=1.8

def mat(name, rgb, metal=0.0, rough=.42):
    m=bpy.data.materials.new(name); m.use_nodes=True
    c=tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb)+(1,)
    p=m.node_tree.nodes['Principled BSDF']; p.inputs['Base Color'].default_value=c; p.inputs['Metallic'].default_value=metal; p.inputs['Roughness'].default_value=rough; m.diffuse_color=c
    return m
def empty(name, loc=(0,0,0), parent=None):
    o=bpy.data.objects.new(name,None); bpy.context.scene.collection.objects.link(o); o.location=loc; o.parent=parent; return o
def finish(o,name,m,parent,bevel=.003):
    o.name=name; o.data.materials.append(m); o.parent=parent
    if bevel:
        b=o.modifiers.new('Manufactured edge','BEVEL'); b.width=bevel; b.segments=2
        o.modifiers.new('Corner normals','WEIGHTED_NORMAL')
    return o
def box(name,loc,dims,m,parent,bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.dimensions=dims; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); return finish(o,name,m,parent,bevel)
def rod(name,a,b,r,m,parent,vertices=16):
    a,b=Vector(a),Vector(b); d=b-a; bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=d.length,location=(a+b)/2); o=bpy.context.object; o.rotation_euler=d.to_track_quat('Z','Y').to_euler(); return finish(o,name,m,parent,.001)
def disc(name,loc,r,depth,m,parent,vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=depth,location=loc); return finish(bpy.context.object,name,m,parent,.001)
def aim(o,p): o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
def slide(o, axis, distance):
    start=o.location[axis]
    for f,v in [(1,start),(30,start+distance),(60,start)]: o.location[axis]=v; o.keyframe_insert(data_path='location',frame=f)
    bpy.context.scene.frame_set(1)
def palette():
    return [mat('Cabinet enamel',(.72,.76,.76),.35,.28),mat('Dark recess',(.035,.05,.055),.05,.28),mat('Brushed grate',(.40,.45,.46),.8,.24),mat('Button blue',(.06,.32,.72),.15,.24),mat('Button neutral',(.72,.76,.73),.3,.25),mat('Rubber',(.045,.055,.06),.05,.5),mat('Display cyan',(.12,.70,.78),.1,.18)]
def build(root):
    steel,dark,grate,blue,neutral,rubber,cyan=palette()
    # Cabinet is a genuine open-front assembly: top, sides, lower plinth and back.
    box('CABINET_Left',(-.33,0,.78),(.04,.50,1.40),steel,root,.01)
    box('CABINET_Right',(.33,0,.78),(.04,.50,1.40),steel,root,.01)
    box('CABINET_Top',(0,0,1.46),(.66,.50,.04),steel,root,.01)
    box('CABINET_LowerFront',(0,-.23,.35),(.66,.04,.40),steel,root,.01)
    box('CABINET_RearUpper',(0,.23,1.01),(.66,.04,.90),steel,root,.01)
    box('CABINET_FrontFrame',(0,-.245,1.22),(.66,.035,.28),steel,root,.008)
    box('BAY_Recess_Back',(0,.12,.88),(.54,.025,.48),dark,root,.006)
    box('BAY_Recess_Left',(-.29,-.275,.88),(.055,.09,.52),steel,root,.006)
    box('BAY_Recess_Right',(.29,-.275,.88),(.055,.09,.52),steel,root,.006)
    box('BAY_Recess_Ceiling',(0,-.275,1.14),(.60,.09,.055),steel,root,.006)
    box('PLINTH',(0,.0,.085),(.74,.54,.17),dark,root,.02)
    box('DRIP_Tray',(0,-.30,.57),(.58,.25,.055),steel,root,.012)
    # Independent grate bars show the catch surface without claiming water simulation.
    for x in [-.20,-.10,0,.10,.20]: box('DRIP_Grate_Bar',(x,-.30,.605),(.025,.19,.018),grate,root,.004)
    for x in [-.24,.24]: box('DRIP_Grate_Rail',(x,-.30,.605),(.018,.20,.025),grate,root,.003)
    # Spout is parented as its own editable moving assembly, aligned to the bay centre.
    sp=empty('MOVABLE_Spout',(0,0,0),root)
    rod('SPOUT_Arm',(0,-.28,1.02),(0,-.39,1.02),.025,steel,sp)
    rod('SPOUT_Nozzle',(0,-.39,1.02),(0,-.39,.94),.018,rubber,sp)
    disc('SPOUT_Tip',(0,-.39,.935),.026,.018,rubber,sp)
    # Two safe, non-hot controls are discrete, independently editable meshes.
    box('CONTROL_Cold',(-.15,-.277,1.31),(.16,.035,.07),blue,root,.015)
    box('CONTROL_Ambient',(.15,-.277,1.31),(.16,.035,.07),neutral,root,.015)
    box('CONTROL_Cold_Indicator',(-.15,-.298,1.31),(.045,.006,.018),cyan,root,.002)
    # Removable-looking service panel, with a small pull slot and an authored clip.
    panel=empty('MOVABLE_ServicePanel',(0,.265,.33),root)
    box('SERVICE_Panel',(0,0,0),(.54,.035,.38),steel,panel,.012)
    box('SERVICE_PullSlot',(0,-.022,.04),(.16,.012,.025),dark,panel,.004)
    slide(panel,1,.12)
    panel.animation_data.action.name='ServicePanelOpenClose'
def studio():
    s=bpy.context.scene; s.world=bpy.data.worlds.new('Neutral corridor studio'); s.world.use_nodes=True; s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.12,.15,.17,1); s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.55
    for name,loc,power in [('Key',(-3,-4,4),900),('Fill',(3,-2,2.5),650),('Rim',(0,3,4),900)]:
        bpy.ops.object.light_add(type='AREA',location=loc); o=bpy.context.object; o.name='STUDIO_'+name; o.data.energy=power; o.data.size=4; aim(o,TARGET)
    bpy.ops.object.camera_add(); s.camera=bpy.context.object; s.camera.name='STUDIO_Camera'; s.camera.data.type='ORTHO'; s.camera.data.ortho_scale=SCALE
    s.render.engine='CYCLES'; s.cycles.samples=24; s.cycles.use_denoising=False; s.render.resolution_x=s.render.resolution_y=768; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'; s.view_settings.look='AgX - Medium High Contrast'
def render_views():
    s=bpy.context.scene
    for name,delta in [('hero',(1.15,-2.2,.75)),('front',(0,-3,.15)),('rear',(1.25,2,.7)),('side',(2.5,-.15,.55)),('open',(-1.05,-2.1,.65))]:
        s.frame_set(30 if name=='open' else 1); s.camera.location=Vector(TARGET)+Vector((1.25,2,.7) if name=='open' else delta)*SCALE; aim(s.camera,TARGET); s.render.filepath=str(HERE/'previews'/(name+'.png')); bpy.ops.render.render(write_still=True)
def export(path):
    bpy.ops.object.select_all(action='DESELECT'); root=bpy.data.objects[ROOT]; root.select_set(True)
    for o in root.children_recursive: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=True,export_texcoords=False,export_extras=True,export_cameras=False,export_lights=False)
def main():
    for d in ['sources','exports','previews','reports','metadata']: (HERE/d).mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.context.preferences.filepaths.save_version=0; s=bpy.context.scene; s.unit_settings.system='METRIC'; s.unit_settings.scale_length=1
    root=empty(ROOT); root['units']='metres'; root['front_axis']='Blender -Y / glTF +Z'; root['scope']='Original illustrative public drinking fixture; no water simulation, hot function, certification or branding'
    build(root); studio(); bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True); export(HERE/'exports/optimized.glb')
    if '--skip-render' not in sys.argv: render_views()
if __name__=='__main__': main()
