"""Mechanical audit, Blender source and independently reimported GLB."""
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector

root = Path(__file__).resolve().parent
slug = 'pasar-dacing-steelyard-scale'
opts = set(sys.argv[sys.argv.index('--')+1:]) if '--' in sys.argv else set()
imported = '--reimport' in opts
if imported:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps=30
    bpy.ops.import_scene.gltf(filepath=str(root/'exports'/f'{slug}.glb'))
scene=bpy.context.scene
scene.render.fps=30
objects=bpy.data.objects
O=lambda n: objects[n]
beam=O('DACING_BEAM')
w=O('DACING_COUNTERWEIGHT')
pan=O('DACING_PAN_SWIVEL')
poise=O('DACING_POISE_SWIVEL')
sample=O('DACING_SAMPLE_MANGOES')
fixed=O('DACING_FIXED_FULCRUM_PIN')
stand=O('Rear support upright')
pan_mesh=O('Spun brass hanging produce pan')
sides=sorted((o for o in objects if o.name.startswith('Open sliding collar side wall')),
             key=lambda o:o.location.y)
assert len(sides)==2
lips=[o for o in objects if o.name.startswith('Open sliding collar upper/lower lip')]
assert len(lips)==2
ticks=[o for o in objects if o.name.startswith('Unitless ruled tick')]
surface=O('Inlaid front face for illustrative ticks')
shaft=O('Long asymmetrical steelyard beam')

assert w.parent==beam and pan.parent==beam and poise.parent==w and sample.parent==pan
assert len([o for o in objects if o.name.startswith('Unitless ruled tick')])==23
assert len([o for o in objects if o.name.startswith('Rigid-looking fine tension cable')])==3
assert len([o for o in objects if o.name.startswith('Riveted pan strap attachment')])==3
# Allow object-axis conversion in the importer: measure world response relative to exact frame zero.
vec=lambda x: x.matrix_world.translation
hold_base={}
base_pan=None
base_poise=None
base_sample=None
world_tables={}
stills={}
arc=[]
minbase=10
minpost=10
min_sleeve=10
max_joint=0
max_upright=0
max_shaft=0
stationary=0
for i in range(133):
    scene.frame_set(i//2,subframe=(i%2)/2)
    # Tail interpolation and NLA end must reach the same target as the settled pose.
    W=lambda obj,p: obj.matrix_world @ Vector(p)
    rel = beam.matrix_world.inverted() @ vec(w)
    left=beam.matrix_world.inverted() @ vec(pan)
    bearing=beam.matrix_world.inverted() @ vec(fixed)
    max_shaft=max(max_shaft,math.hypot(rel.y,rel.z))
    max_joint=max(max_joint,Vector((left.x+.198,left.y,left.z+.007)).length,bearing.length)
    assert math.hypot(rel.y,rel.z)<2e-6,(i,rel)
    assert Vector((left.x+.198,left.y,left.z+.007)).length<2e-6,(i,left)
    assert bearing.length<2e-6,(i,bearing)
    assert rel.x-.019>.103 and rel.x+.019 < .430, (i,rel)
    if arc:
        assert rel.x>=arc[-1]-2e-7, (i,rel.x,arc[-1])
    arc.append(rel.x)
    ib=beam.matrix_world.inverted()
    def bounds(o,j):
        xyz=[(ib @ o.matrix_world @ Vector(k))[j] for k in o.bound_box]
        return min(xyz),max(xyz)
    active_ticks=[o for o in ticks if abs((ib @ o.matrix_world.translation).x-rel.x)<.022]
    envelope=[shaft,surface,*active_ticks]
    lower,upper=sorted(sides,key=lambda o:(ib @ o.matrix_world.translation).y)
    left_gap=min(bounds(o,1)[0] for o in envelope)-bounds(lower,1)[1]
    right_gap=bounds(upper,1)[0]-max(bounds(o,1)[1] for o in envelope)
    bottom,top=sorted(lips,key=lambda o:(ib @ o.matrix_world.translation).z)
    bottom_gap=min(bounds(o,2)[0] for o in envelope)-bounds(bottom,2)[1]
    top_gap=bounds(top,2)[0]-max(bounds(o,2)[1] for o in envelope)
    clearance=min(left_gap,right_gap,bottom_gap,top_gap)
    min_sleeve=min(min_sleeve,clearance)
    assert clearance>.00084,(i,left_gap,right_gap,bottom_gap,top_gap)

    rot=pan.matrix_world.to_3x3()
    rop=poise.matrix_world.to_3x3()
    local=pan.matrix_world.inverted() @ vec(sample)
    if i==0:
        base_pan,base_poise,base_sample=rot.copy(),rop.copy(),local.copy()
        hold_base={o.name:o.matrix_world.copy() for o in (fixed,stand,O('Solid oiled display base'))}
    for a,b in ((rot,base_pan),(rop,base_poise)):
        rot_error=max(abs(a[h][k]-b[h][k]) for h in range(3) for k in range(3))
        max_upright=max(max_upright,rot_error)
        assert rot_error<2e-6,(i,rot_error)
    assert (local-base_sample).length<2e-6
    for o in (fixed,stand,O('Solid oiled display base')):
        err=max(abs(o.matrix_world[h][k]-hold_base[o.name][h][k]) for h in range(4) for k in range(4))
        stationary=max(stationary,err)
        assert err<2e-6
    # Mesh world bounds: the suspended assembly cannot reach the base or rear upright.
    bowl_z=min(W(pan_mesh,k).z for k in pan_mesh.bound_box)
    head=vec(fixed)
    pan_y = max(W(pan_mesh,k).y for k in pan_mesh.bound_box)
    ygap= min(W(stand,k).y for k in stand.bound_box) - pan_y
    xgap= min(W(stand,k).x for k in stand.bound_box) - max(W(pan_mesh,k).x for k in pan_mesh.bound_box)
    base_gap=bowl_z-max(W(O('Solid oiled display base'),k).z for k in O('Solid oiled display base').bound_box)
    assert base_gap > .40 and max(xgap,ygap)>.03,(i,base_gap,xgap,ygap)
    minbase=min(minbase,base_gap);minpost=min(minpost,max(xgap,ygap))
    # World hanger remains vertical; short arm rises, not counterweight endpoint drifting in space.
    assert vec(pan).z-head.z <= 1e-6
    s=math.degrees(math.atan2(-beam.matrix_world[2][0],beam.matrix_world[0][0]))
    if i in (0,61,110,132):
        stills[str(i/60)]={'beam_degrees':s,'weight_x_m':rel.x,'load_pivot_world_z_m':vec(pan).z}
    if i>=110:
        assert abs(s)<.001 and abs(rel.x-.361)<2e-6
assert abs(arc[0]-.126)<2e-6 and abs(arc[-1]-.361)<2e-6
assert abs(stills['0.0']['beam_degrees']+9)<.001
assert stills['2.2']['load_pivot_world_z_m']-stills['0.0']['load_pivot_world_z_m']>.030
print('DACING_MECHANICAL '+json.dumps({'phase':'reimport' if imported else 'source','samples':133,'frames':stills,
      'maximum_joint_error_m':max_joint,'maximum_slide_off_axis_m':max_shaft,'maximum_upright_matrix_error':max_upright,
      'stationary_max_matrix_delta':stationary,'min_pan_base_gap_m':minbase,'min_pan_post_gap_m':minpost,'min_moving_sleeve_envelope_gap_m':min_sleeve}))
