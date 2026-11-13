"""Original mall floor tile module. Blender 4.0.2, metres, Z-up source/Y-up GLB.
Rebuild: make_texture.py, then blender -b --python generate.py.
Export existing edits: blender -b --python generate.py -- --export-source --skip-render.
"""
from pathlib import Path
import bpy, sys
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='mall-floor-tile-module'; ROOT='ASSET_MallFloorTile'

def material(name,rgb,roughness=.4):
    m=bpy.data.materials.new(name);m.use_nodes=True
    def linear(v):
        v=v/255;return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    rgba=(*[linear(v) for v in rgb],1)
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=rgba
    m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=roughness;m.diffuse_color=rgba
    return m

def box(name,loc,dims,mat):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    return o

def grout_bed(mat):
    # Closed heightfield solid: support under slabs, filled joints 1 mm below
    # their wearing surface. No intersecting full-height box under the slabs.
    q=[-.6,-.598,-.002,.002,.598,.6]
    heights=[[.012 if i in (1,3) and j in (1,3) else .029 for j in range(5)] for i in range(5)]
    vertices=[];faces=[];lookup={}
    def face(points):
        ids=[]
        for point in points:
            if point not in lookup:lookup[point]=len(vertices);vertices.append(point)
            ids.append(lookup[point])
        faces.append(ids)
    for i in range(5):
        for j in range(5):
            x0,x1=q[i:i+2];y0,y1=q[j:j+2];h=heights[i][j]
            face([(x0,y0,h),(x1,y0,h),(x1,y1,h),(x0,y1,h)])
            face([(x0,y1,0),(x1,y1,0),(x1,y0,0),(x0,y0,0)])
            low=heights[i-1][j] if i else 0
            if h>low:face([(x0,y1,low),(x0,y0,low),(x0,y0,h),(x0,y1,h)])
            low=heights[i+1][j] if i<4 else 0
            if h>low:face([(x1,y0,low),(x1,y1,low),(x1,y1,h),(x1,y0,h)])
            low=heights[i][j-1] if j else 0
            if h>low:face([(x0,y0,low),(x1,y0,low),(x1,y0,h),(x0,y0,h)])
            low=heights[i][j+1] if j<4 else 0
            if h>low:face([(x1,y1,low),(x0,y1,low),(x0,y1,h),(x1,y1,h)])
    mesh=bpy.data.meshes.new('Continuous filled grout mesh');mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new('MODULE_GroutBed',mesh);bpy.context.scene.collection.objects.link(obj);mesh.materials.append(mat)
    return obj

def point_at(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()

def studio(scale=1.85,target=(0,0,.015)):
    s=bpy.context.scene
    box('Studio floor NOT EXPORTED',(0,0,-.011),(200,200,.02),material('Studio background',(45,58,61),.9))
    for name,loc,energy,size in [('Key',(-2,-3,5),500,4),('Fill',(3,1,4),350,4),('Rim',(-1,3,4),250,3)]:
        bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=name;o.data.energy=energy;o.data.size=size;point_at(o,target)
    bpy.ops.object.camera_add(location=(1.8,-2.2,2.4));s.camera=bpy.context.object;s.camera.data.type='ORTHO';s.camera.data.ortho_scale=scale;point_at(s.camera,target)
    s.world=bpy.data.worlds.new('Studio ambient');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.4
    s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=False
    s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'

def export(root,destination):
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for o in root.children_recursive:o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(destination),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_texcoords=True,export_extras=True,export_cameras=False,export_lights=False)

def main():
    for folder in ('sources','exports','previews','reports'): (HERE/folder).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        grout=material('Warm grey grout',(125,126,115),.83)
        body=material('Ivory stone body',(211,205,187),.6)
        finish=material('Honed ivory terrazzo original seed 421',(255,255,255),.32)
        image=bpy.data.images.load(str(HERE/'textures/terrazzo-original.png'));image.pack()
        tex=finish.node_tree.nodes.new('ShaderNodeTexImage');tex.name='Original editable terrazzo artwork';tex.image=image
        finish.node_tree.links.new(tex.outputs['Color'],finish.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
        # The base includes the 2 mm half-joint on every boundary. Full modules tile at 1.2 m.
        base=grout_bed(grout)
        base['part']='continuous grout bed';base['nominal_pitch_m']=1.2
        tiles=[]
        for i,(x,y) in enumerate([(-.3,-.3),(.3,-.3),(-.3,.3),(.3,.3)]):
            o=box('MODULE_Tile_'+str(i+1),(x,y,.021),(.596,.596,.018),body);o.data.materials.append(finish)
            for p in o.data.polygons:
                if p.normal.z>.5:
                    p.material_index=1
                    for loop in p.loop_indices:
                        v=o.data.vertices[o.data.loops[loop].vertex_index].co
                        u,w=v.x/.596+.5,v.y/.596+.5
                        for _ in range(i):u,w=w,1-u
                        o.data.uv_layers.active.data[loop].uv=(u,w)
            bevel=o.modifiers.new('Submillimetre eased stone edge','BEVEL');bevel.width=.0006;bevel.segments=2
            o['part']='independent editable stone slab';o['tile_pitch_m']=.6;o['grout_joint_m']=.004;tiles.append(o)
        root=bpy.data.objects.new(ROOT,None);s.collection.objects.link(root)
        for o in [base,*tiles]:o.parent=root
        root['units']='metres';root['origin']='bottom centre';root['repeat_pitch_m']=1.2;root['surface_height_m']=.03;root['purpose']='Generic static decorative concept, not a construction specification'
        studio();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(root,HERE/'exports'/(SLUG+'.glb'))
    if '--skip-render' not in sys.argv:
        bpy.context.scene.render.filepath=str(HERE/'previews'/(SLUG+'.png'));bpy.ops.render.render(write_still=True)
if __name__=='__main__':main()
