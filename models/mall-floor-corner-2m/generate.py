"""Build the cut terrazzo corner from the saved 2 m straight module."""
import argparse
import math
import struct
import sys
import tempfile
import zlib
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'mall-floor-corner-2m'
SOURCE = HERE / 'sources' / f'{SLUG}.blend'
BASE = 'mall-floor-module-2m'
STOPS = (.025, .053, .103, .117)
GOLD_X = (181, 153, 103)
GOLD_Z = (170, 139, 92)
TINT = (.29, .41, .31)  # Linear reflectance multiplier for the smoked stone.
TOP = .1


def linear(values):
    values = np.asarray(values) / 255.
    return np.where(values <= .04045, values / 12.92, ((values+.055)/1.055)**2.4)


def srgb(linear_values):
    return 255 * np.where(linear_values <= .0031308, linear_values*12.92,
                          1.055*linear_values**(1/2.4)-.055)


def material(name, rgb, roughness, metal=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*linear(rgb), 1)
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = mat.diffuse_color
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metal
    return mat


def pixels(image):
    buffer = np.empty(image.size[0]*image.size[1]*4, dtype=np.float32)
    image.pixels.foreach_get(buffer)
    return buffer.reshape(image.size[1],image.size[0],4)[:,:,:3] * 255


def packed_image(name, data, color_space):
    height, width = data.shape[:2]
    def chunk(tag, payload):
        return struct.pack('>I',len(payload)) + tag + payload + struct.pack('>I',zlib.crc32(tag+payload))
    rgb = np.uint8(np.clip(np.rint(data[::-1]),0,255))
    scanlines = b''.join(b'\x00'+row.tobytes() for row in rgb)
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR',struct.pack('>2I5B',width,height,8,2,0,0,0)) +
           chunk(b'IDAT',zlib.compress(scanlines,9))+chunk(b'IEND',b''))
    with tempfile.TemporaryDirectory() as directory:
        file = Path(directory)/(name+'.png')
        file.write_bytes(png)
        image = bpy.data.images.load(str(file))
        image.colorspace_settings.name = color_space
        image.pack()
        image.filepath = '//'+file.name
    return image


def surface_uv(x, y):
    # A continuous cut strip has its own phase, independent of the grid joints.
    return ((x+1)/.596+.23) % 1, ((y+1)/.596+.41) % 1


def distant_material(original, stone):
    base_image = next(n.image for n in original.node_tree.nodes if n.type == 'TEX_IMAGE')
    rgb = pixels(base_image)
    pattern = pixels(stone)
    # Use the straight module's 488px atlas window, including its padded edge.
    yy,xx = np.indices(rgb.shape[:2])
    color = np.zeros_like(rgb)
    orm = np.zeros_like(rgb)
    for sx,sy in ((.25,.25),(.75,.25),(.25,.75),(.75,.75)):
        x = np.clip((xx+sx-8)/488,0,1)*2-1
        y = np.clip((yy+sy-16)/488,0,1)*2-1
        d = np.minimum(1-x,1+y)
        band = ((d>=STOPS[0]) & (d<=STOPS[1])) | ((d>=STOPS[2]) & (d<=STOPS[3]))
        green = (d>STOPS[1]) & (d<STOPS[2])
        # The first eight atlas rows contain the underside and perimeter swatches.
        band &= yy>=8
        green &= yy>=8
        u,v = surface_uv(x,y)
        chips = pattern[(v*stone.size[1]).astype(int),(u*stone.size[0]).astype(int)]
        tinted = srgb(linear(chips)*TINT)
        paint = np.where(green[:,:,None],tinted,rgb)
        gold = np.where((x>=-y)[:,:,None],GOLD_X,GOLD_Z)
        color += np.where(band[:,:,None],gold,paint)/4
        orm[:,:,0] += 255/4
        orm[:,:,1] += np.where(band,.33,np.where(green,.47,.37))*255/4
        orm[:,:,2] += band*.69*255/4
    mat = material('Distant corner finish',(255,255,255),1)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    color_tex = nodes.new('ShaderNodeTexImage')
    color_tex.image = packed_image('Corner finished surface',color,'sRGB')
    links.new(color_tex.outputs['Color'],nodes['Principled BSDF'].inputs['Base Color'])
    response = nodes.new('ShaderNodeTexImage')
    response.image = packed_image('Corner material response',orm,'Non-Color')
    channels = nodes.new('ShaderNodeSeparateColor')
    links.new(response.outputs['Color'],channels.inputs['Color'])
    links.new(channels.outputs['Green'],nodes['Principled BSDF'].inputs['Roughness'])
    links.new(channels.outputs['Blue'],nodes['Principled BSDF'].inputs['Metallic'])
    return mat


