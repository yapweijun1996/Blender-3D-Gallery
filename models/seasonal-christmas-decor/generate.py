"""Original deterministic seasonal mall set, Blender 5.2.3; no external assets.

Template: self-checkout-machine (editable source, selective GLB export, studio).
Author in metres, Blender +Z up / -Y front; export glTF +Y up / +Z front.
"""
from pathlib import Path
import bpy
import bmesh
import math
import sys
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'seasonal-christmas-decor'
ROOT = 'ASSET_SeasonalChristmasDecor'


def material(name, rgb, metallic, roughness):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    color = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)
    shader = m.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = color
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    m.diffuse_color = color
    m.use_backface_culling = True
    return m


def empty(name, parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    return o


def finish(o, name, m, parent, batch, bevel=0):
    o.name = name
    o.parent = parent
    o.data.materials.append(m)
    o['delivery_mesh'] = batch
    if bevel:
        edge = o.modifiers.new('Soft manufactured edge', 'BEVEL')
        edge.width = bevel
        edge.segments = 2
        o.modifiers.new('Corner normals', 'WEIGHTED_NORMAL')
    return o


def mesh(name, vertices, faces, m, parent, batch):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    o = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(o)
    return finish(o, name, m, parent, batch)


def box(name, loc, dims, m, parent, batch, bevel=.005):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, name, m, parent, batch, bevel)


def rod(name, a, b, radius, m, parent, batch, segments=10):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments, radius=radius, depth=(b-a).length, location=(a+b)/2)
    o = bpy.context.object
    o.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    finish(o, name, m, parent, batch)
    for face in o.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    return o


def ball(name, loc, radius, m, parent, batch):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=radius, location=loc)
    o = finish(bpy.context.object, name, m, parent, batch)
    for face in o.data.polygons:
        face.use_smooth = True
    return o


def foliage(index, radius, bottom, height, m, parent):
    # Closed overlapping branch skirts; a twelve-tip scallop softens each edge.
    rings = [(radius*.87, 0), (radius, .065), (radius*.91, .19),
             (radius*.66, .43), (radius*.32, .75), (.009, 1)]
    n = 36
    verts = []
    for r, z in rings:
        for i in range(n):
            a = 2*math.pi*i/n
            scallop = 1 + .034*math.cos(12*a + index*.7)
            verts.append((r*scallop*math.cos(a), r*scallop*math.sin(a),
                          bottom + z*height + (.009*math.sin(12*a) if z < .2 else 0)))
    faces = [tuple(reversed(range(n)))]
    for j in range(len(rings)-1):
        for i in range(n):
            k = (i+1) % n
            faces.append((j*n+i, j*n+k, (j+1)*n+k, (j+1)*n+i))
    faces.append(tuple((len(rings)-1)*n+i for i in range(n)))
    o = mesh(f'FOLIAGE_Tier{index+1:02}', verts, faces, m, parent, 'TREE_Pine')
    for face in o.data.polygons:
        face.use_smooth = len(face.vertices) == 4


def star(m, parent):
    verts = []
    for y in [-.012, .012]:
        for i in range(10):
            a = math.pi/2 + i*math.pi/5
            r = .16 if i % 2 == 0 else .073
            verts.append((r*math.cos(a), y, 2.34 + r*math.sin(a)))
    verts += [(0, -.052, 2.34), (0, .042, 2.34)]
    faces = []
    for i in range(10):
        k = (i+1) % 10
        faces += [(20, i, k), (21, 10+k, 10+i), (i, 10+i, 10+k, k)]
    mesh('STAR_FacetedTopper', verts, faces, m, parent, 'TREE_Champagne')
    rod('STAR_Stem', (0,0,2.22), (0,0,2.32), .012, m, parent, 'TREE_Champagne')


