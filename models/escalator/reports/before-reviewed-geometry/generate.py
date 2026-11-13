"""Original static complete escalator V1 / ID004. Metres, Blender Z-up, -Y front.

This is deliberately a static, editable geometry study. It does not claim a
working step chain or matched-speed handrail animation.
"""
from pathlib import Path
import bpy, math, sys
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT_NAME = "ASSET_EscalatorV1_ID004"
SLUG = "escalator"
RISE, TREAD, WIDTH, LANDING, RAIL = 3.0, 0.2886751346, 1.0, 1.2, .9
RUN = RISE / math.tan(math.radians(30.0))
N = 18

def mat(name, colour, rough=.45, metal=0):
    m = bpy.data.materials.new(name); m.diffuse_color = (*colour, 1); m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value = (*colour, 1)
    p.inputs['Roughness'].default_value = rough; p.inputs['Metallic'].default_value = metal
    return m

def box(name, loc, dims, material, bevel=.01, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o=bpy.context.object; o.name=name; o.dimensions=dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True); o.data.materials.append(material)
    if bevel:
        b=o.modifiers.new('Editable rounded edges','BEVEL'); b.width=bevel; b.segments=2
    if parent: o.parent=parent
    return o

def cyl(name, loc, radius, depth, material, parent=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=depth, location=loc)
    o=bpy.context.object; o.name=name; o.data.materials.append(material)
    if parent: o.parent=parent
    return o

def beam(name, a, b, width, material, parent=None):
    mid=(Vector(a)+Vector(b))/2; length=(Vector(b)-Vector(a)).length
    o=box(name, mid, (width,width,length), material, width*.18, parent)
    o.rotation_euler=(Vector(b)-Vector(a)).to_track_quat('Z','Y').to_euler(); return o

def curve_rail(name, points, radius, material, parent):
    cu=bpy.data.curves.new(name,'CURVE'); cu.dimensions='3D'; cu.resolution_u=2; cu.bevel_depth=radius; cu.bevel_resolution=3
    sp=cu.splines.new('BEZIER'); sp.bezier_points.add(len(points)-1)
    for bp,p in zip(sp.bezier_points,points): bp.co=p; bp.handle_left_type='AUTO'; bp.handle_right_type='AUTO'
    o=bpy.data.objects.new(name,cu); bpy.context.scene.collection.objects.link(o); o.parent=parent; cu.materials.append(material); return o

def empty(name, parent, loc=(0,0,0)):
    o=bpy.data.objects.new(name,None); bpy.context.scene.collection.objects.link(o); o.parent=parent; o.location=loc; return o