def cut_corner(obj, inlays):
    mesh = obj.data
    start = len(mesh.materials)
    for mat in inlays:
        mesh.materials.append(mat)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    def cut(point, normal, geometry):
        bmesh.ops.bisect_plane(bm,geom=geometry,dist=0.0000002,plane_co=point,plane_no=normal)
    for distance in STOPS:
        cut((1-distance,0,0),(1,0,0),list(bm.verts)+list(bm.edges)+list(bm.faces))
        cut((0,-1+distance,0),(0,1,0),list(bm.verts)+list(bm.edges)+list(bm.faces))
    # The segment ends exactly at the outer and inner corners of the border.
    # Cutting only this quadrant avoids an extra diagonal across the ivory field.
    quadrant = [f for f in bm.faces if min(v.co.x for v in f.verts) >= 1-STOPS[-1]-1e-6
                and max(v.co.y for v in f.verts) <= -1+STOPS[-1]+1e-6]
    qedges = {e for f in quadrant for e in f.edges}
    qverts = {v for e in qedges for v in e.verts}
    cut((0,0,0),(1,1,0),list(qverts)+list(qedges)+quadrant)
    uv = bm.loops.layers.uv.active
    for face in bm.faces:
        if not all(abs(v.co.z-TOP)<1e-6 for v in face.verts): continue
        c = face.calc_center_median()
        d = min(1-c.x,1+c.y)
        if STOPS[0] < d < STOPS[1] or STOPS[2] < d < STOPS[3]:
            face.material_index = start + (0 if c.x > -c.y else 1)
        elif STOPS[1] < d < STOPS[2]:
            face.material_index = start+2
            for loop in face.loops:
                x,y,_ = loop.vert.co
                # Leave UVs unwrapped so interpolation crosses repeat boundaries correctly.
                loop[uv].uv = ((x+1)/.596+.23,(y+1)/.596+.41)
    # Remove redundant splits within each metal arm. Different materials retain
    # the physical diagonal edge shared by the orthogonal cuts.
    metal = {start,start+1}
    interior = [e for e in bm.edges if len(e.link_faces)==2 and
                e.link_faces[0].material_index in metal and
                e.link_faces[0].material_index==e.link_faces[1].material_index]
    bmesh.ops.dissolve_edges(bm,edges=interior,use_verts=False)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    # Named editing selections make both strips and the stone separately selectable.
    for i,name in enumerate(('Right champagne arm','Front champagne arm','Eucalyptus terrazzo ribbon')):
        group = obj.vertex_groups.new(name=name)
        verts = {v for face in mesh.polygons if face.material_index==start+i for v in face.vertices}
        group.add(list(verts),1,'REPLACE')


