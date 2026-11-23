"""Convert the eleven named gallery exports to the game-ready MRT kit."""
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT))
from geometry import Model, IDENTITY, bounds, part_name
from glb import GLB

ROOT = KIT.parents[2]
ASSETS = {
    'mrt-train-carriage': ('mrt_carriage',7000),
    'mrt-platform': ('mrt_platform',3500),
    'mrt-platform-screen-door': ('platform_screen_door',700),
    'train-ticket-gate': ('fare_gate',600),
    'mrt-station-signage': ('station_sign',400),
    'mrt-route-map-panel': ('route_map',300),
    'mrt-train-seat': ('train_seat',250),
    'mrt-train-door': ('train_door',300),
    'mrt-ceiling-grab-handle': ('grab_handle',120),
    'access-card-reader': ('card_reader',150),
    'bus-arrival-display': ('arrival_display',200),
}
PLATFORM_ROTATION = Matrix(((0,-1,0,0),(1,0,0,0),(0,0,1,0),(0,0,0,1)))
BLUE = (.006,.055,.14)
TEAL = (.021,.109,.136)
GREY = (.305,.366,.397)
WHITE = (1,1,1)
CHARCOAL = (.019,.027,.030)

def original(slug):
    return ROOT/'models'/slug/'exports'/('mrt-train-carriage.glb' if slug=='mrt-train-carriage' else 'optimized.glb')

def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.view_layer.update()
    return [obj for obj in bpy.context.scene.objects if obj.type=='MESH']

def rgba(obj):
    mat = obj.data.materials[0]
    shader = next(node for node in mat.node_tree.nodes if node.type=='BSDF_PRINCIPLED')
    return tuple(shader.inputs['Base Color'].default_value)

def surface(name, rgb, alpha=1):
    return (name,(*rgb[:3],alpha))

def sourced(name, obj, alpha=1):
    return surface(name,rgba(obj),alpha)

def world_bounds(obj):
    return bounds(obj.matrix_world @ vertex.co for vertex in obj.data.vertices)

