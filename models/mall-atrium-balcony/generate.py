"""Original atrium balcony assembly, metres; no structural/load/code certification.
Normal generation replaces source; --export-source preserves source edits.
"""
from pathlib import Path
import bpy,sys,runpy,json,struct
from mathutils import Vector
HERE=Path(__file__).resolve().parent
# Reviewed original procedural helpers copied for a self-contained generator.
def material(name,rgb,roughness=.4,metallic=0,alpha=1):
    m=bpy.data.materials.new(name);m.use_nodes=True
    def linear(v):
        v=v/255;return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    rgba=(*[linear(v) for v in rgb],alpha);m.diffuse_color=rgba
    p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=rgba;p.inputs['Roughness'].default_value=roughness;p.inputs['Metallic'].default_value=metallic;p.inputs['Alpha'].default_value=alpha
    if alpha<1:m.blend_method='BLEND';m.use_backface_culling=False;m.show_transparent_back=False
    return m
def box(name,loc,dims,mat,bevel=.001):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    if bevel:
        b=o.modifiers.new('Editable eased edges','BEVEL');b.width=bevel;b.segments=2
    return o
def cylinder(name,loc,radius,depth,mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=radius,depth=depth,location=loc);o=bpy.context.object;o.name=name;o.data.materials.append(mat);return o
def empty(name,parent=None,loc=(0,0,0)):
    o=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(o);o.parent=parent;o.location=loc;return o
def attach(o,parent):
    bpy.context.view_layer.update();matrix=o.matrix_world.copy();o.parent=parent;o.matrix_world=matrix;return o
def point_at(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def studio():
    s=bpy.context.scene
    floor=material('STUDIO floor only',(220,222,216),.95);box('STUDIO_Floor',(0,0,-.03),(2000,2000,.06),floor,0)
    target=(0,0,1.15)
    for name,loc,power,size in [('Key',(-3,-4,6),800,4),('Fill',(4,-2,3),500,4),('Rear',(1,4,5),900,3)]:
        bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=power;o.data.size=size;point_at(o,target)
    bpy.ops.object.camera_add(location=(3,-6,3.1));s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=3.3;point_at(s.camera,target)
    s.world=bpy.data.worlds.new('Studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.25,.31,.32,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
    s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
def export(root,destination):
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for o in root.children_recursive:o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(destination),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True,export_texcoords=True,export_cameras=False,export_lights=False)
    # Blender may emit identical material definitions for flat/bevelled meshes.
    # Collapse only exact duplicates; geometry, component nodes and BIN stay intact.
    data=destination.read_bytes();length=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+length]);unique=[];mapping={}
    for i,mat in enumerate(doc['materials']):
        if mat not in unique:unique.append(mat)
        mapping[i]=unique.index(mat)
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:primitive['material']=mapping[primitive['material']]
    doc['materials']=unique;chunk=json.dumps(doc,separators=(',',':')).encode();chunk+=b' '*((-len(chunk))%4);tail=data[20+length:]
    destination.write_bytes(struct.pack('<III',0x46546c67,2,20+len(chunk)+len(tail))+struct.pack('<II',len(chunk),0x4e4f534a)+chunk+tail)


SLUG='mall-atrium-balcony';ROOT='ASSET_MallAtriumBalcony'
def append_objects(path,names):
    with bpy.data.libraries.load(str(path),link=False) as (a,b):b.objects=names
    for o in b.objects:bpy.context.scene.collection.objects.link(o)
    return b.objects

