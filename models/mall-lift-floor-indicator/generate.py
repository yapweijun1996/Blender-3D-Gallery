"""V2.1 P0 item 432: static, original lift floor indicator in metres.
Source edits survive --export-source. Configure root display_floor/display_direction;
export applies only segment materials and arrow pose, never rebuilds housing.
"""
from pathlib import Path
import bpy,bmesh,math,json,struct,sys
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='mall-lift-floor-indicator';ROOT='ASSET_MallLiftFloorIndicator'
DIGITS={'0':'abcdef','1':'bc','2':'abdeg','3':'abcdg','4':'bcfg','5':'acdfg','6':'acdefg','7':'abc','8':'abcdefg','9':'abcdfg'}
def material(name,rgb,metallic=0,roughness=.4,emission=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    def linear(v):
        v/=255
        return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    color=(*[linear(v) for v in rgb],1);p=m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value=color;p.inputs['Metallic'].default_value=metallic;p.inputs['Roughness'].default_value=roughness
    if emission:p.inputs['Emission Color'].default_value=color;p.inputs['Emission Strength'].default_value=emission
    m.diffuse_color=color;return m

def mesh(name,verts,faces,mat):
    d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update()
    bm=bmesh.new();bm.from_mesh(d);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(d);bm.free()
    o=bpy.data.objects.new(name,d);bpy.context.scene.collection.objects.link(o);d.materials.append(mat);return o

def empty(name,parent=None,loc=(0,0,0)):
    o=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(o);o.parent=parent;o.location=loc;return o

def cube(name,loc,size,mat,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    if bevel:
        m=o.modifiers.new('Small real edge radius','BEVEL');m.width=bevel;m.segments=3
        bpy.ops.object.modifier_apply(modifier=m.name)
    return o

def cylinder(name,loc,r,depth,mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=r,depth=depth,location=loc,rotation=(math.pi/2,0,0))
    o=bpy.context.object;o.name=name;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    if mat:o.data.materials.append(mat)
    for f in o.data.polygons:f.use_smooth=len(f.vertices)==4
    return o

def annulus(name,z,outer,inner,y0,y1,mat):
    n=48;v=[(r*math.cos(2*math.pi*i/n),y,z+r*math.sin(2*math.pi*i/n)) for r,y in [(outer,y0),(inner,y0),(outer,y1),(inner,y1)] for i in range(n)];f=[]
    for i in range(n):
        j=(i+1)%n
        f.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
    return mesh(name,v,f,mat)

def extrude(name,outline,y0,y1,mat):
    n=len(outline);v=[(x,y,z) for y in (y0,y1) for x,z in outline]
    return mesh(name,v,[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],mat)

def point_at(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()

def export(root,path):
    apply_display(root)
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for o in root.children_recursive:o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True,export_texcoords=False,export_cameras=False,export_lights=False)
    data=path.read_bytes();n=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+n]);mats=[];mapping={}
    for i,m in enumerate(doc['materials']):
        if m not in mats:mats.append(m)
        mapping[i]=mats.index(m)
    for m in doc['meshes']:
        for p in m['primitives']:p['material']=mapping[p['material']]
    doc['materials']=mats;chunk=json.dumps(doc,separators=(',',':')).encode();chunk+=b' '*(-len(chunk)%4);tail=data[20+n:]
    path.write_bytes(struct.pack('<III',0x46546c67,2,20+len(chunk)+len(tail))+struct.pack('<II',len(chunk),0x4e4f534a)+chunk+tail)


def apply_display(root):
    floor=str(root['display_floor']);direction=str(root['display_direction'])
    if len(floor)!=2 or any(c not in DIGITS for c in floor):raise ValueError('display_floor must be two decimal digits')
    if direction not in ['up','down']:raise ValueError('display_direction must be up or down')
    lit=bpy.data.materials['Amber emissive segments'];off=bpy.data.materials['Unlit segment recess']
    for index,digit in enumerate(floor):
        for segment in 'abcdefg':
            o=bpy.data.objects[f'SEGMENT_Digit{index}_{segment}'];active=segment in DIGITS[digit]
            o.data.materials.clear();o.data.materials.append(lit if active else off);o['illuminated']=active
    bpy.data.objects['MODULE_Direction'].rotation_euler.y=0 if direction=='up' else math.pi

def ring(name,outer,inner,y0,y1,mat):
    n=len(outer);v=[(x,y,z) for pts,y in [(outer,y0),(inner,y0),(outer,y1),(inner,y1)] for x,z in pts];f=[]
    for i in range(n):
        j=(i+1)%n;f.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
    return mesh(name,v,f,mat)

def rectangle(w,h,r):
    return [(-w/2+r,0),(w/2-r,0),(w/2,r),(w/2,h-r),(w/2-r,h),(-w/2+r,h),(-w/2,h-r),(-w/2,r)]

