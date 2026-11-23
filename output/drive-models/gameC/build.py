"""Build set C from the original gallery GLBs without modifying the originals."""
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import math
import sys

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT))

import bpy
from mathutils import Matrix, Vector

from mesh_tools import (
    BinaryMesh, box_reduction, compact, emit_group, extents, fit, load,
    torus_from_source, beveled_hub, radial_spokes, wheel_id,
)

REPO = OUT.parents[2]
VEHICLES = {
    'ambulance': ('ambulance', 'optimized.glb', None, 5000),
    'school_bus': ('school-bus', 'optimized.glb', None, 6000),
    'taxi': ('hatchback-car', 'optimized.glb', None, 4800),
    'police': ('hatchback-car', 'optimized.glb', None, 5000),
    'bus_double': ('singapore-public-bus', 'singapore-public-bus.glb', 12, 8000),
    'lorry': ('cargo-truck', 'cargo-truck.glb', None, 5500),
}
WHEELS = ('wheel_FL', 'wheel_FR', 'wheel_RL', 'wheel_RR')
PAINT = {
    'ambulance': 'Medical concept white', 'school_bus': 'School yellow',
    'taxi': 'Original teal paint', 'police': 'Original teal paint',
    'bus_double': 'Palm green', 'lorry': 'Muted teal',
}
# Linear RGB, with a single uniform paint factor for each vehicle.
TAXI_BLUE = (.014, .135, .40)
POLICE_WHITE = (.79, .83, .86)
STRIPE_BLUE = (.011, .097, .32)
STRIPE_ORANGE = (.92, .26, .026)
DARK = (.032, .040, .045)
IVORY = (.82, .91, .96)


@dataclass
class Part:
    obj: object
    transform: object
    slot: str
    rgba: tuple
    metallic: float
    roughness: float
    wheel: str | None


def base_name(obj):
    return obj.name.split('.')[0].lower()


def solid(name, loc, dims, rgb, slot, bevel=0, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.rotation_euler = rotation
    if bevel:
        modifier = obj.modifiers.new('One-segment edge chamfer', 'BEVEL')
        modifier.width = bevel
        modifier.segments = 1
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*rgb, 1)
    shader.inputs['Roughness'].default_value = .42
    obj.data.materials.append(mat)
    obj['slot'] = slot
    return obj


def preserve_body_details(objects, vehicle):
    if vehicle == 'ambulance':
        for obj in objects:
            name = base_name(obj)
            if name == 'roof_beacon':
                obj.location.y += .41
            elif name == 'headlight':
                obj.location.y -= .110
            elif name == 'rear_doorwindow':
                obj.location.y += .046
        for x in (-.72,.72):
            objects.append(solid('Ambulance_headlamp_gasket',(x,-2.721,1.16),
                                 (.354,.023,.234),DARK,'trim',.008))
        for x in (-.92,.92):
            objects.append(solid('Ambulance_tail_lamp',(x,2.756,1.12),(.102,.035,.22),
                                 (.63,.026,.018),'light',.014))
    elif vehicle == 'school_bus':
        label = next(o for o in objects if base_name(o) == 'school_label')
        label.location.z -= .052
        label.location.y -= .043
        glass = solid('Driver_quarter_window',(-1.15,-2.92,2.15),(.025,1.10,1.10),
                      (0,0,0),'glass')
        windscreen = next(o for o in objects if base_name(o) == 'front_windscreen')
        glass.data.materials[0] = windscreen.data.materials[0]
        objects.append(glass)
        for y in (-3.48,-2.34):
            objects.append(solid('Driver_quarter_post',(-1.15,y,2.15),(.067,.062,1.72),
                                 (0,0,0),'paint',.004))
        for x in (-.492,.492):
            objects.append(solid('Emergency_door_jamb',(x,3.566,1.985),(.125,.080,1.80),
                                 (0,0,0),'paint',.005))
    return objects


