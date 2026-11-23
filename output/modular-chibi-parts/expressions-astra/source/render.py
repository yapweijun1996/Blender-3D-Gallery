"""Render the round-tripped deliverable and assemble a labelled contact sheet in Blender."""
import sys, math, json, hashlib
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from face import *
from mathutils import Vector

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def setup(scene,w,h,samples):
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=samples
    scene.cycles.use_denoising=samples>4
    scene.render.resolution_x=w
    scene.render.resolution_y=h
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGB"
    scene.view_settings.view_transform="Standard"
    scene.world=bpy.data.worlds.new("Portrait studio")
    scene.world.use_nodes=True
    return scene.world.node_tree

def camera(position,target,span):
    data=bpy.data.cameras.new("Orthographic camera")
    obj=bpy.data.objects.new(data.name,data)
    bpy.context.collection.objects.link(obj)
    obj.location=position
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()
    data.type="ORTHO"
    data.ortho_scale=span
    bpy.context.scene.camera=obj

def lamp(name,position,power,size):
    data=bpy.data.lights.new(name,"AREA")
    data.energy=power
    data.shape="DISK"
    data.size=size
    ob=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(ob)
    ob.location=position
    ob.rotation_euler=(Vector((0,-.08,.795))-ob.location).to_track_quat("-Z","Y").to_euler()

def portraits():
    body=open_body(ROOT/"body_expressions.glb")
    scene=bpy.context.scene
    nt=setup(scene,720,720,20)
    nt.nodes["Background"].inputs["Color"].default_value=(.76,.80,.86,1)
    nt.nodes["Background"].inputs["Strength"].default_value=.80
    ray=nt.nodes.new("ShaderNodeLightPath")
    sky=nt.nodes.new("ShaderNodeBackground")
    sky.inputs["Color"].default_value=(.82,.86,.885,1)
    mix=nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(ray.outputs["Is Camera Ray"],mix.inputs[0])
    nt.links.new(nt.nodes["Background"].outputs[0],mix.inputs[1])
    nt.links.new(sky.outputs[0],mix.inputs[2])
    nt.links.new(mix.outputs[0],nt.nodes["World Output"].inputs["Surface"])
    camera((0,-2,.801),(0,0,.801),.445)
    lamp("Soft key",(-.62,-1.18,1.65),3.8,1.1)
    lamp("Front fill",(.64,-.94,.88),1.7,1.2)
    lamp("Crown light",(.4,.5,1.5),2.4,.9)
    tex=next(n for n in body.data.materials[0].node_tree.nodes if n.type=="TEX_IMAGE")
    neutral=tex.image
    for state in NAMES:
        for key in list(body.data.shape_keys.key_blocks)[1:]:
            key.value=float(key.name=="expr_"+state)
        tex.image=neutral if state=="neutral" else bpy.data.images.load(str(ROOT/"textures"/(state+".png")))
        scene.render.filepath=str(ROOT/"renders"/(state+".png"))
        bpy.ops.render.render(write_still=True)

def sheet():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    size=1152
    height=1264
    nt=setup(scene,size,height,4)
    nt.nodes["Background"].inputs["Color"].default_value=(.957,.953,.934,1)
    camera((0,0,10),(0,0,0),height/100)
    def point(x,y): return ((x-size/2)/100,(height/2-y)/100,0)
    def surface(name,color=None,img=None):
        mat=bpy.data.materials.new(name)
        mat.use_nodes=True
        tree=mat.node_tree
        em=tree.nodes.new("ShaderNodeEmission")
        if img:
            tex=tree.nodes.new("ShaderNodeTexImage")
            tex.image=img
            tree.links.new(tex.outputs["Color"],em.inputs[0])
        else: em.inputs[0].default_value=(*color,1)
        tree.links.new(em.outputs[0],tree.nodes.get("Material Output").inputs[0])
        return mat
    black=surface("Label ink",(.041,.064,.073))
    fontfile=Path("/System/Library/Fonts/Supplemental/Avenir Next.ttc")
    font=bpy.data.fonts.load(str(fontfile)) if fontfile.exists() else None
    for n,state in enumerate(NAMES):
        left=24+(n%2)*562
        top=24+(n//2)*618
        tile=542
        bpy.ops.mesh.primitive_plane_add(size=tile/100,location=point(left+tile/2,top+tile/2))
        plane=bpy.context.object
        img=bpy.data.images.load(str(ROOT/"renders"/(state+".png")))
        plane.data.materials.append(surface(state,img=img))
        curve=bpy.data.curves.new(state,"FONT")
        curve.body=state.capitalize()
        if font: curve.font=font
        curve.size=.38
        obj=bpy.data.objects.new(state,curve)
        bpy.context.collection.objects.link(obj)
        obj.location=point(left+3,top+tile+41)
        obj.data.materials.append(black)
    scene.render.filepath=str(ROOT/"contact_sheet.png")
    bpy.ops.render.render(write_still=True)

if __name__=="__main__":
    if "sheet-only" not in sys.argv: portraits()
    sheet()
    paths=[ROOT/"body_expressions.glb",BASE,HAIR, ROOT.parent/"generated/base-body-neutral-tpose.png",ROOT/"contact_sheet.png"]
    paths += [ROOT/d/(s+".png") for d in ("renders","textures") for s in NAMES]
    (ROOT/"checks/capture.json").write_text(json.dumps({
        "sha256":{str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else p.name:digest(p) for p in paths},
        "portraits":{"engine":"Blender Cycles CPU","blender":bpy.app.version_string,"samples":20,
                     "ortho_scale_m":.445,"camera_world_m":[0,-2,.801],"resolution":[720,720],
                     "view_transform":"Standard","source":"Reimport of exported GLB; per-state albedo and one-hot morph weights."}
    },indent=2)+"\n")