def build(source):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC'
    with bpy.data.libraries.load(str(source)) as (library, objects):
        objects.objects = [f'MODULE_StraightFloor_L{i}' for i in range(3)]
    modules = objects.objects
    for obj in modules:
        bpy.context.scene.collection.objects.link(obj)
    original_finish = modules[0].data.materials[0]
    tex = next(n.image for n in original_finish.node_tree.nodes if n.type=='TEX_IMAGE')
    smoked = original_finish.copy()
    smoked.name = 'Cut eucalyptus terrazzo'
    nodes,links = smoked.node_tree.nodes,smoked.node_tree.links
    mix = nodes.new('ShaderNodeMix')
    mix.data_type='RGBA'
    mix.blend_type='MULTIPLY'
    mix.inputs[0].default_value=1
    mix.inputs[7].default_value=(*TINT,1)
    links.new(next(n for n in nodes if n.type=='TEX_IMAGE').outputs['Color'],mix.inputs[6])
    links.new(mix.outputs[2],nodes['Principled BSDF'].inputs['Base Color'])
    nodes['Principled BSDF'].inputs['Roughness'].default_value=.47
    inlays = [material('Brushed champagne right',GOLD_X,.33,.69),
              material('Brushed champagne front',GOLD_Z,.33,.69),smoked]
    for level,obj in enumerate(modules):
        obj.name=obj.data.name=f'MODULE_CornerFloor_L{level}'
        obj['registry_id']='MALL-STR-002'
        obj['outside_edges']='glTF +X and +Z'
        obj['border_stops_m']=list(STOPS)
        if level < 2:
            cut_corner(obj,inlays)
        else:
            obj.data.materials[0] = distant_material(obj.data.materials[0],tex)
        obj.hide_set(level != 0)
        obj.hide_render=level != 0
    bpy.context.view_layer.objects.active=modules[0]
    modules[0].select_set(True)
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=3.7
            area.spaces.active.region_3d.view_location=(0,0,.05)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE),compress=True,relative_remap=False)


def export():
    for level in range(3):
        obj = bpy.data.objects[f'MODULE_CornerFloor_L{level}']
        bpy.ops.object.select_all(action='DESELECT')
        obj.hide_set(False)
        obj.hide_render=False
        obj.select_set(True)
        name=SLUG+(f'-lod{level}' if level else '')
        bpy.ops.export_scene.gltf(filepath=str(HERE/'exports'/f'{name}.glb'),export_format='GLB',
                                  use_selection=True,export_animations=False,export_extras=True,
                                  export_image_format='JPEG' if level==2 else 'AUTO',export_image_quality=89)
        obj.hide_set(level!=0)
        obj.hide_render=level!=0


def preview(level):
    name = SLUG + (f'-lod{level}' if level else '')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(HERE/'exports'/f'{name}.glb'))
    scene = bpy.context.scene
    target = Vector((0, 0, .045))
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.0005))
    bpy.context.object.data.materials.append(material('Studio', (47,60,63), .84))
    for light_name, xyz, energy, size in [('Key', (-3,-4,5), 560, 4), ('Fill',(3,1,3),260,3), ('Rim',(-1,3,5),400,3)]:
        bpy.ops.object.light_add(type='AREA', location=xyz)
        lamp = bpy.context.object
        lamp.name = light_name
        lamp.data.energy = energy
        lamp.data.shape = 'DISK'
        lamp.data.size = size
        lamp.rotation_euler = (target - lamp.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.object.camera_add(location=(2.6,-3.5,2.65))
    cam = bpy.context.object
    cam.rotation_euler = (target-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 3.25
    scene.camera = cam
    scene.world = bpy.data.worlds.new('Soft studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .42
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 20
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 900, 675
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'WEBP'
    scene.render.image_settings.quality = 90
    scene.render.filepath = str(HERE/'previews'/f'{name}.webp')
    bpy.ops.render.render(write_still=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--straight-source', type=Path, default=HERE.parent/BASE/'sources'/f'{BASE}.blend')
    parser.add_argument('--export-source',action='store_true')
    parser.add_argument('--skip-render',action='store_true')
    options=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for folder in ('sources','exports','previews'):
        (HERE/folder).mkdir(exist_ok=True)
    if options.export_source:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
    else:
        if SOURCE.exists(): raise FileExistsError(f'Preserve the saved source or use --export-source: {SOURCE}')
        build(options.straight_source.resolve())
    export()
    if not options.skip_render:
        for level in range(3): preview(level)


if __name__=='__main__': main()