def car_conversion(objects, vehicle):
    roof = next(o for o in objects if base_name(o) == 'roof')
    _, upper = extents([roof.matrix_world @ v.co for v in roof.data.vertices])
    z = float(upper[2])
    for side in (-1,1):
        objects.append(solid('Door_roof_weatherstrip',(side*.817,.165,1.514),
                             (.142,.984,.024),DARK,'trim',.004))
    if vehicle == 'taxi':
        objects += [
            solid('Taxi_sign_mount',(0,.22,z+.014),(.59,.235,.032),DARK,'trim',.010),
            solid('Taxi_sign_case',(0,.22,z+.076),(.57,.215,.104),(.73,.78,.79),'trim',.019),
            solid('taxi_lit_front',(0,.110,z+.077),(.48,.009,.065),(.70,.89,.98),'light',.004),
            solid('taxi_lit_rear',(0,.330,z+.077),(.48,.009,.065),(.70,.89,.98),'light',.004),
        ]
        # Recessed-style dark glyphs over each lit panel.
        glyphs = (
            ('111','010','010','010','010'),
            ('010','101','111','101','101'),
            ('101','101','010','101','101'),
            ('111','010','010','010','111'),
        )
        for side in (-1,1):
            vertices, faces = [], []
            for i, glyph in enumerate(glyphs):
                for row, line in enumerate(glyph):
                    for col, cell in enumerate(line):
                        if cell != '1':
                            continue
                        x = -side*((i-1.5)*.084+(col-1)*.014)
                        y = .22+side*.116
                        height = z+.104-row*.013
                        start = len(vertices)
                        vertices.extend((x+dx,y,height+dz) for dx,dz in
                                        ((-.007,-.0065),(.007,-.0065),(.007,.0065),(-.007,.0065)))
                        order = (0,1,2,3) if side < 0 else (3,2,1,0)
                        faces.append(tuple(start+j for j in order))
            label = solid('Taxi_sign_lettering',(0,0,0),(1,1,1),DARK,'trim')
            old_mesh = label.data
            mesh = bpy.data.meshes.new('TAXI glyphs')
            mesh.from_pydata(vertices,[],faces)
            mesh.update()
            mesh.materials.append(old_mesh.materials[0])
            label.data = mesh
            bpy.data.meshes.remove(old_mesh)
            objects.append(label)
    else:
        objects += [
            solid('Police_bar_mount',(0,.24,z+.015),(.97,.17,.035),DARK,'trim',.010),
            solid('Police_bar_housing',(0,.24,z+.044),(1.10,.222,.048),DARK,'trim',.018),
            solid('police_lamp_blue',(-.323,.24,z+.078),(.428,.207,.060),(.035,.22,.97),'light',.018),
            solid('police_lamp_red',(.323,.24,z+.078),(.428,.207,.060),(.97,.049,.055),'light',.018),
            solid('Police_bar_bridge',(0,.24,z+.075),(.204,.185,.054),(.20,.25,.30),'trim',.012),
        ]
        for side in (-1,1):
            # Follow the existing door plane and stop short of each panel gap.
            x = side*.905
            objects.extend((
                solid('Police_door_stripe',(x,.054,.957),(.005,1.105,.082),STRIPE_BLUE,'trim'),
                solid('Police_door_pinstripe',(x,.054,.902),(.005,1.105,.022),STRIPE_ORANGE,'trim'),
                solid('Police_quarter_stripe',(side*.821,1.00,.956),(.006,.65,.082),STRIPE_BLUE,'trim'),
                solid('Police_quarter_pinstripe',(side*.821,1.00,.901),(.006,.65,.022),STRIPE_ORANGE,'trim'),
            ))
    return objects


def bus_conversion(objects, scale):
    # Recover standing headroom on both decks while retaining the gallery
    # wheel arches, entry-door layout, glazing band and green/white livery.
    for obj in objects:
        if wheel_id(obj):
            continue
        transform = obj.matrix_world.copy()
        obj.parent = None
        obj.animation_data_clear()
        obj.matrix_world = transform
        obj.data = obj.data.copy()
        inverse = transform.inverted()
        for v in obj.data.vertices:
            p = transform @ v.co
            p.z -= .55 * max(0, p.z-1.20)/2
            v.co = inverse @ p
    def add(name, loc, dims, rgb, slot, bevel=0):
        objects.append(solid(name, loc, dims, rgb, slot, bevel))

    teal = (.0212,.1095,.1361)
    white = (.92,.94,.93)
    green = (.0467,.1651,.0369)
    # Existing roof becomes the inter-deck floor. The upper windows share the
    # lower deck's teal shade and white posts, with a thinner roof cap.
    add('Upper_roof',(0,.02,4.4/scale-.073),(2.52,11.91,.146),white,'trim',.033)
    for side in (-1,1):
        x = side*1.225
        add('Upper_lower_rail',(x,.02,2.90),(.087,11.92,.51),green,'paint',.014)
        add('Upper_header',(x,.02,4.164),(.089,11.92,.39),white,'trim',.014)
        for i in range(8):
            y = .02-5.96+(i+.5)*11.92/8
            add('Upper_side_glass',(x,y,3.57),(.046,1.41,.88),teal,'window',.011)
        for i in range(9):
            y = .02-5.96+i*11.92/8
            add('Upper_post',(x,y,3.57),(.086,.087,.889),white,'trim')
    for y in (-5.94,5.98):
        add('Upper_end_glazing',(0,y,3.57),(2.34,.06,.88),teal,'window',.015)
        add('Upper_end_header',(0,y,4.164),(2.47,.09,.39),white,'trim',.025)
        add('Upper_end_lower',(0,y,2.90),(2.47,.082,.51),green,'paint',.025)
        for x in (-1.20,1.20):
            add('Upper_corner_post',(x,y,3.57),(.10,.09,.89),white,'trim',.013)
    for x in (-.86,.86):
        add('Upper_front_marker',(x,-5.995,4.08),(.21,.028,.073),IVORY,'light',.010)
        add('Upper_rear_marker',(x,6.035,4.08),(.21,.028,.073),(.58,.028,.022),'light',.010)
        add('Lower_rear_lamp',(x,6.027,1.1),(.24,.04,.21),(.67,.023,.020),'light',.018)
    return objects