def bow_loop(name, x, y, z, direction, m, parent):
    # Closed ribbon with a rectangular section, rather than a tubular bow.
    n = 24
    verts = []
    for i in range(n):
        t = 2*math.pi*i/n
        center = Vector((x + direction*.085*(1-math.cos(t)), y + .018*math.sin(t), z + .045 + .045*math.sin(t)))
        tangent = Vector((direction*.085*math.sin(t), 0, .045*math.cos(t))).normalized()
        normal = Vector((-tangent.z, 0, tangent.x))*.0035
        across = Vector((0,.022,0))
        for a,b in [(-1,-1), (1,-1), (1,1), (-1,1)]:
            verts.append(tuple(center + across*a + normal*b))
    faces = []
    for i in range(n):
        for j in range(4):
            faces.append((i*4+j, ((i+1)%n)*4+j, ((i+1)%n)*4+(j+1)%4, i*4+(j+1)%4))
    mesh(name, verts, faces, m, parent, 'GIFTS_Champagne')


def gift(index, loc, dims, wrapping, gold, parent):
    x,y,bottom = loc
    w,d,h = dims
    group = empty(f'GIFT_{index:02}', parent)
    group['feature'] = 'wrapped gift box'
    batch = 'GIFTS_Pine' if wrapping.name == 'Pine green' else 'GIFTS_Cranberry'
    box(f'BOX_{index:02}_Body', (x,y,bottom+(h-.026)/2), (w,d,h-.026), wrapping, group, batch, .009)
    box(f'BOX_{index:02}_Lid', (x,y,bottom+h-.014), (w+.012,d+.012,.028), wrapping, group, batch, .004)
    # Crossed bands run around the complete box and meet the top bow.
    for xx in [x-w/2-.002, x+w/2+.002]:
        box(f'RIBBON_{index:02}_Side', (xx,y,bottom+h/2), (.005,.049,h-.005), gold, group, 'GIFTS_Champagne', .001)
    for yy in [y-d/2-.002, y+d/2+.002]:
        box(f'RIBBON_{index:02}_Front', (x,yy,bottom+h/2), (.049,.005,h-.005), gold, group, 'GIFTS_Champagne', .001)
    top = bottom+h+.003
    box(f'RIBBON_{index:02}_TopX', (x,y,top), (w+.017,.049,.005), gold, group, 'GIFTS_Champagne', .001)
    box(f'RIBBON_{index:02}_TopY', (x,y,top+.001), (.049,d+.017,.005), gold, group, 'GIFTS_Champagne', .001)
    for side in [-1,1]:
        bow_loop(f'BOW_{index:02}_Loop{side}', x,y,top+.006,side,gold,group)
    box(f'BOW_{index:02}_Knot', (x,y,top+.045), (.054,.067,.048), gold, group, 'GIFTS_Champagne', .008)
    for side in [-1,1]:
        tail = box(f'BOW_{index:02}_Tail', (x+side*.064,y-.083,top+.009), (.045,.14,.006), gold, group, 'GIFTS_Champagne', .001)
        tail.rotation_euler.z = side*.28


def snowflake(index, x, y, z, radius, anchor, gold, parent):
    group = empty(f'SNOWFLAKE_{index:02}', parent)
    group['feature'] = 'six-arm hanging snowflake'
    group['hanging_anchor_blender'] = [x,y,anchor]
    batch = f'SNOWFLAKE_{index:02}_Champagne'
    center = Vector((x,y,z))
    for arm in range(6):
        a = math.pi/2 + arm*math.pi/3
        outward = Vector((math.cos(a),0,math.sin(a)))
        tangent = Vector((-math.sin(a),0,math.cos(a)))
        rod(f'SNOW_{index:02}_Arm{arm}', center, center+outward*radius, .009, gold, group, batch, 6)
        for fraction in [.46,.73]:
            start = center + outward*radius*fraction
            for side in [-1,1]:
                end = start + outward*radius*.18 + tangent*radius*.17*side
                rod(f'SNOW_{index:02}_Branch', start,end,.0065,gold,group,batch,6)
    ball(f'SNOW_{index:02}_Center', center, .024, gold, group, batch)
    # The suspension ring meets the upper arm; the cord ends at an explicit anchor.
    bpy.ops.mesh.primitive_torus_add(major_radius=.017, minor_radius=.003, major_segments=16, minor_segments=6,
        location=(x,y,z+radius+.015), rotation=(math.pi/2,0,0))
    finish(bpy.context.object, f'SNOW_{index:02}_Ring', gold, group, batch)
    rod(f'SNOW_{index:02}_Cord', (x,y,z+radius+.031), (x,y,anchor), .0025, gold, group, batch, 8)


