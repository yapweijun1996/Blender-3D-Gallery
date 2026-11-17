"""Original deterministic CNY mall decoration, Blender 5.2.3, no external assets.

Follows self-checkout-machine source/export/studio layout. Metres, +Z up and
-Y front in Blender; native glTF export gives +Y up and +Z front.
"""
from pathlib import Path
import bpy
import bmesh
import math
import sys
import json
import struct
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'seasonal-cny-decor'
ROOT = 'ASSET_SeasonalCNYDecor'


def material(name, rgb, roughness=.43):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    color = tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb)+(1,)
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = color
    p.inputs['Roughness'].default_value = roughness
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
        mod = o.modifiers.new('Soft edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        o.modifiers.new('Corner normals', 'WEIGHTED_NORMAL')
    return o


def mesh(name, vertices, faces, m, parent, batch, smooth=False):
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
    for face in data.polygons:
        face.use_smooth = smooth and len(face.vertices) == 4
    return finish(o, name, m, parent, batch)


def box(name, loc, dims, m, parent, batch, bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, name, m, parent, batch, bevel)


def rod(name, a, b, radius, m, parent, batch, segments=12):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments, radius=radius,
        depth=(b-a).length, location=(a+b)/2)
    o = bpy.context.object
    o.rotation_euler = (b-a).to_track_quat('Z','Y').to_euler()
    for face in o.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    return finish(o, name, m, parent, batch)


def lathe(name, x, y, rings, m, parent, batch, segments=40, flute=0):
    vertices = []
    for radius, z in rings:
        for i in range(segments):
            a = math.tau*i/segments
            r = radius*(1+flute*math.cos(12*a))
            vertices.append((x+r*math.cos(a),y+r*math.sin(a),z))
    faces = [tuple(reversed(range(segments)))]
    for j in range(len(rings)-1):
        for i in range(segments):
            k = (i+1)%segments
            faces.append((j*segments+i,j*segments+k,(j+1)*segments+k,(j+1)*segments+i))
    faces.append(tuple((len(rings)-1)*segments+i for i in range(segments)))
    return mesh(name,vertices,faces,m,parent,batch,True)


def lantern(number, x, y, z, anchor, red, gold, root):
    group = empty(f'LANTERN_{number:02}_Assembly',root)
    group['feature'] = 'hanging red lantern'
    group['hanging_anchor_blender'] = [x,y,anchor]
    batch = f'LANTERN_{number:02}'
    profile = [(.069,-.19),(.14,-.164),(.218,-.11),(.246,-.045),
               (.246,.045),(.218,.11),(.14,.164),(.069,.19)]
    lathe(f'LANTERN_BODY_{number:02}',x,y,[(r,z+h) for r,h in profile],
          red,group,batch,48,.016)
    for side in [-1,1]:
        zz = z+side*.196
        lathe(f'LANTERN_CAP_{number:02}_{side}',x,y,
              [(.073,zz-.011),(.083,zz-.007),(.083,zz+.007),(.073,zz+.011)],
              gold,group,batch,24)
    rod(f'LANTERN_CORD_{number:02}',(x,y,z+.207),(x,y,anchor),.003,gold,group,batch,8)
    rod(f'LANTERN_TASSEL_NECK_{number:02}',(x,y,z-.207),(x,y,z-.238),.007,gold,group,batch,8)
    lathe(f'LANTERN_TASSEL_{number:02}',x,y,
          [(.026,z-.307),(.022,z-.294),(.010,z-.236)],red,group,batch,12)
    # Narrow raised ribs follow the red shell and meet the collar rings.
    for i in range(12):
        a = math.tau*i/12
        for j in range(len(profile)-1):
            r0,h0 = profile[j]
            r1,h1 = profile[j+1]
            rod(f'LANTERN_RIB_{number:02}_{i:02}_{j}',
                (x+r0*1.016*math.cos(a),y+r0*1.016*math.sin(a),z+h0),
                (x+r1*1.016*math.cos(a),y+r1*1.016*math.sin(a),z+h1),
                .0017,gold,group,batch,5)


def banner(number, x, y, top, red, gold, root):
    group = empty(f'BANNER_{number:02}_Assembly',root)
    group['feature'] = 'blank red banner without text or characters'
    group['hanging_anchor_blender'] = [x,y,top+.09]
    batch = f'BANNER_{number:02}'
    box(f'BANNER_CLOTH_{number:02}',(x,y,top-.36),(.175,.008,.72),red,group,batch,.002)
    for z in [top,top-.72]:
        rod(f'BANNER_ROLL_{number:02}',(x-.106,y,z),(x+.106,y,z),.011,gold,group,batch)
    rod(f'BANNER_LOOP_{number:02}_L',(x-.075,y,top+.008),(x,y,top+.09),.0028,gold,group,batch,8)
    rod(f'BANNER_LOOP_{number:02}_R',(x+.075,y,top+.008),(x,y,top+.09),.0028,gold,group,batch,8)


