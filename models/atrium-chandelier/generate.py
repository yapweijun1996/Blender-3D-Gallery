"""Original deterministic atrium chandelier. Blender 5.2.3; no external assets.

Layout/export workflow adapted from self-checkout-machine. The editable source
retains individual parts; only the delivery copy is batched by shared material.
"""
from pathlib import Path
import math
import sys
import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'atrium-chandelier'
ROOT = 'ASSET_AtriumChandelier'
RINGS = [(1.445, 1.23, 12), (1.025, 1.02, 8), (.605, .80, 4)]


def material(name, rgb, metallic, roughness, emission=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.use_backface_culling = True
    color = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = color
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Emission Color'].default_value = color
    p.inputs['Emission Strength'].default_value = emission
    m.diffuse_color = color
    return m


def finish(o, name, mat, group):
    o.name = name
    o.data.materials.append(mat)
    o.parent = bpy.data.objects[ROOT]
    o['delivery_mesh'] = group
    return o


def mesh(name, vertices, faces, mat, group):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    o = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(o)
    return finish(o, name, mat, group)


def lathe(name, profile, mat, group, segments=96):
    """Closed revolved profile, measured in radius/height metres."""
    vertices = [(r * math.cos(2 * math.pi * i / segments),
                 r * math.sin(2 * math.pi * i / segments), z)
                for i in range(segments) for r, z in profile]
    n = len(profile)
    faces = []
    for i in range(segments):
        for j in range(n):
            faces.append((i*n+j, ((i+1) % segments)*n+j,
                          ((i+1) % segments)*n+(j+1) % n, i*n+(j+1) % n))
    o = mesh(name, vertices, faces, mat, group)
    # Smooth around each circular band while preserving profile edges.
    for polygon in o.data.polygons:
        polygon.use_smooth = True
    for edge in o.data.edges:
        if edge.vertices[0] % n == edge.vertices[1] % n:
            edge.use_edge_sharp = True
    return o


def rod(name, a, b, radius, mat, segments=12):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments, radius=radius,
                                      depth=(b-a).length, location=(a+b)/2)
    o = bpy.context.object
    o.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    finish(o, name, mat, 'FRAME_Chandelier')
    for polygon in o.data.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
    return o


def drop(name, x, y, top, length, width, rotation, mat):
    # Compact cut gemstone: short crown, offset girdle and a short pavilion tip.
    # Flat triangle normals preserve alternating reflections in the web studio.
    vertices = [(x, y, top), (x, y, top-length)]
    bands = [(.08, .27, 0), (.24, .80, 0),
             (.44, 1.0, math.pi/8), (.76, .70, math.pi/8)]
    for fraction, scale, phase in bands:
        vertices.extend((x+width*scale*math.cos(i*math.pi/4+phase+rotation),
                         y+width*scale*math.sin(i*math.pi/4+phase+rotation),
                         top-length*fraction) for i in range(8))
    faces = []
    for i in range(8):
        j = (i+1) % 8
        faces.extend([(0, 2+i, 2+j), (26+i, 1, 26+j)])
        for band in range(len(bands)-1):
            a, b = 2+band*8, 2+(band+1)*8
            faces.extend([(a+i, b+i, b+j), (a+i, b+j, a+j)])
    o = mesh(name, vertices, faces, mat, 'CRYSTAL_Pendants')
    o['role'] = 'Faceted crystal-like opaque drop; no transmission pass'
    return o


def build():
    root = bpy.data.objects.new(ROOT, None)
    bpy.context.scene.collection.objects.link(root)
    root['units'] = 'metres'
    root['origin'] = 'floor centre'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['light_node'] = 'LIGHT_Ring'
    metal = material('Satin champagne steel', (.68, .66, .60), .72, .29)
    crystal = material('Faceted smoke-blue crystal', (.48, .64, .70), .48, .10)
    led = material('Warm white ring diffuser', (1, .94, .83), 0, .30, 3)
    # Ceiling contact is exactly 2 m above the unplaced asset's floor datum.
    rod('CEILING_Plate', (0, 0, 1.94), (0, 0, 2), .25, metal, 64)
    rod('CEILING_LowerCollar', (0, 0, 1.91), (0, 0, 1.94), .17, metal, 48)
    rod('CEILING_CentreButton', (0, 0, 1.895), (0, 0, 1.91), .065, metal, 32)
    index = 0
    for ring, (radius, height, count) in enumerate(RINGS, 1):
        profile = [(radius-.050, height+.055), (radius+.050, height+.055),
                   (radius+.054, height+.051), (radius+.054, height-.051),
                   (radius+.050, height-.055), (radius-.050, height-.055),
                   (radius-.054, height-.051), (radius-.054, height+.051)]
        lathe(f'RING_{ring:02d}_Housing', profile, metal, 'FRAME_Chandelier')
        # Narrow outer inlay and broad underside diffuser remain one light node.
        lathe(f'RING_{ring:02d}_OuterDiffuser',
              [(radius+.054, height-.021), (radius+.055, height-.021),
               (radius+.055, height+.021), (radius+.054, height+.021)], led, 'LIGHT_Ring')
        lathe(f'RING_{ring:02d}_UndersideDiffuser',
              [(radius-.043, height-.056), (radius+.043, height-.056),
               (radius+.043, height-.054), (radius-.043, height-.054)], led, 'LIGHT_Ring')
        phase = math.pi/6 if ring != 2 else math.pi/2
        for j in range(3):
            angle = phase+j*2*math.pi/3
            dx, dy = math.cos(angle), math.sin(angle)
            rod(f'SUSPENSION_R{ring}_{j+1}', (.15*dx, .15*dy, 1.92),
                (radius*dx, radius*dy, height+.055), .009, metal)
            rod(f'SUSPENSION_R{ring}_{j+1}_Socket',
                (radius*dx, radius*dy, height+.044),
                (radius*dx, radius*dy, height+.079), .019, metal)
        for j in range(count):
            index += 1
            angle = j*2*math.pi/count+math.pi/12
            x, y = radius*math.cos(angle), radius*math.sin(angle)
            length = [.24, .28, .31][ring-1]
            width = [.038, .040, .042][ring-1]
            # The longest inner wire keeps the lowest gem tip at the floor datum.
            wire = [.12+.035*(j % 3), .15+.04*(j % 2), .435-.04*(j % 2)][ring-1]
            top = height-.055-wire
            rod(f'DROP_{index:02d}_Wire', (x, y, top-.01), (x, y, height-.045), .0035, metal, 8)
            rod(f'DROP_{index:02d}_Ferrule', (x, y, top-.025), (x, y, top+.015), .014, metal)
            drop(f'DROP_{index:02d}_Crystal', x, y, top, length, width, angle, crystal)