def main():
    for d in ('sources','exports','previews','metadata','reports'): (HERE/d).mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True); s=bpy.context.scene
    s.unit_settings.system='METRIC'; s.unit_settings.scale_length=1
    root=bpy.data.objects.new(ROOT_NAME,None); s.collection.objects.link(root)
    steel=mat('Graphite structural steel',(.09,.12,.13),.36,.72); tread=mat('Brushed tread aluminium',(.42,.48,.49),.3,.65)
    edge=mat('Safety edge yellow',(.86,.55,.05),.4,.1); rail=mat('Black handrail elastomer',(.025,.03,.03),.24,.05)
    glass=mat('Opaque smoke guard',(.15,.2,.21),.38,.15); panel=mat('Maintenance panel',(.18,.22,.23),.42,.5)
    # Floor datum: lower landing is z=0; upper landing is z=3.0.
    box('LOWER_LANDING_DECK',(0,-RUN/2-LANDING/2,.035),(WIDTH,LANDING,.07),steel,.015,root)
    box('UPPER_LANDING_DECK',(0,RUN/2+LANDING/2,RISE+.035),(WIDTH,LANDING,.07),steel,.015,root)
    box('LOWER_COMB_PLATE',(0,-RUN/2+.035,.075),(WIDTH,.07,.03),tread,.006,root)
    box('UPPER_COMB_PLATE',(0,RUN/2-.035,RISE+.075),(WIDTH,.07,.03),tread,.006,root)
    # Independent step treads and risers; no joined or animated chain is implied.
    step_rise=RISE/N
    for i in range(N):
        y=-RUN/2 + (i+.5)*TREAD; z=(i+1)*step_rise
        box(f'STEP_{i+1:02d}_TREAD',(0,y,z),(WIDTH,TREAD*.94,.055),tread,.008,root)
        box(f'STEP_{i+1:02d}_RISER',(0,y-TREAD*.47,z-step_rise/2),(WIDTH,.035,step_rise),steel,.004,root)
        box(f'STEP_{i+1:02d}_EDGE',(0,y+TREAD*.41,z+.032),(WIDTH*.94,.018,.018),edge,.003,root)
    # Side guards, sloped trusses and a truthful static return enclosure.
    for x,side in [(-.62,'L'),(.62,'R')]:
        box(f'SIDE_GUARD_{side}_LOW',(x,-RUN/2-LANDING/2,.48),(.08,LANDING,.9),glass,.018,root)
        box(f'SIDE_GUARD_{side}_UP',(x,RUN/2+LANDING/2,RISE+.48),(.08,LANDING,.9),glass,.018,root)
        beam(f'TRUSS_{side}_TOP',(x,-RUN/2,.43),(x,RUN/2,RISE+.43),.08,steel,root)
        beam(f'TRUSS_{side}_BOTTOM',(x,-RUN/2,-.26),(x,RUN/2,RISE-.26),.08,steel,root)
        for j in range(0,7):
            t=j/6; y=-RUN/2+t*RUN; z=-.26+t*RISE
            beam(f'TRUSS_{side}_WEB_{j}',(x,y,z),(x,y+RUN/6,z+RISE/6),.045,steel,root)
        # Handrail is one coherent static path with rounded landing transitions.
        curve_rail(f'HANDRAIL_{side}',[(x,-RUN/2-LANDING+.12,1.36),(x,-RUN/2+.02,1.36),(x,RUN/2-.02,RISE+1.36),(x,RUN/2+LANDING-.12,RISE+1.36)],.075,rail,root)
        beam(f'BALUSTRADE_{side}',(x,-RUN/2,.65),(x,RUN/2,RISE+.65),.035,glass,root)
    # Return enclosure beneath the incline and a separately editable access panel.
    box('RETURN_ENCLOSURE',(0,0,-.52),(1.16,RUN,.42),steel,.025,root)
    box('MAINTENANCE_PANEL_OPENING',(0,-.25,-.295),(.58,.035,.28),panel,.01,root)
    box('MAINTENANCE_PANEL_SEPARATE',(0,-.25,-.155),(.48,.018,.22),panel,.012,root)
    for name,loc in [('CONNECTOR_LOWER',(0,-RUN/2-LANDING,0)),('CONNECTOR_UPPER',(0,RUN/2+LANDING,RISE)),('CONNECTOR_LEFT',(-WIDTH/2,0,0)),('CONNECTOR_RIGHT',(WIDTH/2,0,0))]: empty(name,root,loc)
    root['units']='metres'; root['asset_id']='ID004'; root['design_rise_m']=3.0; root['tread_width_m']=1.0; root['main_incline_degrees']=30.0; root['landing_run_m']=1.2; root['rail_height_above_tread_m']=.9
    root['mechanism_status']='NEEDS REVIEW: static geometry only; no operating step chain or matched-speed handrail animation is claimed.'
    root['orientation']='Blender Z-up, -Y front; exported glTF Y-up, +Z front.'
    # Source authoring scene only; export selection excludes studio objects and helpers.
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources/escalator.blend'))
    bpy.ops.object.select_all(action='DESELECT'); root.select_set(True); bpy.context.view_layer.objects.active=root
    for o in root.children_recursive: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(HERE/'exports/optimized.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True)
    if '--skip-render' not in sys.argv:
        s.render.engine='BLENDER_WORKBENCH'; s.render.resolution_x=768; s.render.resolution_y=768; s.render.resolution_percentage=100
        s.render.filepath=str(HERE/'previews/escalator.png'); bpy.ops.render.render(write_still=True)

if __name__=='__main__': main()
