"""Additional real source views and assembly of imported committed GLBs."""
from pathlib import Path
import bpy,runpy,json,math,sys
from mathutils import Vector
root=Path(__file__).resolve().parent
helpers=runpy.run_path(str(root/'generate.py'));point_at=helpers['point_at']
for suffix,name,length in ([] if '--assembly-only' in sys.argv else helpers['SPECS']):
    slug='mall-glass-railing-'+suffix
    bpy.ops.wm.open_mainfile(filepath=str(root/'sources'/(slug+'.blend')))
    scene=bpy.context.scene;scene.cycles.samples=48
    for angle,loc in [('front',(0,5,1.8)),('rear',(-2.5,-5,2.3))]:
        scene.camera.location=loc;point_at(scene.camera,(0,0,.56))
        scene.render.filepath=str(root/'previews'/(slug+'-'+angle+'.png'))
        bpy.ops.render.render(write_still=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
layout=json.loads((root/'layouts.json').read_text())['examples'][1]
def imported_module(slug,module):
    before=set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(root/'exports'/(slug+'.glb')))
    imported=set(bpy.context.scene.objects)-before
    selected=next(o for o in imported if o.get('module')==module and (o.name.startswith(module)))
    keep={selected,*selected.children_recursive};world=selected.matrix_world.copy()
    selected.parent=None;selected.matrix_world=world
    for o in imported-keep:bpy.data.objects.remove(o,do_unlink=True)
    return selected
for i,p in enumerate(layout['posts']):
    o=imported_module('mall-glass-railing-post','MODULE_Post')
    o.location=(p[0],-p[2],p[1]);o.name='Assembled post '+str(i)
for i,link in enumerate(layout['infills']):
    o=imported_module(link['asset'],'MODULE_Infill');p=link['position']
    o.location=(p[0],-p[2],p[1]);o.rotation_mode='XYZ';o.rotation_euler.z=link['rotationY'];o.name='Assembled infill '+str(i)
helpers['studio'](4)
scene=bpy.context.scene;scene.camera.location=(6,6,5);point_at(scene.camera,(1.6,-1.1,.5));scene.camera.data.ortho_scale=5.7
scene.cycles.samples=48;scene.render.filepath=str(root/'previews/assembly-mixed-right-angle.png')
bpy.ops.render.render(write_still=True)
print('PASS rendered front/rear saved-source views and actual imported-GLB assembly')