def studio():
    s=bpy.context.scene;bg=material('STUDIO soft grey',(215,221,222),roughness=.9)
    cube('STUDIO_Wall',(0,.04,.08),(3,.05,3),bg)
    for name,pos,energy,size in [('Key',(-.4,-.6,.6),22,.5),('Fill',(.4,-.3,.25),9,.4),('Edge',(.2,.1,.6),12,.3)]:
        bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=energy;o.data.size=size;point_at(o,(0,0,.08))
    bpy.ops.object.camera_add(location=(.38,-.85,.29));s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=.51;point_at(s.camera,(0,-.01,.08))
    s.world=bpy.data.worlds.new('Studio environment');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.35,.39,.42,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
    s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=False
    s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'

def build():
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
    root=empty(ROOT);steel=material('Satin stainless bezel',(171,185,195),.75,.32);housing=material('Charcoal housing',(44,51,57),.3,.4);face=material('Dark display face',(12,19,23),.1,.32);amber=material('Amber emissive segments',(255,170,46),0,.35,1.25);off=material('Unlit segment recess',(31,33,31),0,.5)
    # Closed cup with 1.5 mm back and side walls. Back plane Y=0.
    outer=[(-.204,.006),(.204,.006),(.204,.154),(-.204,.154)];inner=[(-.2025,.0075),(.2025,.0075),(.2025,.1525),(-.2025,.1525)]
    v=[(x,y,z) for pts,y in [(outer,0),(outer,-.022),(inner,-.0015),(inner,-.022)] for x,z in pts];f=[(0,1,2,3),(8,11,10,9)]
    for i in range(4):j=(i+1)%4;f.extend([(i,4+i,4+j,j),(4+i,12+i,12+j,4+j),(8+i,8+j,12+j,12+i)])
    body=mesh('MODULE_Housing',v,f,housing);body.parent=root
    outer=rectangle(.42,.16,.007);inner=[(x,z+.014) for x,z in rectangle(.392,.132,.003)]
    bezel=ring('MODULE_MetalBezel',outer,inner,-.022,-.025,steel);bezel.parent=root
    panel=cube('MODULE_DarkFace',(0,-.0245,.08),(.394,.003,.134),face,.001);panel.parent=root
    # Independent seven-segment digit meshes, using no fonts or textures.
    layout={'a':(0,.042,False),'b':(.029,.021,True),'c':(.029,-.021,True),'d':(0,-.042,False),'e':(-.029,-.021,True),'f':(-.029,.021,True),'g':(0,0,False)}
    for index,cx in enumerate([-.005,.105]):
        group=empty(f'MODULE_Digit{index}',root,(cx,0,.08))
        for key,(x,z,vertical) in layout.items():
            length=.036 if vertical else .052;t=.006
            points=[(-length/2+t/2,0),(-length/2,t/2),(-length/2+t/2,t),(length/2-t/2,t),(length/2,t/2),(length/2-t/2,0)]
            points=[(a,b-t/2) for a,b in points]
            if vertical:points=[(-b,a) for a,b in points]
            o=extrude(f'SEGMENT_Digit{index}_{key}',[(a+x,b+z) for a,b in points],-.0268,-.026,amber);o.parent=group
    direction=empty('MODULE_Direction',root,(-.12,0,.08))
    for name,outline in [('Shaft',[(-.004,-.036),(.004,-.036),(.004,.025),(-.004,.025)]),('Left',[(-.029,.009),(-.023,.003),(.003,.033),(-.003,.039)]),('Right',[(.029,.009),(.023,.003),(-.003,.033),(.003,.039)])]:
        o=extrude('SEGMENT_Arrow_'+name,outline,-.0268,-.026,amber);o.parent=direction
    empty('CONNECTOR_WallMount',root,(0,0,.08));empty('CONNECTOR_DisplayBottom',root)
    root['display_floor']='02';root['display_direction']='up';root['units']='metres';root['backlog']='V2.1 P0 item 432'
    root['scope']='Static visual lift floor indicator only. Not call panel 431, complete lift, live elevator state, runtime update, electrical design or safety/code compliance.'
    root['wall_mount']='Wall plane Blender Y=0; front -Y; bottom Z=0. CONNECTOR_WallMount=(0,0,0.08); installation height chosen by scene author.'
    apply_display(root);studio();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/f'{SLUG}.blend'),compress=True);return root

if __name__=='__main__':
    for name in ['sources','exports','previews','reports']:(HERE/name).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/f'{SLUG}.blend'));root=bpy.data.objects[ROOT]
    else:root=build()
    export(root,HERE/'exports/optimized.glb')
    if '--skip-render' not in sys.argv:s=bpy.context.scene;s.render.filepath=str(HERE/'previews'/f'{SLUG}.png');bpy.ops.render.render(write_still=True)
