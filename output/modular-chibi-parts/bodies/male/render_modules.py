"""Render six on-body views per exported module and a full-outfit contact sheet."""
import hashlib
import json
import math
from pathlib import Path
import sys

from asset_io import HERE, MOTION, bpy, np, write_json
from body_audit import load_body_motion, set_frame, use_action
from fit_module import read_module
from modules import MODULES
from mathutils import Matrix, Vector

VIEWS = (('front',0),('left-three-quarter',35),('left',90),
         ('back',180),('right',-90),('right-three-quarter',-35))
RENDERS = HERE/'renders'
CELL_W,CELL_H = 360,420


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_font(scene, material, content, x, z, size):
    data = bpy.data.curves.new(content,'FONT')
    data.body = content
    data.align_x = 'CENTER'
    data.align_y = 'CENTER'
    data.size = size
    obj = bpy.data.objects.new(content,data)
    scene.collection.objects.link(obj)
    obj.location = (x,-.60,z)
    obj.rotation_euler.x = math.pi/2
    data.materials.append(material)
    return obj


def studio(scene):
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 10
    scene.cycles.use_denoising = True
    scene.render.resolution_x = CELL_W*3
    scene.render.resolution_y = CELL_H*2
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX'
    world = bpy.data.worlds.new('Slate studio')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.15,.19,.25,1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .7
    scene.world = world
    scene.render.film_transparent = False
    for point,energy,color in [((-.7,-1.4,2),3.0,(1,.93,.86)),
                               ((1.5,-.7,.8),1.45,(.8,.9,1)),
                               ((.8,1,1.9),2.1,(.87,.94,1))]:
        data = bpy.data.lights.new('Studio sun','SUN')
        data.energy,data.color,data.angle = energy,color,math.radians(18)
        lamp = bpy.data.objects.new(data.name,data)
        scene.collection.objects.link(lamp)
        lamp.rotation_euler = (-Vector(point)).to_track_quat('-Z','Y').to_euler()
    cam = bpy.data.cameras.new('Contact camera')
    cam.type = 'ORTHO'
    cam.ortho_scale = 3.72
    obj = bpy.data.objects.new(cam.name,cam)
    scene.collection.objects.link(obj)
    obj.location = (0,-8,0)
    obj.rotation_euler.x = math.pi/2
    scene.camera = obj
    ink = bpy.data.materials.new('Label ink')
    ink.use_nodes = True
    nodes = ink.node_tree.nodes
    emit = nodes.new('ShaderNodeEmission')
    emit.inputs['Color'].default_value = (.77,.86,1,1)
    emit.inputs['Strength'].default_value = .8
    ink.node_tree.links.new(emit.outputs[0],nodes['Material Output'].inputs['Surface'])
    return ink


def baked(obj,depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    return bpy.data.meshes.new_from_object(evaluated,depsgraph=depsgraph),evaluated.matrix_world.copy()


def contact_sheet(scene,ink,tiles,filename):
    created = []
    for idx,(title,angle,items) in enumerate(tiles):
        col,row = idx%3,idx//3
        x,z = (col-1)*1.24, (.723 if row==0 else -.723)
        orient = Matrix.Translation((x,0,z-.465)) @ Matrix.Rotation(math.radians(angle),4,'Z')
        for mesh,matrix in items:
            instance = bpy.data.objects.new(mesh.name,mesh)
            scene.collection.objects.link(instance)
            instance.matrix_world = orient @ matrix
            created.append(instance)
        created.append(create_font(scene,ink,title,x,z-.59,.060))
    scene.render.filepath = str(filename)
    bpy.ops.render.render(write_still=True)
    for instance in created:
        bpy.data.objects.remove(instance,do_unlink=True)


def crop_views(sheet,names,directory):
    directory.mkdir(parents=True,exist_ok=True)
    original = bpy.data.images.load(str(sheet),check_existing=False)
    original.colorspace_settings.name = 'Non-Color'
    buffer = np.empty(CELL_W*CELL_H*6*4,dtype=np.float32)
    original.pixels.foreach_get(buffer)
    buffer = buffer.reshape(CELL_H*2,CELL_W*3,4)
    files = []
    for i,name in enumerate(names):
        x,y = (i%3)*CELL_W,(1-i//3)*CELL_H
        image = bpy.data.images.new(name,width=CELL_W,height=CELL_H,alpha=False,float_buffer=False)
        image.colorspace_settings.name = 'Non-Color'
        image.pixels.foreach_set(np.ascontiguousarray(buffer[y:y+CELL_H,x:x+CELL_W]).ravel())
        image.file_format = 'PNG'
        path = directory/f'{name}.png'
        image.save(filepath=str(path))
        bpy.data.images.remove(image)
        files.append(str(path.relative_to(HERE)))
    bpy.data.images.remove(original)
    return files


def render(names):
    RENDERS.mkdir(exist_ok=True)
    scene,arm,body,actions = load_body_motion(MOTION)
    modules = {key:read_module(HERE/f'male-{key}.glb',arm) for key in names}
    use_action(arm,actions['idle'])
    set_frame(scene,24)
    dg = bpy.context.evaluated_depsgraph_get()
    poses = {key:baked(obj,dg) for key,obj in [('body',body),*modules.items()]}
    for obj in [body,*modules.values()]:
        obj.hide_render = True
    ink = studio(scene)
    manifest = {'renderer':'Cycles CPU','resolution':[CELL_W,CELL_H],'clip':'idle','blender_frame':24,
                'motion_sha256':hash_file(MOTION),'body_sha256':hash_file(HERE/'body_male.glb'),
                'modules':{}}
    record = RENDERS/'manifest.json'
    if record.exists():
        previous = json.loads(record.read_text())
        if all(previous.get(k)==manifest[k] for k in ('renderer','motion_sha256','body_sha256','clip','blender_frame')):
            manifest['modules'].update(previous.get('modules',{}))
    for key in names:
        source_hash = hash_file(HERE/f'male-{key}.glb')
        saved = manifest['modules'].get(key,{})
        if saved.get('sha256')==source_hash and all((HERE/path).is_file() for path in [saved['sheet'],*saved['views']]):
            continue
        folder = RENDERS/key
        folder.mkdir(exist_ok=True)
        sheet = folder/'six-views.png'
        contact_sheet(scene,ink,[(name.replace('-',' ').title(),angle,[poses['body'],poses[key]])
                                 for name,angle in VIEWS],sheet)
        files = crop_views(sheet,[name for name,_ in VIEWS],folder)
        manifest['modules'][key] = {'sha256':source_hash,'views':files,
                                    'sheet':str(sheet.relative_to(HERE))}
        write_json(RENDERS/'manifest.json',manifest)
    if set(names)==set(MODULES):
        outfits = [
            ('Spiky / T-shirt + jeans',('hair-spiky','tshirt','jeans','sneakers')),
            ('Bob / T-shirt + jeans',('hair-bob','tshirt','jeans','sneakers')),
            ('Side part / dress',('hair-sidepart','dress','sneakers')),
        ]
        sheet = RENDERS/'outfits.png'
        contact_sheet(scene,ink,[(title,angle,[poses['body'],*(poses[k] for k in parts)])
                                 for angle in (20,155) for title,parts in outfits],sheet)
        manifest['outfits'] = {'file':str(sheet.relative_to(HERE)),'sha256':hash_file(sheet)}
        write_json(RENDERS/'manifest.json',manifest)


if __name__=='__main__':
    args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    render(args or list(MODULES))