def carriage(model, objects):
    appearance = {
        'Roof':'paint','Upper_Side_Rail':'paint','Lower_Side_Rail':'paint',
        'Lower_Wall':'paint','Window_Post':'paint','Door_Header':'paint',
        'End_Wall':'paint','End_Header':'paint','Front_Headlamp':'light',
        'Window_Band':'glass','Door_Pane':'glass','End_Window':'glass',
    }
    wheels = {'00':'F','01':'F2','10':'R2','11':'R'}
    for obj in objects:
        key = part_name(obj)
        if obj.parent and obj.parent.name.startswith('ROLL_'):
            side, a, b = obj.parent.name[5:]
            axle = wheels[a+b]
            group = 'wheel_'+axle[0]+side+axle[1:]
            model.pivots[group] = obj.parent.matrix_world.translation.copy()
            if key.startswith('Tyre_'):
                low,high = bounds(v.co for v in obj.data.vertices)
                half = (high.z-low.z)/2
                radius = (high.x-low.x)/2
                profile = [(-half,.25),(-half,radius-.027),(-half*.58,radius),
                           (half*.58,radius),(half,radius-.027),(half,.25)]
                model.lathe(obj.matrix_world,profile,16,sourced('tire',obj),group,closed=True)
            elif key.startswith('Hub_'):
                model.rod(obj,sourced('tire',obj),12,group)
            else:
                model.part(obj,surface('tire',(.62,.66,.68)),group=group)
            continue
        group = 'body'
        for prefix in ['Door_Pane','Door_Lower','Door_Stile','Door_Top']:
            if key.startswith(prefix+'_'):
                tag = obj.parent.name.split('_')[1]
                group = 'door_'+tag[0]+('1' if tag.endswith('Front') else '2')
                center = obj.parent.matrix_world.translation
                model.pivots[group] = Vector((center.x,-3.4 if group.endswith('1') else 3.4,center.z))
                model.moves[group] = Vector((0,1.46 if group.endswith('1') else -1.46,0))
                style = sourced('glass',obj,.37 if prefix=='Door_Pane' else 1)
                model.part(obj,style,group=group)
                if prefix=='Door_Lower':
                    lo,hi = world_bounds(obj)
                    x = (hi.x + .0008) if hi.x>0 else (lo.x - .0008)
                    model.box((min(x, x-.004 if x>0 else x+.004),lo.y,1.887),
                              (max(x, x-.004 if x>0 else x+.004),hi.y,2.017),
                              surface('glass',TEAL),group)
                break
        if group != 'body':
            continue
        material = appearance.get(key,'trim')
        style = sourced(material,obj,.34 if material=='glass' else 1)
        if key == 'Grab_Pole':
            model.rod(obj,style,8)
        elif key == 'Front_Headlamp':
            lo,hi = world_bounds(obj)
            model.box((lo.x-.025,lo.y-.004,lo.z-.02),(hi.x+.025,hi.y-.002,hi.z+.02),
                      surface('trim',CHARCOAL),chamfer=.016,axis=1)
            model.box((lo.x+.006,lo.y-.012,lo.z+.006),(hi.x-.006,lo.y-.003,hi.z-.006),
                      surface('light',(.78,.86,.91)),chamfer=.015,axis=1)
        elif key == 'End_Wall':
            # Keep the original end-window footprint and replace its opaque backing with a frame.
            lo,hi = world_bounds(obj)
            for x0,x1,z0,z1 in [(lo.x,-.7,lo.z,hi.z),(.7,hi.x,lo.z,hi.z),
                                (-.7,.7,lo.z,2.2),(-.7,.7,3,hi.z)]:
                model.box((x0,lo.y,z0),(x1,hi.y,z1),style)
            outer = lo.y if lo.y<0 else hi.y
            a,b = sorted((outer,outer+(-.006 if outer<0 else .006)))
            for x0,x1,z0,z1 in [(-.728,-.7,2.172,3.028),(.7,.728,2.172,3.028),
                                (-.7,.7,2.172,2.2),(-.7,.7,3,3.028)]:
                model.box((x0,a,z0),(x1,b,z1),surface('trim',CHARCOAL))
            model.box((lo.x,a,1.887),(hi.x,b,2.019),surface('trim',TEAL))
        elif key in ('Seat_Back','Seat_Cushion'):
            model.part(obj,style,chamfer=.022,axis=1 if key=='Seat_Back' else 2)
        else:
            bevel = .022 if key in ('Roof','Carriage_Floor') else .014 if key=='Front_Headlamp' else 0
            model.part(obj,style,chamfer=bevel,axis=1 if key=='Front_Headlamp' else 2)
        if key == 'Window_Band':
            lo,hi = world_bounds(obj)
            length = hi.y-lo.y
            for j in (1,2,3):
                y = lo.y+length*j/4
                model.box((lo.x-.006,y-.012,lo.z),(hi.x+.006,y+.012,hi.z),
                          surface('trim',(.065,.080,.087)))
        if key == 'Lower_Wall':
            lo,hi = world_bounds(obj)
            x = hi.x if hi.x>0 else lo.x
            a,b = sorted((x,x+(.002 if x>0 else -.002)))
            model.box((a,lo.y,1.887),(b,hi.y,2.019),surface('trim',TEAL))
    for x in (-1,1):
        for y in (-3.4,3.4):
            x0,x1 = sorted((1.398*x,1.482*x))
            model.box((x0,y-.72,1.135),(x1,y+.72,1.2),surface('trim',GREY))
    for y in (-6,0,6):
        for x in (-.54,.54):
            model.box((x-.036,y-2.75,3.513),(x+.036,y+2.75,3.54),
                      surface('light',(.82,.89,.91)))
    # The handle profile and hanger proportions come from the gallery's ceiling handle generator.
    for y in (-8,-4.7,0,4.7,8):
        for x in (-.63,.63):
            for a,b,r in [
                ((x,y-.105,3.06),(x,y+.105,3.06),.019),
                ((x,y-.105,3.06),(x,y,3.23),.017),
                ((x,y+.105,3.06),(x,y,3.23),.017),
            ]:
                a,b = Vector(a),Vector(b)
                frame = Matrix.Translation(a) @ (b-a).to_track_quat('Z','Y').to_matrix().to_4x4()
                model.lathe(frame,[(0,r),((b-a).length,r)],5,surface('trim',(.80,.82,.78)),'body')
            model.box((x-.012,y-.023,3.21),(x+.012,y+.023,3.55),surface('trim',CHARCOAL))

