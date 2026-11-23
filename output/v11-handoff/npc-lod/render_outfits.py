"""Six views of the three requested outfits, full detail at left and NPC at right."""
import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WARDROBE = ROOT / 'models/chibi-dressup'
OUTFITS = (
    ('Spiky / T-shirt + jeans', ('hair-spiky', 'top-tshirt', 'bottom-jeans', 'shoes-sneakers')),
    ('Bob / Dress', ('hair-bob', 'top-dress', 'shoes-sneakers')),
    ('Bob / T-shirt + jeans', ('hair-bob', 'top-tshirt', 'bottom-jeans', 'shoes-sneakers')),
)
VIEWS = (('front', 0, 4), ('front-three-quarter', 42, 7), ('right', 90, 4),
         ('rear-three-quarter', 139, 7), ('rear', 180, 4), ('left', -90, 4))


def import_glb(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return set(bpy.context.scene.objects) - before


def load_geometry(path, cache):
    if path not in cache:
        objects = import_glb(path)
        obj, = [o for o in objects if o.type == 'MESH' and o.vertex_groups]
        # Render the exported rest pose, with geometric normals and authored
        # corner attributes intact. All modules share the body rest coordinates.
        transform = obj.matrix_world.copy()
        mesh = obj.data.copy()
        mesh.transform(transform)
        for o in sorted(objects, key=lambda x: x.name):
            bpy.data.objects.remove(o, do_unlink=True)
        cache[path] = mesh
    return cache[path]


def text(scene, content, x, z, size, ink):
    data = bpy.data.curves.new(content, 'FONT')
    data.body = content
    data.align_x = 'CENTER'
    data.align_y = 'CENTER'
    data.size = size
    obj = bpy.data.objects.new(content, data)
    scene.collection.objects.link(obj)
    obj.location = (x, -.66, z)
    obj.rotation_euler.x = math.pi/2
    data.materials.append(ink)


def studio(scene):
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 14
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 2160
    scene.render.resolution_y = 840
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX'
    scene.world = bpy.data.worlds.new('Studio')
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (.68,.75,.88,1)
    bg.inputs['Strength'].default_value = .46
    for name, direction, energy, color in (
        ('Large key', (-.95,-1.6,2.8), 2.1, (1,.94,.89)),
        ('Fill', (1.4,-.8,1.8), .84, (.83,.91,1)),
        ('Rim', (.25,1.45,2.2), 1.35, (1,.94,.91)),
    ):
        data = bpy.data.lights.new(name, 'SUN')
        data.energy, data.angle, data.color = energy, math.radians(35), color
        lamp = bpy.data.objects.new(name, data)
        scene.collection.objects.link(lamp)
        lamp.rotation_euler = (-Vector(direction)).to_track_quat('-Z','Y').to_euler()
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-.065))
    floor = bpy.data.materials.new('Warm studio floor')
    floor.diffuse_color = (.54,.57,.62,1)
    bpy.context.object.data.materials.append(floor)
    d = bpy.data.cameras.new('Matched orthographic views')
    d.type = 'ORTHO'
    d.ortho_scale = 5.16
    cam = bpy.data.objects.new(d.name, d)
    scene.collection.objects.link(cam)
    scene.camera = cam
    ink = bpy.data.materials.new('Labels')
    ink.use_nodes = True
    em = ink.node_tree.nodes.new('ShaderNodeEmission')
    em.inputs[0].default_value = (.028,.037,.055,1)
    ink.node_tree.links.new(em.outputs[0],ink.node_tree.nodes['Material Output'].inputs[0])
    floor_obj, = [o for o in scene.objects if o.type == "MESH"]
    return cam, ink, floor_obj


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    camera, ink, floor = studio(scene)
    cache, dolls = {}, []
    for i, (label, names) in enumerate(OUTFITS):
        center = (i-1)*1.68
        text(scene, label, center, 1.47, .078, ink)
        for is_npc in (False, True):
            x = center + (.395 if is_npc else -.395)
            text(scene, 'NPC' if is_npc else 'Full detail', x, 1.348, .054, ink)
            paths = [WARDROBE/'base_body.glb']
            paths += [HERE/f'npc-{name}.glb' if is_npc else WARDROBE/'modules'/f'{name}.glb'
                      for name in names]
            meshes = []
            for path in paths:
                obj = bpy.data.objects.new(path.stem, load_geometry(path, cache))
                scene.collection.objects.link(obj)
                meshes.append(obj)
            dolls.append((x, meshes))
    floor.location.z = min(v.co.z for obj in cache.values() for v in obj.vertices) - .001
    dest = HERE/'renders'
    dest.mkdir(exist_ok=True)
    target = Vector((0, 0, .70))
    photos = []
    for number, (name, yaw, pitch) in enumerate(VIEWS, 1):
        rad = math.radians(pitch)
        camera.location = target + Vector((0, -math.cos(rad), math.sin(rad)))*6
        camera.rotation_euler = (target-camera.location).to_track_quat('-Z','Y').to_euler()
        for x, meshes in dolls:
            matrix = Matrix.Translation((x,0,0)) @ Matrix.Rotation(math.radians(yaw),4,'Z')
            for obj in meshes:
                obj.matrix_world = matrix
        photo = dest/f'{number:02}-{name}.png'
        scene.render.filepath = str(photo)
        bpy.ops.render.render(write_still=True)
        photos.append(dict(file=photo.name, yaw_degrees=yaw, pitch_degrees=pitch,
                           sha256=hashlib.sha256(photo.read_bytes()).hexdigest()))
        print('RENDERED', name, flush=True)
    inputs = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in cache}
    (dest/'render-receipt.json').write_text(json.dumps(
        dict(blender=bpy.app.version_string, renderer='Cycles CPU', pose='rest',
             inputs=inputs, views=photos), indent=2)+'\n')


if __name__ == '__main__':
    main()