def tipper_conversion(objects):
    # Keep the cab and original cargo floor plan, with a lowered open steel
    # tub, tapered walls, external stiffeners and a rear dump hinge.
    objects = [o for o in objects if not base_name(o).startswith(
        ('cargo_', 'loading_door', 'door_lockbar'))]
    steel = (.32,.37,.38)
    inside = (.22,.26,.27)
    locked = (.08,.11,.115)

    def add(name, loc, dims, color, slot='metal', bevel=.010, rotation=(0,0,0)):
        objects.append(solid(name,loc,dims,color,slot,bevel,rotation))

    add('Tipper_underframe',(0,1.29,1.01),(1.54,6.29,.19),locked,'trim')
    add('Tipper_floor',(0,1.29,1.182),(2.34,6.36,.16),inside)
    for side in (-1,1):
        add('Tipper_side_wall',(side*1.211,1.274,1.766),(.085,6.36,1.08),steel,
            rotation=(0,side*.112,0))
        add('Tipper_top_rail',(side*1.266,1.274,2.30),(.119,6.45,.115),steel)
        add('Tipper_lower_rail',(side*1.148,1.274,1.26),(.128,6.44,.13),locked,'trim')
        for y in (-1.80,-.77,.28,1.33,2.38,3.43,4.44):
            add('Tipper_external_rib',(side*1.263,y,1.78),(.088,.13,1.046),steel,
                rotation=(0,side*.112,0))
        add('Tipper_tailgate_pin',(side*1.204,4.48,2.22),(.16,.14,.14),locked,'trim')
        add('Tipper_rear_lamp',(side*.85,4.545,.92),(.29,.052,.125),(.64,.033,.025),'light')
    add('Tipper_headboard',(0,-1.86,1.94),(2.46,.13,1.47),steel)
    add('Tipper_headboard_cap',(0,-1.86,2.674),(2.51,.185,.104),steel)
    add('Tipper_tailgate',(0,4.47,1.776),(2.39,.103,1.05),steel)
    for x in (-.77,0,.77):
        add('Tailgate_stiffener',(x,4.534,1.77),(.12,.077,1.02),locked,'trim')
    add('Tailgate_sill',(0,4.528,1.234),(2.36,.14,.117),locked,'trim')
    add('Rear_underrun_bar',(0,4.43,.75),(2.24,.17,.14),locked,'trim')
    add('Tipper_hydraulic_body',(0,-1.02,1.02),(.23,1.47,.18),locked,'trim',
        rotation=(.19,0,0))
    return objects


def part_for(obj, vehicle):
    name = base_name(obj)
    material, = obj.data.materials
    shader = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    rgba = tuple(shader.inputs['Base Color'].default_value[:3])+(shader.inputs['Alpha'].default_value,)
    metallic = shader.inputs['Metallic'].default_value
    roughness = shader.inputs['Roughness'].default_value
    wheel = wheel_id(obj)
    if wheel:
        slot = 'tire' if name.startswith('tyre') else 'metal'
    elif 'slot' in obj:
        slot = obj['slot']
    elif name.startswith(('headlight','front_headlamp','tail_light','roof_beacon')):
        slot = 'light'
    elif name.startswith(('plate_', 'editable_label', 'school_label')):
        slot = 'plate'
    elif any(t in name for t in ('glass','pane','windscreen','window','glaz')) and not any(
        t in name for t in ('frame','pillar','post')):
        slot = 'glass' if rgba[3] < .999 else 'window'
    elif material.name == PAINT[vehicle] and not name.startswith('seat'):
        slot = 'paint'
    elif metallic >= .2 or material.name in ('Steel','Satin metal'):
        slot = 'metal'
    else:
        slot = 'trim'
    if slot == 'paint' and vehicle in ('taxi','police'):
        rgba = (*(TAXI_BLUE if vehicle == 'taxi' else POLICE_WHITE),1)
    transform = obj.matrix_world.copy()
    if wheel and name.startswith('rim_spoke_'):
        pivot = obj.parent.matrix_world.translation
        if pivot.x < 0:
            transform = (Matrix.Translation(pivot) @ Matrix.Rotation(math.pi,4,'Z')
                         @ Matrix.Translation(-pivot) @ transform)
    return Part(obj,transform,slot,rgba,metallic,roughness,wheel)


