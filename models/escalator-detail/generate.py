"""Original deterministic escalator detail. Blender 5.2.3, no external assets.

Folder, saved-source export and studio workflow follow self-checkout-machine.
Blender +Z up / -Y front becomes glTF +Y up / +Z front.
"""
from pathlib import Path
import bpy
import bmesh
import math
import sys
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'escalator-detail'
ROOT = 'ASSET_EscalatorDetail'
COUNT = 22
LENGTH = 6.0
RISE = 3.6
RUN = LENGTH - .90
HALF_RUN = RUN / 2
HALF_LENGTH = LENGTH / 2
NEWEL_Y = HALF_RUN + .10
PITCH = RUN / COUNT
DECK = .10
UPPER_DECK = DECK + RISE
# Two flush treads at either terminal, three increasing/decreasing risers,
# and a constant-rise central flight. Dimensions change the shared track rather
# than scaling the finished treads, ribs, handrails or panels.
transition_scale = RISE / 3.6
terminal_risers = [0, .05*transition_scale, .12*transition_scale, .19*transition_scale]
RISERS = terminal_risers + [(RISE-2*sum(terminal_risers))/13]*13 + list(reversed(terminal_risers))
LEVELS = [DECK]
for rise in RISERS:
    LEVELS.append(LEVELS[-1] + rise)
STATIONS = [(-HALF_RUN, DECK)]
STATIONS += [(-HALF_RUN + (i + .5) * PITCH, z) for i, z in enumerate(LEVELS)]
STATIONS.append((HALF_RUN, UPPER_DECK))
# Remove collinear stations to keep the extruded casing faces well conditioned.
TRACK = []
for station in STATIONS:
    while len(TRACK) >= 2:
        a, b = TRACK[-2:]
        cross = (b[0]-a[0])*(station[1]-b[1])-(b[1]-a[1])*(station[0]-b[0])
        if abs(cross) > 1e-10:
            break
        TRACK.pop()
    TRACK.append(station)


def track_height(y):
    for (a, za), (b, zb) in zip(TRACK, TRACK[1:]):
        if y <= b:
            return za + (zb-za)*(y-a)/(b-a)
    return TRACK[-1][1]


def material(name, rgb, metal=0, rough=.4, alpha=1):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.use_backface_culling = True
    c = tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb)+(alpha,)
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = c
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    p.inputs['Alpha'].default_value = alpha
    m.diffuse_color = c
    if alpha < 1:
        m.surface_render_method = 'DITHERED'
    return m


