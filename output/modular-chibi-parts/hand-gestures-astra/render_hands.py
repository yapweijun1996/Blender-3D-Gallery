"""Three hand-relative studio cameras. Temporary QA rig is never saved."""
import bpy
from mathutils import Vector, Matrix
from hand_common import OUT, prefix


class Studio:
    def __init__(self, body):
        scene = bpy.context.scene
        self.scene = scene
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = 12
        scene.cycles.use_denoising = True
        scene.render.resolution_x = 480
        scene.render.resolution_y = 420
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.use_compositing = False
        scene.render.use_sequencer = False
        scene.render.film_transparent = False
        scene.view_settings.view_transform = 'AgX'
        world = bpy.data.worlds.new('Study studio')
        scene.world = world
        world.use_nodes = True
        bg = world.node_tree.nodes['Background']
        bg.inputs[0].default_value = (.14, .195, .255, 1)
        bg.inputs[1].default_value = .54
        clay = bpy.data.materials.new('Study • unglazed terracotta')
        clay.use_nodes = True
        shader = clay.node_tree.nodes['Principled BSDF']
        shader.inputs['Base Color'].default_value = (.57, .294, .165, 1)
        shader.inputs['Roughness'].default_value = .62
        body.data.materials.clear()
        body.data.materials.append(clay)
        cd = bpy.data.cameras.new('Orthographic hand detail')
        cd.type = 'ORTHO'
        cd.clip_start = .01
        cam = bpy.data.objects.new(cd.name, cd)
        scene.collection.objects.link(cam)
        scene.camera = cam
        self.camera = cam
        self.lights = []
        for power, size, col in [(2.4, .20, (1, .87, .72)), (.95, .24, (.75, .87, 1)), (2.2, .17, (1, .91, .80))]:
            ld = bpy.data.lights.new('Softbox', 'AREA')
            ld.energy = power
            ld.size = size
            ld.shape = 'DISK'
            ld.color = col
            light = bpy.data.objects.new(ld.name, ld)
            scene.collection.objects.link(light)
            self.lights.append(light)

    def render(self, name, side, sg, body, rig, points):
        h = rig.pose.bones[prefix(side)]
        rot = (h.matrix@h.bone.matrix_local.inverted()).to_quaternion()
        # Frame the silhouette from just proximal to the wrist through the
        # furthest visible finger, with the camera attached to the posed hand.
        ids = [v.index for v in body.data.vertices if sg*v.co.x > .257]
        directions = {'palm': (.20*sg, -.09, -1), 'back': (.20*sg, .09, 1),
                      'thumb-side': (.24*sg, -1, -.33)}
        upright = 'thumbs_up' in name
        if upright:
            # Oblique palmar/dorsal views retain each surface and show the
            # thumb's height. A camera directly on Z foreshortens that thumb.
            directions.update(palm=(.32*sg, -.93, -.78), back=(.12*sg, .90, .79))
        if 'grip_small' in name:
            directions['thumb-side'] = (.45*sg, -1, 0)
        for view, local in directions.items():
            direction = (rot @ Vector(local)).normalized()
            up = Vector((0, 0, 1)) if upright else rot @ Vector((sg, 0, 0))
            up = (up-direction*direction.dot(up)).normalized()
            right = up.cross(direction).normalized()
            basis = Matrix((right, up, direction)).transposed()
            center = Vector()
            widths = []
            for axis in (right, up, direction):
                dist = [points[i].dot(axis) for i in ids]
                center += axis*((min(dist)+max(dist))*.5)
                widths.append(max(dist)-min(dist))
            cam = self.camera
            cam.rotation_euler = basis.to_euler()
            cam.location = center+direction*.55
            cam.data.ortho_scale = max(widths[0], widths[1]*480/420)*1.18
            cam.data.clip_end = .55+widths[2]/2+.005
            for light, (u, v, w) in zip(self.lights, [(-.14, .18, .20), (.20, -.02, .23), (.12, .13, -.16)]):
                light.location = center+u*right+v*up+w*direction
                light.rotation_euler = (center-light.location).to_track_quat('-Z', 'Y').to_euler()
            self.scene.render.filepath = str(OUT/'renders'/(name+'_'+view+'.png'))
            bpy.ops.render.render(write_still=True)
