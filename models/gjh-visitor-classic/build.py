"""Build the Classic visitor in a clean Blender background process."""
import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from geometry import Geometry
from build_hair import build_hair
from build_outfit import build_outfit
from build_body import build_body
from optimize_export import optimize_export
from build_rig import build_rig, build_actions

OPTIONAL={'Hat','Jeans'}
HIDE_FOR_JEANS=['Shorts','Leg.L','Leg.R','Sock.L','Sock.R']
GLB='GJH-Classic-Visitor.glb'


def look(obj, at):
    obj.rotation_euler=(Vector(at)-obj.location).to_track_quat('-Z','Y').to_euler()


def camera_view(scene, angle):
    target=Vector((0.,0.,.643))
    a=math.radians(angle)
    scene.camera.location=target+Vector((3.5*math.sin(a),-3.5*math.cos(a),.17))
    look(scene.camera,target)


def studio(scene):
    col=bpy.data.collections.new('Studio')
    scene.collection.children.link(col)
    def put(name,data,location):
        obj=bpy.data.objects.new(name,data)
        col.objects.link(obj)
        obj.location=location
        return obj
    cam=put('Portrait Camera',bpy.data.cameras.new('Portrait'),(0,0,0))
    cam.data.type='ORTHO'; cam.data.ortho_scale=1.51
    cam.data.lens=55
    scene.camera=cam
    camera_view(scene,14)
    for name,loc,power,size,color in [
        ('Softbox • key',(-2.0,-3.0,3.9),230,3.2,(1,.87,.79)),
        ('Softbox • fill',(2.7,-1.8,2.2),180,3.0,(.83,.88,1)),
        ('Softbox • edge',(1.2,1.8,3.1),220,2.4,(1,.85,.78))]:
        light=bpy.data.lights.new(name,'AREA')
        light.energy=power; light.shape='DISK'; light.size=size; light.color=color
        look(put(name,light,loc),(0,0,.65))
    world=bpy.data.worlds.new('Soft pearl studio')
    scene.world=world; world.use_nodes=True
    world.node_tree.nodes.get('Background').inputs[0].default_value=(.8,.77,.85,1)
    world.node_tree.nodes.get('Background').inputs[1].default_value=.42
    plane=bpy.data.meshes.new('Floor')
    plane.from_pydata([(-100,-100,-.001),(100,-100,-.001),(100,100,-.001),(-100,100,-.001)],[],[(0,1,2,3)])
    floor=put('Pearl sweep',plane,(0,0,0))
    material=bpy.data.materials.new('Studio • pearl')
    material.diffuse_color=(.69,.65,.74,1); material.use_nodes=True
    material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.69,.65,.75,1)
    floor_shader=material.node_tree.nodes.get('Principled BSDF')
    floor_shader.inputs['Emission Color'].default_value=(.79,.72,.87,1)
    floor_shader.inputs['Emission Strength'].default_value=.53
    floor.data.materials.append(material)
    scene.render.engine='CYCLES'; scene.cycles.samples=16
    scene.cycles.use_denoising=True
    scene.render.resolution_x=720; scene.render.resolution_y=800
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='Khronos PBR Neutral'
    scene.view_settings.look='None'
    scene.view_settings.exposure=-.38
    scene.render.film_transparent=False


def source():
    if not bpy.app.background:
        raise RuntimeError('Build in a clean background Blender instance.')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.name='GJH • Classic Visitor'
    scene.unit_settings.system='METRIC'
    img=bpy.data.images.load(str(HERE/'face.png'),check_existing=True); img.name='Visitor • face atlas'; img.pack()
    api=Geometry(scene,img)
    rig=build_rig()
    build_body(api); build_hair(api); build_outfit(api)
    for slot,col in api.parts.items():
        for ob in col.objects:
            for g in ob.vertex_groups:
                if g.name not in rig.data.bones:
                    raise ValueError((ob.name,g.name))
            mod=ob.modifiers.new('Visitor skeleton','ARMATURE'); mod.object=rig
            ob.parent=rig
        if slot in OPTIONAL:
            col.hide_render=True; col.hide_viewport=True
    build_actions(rig)
    studio(scene)
    rig.show_in_front=False
    rig.data.display_type='STICK'
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active=None
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active
                space.region_3d.view_perspective='CAMERA'
                space.overlay.show_overlays=False
                space.shading.type='MATERIAL'
    return api,scene,rig


def export_selected(path,selection,actions):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in selection:
        ob.select_set(True)
    bpy.context.view_layer.objects.active=selection[0]
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
        export_animations=actions,export_animation_mode='NLA_TRACKS',export_force_sampling=True,
        export_anim_slide_to_zero=True,export_extras=True,export_vertex_color='MATERIAL',
        export_yup=True,export_cameras=False,export_lights=False,export_all_influences=False)


def run():
    api,scene,rig=source()
    out=HERE/'exports'; modules=out/'modules'
    modules.mkdir(parents=True,exist_ok=True)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'GJH-Classic-Visitor.blend'),compress=True)
    # Keep named locks and garment components in the saved source. Join by slot
    # in the export working copy so every slot remains individually swappable.
    optimize_export(api)
    combined={}
    for slot,col in sorted(api.parts.items()):
        col.hide_viewport=False; col.hide_render=False
        bpy.context.view_layer.update()
        items=list(col.objects)
        bpy.ops.object.select_all(action='DESELECT')
        for item in items:
            item.select_set(True)
        ob=items[0]
        bpy.context.view_layer.objects.active=ob
        if len(items)>1:
            bpy.ops.object.join()
        world=ob.matrix_world.copy()
        ob.parent=None
        ob.matrix_world=world
        ob.name='Visitor | '+slot; ob['partSlot']=slot
        combined[slot]=ob
    export_selected(out/GLB,[rig]+[ob for s,ob in combined.items() if s not in OPTIONAL],True)
    entries=[]
    for slot,ob in combined.items():
        ob.data.calc_loop_triangles()
        entry={'slot':slot,'file':'modules/'+slot+'.glb','triangles':len(ob.data.loop_triangles),
               'bones':sorted(g.name for g in ob.vertex_groups),'optional':slot in OPTIONAL}
        if os.environ.get('CLASSIC_QUICK') != '1':
            export_selected(modules/(slot+'.glb'),[rig,ob],False)
        entries.append(entry)
    (out/'manifest.json').write_text(json.dumps({'character':GLB,'units':'m','slots':entries,
        'variants':{'Jeans':{'hide':HIDE_FOR_JEANS},'Hat':{'hide':[]}}},indent=2)+'\n')


if __name__=='__main__':
    run()