def empty(name, parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    return o


def finish(o, name, mat, group, bevel=0):
    o.name = name
    o.data.materials.append(mat)
    o.parent = bpy.data.objects[ROOT]
    o['delivery_mesh'] = group
    if bevel:
        b = o.modifiers.new('Small manufactured edge', 'BEVEL')
        b.width = bevel
        b.segments = 2
        o.modifiers.new('Corner normals', 'WEIGHTED_NORMAL')
    return o


def box(name, loc, dims, mat, group, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, name, mat, group, bevel)


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


def profile_x(name, yz, x0, x1, mat, group):
    n = len(yz)
    vertices = [(x,y,z) for x in [x0,x1] for y,z in yz]
    faces = [tuple(range(n-1,-1,-1)), tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name, vertices, faces, mat, group)


def bar(name, a, b, width, depth, mat, group):
    a,b = Vector(a),Vector(b)
    o = box(name, (a+b)/2, (width,depth,(b-a).length), mat, group)
    o.rotation_euler = (b-a).to_track_quat('Z','Y').to_euler()
    return o


def merge(objects, name, parent, pivot=(0,0,0)):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    o = bpy.context.object
    o.name = name
    o.data.name = name
    o.parent = parent
    bpy.context.scene.cursor.location = pivot
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    return o


def belt(side, mat):
    # Closed belt centreline: two horizontal terminals, inclined flight and
    # rounded newel returns. Eight-sided belt section avoids round pipe styling.
    path = [(-NEWEL_Y,DECK+.92)] + [(y,z+.92) for y,z in TRACK] + [(NEWEL_Y,UPPER_DECK+.92)]
    for i in range(1,17):
        a = math.pi/2-math.pi*i/16
        path.append((NEWEL_Y+.28*math.cos(a),UPPER_DECK+.64+.28*math.sin(a)))
    path += [(y,z+.36) for y,z in reversed(TRACK)] + [(-NEWEL_Y,DECK+.36)]
    for i in range(1,16):
        a = -math.pi/2-math.pi*i/16
        path.append((-NEWEL_Y+.28*math.cos(a),DECK+.64+.28*math.sin(a)))
    cross = [(-.027,-.021),(.027,-.021),(.036,-.012),(.036,.012),
             (.027,.021),(-.027,.021),(-.036,.012),(-.036,-.012)]
    verts = []
    for i,(y,z) in enumerate(path):
        tangent = Vector(path[(i+1)%len(path)])-Vector(path[(i-1)%len(path)])
        tangent.normalize()
        normal = Vector((-tangent.y,tangent.x))
        verts += [(side*.61+x,y+normal.x*h,z+normal.y*h) for x,h in cross]
    faces = [(i*8+j,((i+1)%len(path))*8+j,((i+1)%len(path))*8+(j+1)%8,i*8+(j+1)%8)
             for i in range(len(path)) for j in range(8)]
    o = mesh('BELT_Left' if side<0 else 'BELT_Right',verts,faces,mat,'HANDRAIL_Belts')
    for p in o.data.polygons:
        p.use_smooth = True


def build():
    root = empty(ROOT)
    root['units'] = 'metres'
    root['origin'] = 'floor centre'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['scope'] = 'Static illustrative escalator; no animation, collider or transport logic'
    steps = empty('STEPS_FutureMotion',root)
    steps['runtime_role'] = '22 independent rigid step nodes; future motion is scene-owned'
    steel = material('Satin stainless steel',(.64,.68,.70),.68,.32)
    rubber = material('Graphite handrail and insets',(.065,.080,.091),.05,.48)
    glass = material('Blue green balustrade glass',(.47,.73,.77),.08,.17,.27)

    # Sloped supporting cassette, shallow terminal plinths and skirt trims.
    # A continuous raised skirt covers the complete tread/riser side envelopes.
    # Its glass channel follows the same flattened terminal transitions.
    casing_track = [(-HALF_LENGTH,DECK)] + TRACK + [(HALF_LENGTH,UPPER_DECK)]
    profile = [(y,max(0,z-.40)) for y,z in casing_track]
    profile += [(y,z+.24) for y,z in reversed(casing_track)]
    for side in [-1,1]:
        x0,x1 = sorted([side*.50,side*.66])
        o = profile_x('CASING_Side',profile,x0,x1,steel,'FRAME_Chassis')
        b = o.modifiers.new('Casing edge', 'BEVEL'); b.width=.008; b.segments=2
        o.modifiers.new('Casing normals','WEIGHTED_NORMAL')
        for (a,za),(b,zb) in zip(TRACK,TRACK[1:]):
            bar('SKIRT_DarkInlay',(side*.505,a,za+.205),(side*.505,b,zb+.205),
                .018,.025,rubber,'HANDRAIL_Belts')
            bar('GLASS_BaseChannel',(side*.61,a,za+.25),(side*.61,b,zb+.25),
                .052,.035,steel,'FRAME_Chassis')
        for y,z in [(-NEWEL_Y-.11,DECK+.02),(NEWEL_Y+.11,UPPER_DECK+.02)]:
            box('NEWEL_Foot',(side*.61,y,z+.17),(.075,.18,.34),steel,'FRAME_Chassis',.012)
        belt(side,rubber)
        # Six discrete glass panels per side with narrow, visible expansion joints.
        for j in range(6):
            a = -HALF_RUN+j*RUN/6+.009
            b = -HALF_RUN+(j+1)*RUN/6-.009
            samples = [(a,track_height(a))] + [(y,z) for y,z in TRACK if a<y<b] + [(b,track_height(b))]
            yz = [(y,z+.25) for y,z in samples] + [(y,z+.85) for y,z in reversed(samples)]
            profile_x('GLASS_FlightPanel',yz,
                      side*.61-.006,side*.61+.006,glass,'BALUSTRADE_Glass')
        for end,base in [(-1,DECK),(1,UPPER_DECK)]:
            c = end*NEWEL_Y
            yz = [(end*HALF_RUN,base+.25)]
            for j in range(17):
                a = -math.pi/2+math.pi*j/16
                yz.append((c+end*.215*math.cos(a),base+.525+.325*math.sin(a)))
            yz += [(end*HALF_RUN,base+.85)]
            profile_x('GLASS_RoundedTerminal',yz,side*.61-.006,side*.61+.006,glass,'BALUSTRADE_Glass')
    # An underside pan follows the incline; it does not add a pit or floor slab.
    for (a,za),(b,zb) in zip(TRACK,TRACK[1:]):
        bar('PAN_Underside',(0,a,max(.028,za-.372)),(0,b,max(.028,zb-.372)),
            1.0,.05,steel,'FRAME_Chassis')
    box('BASE_Lower',(0,-HALF_RUN-.225,.035),(1.32,.45,.07),steel,'FRAME_Chassis')
    box('BASE_Upper',(0,HALF_RUN+.225,UPPER_DECK-.25),(1.32,.45,.34),steel,'FRAME_Chassis')
    for label,y,z in [('Lower',-HALF_RUN-.225,DECK),('Upper',HALF_RUN+.225,UPPER_DECK)]:
        box('LANDING_'+label,(0,y,z-.018),(1.0,.45,.036),steel,'LANDING_Plates',.003)
        for j in range(23):
            x = -.462+j*.042
            box('LANDING_Rib',(x,y,z+.0015),(.014,.38,.003),steel,'LANDING_Plates')
        # A contrasting access seam and two unmarked fastener recesses.
        box('LANDING_Seam',(0,y+(-.13 if label=='Lower' else .13),z+.001),(.97,.007,.002),rubber,'HANDRAIL_Belts')
        cy = -HALF_RUN-.01 if label=='Lower' else HALF_RUN+.01
        box('COMB_'+label+'_Spine',(0,cy,z+.006),(1.0,.045,.012),steel,'COMB_Plates')
        for j in range(25):
            x = -.48+j*.04
            box('COMB_Tooth',(x,cy+(.036 if label=='Lower' else -.036),z+.006),
                (.018,.058,.012),steel,'COMB_Plates')

    for i in range(COUNT):
        name = f'STEP_{i+1:03d}'
        y = -HALF_RUN+(i+.5)*PITCH
        z = LEVELS[i]
        rise = z-LEVELS[max(0,i-1)]
        bottom = z-.035-rise
        parts = [box(name+'_Body',(0,y,(z-.005+bottom)/2),
                     (1.0,PITCH-.004,z-.005-bottom),steel,name)]
        # Individual raised ribs are geometry, not texture; they remain one step mesh.
        for j in range(23):
            x = -.462+j*.042
            parts.append(box(name+'_TreadRib',(x,y,z-.001),(.018,PITCH-.014,.007),steel,name))
            parts.append(box(name+'_RiserRib',(x,y-PITCH/2+.001,(z-.012+bottom+.008)/2),
                             (.018,.008,z-.020-bottom),steel,name))
        parts.append(box(name+'_Nose',(0,y-PITCH/2+.001,z-.001),(1.0,.014,.008),steel,name))
        step = merge(parts,name,steps,(0,y,z))
        step['delivery_mesh'] = name
        step['step_index'] = i+1
        step['runtime_role'] = 'Independent rigid step; static rest pose'

    # Freestanding blank sign outside the complete casing and moving-belt envelope.
    # The weighted floor base carries the stem without using the glass as a support.
    sign_x, sign_y = .90, -NEWEL_Y-.05
    box('SIGN_Base',(sign_x,sign_y,.04),(.22,.30,.08),steel,'SIGNAGE_BlankPost',.012)
    box('SIGN_Stem',(sign_x,sign_y,.69),(.032,.032,1.24),steel,'SIGNAGE_BlankPost',.003)
    box('SIGN_BlankPanel',(sign_x,sign_y,1.38),(.20,.045,.28),steel,'SIGNAGE_BlankPost',.012)
    box('SIGN_BlankInset',(sign_x,sign_y-.025,1.38),(.162,.007,.242),rubber,'SIGNAGE_BlankPost',.0015)
    centre_floor_origin(root)


def centre_floor_origin(root):
    # Include the independent side sign in the footprint, preserving the root at 0.
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    points = [o.matrix_world @ Vector(corner)
              for o in root.children_recursive if o.type == 'MESH'
              for corner in o.evaluated_get(deps).bound_box]
    offset = Vector(((min(v.x for v in points)+max(v.x for v in points))/2,
                     (min(v.y for v in points)+max(v.y for v in points))/2,
                     min(v.z for v in points)))
    for o in root.children:
        o.location -= offset
    bpy.context.view_layer.update()


def export(path):
    """Batch only fixed parts in an evaluated copy, preserving saved edits."""
    root = bpy.data.objects[ROOT]
    deps = bpy.context.evaluated_depsgraph_get()
    groups = {}
    pivots = {}
    for source in list(root.children_recursive):
        if source.type != 'MESH':
            continue
        data = bpy.data.meshes.new_from_object(source.evaluated_get(deps),depsgraph=deps)
        o = bpy.data.objects.new('DELIVERY_'+source.name,data)
        bpy.context.scene.collection.objects.link(o)
        o.matrix_world = source.matrix_world.copy()
        name = source['delivery_mesh']
        groups.setdefault(name,[]).append(o)
        if name.startswith('STEP_'):
            pivots[name] = source.matrix_world.translation.copy()
    root.name = ROOT+'_Source'
    # Temporarily free canonical step names for stable delivery node names.
    source_steps = list(bpy.data.objects['STEPS_FutureMotion'].children)
    bpy.data.objects['STEPS_FutureMotion'].name = 'STEPS_FutureMotion_Source'
    for o in source_steps:
        o.name += '_Source'
    anchor = empty(ROOT)
    for k,v in root.items():
        anchor[k] = v
    steps = empty('STEPS_FutureMotion',anchor)
    batches = []
    for name,objects in sorted(groups.items()):
        step = name.startswith('STEP_')
        o = merge(objects,name,steps if step else anchor,pivots.get(name,(0,0,0)))
        if step:
            o['step_index'] = int(name[-3:])
            o['runtime_role'] = 'Independent rigid step; static rest pose'
        batches.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in [anchor,steps]+batches:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
        export_apply=True,export_yup=True,export_animations=False,export_texcoords=False,
        export_extras=True,export_cameras=False,export_lights=False)
    for o in batches+[steps,anchor]:
        bpy.data.objects.remove(o,do_unlink=True)
    for o in source_steps:
        o.name = o.name.removesuffix('_Source')
    bpy.data.objects['STEPS_FutureMotion_Source'].name = 'STEPS_FutureMotion'
    root.name = ROOT


