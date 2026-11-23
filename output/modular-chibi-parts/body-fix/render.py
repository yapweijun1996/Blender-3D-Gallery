"""Matched, textured inspection plates rendered in Blender Cycles CPU."""
import math
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from bodycheck import *
from mathutils import Matrix, Vector
from clearance import bone

VIEWS={'walk':([27,42],20),'wave':([0,19],8),'run':([9,17],-32)}
def material(name,color,emission=False):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    if emission:
        shader=mat.node_tree.nodes.new('ShaderNodeEmission')
        shader.inputs['Color'].default_value=(*color,1.0)
        mat.node_tree.links.new(shader.outputs[0],mat.node_tree.nodes.get('Material Output').inputs['Surface'])
    else: mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1.0)
    return mat


def text_object(scene,name,content,x,z,fontsize,ink):
    data=bpy.data.curves.new(name,'FONT');data.body=content
    data.align_x='CENTER';data.align_y='CENTER';data.size=fontsize
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o)
    o.location=(x,-.75,z);o.rotation_euler.x=math.pi/2;o.data.materials.append(ink)
    return o


def render():
    samples={}
    for version,path in [('Original',SOURCE),('Corrected',OUT/'motion_fixed.glb')]:
        scene,arm,body,_=load(path)
        for clip,(frames,angle) in VIEWS.items():
            bind(arm,clip)
            for f in frames:
                scene.frame_set(f)
                p=posed(body)
                center=bone(arm,'Hips').head
                p[:,0]-=center.x;p[:,1]-=center.y
                samples[clip,f,version]=p
    body.hide_render=True;arm.hide_render=True
    camera=bpy.data.cameras.new('Plate camera')
    ob=bpy.data.objects.new('Plate camera',camera);scene.collection.objects.link(ob)
    ob.location=(0,-5,0);ob.rotation_euler.x=math.pi/2
    camera.type='ORTHO';camera.ortho_scale=2.66;scene.camera=ob
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=12
    scene.cycles.use_denoising=True
    scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    world=bpy.data.worlds.new('Blue gray studio');scene.world=world;world.use_nodes=True
    bg=world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.115,.155,.205,1);bg.inputs['Strength'].default_value=.65
    for direction,power,color in [((-.8,-1.4,2.3),3,(1,.9,.79)),((1.3,-1,.9),1.35,(.76,.87,1)),((.5,1,1.5),2,(.88,.95,1))]:
        lamp=bpy.data.lights.new('Studio sun','SUN');lamp.energy=power;lamp.angle=math.radians(20);lamp.color=color
        ob=bpy.data.objects.new(lamp.name,lamp);scene.collection.objects.link(ob)
        ob.rotation_euler=(-Vector(direction)).to_track_quat('-Z','Y').to_euler()
    ink=material('Type',(.88,.94,1),True)
    padmat=material('Ground',(.15,.20,.26))
    plates=OUT/'renders';plates.mkdir(exist_ok=True)
    for clip,(frames,angle) in VIEWS.items():
        created=[]
        matrix=np.asarray(Matrix.Rotation(math.radians(7),3,'X') @ Matrix.Rotation(math.radians(-angle),3,'Z'))
        for col,version in enumerate(('Original','Corrected')):
            x=(-.59,.59)[col]
            created.append(text_object(scene,'Column title',f'{clip.upper()}   /   {version}',x,1.235,.080,ink))
            for row,f in enumerate(frames):
                bottom=(.034,-1.145)[row]
                pts=samples[clip,f,version] @ matrix.T + np.array([x,0,bottom])
                data=body.data.copy();data.vertices.foreach_set('co',pts.astype(np.float32).ravel());data.update()
                ob=bpy.data.objects.new('Posed master',data);scene.collection.objects.link(ob);created.append(ob)
                # A ground ellipse shares z=0 with the original scene.
                n=80; theta=np.arange(n)*2*math.pi/n
                base=np.stack([.39*np.cos(theta),.26*np.sin(theta),np.full(n,-.003)],axis=1)
                base=base @ matrix.T + np.array([x,0,bottom])
                ground=bpy.data.meshes.new('Ground plane');ground.from_pydata(base.tolist(),[],[list(range(n))])
                go=bpy.data.objects.new('Ground plane',ground);scene.collection.objects.link(go);ground.materials.append(padmat);created.append(go)
                created.append(text_object(scene,'Sample frame',f'Frame {f}',x,bottom-.084,.052,ink))
        scene.render.filepath=str(plates/f'{clip}_before_after.png')
        bpy.ops.render.render(write_still=True)
        for o in created:
            bpy.data.objects.remove(o,do_unlink=True)

if __name__=='__main__':
    render()
