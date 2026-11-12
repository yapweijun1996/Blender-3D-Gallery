"""Original suspended mall ceiling cassette, metres, source Z-up/export Y-up.
Regenerate: blender -b --python generate.py -- --skip-render
Preserve manual edits: add --export-source; this reopens the saved source.
"""
from pathlib import Path
import bpy,sys
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='mall-ceiling-panel-module'; ROOT='ASSET_MallCeilingPanel'
def material(name,rgb,roughness=.5,metallic=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    def linear(v):
        v=v/255;return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    rgba=(*[linear(v) for v in rgb],1);m.diffuse_color=rgba
    p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=rgba
    p.inputs['Roughness'].default_value=roughness;p.inputs['Metallic'].default_value=metallic
    return m
def box(name,loc,dims,mat,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    if bevel:
        b=o.modifiers.new('Editable eased edge','BEVEL');b.width=bevel;b.segments=2
    return o
def t_rail(name,centre,length,width,mat,along_x=True):
    # Extruded closed T section: visible flange z=0..4mm, web z=4..32mm.
    w=width/2; t=min(.0015,w/2)
    profile=[(-w,0),(w,0),(w,.004),(t,.004),(t,.032),(-t,.032),(-t,.004),(-w,.004)]
    vs=[]
    for q in [-length/2,length/2]:
        for u,z in profile:vs.append((q,u,z) if along_x else (u,q,z))
    faces=[tuple(range(7,-1,-1)),tuple(range(8,16))]
    for i in range(8):j=(i+1)%8;faces.append((i,j,j+8,i+8))
    mesh=bpy.data.meshes.new(name+' closed T section');mesh.from_pydata(vs,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);o.location=centre;mesh.materials.append(mat)
    # Recalculate outward normals independent of extrusion axis.
    bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT');o.select_set(False)
    return o
def rod(name,x,y,mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.004,depth=.314,location=(x,y,.191))
    o=bpy.context.object;o.name=name;o.data.materials.append(mat)
    return o
def point_at(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def studio(scale=1.95,target=(0,0,.12)):
    s=bpy.context.scene
    for name,loc,power,size in [('Key',(-2,-3,-4),420,3),('Fill',(3,1,-3),240,3),('Rear',(0,3,3),320,3)]:
        bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=power;o.data.size=size;point_at(o,target)
    bpy.ops.object.camera_add(location=(1.8,-2.3,-1.8));s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=scale;point_at(s.camera,target)
    s.world=bpy.data.worlds.new('Studio slate');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.13,.18,.21,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45
    s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
def export(root,destination):
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for o in root.children_recursive:o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(destination),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True,export_cameras=False,export_lights=False)
def main():
    for folder in ('sources','exports','previews','reports'):(HERE/folder).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        frame=material('Powder-coated ivory T grid',(210,214,208),.42)
        core=material('Mineral panel edge',(201,198,184),.82)
        finish=material('Mineral fibre underside original seed 422',(255,255,255),.85)
        image=bpy.data.images.load(str(HERE/'textures/mineral-fibre-original.png'));image.pack()
        tex=finish.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
        finish.node_tree.links.new(tex.outputs['Color'],finish.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
        steel=material('Suspension galvanized steel',(128,143,149),.4,.55)
        parts=[]
        for i,(x,y) in enumerate([(-.3,-.3),(.3,-.3),(-.3,.3),(.3,.3)],1):
            o=box('PANEL_'+str(i),(x,y,.016),(.576,.576,.016),core,.0008);o.data.materials.append(finish)
            for f in o.data.polygons:
                if f.normal.z<-.5:f.material_index=1
            o['part']='independent removable acoustic-style panel';parts.append(o)
        for i,(y,width) in enumerate([(-.594,.012),(0,.024),(.594,.012)],1):
            parts.append(t_rail('GRID_Main_'+str(i),(0,y,0),1.2,width,frame))
        for i,(x,width) in enumerate([(-.594,.012),(0,.024),(.594,.012)],1):
            for j,y in enumerate([-.3,.3],1):parts.append(t_rail('GRID_Cross_'+str(i)+'_'+str(j),(x,y,0),.576,width,frame,False))
        for i,(x,y) in enumerate([(-.48,-.594),(.48,-.594),(-.48,.594),(.48,.594)],1):
            parts.extend([rod('HANGER_Rod_'+str(i),x,y,steel),box('HANGER_Cleat_'+str(i),(x,y,.030),(.024,.012,.008),steel,.0008),box('HANGER_TopPlate_'+str(i),(x,y,.354),(.04,.012,.012),steel,.001)])
        root=bpy.data.objects.new(ROOT,None);s.collection.objects.link(root)
        for o in parts:o.parent=root
        for name,loc,normal in [('XP',(.6,0,.018),(1,0,0)),('XN',(-.6,0,.018),(-1,0,0)),('YP',(0,.6,.018),(0,1,0)),('YN',(0,-.6,.018),(0,-1,0))]:
            o=bpy.data.objects.new('CONNECTOR_'+name,None);s.collection.objects.link(o);o.parent=root;o.location=loc;o['outward_normal_source']=normal;o['role']='repeat edge, visual registration only';o.empty_display_size=.04
        root['units']='metres';root['origin']='centre of visible grid underside';root['repeat_pitch_m']=1.2;root['underside_z_m']=0;root['purpose']='generic decorative ceiling concept, not structural or electrical specification'
        studio();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(root,HERE/'exports'/(SLUG+'.glb'))
    if '--skip-render' not in sys.argv:
        bpy.context.scene.render.filepath=str(HERE/'previews'/(SLUG+'.png'));bpy.ops.render.render(write_still=True)
if __name__=='__main__':main()