def platform(model, objects):
    continuous = {'PLATFORM_Slab':'concrete','EDGE_Tactile':'trim','CANOPY_Roof':'roof','REAR_ServiceWall':'wall'}
    rib = next(obj for obj in objects if part_name(obj)=='TACTILE_Rib')
    for obj in objects:
        key = part_name(obj)
        if key in continuous:
            expand = Matrix.Diagonal((1,120/20.4 if key=='CANOPY_Roof' else 6,1,1))
            model.part(obj,sourced(continuous[key],obj),before=PLATFORM_ROTATION @ expand)
            if key=='EDGE_Tactile':
                model.box((-60,-2.464,1.15),(60,-2.417,1.157),sourced('trim',obj))
            continue
        style = sourced('seat' if key=='SEATING_Bench' else 'trim' if key=='TACTILE_Rib' else 'metal',obj)
        for offset in (-50,-30,-10,10,30,50):
            if key=='UNDERSTRUCTURE' and abs(obj.location.y)==9 and abs(offset+obj.location.y)<58:
                continue
            transform = PLATFORM_ROTATION @ Matrix.Translation((0,offset,0))
            if key=='TACTILE_Rib':
                model.part(obj,style,before=transform,skip=(0,2,4))
            else:
                hidden = (0,1) if key=='SEATING_Leg' else ()
                model.part(obj,style,before=transform,skip=hidden)
    for y in (-40,-20,0,20,40):
        for x in (-2.30,-2.20,-2.10):
            offset = Vector((x,y,1.18))-rib.matrix_world.translation
            model.part(rib,sourced('trim',rib),before=PLATFORM_ROTATION @ Matrix.Translation(offset),skip=(0,2,4))

def platform_door(model, objects):
    resize = Matrix.Diagonal((3/4.4,1,1,1))
    for obj in objects:
        key = part_name(obj)
        group = 'body'
        if obj.parent.name.startswith('MOVABLE_'):
            x = obj.matrix_world.translation.x
            group = 'leaf_1' if x<0 else 'leaf_2'
            sign = -1 if x<0 else 1
            model.pivots[group] = resize @ Vector((sign*.55,-.22,0))
            model.moves[group] = Vector((sign*1.10*3/4.4,0,0))
        material = ('glass' if 'Glass' in key else 'trim' if 'Warning' in key or 'WARNING' in key
                    else 'paint' if key=='HEADER_Service' else 'metal')
        if key.startswith('EDITABLE'):
            # Project the original lettering onto the actual outer header face.
            lo,hi = world_bounds(obj)
            model.cap_text(obj,sourced('plate',obj),resize @ Matrix.Translation((0,-.302-lo.y,0)))
        elif key in ('FRAME_Post','DOOR_Stile','DOOR_Rail'):
            lo,hi = world_bounds(obj)
            if key=='FRAME_Post':
                lo.z,hi.z = .0705,2.2995
            elif key=='DOOR_Stile':
                lo.z,hi.z = .1803,2.2197
            if group=='leaf_1':
                hi.x = min(hi.x,-.003)
            elif group=='leaf_2':
                lo.x = max(lo.x,.003)
            model.box(lo,hi,sourced(material,obj),group,resize)
        else:
            model.part(obj,sourced(material,obj,.40 if material=='glass' else 1),before=resize,
                       group=group,chamfer=.008 if material=='glass' else 0,axis=1)
            if key=='FIXED_Glass':
                lo,hi = world_bounds(obj)
                inner = lo.x if hi.x>0 else hi.x
                x0,x1 = sorted((inner,inner+(-.048 if inner>0 else .048)))
                metal = surface('metal',(.263,.330,.367))
                model.box((x0,-.035,.071),(x1,.064,2.299),metal,transform=resize)
                model.box((lo.x,-.035,.071),(hi.x,.064,lo.z+.002),metal,transform=resize)

def gate(model, objects):
    for obj in objects:
        key = part_name(obj)
        if key == 'FLAP':
            lo,hi = world_bounds(obj)
            for side,name in [(-1,'flap_L'),(1,'flap_R')]:
                x0,x1 = sorted((side*abs(lo.x),side*.009))
                model.pivots[name] = Vector((side*abs(lo.x),0,(lo.z+hi.z)/2))
                model.moves[name] = Vector((side*.251,0,0))
                model.box((x0,lo.y,lo.z),(x1,hi.y,hi.z),sourced('glass',obj,.48),name,chamfer=.018,axis=1)
        else:
            mat = {'CABINET':'metal','READER':'rubber','INDICATOR':'light'}[key]
            if key=='CABINET':
                model.source_mesh(obj,sourced(mat,obj))
            else:
                model.part(obj,sourced(mat,obj),chamfer=.005,axis=1 if key=='INDICATOR' else 2)

def station_sign(model, objects):
    for obj in objects:
        key = part_name(obj)
        if key.startswith('EDITABLE'):
            model.cap_text(obj,sourced('trim' if key.endswith('Direction') else 'plate',obj))
        elif key=='SIGN_Housing':
            model.source_mesh(obj,sourced('paint',obj))
        else:
            model.part(obj,sourced('metal',obj))