def build():
    root = empty(ROOT)
    root['units'] = 'metres'
    root['origin'] = 'floor centre of complete set bounds'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['scope'] = 'Static theme-switching decoration; no switching runtime or animations'
    pine = material('Pine green', (.12,.34,.235), .02,.53)
    red = material('Cranberry red', (.66,.075,.12), .12,.29)
    gold = material('Champagne gold', (.90,.74,.43), .58,.32)
    tree = empty('TREE_Assembly', root)
    tree['feature'] = '2.5 metre decorated tree including star'
    rod('TREE_Trunk', (0,0,.04), (0,0,2.25), .055, pine, tree, 'TREE_Pine', 16)
    rod('TREE_Plinth', (0,0,.025), (0,0,.115), .24, gold, tree, 'TREE_Champagne', 32)
    rod('TREE_Foot', (0,0,0), (0,0,.035), .26, pine, tree, 'TREE_Pine', 32)
    radii = [.77,.66,.55,.44,.33,.225,.13]
    for i,r in enumerate(radii):
        bottom = .26 + i*.28
        foliage(i,r,bottom,.62 if i < 5 else .36,pine,tree)
        count = [7,6,6,5,4,3,0][i]
        for j in range(count):
            # Keep the foreground presents and their bows clear of ornaments.
            if (i == 0 and j in [4,5,6]) or (i == 1 and j == 3):
                continue
            a = 2*math.pi*j/count + .4 + i*.65
            radius = .055 if i < 3 else .043
            radial = r+.017
            x,y,z = radial*math.cos(a),radial*math.sin(a),bottom+.067
            m = gold if (i+j)%3 == 0 else red
            batch = 'TREE_Champagne' if m == gold else 'TREE_Cranberry'
            ball(f'BAUBLE_{i:02}_{j:02}', (x,y,z), radius,m,tree,batch)
            rod(f'CAP_{i:02}_{j:02}', (x,y,z+radius*.86), (x,y,z+radius+ .013), .014,gold,tree,'TREE_Champagne',10)
            rod(f'HANGER_{i:02}_{j:02}', (x,y,z+radius+.013), (x*.94,y*.94,z+radius+.058), .003,gold,tree,'TREE_Champagne',8)
    star(gold,tree)
    gifts = empty('GIFTS_Assembly',root)
    gift(1,(-.49,-.60,0),(.50,.43,.31),red,gold,gifts)
    gift(2,(-.51,-.58,.31),(.34,.32,.24),pine,gold,gifts)
    gift(3,(.10,-.79,0),(.39,.34,.25),pine,gold,gifts)
    gift(4,(.55,-.51,0),(.34,.35,.42),red,gold,gifts)
    snowflake(1,-1.08,.10,1.94,.23,2.46,gold,root)
    snowflake(2,1.08,.10,1.72,.195,2.34,gold,root)
    # Centre the complete footprint, including the suspended ornaments.
    bpy.context.view_layer.update()
    meshes = [o for o in root.children_recursive if o.type == 'MESH']
    points = [o.matrix_world @ Vector(v) for o in meshes for v in o.bound_box]
    offset = Vector(((min(v.x for v in points)+max(v.x for v in points))/2,
                     (min(v.y for v in points)+max(v.y for v in points))/2,0))
    for o in meshes:
        o.location -= offset
    for o in root.children_recursive:
        if 'hanging_anchor_blender' in o:
            o['hanging_anchor_blender'] = list(Vector(o['hanging_anchor_blender'])-offset)
    root['footprint_offset_blender'] = list(offset)


