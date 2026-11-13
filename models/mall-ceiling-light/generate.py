"""Original recessed mall ceiling light. Blender metres +Z up; glTF metres +Y up.
Run with --skip-render to regenerate; --export-source preserves saved source edits.
"""
from pathlib import Path
import bpy,sys
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='mall-ceiling-light-module';ROOT='ASSET_MallCeilingLight'
def material(name,rgb,roughness=.5,metallic=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    def linear(v):
        v=v/255;return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    rgba=(*[linear(v) for v in rgb],1);m.diffuse_color=rgba
    p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=rgba
    p.inputs['Roughness'].default_value=roughness;p.inputs['Metallic'].default_value=metallic
    return m
def finish(o,mat,bevel=0):
    o.data.materials.append(mat)
    if bevel:
        b=o.modifiers.new('Editable eased edge','BEVEL');b.width=bevel;b.segments=2
    return o
def box(name,loc,dims,mat,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(o,mat,bevel)
def ring(name,outer,inner,z0,z1,mat,bevel=0):
    # Closed rectangular annulus, not four interpenetrating boxes.
    vs=[]
    for z in (z0,z1):
        for side in (outer,inner):
            h=side/2
            vs.extend([(-h,-h,z),(h,-h,z),(h,h,z),(-h,h,z)])
    faces=[]
    for i in range(4):
        j=(i+1)%4
        faces.extend([(i,j,j+8,i+8),(i+4,i+12,j+12,j+4),(i+8,j+8,j+12,i+12),(i+4,j+4,j,i)])
    mesh=bpy.data.meshes.new(name+' annular mesh');mesh.from_pydata(vs,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o)
    return finish(o,mat,bevel)
def cylinder(name,loc,radius,depth,mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=radius,depth=depth,location=loc);o=bpy.context.object;o.name=name
    return finish(o,mat,.0003)
def point_at(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def studio(scale=.94,target=(0,0,.025)):
    s=bpy.context.scene
    for name,loc,power,size in [('Key',(-1,-1.5,-2),200,2),('Fill',(2,1,-1),90,2),('Rear',(0,2,2),160,2)]:
        bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=power;o.data.size=size;point_at(o,target)
    bpy.ops.object.camera_add(location=(1.2,-1.6,-1.1));s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=scale;point_at(s.camera,target)
    s.world=bpy.data.worlds.new('Studio slate');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.13,.18,.21,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.4
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
        ivory=material('Ivory powder-coated bezel',(219,223,216),.38,.12)
        metal=material('Brushed aluminum housing',(129,143,147),.35,.65)
        diffuser=material('Warm opal emissive diffuser',(241,238,218),.62)
        p=diffuser.node_tree.nodes['Principled BSDF'];p.inputs['Emission Color'].default_value=(.80,.73,.55,1);p.inputs['Emission Strength'].default_value=1
        charcoal=material('Graphite driver cover',(42,53,57),.52)
        parts=[ring('FRAME_Bezel',.576,.528,0,.012,ivory,.001),
          ring('HOUSING_TrayWalls',.55,.53,.012,.044,metal,.0006),
          box('DIFFUSER_Opal',(0,0,.006),(.534,.534,.006),diffuser,.0006),
          box('HOUSING_BackPlate',(0,0,.0455),(.55,.55,.003),metal,.0005),
          box('DRIVER_Cover',(0,0,.0555),(.12,.06,.017),charcoal,.002)]
        for i,(x,y) in enumerate([(-.274,-.274),(.274,-.274),(-.274,.274),(.274,.274)],1):
            parts.append(cylinder('FASTENER_Bezel_'+str(i),(x,y,0),.0035,.002,metal))
        for i,x in enumerate([-.08,.08],1):parts.append(cylinder('GLAND_CableEntry_'+str(i),(x,0,.051),.008,.008,charcoal))
        root=bpy.data.objects.new(ROOT,None);s.collection.objects.link(root)
        for o in parts:o.parent=root
        root['units']='metres';root['origin']='centre of bezel underside';root['mounting']='Replace exactly one 576mm panel in asset 422, offset X/Y +/-0.3m and Z +0.008m; keep grid, hangers and other three panels.'
        root['emission']='Static emissive appearance only in Three.js. No switch, punctual light, electrical or photometric compliance.'
        studio();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(root,HERE/'exports'/(SLUG+'.glb'))
    if '--skip-render' not in sys.argv:
        bpy.context.scene.render.filepath=str(HERE/'previews'/(SLUG+'.png'));bpy.ops.render.render(write_still=True)
if __name__=='__main__':main()