def export(path):
    """Batch a temporary evaluated copy; preserve every saved source edit."""
    root = bpy.data.objects[ROOT]
    deps = bpy.context.evaluated_depsgraph_get()
    groups = {}
    for source in list(root.children_recursive):
        if source.type != 'MESH':
            continue
        data = bpy.data.meshes.new_from_object(source.evaluated_get(deps), depsgraph=deps)
        o = bpy.data.objects.new('DELIVERY_'+source.name, data)
        bpy.context.scene.collection.objects.link(o)
        o.matrix_world = source.matrix_world.copy()
        groups.setdefault(source['delivery_mesh'], []).append(o)
    root.name = ROOT+'_Source'
    anchor = bpy.data.objects.new(ROOT, None)
    bpy.context.scene.collection.objects.link(anchor)
    for key, value in root.items():
        anchor[key] = value
    batches = []
    for name, objects in sorted(groups.items()):
        bpy.ops.object.select_all(action='DESELECT')
        for o in objects:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.join()
        o = bpy.context.object
        o.name = name
        o.data.name = name
        o.parent = anchor
        bpy.context.scene.cursor.location = (0, 0, 0)
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        if name == 'LIGHT_Ring':
            o['runtime_role'] = 'Three concentric emissive rings; scene-owned Bloom target'
        if name == 'CRYSTAL_Pendants':
            o['pendant_count'] = 24
        batches.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    anchor.select_set(True)
    for o in batches:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
        export_apply=True, export_yup=True, export_animations=False, export_texcoords=False,
        export_extras=True, export_cameras=False, export_lights=False)
    for o in batches:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.objects.remove(anchor, do_unlink=True)
    root.name = ROOT


def aim(o, point):
    o.rotation_euler = (Vector(point)-o.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    s = bpy.context.scene
    s.world = bpy.data.worlds.new('Slate studio')
    s.world.use_nodes = True
    s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.12, .16, .21, 1)
    s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .55
    for name, loc, energy, size in [('Key', (-3, -4, 6), 1600, 4),
                                     ('Fill', (4, -2, 3), 1100, 3),
                                     ('Rim', (1, 4, 5), 1800, 3)]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        o = bpy.context.object
        o.name = 'STUDIO_'+name
        o.data.energy = energy
        o.data.shape = 'DISK'
        o.data.size = size
        aim(o, (0, 0, 1))
    bpy.ops.object.camera_add()
    s.camera = bpy.context.object
    s.camera.name = 'STUDIO_Camera'
    s.camera.data.type = 'ORTHO'
    s.camera.data.ortho_scale = 3.65
    s.render.engine = 'CYCLES'
    s.cycles.samples = 32
    s.cycles.use_denoising = True
    s.render.resolution_x = s.render.resolution_y = 900
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.view_settings.view_transform = 'AgX'


def render_views():
    s = bpy.context.scene
    for name, delta in [('hero', (4, -6, 2.6)), ('front', (0, -7, .15)),
                        ('side', (7, 0, .15)), ('3q', (4, -6, -2.0))]:
        s.camera.location = Vector((0, 0, 1))+Vector(delta)
        aim(s.camera, (0, 0, 1))
        s.render.filepath = str(HERE/'previews'/(name+'.png'))
        bpy.ops.render.render(write_still=True)


def main():
    for directory in ['sources', 'exports', 'previews', 'reports', 'metadata']:
        (HERE/directory).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        s = bpy.context.scene
        s.unit_settings.system = 'METRIC'
        s.unit_settings.scale_length = 1
        build()
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')), compress=True)
    export(HERE/'exports/optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