def main():
    for d in ('sources','exports','previews','reports'):(HERE/d).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        root=empty(ROOT);deck=empty('MODULE_Deck',root)
        concrete=material('Warm mineral slab',(178,178,163),.8)
        fascia=material('Champagne anodised fascia',(177,157,110),.33,.6)
        soffit=material('Warm ivory soffit',(222,220,209),.6)
        attach(box('DECK_Slab',(0,0,.12),(2,1.2,.20),concrete,.001),deck)
        attach(box('DECK_Soffit',(0,0,.01),(1.996,1.196,.02),soffit,.001),deck)
        attach(box('EDGE_Fascia',(0,-.61,.115),(1.996,.02,.208),fascia,.001),deck)
        # Append the real original railing's independent authored meshes, not a lookalike.
        path=HERE.parent/'mall-glass-railing/sources/mall-glass-railing-2m.blend'
        with bpy.data.libraries.load(str(path),link=False) as (a,b):names=[n for n in a.objects if n not in ('ASSET_MallGlass2m',) and not n.startswith(('Studio','Key','Fill','Rim','Camera'))]
        parts=append_objects(path,names)
        groups={k:empty(k,root) for k in ('MODULE_Post_Left','MODULE_Post_Right','MODULE_Infill')}
        for o in parts:
            if o.type!='MESH' or not o.get('module'):
                bpy.data.objects.remove(o,do_unlink=True);continue
            # Source children have identity root transforms; bake only translation into this assembly.
            o.parent=groups[o['module']];o.location.y-=.52;o.location.z+=.25
            o.name='RAILING_'+o.name
        for k,x in [('Left',-1),('Right',1)]:
            cap=empty('MODULE_EndCap_'+k,root)
            attach(box('ENDCAP_'+k,(x+(-.04 if x<0 else .04),0,.125),(.08,1.2,.25),concrete,.001),cap)
        # Actual 421 slab mesh and materials, cropped at the two boundary strips.
        tile=append_objects(HERE.parent/'mall-floor-tile/sources/mall-floor-tile-module.blend',['MODULE_Tile_1'])[0]
        tile.parent=None;tile.name='SOURCE_TILE_TEMPLATE'
        for j,y in enumerate((-.3,.3)):
            for i,(x,w) in enumerate(((-.8,.396),(-.3,.596),(.3,.596),(.8,.396))):
                o=tile.copy();o.data=tile.data.copy();s.collection.objects.link(o);o.parent=deck;o.name='FLOOR_Tile_'+str(j*4+i+1);o.location=(x,y,.241)
                for v in o.data.vertices:
                    if abs(v.co.x)>.1:v.co.x=(1 if v.co.x>0 else -1)*w/2
                # Match original texture scale on trimmed boundary tiles, not stretched artwork.
                for poly in o.data.polygons:
                    if poly.normal.z>.5:
                        for li in poly.loop_indices:
                            v=o.data.vertices[o.data.loops[li].vertex_index].co;o.data.uv_layers.active.data[li].uv=(v.x/.596+.5,v.y/.596+.5)
                o['provenance']='421 MODULE_Tile_1; boundary tiles cropped; original material/packed texture'
        grout=bpy.data.materials.get('Warm grey grout')
        if not grout:
            with bpy.data.libraries.load(str(HERE.parent/'mall-floor-tile/sources/mall-floor-tile-module.blend'),link=False) as (a,b):b.materials=['Warm grey grout']
            grout=b.materials[0]
        bpy.data.objects.remove(tile,do_unlink=True)
        # Adapt original 421 heightfield grout to 0.4/0.6/0.6/0.4 m tile widths.
        qx=[-1,-.998,-.602,-.598,-.002,.002,.598,.602,.998,1];qy=[-.6,-.598,-.002,.002,.598,.6]
        heights=[[.012 if i in (1,3,5,7) and j in (1,3) else .029 for j in range(5)] for i in range(9)]
        vertices=[];faces=[];lookup={}
        def face(points):
            ids=[]
            for point in points:
                point=(point[0],point[1],point[2]+.22)
                if point not in lookup:lookup[point]=len(vertices);vertices.append(point)
                ids.append(lookup[point])
            faces.append(ids)
        for i in range(9):
            for j in range(5):
                x0,x1=qx[i:i+2];y0,y1=qy[j:j+2];h=heights[i][j]
                face([(x0,y0,h),(x1,y0,h),(x1,y1,h),(x0,y1,h)])
                face([(x0,y1,0),(x1,y1,0),(x1,y0,0),(x0,y0,0)])
                low=heights[i-1][j] if i else 0
                if h>low:face([(x0,y1,low),(x0,y0,low),(x0,y0,h),(x0,y1,h)])
                low=heights[i+1][j] if i<8 else 0
                if h>low:face([(x1,y0,low),(x1,y1,low),(x1,y1,h),(x1,y0,h)])
                low=heights[i][j-1] if j else 0
                if h>low:face([(x0,y0,low),(x1,y0,low),(x1,y0,h),(x0,y0,h)])
                low=heights[i][j+1] if j<4 else 0
                if h>low:face([(x1,y1,low),(x0,y1,low),(x0,y1,h),(x1,y1,h)])
        mesh=bpy.data.meshes.new('421 adapted filled grout');mesh.from_pydata(vertices,[],faces);mesh.update();o=bpy.data.objects.new('FLOOR_GroutBed',mesh);s.collection.objects.link(o);o.parent=deck;mesh.materials.append(grout)
        for name,loc in [('JointLeft',(-1,-.52,.25)),('JointRight',(1,-.52,.25)),('DeckTop',(0,0,.25)),('Underside',(0,0,0))]:empty('CONNECTOR_'+name,root,loc)
        root['units']='metres';root['repeat_pitch_m']=2.0;root['finished_deck_height_m']=.25
        root['origin']='Centre of slab underside; local zero, not building ground. Add installation elevation to the whole root.'
        root['scope']='Visual architecture only, no structural/load/safety/code certification.'
        root['assembly']='Repeat MODULE_Deck and MODULE_Infill at 2 m; one post per unique joint; end caps only at exposed outer ends.'
        root['provenance']='Existing project 006 railing source and 421 tiles/materials; unchanged originals.'
        for image in bpy.data.images:
            if image.source=='FILE':image.pack()
        studio();s.camera.location=(3,-5,3);s.camera.data.ortho_scale=3.4;point_at(s.camera,(0,0,.65));s.cycles.samples=32
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(root,HERE/'exports'/(SLUG+'.glb'))
    if '--skip-render' not in sys.argv:
        bpy.context.scene.render.filepath=str(HERE/'previews'/(SLUG+'.png'));bpy.ops.render.render(write_still=True)
if __name__=='__main__':main()