def export(path):
    # Keep authoring parts editable; batch only evaluated delivery copies by material.
    root = bpy.data.objects[ROOT]
    deps = bpy.context.evaluated_depsgraph_get()
    groups = {}
    for source in root.children_recursive:
        if source.type != 'MESH':
            continue
        data = bpy.data.meshes.new_from_object(source.evaluated_get(deps), depsgraph=deps)
        o = bpy.data.objects.new('DELIVERY_'+source.name, data)
        bpy.context.scene.collection.objects.link(o)
        o.matrix_world = source.matrix_world.copy()
        groups.setdefault(source['delivery_mesh'],[]).append(o)
    anchor = empty(ROOT+'_Delivery')
    root.name = ROOT+'_Source'
    anchor.name = ROOT
    for key,value in root.items():
        anchor[key] = value
    batches = []
    for name,objects in sorted(groups.items()):
        bpy.ops.object.select_all(action='DESELECT')
        for o in objects:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.join()
        o = bpy.context.object
        o.name = name
        o.data.name = name
        o.parent = anchor
        bpy.context.scene.cursor.location = (0,0,0)
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        batches.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in [anchor]+batches:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
        export_apply=True, export_yup=True, export_animations=False, export_texcoords=False,
        export_extras=True, export_cameras=False, export_lights=False)
    for o in batches+[anchor]:
        bpy.data.objects.remove(o, do_unlink=True)
    root.name = ROOT


def aim(o,point):
    o.rotation_euler = (Vector(point)-o.location).to_track_quat('-Z','Y').to_euler()


def studio():
    s = bpy.context.scene
    s.world = bpy.data.worlds.new('Slate studio')
    s.world.use_nodes = True
    s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.07,.095,.12,1)
    s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .55
    for name,loc,power,size in [('Key',(-3,-4,6),750,4),('Fill',(4,-2,4),480,3),('Rim',(1,4,5),950,3)]:
        bpy.ops.object.light_add(type='AREA',location=loc)
        o = bpy.context.object
        o.name = 'STUDIO_'+name
        o.data.energy = power
        o.data.size = size
        aim(o,(0,0,1.2))
    # Studio floor is excluded from the root and the exported GLB.
    floor = material('Studio only',(.18,.22,.26),0,.8)
    box('STUDIO_Ground',(0,0,-.035),(2000,2000,.06),floor,None,'STUDIO',0)
    bpy.ops.object.camera_add()
    s.camera = bpy.context.object
    s.camera.name = 'STUDIO_Camera'
    s.camera.data.type = 'ORTHO'
    s.camera.data.ortho_scale = 3.4
    s.camera.location = (2.5,-6,3.05)
    aim(s.camera,(0,0,1.21))
    s.render.engine = 'CYCLES'
    s.cycles.samples = 40
    s.cycles.seed = 0
    s.cycles.use_denoising = True
    s.render.resolution_x = s.render.resolution_y = 800
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.view_settings.view_transform = 'AgX'


def render_views():
    s = bpy.context.scene
    for name,loc in [('hero',(2.5,-6,3.05)),('front',(0,-7,1.25)),
                     ('side',(7,0,1.5)),('3q',(-3.8,-5,3.5))]:
        s.camera.location = loc
        aim(s.camera,(0,0,1.21))
        s.render.filepath = str(HERE/'previews'/(name+'.png'))
        bpy.ops.render.render(write_still=True)


def main():
    for folder in ['sources','exports','previews','reports','metadata']:
        (HERE/folder).mkdir(exist_ok=True)
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
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(HERE/'exports/optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
