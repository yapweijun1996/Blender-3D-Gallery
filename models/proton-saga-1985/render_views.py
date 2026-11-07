"""Render the actual Blender scene with the gallery's established cameras."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
import bpy
from mathutils import Vector

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
parser=argparse.ArgumentParser()
parser.add_argument('--output',required=True)
parser.add_argument('--views',default='preview,view-rear-3q,view-front,view-rear,view-left,view-right')
parser.add_argument('--samples',type=int,default=48)
parser.add_argument('--width',type=int,default=1536)
parser.add_argument('--height',type=int,default=1024)
opts=parser.parse_args(args)
out=Path(opts.output).resolve();out.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene
camera=scene.camera
assert camera is not None and camera.type=='CAMERA','Missing scene camera'
scene.render.engine='CYCLES'
scene.cycles.samples=opts.samples
scene.cycles.use_denoising=True
scene.render.resolution_x=opts.width
scene.render.resolution_y=opts.height
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
views={'preview':(-9,-4,1.95),'view-rear-3q':(9,4,1.95),'view-front':(-9.5,0,1.12),'view-rear':(9.5,0,1.12),'view-left':(0,-30,2.4),'view-right':(0,30,2.4)}
report={}
for name in opts.views.split(','):
 if name not in views: raise ValueError(f'Unknown view {name}')
 camera.data.type='ORTHO' if name in ('view-left','view-right') else 'PERSP'
 camera.data.lens=75 if name=='view-rear-3q' else 94
 camera.data.ortho_scale=4.85
 camera.location=views[name]
 target=Vector((0,.35,.78)) if name=='preview' else Vector((0,0,.86))
 camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
 png=out/(name+'.png');webp=out/(name+'.webp');scene.render.filepath=str(png)
 start=time.monotonic();bpy.ops.render.render(write_still=True)
 subprocess.run(['/opt/homebrew/bin/cwebp','-quiet','-q','92',str(png),'-o',str(webp)],check=True)
 png.unlink()
 report[name]={'seconds':round(time.monotonic()-start,2),'bytes':webp.stat().st_size}
 print('RENDER_RESULT',name,json.dumps(report[name]),flush=True)
(out/'render-report.json').write_text(json.dumps({'samples':opts.samples,'width':opts.width,'height':opts.height,'views':report},indent=2)+'\n')