def leaf(name, start, direction, length, width, green, parent):
    start, direction = Vector(start), Vector(direction).normalized()
    side = direction.cross(Vector((0,0,1))).normalized()
    if side.length < .5:
        side = Vector((1,0,0))
    normal = side.cross(direction).normalized()
    # A closed, shallow lenticular leaf with a raised midrib and pointed tip.
    vertices = [tuple(start),tuple(start+direction*length)]
    for t in [.28,.62]:
        center = start+direction*length*t+Vector((0,0,.014*math.sin(math.pi*t)))
        for offset in [side*width/2,normal*.006,-side*width/2,-normal*.003]:
            vertices.append(tuple(center+offset))
    faces = []
    for j in range(4):
        k = (j+1)%4
        faces += [(0,2+k,2+j),(2+j,2+k,6+k,6+j),(1,6+j,6+k)]
    return mesh(name,vertices,faces,green,parent,'PLANT_Green',True)


def plant(red, green, gold, root):
    group = empty('PLANT_Assembly',root)
    group['feature'] = 'one metre potted tangerine plant with oranges'
    x,y = -.19,-.075
    lathe('POT_Body',x,y,[(.102,0),(.112,.022),(.144,.226),(.144,.25),
          (.129,.25),(.125,.228),(.093,.04)],red,group,'PLANT_Red',32)
    lathe('POT_Rim',x,y,[(.145,.225),(.154,.233),(.154,.257),(.144,.264)],
          gold,group,'PLANT_Gold',32)
    rod('POT_Surface',(x,y,.235),(x,y,.24),.124,green,group,'PLANT_Green',32)
    rod('PLANT_Trunk',(x,y,.235),(x+.022,y,.77),.014,green,group,'PLANT_Green')
    for tier,(height,radius,count) in enumerate([(.51,.235,5),(.68,.23,6),(.82,.15,5)]):
        for j in range(count):
            a = math.tau*j/count+tier*.87
            endpoint = Vector((x+radius*math.cos(a),y+radius*math.sin(a),height+.055))
            base = Vector((x+.012,y,height-.12))
            rod(f'BRANCH_{tier}_{j}',base,endpoint,.0055,green,group,'PLANT_Green',8)
            for k in range(5):
                fraction = .39+k*.145
                start = base.lerp(endpoint,fraction)
                angle = a+(-1 if k%2 else 1)*.83
                direction = (math.cos(angle),math.sin(angle),.20+(k%2)*.22)
                leaf(f'LEAF_{tier}_{j}_{k}',start,direction,.12 if tier<2 else .10,.043,green,group)
            # Oranges sit just below branch tips, with visible green stalks.
            center = endpoint+Vector((0,0,-.037))
            rod(f'FRUIT_STEM_{tier}_{j}',endpoint,center,.003,green,group,'PLANT_Green',6)
            bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,
                radius=.035 if tier<2 else .031,location=center)
            fruit = finish(bpy.context.object,f'ORANGE_{tier}_{j}',gold,group,'PLANT_Gold')
            fruit.scale.z = .93
            for face in fruit.data.polygons:
                face.use_smooth = True
    # Upright terminal shoot establishes the one-metre measured plant height.
    rod('PLANT_TerminalStem',(x+.022,y,.76),(x+.022,y,.965),.004,green,group,'PLANT_Green',8)
    leaf('LEAF_Terminal', (x+.022,y,.90),(0,0,1),.10,.035,green,group)


def envelope_stand(red, gold, root):
    group = empty('ENVELOPE_STAND_Assembly',root)
    group['feature'] = 'small red envelope stand'
    batch = 'ENVELOPE_STAND'
    x,y = .43,-.19
    box('STAND_Foot',(x,y,.018),(.38,.29,.036),red,group,batch,.009)
    box('STAND_Pedestal',(x,y+.024,.102),(.075,.085,.15),gold,group,batch,.005)
    box('STAND_Tray',(x,y,.193),(.35,.25,.032),gold,group,batch,.004)
    box('STAND_Back',(x,y+.099,.286),(.35,.025,.19),red,group,batch,.005)
    for j in range(2):
        yy = y-.065+j*.102
        box(f'STAND_Lip_{j}',(x,yy-.023,.223+j*.041),(.345,.016,.046),red,group,batch,.003)
        for k in range(3):
            xx = x+(k-1)*.108
            zz = .279+j*.046
            box(f'ENVELOPE_{j}_{k}',(xx,yy,zz),(.092,.009,.132),red,group,batch,.0015)
            # Triangular flap seam is geometry only; no text or symbols.
            for side in [-1,1]:
                rod(f'ENVELOPE_Flap_{j}_{k}_{side}',(xx+side*.041,yy-.0055,zz+.050),
                    (xx,yy-.0055,zz+.023),.0008,gold,group,batch,5)