def geometry(part, vehicle):
    obj = part.obj
    mesh = obj.data
    name = base_name(obj)
    mesh.calc_loop_triangles()
    count = len(mesh.loop_triangles)
    if 'slot' in obj:
        return mesh
    if part.slot == 'tire':
        steps = 20 if vehicle in ('taxi','police') else 24
        return torus_from_source(mesh,steps,(0,1,2,4,6,7))
    if name == 'rim_spokes':
        return radial_spokes(obj)
    if name == 'hub':
        return beveled_hub(mesh,16 if vehicle in ('taxi','police') else 20)
    if name in ('steering_wheel','interior_steering'):
        return torus_from_source(mesh,12,(0,2,4,6))
    if name == 'editable_label_bus':
        return compact(obj,460)
    if count == 188:
        return compact(obj,46)
    if name.startswith('body_wheelarchsill'):
        return compact(obj,190)
    if count != 108 or (vehicle in ('taxi','police') and name.startswith(
        ('door_lower', 'door_clearpane', 'rear_quarter'))):
        return mesh
    detail = part.slot in ('paint','light','plate') or name.startswith(
        ('bumper','door_handle','mirror','tail_light','passenger_roof'))
    return box_reduction(mesh, chamfer=detail)


def material_table(parts, vehicle):
    table = {}
    groups = defaultdict(list)
    for part in parts:
        groups[part.slot].append(part)
    for name, subset in groups.items():
        source = subset[0]
        if name == 'paint':
            source = next(p for p in subset if 'slot' not in p.obj)
        roughness = {'glass': .18, 'window': .25, 'trim': .62, 'metal': .45, 'light': .25}
        metallic = {'metal': .35, 'window': .10, 'glass': 0, 'trim': 0, 'light': 0}
        factors = {
            'roughnessFactor': roughness.get(name,source.roughness),
            'metallicFactor': metallic.get(name,source.metallic),
        }
        if name in ('paint','tire'):
            factors['baseColorFactor'] = source.rgba
        mat = {'name': name, 'pbrMetallicRoughness': factors, 'doubleSided': True}
        if name == 'glass':
            mat['alphaMode'] = 'BLEND'
        if name == 'light':
            mat['emissiveFactor'] = [.035,.035,.035] if vehicle in ('taxi','police') else [.005,.005,.005]
            if vehicle == 'police':
                mat['extras'] = {'lamps':['police_lamp_blue','police_lamp_red']}
            if vehicle == 'taxi':
                mat['extras'] = {'lit_panels':['taxi_lit_front','taxi_lit_rear']}
        table[name] = mat
    return table


def build(vehicle):
    slug, filename, length, budget = VEHICLES[vehicle]
    objects = load(REPO/'models'/slug/'exports'/filename)
    if vehicle in ('ambulance','school_bus'):
        objects = preserve_body_details(objects,vehicle)
    elif vehicle in ('taxi','police'):
        objects = car_conversion(objects,vehicle)
    elif vehicle == 'bus_double':
        # Top markers stay inside the bumper-controlled length.
        objects = bus_conversion(objects,fit(objects,length)[1])
    elif vehicle == 'lorry':
        objects = tipper_conversion(objects)
    bpy.context.view_layer.update()
    center, scale = fit(objects,length)
    parts = [part_for(o,vehicle) for o in objects]
    materials = material_table(parts,vehicle)
    glb = BinaryMesh(materials)
    totals = {}
    for name in ('body', *WHEELS):
        subset = [p for p in parts if (p.wheel or 'body') == name]
        pivot = Vector()
        if name != 'body':
            tire, = [p for p in subset if p.slot == 'tire']
            pivot = (tire.obj.parent.matrix_world.translation-center)*scale
        totals[name] = emit_group(glb,name,subset,[geometry(p,vehicle) for p in subset],
                                  center,scale,pivot)
    triangle_count = sum(totals.values())
    path = OUT/f'{vehicle}_hd.glb'
    glb.write(path)
    print('BUILD',vehicle,totals,triangle_count,path.stat().st_size,list(materials),flush=True)
    assert triangle_count <= budget and path.stat().st_size <= 400_000


if __name__ == '__main__':
    for key in sys.argv[sys.argv.index('--')+1:] or VEHICLES:
        build(key)