def aim(o,point):
    o.rotation_euler = (Vector(point)-o.location).to_track_quat('-Z','Y').to_euler()


def studio():
    s = bpy.context.scene
    s.world = bpy.data.worlds.new('Slate studio')
    s.world.use_nodes = True
    s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.095,.125,.16,1)
    s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
    for name,loc,energy,size in [('Key',(-4,-5,9),2800,6),('Fill',(5,-2,6),2200,5),('Rim',(1,5,8),3200,5)]:
        bpy.ops.object.light_add(type='AREA',location=loc)
        o = bpy.context.object
        o.name = 'STUDIO_'+name
        o.data.energy = energy
        o.data.size = size
        aim(o,(0,0,2))
    bpy.ops.object.camera_add()
    s.camera = bpy.context.object
    s.camera.name = 'STUDIO_Camera'
    s.camera.data.type = 'ORTHO'
    s.camera.data.ortho_scale = max(7.4,LENGTH*1.13)
    s.render.engine = 'CYCLES'
    s.cycles.samples = 32
    s.cycles.seed = 0
    s.cycles.use_denoising = True
    s.render.resolution_x = s.render.resolution_y = 900
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.view_settings.view_transform = 'AgX'


def render_views():
    s = bpy.context.scene
    for name,delta in [('hero',(7,-9,5.8)),('front',(0,-10,1.6)),
                       ('side',(10,0,1.2)),('3q',(-7,9,4.8))]:
        s.camera.location = Vector((0,0,2.25))+Vector(delta)
        aim(s.camera,(0,0,2.25))
        s.render.filepath = str(HERE/'previews'/(name+'.png'))
        bpy.ops.render.render(write_still=True)


def main():
    for directory in ['sources','exports','previews','reports','metadata']:
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
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(HERE/'exports/optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