def seat(model, objects):
    for obj in objects:
        key = part_name(obj)
        if key=='SEAT_Back':
            model.beveled_faces(obj,sourced('seat',obj),.016,.024,1)
        elif key=='SEAT_Pan':
            model.part(obj,sourced('seat',obj),chamfer=.028,axis=0,corner_pair='low_u')
        elif key=='FOOT_Plate':
            model.part(obj,sourced('metal',obj),skip=(0,))
        else:
            model.rod(obj,sourced('metal',obj),4)

def train_door(model, objects):
    for obj in objects:
        key = part_name(obj)
        mat = ('glass' if key=='WINDOW_Pane' else 'trim' if key=='WARNING_Band'
               else 'rubber' if key=='DOOR_EdgeSeal' else 'paint' if key.startswith('DOOR_') else 'metal')
        style = sourced(mat,obj,.42 if mat=='glass' else 1)
        if key in ('FRAME_Side','DOOR_Stile','WINDOW_Pane'):
            lo,hi = world_bounds(obj)
            if key=='FRAME_Side':
                hi.z = 2.1398
            if key=='DOOR_Stile':
                lo.z,hi.z = .8902,1.8498
            if key=='WINDOW_Pane':
                lo.x,hi.x = lo.x-.021,hi.x+.021
                lo.z,hi.z = .889,1.851
            model.box(lo,hi,style,chamfer=.013 if key=='WINDOW_Pane' else 0,axis=1)
        else:
            model.part(obj,style,chamfer=.016 if key=='DOOR_Lower' else 0,axis=1,
                       skip=(1,) if key=='WARNING_Band' else ())

def handle(model, objects):
    for obj in objects:
        key = part_name(obj)
        if key=='STRAP_Hanger':
            lo,hi = world_bounds(obj)
            lo.z += .008
            model.box(lo,hi,sourced('rubber',obj),chamfer=.008,axis=1)
        else:
            mount = key.startswith('MOUNT')
            model.rod(obj,sourced('metal' if mount else 'trim',obj),8 if mount else 6)

def reader(model, objects):
    for obj in objects:
        key = part_name(obj)
        mat = {'CABLE_Entry':'rubber','READER_Enclosure':'rubber','RFID_Pad':'screen',
               'SPEAKER_Slot':'metal','STATUS_Indicator':'light','WALL_Backplate':'metal'}[key]
        style = sourced(mat,obj)
        if key=='SPEAKER_Slot':
            lo,hi = world_bounds(obj)
            model.front_quad(lo.x,hi.x,lo.y,lo.z,hi.z,style)
        elif key=='READER_Enclosure':
            model.beveled_faces(obj,style,.006,.007,1,corner=.004)
        elif key=='WALL_Backplate':
            model.beveled_faces(obj,style,.0035,.004,1)
        elif key=='RFID_Pad':
            model.beveled_faces(obj,style,.002,.0025,1)
        else:
            model.part(obj,style)

# Pinned front-face labels and compact equipment lettering.
from lettering import route_map, bus_display

BUILDERS = dict(zip(ASSETS,[carriage,platform,platform_door,gate,station_sign,
                           lambda model,objs: route_map(model,objs,sourced,world_bounds),seat,
                           train_door,handle,reader,
                           lambda model,objs: bus_display(model,objs,sourced,world_bounds)]))

def build(slugs):
    work = KIT/'.work'
    for slug in slugs:
        stem,budget = ASSETS[slug]
        source = original(slug)
        model = Model()
        BUILDERS[slug](model,load(source))
        totals = {group:{mat:len(tris) for mat,tris in mesh.items()} for group,mesh in model.meshes.items()}
        count = sum(sum(mesh.values()) for mesh in totals.values())
        print('BUILD',stem,count,totals,flush=True)
        if count>budget or sum(len(mesh) for mesh in totals.values())>16:
            raise ValueError(f'{stem}: {count} triangles, budget {budget}')
        path = KIT/(stem+'.glb')
        origin = GLB().write(model,path)
        (work/(stem+'-build.json')).write_text(json.dumps({
            'slug':slug,'originInBlenderMeters':origin,
            'source':str(source.relative_to(ROOT)),
            'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'candidateSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        },indent=2)+'\n')

if __name__=='__main__':
    build(sys.argv[sys.argv.index('--')+1:] or ASSETS)
