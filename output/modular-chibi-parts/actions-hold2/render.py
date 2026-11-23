"""Cycles CPU orthographic views of the actual exported assets on the demo body."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from module_checks import MODULES
import render_actions as plates

FRAMES={'hold_box':(0,12,24,36),'hold_bag':(0,12,24,36),'take_item':(0,16,29,39)}
def capture():
    scene=setup();arm=armature(load(BODY))
    load(BANK)
    dress(arm,MODULES['bob']);dress(arm,MODULES['sneakers'])
    config=placement()
    lift=config['sneaker_v3_root_lift_m']
    arm.location.z+=lift
    scene.render.engine='CYCLES'
    scene.cycles.device='CPU';scene.cycles.samples=14;scene.cycles.use_denoising=True
    scene.render.resolution_x,scene.render.resolution_y=plates.SIZE=(296,316)
    scene.render.resolution_percentage=100
    scene.render.use_compositing=False
    scene.render.use_sequencer=False
    scene.world=bpy.data.worlds.new('Studio ambient');scene.world.use_nodes=True
    bg=scene.world.node_tree.nodes.get('Background')
    bg.inputs[0].default_value=(.83,.87,.86,1);bg.inputs[1].default_value=.52
    bpy.ops.mesh.primitive_plane_add(size=200)
    floor=bpy.context.object
    floor.location.z=-.0004
    mat=bpy.data.materials.new('Sage cyclorama');mat.diffuse_color=(.36,.49,.44,1)
    floor.data.materials.append(mat)
    focus=Vector((0,-.08,.50))
    for pos,power,size,color in [((-1.4,-2.2,2.7),135,1.6,(1,.89,.77)),((1.5,-.9,1.7),45,1.2,(.85,.94,1)),((.4,1.4,2.1),78,1.25,(1,.96,.84))]:
        light=bpy.data.lights.new('Softbox','AREA')
        light.energy=power;light.size=size;light.color=color
        o=bpy.data.objects.new(light.name,light);scene.collection.objects.link(o)
        o.location=pos;o.rotation_euler=(focus-o.location).to_track_quat('-Z','Y').to_euler()
    cam=bpy.data.cameras.new('Review');cam.type='ORTHO';cam.ortho_scale=1.20;cam.clip_start=.01
    co=bpy.data.objects.new(cam.name,cam);scene.collection.objects.link(co);scene.camera=co
    plates.RENDERS=HERE/'renders';plates.FPS=FPS;plates.FRAMES=FRAMES
    proof='--proof' in sys.argv
    for name,frames in FRAMES.items():
        cfg=json.loads((HERE/'props'/(FILES[name]+'.attachment.json')).read_text())
        objs=load(HERE/cfg['prop']);moving=next(o for o in objs if o.name==cfg['node'])
        if name=='take_item':
            place_shelf(next(o for o in objs if o.name==cfg['shelf_node']),config,lift)
        bind(arm,bpy.data.actions[name])
        for f in (frames[:1] if proof else frames):
            scene.frame_set(f);moving.matrix_world=equipment(name,arm,f,cfg,lift,first_pick=True)
            for label,aim in [('front',(0,-1,.063)),('side',(-1,0,.063))]:
                focus=Vector((-.035 if name!='hold_box' else 0,-.103 if name!='hold_bag' else -.02,.514))
                co.location=focus+Vector(aim).normalized()*3
                co.rotation_euler=(focus-co.location).to_track_quat('-Z','Y').to_euler()
                scene.render.filepath=str(plates.RENDERS/f'{name}_{f:03}_{label}.png')
                bpy.ops.render.render(write_still=True)
        if not proof:plates.sheet(name)
        for o in objs:bpy.data.objects.remove(o,do_unlink=True)
if __name__=='__main__':capture()
