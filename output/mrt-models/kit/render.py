"""Matched Cycles CPU views of the original and delivered binary glTFs."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
from build import ASSETS, KIT, PLATFORM_ROTATION, load, original
from geometry import bounds

TILE_W,TILE_H = 448,320
SAMPLES = 8
VIEWS = ('front','three-quarter','side','rear','elevated','detail')
ANGLES = [(0,-1,.01),(-1,-1.7,.55),(-1,0,.01),(0,1,.04),(.92,-1.36,1.3),(.78,.95,.35)]
PLATFORM_AXES = {'front':(0,-1,0),'side':(-1,0,0),'rear':(0,1,0)}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def points(objects):
    return [obj.matrix_world @ vertex.co for obj in objects for vertex in obj.data.vertices]

def aim(obj,target):
    obj.rotation_euler = (target-obj.location).to_track_quat('-Z','Y').to_euler()

def setup(center, span, bottom, studio_span, platform=False):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.cycles.device = 'CPU'
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.cycles.transparent_max_bounces = 12
    scene.world = bpy.data.worlds.new('Neutral studio')
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes['Background']
    background.inputs['Color'].default_value = (.76,.83,.94,1)
    background.inputs['Strength'].default_value = .47
    bpy.ops.mesh.primitive_plane_add(size=span*120,location=(center.x,center.y,bottom-span*.001))
    mat = bpy.data.materials.new('Review ground')
    mat.diffuse_color = (.32,.37,.43,1)
    bpy.context.object.data.materials.append(mat)
    for delta,energy,tint in [((-.8,-1.2,1.55),235,(1,.94,.85)),
                              ((1,-.12,1.05),125,(.84,.91,1)),
                              ((.25,1.2,1.65),175,(1,.97,.92))]:
        bpy.ops.object.light_add(type='SUN' if platform else 'AREA',
                                 location=center+Vector(delta)*studio_span)
        light = bpy.context.object
        if platform:
            light.data.energy = energy*.0025
            light.data.angle = .55
        else:
            light.data.energy = energy*studio_span**2
            light.data.shape = 'DISK'
            light.data.size = studio_span*1.65
        light.data.color = tint
        aim(light,center)
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.data.clip_end = max(100,span*120)
    scene.camera.data.clip_start = min(.015,span/400)
    scene.render.resolution_x = TILE_W
    scene.render.resolution_y = TILE_H
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    return scene

def orthographic(camera, vertices, delta):
    lo,hi = bounds(vertices)
    center = (lo+hi)/2
    direction = Vector(delta).normalized()
    rotation = (-direction).to_track_quat('-Z','Y')
    right,up = rotation @ Vector((1,0,0)),rotation @ Vector((0,1,0))
    uu,vv = [[axis.dot(v-center) for v in vertices] for axis in (right,up)]
    target = center+right*((min(uu)+max(uu))/2)+up*((min(vv)+max(vv))/2)
    camera.location = target+direction*(max(hi-lo)*2.7)
    camera.rotation_euler = rotation.to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 1.13*max(max(uu)-min(uu),(max(vv)-min(vv))*TILE_W/TILE_H)

def perspective(scene, position, target, lens):
    scene.camera.data.type = 'PERSP'
    scene.camera.location = position
    scene.camera.data.lens = lens
    aim(scene.camera,Vector(target))

def detail(scene, slug, vertices):
    if slug=='mrt-train-carriage':
        perspective(scene,(0,-9.27,2.37),(.04,2.3,2.48),18)
        bpy.ops.object.light_add(type='AREA',location=(0,-1.6,3.46))
        light = bpy.context.object
        light.data.energy = 84
        light.data.shape = 'RECTANGLE'
        light.data.size = .40
        light.data.size_y = 6
    elif slug=='mrt-platform':
        perspective(scene,(-6,-3.8,2.5),(4,.25,2.67),24)
    else:
        orthographic(scene.camera,vertices,ANGLES[-1])

def orient(slug, origin, candidate):
    root_objects = [obj for obj in bpy.context.scene.objects if obj.parent is None]
    if candidate:
        for obj in root_objects:
            obj.location += Vector(origin)
    elif slug=='mrt-platform':
        for obj in root_objects:
            obj.matrix_world = PLATFORM_ROTATION @ obj.matrix_world
    bpy.context.view_layer.update()

def sheet(tiles, path):
    layout = '|'.join(f'{(i%3)*(TILE_W+4)}_{(i//3)*(TILE_H+4)}' for i in range(12))
    args = ['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y']
    for tile in tiles:
        args += ['-threads','1','-i',str(tile)]
    args += ['-filter_complex_threads','1','-filter_complex',f'xstack=inputs=12:layout={layout}:fill=0x263138',
             '-frames:v','1','-threads','1',str(path)]
    subprocess.run(args,check=True)

def render(slug, candidate_only=False):
    stem = ASSETS[slug][0]
    reference,candidate = original(slug),KIT/(stem+'.glb')
    evidence = json.loads((KIT/'.work'/(stem+'-build.json')).read_text())
    assert evidence['sourceSha256']==digest(reference) and evidence['candidateSha256']==digest(candidate)
    origin = evidence['originInBlenderMeters']
    work = KIT/'.work'/stem
    work.mkdir(exist_ok=True)
    snapshots = {}
    for label,path in [('original',reference),('kit',candidate)]:
        objects = load(path)
        orient(slug,origin,label=='kit')
        snapshots[label] = points(objects)
    shared = snapshots['original'] + snapshots['kit']
    lo,hi = bounds(shared)
    center = (lo+hi)/2
    studio_span = 18 if slug=='mrt-platform' else max(hi-lo)
    for label,path in [('original',reference),('kit',candidate)]:
        if candidate_only and label=='original':
            continue
        load(path)
        orient(slug,origin,label=='kit')
        scene = setup(center,max(hi-lo),lo.z,studio_span,platform=slug=='mrt-platform')
        vertices = snapshots[label] if slug in ('mrt-platform','mrt-platform-screen-door') else shared
        for index,view in enumerate(VIEWS):
            if view=='detail':
                detail(scene,slug,vertices)
            else:
                framing = snapshots['original'] if slug=='mrt-platform' and view=='front' else vertices
                angle = PLATFORM_AXES.get(view,ANGLES[index]) if slug=='mrt-platform' else ANGLES[index]
                orthographic(scene.camera,framing,angle)
            scene.render.filepath = str(work/f'{label}-{view}.png')
            bpy.ops.render.render(write_still=True)
    comparisons = KIT/'comparisons'
    comparisons.mkdir(exist_ok=True)
    path = comparisons/(stem+'.png')
    tiles = [work/f'{label}-{view}.png' for start in (0,3) for label in ('original','kit')
             for view in VIEWS[start:start+3]]
    sheet(tiles,path)
    evidence.update(sheet=str(path.relative_to(KIT)),sheetSha256=digest(path),views=VIEWS,
                    layout=['original front / three-quarter / side','kit front / three-quarter / side',
                            'original rear / elevated / detail','kit rear / elevated / detail'],
                    renderer=f'Blender {bpy.app.version_string} Cycles CPU',threads=2,samples=SAMPLES,
                    tilePixels=[TILE_W,TILE_H])
    (comparisons/(stem+'.json')).write_text(json.dumps(evidence,indent=2)+'\n')
    print('SHEET',stem,flush=True)

if __name__=='__main__':
    args = sys.argv[sys.argv.index('--')+1:]
    for slug in [arg for arg in args if arg!='--candidate-only'] or ASSETS:
        render(slug,'--candidate-only' in args)
