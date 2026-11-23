"""Render the exact fitted placements from sockets_female.json using Cycles CPU."""
from fit_geometry import *
from verify import prop_pose
from chair_fit import BASE_CHAIR

FRAMES = {
    'hold_item': (0, 15, 30, 45), 'hold_box': (0, 12, 24, 36),
    'hold_bag': (0, 12, 24, 36), 'take_item': (0, 16, 29, 39),
    'sit_down': (0, 12, 24, 36), 'sit_idle': (0, 22, 45, 68), 'stand_up': (0, 10, 20, 30),
}
SIZE = (336, 372)
RENDERS = HERE / 'renders'

def studio(scene):
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x,scene.render.resolution_y=SIZE
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGB'
    scene.render.image_settings.compression=33
    scene.world=bpy.data.worlds.new('Studio environment')
    scene.world.use_nodes=True
    bg=scene.world.node_tree.nodes.get('Background')
    bg.inputs[0].default_value=(.78,.84,.89,1)
    bg.inputs[1].default_value=.44
    scene.view_settings.view_transform='AgX'
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.0007))
    floor=bpy.context.object
    floor.name='Backdrop'
    mat=bpy.data.materials.new('Warm gray backdrop')
    mat.use_nodes=True
    mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.21,.25,.28,1)
    mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.76
    floor.data.materials.append(mat)
    focus=Vector((0,-.10,.50))
    for pos,energy,size,color in [((-1.4,-2.1,2.5),145,1.7,(1,.89,.77)),
                                  ((1.1,-1.1,1.35),65,1.2,(.84,.93,1)),
                                  ((.40,1.10,1.9),85,1.3,(1,.95,.85))]:
        light=bpy.data.lights.new('Softbox','AREA')
        light.energy,light.size,light.color=energy,size,color
        o=bpy.data.objects.new(light.name,light)
        scene.collection.objects.link(o)
        o.location=pos
        o.rotation_euler=(focus-o.location).to_track_quat('-Z','Y').to_euler()
    cam=bpy.data.cameras.new('Orthographic')
    cam.type='ORTHO'
    cam.clip_start=.01
    cam.ortho_scale=1.20
    o=bpy.data.objects.new(cam.name,cam)
    scene.collection.objects.link(o)
    scene.camera=o
    return o

def capture(scene, cam, folder, frame, focus, label, aim):
    cam.location=focus+Vector(aim)*3
    cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler()
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/f'{frame:03d}_{label}.png'
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    return path

def contact_sheet(clip, views):
    w,h=SIZE
    margin=8
    full_w=4*w+5*margin
    full_h=2*h+3*margin
    sheet=np.ones((full_h,full_w,4),dtype=np.float32)
    sheet[:,:,:3]=.105
    for i,(front,side) in enumerate(views):
        for row,path in enumerate((side,front)):
            image=bpy.data.images.load(str(path),check_existing=False)
            buffer=np.empty(w*h*4,dtype=np.float32)
            image.pixels.foreach_get(buffer)
            x=margin+i*(w+margin)
            y=margin+row*(h+margin)
            sheet[y:y+h,x:x+w]=buffer.reshape(h,w,4)
            bpy.data.images.remove(image)
    image=bpy.data.images.new(clip,width=full_w,height=full_h,alpha=False)
    image.pixels.foreach_set(sheet.ravel())
    image.filepath_raw=str(RENDERS/(clip+'.png'))
    image.file_format='PNG'
    image.save()
    bpy.data.images.remove(image)

def render(stage, config):
    for o in stage.scene.objects:
        if o!=stage.body and o.type=='MESH':
            o.hide_render=True
    scene=stage.scene
    camera=studio(scene)
    views=(('front',(0,-1,0)),('side',(-1,0,0)))
    selected=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    filtered=set(selected)&set(FRAMES)
    for clip,frames in FRAMES.items():
        if filtered and clip not in filtered:
            continue
        is_prop=clip in PROPS
        if is_prop:
            asset,node,_,fps,_=PROPS[clip]
            objects=stage.asset(asset)
            moving=objects[node]
            cfg=config['sockets']['jar' if clip=='take_item' else clip]
            if 'shelf' in cfg:
                rail=cfg['shelf']
                objects[rail['node']].matrix_world=B@trs(rail['world_gltf'])@G
        else:
            objects=stage.asset(ASTRA/'chair.glb')
            moving=objects['Chair']
            moving.matrix_world=B@trs(config['chair']['world_gltf'])@G
            fps=30
        plate=[]
        for f in frames:
            p=stage.frame(clip,f/fps)
            if is_prop:
                moving.matrix_world=prop_pose(stage,clip,cfg,f/fps)
            focus=Vector((-.06 if clip!='hold_box' and is_prop else 0,-.102,max(.48,float(p[:,2].max())*.5)))
            plate.append(tuple(capture(scene,camera,RENDERS/clip,f,focus,label,aim) for label,aim in views))
        contact_sheet(clip,plate)
        if not is_prop:
            moving.matrix_world=B@trs(BASE_CHAIR)@G
            f=frames[-1] if clip=='sit_down' else frames[0]
            p=stage.frame(clip,f/fps)
            capture(scene,camera,RENDERS/'chair_at_origin'/clip,f,
                    Vector((0,-.102,max(.48,float(p[:,2].max())*.5))), 'side', views[1][1])
        for o in objects.values():
            bpy.data.objects.remove(o,do_unlink=True)