def build():
    root = empty(ROOT)
    root['units'] = 'metres'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['origin'] = 'floor centre of complete set bounds'
    root['scope'] = 'Static decoration set; scene supplies mounts and theme switching'
    red = material('Festive red',(.76,.065,.085),.39)
    green = material('Tangerine green',(.12,.34,.19),.52)
    gold = material('Golden orange',(.97,.56,.13),.4)
    lantern(1,-.73,.05,1.60,2.02,red,gold,root)
    lantern(2,.73,.05,1.50,1.94,red,gold,root)
    banner(1,-.33,.23,1.80,red,gold,root)
    banner(2,.33,.23,1.80,red,gold,root)
    plant(red,green,gold,root)
    envelope_stand(red,gold,root)
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


def canonicalize_indices(path):
    # Blender can reorder equal-material triangles between processes. Sort
    # cyclically rotated index triples, preserving winding and every triangle.
    data = bytearray(path.read_bytes())
    json_length = struct.unpack_from('<I',data,12)[0]
    document = json.loads(data[20:20+json_length])
    binary_start = 28+json_length
    for model in document['meshes']:
        for primitive in model['primitives']:
            assert primitive.get('mode',4) == 4
            accessor = document['accessors'][primitive['indices']]
            view = document['bufferViews'][accessor['bufferView']]
            fmt = {5123:'H',5125:'I'}[accessor['componentType']]
            size = struct.calcsize('<'+fmt)
            offset = binary_start+view.get('byteOffset',0)+accessor.get('byteOffset',0)
            assert accessor['count'] % 3 == 0 and 'byteStride' not in view
            triangles = []
            for i in range(0,accessor['count'],3):
                triangle = struct.unpack_from('<'+fmt*3,data,offset+i*size)
                first = triangle.index(min(triangle))
                triangles.append(triangle[first:]+triangle[:first])
            for i,triangle in enumerate(sorted(triangles)):
                struct.pack_into('<'+fmt*3,data,offset+i*3*size,*triangle)
    path.write_bytes(data)


def export(path):
    # Preserve editable source components; batch evaluated delivery copies.
    root = bpy.data.objects[ROOT]
    deps = bpy.context.evaluated_depsgraph_get()
    groups = {}
    for source in sorted(root.children_recursive,key=lambda o:o.name):
        if source.type != 'MESH':
            continue
        data = bpy.data.meshes.new_from_object(source.evaluated_get(deps),depsgraph=deps)
        o = bpy.data.objects.new('DELIVERY_'+source.name,data)
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
        bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
        batches.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in [anchor]+batches:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
        export_apply=True,export_yup=True,export_animations=False,export_texcoords=False,
        export_extras=True,export_cameras=False,export_lights=False)
    canonicalize_indices(path)
    for o in batches+[anchor]:
        bpy.data.objects.remove(o,do_unlink=True)
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
        aim(o,(0,0,1))
    floor = material('Studio only',(.18,.22,.26),.8)
    box('STUDIO_Ground',(0,0,-.035),(2000,2000,.06),floor,None,'STUDIO',0)
    bpy.ops.object.camera_add()
    s.camera = bpy.context.object
    s.camera.name = 'STUDIO_Camera'
    s.camera.data.type = 'ORTHO'
    s.camera.data.ortho_scale = 2.7
    s.render.engine = 'CYCLES'
    s.cycles.samples = 40
    s.cycles.seed = 0
    s.cycles.use_denoising = True
    s.render.resolution_x = s.render.resolution_y = 800
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.view_settings.view_transform = 'AgX'
    s.camera.location = (2.3,-6,2.8)
    aim(s.camera,(0,0,1))


def render_views():
    s = bpy.context.scene
    for name,loc in [('hero',(2.3,-6,2.8)),('front',(0,-7,1.03)),
                     ('side',(7,0,1.25)),('3q',(-3.8,-5,3.2))]:
        s.camera.location = loc
        aim(s.camera,(0,0,1))
        s.render.filepath = str(HERE/'previews'/(name+'.png'))
        bpy.ops.render.render(write_still=True)


def main():
    for folder in ['sources','exports','previews','metadata','reports']:
        (HERE/folder).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.context.scene.unit_settings.system = 'METRIC'
        bpy.context.scene.unit_settings.scale_length = 1
        build()
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(HERE/'exports/optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
